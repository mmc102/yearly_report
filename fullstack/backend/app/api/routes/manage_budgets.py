from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_current_user, get_db
from app.local_types import (
    BudgetCategoryLinkBase,
    BudgetCategoryLinkOut,
    BudgetCategoryLinkStatus,
    BudgetEntryCreate,
    BudgetEntryEdit,
    BudgetEntryOut,
    BudgetEntryStatus,
    BudgetOut,
    BudgetStatus,
    TransactionOut,
)
from app.models.budget import Budget, BudgetCategoryLink, BudgetEntry, BudgetEntryId
from app.models.category import Category, CategoryId
from app.models.transaction_source import TransactionSource
from app.models.transaction import Transaction, TransactionKind
from app.models.user import User


router = APIRouter(prefix="/budgets", tags=["budgets"])


def create_budget(session: Session, user: User) -> Budget:
    new_budget = Budget(name="Budget", user_id=user.id, active=True)
    session.add(new_budget)
    session.commit()
    return new_budget


def get_budget_out(session: Session, user: User) -> BudgetOut:
    budget = session.query(Budget).filter(Budget.user_id == user.id).first()

    if not budget:
        budget = create_budget(session=session, user=user)

    entries = (
        session.query(BudgetEntry)
        .filter(BudgetEntry.budget_id == budget.id, BudgetEntry.user_id == user.id)
        .all()
    )

    entry_ids = [entry.id for entry in entries]
    categories = (
        session.query(BudgetCategoryLink)
        .filter(
            BudgetCategoryLink.budget_entry_id.in_(entry_ids),
            BudgetCategoryLink.user_id == user.id,
        )
        .all()
    )

    category_by_entry: dict[BudgetEntryId, list[BudgetCategoryLinkOut]] = defaultdict(
        list
    )

    name_lookup = get_stylized_name_lookup(session, user)

    for category in categories:
        category_by_entry[category.budget_entry_id].append(
            BudgetCategoryLinkOut(
                **category.__dict__, stylized_name=name_lookup[category.category_id]
            )
        )

    entries_out = [
        BudgetEntryOut(
            **entry.__dict__,
            category_links=category_by_entry[entry.id],
        )
        for entry in entries
    ]
    return BudgetOut(
        active=budget.active,
        id=budget.id,
        user_id=budget.user_id,
        name=budget.name,
        entries=entries_out,
    )


@router.get("/{budget_id}/entries", response_model=list[BudgetEntryOut])
def get_budget_entries(
    budget_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BudgetEntryOut]:
    db_entries = (
        session.query(BudgetEntry)
        .filter(BudgetEntry.budget_id == budget_id, BudgetEntry.user_id == user.id)
        .all()
    )

    entry_ids = [entry.id for entry in db_entries]

    budget_links = (
        session.query(BudgetCategoryLink)
        .filter(
            BudgetCategoryLink.budget_entry_id.in_(entry_ids),
            BudgetCategoryLink.user_id == user.id,
        )
        .all()
    )

    link_by_entry = defaultdict(list)
    for link in budget_links:
        link_by_entry[link.budget_entry_id].append(link)

    if not db_entries:
        raise HTTPException(status_code=404, detail="Budget not found.")

    val = [
        BudgetEntryOut.model_validate(
            {**entry.__dict__, "category_links": link_by_entry[entry.id]}
        )
        for entry in db_entries
    ]
    return val


@router.post("/{budget_id}/entries", response_model=BudgetEntryOut)
def create_budget_entry(
    budget_id: int,
    entry: BudgetEntryCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetEntryOut:
    new_entry = BudgetEntry(
        amount=Decimal(entry.amount),
        name=entry.name,
        budget_id=budget_id,
        user_id=user.id,
    )
    session.add(new_entry)
    session.commit()

    category_links = []
    for category_link_id in entry.category_link_ids:
        category_links.append(
            BudgetCategoryLink(
                budget_entry_id=new_entry.id,
                category_id=category_link_id,
                user_id=user.id,
            )
        )
    session.add_all(category_links)
    session.commit()
    session.refresh(new_entry)
    stylized_name_lookup = get_stylized_name_lookup(session, user)

    links_out: list[BudgetCategoryLinkOut] = [
        BudgetCategoryLinkOut(
            budget_entry_id=link.budget_entry_id,
            category_id=link.category_id,
            id=link.id,
            stylized_name=stylized_name_lookup[link.category_id],
        )
        for link in category_links
    ]

    return BudgetEntryOut(
        budget_id=new_entry.budget_id,
        user_id=new_entry.user_id,
        amount=new_entry.amount,
        name=new_entry.name,
        id=new_entry.id,
        category_links=links_out,
    )


def get_stylized_name_lookup(session: Session, user: User) -> dict[CategoryId, str]:
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


@router.put("/entry/{entry_id}", response_model=BudgetEntryOut)
def update_budget_entry(
    entry_id: int,
    entry: BudgetEntryEdit,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetEntryOut:
    db_entry = (
        session.query(BudgetEntry)
        .filter(BudgetEntry.id == entry_id, BudgetEntry.user_id == user.id)
        .one_or_none()
    )

    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found.")

    db_entry.name = entry.name
    db_entry.amount = Decimal(entry.amount)

    session.query(BudgetCategoryLink).filter(
        BudgetCategoryLink.budget_entry_id == db_entry.id,
        BudgetCategoryLink.user_id == user.id,
    ).delete()
    links = [
        BudgetCategoryLink(
            budget_entry_id=db_entry.id, user_id=user.id, category_id=entry.category_id
        )
        for entry in entry.category_links
    ]

    session.add_all(links)

    session.commit()
    session.refresh(db_entry)

    stylized_name_lookup = get_stylized_name_lookup(session, user)

    links_out: list[BudgetCategoryLinkOut] = [
        BudgetCategoryLinkOut(
            budget_entry_id=link.budget_entry_id,
            category_id=link.category_id,
            id=link.id,
            stylized_name=stylized_name_lookup[link.category_id],
        )
        for link in links
    ]

    return BudgetEntryOut(
        budget_id=db_entry.budget_id,
        user_id=db_entry.user_id,
        amount=db_entry.amount,
        name=db_entry.name,
        id=db_entry.id,
        category_links=links_out,
    )


@router.delete("/entry/{entry_id}", response_model=None)
def delete_budget_entry(
    entry_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    db_entry = (
        session.query(BudgetEntry)
        .filter(BudgetEntry.id == entry_id, BudgetEntry.user_id == user.id)
        .one_or_none()
    )

    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found.")

    session.query(BudgetCategoryLink).filter(
        BudgetCategoryLink.budget_entry_id == entry_id
    ).delete()
    session.delete(db_entry)

    session.commit()
    return None


@router.get("/{budget_entry_id}/categories", response_model=list[BudgetCategoryLinkOut])
def get_budget_categories(
    budget_entry_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BudgetCategoryLinkOut]:
    query = session.query(BudgetCategoryLink).filter(
        BudgetCategoryLink.budget_entry_id == budget_entry_id,
        BudgetCategoryLink.user_id == user.id,
    )

    stylized_name_lookup = get_stylized_name_lookup(session, user)

    return [
        BudgetCategoryLinkOut(
            budget_entry_id=link.budget_entry_id,
            category_id=link.category_id,
            id=link.id,
            stylized_name=stylized_name_lookup[link.category_id],
        )
        for link in query.all()
    ]


@router.post("/{budget_entry_id}/categories", response_model=BudgetCategoryLinkOut)
def create_budget_category(
    budget_entry_id: int,
    category: BudgetCategoryLinkBase,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetCategoryLink:
    new_link = BudgetCategoryLink(
        **category.model_dump(), budget_entry_id=budget_entry_id, user_id=user.id
    )
    session.add(new_link)
    session.commit()
    session.refresh(new_link)
    return new_link


@router.put("/categories/{category_link_id}", response_model=BudgetCategoryLinkOut)
def update_budget_category(
    category_link_id: int,
    category: BudgetCategoryLinkBase,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetCategoryLink:
    db_link = (
        session.query(BudgetCategoryLink)
        .filter(
            BudgetCategoryLink.id == category_link_id,
            BudgetCategoryLink.user_id == user.id,
        )
        .one_or_none()
    )

    if not db_link:
        raise HTTPException(status_code=404, detail="Category link not found.")

    for key, value in category.model_dump().items():
        setattr(db_link, key, value)

    session.commit()
    session.refresh(db_link)
    return db_link


@router.delete("/categories/{category_link_id}", response_model=None)
def delete_budget_category(
    category_link_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    db_link = (
        session.query(BudgetCategoryLink)
        .filter(
            BudgetCategoryLink.id == category_link_id,
            BudgetCategoryLink.user_id == user.id,
        )
        .one_or_none()
    )

    if not db_link:
        raise HTTPException(status_code=404, detail="Category link not found.")

    session.delete(db_link)
    session.commit()
    return None


def group_transactions_by_month(
    transactions: list[Transaction],
) -> dict[str, list[Transaction]]:
    grouped_transactions = defaultdict(list)

    for transaction in transactions:
        month = transaction.date_of_transaction.strftime("%Y-%m")
        grouped_transactions[month].append(transaction)

    return dict(grouped_transactions)


@router.get("/budget_status", response_model=BudgetStatus)
def get_budget_status(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetStatus:
    budget = get_budget_out(session=session, user=user)

    entry_statuses = []
    months_with_entries = set()
    for entry in budget.entries:
        category_status: dict[str, BudgetCategoryLinkStatus] = {}
        running_total: Decimal = Decimal(0)
        for category in entry.category_links:
            transactions = (
                session.query(Transaction)
                .filter(Transaction.category_id == category.category_id)
                .all()
            )

            for month, month_transactions in group_transactions_by_month(
                transactions
            ).items():
                transactions_out = [
                    TransactionOut(**transaction.__dict__)
                    for transaction in month_transactions
                    if transaction.kind == TransactionKind.withdrawal
                ]
                total = Decimal(sum([t.amount for t in transactions_out]))
                running_total += total
                months_with_entries.add(month)
                category_status[month] = BudgetCategoryLinkStatus(
                    budget_entry_id=category.budget_entry_id,
                    id=category.id,
                    stylized_name=category.stylized_name,
                    category_id=category.category_id,
                    transactions=transactions_out,
                    total=total,
                )

        entry_statuses.append(
            BudgetEntryStatus(
                id=entry.id,
                budget_id=budget.id,
                name=entry.name,
                amount=entry.amount,
                category_links_status=category_status,
                total=running_total,
            )
        )

    return BudgetStatus(
        budget_id=budget.id,
        user_id=user.id,
        name=budget.name,
        active=True,
        entries=budget.entries,
        entry_status=entry_statuses,
        months_with_entries=list(months_with_entries),
    )
