from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from itertools import groupby
from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import ColumnExpressionArgument, false, func, or_, true
from sqlalchemy.orm import Query as SqlQuery

from app.db import (
    Session,
    get_current_user,
    get_db,
)
from app.func_utils import pipe
from app.local_types import (
    AggregatedGroup,
    AggregatedTransactions,
    CategoryOut,
    TransactionEdit,
    TransactionOut,
)
from app.models.audit_log import AuditChange, AuditLog, AuditLogAction
from app.models.budget import BudgetCategoryLink, BudgetEntry, BudgetEntryId
from app.models.category import Category, CategoryId
from app.models.filter import FilterData, FilterEntries, GroupByOption
from app.models.transaction import Transaction
from app.models.transaction_source import TransactionSource, TransactionSourceId
from app.models.user import User
from app.models.worker_status import WorkerStatus


router = APIRouter(prefix="/transactions", tags=["transactions"])


CategoryLookup = dict[CategoryId, Category]
BudgetLookup = dict[CategoryId, BudgetEntry]
AccountLookup = dict[TransactionSourceId, TransactionSource]

GroupByKeyFunc = Callable[
    [Transaction, CategoryLookup, AccountLookup, BudgetLookup], str
]
SortFunc = Callable[
    [Transaction, CategoryLookup, AccountLookup, BudgetLookup], str | datetime
]
GroupByNameFunc = Callable[[str], str]
GroupByIdFunc = Callable[[str], str]


def get_stylized_name_lookup(session: Session, user: User) -> dict[int, str]:
    categories = (
        session.query(Category, TransactionSource)
        .join(TransactionSource, TransactionSource.id == Category.source_id)
        .filter(Category.user_id == user.id)
        .all()
    )
    return {
        category.id: f"{category.name} ({source.name})"
        for category, source in categories
    }


def get_account_key(
    transaction: Transaction,
    _lookup: CategoryLookup,
    account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> str:
    return account_lookup[transaction.transaction_source_id].name


def get_category_key(
    transaction: Transaction,
    lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> str:
    return lookup[transaction.category_id].name


def get_month_key(
    transaction: Transaction,
    _lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> str:
    return transaction.date_of_transaction.strftime("%B %Y")


def get_year_key(
    transaction: Transaction,
    _lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> str:
    return str(transaction.date_of_transaction.year)


def get_budget_key(
    transaction: Transaction,
    _lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> str:
    val = _budget_lookup.get(transaction.category_id)
    if val:
        return val.name
    return "Unbudgeted"


def get_category_sort(
    transaction: Transaction,
    lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> str:
    return lookup[transaction.category_id].name


def get_month_sort(
    transaction: Transaction,
    _lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> datetime:
    return transaction.date_of_transaction


def get_year_sort(
    transaction: Transaction,
    _lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> datetime:
    return transaction.date_of_transaction


def get_account_sort(
    transaction: Transaction,
    _lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> str:
    return str(transaction.transaction_source_id)


def get_budget_sort(
    transaction: Transaction,
    _lookup: CategoryLookup,
    _account_lookup: AccountLookup,
    _budget_lookup: BudgetLookup,
) -> str:
    return get_budget_key(transaction, _lookup, _account_lookup, _budget_lookup)


def id(key: str) -> str:
    return key


group_by_key_funcs: dict[GroupByOption, GroupByKeyFunc] = {
    GroupByOption.budget: get_budget_key,
    GroupByOption.account: get_account_key,
    GroupByOption.category: get_category_key,
    GroupByOption.month: get_month_key,
    GroupByOption.year: get_year_key,
}

sort_funcs: dict[GroupByOption, SortFunc] = {
    GroupByOption.category: get_category_sort,
    GroupByOption.month: get_month_sort,
    GroupByOption.year: get_year_sort,
    GroupByOption.account: get_account_sort,
    GroupByOption.budget: get_budget_sort,
}


group_by_name_funcs: dict[GroupByOption, GroupByNameFunc] = {
    GroupByOption.category: id,
    GroupByOption.month: id,
    GroupByOption.year: id,
    GroupByOption.account: id,
    GroupByOption.budget: id,
}

group_by_id_funcs: dict[GroupByOption, GroupByIdFunc] = {
    GroupByOption.category: id,
    GroupByOption.month: id,
    GroupByOption.year: id,
    GroupByOption.account: id,
    GroupByOption.budget: id,
}


def recursive_grouping(
    txns: list[Transaction],
    group_options: list[GroupByOption],
    category_lookup: CategoryLookup,
    account_lookup: AccountLookup,
    budget_lookup: BudgetLookup,
) -> list[AggregatedGroup]:
    if not group_options:
        total_withdrawals = sum(t.amount for t in txns if t.kind == "withdrawal")
        total_deposits = sum(t.amount for t in txns if t.kind == "deposit")
        return [
            AggregatedGroup(
                group_id="all",
                group_name="All",
                groupby_kind=None,
                total_withdrawals=total_withdrawals,
                budgeted_total=0,
                total_deposits=total_deposits,
                total_balance=total_deposits - total_withdrawals,
                transactions=[TransactionOut.model_validate(t) for t in txns],
                subgroups=[],
            )
        ]

    current = group_options[0]

    def key_fn(txn: Transaction) -> str:
        return group_by_key_funcs[current](
            txn, category_lookup, account_lookup, budget_lookup
        )

    def sort_fn(txn: Transaction) -> str | datetime:
        return sort_funcs[current](txn, category_lookup, account_lookup, budget_lookup)

    name_fn = group_by_name_funcs[current]
    id_fn = group_by_id_funcs[current]

    txns.sort(key=sort_fn, reverse=True)
    groups = []
    for key, group_iter in groupby(txns, key=key_fn):
        group_list = list(group_iter)
        group_withdrawals = sum(t.amount for t in group_list if t.kind == "withdrawal")
        group_deposits = sum(t.amount for t in group_list if t.kind == "deposit")
        balance = group_deposits - group_withdrawals
        group_id = id_fn(key)
        group_name = name_fn(key)

        if len(group_options) > 1:
            subgroups = recursive_grouping(
                group_list,
                group_options[1:],
                category_lookup,
                account_lookup,
                budget_lookup,
            )
            groups.append(
                AggregatedGroup(
                    group_id=group_id,
                    group_name=group_name,
                    groupby_kind=current,
                    budgeted_total=0,
                    total_withdrawals=group_withdrawals,
                    total_deposits=group_deposits,
                    total_balance=balance,
                    subgroups=subgroups,
                    transactions=[],
                )
            )
        else:
            groups.append(
                AggregatedGroup(
                    group_id=group_id,
                    group_name=group_name,
                    groupby_kind=current,
                    budgeted_total=0,
                    total_withdrawals=group_withdrawals,
                    total_deposits=group_deposits,
                    total_balance=balance,
                    subgroups=[],
                    transactions=[TransactionOut.model_validate(t) for t in group_list],
                )
            )
    return groups


@router.get(
    "/",
    dependencies=[Depends(get_current_user)],
    response_model=list[TransactionOut],
)
def get_transactions(
    session: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Transaction]:
    val = session.query(Transaction).filter(Transaction.user_id == user.id).all()
    return val


def build_grouping_option_choices(
    session: Session, user: User
) -> dict[GroupByOption, list[str]]:
    all_dates = (
        session.query(Transaction.date_of_transaction)
        .filter(Transaction.user_id == user.id)
        .join(
            TransactionSource, TransactionSource.id == Transaction.transaction_source_id
        )
        .filter(~TransactionSource.archived)
        .distinct()
        .order_by(Transaction.date_of_transaction)
        .all()
    )
    all_categories = (
        session.query(Category.name)
        .filter(Category.user_id == user.id)
        .join(TransactionSource, TransactionSource.id == Category.source_id)
        .filter(~TransactionSource.archived)
        .distinct()
        .order_by(Category.name)
        .all()
    )
    all_accounts = (
        session.query(TransactionSource.name)
        .filter(TransactionSource.user_id == user.id)
        .filter(~TransactionSource.archived)
        .distinct()
        .order_by(TransactionSource.name)
        .all()
    )

    all_entries = (
        session.query(BudgetEntry.name)
        .filter(BudgetEntry.user_id == user.id)
        .distinct()
        .order_by(BudgetEntry.name)
        .all()
    )

    val = {
        GroupByOption.year: list(
            {str(row.date_of_transaction.year) for row in all_dates}
        ),
        GroupByOption.month: list(
            {str(row.date_of_transaction.strftime("%B")) for row in all_dates}
        ),
        GroupByOption.category: list({category.name for category in all_categories}),
        GroupByOption.account: list({account.name for account in all_accounts}),
        GroupByOption.budget: list({entry.name for entry in all_entries}),
    }

    val[GroupByOption.budget].append("Unbudgeted")

    for key, value in val.items():
        val[key] = sorted(value)

    return val


def apply_category_filter(
    transactions: SqlQuery[Transaction],
    categories: FilterEntries,
) -> SqlQuery[Transaction]:
    if categories.specifics is None:
        return transactions

    return transactions.join(Category, Category.id == Transaction.category_id).filter(
        Category.name.in_(
            [c.value for c in categories.specifics] if categories.specifics else []
        )
    )


def apply_account_filter(
    transactions: SqlQuery[Transaction],
    accounts: FilterEntries,
) -> SqlQuery[Transaction]:
    if accounts.specifics is None:
        return transactions

    return (
        transactions.filter(
            TransactionSource.name.in_([a.value for a in accounts.specifics])
        )
        if accounts.specifics
        else transactions
    )


def apply_year_filter(
    transactions: SqlQuery[Transaction],
    years: FilterEntries,
) -> SqlQuery[Transaction]:
    if years.specifics is None:
        return transactions

    return transactions.filter(
        func.extract("year", Transaction.date_of_transaction).in_(
            list(
                map(int, [y.value for y in years.specifics] if years.specifics else [])
            )
        )
    )


def apply_budget_filter(
    transactions: SqlQuery[Transaction],
    budgets: FilterEntries,
) -> SqlQuery[Transaction]:
    MAGIC_WORD_FOR_NO_BUDGET = "Unbudgeted"

    # Separate out any real budget names from the special magic word
    normal_budgets = (
        [b.value for b in budgets.specifics if b.value != MAGIC_WORD_FOR_NO_BUDGET]
        if budgets.specifics
        else []
    )

    # If we have normal budget names, build an IN(...) condition; else use `false()`
    # (i.e. no normal budgets matched)
    budget_filter: ColumnExpressionArgument[bool]
    if normal_budgets:
        budget_filter = BudgetEntry.name.in_(normal_budgets)
    elif budgets.specifics is None:
        budget_filter = true()
    else:
        # No normal budgets in the list, so base condition is always false
        # (we'll check "Unbudgeted" separately below)
        budget_filter = false()

    # If the magic word "Unbudgeted" is in budgets, include transactions
    # where BudgetEntry is NULL as well.
    if budgets.specifics and MAGIC_WORD_FOR_NO_BUDGET in [
        b.value for b in budgets.specifics
    ]:
        budget_filter = or_(budget_filter, BudgetEntry.id.is_(None))

    return (
        transactions
        # Use left (outer) join so that rows with no BudgetCategoryLink
        # still appear (as NULLs in the joined fields).
        .outerjoin(
            BudgetCategoryLink,
            BudgetCategoryLink.category_id == Transaction.category_id,
        )
        .outerjoin(BudgetEntry, BudgetEntry.id == BudgetCategoryLink.budget_entry_id)
        .filter(budget_filter)
    )


def apply_month_filter(
    transactions: SqlQuery[Transaction],
    months: FilterEntries,
) -> SqlQuery[Transaction]:
    if months.specifics is None:
        return transactions

    MONTH_LOOKUP = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "11": 11,
        "12": 12,
    }

    month_numbers = (
        [MONTH_LOOKUP[m.value.lower()] for m in months.specifics]
        if months.specifics
        else []
    )
    return transactions.filter(
        func.extract("month", Transaction.date_of_transaction).in_(month_numbers)
    )


def get_budget_lookup(session: Session, user: User) -> BudgetLookup:
    links = (
        session.query(BudgetCategoryLink)
        .filter(BudgetCategoryLink.user_id == user.id)
        .all()
    )
    entries = session.query(BudgetEntry).filter(BudgetEntry.user_id == user.id).all()
    entries_dict: dict[BudgetEntryId, BudgetEntry] = {
        entry.id: entry for entry in entries
    }
    lookup: dict[CategoryId, BudgetEntry] = {}
    for link in links:
        lookup[link.category_id] = entries_dict[link.budget_entry_id]
    return lookup


def enrich_with_budget_info(
    session: Session, user: User, agg: AggregatedTransactions
) -> AggregatedTransactions:
    budget_entries = (
        session.query(BudgetEntry).filter(BudgetEntry.user_id == user.id).all()
    )

    _entry_lookup = {entry.id: entry for entry in budget_entries}
    entry_lookup_worse: dict[str, float] = {
        entry.name: float(entry.monthly_target) for entry in budget_entries
    }

    # first we start at the outer most group
    for group in agg.groups:
        if group.groupby_kind == GroupByOption.budget:
            total_amount: float = 0
            per_month_amount = entry_lookup_worse.get(group.group_name, 0)
            for subgroup in group.subgroups:
                if subgroup.groupby_kind == GroupByOption.month:
                    subgroup.budgeted_total = per_month_amount
                    total_amount += per_month_amount
                elif subgroup.groupby_kind == GroupByOption.year:
                    subgroup.budgeted_total = per_month_amount * 12
                    total_amount += per_month_amount * 12
            group.budgeted_total = total_amount

    return agg


def build_transactions(
    session: Session, user: User, current_filter: FilterData
) -> list[Transaction]:
    transactions_query = (
        session.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .join(
            TransactionSource, TransactionSource.id == Transaction.transaction_source_id
        )
        .filter(~TransactionSource.archived)
    )

    FILTER_FUNCTIONS: dict[
        GroupByOption,
        Callable[[SqlQuery[Transaction], FilterEntries], SqlQuery[Transaction]],
    ] = {
        GroupByOption.year: apply_year_filter,
        GroupByOption.month: apply_month_filter,
        GroupByOption.category: apply_category_filter,
        GroupByOption.account: apply_account_filter,
        GroupByOption.budget: apply_budget_filter,
    }

    for option, argument in current_filter.lookup.items():
        filter_func = FILTER_FUNCTIONS[option]
        if argument.specifics and len(argument.specifics) > 0:
            transactions_query = filter_func(transactions_query, argument)

    return transactions_query.order_by(Transaction.transaction_source_id).all()


def build_empty_result(
    grouping_option_choices: dict[GroupByOption, list[str]],
) -> AggregatedTransactions:
    return AggregatedTransactions(
        groups=[],
        overall_withdrawals=0.0,
        group_by_ordering=[],
        overall_deposits=0.0,
        overall_balance=0.0,
        grouping_options_choices=grouping_option_choices,
    )


@dataclass(kw_only=True)
class TransactionContext:
    current_filter: FilterData = field(default_factory=FilterData)
    session: Session
    user: User
    transactions: list[Transaction] = field(default_factory=list)
    grouping_option_choices: dict[GroupByOption, list[str]] = field(
        default_factory=dict
    )
    category_lookup: dict[CategoryId, Category] = field(default_factory=dict)
    budget_lookup: dict[CategoryId, BudgetEntry] = field(default_factory=dict)
    transaction_source_lookup: dict[TransactionSourceId, TransactionSource] = field(
        default_factory=dict
    )
    overall_withdrawals: float = 0.0
    overall_deposits: float = 0.0
    overall_balance: float = 0.0
    group_by_with_hidden_removed: list[GroupByOption] = field(default_factory=list)
    groups: list[AggregatedGroup] = field(default_factory=list)
    result: AggregatedTransactions | None = None


def fetch_transactions(ctx: TransactionContext) -> TransactionContext:
    ctx.transactions = build_transactions(ctx.session, ctx.user, ctx.current_filter)
    return ctx


def fetch_grouping_options(ctx: TransactionContext) -> TransactionContext:
    ctx.grouping_option_choices = build_grouping_option_choices(ctx.session, ctx.user)
    return ctx


def build_all_lookups(ctx: TransactionContext) -> TransactionContext:
    if not ctx.transactions:
        return ctx

    ctx.category_lookup, ctx.budget_lookup, ctx.transaction_source_lookup = (
        build_lookups(ctx.session, ctx.user, ctx.transactions, ctx.current_filter)
    )
    return ctx


def compute_totals(ctx: TransactionContext) -> TransactionContext:
    if not ctx.transactions:
        return ctx

    ctx.overall_withdrawals, ctx.overall_deposits, ctx.overall_balance = (
        calculate_totals(ctx.transactions)
    )
    return ctx


def get_group_by_options(ctx: TransactionContext) -> TransactionContext:
    ctx.group_by_with_hidden_removed = get_visible_group_by_options(ctx.current_filter)
    return ctx


def handle_empty_transactions(ctx: TransactionContext) -> TransactionContext:
    if not ctx.transactions:
        ctx.result = build_empty_result(ctx.grouping_option_choices)
    return ctx


def group_transactions(ctx: TransactionContext) -> TransactionContext:
    if not ctx.transactions or ctx.result:
        return ctx

    ctx.groups = recursive_grouping(
        ctx.transactions,
        ctx.group_by_with_hidden_removed,
        ctx.category_lookup,
        ctx.transaction_source_lookup,
        ctx.budget_lookup,
    )
    return ctx


def build_result(ctx: TransactionContext) -> TransactionContext:
    if ctx.result:
        return ctx

    ctx.result = AggregatedTransactions(
        groups=ctx.groups,
        group_by_ordering=list(ctx.current_filter.lookup.keys()),
        overall_withdrawals=ctx.overall_withdrawals,
        overall_deposits=ctx.overall_deposits,
        overall_balance=ctx.overall_balance,
        grouping_options_choices=ctx.grouping_option_choices,
    )
    return ctx


def add_budget_info(ctx: TransactionContext) -> AggregatedTransactions:
    if not ctx.result:
        return build_empty_result(ctx.grouping_option_choices)

    return enrich_with_budget_info(ctx.session, ctx.user, ctx.result)


@router.post(
    "/aggregated",
    dependencies=[Depends(get_current_user)],
    response_model=AggregatedTransactions,
)
def get_aggregated_transactions(
    current_filter: FilterData | None = None,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AggregatedTransactions:
    ctx = TransactionContext(
        current_filter=current_filter or FilterData(), session=session, user=user
    )

    return pipe(
        ctx,
        fetch_transactions,
        fetch_grouping_options,
        build_all_lookups,
        compute_totals,
        get_group_by_options,
        handle_empty_transactions,
        group_transactions,
        build_result,
        final=add_budget_info,
    )


def make_audit_entry(old: Transaction, new: TransactionEdit) -> list[AuditLog]:
    actions: list[AuditLogAction] = []
    changes: list[AuditChange] = []

    if old.date_of_transaction != new.date_of_transaction:
        actions.append(AuditLogAction.change_date)
        changes.append(
            AuditChange(
                old_date=old.date_of_transaction, new_date=new.date_of_transaction
            )
        )
    if old.amount != new.amount:
        actions.append(AuditLogAction.change_amount)
        changes.append(AuditChange(old_amount=old.amount, new_amount=new.amount))
    if old.category_id != new.category_id:
        actions.append(AuditLogAction.reclassify_transaction_category)
        changes.append(
            AuditChange(
                old_category=old.category_id,
                new_category=cast(CategoryId, new.category_id),
            )
        )
    if old.kind != new.kind:
        actions.append(AuditLogAction.reclassify_transaction_kind)
        changes.append(AuditChange(old_kind=old.kind, new_kind=new.kind))

    logs: list[AuditLog] = []
    for action, change in zip(actions, changes, strict=False):
        val = AuditLog(
            user_id=old.user_id,
            action=action,
            change=change,
            transaction_id=old.id,
            apply_to_future=True,
        )
        logs.append(val)

    return logs


@router.put(
    "/{transaction_id}",
    response_model=TransactionOut,
)
def update_transaction(
    transaction: TransactionEdit,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Transaction:
    transaction_db = (
        session.query(Transaction)
        .filter(Transaction.id == transaction.id, Transaction.user_id == user.id)
        .one()
    )

    audit_logs = make_audit_entry(old=transaction_db, new=transaction)

    transaction_db.amount = transaction.amount
    transaction_db.description = transaction.description
    transaction_db.date_of_transaction = transaction.date_of_transaction
    transaction_db.kind = transaction.kind
    transaction_db.category_id = cast(CategoryId, transaction.category_id)

    session.add_all(audit_logs)
    session.commit()
    return transaction_db


@router.post(
    "/delete/{transaction_id}",
    response_model=dict[str, str],
)
def delete_transaction(
    transaction_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, str]:
    transaction_db = (
        session.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .one_or_none()
    )
    if not transaction_db:
        raise HTTPException(status_code=404, detail="Transaction not found")

    session.delete(transaction_db)
    session.commit()
    return {"message": "ok"}


@router.get(
    "list_categories/{transaction_id}",
    response_model=list[CategoryOut],
)
def list_categories(
    transaction_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CategoryOut]:
    categories_query = session.query(Category).filter(
        Category.user_id == user.id,
    )

    transaction_db = (
        session.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .filter(~Transaction.archived)
        .one()
    )
    categories_query = categories_query.filter(
        Category.source_id == transaction_db.transaction_source_id
    )

    stylized_name_lookup = get_stylized_name_lookup(session, user)

    return [
        CategoryOut(
            name=category.name,
            stylized_name=stylized_name_lookup[category.id],
            id=category.id,
            archived=category.archived,
            source_id=category.source_id,
        )
        for category in categories_query.all()
    ]


@router.get(
    "list_all_categories",
    response_model=list[CategoryOut],
)
def list_all_categories(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CategoryOut]:
    categories_query = (
        session.query(Category)
        .join(TransactionSource, TransactionSource.id == Category.source_id)
        .filter(
            Category.user_id == user.id,
            ~TransactionSource.archived,
        )
    )

    stylized_name_lookup = get_stylized_name_lookup(session, user)

    return [
        CategoryOut(
            name=category.name,
            stylized_name=stylized_name_lookup[category.id],
            id=category.id,
            archived=category.archived,
            source_id=category.source_id,
        )
        for category in categories_query.all()
    ]


def build_lookups(
    session: Session,
    user: User,
    transactions: list[Transaction],
    current_filter: FilterData,
) -> tuple[
    dict[CategoryId, Category],
    dict[CategoryId, BudgetEntry],
    dict[TransactionSourceId, TransactionSource],
]:
    # Build category lookup if needed
    if GroupByOption.category in current_filter.lookup:
        category_ids = {txn.category_id for txn in transactions}
        category_lookup = {
            c.id: c
            for c in session.query(Category).filter(Category.id.in_(category_ids))
        }
    else:
        category_lookup = {}

    # Build budget lookup
    budget_lookup = get_budget_lookup(session, user)

    # Build transaction source lookup
    ts_ids = {txn.transaction_source_id for txn in transactions}
    ts_lookup = {
        ts.id: ts
        for ts in session.query(TransactionSource).filter(
            TransactionSource.id.in_(ts_ids)
        )
    }

    return category_lookup, budget_lookup, ts_lookup


def calculate_totals(transactions: list[Transaction]) -> tuple[float, float, float]:
    overall_withdrawals = sum(t.amount for t in transactions if t.kind == "withdrawal")
    overall_deposits = sum(t.amount for t in transactions if t.kind == "deposit")
    overall_balance = overall_deposits - overall_withdrawals
    return overall_withdrawals, overall_deposits, overall_balance


def get_visible_group_by_options(current_filter: FilterData) -> list[GroupByOption]:
    return sorted(
        [key for key, entries in current_filter.lookup.items() if entries.visible],
        key=lambda x: current_filter.lookup[x].index,
    )


class LandingStatus(str, Enum):
    has_transactions = "has_transactions"
    no_transactions = "no_transactions_not_processing"
    no_transactions_processing = "no_transactions_processing"


@router.get(
    "get_landing_status",
    response_model=LandingStatus,
)
def get_landing_status(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> LandingStatus:
    transaction = (
        session.query(Transaction)
        .filter(
            Transaction.user_id == user.id,
        )
        .first()
    )

    if transaction:
        return LandingStatus.has_transactions
    else:
        worker = (
            session.query(WorkerStatus)
            .filter(
                WorkerStatus.user_id == user.id,
            )
            .first()
        )
        if worker:
            return LandingStatus.no_transactions_processing
        return LandingStatus.no_transactions
