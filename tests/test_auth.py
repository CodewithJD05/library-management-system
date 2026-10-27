
from app.core.security import create_access_token, hash_password
from app.models.staff_user import StaffUser


def create_staff_user(
    db_session,
    email="librarian@test.com",
    password="TestPassword123!",
    is_active=True,
    role="librarian",
):
    staff_user = StaffUser(
        full_name="Test Librarian",
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db_session.add(staff_user)
    db_session.commit()
    db_session.refresh(staff_user)
    return staff_user


def test_login_success(client, db_session):
    create_staff_user(db_session)

    response = client.post(
        "/auth/login",
        data={
            "username": "librarian@test.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"


def test_login_rejects_invalid_password(client, db_session):
    create_staff_user(db_session)

    response = client.post(
        "/auth/login",
        data={
            "username": "librarian@test.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/auth/login",
        data={
            "username": "unknown@test.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_inactive_staff_cannot_login(client, db_session):
    create_staff_user(
        db_session,
        email="inactive@test.com",
        is_active=False,
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "inactive@test.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Staff account is inactive"


def test_books_endpoint_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/books/")
    assert response.status_code == 401


def test_database_health_endpoint_requires_authentication(client):
    response = client.get("/health/db")

    assert response.status_code == 401


def test_inactive_staff_token_is_rejected(unauthenticated_client, db_session):
    staff_user = create_staff_user(
        db_session,
        email="inactive-token@test.com",
        is_active=False,
    )

    token = create_access_token(
        subject=str(staff_user.id),
        role=staff_user.role,
    )

    unauthenticated_client.headers.update(
        {"Authorization": f"Bearer {token}"}
    )

    response = unauthenticated_client.get("/books/")
    assert response.status_code == 401