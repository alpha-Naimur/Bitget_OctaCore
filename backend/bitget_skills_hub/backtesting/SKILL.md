# Strategy Backtesting Skill

Vectorized historical strategy backtesting engine supporting 6 institutional quantitative trading models with realistic fees, slippage, and equity curve data generation.

## Supported Strategies
1. `EMA_CROSSOVER`: Fast/Slow EMA crossover with trend filter.
2. `RSI_MEAN_REVERSION`: Dynamic oversold accumulation with mean exit bounds.
3. `MACD_TREND`: MACD signal cross with zero-line recovery.
4. `BOLLINGER_BREAKOUT`: Volatility band expansion with volume confirmation.
5. `QUANT_MULTI_FACTOR`: Composite Z-Score + Momentum + Volatility sizing.
6. `DYNAMIC_DCA`: Volatility-scaled dip accumulation with take-profit targets.
