import uuid
from unittest.mock import patch, MagicMock

import pyotp
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.core.security import verify_password
from app.models.user import User
from app.tests.utils.utils import random_email, random_lower_string

from ....local_types import UserRegister


@pytest.mark.skip(reason="Skipping for now")
def test_get_users_superuser_me(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=superuser_token_headers)
    current_user = r.json()
    assert current_user
    assert current_user["is_active"] is True
    assert current_user["is_superuser"]
    assert current_user["email"] == settings.FIRST_SUPERUSER


@pytest.mark.skip(reason="Skipping for now")
def test_get_users_normal_user_me(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=normal_user_token_headers)
    current_user = r.json()
    assert current_user
    assert current_user["id"] is not None
    assert current_user["settings"] is not None


@pytest.mark.skip(reason="Skipping for now")
def test_create_user_new_email(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    with (
        patch("app.utils.send_email", return_value=None),
        patch("app.core.config.settings.SMTP_HOST", "smtp.example.com"),
        patch("app.core.config.settings.SMTP_USER", "admin@example.com"),
    ):
        username = random_email()
        password = random_lower_string()
        data = {"email": username, "password": password}
        r = client.post(
            f"{settings.API_V1_STR}/users/",
            headers=superuser_token_headers,
            json=data,
        )
        assert 200 <= r.status_code < 300
        created_user = r.json()
        user = crud.get_user_by_email(session=db, email=username)
        assert user
        assert user.email == created_user["email"]


@pytest.mark.skip(reason="Skipping for now")
def test_get_existing_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    user = crud.create_user(session=db, user=user_in)
    user_id = user.id
    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert 200 <= r.status_code < 300
    api_user = r.json()
    existing_user = crud.get_user_by_email(session=db, email=username)
    assert existing_user
    assert existing_user.email == api_user["email"]


@pytest.mark.skip(reason="Skipping for now")
def test_get_existing_user_current_user(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    user = crud.create_user(session=db, user=user_in)
    user_id = user.id

    # Create auth headers directly without going through login flow
    headers = {"Authorization": f"Bearer test_token_{username}"}

    # Mock the authentication dependency to bypass 2FA
    with patch("app.db.get_current_active_user", return_value=user):
        r = client.get(
            f"{settings.API_V1_STR}/users/{user_id}",
            headers=headers,
        )
        assert 200 <= r.status_code < 300
        api_user = r.json()
        existing_user = crud.get_user_by_email(session=db, email=username)
        assert existing_user
        assert existing_user.email == api_user["email"]


@pytest.mark.skip(reason="Skipping for now")
def test_get_existing_user_permissions_error(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403
    assert r.json() == {"detail": "The user doesn't have enough privileges"}


@pytest.mark.skip(reason="Skipping for now")
def test_create_user_existing_username(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    # username = email
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    crud.create_user(session=db, user=user_in)
    data = {"email": username, "password": password}
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=data,
    )
    created_user = r.json()
    assert r.status_code == 400
    assert "_id" not in created_user


@pytest.mark.skip(reason="Skipping for now")
def test_create_user_by_normal_user(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    username = random_email()
    password = random_lower_string()
    data = {"email": username, "password": password}
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 403


@pytest.mark.skip(reason="Skipping for now")
def test_retrieve_users(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    crud.create_user(session=db, user=user_in)

    username2 = random_email()
    password2 = random_lower_string()
    user_in2 = UserRegister(email=username2, password=password2, full_name="dogg")
    crud.create_user(session=db, user=user_in2)

    r = client.get(f"{settings.API_V1_STR}/users/", headers=superuser_token_headers)
    all_users = r.json()

    assert len(all_users["data"]) > 1
    assert "count" in all_users
    for item in all_users["data"]:
        assert "email" in item


@pytest.mark.skip(reason="Skipping for now")
def test_update_user_me(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    full_name = "Updated Name"
    email = random_email()
    data = {"full_name": full_name, "email": email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 200
    updated_user = r.json()
    assert updated_user["email"] == email
    assert updated_user["full_name"] == full_name

    user_query = db.query(User).filter(User.email == email).first()

    assert user_query
    assert user_query.email == email
    assert user_query.full_name == full_name


@pytest.mark.skip(reason="Skipping for now")
def test_update_password_me(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    new_password = random_lower_string()
    data = {
        "current_password": settings.FIRST_SUPERUSER_PASSWORD,
        "new_password": new_password,
    }
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    updated_user = r.json()
    assert updated_user["message"] == "Password updated successfully"

    user_query = db.query(User).filter(User.email == settings.FIRST_SUPERUSER).first()
    assert user_query
    assert user_query.email == settings.FIRST_SUPERUSER
    assert verify_password(new_password, user_query.hashed_password)

    # Revert to the old password to keep consistency in test
    old_data = {
        "current_password": new_password,
        "new_password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=old_data,
    )
    assert r.status_code == 200
    assert verify_password(
        settings.FIRST_SUPERUSER_PASSWORD, user_query.hashed_password
    )


@pytest.mark.skip(reason="Skipping for now")
def test_update_password_me_incorrect_password(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    new_password = random_lower_string()
    data = {"current_password": new_password, "new_password": new_password}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 400
    updated_user = r.json()
    assert updated_user["detail"] == "Incorrect password"


@pytest.mark.skip(reason="Skipping for now")
def test_update_user_me_email_exists(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    user = crud.create_user(session=db, user=user_in)

    data = {"email": user.email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "User with this email already exists"


@pytest.mark.skip(reason="Skipping for now")
def test_update_password_me_same_password_error(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {
        "current_password": settings.FIRST_SUPERUSER_PASSWORD,
        "new_password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 400
    updated_user = r.json()
    assert (
        updated_user["detail"] == "New password cannot be the same as the current one"
    )


@pytest.mark.skip(reason="Skipping for now")
def test_register_user(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_lower_string()
    full_name = random_lower_string()
    data = {"email": username, "password": password, "full_name": full_name}
    # Don't check if mock_send is called since it might not be in the test environment
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )
    assert r.status_code == 200
    created_user = r.json()
    assert created_user["email"] == username
    assert created_user["full_name"] == full_name

    user_db = db.query(User).filter(User.email == username).first()
    assert user_db
    assert user_db.email == username
    assert user_db.full_name == full_name
    assert verify_password(password, user_db.hashed_password)


@pytest.mark.skip(reason="Skipping for now")
def test_register_user_already_exists_error(client: TestClient) -> None:
    password = random_lower_string()
    full_name = random_lower_string()
    data = {
        "email": settings.FIRST_SUPERUSER,
        "password": password,
        "full_name": full_name,
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "The user with this email already exists in the system"


@pytest.mark.skip(reason="Skipping for now")
def test_update_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    user = crud.create_user(session=db, user=user_in)

    data = {"full_name": "Updated_full_name"}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    updated_user = r.json()

    assert updated_user["full_name"] == "Updated_full_name"

    user_db = db.query(User).filter(User.email == username).first()
    db.refresh(user_db)
    assert user_db
    assert user_db.full_name == "Updated_full_name"


@pytest.mark.skip(reason="Skipping for now")
def test_update_user_not_exists(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"full_name": "Updated_full_name"}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "The user with this id does not exist in the system"


@pytest.mark.skip(reason="Skipping for now")
def test_update_user_email_exists(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    user = crud.create_user(session=db, user=user_in)

    username2 = random_email()
    password2 = random_lower_string()
    user_in2 = UserRegister(email=username2, password=password2, full_name="dogg")
    user2 = crud.create_user(session=db, user=user_in2)

    data = {"email": user2.email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "User with this email already exists"


@pytest.mark.skip(reason="Skipping for now")
def test_delete_user_me(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    user = crud.create_user(session=db, user=user_in)
    user_id = user.id

    # Create auth headers directly without going through login flow
    headers = {"Authorization": f"Bearer test_token_{username}"}

    # Mock the authentication dependency to bypass 2FA
    with patch("app.db.get_current_active_user", return_value=user):
        r = client.delete(
            f"{settings.API_V1_STR}/users/me",
            headers=headers,
        )
        assert r.status_code == 200
        deleted_user = r.json()
        assert deleted_user["message"] == "User deleted successfully"

    user_db = db.query(User).filter(User.id == user_id).first()
    assert user_db is None


@pytest.mark.skip(reason="Skipping for now")
def test_delete_user_me_as_superuser(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=superuser_token_headers,
    )
    assert r.status_code == 403
    response = r.json()
    assert response["detail"] == "Super users are not allowed to delete themselves"


@pytest.mark.skip(reason="Skipping for now")
def test_delete_user_super_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    user = crud.create_user(session=db, user=user_in)
    user_id = user.id
    r = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    deleted_user = r.json()
    assert deleted_user["message"] == "User deleted successfully"
    result = db.query(User).filter(User.id == user_id).first()
    assert result is None


@pytest.mark.skip(reason="Skipping for now")
def test_delete_user_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


@pytest.mark.skip(reason="Skipping for now")
def test_delete_user_current_super_user_error(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    super_user = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert super_user
    user_id = super_user.id

    r = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Super users are not allowed to delete themselves"


@pytest.mark.skip(reason="Skipping for now")
def test_delete_user_without_privileges(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserRegister(email=username, password=password, full_name="catt")
    user = crud.create_user(session=db, user=user_in)

    r = client.delete(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "The user doesn't have enough privileges"
