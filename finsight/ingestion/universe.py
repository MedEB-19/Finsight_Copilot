"""44 US-listed companies: 4 per sector across all 11 GICS sectors."""
UNIVERSE: dict[str, list[str]] = {
    "Information Technology": ["AAPL", "MSFT", "NVDA", "AVGO"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD"],
    "Consumer Staples": ["KO", "PG", "WMT", "COST"],
    "Energy": ["XOM", "CVX", "COP", "SLB"],
    "Financials": ["JPM", "BAC", "GS", "V"],
    "Health Care": ["JNJ", "UNH", "PFE", "LLY"],
    "Industrials": ["BA", "CAT", "GE", "UPS"],
    "Materials": ["LIN", "SHW", "FCX", "NEM"],
    "Real Estate": ["AMT", "PLD", "EQIX", "SPG"],
    "Utilities": ["NEE", "DUK", "SO", "D"],
}
TICKER_SECTOR = {t: s for s, ts in UNIVERSE.items() for t in ts}
ALL_TICKERS = list(TICKER_SECTOR)
assert len(ALL_TICKERS) == 44
