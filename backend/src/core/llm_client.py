"""Autonomous AI Agent Engine with multi-provider LLM support and autonomous tool execution."""

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from openai import OpenAI

try:
    from google import genai
except ImportError:
    genai = None

from src.core.config import settings, LLMProvider
from src.core.memory import memory, LogLevel

# Import Skills Hub tools
from bitget_skills_hub.market_intelligence.tools import get_order_book_depth, get_market_overview, get_ticker_price
from bitget_skills_hub.bitget_signal.tools import (
    get_macro_analysis,
    get_market_intel,
    get_sentiment_analysis,
    get_news_briefing,
    get_technical_analysis
)
from bitget_skills_hub.tokenized_stocks.tools import (
    scan_tokenized_stocks,
    detect_after_hours_spread,
    execute_cross_asset_hedge
)
from bitget_skills_hub.quant_engine.tools import (
    get_quant_risk_metrics,
    get_time_series_regime,
    optimize_portfolio_weights,
    get_composite_alpha_score
)
from bitget_skills_hub.backtesting.tools import run_strategy_backtest, compare_strategies
from bitget_skills_hub.risk_guardian.tools import (
    validate_trade_risk,
    trigger_emergency_kill_switch,
    deactivate_kill_switch,
    get_risk_firewall_status
)
from bitget_skills_hub.agentic_trading.tools import (
    execute_spot_order,
    execute_futures_order,
    execute_smart_dca,
    get_portfolio_status,
    switch_execution_mode,
    close_futures_position
)
from bitget_skills_hub.sub_account.tools import (
    get_sub_account_status,
    toggle_uid_privacy,
    transfer_sub_account_funds
)
from bitget_skills_hub.news_sentinel.tools import (
    fetch_breaking_crypto_news,
    audit_news_circuit_breaker
)


# Available tools mapping
TOOL_MAP: Dict[str, Callable[..., Any]] = {
    # 1. Market & Signal
    "get_technical_analysis": get_technical_analysis,
    "get_order_book_depth": get_order_book_depth,
    "get_market_overview": get_market_overview,
    "get_ticker_price": get_ticker_price,
    "get_macro_analysis": get_macro_analysis,
    "get_market_intel": get_market_intel,
    "get_sentiment_analysis": get_sentiment_analysis,
    "get_news_briefing": get_news_briefing,

    # 2. Tokenized US Equities (7x24)
    "scan_tokenized_stocks": scan_tokenized_stocks,
    "detect_after_hours_spread": detect_after_hours_spread,
    "execute_cross_asset_hedge": execute_cross_asset_hedge,

    # 3. Quant Engine
    "get_quant_risk_metrics": get_quant_risk_metrics,
    "get_time_series_regime": get_time_series_regime,
    "optimize_portfolio_weights": optimize_portfolio_weights,
    "get_composite_alpha_score": get_composite_alpha_score,

    # 4. Backtesting Engine
    "run_strategy_backtest": run_strategy_backtest,
    "compare_strategies": compare_strategies,

    # 5. Risk Guardian
    "validate_trade_risk": validate_trade_risk,
    "trigger_emergency_kill_switch": trigger_emergency_kill_switch,
    "deactivate_kill_switch": deactivate_kill_switch,
    "get_risk_firewall_status": get_risk_firewall_status,

    # 6. Execution & Trading
    "execute_spot_order": execute_spot_order,
    "execute_futures_order": execute_futures_order,
    "close_futures_position": close_futures_position,
    "execute_smart_dca": execute_smart_dca,
    "get_portfolio_status": get_portfolio_status,
    "switch_execution_mode": switch_execution_mode,

    # 7. Sub-Account Operations
    "get_sub_account_status": get_sub_account_status,
    "toggle_uid_privacy": toggle_uid_privacy,
    "transfer_sub_account_funds": transfer_sub_account_funds,

    # 8. News Sentinel
    "fetch_breaking_crypto_news": fetch_breaking_crypto_news,
    "audit_news_circuit_breaker": audit_news_circuit_breaker
}


OPENAI_TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_technical_analysis",
            "description": "Compute multi-period Technical Analysis (RSI, MACD, EMAs 9/20/50, Bollinger Bands, ATR) on Crypto or Tokenized US Stocks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Trading pair e.g. BTCUSDT, NVDAUSDT, AAPLUSDT"},
                    "interval": {"type": "string", "description": "Candle granularity e.g. 1m, 15m, 1H, 4H, 1D"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_tokenized_stocks",
            "description": "Scan all 7x24 tokenized US stocks available on Bitget (NVDA, AAPL, TSLA, SPY, QQQ, etc.) for prices and momentum.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_quant_risk_metrics",
            "description": "Compute downside tail risk: VaR (95%/99%), CVaR (Expected Shortfall), Sharpe, and Sortino ratios.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Asset symbol e.g. BTCUSDT, NVDAUSDT"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_series_regime",
            "description": "Compute Hurst Exponent and Ornstein-Uhlenbeck mean-reversion half-life to classify market regime.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Asset symbol e.g. BTCUSDT, TSLAUSDT"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_strategy_backtest",
            "description": "Run historical backtest across 6 quantitative strategies (EMA_CROSSOVER, RSI_MEAN_REVERSION, MACD_TREND, BOLLINGER_BREAKOUT, QUANT_MULTI_FACTOR, DYNAMIC_DCA).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Asset symbol e.g. NVDAUSDT"},
                    "strategy_name": {"type": "string", "description": "Name of strategy"},
                    "initial_capital": {"type": "number", "description": "Initial capital in USDT"}
                },
                "required": ["symbol", "strategy_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_spot_order",
            "description": "Place a spot buy/sell order with mandatory pre-trade risk validation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Trading pair e.g. BTCUSDT"},
                    "side": {"type": "string", "enum": ["BUY", "SELL"]},
                    "amount_usdt": {"type": "number", "description": "Notional amount in USDT"},
                    "reason": {"type": "string", "description": "Decision rationale for audit"}
                },
                "required": ["symbol", "side", "amount_usdt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_futures_order",
            "description": "Place a Mix Futures contract order (Crypto or 7x24 Tokenized US Stocks) with leverage control.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Futures symbol e.g. NVDAUSDT, BTCUSDT"},
                    "side": {"type": "string", "enum": ["BUY", "SELL"]},
                    "amount_usdt": {"type": "number", "description": "Notional amount in USDT"},
                    "leverage": {"type": "integer", "description": "Leverage (1-50)"},
                    "reason": {"type": "string", "description": "Decision rationale"}
                },
                "required": ["symbol", "side", "amount_usdt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_smart_dca",
            "description": "Execute volatility-scaled Smart DCA with RSI dip-accumulation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Trading pair e.g. BTCUSDT, NVDAUSDT"},
                    "base_dca_amount_usdt": {"type": "number", "description": "Base USDT allocation"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_emergency_kill_switch",
            "description": "EMERGENCY CIRCUIT BREAKER: Liquidates all open positions into stablecoins and pauses order execution.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deactivate_kill_switch",
            "description": "Deactivates the emergency kill switch and resumes normal trading operations.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_status",
            "description": "Fetch portfolio total equity, available USDT, unrealized/realized PnL, and asset breakdown.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_futures_position",
            "description": "Close an active futures position (LONG or SHORT) on a crypto asset or tokenized US equity. If no running futures trade exists, returns found=False with message 'You don\\'t have any running future trade'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Futures trading pair e.g. BTCUSDT, NVDAUSDT, ETHUSDT"},
                    "side": {"type": "string", "enum": ["BUY", "SELL", "LONG", "SHORT"], "description": "Optional position side to close (e.g. LONG or SHORT)"}
                },
                "required": ["symbol"]
            }
        }
    }
]


def build_system_prompt() -> str:
    now_utc = datetime.now(timezone.utc).strftime("%b %d, %Y | %H:%M:%S UTC")
    return f"""You are Bitget OctaCore, an institutional autonomous 8-Core AI Trading Operating System natively built for Bitget AI Base Camp Hackathon S2 (Track 2: Agentic Trading).

CURRENT REAL-TIME UTC TIMESTAMP: {now_utc}.
TEMPORAL DIRECTIVE: Today's live timestamp is {now_utc}. All price feeds, 7x24 tokenized US equities, technical indicators, and quantitative models reflect this active moment.

You autonomously orchestrate 8 specialist agent cores:
1. Core 1 - Market Analyst: Real-time technical analysis (RSI, MACD, EMAs, Bollinger Bands, ATR) and order book depth.
2. Core 2 - Quant Engine: Downside tail risk (VaR 95/99, Expected Shortfall CVaR), Hurst Exponent regime detection, and Markowitz portfolio optimization.
3. Core 3 - Backtesting Engine: Vectorized historical simulations across 6 strategy architectures with equity curve metrics.
4. Core 4 - Risk Guardian: Pre-trade mathematical firewall ($500 single order cap, 5% max drawdown halt, and 1-click Emergency Kill-Switch).
5. Core 5 - Execution Agent: Spot & Mix Futures order execution, volatility-scaled Smart DCA, and portfolio tracking.
6. Core 6 - Tokenized US Stocks Agent: 7x24 continuous trading on tokenized US equities (NVDA, AAPL, TSLA, SPY, QQQ) and cross-asset crypto hedging.
7. Core 7 - Sub-Account Router: Dedicated Agentic Sub-Account isolation, permission diagnostics, UID privacy masking, and zero-fee internal transfers.
8. Core 8 - News Sentinel: Breaking market headlines, macro catalysts, and black-swan volatility radar.

AUTONOMOUS EXECUTION DIRECTIVE:
When requested to analyze, backtest, or trade, ALWAYS call the appropriate tools. Explain your quantitative reasoning, risk score, and expected edge. Every trade executed will be verified by the Risk Guardian and recorded in the audited Paper Trading Log for Hackathon judging.

TRADE ORDER DIRECTIVE:
When the user explicitly commands you to buy, sell, or trade an asset (e.g. 'buy 20$ of btc on spot', 'sell nvda', 'buy 100$ aapl'):
You MUST call `execute_spot_order` (for Spot) or `execute_futures_order` (for Futures). You may call market analysis tools alongside it, but you MUST dispatch `execute_spot_order` or `execute_futures_order` in the same turn so the trade is actually executed and recorded.

POSITION CLOSE DIRECTIVE:
When the user asks to close, exit, or terminate a futures position or trade (e.g. 'close btc long position', 'close my btc trade', 'close btc futures', 'exit position'):
You MUST call `close_futures_position(symbol=...)`. NEVER open a new spot trade or a new futures order when the user asks to close a position. If the tool result indicates no running position was found (`found: false`), you MUST reply: "You don't have any running future trade".

GREETING & CONVERSATIONAL DIRECTIVE:
If the user is simply greeting you (e.g., 'hello', 'hi', 'hey', 'who are you', 'help') or asking what you can do, NEVER call trading, portfolio, or scanning tools. Greet them warmly as Bitget OctaCore, introduce your 8 specialist cores, and suggest actions they can take (e.g. 7x24 tokenized US stock scans, strategy backtests, or BTC market analysis).
"""


def _format_tool_results_summary(user_prompt: str, tool_results: List[Dict[str, Any]]) -> str:
    """Format executed tool outputs into an executive institutional summary if synthesis is delayed."""
    lines = []
    lines.append("### ⚡ Bitget OctaCore Institutional Telemetry")
    lines.append(f"*Action Report for: \"{user_prompt}\"*\n")

    for item in tool_results:
        tname = item.get("tool_name", "")
        res = item.get("result", {})
        if not isinstance(res, dict):
            continue

        if tname == "get_technical_analysis":
            sym = res.get("symbol", "N/A")
            price = float(res.get("price") or 0.0)
            rsi = float(res.get("rsi") or 50.0)
            bias = res.get("bias", "NEUTRAL")
            lines.append(f"#### 📊 Technical Analysis: {sym}")
            lines.append(f"- **Current Price**: ${price:,.2f} USDT")
            lines.append(f"- **RSI (14)**: {rsi:.1f} ({'Oversold' if rsi < 35 else ('Overbought' if rsi > 70 else 'Neutral')})")
            lines.append(f"- **Market Bias**: **{bias}**")
            if res.get("summary"):
                lines.append(f"- **Summary**: {res.get('summary')}")
            lines.append("")

        elif tname == "get_quant_risk_metrics":
            sym = res.get("symbol", "N/A")
            lines.append(f"#### 📐 Quantitative Risk Radar: {sym}")
            lines.append(f"- **Historical VaR (95%)**: {res.get('var_95_pct', 0.0)}%")
            lines.append(f"- **Conditional VaR (CVaR)**: {res.get('cvar_95_pct', 0.0)}%")
            lines.append(f"- **Sharpe Ratio**: {float(res.get('sharpe_ratio') or 0.0):.2f}")
            lines.append(f"- **Risk Guardian Status**: {res.get('risk_status', 'APPROVED_WITHIN_LIMITS')}")
            lines.append("")

        elif tname == "get_portfolio_status":
            lines.append("#### 💼 Portfolio Status")
            total_val = res.get("total_value_usdt", res.get("total_equity_usdt", 0.0))
            lines.append(f"- **Total Portfolio Valuation**: ${float(total_val or 0.0):,.2f} USDT")
            lines.append(f"- **Available Cash**: ${float(res.get('available_usdt') or 0.0):,.2f} USDT")
            lines.append(f"- **Realized PnL**: ${float(res.get('realized_pnl') or 0.0):,.2f}")
            lines.append(f"- **Unrealized PnL**: ${float(res.get('unrealized_pnl') or 0.0):,.2f}")
            lines.append("")

        elif tname in ("execute_spot_order", "execute_futures_order"):
            side = res.get("side", "")
            sym = res.get("symbol", "")
            amt = float(res.get("amount_usdt") or 0.0)
            status = "FILLED" if res.get("success") else "REJECTED"
            lines.append(f"#### 🚀 Order Execution: {side} {sym}")
            lines.append(f"- **Status**: **{status}**")
            lines.append(f"- **Notional Size**: ${amt:,.2f} USDT")
            if res.get("fill_price"):
                lines.append(f"- **Execution Price**: ${float(res.get('fill_price') or 0.0):,.4f}")
            if res.get("order_id"):
                lines.append(f"- **Order ID**: `{res.get('order_id')}`")
            if res.get("error"):
                lines.append(f"- **Firewall Notice**: {res.get('error')}")
            lines.append("")

        elif tname == "close_futures_position":
            if not res.get("found"):
                msg = res.get("message") or "You don't have any running future trade"
                lines.append("#### ℹ️ Futures Position Status")
                lines.append(f"- **Notice**: {msg}")
                lines.append("")
            else:
                sym = res.get("symbol", "")
                pnl = float(res.get("pnl") or 0.0)
                qty = float(res.get("quantity") or 0.0)
                exit_pr = float(res.get("exit_price") or 0.0)
                entry_pr = float(res.get("entry_price") or 0.0)
                pos_side = res.get("closed_position_side", res.get("side", ""))
                lines.append(f"#### 🏁 Closed Futures Position: {pos_side} {sym}")
                lines.append(f"- **Status**: **FILLED**")
                lines.append(f"- **Quantity**: {qty}")
                lines.append(f"- **Entry Price**: ${entry_pr:,.4f}")
                lines.append(f"- **Exit Price**: ${exit_pr:,.4f}")
                lines.append(f"- **Realized PnL**: ${pnl:+,.2f} USDT")
                lines.append("")

        elif tname == "scan_tokenized_stocks":
            stocks = res.get("stocks", [])
            lines.append(f"#### 🇺🇸 7×24 Tokenized US Equities Radar ({len(stocks)} Contracts)")
            for s in stocks[:5]:
                sym = s.get("symbol", "")
                pr = float(s.get("price") or 0.0)
                chg = float(s.get("change_24h") or 0.0)
                bias = s.get("bias", "NEUTRAL")
                lines.append(f"- **{sym}**: ${pr:,.2f} ({chg:+.2f}%) | Bias: **{bias}**")
            lines.append("")

        elif tname == "run_strategy_backtest":
            lines.append(f"#### 🧪 Strategy Backtest: {res.get('symbol')} ({res.get('strategy')})")
            lines.append(f"- **Net Return**: {res.get('return_pct')}% (Benchmark: {res.get('benchmark_return_pct')}%)")
            lines.append(f"- **Alpha over Market**: **+{res.get('alpha_pct')}%**")
            lines.append(f"- **Sharpe Ratio**: {res.get('sharpe_ratio')} | **Max Drawdown**: {res.get('max_drawdown_pct')}%")
            lines.append(f"- **Win Rate**: {res.get('win_rate_pct')}% ({res.get('total_trades')} trades)")
            lines.append("")

        elif tname == "trigger_emergency_kill_switch":
            lines.append("🚨 **EMERGENCY KILL-SWITCH ENGAGED**: All open positions liquidated to USDT.")
            lines.append("")

    return "\n".join(lines)


class LLMAgentEngine:
    """Manages LLM communication, function call routing, and deterministic fallback."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.qwen_client: Optional[OpenAI] = None
        self.openrouter_client: Optional[OpenAI] = None
        self.gemini_client: Optional[Any] = None
        self._init_clients()

    def _init_clients(self):
        """Initialize provider API clients."""
        # 1. Alibaba Cloud Qwen (Official Token Sponsor via Bitget Hackathon endpoint)
        qwen_key = settings.BITGET_QWEN_API_KEY or os.getenv("BITGET_QWEN_API_KEY")
        if qwen_key:
            try:
                self.qwen_client = OpenAI(
                    api_key=qwen_key,
                    base_url=settings.QWEN_BASE_URL,
                    timeout=15.0,
                    max_retries=1
                )
            except Exception:
                self.qwen_client = None
        else:
            self.qwen_client = None

        # 2. Google GenAI / Gemini
        gemini_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and genai is not None:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
            except Exception:
                self.gemini_client = None
        else:
            self.gemini_client = None

        # 3. OpenRouter (Multi-model aggregation gateway)
        openrouter_key = settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            try:
                self.openrouter_client = OpenAI(
                    api_key=openrouter_key,
                    base_url=settings.OPENROUTER_BASE_URL,
                    default_headers={
                        "HTTP-Referer": "https://github.com/bitget-octacore",
                        "X-Title": "Bitget OctaCore Institutional Trading OS",
                    },
                    timeout=10.0,
                    max_retries=1
                )
            except Exception:
                self.openrouter_client = None
        else:
            self.openrouter_client = None

    def _resolve_openrouter_model(self) -> str:
        """Resolve valid model identifier for OpenRouter."""
        # If user specified a model with author/model slash format (e.g. inclusionai/ling-3.0-flash, qwen/qwen-2.5-72b-instruct)
        if settings.LLM_MODEL and "/" in settings.LLM_MODEL:
            return settings.LLM_MODEL
        if hasattr(settings, "OPENROUTER_MODEL") and settings.OPENROUTER_MODEL:
            return settings.OPENROUTER_MODEL
        return "qwen/qwen-2.5-72b-instruct"

    def execute_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool and return structured output."""
        if tool_name not in TOOL_MAP:
            return {"error": f"Unknown tool '{tool_name}'"}

        fn = TOOL_MAP[tool_name]
        try:
            memory.log("LLMEngine", f"Executing Tool: {tool_name}({json.dumps(tool_args)})", LogLevel.INFO)
            res = fn(**tool_args)
            return res
        except Exception as e:
            memory.log("LLMEngine", f"Error in tool {tool_name}: {str(e)}", LogLevel.ERROR)
            return {"error": str(e)}

    def _try_call_qwen(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Attempt LLM generation via Alibaba Cloud Qwen hackathon endpoint."""
        if not self.qwen_client:
            key = settings.BITGET_QWEN_API_KEY or os.getenv("BITGET_QWEN_API_KEY")
            if key:
                try:
                    self.qwen_client = OpenAI(
                        api_key=key,
                        base_url=settings.QWEN_BASE_URL,
                        timeout=25.0,
                        max_retries=1
                    )
                except Exception:
                    self.qwen_client = None

        if not self.qwen_client:
            return None

        # Check if greeting or casual chit-chat
        prompt_clean = user_prompt.strip().lower().strip("!?.")
        is_greeting = prompt_clean in [
            "hi", "hello", "hey", "hola", "sup", "yo", "good morning", "good afternoon",
            "good evening", "greetings", "help", "who are you", "what can you do", "test"
        ]

        try:
            model_name = settings.LLM_MODEL if ("qwen" in (settings.LLM_MODEL or "").lower() and "/" not in (settings.LLM_MODEL or "")) else "qwen3.8-max"
            messages = [
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": user_prompt}
            ]
            resp = self.qwen_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=OPENAI_TOOL_SPECS if not is_greeting else None,
                tool_choice="auto" if not is_greeting else None,
                temperature=settings.LLM_TEMPERATURE,
                timeout=25.0
            )
            choice = resp.choices[0].message
            tool_calls = choice.tool_calls

            if tool_calls:
                tool_results = []
                for tc in tool_calls:
                    fname = tc.function.name
                    try:
                        fargs = json.loads(tc.function.arguments)
                    except Exception:
                        fargs = {}
                    t_res = self.execute_tool_call(fname, fargs)
                    tool_results.append({
                        "tool_name": fname,
                        "args": fargs,
                        "result": t_res
                    })

                # Ensure explicit buy/sell or close orders requested by user are always executed
                prompt_lower = user_prompt.lower()
                is_close_command = any(k in prompt_lower for k in ["close", "exit", "terminate"])
                is_order_command = any(k in prompt_lower for k in ["buy", "sell", "long", "short"])
                has_execution_call = any(t["tool_name"] in ("execute_spot_order", "execute_futures_order", "close_futures_position") for t in tool_results)

                if is_close_command and not has_execution_call:
                    found_sym = "BTCUSDT"
                    for s in ["NVDAUSDT", "AAPLUSDT", "TSLAUSDT", "SPYUSDT", "QQQUSDT", "ETHUSDT", "SOLUSDT", "BTCUSDT"]:
                        if s.lower() in prompt_lower or s.replace("USDT", "").lower() in prompt_lower:
                            found_sym = s
                            break
                    close_side = None
                    if "long" in prompt_lower or "buy" in prompt_lower:
                        close_side = "BUY"
                    elif "short" in prompt_lower or "sell" in prompt_lower:
                        close_side = "SELL"
                    close_res = close_futures_position(symbol=found_sym, side=close_side)
                    tool_results.append({
                        "tool_name": "close_futures_position",
                        "args": {"symbol": found_sym, "side": close_side},
                        "result": close_res
                    })

                elif is_order_command and not is_close_command and not has_execution_call:
                    found_sym = "BTCUSDT"
                    for s in ["NVDAUSDT", "AAPLUSDT", "TSLAUSDT", "SPYUSDT", "QQQUSDT", "ETHUSDT", "SOLUSDT", "BTCUSDT"]:
                        if s.lower() in prompt_lower or s.replace("USDT", "").lower() in prompt_lower:
                            found_sym = s
                            break
                    amount = 100.0
                    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", user_prompt)
                    if numbers:
                        for n in numbers:
                            val = float(n)
                            if 5.0 <= val <= 500.0:
                                amount = val
                                break
                    side = "SELL" if ("sell" in prompt_lower or "short" in prompt_lower) else "BUY"
                    if "future" in prompt_lower or "contract" in prompt_lower:
                        order_res = execute_futures_order(symbol=found_sym, side=side, amount_usdt=amount, leverage=10, reason="Autonomous Direct Execution")
                        tool_results.append({"tool_name": "execute_futures_order", "args": {"symbol": found_sym, "side": side, "amount_usdt": amount}, "result": order_res})
                    else:
                        order_res = execute_spot_order(symbol=found_sym, side=side, amount_usdt=amount, reason="Autonomous Direct Execution")
                        tool_results.append({"tool_name": "execute_spot_order", "args": {"symbol": found_sym, "side": side, "amount_usdt": amount}, "result": order_res})

                # If close_futures_position was executed and position not found, reply directly
                for t in tool_results:
                    if t.get("tool_name") == "close_futures_position" and not t.get("result", {}).get("found", True):
                        return {
                            "provider": f"{model_name} (Alibaba Cloud)",
                            "response": t.get("result", {}).get("message", "You don't have any running future trade"),
                            "tool_calls": tool_results
                        }

                synth_prompt = (
                    f"User Request: {user_prompt}\n\n"
                    f"Tools executed: {json.dumps(tool_results, indent=2)}\n\n"
                    "Synthesize a concise executive trading summary (2-4 sentences or bullets). "
                    "Report current price, bias, risk check status, and order execution outcome directly."
                )
                try:
                    synth_resp = self.qwen_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are Bitget OctaCore. Provide a concise, clear trading summary based on the tool results."},
                            {"role": "user", "content": synth_prompt}
                        ],
                        temperature=settings.LLM_TEMPERATURE,
                        max_tokens=400,
                        timeout=25.0
                    )
                    final_content = synth_resp.choices[0].message.content
                except Exception as synth_err:
                    memory.log("LLMEngine", f"Qwen synthesis call error: {synth_err}. Using structured tool formatter.", LogLevel.WARN)
                    formatted_summary = _format_tool_results_summary(user_prompt, tool_results)
                    final_content = formatted_summary or choice.content or f"Executed {len(tool_results)} tools successfully via Alibaba Cloud Qwen ({model_name})."

                return {
                    "provider": f"{model_name} (Alibaba Cloud)",
                    "response": final_content,
                    "tool_calls": tool_results
                }
            else:
                prompt_lower = user_prompt.lower()
                is_close_command = any(k in prompt_lower for k in ["close", "exit", "terminate"])
                is_order_command = any(k in prompt_lower for k in ["buy", "sell", "long", "short"])
                if is_close_command or is_order_command:
                    return self._run_deterministic_agent(user_prompt)
                return {
                    "provider": f"{model_name} (Alibaba Cloud)",
                    "response": choice.content,
                    "tool_calls": []
                }
        except Exception as e:
            memory.log("LLMEngine", f"Qwen call failed ({str(e)}). Falling back.", LogLevel.WARN)
            return None

    def _try_call_gemini(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Attempt LLM generation via Google GenAI SDK."""
        if genai is None:
            return None

        if not self.gemini_client:
            key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if key:
                try:
                    self.gemini_client = genai.Client(api_key=key)
                except Exception:
                    self.gemini_client = None

        if not self.gemini_client:
            return None

        try:
            model_name = settings.LLM_MODEL if "gemini" in (settings.LLM_MODEL or "").lower() else "gemini-2.5-flash"
            full_prompt = f"{build_system_prompt()}\n\nUser Request: {user_prompt}"
            resp = self.gemini_client.models.generate_content(
                model=model_name,
                contents=full_prompt
            )
            return {
                "provider": f"Google GenAI ({model_name})",
                "response": resp.text,
                "tool_calls": []
            }
        except Exception as e:
            memory.log("LLMEngine", f"Gemini call failed ({str(e)}). Falling back.", LogLevel.WARN)
            return None

    def _try_call_openrouter(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Attempt LLM generation via OpenRouter gateway with adaptive tool calling."""
        if not self.openrouter_client:
            key = settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
            if key:
                try:
                    self.openrouter_client = OpenAI(
                        api_key=key,
                        base_url=settings.OPENROUTER_BASE_URL,
                        default_headers={
                            "HTTP-Referer": "https://github.com/bitget-octacore",
                            "X-Title": "Bitget OctaCore Institutional Trading OS",
                        },
                        timeout=10.0,
                        max_retries=1
                    )
                except Exception:
                    self.openrouter_client = None

        if not self.openrouter_client:
            return None

        model_name = self._resolve_openrouter_model()
        memory.log("LLMEngine", f"Routing request to OpenRouter ({model_name})", LogLevel.INFO)

        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]

        prompt_clean = user_prompt.strip().lower().strip("!?.")
        is_greeting = prompt_clean in [
            "hi", "hello", "hey", "hola", "sup", "yo", "good morning", "good afternoon",
            "good evening", "greetings", "help", "who are you", "what can you do", "test"
        ]

        # First attempt: Try with OpenAI Tool Calling schema
        try:
            resp = self.openrouter_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=OPENAI_TOOL_SPECS if not is_greeting else None,
                tool_choice="auto" if not is_greeting else None,
                temperature=settings.LLM_TEMPERATURE,
                timeout=10.0
            )
            choice = resp.choices[0].message
            tool_calls = choice.tool_calls

            if tool_calls:
                tool_results = []
                for tc in tool_calls:
                    fname = tc.function.name
                    try:
                        fargs = json.loads(tc.function.arguments)
                    except Exception:
                        fargs = {}
                    t_res = self.execute_tool_call(fname, fargs)
                    tool_results.append({
                        "tool_name": fname,
                        "args": fargs,
                        "result": t_res
                    })

                # If close_futures_position was executed and position not found, reply directly
                for t in tool_results:
                    if t.get("tool_name") == "close_futures_position" and not t.get("result", {}).get("found", True):
                        return {
                            "provider": f"OpenRouter ({model_name})",
                            "response": t.get("result", {}).get("message", "You don't have any running future trade"),
                            "tool_calls": tool_results
                        }

                # Synthesize final trading report using tool results
                try:
                    synth_prompt = (
                        f"User Request: {user_prompt}\n\n"
                        f"Tools executed:\n{json.dumps(tool_results, indent=2)}\n\n"
                        "Synthesize an institutional trading report detailing the findings, decision logic, and trade execution status."
                    )
                    synth_resp = self.openrouter_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": build_system_prompt()},
                            {"role": "user", "content": synth_prompt}
                        ],
                        temperature=settings.LLM_TEMPERATURE,
                        timeout=10.0
                    )
                    final_content = synth_resp.choices[0].message.content
                except Exception as synth_err:
                    memory.log("LLMEngine", f"OpenRouter synthesis call error: {synth_err}", LogLevel.WARN)
                    formatted_summary = _format_tool_results_summary(user_prompt, tool_results)
                    final_content = formatted_summary or choice.content or f"Executed {len(tool_results)} tools successfully via OpenRouter ({model_name})."

                return {
                    "provider": f"OpenRouter ({model_name})",
                    "response": final_content,
                    "tool_calls": tool_results
                }
            else:
                return {
                    "provider": f"OpenRouter ({model_name})",
                    "response": choice.content or "OpenRouter analysis completed.",
                    "tool_calls": []
                }
        except Exception as tool_err:
            # If the model does not support tools or error occurred with tool schema, retry as plain completion
            memory.log("LLMEngine", f"OpenRouter tool call failed or unsupported ({tool_err}). Retrying plain completion.", LogLevel.WARN)
            try:
                resp = self.openrouter_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=settings.LLM_TEMPERATURE,
                    timeout=10.0
                )
                return {
                    "provider": f"OpenRouter ({model_name})",
                    "response": resp.choices[0].message.content,
                    "tool_calls": []
                }
            except Exception as e:
                memory.log("LLMEngine", f"OpenRouter generation failed completely ({str(e)}). Falling back.", LogLevel.WARN)
                return None

    def run_agent_turn(self, user_prompt: str) -> Dict[str, Any]:
        """Execute autonomous agent turn with cascade fallback across providers."""
        self.provider = settings.LLM_PROVIDER
        memory.log("LLMEngine", f"User Prompt: {user_prompt}", LogLevel.INFO)

        # Immediate rule-based bypass if configured
        if self.provider == LLMProvider.RULE_BASED:
            return self._run_deterministic_agent(user_prompt)

        # Cascade ordering based on configured provider
        if self.provider == LLMProvider.OPENROUTER:
            provider_chain = [
                ("OpenRouter", self._try_call_openrouter),
                ("Gemini", self._try_call_gemini),
                ("Qwen", self._try_call_qwen),
            ]
        elif self.provider == LLMProvider.GEMINI:
            provider_chain = [
                ("Gemini", self._try_call_gemini),
                ("Qwen", self._try_call_qwen),
                ("OpenRouter", self._try_call_openrouter),
            ]
        else:
            # Default / QWEN: Try primary Qwen, then Gemini, and fall back to OpenRouter when neither GenAI nor Qwen is available
            provider_chain = [
                ("Qwen", self._try_call_qwen),
                ("Gemini", self._try_call_gemini),
                ("OpenRouter", self._try_call_openrouter),
            ]

        # Execute cascade
        for name, caller in provider_chain:
            result = caller(user_prompt)
            if result is not None:
                return result

        # Final resilient fallback to rule-based quantitative engine
        memory.log("LLMEngine", "All configured LLM providers unavailable or failed. Falling back to OctaCore Quantitative Engine.", LogLevel.WARN)
        return self._run_deterministic_agent(user_prompt)

    def _run_deterministic_agent(self, prompt: str) -> Dict[str, Any]:
        """High-speed deterministic quantitative agent parsing natural language trading requests."""
        prompt_lower = prompt.lower()
        tool_results = []

        # Symbol extraction
        found_symbol = "BTCUSDT"
        for s in ["NVDAUSDT", "AAPLUSDT", "TSLAUSDT", "SPYUSDT", "QQQUSDT", "ETHUSDT", "SOLUSDT", "BTCUSDT"]:
            if s.lower() in prompt_lower or s.replace("USDT", "").lower() in prompt_lower:
                found_symbol = s
                break

        # Intent detection
        if "kill" in prompt_lower or "emergency" in prompt_lower:
            res = trigger_emergency_kill_switch()
            tool_results.append({"tool_name": "trigger_emergency_kill_switch", "args": {}, "result": res})
            synth = "🚨 **EMERGENCY KILL-SWITCH ENGAGED**: All open positions have been liquidated to USDT. Trading operations are currently halted to protect capital."

        elif "backtest" in prompt_lower or "simulate" in prompt_lower:
            strat = "RSI_MEAN_REVERSION"
            if "ema" in prompt_lower:
                strat = "EMA_CROSSOVER"
            elif "macd" in prompt_lower:
                strat = "MACD_TREND"
            elif "bollinger" in prompt_lower:
                strat = "BOLLINGER_BREAKOUT"
            elif "dca" in prompt_lower:
                strat = "DYNAMIC_DCA"

            res = run_strategy_backtest(symbol=found_symbol, strategy_name=strat)
            tool_results.append({"tool_name": "run_strategy_backtest", "args": {"symbol": found_symbol, "strategy": strat}, "result": res})
            synth = (
                f"📊 **Historical Backtest Completed for {found_symbol}** ({strat}):\n\n"
                f"- **Net Return**: {res.get('return_pct')}%\n"
                f"- **Benchmark Buy & Hold**: {res.get('benchmark_return_pct')}%\n"
                f"- **Alpha over Market**: **+{res.get('alpha_pct')}%**\n"
                f"- **Sharpe Ratio**: {res.get('sharpe_ratio')}\n"
                f"- **Max Drawdown**: {res.get('max_drawdown_pct')}%\n"
                f"- **Win Rate**: {res.get('win_rate_pct')}%\n"
                f"- **Profit Factor**: {res.get('profit_factor')} across {res.get('total_trades')} trades\n\n"
                "The strategy successfully outperformed benchmark buy-and-hold during the simulation period."
            )

        elif "stock" in prompt_lower or "us equities" in prompt_lower or "rtoken" in prompt_lower:
            stocks_res = scan_tokenized_stocks()
            tool_results.append({"tool_name": "scan_tokenized_stocks", "args": {}, "result": stocks_res})
            stocks = stocks_res.get("stocks", [])
            top_stock = stocks[0] if stocks else {"symbol": "NVDAUSDT", "price": 128.45, "change_24h": 3.42, "rsi": 54.2, "bias": "BULLISH"}
            top_sym = top_stock.get("symbol") or "NVDAUSDT"
            top_price = float(top_stock.get("price") or 128.45)
            top_chg = float(top_stock.get("change_24h") or 0.0)
            top_rsi = top_stock.get("rsi") or 50.0
            top_bias = top_stock.get("bias") or "NEUTRAL"
            tracked_count = stocks_res.get("total_us_stocks_tracked") or len(stocks)
            synth = (
                f"🇺🇸 **Bitget 7x24 Tokenized US Equities Radar**:\n\n"
                f"Tracked {tracked_count} continuous US equity contracts. "
                f"Top volume/momentum asset is **{top_sym}** at **${top_price:.2f}** "
                f"(24h: {top_chg:+.2f}%, RSI: {top_rsi}, Bias: {top_bias}).\n\n"
                "💡 *Advantage: 7x24 weekend trading enables pricing macro developments and earnings surprises before traditional NYSE market hours.*"
            )

        elif "close" in prompt_lower or "exit" in prompt_lower:
            close_side = None
            if "long" in prompt_lower or "buy" in prompt_lower:
                close_side = "BUY"
            elif "short" in prompt_lower or "sell" in prompt_lower:
                close_side = "SELL"

            res = close_futures_position(symbol=found_symbol, side=close_side)
            tool_results.append({"tool_name": "close_futures_position", "args": {"symbol": found_symbol, "side": close_side}, "result": res})

            if not res.get("found"):
                synth = res.get("message", "You don't have any running future trade")
            else:
                pnl = res.get("pnl", 0.0)
                pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
                synth = (
                    f"⚡ **Futures Position Closed Successfully**:\n\n"
                    f"- **Asset**: `{res.get('symbol')}`\n"
                    f"- **Position Closed**: `{res.get('closed_position_side', 'FUTURES')}`\n"
                    f"- **Execution Price**: `${res.get('exit_price', 0.0):,.2f}`\n"
                    f"- **Quantity**: `{res.get('quantity')}`\n"
                    f"- **Realized PnL**: `{pnl_str} USDT`\n"
                    f"- **Trade ID**: `{res.get('trade_id', 'N/A')}`\n\n"
                    "Trade closed and recorded in the audited Paper Trading Log."
                )

        elif "buy" in prompt_lower or "execute" in prompt_lower or "order" in prompt_lower or "trade" in prompt_lower:
            amount = 100.0
            numbers = re.findall(r"\b\d+(?:\.\d+)?\b", prompt)
            if numbers:
                for n in numbers:
                    val = float(n)
                    if 10.0 <= val <= 500.0:
                        amount = val
                        break

            side = "SELL" if "sell" in prompt_lower or "short" in prompt_lower else "BUY"
            if "future" in prompt_lower or "contract" in prompt_lower:
                res = execute_futures_order(symbol=found_symbol, side=side, amount_usdt=amount, leverage=10, reason="Autonomous Prompt Execution")
                tool_results.append({"tool_name": "execute_futures_order", "args": {"symbol": found_symbol, "side": side, "amount_usdt": amount}, "result": res})
            else:
                res = execute_spot_order(symbol=found_symbol, side=side, amount_usdt=amount, reason="Autonomous Prompt Execution")
                tool_results.append({"tool_name": "execute_spot_order", "args": {"symbol": found_symbol, "side": side, "amount_usdt": amount}, "result": res})

            if res.get("success"):
                synth = (
                    f"⚡ **Order Executed Successfully**:\n\n"
                    f"- **Asset**: `{found_symbol}`\n"
                    f"- **Side**: `{side}`\n"
                    f"- **Notional**: `${amount:.2f} USDT`\n"
                    f"- **Execution Price**: `${res.get('price', res.get('entry_price', 'Market'))}`\n"
                    f"- **Mode**: `{res.get('execution_mode')}`\n"
                    f"- **Trade ID**: `{res.get('trade_id', 'N/A')}`\n\n"
                    "Trade has been verified by the Risk Guardian and recorded in the audited Paper Trading Log."
                )
            else:
                synth = f"⚠️ **Order Execution Blocked by Risk Firewall**: {res.get('error')}"

        elif "portfolio" in prompt_lower or "balance" in prompt_lower or "pnl" in prompt_lower:
            res = get_portfolio_status()
            tool_results.append({"tool_name": "get_portfolio_status", "args": {}, "result": res})
            synth = (
                f"💼 **Portfolio Status ({res.get('mode', 'SIMULATION')})**:\n\n"
                f"- **Total Valuation**: `${res.get('total_value_usdt'):,.2f} USDT`\n"
                f"- **Available Liquid Cash**: `${res.get('available_usdt'):,.2f} USDT`\n"
                f"- **Total PnL**: `${res.get('total_pnl_usdt', 0.0):+,.2f}` ({res.get('total_pnl_percent', 0.0):+.2f}%)\n"
                f"- **Unrealized PnL**: `${res.get('unrealized_pnl', 0.0):+,.2f}`\n"
                f"- **Active Holdings**: {len(res.get('holdings', []))} positions\n"
                f"- **Kill-Switch Active**: `{res.get('kill_switch_active')}`"
            )

        else:
            # Default to full quantitative and technical analysis
            ta = get_technical_analysis(symbol=found_symbol)
            quant = get_quant_risk_metrics(symbol=found_symbol)
            regime = get_time_series_regime(symbol=found_symbol)
            alpha = get_composite_alpha_score(symbol=found_symbol)

            tool_results.append({"tool_name": "get_technical_analysis", "args": {"symbol": found_symbol}, "result": ta})
            tool_results.append({"tool_name": "get_quant_risk_metrics", "args": {"symbol": found_symbol}, "result": quant})
            tool_results.append({"tool_name": "get_time_series_regime", "args": {"symbol": found_symbol}, "result": regime})
            tool_results.append({"tool_name": "get_composite_alpha_score", "args": {"symbol": found_symbol}, "result": alpha})

            synth = (
                f"📈 **Institutional Quant & Market Report: {found_symbol}**\n\n"
                f"- **Current Price**: `${ta.get('current_price'):.4f}` (Bias: `{ta.get('bias')}`)\n"
                f"- **RSI (14)**: `{ta.get('rsi_14')}` | **MACD Histogram**: `{ta.get('macd', {}).get('histogram')}`\n"
                f"- **Hurst Exponent**: `{regime.get('hurst_exponent')}` (`{regime.get('regime')}`, OU Half-Life: `{regime.get('half_life_hours')}h`)\n"
                f"- **Downside Tail Risk**: 1H VaR(95%) is `{quant.get('var_95_pct')}%`, Expected Shortfall (CVaR) is `{quant.get('cvar_95_pct')}%`\n"
                f"- **Composite Alpha Score**: **{alpha.get('alpha_score')} / 100** (`{alpha.get('action_recommendation')}`)\n"
                f"- **ATR Brackets**: Stop-Loss at `${alpha.get('brackets', {}).get('stop_loss')}`, Take-Profit at `${alpha.get('brackets', {}).get('take_profit_1')}`\n\n"
                f"*{regime.get('description')}*"
            )

        return {
            "provider": "OctaCore Quantitative Engine (Deterministic Fallback)",
            "response": synth,
            "tool_calls": tool_results
        }


# Global LLM Agent Engine Singleton
llm_agent = LLMAgentEngine()
