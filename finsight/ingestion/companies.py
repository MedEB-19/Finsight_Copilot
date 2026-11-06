"""Load the company reference table (idempotent)."""
import logging

import yfinance as yf

from finsight.db.engine import get_engine
from finsight.db.helpers import merge_rows
from finsight.ingestion.universe import TICKER_SECTOR

log = logging.getLogger(__name__)
TYPES = {"ticker": "NVARCHAR(10)", "name": "NVARCHAR(200)", "sector": "NVARCHAR(60)", "industry": "NVARCHAR(120)"}


def load_companies() -> int:
    rows = []
    for tk, sector in TICKER_SECTOR.items():
        name, industry = tk, None
        try:
            info = yf.Ticker(tk).info or {}
            name = info.get("longName") or info.get("shortName") or tk
            industry = info.get("industry")
        except Exception as e:  # network hiccup must not stop the load
            log.warning("info failed for %s: %s", tk, e)
        rows.append({"ticker": tk, "name": name, "sector": sector, "industry": industry})
    with get_engine().begin() as c:
        n = merge_rows(c, "companies", rows, TYPES, ["ticker"])
    log.info("companies upserted: %d", n)
    return n
