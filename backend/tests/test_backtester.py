"""Tests for Strategy Backtester across 6 strategy architectures."""

import pytest
from bitget_skills_hub.backtesting.tools import run_strategy_backtest, compare_strategies


def test_run_strategy_backtest():
    res = run_strategy_backtest(symbol="NVDAUSDT", strategy_name="RSI_MEAN_REVERSION", initial_capital=10000.0)
    assert res["symbol"] == "NVDAUSDT"
    assert res["strategy"] == "RSI_MEAN_REVERSION"
    assert "return_pct" in res
    assert "benchmark_return_pct" in res
    assert "alpha_pct" in res
    assert "sharpe_ratio" in res
    assert "max_drawdown_pct" in res
    assert "win_rate_pct" in res
    assert "equity_curve" in res
    assert len(res["equity_curve"]) > 0


def test_compare_strategies():
    comp = compare_strategies("NVDAUSDT")
    assert comp["total_evaluated"] == 6
    assert "top_performing_strategy" in comp
    assert len(comp["rankings"]) == 6
