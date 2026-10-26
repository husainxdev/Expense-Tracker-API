from sqlalchemy import select

from app.models import Transaction, User


def test_get_transactions(client, headers, transaction, auth, payload):
    response = client.get("/transactions", headers=headers)
    assert response.status_code == 200
    assert response.json() == [transaction]

    filtered = client.get("/transactions/filter?type=expense&category=Food&minimum_amount=100&maximum_amount=5000", headers=headers)
    assert filtered.status_code == 200
    assert filtered.json() == [transaction]
    assert client.get("/transactions/filter?minimum_amount=5000", headers=headers).json() == []

    bob = auth("bob")
    assert client.get("/transactions", headers=bob).json() == []
    assert client.get("/transactions/filter?category=Food", headers=bob).json() == []
    assert client.get("/transactions").status_code == 401


def test_get_specific_transaction(client, headers, transaction, auth):
    path = f"/transactions/{transaction['id']}"
    response = client.get(path, headers=headers)
    assert response.status_code == 200
    assert response.json() == transaction
    assert client.get(path, headers=auth("bob")).status_code == 404
    assert client.get("/transactions/99999999", headers=headers).status_code == 404


def test_create_transaction(client, headers, payload, db):
    # Any positive float is allowed, including values smaller than one cent.
    payload = {**payload, "amount": 0.001}
    response = client.post("/transactions", headers=headers, json=payload)
    assert response.status_code == 201
    result = response.json()
    assert all(result[key] == value for key, value in payload.items())
    row = db.get(Transaction, result["id"])
    assert row.owner.username == "alice"
    assert row.amount == payload["amount"]
    user = db.scalar(select(User).where(User.username == "alice"))
    assert user.hashed_password != "Test-password-123"
    assert client.post("/transactions", headers=headers, json={**payload, "amount": 0}).status_code == 422
    assert client.post("/transactions", headers=headers, json={**payload, "type": "transfer"}).status_code == 422


def test_update_transaction(client, headers, transaction, payload, db, auth):
    path = f"/transactions/{transaction['id']}"
    updated = {**payload, "title": "Salary", "amount": 5000, "type": "income", "category": "Work"}
    assert client.put(path, headers=auth("bob"), json=updated).status_code == 404
    response = client.put(path, headers=headers, json=updated)
    assert response.status_code == 200
    assert all(response.json()[key] == value for key, value in updated.items())
    db.expire_all()
    assert db.get(Transaction, transaction["id"]).title == "Salary"
    assert client.put("/transactions/99999999", headers=headers, json=updated).status_code == 404


def test_delete_transaction(client, headers, transaction, db, auth):
    path = f"/transactions/{transaction['id']}"
    assert client.delete(path, headers=auth("bob")).status_code == 404
    response = client.delete(path, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Transaction deleted successfully"}
    assert client.get(path, headers=headers).status_code == 404
    assert db.get(Transaction, transaction["id"]) is None
    assert client.delete(path, headers=headers).status_code == 404
