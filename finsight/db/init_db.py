"""Create the database (if missing) and apply schema.sql. Safe to re-run."""
import re
import time
from pathlib import Path

from sqlalchemy import create_engine, text

from finsight.config import DB_NAME, db_url
from finsight.db.engine import get_engine


def init_db(retries: int = 30) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_]+", DB_NAME):
        raise ValueError("DB_NAME must be alphanumeric/underscore")
    master = create_engine(db_url("master"), isolation_level="AUTOCOMMIT")
    for attempt in range(retries):  # SQL Server in Docker needs ~20s to boot
        try:
            with master.connect() as c:
                c.execute(text(f"IF DB_ID('{DB_NAME}') IS NULL CREATE DATABASE [{DB_NAME}]"))
            break
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"Waiting for SQL Server... ({e.__class__.__name__})")
            time.sleep(2)
    ddl = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with get_engine().begin() as c:
        for stmt in re.split(r"^\s*GO\s*$", ddl, flags=re.M):
            if stmt.strip():
                c.execute(text(stmt))
    print(f"Database '{DB_NAME}' ready.")
