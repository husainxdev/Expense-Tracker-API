from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import Transaction, User
from app.security import password_hash


def test_get_transactions(client, headers, transaction):
    response = client.get("/transactions", headers=headers)
    assert response.status_code == 200
    assert response.json() == [transaction]


def test_get_specific_transaction(client, headers, transaction):
    response = client.get(f"/transactions/{transaction['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json() == transaction


def test_create_transaction(client, headers, payload, db):
    response = client.post("/transactions", headers=headers, json=payload)
    assert response.status_code == 201
    result = response.json()
    assert all(result[key] == value for key, value in payload.items())
    row = db.get(Transaction, result["id"])
    assert row.owner.username == "alice"
    assert float(row.amount) == payload["amount"]


def test_update_transaction(client, headers, transaction, payload, db):
    updated = {**payload, "title": "Salary", "amount": 5000, "type": "income", "category": "Work"}
    response = client.put(f"/transactions/{transaction['id']}", headers=headers, json=updated)
    assert response.status_code == 200
    assert all(response.json()[key] == value for key, value in updated.items())
    db.expire_all()
    assert db.get(Transaction, transaction["id"]).title == "Salary"


def test_delete_transaction(client, headers, transaction, db):
    url = f"/transactions/{transaction['id']}"
    response = client.delete(url, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Transaction deleted successfully"}
    assert client.get(url, headers=headers).status_code == 404
    assert db.get(Transaction, transaction["id"]) is None


def test_registration_hashes_password(client, db):
    response = client.post("/auth/register", json={"username": "new_user", "email": "new@example.com", "password": "Test-password-123"})
    assert response.status_code == 201
    assert set(response.json()) == {"id", "username", "email"}
    user = db.scalar(select(User).where(User.username == "new_user"))
    assert user.hashed_password != "Test-password-123"
    assert password_hash.verify("Test-password-123", user.hashed_password)


def test_duplicate_username(client, headers):
    response = client.post("/auth/register", json={"username": "alice", "email": "other@example.com", "password": "Test-password-123"})
    assert response.status_code == 409
    # The failed transaction must have been rolled back.
    assert client.get("/transactions", headers=headers).status_code == 200


@pytest.mark.parametrize("username,password", [("alice", "wrong"), ("nobody", "wrong")])
def test_bad_login(client, headers, username, password):
    assert client.post("/auth/login", data={"username": username, "password": password}).status_code == 401


def test_login_returns_jwt(client, headers):
    token = headers["Authorization"].split()[1]
    claims = jwt.decode(token, get_settings().jwt_secret_key, algorithms=["HS256"])
    assert claims["exp"] > claims["iat"]
    assert int(claims["sub"]) > 0


@pytest.mark.parametrize("method,path", [("get", "/transactions"), ("get", "/transactions/filter"), ("get", "/transactions/1"), ("post", "/transactions"), ("put", "/transactions/1"), ("delete", "/transactions/1")])
def test_authentication_required(client, payload, method, path):
    kwargs = {"json": payload} if method in ("post", "put") else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_other_user_cannot_access_transaction(client, auth, transaction, payload, method):
    bob = auth("bob")
    kwargs = {"json": payload} if method == "put" else {}
    assert getattr(client, method)(f"/transactions/{transaction['id']}", headers=bob, **kwargs).status_code == 404
    assert client.get("/transactions", headers=bob).json() == []
    assert client.get("/transactions/filter?category=Food", headers=bob).json() == []


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_transaction(client, headers, payload, method):
    kwargs = {"json": payload} if method == "put" else {}
    response = getattr(client, method)("/transactions/99999999", headers=headers, **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


@pytest.mark.parametrize("patch", [{"amount": 0}, {"amount": -1}, {"amount": 0.001}, {"type": "transfer"}, {"date": "invalid"}, {"title": " "}, {"category": ""}, {"owner_id": 42}])
def test_transaction_validation(client, headers, payload, patch):
    assert client.post("/transactions", headers=headers, json={**payload, **patch}).status_code == 422


def test_update_validation(client, headers, transaction, payload):
    assert client.put(f"/transactions/{transaction['id']}", headers=headers, json={**payload, "amount": -2}).status_code == 422
    assert client.get(f"/transactions/{transaction['id']}", headers=headers).json() == transaction


def test_filter_transactions(client, headers, transaction, payload):
    response = client.post("/transactions", headers=headers, json={**payload, "type": "income", "category": "Work", "amount": 5000})
    assert response.status_code == 201
    response = client.get("/transactions/filter?type=expense&category=Food&minimum_amount=100&maximum_amount=200", headers=headers)
    assert response.status_code == 200
    assert response.json() == [transaction]
    assert client.get("/transactions/filter?minimum_amount=6000", headers=headers).json() == []
    assert len(client.get("/transactions/filter", headers=headers).json()) == 2
    assert len(client.get("/transactions/filter?minimum_amount=150.5&maximum_amount=150.5", headers=headers).json()) == 1


@pytest.mark.parametrize("query", ["minimum_amount=10&maximum_amount=1", "minimum_amount=-1", "type=invalid", "maximum_amount=nan", "maximum_amount=inf"])
def test_invalid_filter(client, headers, query):
    assert client.get(f"/transactions/filter?{query}", headers=headers).status_code == 422


@pytest.mark.parametrize("kind", ["expired", "tampered", "missing_claims", "non_numeric_subject", "deleted_user"])
def test_invalid_token(client, headers, kind):
    key = get_settings().jwt_secret_key
    now = datetime.now(timezone.utc)
    claims = {"sub": "99999999", "iat": now, "exp": now + timedelta(minutes=5)}
    if kind == "expired":
        claims["exp"] = now - timedelta(seconds=5)
    if kind == "missing_claims":
        del claims["exp"]
    if kind == "non_numeric_subject":
        claims["sub"] = "invalid"
    token = jwt.encode(claims, "wrong-signing-key" if kind == "tampered" else key, algorithm="HS256")
    response = client.get("/transactions", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_registration_validation(client):
    assert client.post("/auth/register", json={"username": "a", "email": "not-email", "password": "123"}).status_code == 422


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
