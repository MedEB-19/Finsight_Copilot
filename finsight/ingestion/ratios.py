"""Derived ratios computed from the stored tables. Missing inputs -> NULL, never invented."""
import logging

import pandas as pd
from sqlalchemy import text

from finsight.db.engine import get_engine
from finsight.db.helpers import merge_rows

log = logging.getLogger(__name__)
TYPES = {"company_id": "INT", "fiscal_year": "INT", "pe_ratio": "DECIMAL(18,4)",
         "profit_margin": "DECIMAL(18,4)", "roe": "DECIMAL(18,4)", "roa": "DECIMAL(18,4)",
         "debt_to_equity": "DECIMAL(18,4)"}


def _num(x):
    try:
        v = float(x)
        return None if pd.isna(v) else v
    except (TypeError, ValueError):
        return None


def _div(a, b, require_positive_den=False):
    if a is None or b is None or b == 0:
        return None
    if require_positive_den and b < 0:
        return None
    return round(a / b, 4)


def compute_ratios(f: dict, price: float | None) -> dict:
    ni, rev, ta, tl, debt, eps = (_num(f.get(k)) for k in
                                  ("net_income", "revenue", "total_assets", "total_liabilities", "total_debt", "eps"))
    equity = ta - tl if (ta is not None and tl is not None) else None  # equity = assets - liabilities
    return {
        "pe_ratio": _div(price, eps, True) if eps is not None and eps > 0 else None,
        "profit_margin": _div(ni, rev),
        "roe": _div(ni, equity, True),
        "roa": _div(ni, ta),
        "debt_to_equity": _div(debt, equity, True),
    }


def load_ratios() -> int:
    eng = get_engine()
    with eng.connect() as c:
        funds = pd.read_sql(text("SELECT * FROM fundamentals"), c)
    rows = []
    with eng.connect() as c:
        for f in funds.to_dict("records"):
            price = None
            if f["period_end"] is not None and not pd.isna(f["period_end"]):
                price = _num(c.execute(text(
                    "SELECT TOP 1 close_price FROM prices WHERE company_id=:c AND trade_date<=:d "
                    "ORDER BY trade_date DESC"), {"c": f["company_id"], "d": f["period_end"]}).scalar())
            rows.append({"company_id": f["company_id"], "fiscal_year": f["fiscal_year"],
                         **compute_ratios(f, price)})
    with eng.begin() as c:
        n = merge_rows(c, "ratios", rows, TYPES, ["company_id", "fiscal_year"])
    log.info("ratios upserted: %d", n)
    return n
