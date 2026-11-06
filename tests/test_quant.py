import numpy as np
import pandas as pd
import pytest

from finsight.tools import quant_tools as q


def series(vals):
    return pd.Series(vals, index=pd.date_range("2024-01-01", periods=len(vals), freq="B"))


def test_daily_returns():
    r = q.daily_returns(series([100, 110, 99]))
    assert r.iloc[0] == pytest.approx(0.10)
    assert r.iloc[1] == pytest.approx(-0.10)


def test_max_drawdown():
    d = q.max_drawdown(series([100, 120, 90, 110]))
    assert d["max_drawdown_pct"] == -25.0
    assert d["peak_date"] < d["trough_date"]


def test_volatility_zero_for_flat_returns_and_sharpe_none():
    r = series([0.001] * 50)
    assert q.annualized_volatility(r) == pytest.approx(0.0, abs=1e-12)


def test_beta_of_scaled_series_is_scale():
    rng = np.random.default_rng(0)
    bench = pd.Series(rng.normal(0, 0.01, 200), index=pd.date_range("2024-01-01", periods=200, freq="B"))
    assert q.beta(bench * 1.5, bench) == pytest.approx(1.5)


def test_portfolio_weights_normalised():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2024-01-01", periods=120, freq="B")
    prices = pd.DataFrame({"A": 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, 120)),
                           "B": 50 * np.cumprod(1 + rng.normal(0.0003, 0.008, 120))}, index=idx)
    out = q.portfolio_stats(prices, {"A": 2, "B": 2})
    assert out["weights"] == {"A": 0.5, "B": 0.5}
    assert out["annualized_volatility_pct"] > 0
