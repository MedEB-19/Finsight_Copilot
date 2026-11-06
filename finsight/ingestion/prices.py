"""Incremental, idempotent daily price loader with validation at the boundary."""
import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from sqlalchemy import text

from finsight.db.engine import get_engine
from finsight.db.helpers import merge_rows

log = logging.getLogger(__name__)
TYPES = {
    "company_id": "INT", "trade_date": "DATE",
    "open_price": "DECIMAL(18,4)", "high_price": "DECIMAL(18,4)",
    "low_price": "DECIMAL(18,4)", "close_price": "DECIMAL(18,4)",
    "adj_close": "DECIMAL(18,4)", "volume": "BIGINT",
}


def clean_history(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with NaN/non-positive prices (yfinance sometimes returns an all-NaN row)."""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if "Adj Close" not in df:
        df["Adj Close"] = df["Close"]
    df["Adj Close"] = df["Adj Close"].fillna(df["Close"])
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[(df[["Open", "High", "Low", "Close", "Adj Close"]] > 0).all(axis=1)]
    df["Volume"] = df["Volume"].fillna(0)
    return df


def _fetch(ticker: str, last: date | None) -> pd.DataFrame:
    t = yf.Ticker(ticker)
    if last is None:  # first run = full 5-year backfill
        df = t.history(period="5y", auto_adjust=False)
    else:  # incremental: only rows newer than what we already have
        start = last + timedelta(days=1)
        if start > date.today():
            return pd.DataFrame()
        df = t.history(start=start.isoformat(), auto_adjust=False)
    return clean_history(df)


def load_prices(tickers: list[str] | None = None) -> int:
    eng = get_engine()
    with eng.connect() as c:
        ids = {t: i for t, i in c.execute(text("SELECT ticker, company_id FROM companies")).all()}
    total = 0
    for tk in tickers or list(ids):
        if tk not in ids:
            log.warning("unknown ticker %s (run 'companies' first)", tk)
            continue
        try:  # per-ticker isolation: one bad record never stops the other 43
            with eng.connect() as c:
                last = c.execute(text("SELECT MAX(trade_date) FROM prices WHERE company_id=:i"),
                                 {"i": ids[tk]}).scalar()
            df = _fetch(tk, last)
            if df.empty:
                log.info("%s: up to date", tk)
                continue
            rows = [{
                "company_id": ids[tk], "trade_date": idx.date(),
                "open_price": round(float(r.Open), 4), "high_price": round(float(r.High), 4),
                "low_price": round(float(r.Low), 4), "close_price": round(float(r.Close), 4),
                "adj_close": round(float(r["Adj Close"]), 4), "volume": int(r.Volume),
            } for idx, r in df.iterrows()]
            with eng.begin() as c:
                total += merge_rows(c, "prices", rows, TYPES, ["company_id", "trade_date"])
            log.info("%s: %d rows", tk, len(rows))
        except Exception as e:
            log.error("%s failed: %s", tk, e)
    return total
