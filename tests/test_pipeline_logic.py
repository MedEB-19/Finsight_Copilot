import math

import pandas as pd

from finsight.db.helpers import to_none
from finsight.ingestion.embed import chunk_words, clean_html
from finsight.ingestion.fundamentals import build_rows
from finsight.ingestion.prices import clean_history
from finsight.ingestion.ratios import compute_ratios
from finsight.ingestion.universe import ALL_TICKERS, UNIVERSE


def test_universe_is_44_with_4_per_sector():
    assert len(ALL_TICKERS) == 44 and len(set(ALL_TICKERS)) == 44
    assert len(UNIVERSE) == 11 and all(len(v) == 4 for v in UNIVERSE.values())


def test_to_none_handles_nan():
    assert to_none(float("nan")) is None and to_none(None) is None and to_none("x") is None
    assert to_none(3) == 3.0


def test_price_validation_drops_nan_rows():
    df = pd.DataFrame({"Open": [1, math.nan], "High": [2, math.nan], "Low": [1, math.nan],
                       "Close": [2, math.nan], "Adj Close": [2, math.nan], "Volume": [10, math.nan]},
                      index=pd.date_range("2024-01-01", periods=2))
    assert len(clean_history(df)) == 1


def test_fundamentals_skip_empty_placeholder_year_but_keep_partial():
    cols = [pd.Timestamp("2022-12-31"), pd.Timestamp("2023-12-31")]
    income = pd.DataFrame({cols[0]: [math.nan], cols[1]: [100.0]}, index=["Total Revenue"])
    rows = build_rows(1, income, None)
    assert len(rows) == 1 and rows[0]["fiscal_year"] == 2023 and rows[0]["total_assets"] is None


def test_ratios_null_when_inputs_missing():
    r = compute_ratios({"net_income": 10, "revenue": 100, "total_assets": 200, "total_liabilities": None,
                        "total_debt": 50, "eps": 2}, price=40)
    assert r["profit_margin"] == 0.1 and r["roa"] == 0.05 and r["pe_ratio"] == 20
    assert r["roe"] is None and r["debt_to_equity"] is None  # like NVDA: no liabilities -> NULL by design


def test_chunking_overlap():
    text = " ".join(f"w{i}" for i in range(1000))
    ch = chunk_words(text)
    assert len(ch) == 3
    assert ch[0].split()[-80:] == ch[1].split()[:80]


def test_clean_html_strips_xbrl_metadata():
    html = ("<html><body><ix:header>SECRET_META</ix:header><div style='display:none'>HIDDEN</div>"
            "<p>Revenue increased due to services.</p></body></html>")
    out = clean_html(html)
    assert "SECRET_META" not in out and "HIDDEN" not in out and "Revenue increased" in out
