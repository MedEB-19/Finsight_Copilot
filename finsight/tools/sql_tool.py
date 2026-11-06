"""Station 4: SQL tool. Five reviewed, parameterized functions. The agent never writes SQL."""
from datetime import date, timedelta

from sqlalchemy import text

from finsight.db.engine import get_engine

PERIOD_DAYS = {"1m": 30, "3m": 91, "6m": 182, "1y": 365, "3y": 1095, "5y": 1826}


def _f(x):
    return None if x is None else float(x)


def _company(c, ticker: str):
    return c.execute(text("SELECT company_id, ticker, name, sector, industry FROM companies WHERE ticker=:t"),
                     {"t": ticker.strip().upper()}).mappings().first()


def _perf(c, company_id: int, period: str) -> dict | None:
    end = c.execute(text("SELECT MAX(trade_date) FROM prices WHERE company_id=:i"), {"i": company_id}).scalar()
    if end is None:
        return None
    start = date(end.year, 1, 1) if period == "ytd" else end - timedelta(days=PERIOD_DAYS.get(period, 365))
    rows = c.execute(text(
        "SELECT trade_date, close_price, adj_close FROM prices "
        "WHERE company_id=:i AND trade_date>=:s ORDER BY trade_date"), {"i": company_id, "s": start}).mappings().all()
    if len(rows) < 2:
        return None
    first, last = rows[0], rows[-1]
    closes = [float(r["close_price"]) for r in rows]
    return {
        "period": period, "start_date": str(first["trade_date"]), "end_date": str(last["trade_date"]),
        "start_close": _f(first["close_price"]), "end_close": _f(last["close_price"]),
        "price_return_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
        "total_return_pct": round((float(last["adj_close"]) / float(first["adj_close"]) - 1) * 100, 2),
        "period_high": max(closes), "period_low": min(closes),
    }


def get_company_overview(ticker: str) -> dict:
    """Company reference data + latest price + latest fundamentals and ratios."""
    with get_engine().connect() as c:
        co = _company(c, ticker)
        if not co:
            return {"error": f"Ticker {ticker} not in the 44-company universe"}
        px = c.execute(text("SELECT TOP 1 trade_date, close_price FROM prices WHERE company_id=:i "
                            "ORDER BY trade_date DESC"), {"i": co["company_id"]}).mappings().first()
        fin = c.execute(text(
            "SELECT TOP 1 f.fiscal_year, f.revenue, f.net_income, r.pe_ratio, r.profit_margin, r.roe "
            "FROM fundamentals f LEFT JOIN ratios r ON r.company_id=f.company_id AND r.fiscal_year=f.fiscal_year "
            "WHERE f.company_id=:i ORDER BY f.fiscal_year DESC"), {"i": co["company_id"]}).mappings().first()
    return {
        "ticker": co["ticker"], "name": co["name"], "sector": co["sector"], "industry": co["industry"],
        "latest_price": {"date": str(px["trade_date"]), "close": _f(px["close_price"])} if px else None,
        "latest_fiscal": {k: (_f(v) if k != "fiscal_year" else v) for k, v in dict(fin).items()} if fin else None,
    }


def get_financials(ticker: str, years: int = 4) -> dict:
    """Fiscal-year revenue, net income, EBITDA, balance sheet items, EPS and ratios (NULL = not available)."""
    years = max(1, min(int(years), 4))
    with get_engine().connect() as c:
        co = _company(c, ticker)
        if not co:
            return {"error": f"Ticker {ticker} not in the 44-company universe"}
        rows = c.execute(text(
            "SELECT TOP (:n) f.fiscal_year, f.revenue, f.net_income, f.ebitda, f.total_assets, f.total_liabilities, "
            "f.total_debt, f.cash, f.eps, r.pe_ratio, r.profit_margin, r.roe, r.roa, r.debt_to_equity "
            "FROM fundamentals f LEFT JOIN ratios r ON r.company_id=f.company_id AND r.fiscal_year=f.fiscal_year "
            "WHERE f.company_id=:i ORDER BY f.fiscal_year DESC"), {"n": years, "i": co["company_id"]}).mappings().all()
    out = []
    for i, r in enumerate(rows):
        d = {k: (v if k == "fiscal_year" else _f(v)) for k, v in dict(r).items()}
        if i + 1 < len(rows) and d["revenue"] and rows[i + 1]["revenue"]:
            d["revenue_growth_pct"] = round((d["revenue"] / float(rows[i + 1]["revenue"]) - 1) * 100, 2)
        out.append(d)
    return {"ticker": co["ticker"], "name": co["name"], "fiscal_years": out}


def get_price_performance(ticker: str, period: str = "1y") -> dict:
    """Price/total return, high and low over 1m, 3m, 6m, ytd, 1y, 3y or 5y."""
    period = period.lower()
    if period != "ytd" and period not in PERIOD_DAYS:
        return {"error": f"period must be one of {list(PERIOD_DAYS) + ['ytd']}"}
    with get_engine().connect() as c:
        co = _company(c, ticker)
        if not co:
            return {"error": f"Ticker {ticker} not in the 44-company universe"}
        perf = _perf(c, co["company_id"], period)
    return {"ticker": co["ticker"], **(perf or {"error": "not enough price data"})}


def compare_companies(tickers: list[str], period: str = "1y") -> dict:
    """Side-by-side: sector, latest fiscal revenue/net income/ratios and price return."""
    out = []
    for tk in tickers[:6]:
        ov = get_company_overview(tk)
        if "error" in ov:
            out.append(ov)
            continue
        perf = get_price_performance(tk, period)
        out.append({**ov, "performance": perf})
    return {"period": period, "companies": out}


def get_sector_companies(sector: str) -> dict:
    """List companies in a GICS sector (case-insensitive partial match)."""
    with get_engine().connect() as c:
        rows = c.execute(text("SELECT ticker, name, sector FROM companies WHERE sector LIKE :s ORDER BY ticker"),
                         {"s": f"%{sector.strip()}%"}).mappings().all()
        sectors = [r[0] for r in c.execute(text("SELECT DISTINCT sector FROM companies ORDER BY sector"))]
    if not rows:
        return {"error": f"No sector matches '{sector}'", "available_sectors": sectors}
    return {"companies": [dict(r) for r in rows]}
