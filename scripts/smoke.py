"""Functional HTTP check; run against the local development server."""
import secrets
import uuid

import httpx

username = f"smoke_{uuid.uuid4().hex[:16]}"
password = secrets.token_urlsafe(24)
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=15, trust_env=False) as client:
    response = client.get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    response = client.post("/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password})
    assert response.status_code == 201, response.text
    assert "hashed_password" not in response.json()
    response = client.post("/auth/login", data={"username": username, "password": password})
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    payload = {"title": "HTTP smoke check", "amount": 10.50, "type": "expense", "category": "Test", "date": "2026-10-26"}
    response = client.post("/transactions", json=payload)
    assert response.status_code == 201, response.text
    created = response.json()
    path = f"/transactions/{created['id']}"
    try:
        assert client.get(path).json() == created
        assert client.get("/transactions").json() == [created]
        assert client.get("/transactions/filter?category=Test&minimum_amount=10&maximum_amount=11").json() == [created]
        response = client.put(path, json={**payload, "amount": 20})
        assert response.status_code == 200 and response.json()["amount"] == 20
    finally:
        assert client.delete(path).status_code == 200
    assert client.get(path).status_code == 404
print("HTTP smoke check passed: database health, registration, JWT login, CRUD, filtering, and deletion.")
