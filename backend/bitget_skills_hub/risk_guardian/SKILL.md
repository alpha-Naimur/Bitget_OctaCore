# Risk Guardian Skill

Mathematical pre-trade safety firewall, exposure limits, drawdown circuit breakers, and 1-click Emergency Kill-Switch for Bitget OctaCore.

## Tools
- `validate_trade_risk(symbol, side, amount_usdt)`: Mandatory pre-trade check evaluating order caps, exposure limits, and drawdown halts.
- `trigger_emergency_kill_switch()`: Liquidates all non-USDT holdings into stablecoins and blocks orders.
- `deactivate_kill_switch()`: Reauthorizes trading operations.
- `get_risk_firewall_status()`: Live telemetry on risk limits and utilization.
