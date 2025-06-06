from fastapi import APIRouter, Depends, HTTPException
from app.db import Session, get_current_active_superuser, get_db, get_db_for_user
from app.models.user import User
from app.seed.accounts_page import delete_account_page, seed_account_page
from app.seed.effects import (
    seed_effects_and_dont_update_existing,
    seed_effects_with_hard_delete_of_existing,
)

router = APIRouter(tags=["admin"])


@router.post("/admin/reseed-account-page/{user_id}")
def reseed_account_page(
    user_id: int,
    current_user: User = Depends(get_current_active_superuser),
) -> dict[str, str]:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        delete_account_page(user_id)
    except Exception as e:
        print(f"❌ Failed to delete account page: {e}")
    try:
        seed_account_page(user_id)
        return {"status": "success"}
    except Exception as e:
        print(f"❌ Failed to seed account page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/reseed-account-page")
def reseed_all_account_pages(
    current_user: User = Depends(get_current_active_superuser),
    session: Session = Depends(get_db),
) -> dict[str, str]:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    for user in session.query(User).all():
        try:
            delete_account_page(user.id)
        except Exception as e:
            print(f"❌ Failed to delete account page for user {user.id}: {e}")
        try:
            seed_account_page(user.id)
        except Exception as e:
            print(f"❌ Failed to seed account page for user {user.id}: {e}")
    return {"status": "success"}


@router.post("/admin/reseed-notifications")
def reseed_all_notifications(
    current_user: User = Depends(get_current_active_superuser),
    additive: bool = False,
    session: Session = Depends(get_db),
) -> dict[str, str]:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    seed_func = (
        seed_effects_and_dont_update_existing
        if additive
        else seed_effects_with_hard_delete_of_existing
    )

    for user in session.query(User).all():
        user_specific_session = next(get_db_for_user(user.id))
        try:
            seed_func(user_specific_session, user)
            user_specific_session.commit()
        except Exception as e:
            print(f"❌ Failed to seed effects for user {user.id}: {e}")
            user_specific_session.rollback()
        finally:
            user_specific_session.close()

    return {"status": "success"}
