"""Run tests against the separate local database; do not print credentials."""
import os
from pathlib import Path
import subprocess
import sys

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

os.chdir(Path(__file__).resolve().parents[1])
config = dotenv_values(".env")
if not os.environ.get("TEST_DATABASE_URL"):
    url = make_url(config["DATABASE_URL"])
    if url.host not in {"localhost", "127.0.0.1"} or url.database != "expense_tracker":
        raise SystemExit("Set TEST_DATABASE_URL to a separate PostgreSQL test database ending in _test")
    os.environ["TEST_DATABASE_URL"] = url.set(database="expense_tracker_test").render_as_string(hide_password=False)
if not os.environ.get("JWT_SECRET_KEY") and config.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = config["JWT_SECRET_KEY"]
raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", *sys.argv[1:]]))
