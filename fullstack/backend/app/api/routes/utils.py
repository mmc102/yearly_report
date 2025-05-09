from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app.db import get_current_active_superuser
from app.local_types import Message
from app.utils import generate_test_email

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails.
    """
    _email_data = generate_test_email(email_to=email_to)
    return Message(message="Test email sent")


@router.get("/health-check/")
async def health_check() -> bool:
    return True
