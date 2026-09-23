"""Core 7: Sub-Account Router Agent - Isolation, Permissions, and Universal Transfer."""

from typing import Any, Dict
from bitget_skills_hub.sub_account.tools import (
    get_sub_account_status,
    toggle_uid_privacy,
    transfer_sub_account_funds
)
from src.core.memory import memory, LogLevel


class SubAccountRouterAgent:
    """Specialist sub-agent for managing isolated sub-account routing, privacy masking, and capital moves."""

    def __init__(self):
        self.name = "Core 7 - Sub-Account Router"

    def get_status(self) -> Dict[str, Any]:
        return get_sub_account_status()

    def toggle_privacy(self) -> Dict[str, Any]:
        return toggle_uid_privacy()

    def transfer(self, from_type: str, to_type: str, amount_usdt: float) -> Dict[str, Any]:
        return transfer_sub_account_funds(from_type, to_type, amount_usdt)


sub_account_agent = SubAccountRouterAgent()
