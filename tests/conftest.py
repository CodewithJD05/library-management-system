
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.staff_user import StaffUser


TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def unauthenticated_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.headers.pop("Authorization", None)
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def client(unauthenticated_client):
    return unauthenticated_client


@pytest.fixture()
def authenticated_client(unauthenticated_client, db_session):
    staff_user = StaffUser(
        full_name="Test Librarian",
        email="librarian@test.com",
        password_hash=hash_password("TestPassword123!"),
        role="librarian",
        is_active=True,
    )

    db_session.add(staff_user)
    db_session.commit()
    db_session.refresh(staff_user)

    token = create_access_token(
        subject=str(staff_user.id),
        role=staff_user.role,
    )

    unauthenticated_client.headers.update(
        {"Authorization": f"Bearer {token}"}
    )

    return unauthenticated_client
