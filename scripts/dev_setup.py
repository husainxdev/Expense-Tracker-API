"""Prepare a private local PostgreSQL instance without committing credentials."""
import os
from pathlib import Path
import secrets
import subprocess
import time

from dotenv import dotenv_values
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
CONTAINER = "expense-tracker-postgres"
LABEL = "dev.expense-tracker.managed=true"
docker_env = {key: value for key, value in os.environ.items() if key not in {"DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"}}


def docker(*args, **kwargs):
    return subprocess.run(["docker", "--host=unix:///var/run/docker.sock", *args], env=docker_env, check=True, **kwargs)


def private_file(path, content):
    with open(path, "x", opener=lambda p, flags: os.open(p, flags, 0o600)) as file:
        file.write(content)


if not Path(".env").exists():
    password = secrets.token_urlsafe(32)
    private_file(".env", f"DATABASE_URL=postgresql+psycopg://expense:{password}@localhost:5432/expense_tracker\nJWT_SECRET_KEY={secrets.token_urlsafe(48)}\nACCESS_TOKEN_EXPIRE_MINUTES=30\n")

config = dotenv_values(".env")
url = make_url(config["DATABASE_URL"])
if url.host not in {"localhost", "127.0.0.1"} or url.database != "expense_tracker" or url.username != "expense" or url.port != 5432:
    raise SystemExit("Existing .env is not the managed local database. Leave it unchanged; configure your database separately.")
if not url.password or any(char in url.password for char in "\n\r"):
    raise SystemExit("A valid local database password is required")

docker("info", stdout=subprocess.DEVNULL)
existing = docker("ps", "-a", "--filter", f"name=^/{CONTAINER}$", "--format", "{{.Names}}", capture_output=True, text=True).stdout.strip()
if existing:
    label = docker("inspect", "--format", '{{index .Config.Labels "dev.expense-tracker.managed"}}', CONTAINER, capture_output=True, text=True).stdout.strip()
    if label != "true":
        raise SystemExit("Container name already used by an unmanaged container; refusing to change it")
    docker("start", CONTAINER, stdout=subprocess.DEVNULL)
else:
    # Write only a local ignored file; passwords never appear in subprocess arguments.
    env_path = Path(".env.postgres")
    if env_path.exists():
        env_path.unlink()
    private_file(env_path, f"POSTGRES_USER=expense\nPOSTGRES_PASSWORD={url.password}\nPOSTGRES_DB=expense_tracker\n")
    docker("run", "-d", "--name", CONTAINER, "--label", LABEL,
           "--env-file", str(env_path), "-p", "127.0.0.1:5432:5432",
           "-v", "expense-tracker-postgres-data:/var/lib/postgresql/data",
           "postgres:17-bookworm", stdout=subprocess.DEVNULL)

# Use an actual SQL connection, not only an open port, as the readiness check.
params = dict(host=url.host, port=url.port, user=url.username, password=url.password, dbname=url.database, connect_timeout=2)
for attempt in range(40):
    try:
        with psycopg.connect(**params, autocommit=True) as connection:
            connection.execute("SELECT 1")
            if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("expense_tracker_test",)).fetchone():
                connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier("expense_tracker_test")))
        break
    except psycopg.OperationalError:
        if attempt == 39:
            raise SystemExit("PostgreSQL did not become ready; inspect the managed container logs") from None
        time.sleep(1)

print("Local PostgreSQL is ready; .env contains private development configuration.")
print("Next: .venv/bin/alembic upgrade head")
