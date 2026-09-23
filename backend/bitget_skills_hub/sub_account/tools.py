"""Sub-Account operations, API health diagnostics, and universal fund transfers."""

from typing import Any, Dict
from src.bitget.sub_account import sub_account_manager


def get_sub_account_status() -> Dict[str, Any]:
    """Retrieve sub-account health, isolation boundaries, and API permission telemetry."""
    return sub_account_manager.get_sub_account_status()


def toggle_uid_privacy() -> Dict[str, Any]:
    """Toggle UID privacy masking between masked and clear text."""
    masked = sub_account_manager.toggle_privacy_mask()
    return {
        "privacy_masked": masked,
        "display_uid": sub_account_manager.get_display_uid(),
        "message": f"UID privacy masking {'ENABLED' if masked else 'DISABLED'}"
    }


def transfer_sub_account_funds(
    from_type: str,  # SPOT | MIX_USDT
    to_type: str,    # MIX_USDT | SPOT
    amount_usdt: float
) -> Dict[str, Any]:
    """Transfer liquidity between Spot and Mix Futures within the sub-account (zero fee)."""
    return sub_account_manager.transfer_internal_funds(
        from_type=from_type,
        to_type=to_type,
        amount_usdt=amount_usdt
    )
