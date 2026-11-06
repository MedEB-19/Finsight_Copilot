"""LangChain tool wrappers. Descriptions are deliberately explicit: small local models need them."""
import json

from langchain_core.tools import tool

from finsight.tools import quant_tools, rag_tool, sql_tool


def _j(obj) -> str:
    return json.dumps(obj, default=str)


@tool
def company_overview(ticker: str) -> str:
    """Get name, sector, latest price and latest fiscal-year revenue/net income/ratios for ONE ticker (e.g. 'AAPL')."""
    return _j(sql_tool.get_company_overview(ticker))


@tool
def financials(ticker: str, years: int = 4) -> str:
    """Get yearly revenue, net income, EBITDA, assets, liabilities, debt, cash, EPS, revenue growth and
    ratios (P/E, profit margin, ROE, ROA, debt/equity) for ONE ticker. Use for 'what happened' numbers."""
    return _j(sql_tool.get_financials(ticker, years))


@tool
def price_performance(ticker: str, period: str = "1y") -> str:
    """Stock price return, total return, high and low for ONE ticker. period: 1m, 3m, 6m, ytd, 1y, 3y or 5y."""
    return _j(sql_tool.get_price_performance(ticker, period))


@tool
def compare(tickers: list[str], period: str = "1y") -> str:
    """Compare up to 6 tickers side by side (fundamentals, ratios and price return over the period)."""
    return _j(sql_tool.compare_companies(tickers, period))


@tool
def sector_companies(sector: str) -> str:
    """List the companies in a GICS sector, e.g. 'Energy', 'Health Care', 'Information Technology'."""
    return _j(sql_tool.get_sector_companies(sector))


@tool
def search_filings(query: str, ticker: str = "") -> str:
    """Semantic search in the company's 10-K annual report. Use for 'why' questions and what the company says
    (risks, strategy, drivers of revenue, segments). Pass the ticker to restrict to one company."""
    return _j(rag_tool.search_filings(query, ticker or None, k=4))


@tool
def risk_metrics(ticker: str, period: str = "1y") -> str:
    """Computed volatility, Sharpe ratio, max drawdown and beta for ONE ticker. period: 1m, 3m, 6m, ytd, 1y, 3y, 5y."""
    return _j(quant_tools.risk_metrics(ticker, period))


@tool
def portfolio(weights: dict[str, float], period: str = "1y") -> str:
    """Analyse a portfolio. weights maps ticker -> weight, e.g. {"AAPL": 0.5, "JPM": 0.5}."""
    return _j(quant_tools.portfolio_analysis(weights, period))


TOOLS = [company_overview, financials, price_performance, compare, sector_companies,
         search_filings, risk_metrics, portfolio]
