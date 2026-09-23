"""Tests for Risk Guardian mathematical firewall and circuit breakers."""

import pytest
from bitget_skills_hub.risk_guardian.tools import (
    validate_trade_risk,
    trigger_emergency_kill_switch,
    deactivate_kill_switch
)
from src.core.config import settings


def test_order_size_cap_rejection():
    # Attempt order exceeding MAX_SINGLE_ORDER_USD
    too_large = settings.MAX_SINGLE_ORDER_USD + 500.0
    res = validate_trade_risk("BTCUSDT", "BUY", too_large)
    assert res["approved"] is False
    assert "MAX_SINGLE_ORDER_USD" in res["reason"]


def test_order_size_approval():
    safe_order = 100.0
    res = validate_trade_risk("BTCUSDT", "BUY", safe_order)
    assert res["approved"] is True
    assert res["risk_score"] < 50


def test_kill_switch_lockout():
    # Trigger kill switch
    trigger_emergency_kill_switch()

    # Any new order must be rejected
    res = validate_trade_risk("BTCUSDT", "BUY", 50.0)
    assert res["approved"] is False
    assert "Kill-Switch" in res["reason"]

    # Deactivate and verify reauthorization
    deactivate_kill_switch()
    res_after = validate_trade_risk("BTCUSDT", "BUY", 50.0)
    assert res_after["approved"] is True
