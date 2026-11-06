"""Reshape yfinance wide statements (dates as columns) into one row per fiscal year."""
import logging

import pandas as pd
import yfinance as yf
from sqlalchemy import text

from finsight.db.engine import get_engine
from finsight.db.helpers import merge_rows, to_none

log = logging.getLogger(__name__)

INCOME = {
    "revenue": ["Total Revenue", "Operating Revenue"],
    "net_income": ["Net Income", "Net Income Common Stockholders"],
    "ebitda": ["EBITDA", "Normalized EBITDA"],
    "eps": ["Diluted EPS", "Basic EPS"],
}
BALANCE = {
    "total_assets": ["Total Assets"],
    "total_liabilities": ["Total Liabilities Net Minority Interest"],
    "total_debt": ["Total Debt"],
    "cash": ["Cash And Cash Equivalents"],
    "shares_outstanding": ["Ordinary Shares Number", "Share Issued"],
}
FIELDS = list(INCOME) + list(BALANCE)
TYPES = {
    "company_id": "INT", "fiscal_year": "INT", "period_end": "DATE",
    "revenue": "DECIMAL(24,2)", "net_income": "DECIMAL(24,2)", "ebitda": "DECIMAL(24,2)",
    "total_assets": "DECIMAL(24,2)", "total_liabilities": "DECIMAL(24,2)",
    "total_debt": "DECIMAL(24,2)", "cash": "DECIMAL(24,2)",
    "eps": "DECIMAL(18,4)", "shares_outstanding": "DECIMAL(24,0)",
}


def safe_get(df: pd.DataFrame | None, col, names: list[str]):
    """Safe accessor: NULL (None) for any missing line item instead of crashing."""
    if df is None or df.empty or col not in df.columns:
        return None
    for n in names:
        if n in df.index:
            v = df.loc[n, col]
            if isinstance(v, pd.Series):
                v = v.iloc[0]
            v = to_none(v)
            if v is not None:
                return v
    return None


def build_rows(company_id: int, income: pd.DataFrame | None, balance: pd.DataFrame | None) -> list[dict]:
    cols = set()
    for d in (income, balance):
        if d is not None and not d.empty:
            cols |= set(d.columns)
    rows = []
    for col in sorted(cols):
        rec = {f: safe_get(income, col, INCOME[f]) for f in INCOME}
        rec.update({f: safe_get(balance, col, BALANCE[f]) for f in BALANCE})
        # keep the row if at least ONE field has a real value (no blunt dropna:
        # that would discard legitimate partial data). Fully empty placeholder years are skipped.
        if all(rec[f] is None for f in FIELDS):
            continue
        ts = pd.Timestamp(col)
        rec.update({"company_id": company_id, "fiscal_year": int(ts.year), "period_end": ts.date()})
        rows.append(rec)
    return rows


def load_fundamentals(tickers: list[str] | None = None) -> int:
    eng = get_engine()
    with eng.connect() as c:
        ids = {t: i for t, i in c.execute(text("SELECT ticker, company_id FROM companies")).all()}
    total = 0
    for tk in tickers or list(ids):
        try:
            t = yf.Ticker(tk)
            rows = build_rows(ids[tk], t.income_stmt, t.balance_sheet)
            with eng.begin() as c:
                total += merge_rows(c, "fundamentals", rows, TYPES, ["company_id", "fiscal_year"])
            log.info("%s: %d fiscal years", tk, len(rows))
        except Exception as e:
            log.error("%s failed: %s", tk, e)
    return total
