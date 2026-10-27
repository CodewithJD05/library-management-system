
import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.models.staff_user import StaffUser


@pytest.fixture()
def admin_client(authenticated_client, db_session):
    # The authenticated_client fixture creates a librarian.
    # Promote that test user to admin for these tests.
    admin = db_session.scalar(
        select(StaffUser).where(
            StaffUser.email == "librarian@test.com"
        )
    )
    admin.role = "admin"
    db_session.commit()

    return authenticated_client


def test_admin_can_create_staff(admin_client, db_session):
    response = admin_client.post(
        "/staff/",
        json={
            "full_name": "New Librarian",
            "email": "new.librarian@test.com",
            "password": "StrongPassword123!",
            "role": "librarian",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "new.librarian@test.com"
    assert data["role"] == "librarian"
    assert "password_hash" not in data
    assert "password" not in data

    staff_user = db_session.scalar(
        select(StaffUser).where(
            StaffUser.email == "new.librarian@test.com"
        )
    )

    assert staff_user is not None
    assert staff_user.password_hash != "StrongPassword123!"
    assert verify_password(
        "StrongPassword123!",
        staff_user.password_hash,
    )


def test_admin_can_list_staff(admin_client):
    response = admin_client.get("/staff/")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

    assert any(
        user["email"] == "librarian@test.com"
        for user in response.json()
    )


def test_admin_cannot_create_duplicate_email(admin_client):
    response = admin_client.post(
        "/staff/",
        json={
            "full_name": "Duplicate User",
            "email": "librarian@test.com",
            "password": "StrongPassword123!",
            "role": "librarian",
        },
    )

    assert response.status_code == 409


def test_librarian_cannot_access_staff_management(
    authenticated_client,
):
    response = authenticated_client.get("/staff/")

    assert response.status_code == 403


def test_cannot_demote_last_active_admin(admin_client):
    admin_id = next(
        user["id"]
        for user in admin_client.get("/staff/").json()
        if user["email"] == "librarian@test.com"
    )

    response = admin_client.patch(
        f"/staff/{admin_id}",
        json={"role": "librarian"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Cannot remove the last active administrator"
    )


def test_cannot_deactivate_last_active_admin(admin_client):
    admin_id = next(
        user["id"]
        for user in admin_client.get("/staff/").json()
        if user["email"] == "librarian@test.com"
    )

    response = admin_client.patch(
        f"/staff/{admin_id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Cannot remove the last active administrator"
    )


def test_admin_can_demote_admin_when_another_active_admin_exists(
    admin_client,
    db_session,
):
    admin_id = db_session.scalar(
        select(StaffUser.id).where(
            StaffUser.email == "librarian@test.com"
        )
    )

    second_admin = StaffUser(
        full_name="Second Admin",
        email="second.admin@test.com",
        password_hash="test-hash",
        role="admin",
        is_active=True,
    )

    db_session.add(second_admin)
    db_session.commit()

    response = admin_client.patch(
        f"/staff/{admin_id}",
        json={"role": "librarian"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "librarian"


def test_existing_token_uses_updated_staff_role(
    authenticated_client,
    db_session,
):
    # The existing token belongs to a librarian.
    staff_user = db_session.scalar(
        select(StaffUser).where(
            StaffUser.email == "librarian@test.com"
        )
    )

    assert staff_user.role == "librarian"

    # A librarian cannot access staff management.
    response = authenticated_client.get("/staff/")
    assert response.status_code == 403

    # Promote the same user without issuing a new token.
    staff_user.role = "admin"
    db_session.commit()

    # The existing token should now use the updated database role.
    response = authenticated_client.get("/staff/")
    assert response.status_code == 200