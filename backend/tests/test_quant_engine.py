"""Tests for Quant Engine, VaR/CVaR, Hurst Exponent, and Markowitz Optimization."""

import pytest
from bitget_skills_hub.quant_engine.tools import (
    get_quant_risk_metrics,
    get_time_series_regime,
    optimize_portfolio_weights,
    get_composite_alpha_score
)


def test_quant_risk_metrics():
    metrics = get_quant_risk_metrics("BTCUSDT")
    assert "var_95_pct" in metrics
    assert "cvar_95_pct" in metrics
    assert "sharpe_ratio" in metrics
    assert metrics["var_95_pct"] > 0
    assert metrics["cvar_95_pct"] >= metrics["var_95_pct"]  # CVaR is tail average


def test_time_series_regime():
    regime = get_time_series_regime("NVDAUSDT")
    assert "hurst_exponent" in regime
    assert 0.0 < regime["hurst_exponent"] < 1.0
    assert regime["regime"] in ("MEAN_REVERTING", "TRENDING_MOMENTUM", "RANDOM_WALK")
    assert regime["half_life_hours"] > 0


def test_portfolio_optimization():
    opt = optimize_portfolio_weights(["BTCUSDT", "NVDAUSDT", "AAPLUSDT"])
    assert "allocations" in opt
    allocations = opt["allocations"]
    assert len(allocations) >= 2
    total_alloc = sum(allocations.values())
    assert 0.95 <= total_alloc <= 1.05  # sum to ~1.0


def test_composite_alpha_score():
    alpha = get_composite_alpha_score("NVDAUSDT")
    assert "alpha_score" in alpha
    assert -100 <= alpha["alpha_score"] <= 100
    assert "brackets" in alpha
    assert "stop_loss" in alpha["brackets"]
    assert "take_profit_1" in alpha["brackets"]
