# Quant Engine Skill

Institutional factor modeling, tail-risk decomposition (VaR, CVaR), Hurst Exponent regime detection, and Markowitz portfolio optimization built on vectorized NumPy and SciPy.

## Tools
- `get_quant_risk_metrics(symbol)`: Calculates Parametric/Historical VaR (95%/99%), CVaR (Expected Shortfall), Sharpe, and Sortino ratios.
- `get_time_series_regime(symbol)`: Computes Hurst Exponent and Ornstein-Uhlenbeck mean-reversion half-life.
- `optimize_portfolio_weights(symbols)`: Solves Markowitz MPT for Max Sharpe, Min Volatility, and Risk Parity.
- `get_composite_alpha_score(symbol)`: Generates composite alpha score (-100 to +100) with volatility-adjusted stops.
