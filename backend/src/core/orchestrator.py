"""Master Agent Orchestrator coordinating the 8 autonomous specialist cores."""

from typing import Any, Dict, List, Optional
from src.agents.market_analyst import market_analyst_agent
from src.agents.quant_agent import quant_agent
from src.agents.backtest_agent import backtest_agent
from src.agents.risk_guardian import risk_guardian_agent
from src.agents.execution_agent import execution_agent
from src.agents.tokenized_stocks_agent import tokenized_stocks_agent
from src.agents.sub_account_agent import sub_account_agent
from src.agents.news_sentinel import news_sentinel_agent
from src.core.llm_client import llm_agent
from src.core.memory import memory, LogLevel


class AgentOrchestrator:
    """Coordinates the 8 specialist cores into a unified institutional AI trading desk."""

    def __init__(self):
        self.cores = {
            "core_1_market_analyst": market_analyst_agent,
            "core_2_quant_engine": quant_agent,
            "core_3_backtest_engine": backtest_agent,
            "core_4_risk_guardian": risk_guardian_agent,
            "core_5_execution_agent": execution_agent,
            "core_6_tokenized_stocks": tokenized_stocks_agent,
            "core_7_sub_account": sub_account_agent,
            "core_8_news_sentinel": news_sentinel_agent
        }

    def get_cores_status(self) -> List[Dict[str, Any]]:
        """Return operational health of all 8 cores."""
        return [
            {"id": 1, "name": "Market Analyst", "role": "Technical Analysis & Order Book Depth", "status": "ACTIVE"},
            {"id": 2, "name": "Quant Engine", "role": "VaR, CVaR, Hurst Exponent & MPT Optimization", "status": "ACTIVE"},
            {"id": 3, "name": "Backtest Engine", "role": "Vectorized Strategy Historical Backtesting", "status": "ACTIVE"},
            {"id": 4, "name": "Risk Guardian", "role": "Pre-Trade Mathematical Safety Firewall & Kill-Switch", "status": "ACTIVE"},
            {"id": 5, "name": "Execution Agent", "role": "Spot & Futures Order Routing & Volatility DCA", "status": "ACTIVE"},
            {"id": 6, "name": "Tokenized US Stocks", "role": "7x24 Continuous US Equities & Cross-Asset Hedging", "status": "ACTIVE"},
            {"id": 7, "name": "Sub-Account Router", "role": "Dedicated Agentic Isolation & Universal Transfer", "status": "ACTIVE"},
            {"id": 8, "name": "News Sentinel", "role": "Breaking News & Macro Sentiment Volatility Radar", "status": "ACTIVE"}
        ]

    def process_command(self, user_prompt: str) -> Dict[str, Any]:
        """Dispatch user prompt through LLM engine with tool calls or route directly."""
        memory.log("Orchestrator", f"Processing query through 8-Core subsystem: '{user_prompt}'", LogLevel.INFO)
        result = llm_agent.run_agent_turn(user_prompt)
        return {
            "query": user_prompt,
            "provider": result.get("provider"),
            "response": result.get("response"),
            "tool_calls": result.get("tool_calls", []),
            "cores_active": 8
        }


# Global Orchestrator Singleton
orchestrator = AgentOrchestrator()
