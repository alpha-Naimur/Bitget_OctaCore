"""Core 8: News Sentinel Agent - Breaking News, Macro Alerts, and Volatility Radar."""

from typing import Any, Dict
from bitget_skills_hub.news_sentinel.tools import (
    fetch_breaking_crypto_news,
    audit_news_circuit_breaker
)
from bitget_skills_hub.bitget_signal.tools import get_news_briefing
from src.core.memory import memory, LogLevel


class NewsSentinelAgent:
    """Specialist sub-agent monitoring breaking headlines, macro catalysts, and volatility events."""

    def __init__(self):
        self.name = "Core 8 - News Sentinel"

    def fetch_latest_news(self) -> Dict[str, Any]:
        memory.log(self.name, "Scanning breaking news and market narrative feeds", LogLevel.INFO)
        news = fetch_breaking_crypto_news()
        breaker = audit_news_circuit_breaker()
        return {
            "core": self.name,
            "breaking_news": news,
            "circuit_breaker": breaker
        }

    def get_macro_briefing(self, keyword: str = "") -> Dict[str, Any]:
        return get_news_briefing(keyword=keyword)


news_sentinel_agent = NewsSentinelAgent()
