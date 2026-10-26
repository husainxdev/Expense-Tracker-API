import os
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

# Require a separate disposable PostgreSQL database. Never reuse DATABASE_URL.
test_url = os.environ.get("TEST_DATABASE_URL")
if not test_url:
    raise RuntimeError("Set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test")
if not (make_url(test_url).database or "").endswith("_test"):
    raise RuntimeError("Refusing tests: database name must end in _test")
os.environ["DATABASE_URL"] = test_url
os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(48))

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(test_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(db):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    def register_and_login(username="alice"):
        response = client.post("/auth/register", json={"username": username, "email": f"{username}@example.com", "password": "Test-password-123"})
        assert response.status_code == 201, response.text
        response = client.post("/auth/login", data={"username": username, "password": "Test-password-123"})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    return register_and_login


@pytest.fixture
def headers(auth):
    return auth()


@pytest.fixture
def payload():
    return {"title": "Lunch", "amount": 150.50, "type": "expense", "category": "Food", "date": "2026-10-26"}


@pytest.fixture
def transaction(client, headers, payload):
    response = client.post("/transactions", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()
