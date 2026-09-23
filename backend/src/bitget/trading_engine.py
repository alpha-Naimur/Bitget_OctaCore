"""Unified trading engine routing between SIMULATION, TESTNET, MAINNET, and SUB_ACCOUNT."""

from typing import Any, Dict, List, Optional
from src.bitget.client import bitget_client
from src.bitget.market_data import market_data, TOKENIZED_US_STOCKS
from src.bitget.simulator import simulator
from src.bitget.sub_account import sub_account_manager
from src.core.config import settings, ExecutionMode
from src.core.memory import memory, LogLevel


class TradingEngine:
    """Unified trading execution engine routing orders to Simulator or Live Bitget UTA APIs."""

    def __init__(self, mode: Optional[ExecutionMode] = None):
        self.mode = mode or settings.EXECUTION_MODE
        self.kill_switch_active: bool = False

    def set_execution_mode(self, mode: ExecutionMode):
        """Switch execution mode dynamically."""
        self.mode = mode
        bitget_client.configure(mode=mode)
        memory.log("TradingEngine", f"Switched execution mode to {mode.value}", LogLevel.INFO)

    def get_execution_status(self) -> Dict[str, Any]:
        """Return operational status and connectivity."""
        has_keys = bitget_client.has_valid_credentials()
        is_sub = self.mode == ExecutionMode.SUB_ACCOUNT
        sub_info = sub_account_manager.get_sub_account_status()

        return {
            "mode": self.mode.value,
            "is_live": self.mode in (ExecutionMode.TESTNET, ExecutionMode.MAINNET, ExecutionMode.SUB_ACCOUNT),
            "is_sub_account": is_sub,
            "has_api_credentials": has_keys,
            "base_url": bitget_client.base_url,
            "kill_switch_active": self.kill_switch_active or simulator.kill_switch_triggered,
            "sub_account_info": sub_info
        }

    def get_portfolio(self) -> Dict[str, Any]:
        """Fetch current portfolio status depending on execution mode."""
        if self.mode == ExecutionMode.SIMULATION or not bitget_client.has_valid_credentials():
            summary = simulator.get_portfolio_summary()
            summary["mode"] = self.mode.value
            return summary

        # Live Bitget Query (Spot & Futures)
        spot_res = bitget_client.get_spot_account_assets()
        fut_res = bitget_client.get_futures_account()

        if spot_res.get("success"):
            holdings = []
            total_val = 0.0
            avail_usdt = 0.0

            # If equity metadata is present from UTA v3
            equity_meta = spot_res.get("equity", {})
            if equity_meta:
                try:
                    total_val = float(equity_meta.get("usdtEquity") or equity_meta.get("accountEquity") or 0.0)
                except (ValueError, TypeError):
                    total_val = 0.0

            for asset_item in spot_res.get("data", []):
                coin = asset_item.get("coin", "").upper()
                avail = float(asset_item.get("available") or 0.0)
                frozen = float(asset_item.get("frozen") or 0.0)
                total_qty = avail + frozen

                if total_qty <= 0.0001:
                    continue

                if coin == "USDT":
                    avail_usdt += avail
                    price = 1.0
                    val = total_qty
                else:
                    sym = f"{coin}USDT"
                    price = market_data.get_ticker_price(sym) or 0.0
                    val = total_qty * price

                if total_val == 0.0:
                    total_val += val

                holdings.append({
                    "type": "UTA" if getattr(bitget_client, "is_unified_account", False) else "SPOT",
                    "asset": coin,
                    "symbol": f"{coin}USDT" if coin != "USDT" else "USDT",
                    "quantity": round(total_qty, 6),
                    "price_usdt": round(price, 4),
                    "value_usdt": round(val, 2),
                    "allocation_pct": 0.0
                })

            if total_val > 0:
                for h in holdings:
                    h["allocation_pct"] = round((h["value_usdt"] / total_val) * 100, 1)

            acct_type = "Unified Trading Account (UTA v3)" if getattr(bitget_client, "is_unified_account", False) else "Classic Account"
            return {
                "mode": self.mode.value,
                "total_value_usdt": round(total_val, 2),
                "available_usdt": round(avail_usdt, 2),
                "holdings": holdings,
                "kill_switch_active": self.kill_switch_active,
                "account_mode": "UTA_V3" if getattr(bitget_client, "is_unified_account", False) else "CLASSIC",
                "notice": f"Live connected to Bitget {acct_type} ({self.mode.value})."
            }

        # Fallback to simulation if live query fails
        summary = simulator.get_portfolio_summary()
        summary["mode"] = self.mode.value
        summary["notice"] = f"Warning: Failed to reach live {self.mode.value}. Showing simulated portfolio."
        return summary

    def execute_spot_order(
        self,
        symbol: str,
        side: str,
        amount_usdt: Optional[float] = None,
        quantity: Optional[float] = None,
        reason: str = "Market Execution",
        agent_core: str = "Core 5 - Execution Agent"
    ) -> Dict[str, Any]:
        """Dispatch spot order to Simulator or Live Bitget API."""
        symbol = symbol.upper()
        side = side.upper()

        if (self.kill_switch_active or simulator.kill_switch_triggered) and "KILL-SWITCH" not in reason:
            return {"success": False, "error": "Emergency Kill-Switch is active. Orders rejected."}

        # Simulation mode or credentials missing
        if self.mode == ExecutionMode.SIMULATION or not bitget_client.has_valid_credentials():
            return simulator.execute_spot_order(
                symbol=symbol,
                side=side,
                amount_usdt=amount_usdt,
                quantity=quantity,
                reason=reason,
                agent_core=agent_core
            )

        # Live Execution
        current_price = market_data.get_ticker_price(symbol) or 1.0
        size_str = str(quantity) if quantity else str(round(amount_usdt / current_price, 4))
        res = bitget_client.place_spot_order(symbol, side, order_type="market", size=size_str)
        
        if res.get("success"):
            memory.log("TradingEngine", f"Live {side} order placed on {symbol} (size: {size_str})", LogLevel.SUCCESS)
            return {
                "success": True,
                "order_id": res.get("data", {}).get("orderId"),
                "symbol": symbol,
                "side": side,
                "execution_mode": self.mode.value
            }
        return res

    def execute_futures_order(
        self,
        symbol: str,
        side: str,
        amount_usdt: float,
        leverage: int = 10,
        reason: str = "Futures Contract Order",
        agent_core: str = "Core 6 - Tokenized US Stocks Agent"
    ) -> Dict[str, Any]:
        """Dispatch futures contract order (Crypto or Tokenized US Stocks)."""
        symbol = symbol.upper()
        side = side.upper()

        if (self.kill_switch_active or simulator.kill_switch_triggered) and "KILL-SWITCH" not in reason:
            return {"success": False, "error": "Emergency Kill-Switch is active. Futures rejected."}

        if self.mode == ExecutionMode.SIMULATION or not bitget_client.has_valid_credentials():
            return simulator.execute_futures_order(
                symbol=symbol,
                side=side,
                amount_usdt=amount_usdt,
                leverage=leverage,
                reason=reason,
                agent_core=agent_core
            )

        # Live Execution
        current_price = market_data.get_ticker_price(symbol) or 100.0
        size = str(round(amount_usdt / current_price, 3))
        # Ensure leverage is set
        bitget_client.set_futures_leverage(symbol, leverage)
        res = bitget_client.place_futures_order(symbol, side, order_type="market", size=size)
        return res

    def execute_smart_dca(
        self,
        symbol: str,
        base_dca_amount_usdt: float = 100.0,
        agent_core: str = "Core 5 - Execution Agent"
    ) -> Dict[str, Any]:
        """Execute Volatility-Scaled Smart DCA: increases allocation on deep RSI oversold dips."""
        symbol = symbol.upper()
        ta = market_data.compute_technical_analysis(symbol)
        rsi = ta.get("rsi_14", 50.0)

        # Dynamic DCA Volatility & RSI Multiplier
        if rsi < 25.0:
            scale_factor = 2.0  # Deep oversold dip
            dca_reason = f"Smart DCA Extreme Dip: RSI {rsi:.1f} (2.0x Allocation)"
        elif rsi < 35.0:
            scale_factor = 1.5
            dca_reason = f"Smart DCA Oversold Dip: RSI {rsi:.1f} (1.5x Allocation)"
        elif rsi < 45.0:
            scale_factor = 1.0
            dca_reason = f"Smart DCA Mild Dip: RSI {rsi:.1f} (1.0x Allocation)"
        elif rsi > 70.0:
            scale_factor = 0.5  # Trim accumulation at overbought
            dca_reason = f"Smart DCA Overbought Defensiveness: RSI {rsi:.1f} (0.5x Allocation)"
        else:
            scale_factor = 1.0
            dca_reason = f"Smart DCA Standard Cycle: RSI {rsi:.1f}"

        effective_amount = round(base_dca_amount_usdt * scale_factor, 2)
        exec_res = self.execute_spot_order(
            symbol=symbol,
            side="BUY",
            amount_usdt=effective_amount,
            reason=dca_reason,
            agent_core=agent_core
        )

        return {
            "smart_dca_executed": exec_res.get("success", False),
            "symbol": symbol,
            "base_amount_usdt": base_dca_amount_usdt,
            "scale_factor": scale_factor,
            "effective_amount_usdt": effective_amount,
            "rsi": rsi,
            "strategy_reason": dca_reason,
            "execution_details": exec_res
        }

    def trigger_kill_switch(self) -> Dict[str, Any]:
        """Engage global emergency kill-switch."""
        self.kill_switch_active = True
        return simulator.trigger_emergency_kill_switch()

    def deactivate_kill_switch(self) -> Dict[str, Any]:
        """Lift emergency kill switch."""
        self.kill_switch_active = False
        return simulator.deactivate_kill_switch()


# Global Trading Engine Singleton
trading_engine = TradingEngine()
