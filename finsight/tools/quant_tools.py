"""Deterministic quantitative analysis: the LLM never guesses a number it can calculate."""
import numpy as np
import pandas as pd
from sqlalchemy import text

from finsight.config import RISK_FREE_RATE
from finsight.db.engine import get_engine
from finsight.tools.sql_tool import PERIOD_DAYS

TRADING_DAYS = 252


# ---------- pure functions (unit-tested, no DB) ----------
def daily_returns(prices: pd.Series) -> pd.Series:
    return prices.astype(float).pct_change().dropna()


def annualized_volatility(r: pd.Series) -> float:
    return float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))


def annualized_return(r: pd.Series) -> float:
    return float((1 + r).prod() ** (TRADING_DAYS / max(len(r), 1)) - 1)


def sharpe_ratio(r: pd.Series, rf: float = RISK_FREE_RATE) -> float | None:
    vol = annualized_volatility(r)
    return None if vol == 0 or np.isnan(vol) else float((annualized_return(r) - rf) / vol)


def max_drawdown(prices: pd.Series) -> dict:
    p = prices.astype(float)
    dd = p / p.cummax() - 1
    trough = dd.idxmin()
    peak = p.loc[:trough].idxmax()
    return {"max_drawdown_pct": round(float(dd.min()) * 100, 2), "peak_date": str(peak)[:10],
            "trough_date": str(trough)[:10]}


def beta(r_asset: pd.Series, r_bench: pd.Series) -> float | None:
    df = pd.concat([r_asset, r_bench], axis=1, join="inner").dropna()
    if len(df) < 30 or df.iloc[:, 1].var() == 0:
        return None
    return float(df.iloc[:, 0].cov(df.iloc[:, 1]) / df.iloc[:, 1].var())


def portfolio_stats(prices: pd.DataFrame, weights: dict[str, float], rf: float = RISK_FREE_RATE) -> dict:
    w = pd.Series(weights, dtype=float)
    w = w / w.sum()  # normalise
    rets = prices[w.index].astype(float).pct_change().dropna()
    port = rets.mul(w, axis=1).sum(axis=1)  # daily-rebalanced
    value = (1 + port).cumprod()
    return {
        "weights": {k: round(float(v), 4) for k, v in w.items()},
        "annualized_return_pct": round(annualized_return(port) * 100, 2),
        "annualized_volatility_pct": round(annualized_volatility(port) * 100, 2),
        "sharpe_ratio": None if sharpe_ratio(port, rf) is None else round(sharpe_ratio(port, rf), 3),
        **max_drawdown(value),
        "correlation_matrix": rets.corr().round(3).to_dict(),
    }


# ---------- DB-backed wrappers ----------
def _start(end, period):
    from datetime import date
    return date(end.year, 1, 1) if period == "ytd" else end - pd.Timedelta(days=PERIOD_DAYS.get(period, 365))


def load_prices_wide(tickers: list[str] | None, period: str) -> pd.DataFrame:
    """Adjusted closes, dates x tickers. tickers=None -> whole universe."""
    with get_engine().connect() as c:
        end = c.execute(text("SELECT MAX(trade_date) FROM prices")).scalar()
        if end is None:
            return pd.DataFrame()
        df = pd.read_sql(text(
            "SELECT p.trade_date, co.ticker, p.adj_close FROM prices p JOIN companies co ON co.company_id=p.company_id "
            "WHERE p.trade_date>=:s"), c, params={"s": _start(end, period.lower())})
    df["adj_close"] = df["adj_close"].astype(float)
    wide = df.pivot(index="trade_date", columns="ticker", values="adj_close").sort_index()
    if tickers:
        wide = wide[[t for t in tickers if t in wide.columns]]
    return wide


def risk_metrics(ticker: str, period: str = "1y") -> dict:
    """Annualized volatility, Sharpe, max drawdown and beta (vs equal-weighted 44-company universe)."""
    ticker = ticker.strip().upper()
    wide = load_prices_wide(None, period)
    if ticker not in wide.columns:
        return {"error": f"No price data for {ticker}"}
    r = daily_returns(wide[ticker].dropna())
    bench = wide.pct_change().dropna(how="all").mean(axis=1)
    b = beta(r, bench)
    return {
        "ticker": ticker, "period": period, "observations": int(len(r)),
        "annualized_return_pct": round(annualized_return(r) * 100, 2),
        "annualized_volatility_pct": round(annualized_volatility(r) * 100, 2),
        "sharpe_ratio": None if sharpe_ratio(r) is None else round(sharpe_ratio(r), 3),
        "risk_free_rate": RISK_FREE_RATE,
        **max_drawdown(wide[ticker].dropna()),
        "beta": None if b is None else round(b, 3),
        "beta_benchmark": "equal-weighted average of the 44 universe stocks (proxy for the market)",
    }


def portfolio_analysis(weights: dict[str, float], period: str = "1y") -> dict:
    """Return, volatility, Sharpe, drawdown and correlations of a weighted portfolio."""
    tickers = [t.strip().upper() for t in weights]
    wide = load_prices_wide(tickers, period).dropna()
    missing = [t for t in tickers if t not in wide.columns]
    if missing or wide.empty:
        return {"error": f"No price data for {missing or tickers}"}
    clean = {t.strip().upper(): float(v) for t, v in weights.items()}
    return {"period": period, **portfolio_stats(wide, clean)}
