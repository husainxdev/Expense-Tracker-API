# Personal Expense Tracker API

A FastAPI + PostgreSQL application for the PHITRON Module 16 midterm. Users register, log in with JWT authentication, and manage only their own income and expense transactions.

## Features

- Argon2 password hashing; password hashes never appear in API responses.
- Expiring, signed JWT bearer tokens and Swagger's **Authorize** login flow.
- SQLAlchemy user-to-transaction relationship and persistent PostgreSQL storage.
- Owner-scoped CRUD and filtering; inaccessible and missing records both return 404.
- Pydantic validation, database constraints, and Alembic schema migrations.
- PostgreSQL-backed pytest suite, GitHub Actions, and a Render Blueprint.

Money is stored as PostgreSQL `NUMERIC(14, 2)` for exact cents and exposed as a JSON number. Amounts must be positive, have at most two decimal places, and not exceed 999999999999.99. Usernames are case-sensitive and accept letters, digits, and underscores. Dates use `YYYY-MM-DD`. PUT replaces all editable fields; clients cannot set `owner_id`.

## Run locally

Requirements: Python 3.12 and a running Docker daemon (or your own PostgreSQL instance).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/dev_setup.py
alembic upgrade head
uvicorn app.main:app --reload
```

`dev_setup.py` generates an ignored `.env` with random local credentials, starts a dedicated PostgreSQL 17 container bound to loopback, and creates a separate test database. Rerunning it reuses the container and database. It preserves an existing `.env` and refuses to reconfigure a nonlocal database. Database data lives in the `expense-tracker-postgres-data` Docker volume.

Alternatively, copy `.env.example` to `.env`, configure your own PostgreSQL `DATABASE_URL`, generate a random `JWT_SECRET_KEY` with the command in the example, and run the migration and server commands above. `postgres://` and `postgresql://` URLs from hosting providers are automatically normalized to the psycopg driver. Keep any provider-required TLS query parameters such as `sslmode=require`.

Interactive API documentation is at `/docs`; the OpenAPI schema is at `/openapi.json`. `GET /health` checks database connectivity and returns 503 if the database is unavailable.

## API

| Method | Endpoint | Authentication | Result |
| --- | --- | --- | --- |
| POST | `/auth/register` | Public | 201: user ID, username, email |
| POST | `/auth/login` | Public | 200: access token and bearer token type |
| POST | `/transactions` | Bearer JWT | 201: created transaction |
| GET | `/transactions` | Bearer JWT | 200: your transactions |
| GET | `/transactions/filter` | Bearer JWT | 200: your matching transactions |
| GET | `/transactions/{id}` | Bearer JWT | 200: your transaction, or 404 |
| PUT | `/transactions/{id}` | Bearer JWT | 200: updated transaction, or 404 |
| DELETE | `/transactions/{id}` | Bearer JWT | 200: confirmation message, or 404 |

Registration accepts JSON:

```json
{"username": "alice", "email": "alice@example.com", "password": "a-long-personal-password"}
```

Login uses **form data**, not JSON, for compatibility with OAuth2 and Swagger:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=alice' \
  --data-urlencode 'password=a-long-personal-password'
```

Use the returned token as `Authorization: Bearer <access_token>`. Create and update accept this JSON body:

```json
{
  "title": "Lunch",
  "amount": 150.50,
  "type": "expense",
  "category": "Food",
  "date": "2026-10-26"
}
```

Filtering supports any combination of `type`, `category`, `minimum_amount`, and `maximum_amount`. Categories match exactly; amount bounds are inclusive. For example: `/transactions/filter?type=expense&category=Food&minimum_amount=100&maximum_amount=5000`. Reversed bounds and invalid types return 422. Duplicate usernames return 409; failed login and missing/invalid/expired tokens return 401.

## Tests

With the local setup above:

```bash
python scripts/test.py -q
```

For another test PostgreSQL instance, set `TEST_DATABASE_URL` securely and run `pytest -q`. The database name **must end in `_test`**. Tests run migrations there and roll back each test's changes. Never point this variable at a production database. Tests cover all five required CRUD cases plus registration, hashing, login, ownership on read/update/delete/filter, validation, invalid JWTs, missing records, and database health. GitHub Actions provisions its own PostgreSQL service.

To exercise a running server over HTTP:

```bash
python scripts/smoke.py
```

This creates a uniquely named smoke-test user, exercises CRUD and filtering, and deletes its transaction. The local smoke-test user remains in the database.

## Deploy to Render with online PostgreSQL

The repository includes `render.yaml` to create both a web service and a managed online PostgreSQL database. No database credentials or signing keys are committed.

1. Push the project to your GitHub repository.
2. In Render, select **New → Blueprint**, connect the repository, and review the proposed resources and current pricing/limits before creating them.
3. Apply the Blueprint. Render injects the database connection string and generates the JWT signing key. The start command runs `alembic upgrade head`, then starts Uvicorn on Render's `$PORT`.
4. Verify `/health`, open `/docs`, register an account, authorize, and create/list a transaction on the deployed service.

The Blueprint requests free plans where available. Free services can sleep and free PostgreSQL databases can expire; check Render's current terms and choose a paid database if you need ongoing storage. For a paid web service or multiple replicas, move migrations to a single `preDeployCommand: alembic upgrade head` and use only Uvicorn in `startCommand`.

Environment variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Required PostgreSQL connection string |
| `JWT_SECRET_KEY` | Required random signing secret, at least 32 characters |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime, defaults to 30 |
| `TEST_DATABASE_URL` | Separate test database; tests only |

## Structure

```text
app/
  main.py              FastAPI entry point and health endpoint
  config.py            Environment validation
  database.py          Engine and database sessions
  models.py            SQLAlchemy tables and relationships
  schemas.py           Request and response validation
  security.py          Password hashing, JWTs, current user
  routers/
    auth.py            Register and login
    transactions.py    Owner-scoped CRUD and filtering
migrations/            Alembic schema migrations
scripts/               Local PostgreSQL setup, test runner, HTTP smoke check
tests/                 PostgreSQL-backed API tests
render.yaml            Web service and online PostgreSQL deployment
```
