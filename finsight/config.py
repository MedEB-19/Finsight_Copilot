"""Central configuration. Credentials come from .env, never hard-coded."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
FILINGS_DIR = DATA_DIR / "filings"
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", DATA_DIR / "chroma"))
FILINGS_DIR.mkdir(parents=True, exist_ok=True)

# explicit 127.0.0.1 avoids IPv6 'localhost' resolution problems
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "1433"))
DB_NAME = os.getenv("DB_NAME", "finsight")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("MSSQL_SA_PASSWORD", "")
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "FinSightAI contact@example.com")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

EMBED_MODEL = "all-MiniLM-L6-v2"  # 384 dimensions
CHUNK_WORDS = 400
CHUNK_OVERLAP = 80
COLLECTION = "filings"

RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.04"))


def db_url(database: str | None = None) -> URL:
    """URL.create handles passwords with special characters safely."""
    return URL.create(
        "mssql+pyodbc",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=database or DB_NAME,
        query={"driver": ODBC_DRIVER, "TrustServerCertificate": "yes"},
    )
