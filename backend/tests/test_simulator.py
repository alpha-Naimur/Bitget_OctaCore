"""Tests for Paper Trading Simulator, PnL accounting, and audit persistence."""

import pytest
from src.bitget.simulator import simulator
from src.core.memory import memory


def test_simulator_spot_cycle():
    simulator.reset()
    init_balance = simulator.get_balance("USDT")
    assert init_balance == 10000.0

    # 1. Buy 500 USDT of NVDAUSDT
    buy_res = simulator.execute_spot_order("NVDAUSDT", "BUY", amount_usdt=500.0)
    assert buy_res["success"] is True
    assert buy_res["amount_usdt"] == 500.0
    assert simulator.get_balance("NVDA") > 0

    port = simulator.get_portfolio_summary()
    assert len(port["holdings"]) >= 1

    # 2. Sell NVDA holdings
    sell_res = simulator.execute_spot_order("NVDAUSDT", "SELL", quantity=simulator.get_balance("NVDA"))
    assert sell_res["success"] is True
    assert simulator.get_balance("NVDA") <= 0.00001


def test_simulator_futures_order():
    simulator.reset()
    fut_res = simulator.execute_futures_order("AAPLUSDT", "BUY", amount_usdt=300.0, leverage=10)
    assert fut_res["success"] is True
    assert fut_res["leverage"] == 10
    assert "AAPLUSDT" in simulator.futures_positions


def test_paper_trading_audit_metrics():
    metrics = memory.get_paper_trading_metrics()
    assert "total_trades" in metrics
    assert "win_rate_pct" in metrics
    assert "realized_pnl_usdt" in metrics


def test_kill_switch_spot_and_futures_liquidation():
    simulator.reset()
    # 1. Open spot position
    buy_spot = simulator.execute_spot_order("BTCUSDT", "BUY", amount_usdt=200.0)
    assert buy_spot["success"] is True
    assert simulator.get_balance("BTC") > 0

    # 2. Open futures position
    buy_fut = simulator.execute_futures_order("AAPLUSDT", "BUY", amount_usdt=300.0, leverage=10)
    assert buy_fut["success"] is True
    assert "AAPLUSDT" in simulator.futures_positions

    # 3. Trigger emergency kill switch
    kill_res = simulator.trigger_emergency_kill_switch()
    assert kill_res["status"] == "KILL_SWITCH_ACTIVE"
    assert kill_res["closed_spot_count"] == 1
    assert kill_res["closed_futures_count"] == 1

    # Verify all positions zeroed out and returned to USDT
    port = simulator.get_portfolio_summary()
    assert len(port["holdings"]) == 0
    assert simulator.get_balance("BTC") <= 0.00001
    assert len(simulator.futures_positions) == 0

    # Deactivate for subsequent tests
    simulator.deactivate_kill_switch()


def test_simulator_futures_close_lifecycle():
    simulator.reset()
    # Open long futures
    open_res = simulator.execute_futures_order("NVDAUSDT", "BUY", amount_usdt=400.0, leverage=10)
    assert open_res["success"] is True
    assert "NVDAUSDT" in simulator.futures_positions

    margin_before = simulator.futures_margin_balance
    # Close by placing opposite side (SELL)
    close_res = simulator.execute_futures_order("NVDAUSDT", "SELL", amount_usdt=400.0)
    assert close_res["success"] is True
    assert close_res["side"] == "CLOSE_BUY"
    assert "NVDAUSDT" not in simulator.futures_positions
    # Margin should have been returned
    assert simulator.futures_margin_balance > margin_before

