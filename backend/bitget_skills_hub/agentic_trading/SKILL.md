# Agentic Trading Execution Skill

Unified trading execution skill routing orders across Spot, Mix Futures (Crypto & 7x24 Tokenized US Equities), and Volatility-Scaled Smart DCA with pre-trade risk verification.

## Tools
- `execute_spot_order(symbol, side, amount_usdt, quantity, reason)`: Places spot orders with pre-trade firewall check.
- `execute_futures_order(symbol, side, amount_usdt, leverage, reason)`: Places futures orders with leverage control.
- `execute_smart_dca(symbol, base_dca_amount_usdt)`: Accumulates assets with volatility-adjusted allocation sizing.
- `get_portfolio_status()`: Returns equity, balances, unrealized/realized PnL, and holdings.
- `switch_execution_mode(mode)`: Toggles between SIMULATION, TESTNET, MAINNET, and SUB_ACCOUNT.
