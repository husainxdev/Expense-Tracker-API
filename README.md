# Expense Tracker API

PHITRON Module 16 Mid Term: a personal expense tracker built with FastAPI, SQLAlchemy, PostgreSQL, JWT authentication, and Pydantic.

## Setup

Use Python 3.12 and a PostgreSQL database.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `DATABASE_URL` in `.env` to your PostgreSQL connection string. For the assignment, use an online PostgreSQL instance, such as Render PostgreSQL. Preserve TLS settings required by your provider.

Generate `JWT_SECRET_KEY` with the following command and place it in `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Start the API:

```bash
uvicorn app.main:app --reload
```

SQLAlchemy creates the user and transaction tables on startup. API documentation is available at `/docs`.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Log in and receive a JWT token |
| POST | `/transactions` | Create your transaction |
| GET | `/transactions` | List your transactions |
| GET | `/transactions/filter` | Filter your transactions |
| GET | `/transactions/{transaction_id}` | Get your transaction |
| PUT | `/transactions/{transaction_id}` | Update your transaction |
| DELETE | `/transactions/{transaction_id}` | Delete your transaction |

Register with JSON:

```json
{"username": "alice", "email": "alice@example.com", "password": "my-password"}
```

Login accepts form fields `username` and `password`. Use the returned access token in `Authorization: Bearer <access_token>`, or log in using the **Authorize** button in `/docs`.

Create and update accept JSON:

```json
{
  "title": "Lunch",
  "amount": 150.5,
  "type": "expense",
  "category": "Food",
  "date": "2026-10-26"
}
```

`amount` must be positive and `type` must be `income` or `expense`. The API automatically assigns the logged-in user as owner. Another user's transaction and a missing transaction both return 404.

Filtering supports `type`, `category`, `minimum_amount`, and `maximum_amount`, individually or together:

```text
/transactions/filter?type=expense&category=Food&minimum_amount=100&maximum_amount=5000
```

## Pytest

Create a separate PostgreSQL database with a name ending in `_test`, and set `TEST_DATABASE_URL` to its connection string. Then run:

```bash
pytest -q
```

The five tests cover listing, getting a specific transaction, creating, updating, and deleting. They also check ownership, filtering, validation, and missing records within those cases. Test changes are rolled back.

## Render deployment

1. Push the project to GitHub.
2. In Render, select **New → Blueprint** and connect this repository.
3. Review and apply `render.yaml`. It configures a Python web service and online PostgreSQL, injects `DATABASE_URL`, and generates `JWT_SECRET_KEY`.
4. Open the deployed service's `/docs` and test registration, login, and transactions.

The build command is `pip install -r requirements.txt`. The start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

Check current Render pricing and free database expiration limits before provisioning. Live deployment requires access to your Render account.
