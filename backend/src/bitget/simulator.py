"""High-fidelity Paper Trading Simulator with order book fill, PnL, and audit persistence."""

import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from src.bitget.market_data import market_data
from src.core.config import settings
from src.core.memory import memory, TradeRecord, LogLevel


class PaperTradingSimulator:
    """Simulates spot & mix futures execution with fee schedules, slippage, and portfolio PnL."""

    def __init__(self, initial_usdt: float = 10000.0, fee_rate: float = 0.0006):
        self._lock = threading.RLock()
        self.initial_usdt = initial_usdt
        self.fee_rate = fee_rate
        self.balances: Dict[str, float] = {"USDT": initial_usdt}
        self.positions: Dict[str, Dict[str, Any]] = {}  # Spot positions
        self.futures_positions: Dict[str, Dict[str, Any]] = {}  # Mix futures positions
        self.futures_leverage: Dict[str, int] = {}
        self.futures_margin_balance: float = settings.SIMULATOR_FUTURES_MARGIN_USDT
        self.realized_pnl: float = 0.0
        self.kill_switch_triggered: bool = False

    def reset(self):
        """Reset simulator back to initial capital."""
        with self._lock:
            self.balances = {"USDT": self.initial_usdt}
            self.positions.clear()
            self.futures_positions.clear()
            self.futures_leverage.clear()
            self.futures_margin_balance = settings.SIMULATOR_FUTURES_MARGIN_USDT
            self.realized_pnl = 0.0
            self.kill_switch_triggered = False
            memory.log("Simulator", "Paper trading portfolio reset to initial state.", LogLevel.INFO)

    def get_balance(self, asset: str = "USDT") -> float:
        with self._lock:
            return self.balances.get(asset.upper(), 0.0)

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Calculate total portfolio valuation, unrealized PnL, and asset allocations."""
        with self._lock:
            balances_copy = dict(self.balances)
            positions_copy = {k: dict(v) for k, v in self.positions.items()}
            fut_positions_copy = {k: dict(v) for k, v in self.futures_positions.items()}
            realized_pnl = self.realized_pnl
            kill_switch = self.kill_switch_triggered

        total_value_usdt = balances_copy.get("USDT", 0.0) + self.futures_margin_balance
        breakdown = []
        unrealized_pnl = 0.0

        # 1. Spot Holdings
        for asset, qty in balances_copy.items():
            if asset == "USDT":
                continue
            if qty <= 0.000001:
                continue

            symbol = f"{asset}USDT"
            current_price = market_data.get_ticker_price(symbol) or 0.0
            val = qty * current_price
            total_value_usdt += val

            pos = positions_copy.get(symbol, {})
            avg_entry = pos.get("avg_entry_price", current_price)
            pos_pnl = (current_price - avg_entry) * qty if avg_entry > 0 else 0.0
            unrealized_pnl += pos_pnl

            breakdown.append({
                "type": "SPOT",
                "asset": asset,
                "symbol": symbol,
                "quantity": round(qty, 6),
                "price_usdt": round(current_price, 4),
                "value_usdt": round(val, 2),
                "avg_entry_price": round(avg_entry, 4),
                "unrealized_pnl": round(pos_pnl, 2),
                "allocation_pct": 0.0
            })

        # 2. Futures Positions (Crypto & 7x24 Tokenized US Stocks)
        for sym, f_pos in fut_positions_copy.items():
            qty = f_pos.get("quantity", 0.0)
            if abs(qty) <= 0.000001:
                continue

            current_price = market_data.get_ticker_price(sym) or f_pos.get("entry_price", 0.0)
            entry_price = f_pos.get("entry_price", current_price)
            side = f_pos.get("side", "BUY")
            leverage = f_pos.get("leverage", 10)
            margin = f_pos.get("margin", 0.0)

            if side == "BUY":
                pnl = (current_price - entry_price) * qty
            else:
                pnl = (entry_price - current_price) * qty

            unrealized_pnl += pnl
            total_value_usdt += pnl

            breakdown.append({
                "type": "FUTURES",
                "asset": sym.replace("USDT", ""),
                "symbol": sym,
                "side": side,
                "quantity": round(qty, 4),
                "leverage": leverage,
                "margin_usdt": round(margin, 2),
                "price_usdt": round(current_price, 4),
                "value_usdt": round(qty * current_price, 2),
                "avg_entry_price": round(entry_price, 4),
                "unrealized_pnl": round(pnl, 2),
                "allocation_pct": 0.0
            })

        for item in breakdown:
            item["allocation_pct"] = round((item["value_usdt"] / total_value_usdt * 100), 2) if total_value_usdt > 0 else 0.0

        total_pnl = (total_value_usdt - self.initial_usdt)
        total_pnl_pct = (total_pnl / self.initial_usdt) * 100 if self.initial_usdt > 0 else 0.0

        return {
            "total_value_usdt": round(total_value_usdt, 2),
            "initial_capital_usdt": self.initial_usdt,
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl_usdt": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_pct, 2),
            "available_usdt": round(balances_copy.get("USDT", 0.0), 2),
            "futures_margin_balance": round(self.futures_margin_balance, 2),
            "holdings": breakdown,
            "kill_switch_active": kill_switch
        }

    def execute_spot_order(
        self,
        symbol: str,
        side: str,
        amount_usdt: Optional[float] = None,
        quantity: Optional[float] = None,
        reason: str = "Algorithmic Spot",
        agent_core: str = "Core 5 - Execution Agent"
    ) -> Dict[str, Any]:
        """Execute simulated spot order with slippage and fee deduction."""
        symbol = symbol.upper()
        side = side.upper()
        asset = symbol.replace("USDT", "")

        with self._lock:
            if self.kill_switch_triggered and "KILL-SWITCH" not in reason:
                return {"success": False, "error": "Kill switch is active. Orders rejected."}

            current_price = market_data.get_ticker_price(symbol)
            if not current_price or current_price <= 0:
                current_price = 100.0  # Fallback baseline

            # Realistic slippage (0.05% ~ 0.15%)
            slippage = 0.0008 if side == "BUY" else -0.0008
            exec_price = current_price * (1.0 + slippage)

            if side == "BUY":
                if amount_usdt is None:
                    if quantity is not None:
                        amount_usdt = quantity * exec_price
                    else:
                        return {"success": False, "error": "Either amount_usdt or quantity must be provided."}

                fee = amount_usdt * self.fee_rate
                total_cost = amount_usdt + fee

                if self.balances.get("USDT", 0.0) < total_cost:
                    return {
                        "success": False,
                        "error": f"Insufficient USDT. Required: ${total_cost:.2f}, Available: ${self.balances.get('USDT', 0.0):.2f}"
                    }

                qty = amount_usdt / exec_price
                self.balances["USDT"] -= total_cost
                self.balances[asset] = self.balances.get(asset, 0.0) + qty

                # Update position avg price
                existing_pos = self.positions.get(symbol, {"quantity": 0.0, "avg_entry_price": 0.0})
                total_qty = existing_pos["quantity"] + qty
                weighted_cost = (existing_pos["quantity"] * existing_pos["avg_entry_price"]) + (qty * exec_price)
                avg_price = weighted_cost / total_qty if total_qty > 0 else exec_price

                self.positions[symbol] = {
                    "quantity": total_qty,
                    "avg_entry_price": avg_price
                }

                trade_id = str(uuid.uuid4())[:8]
                record = TradeRecord(
                    id=trade_id,
                    symbol=symbol,
                    side="BUY",
                    order_type="MARKET",
                    amount_usdt=round(amount_usdt, 2),
                    price=round(exec_price, 4),
                    quantity=round(qty, 6),
                    fee=round(fee, 4),
                    pnl=0.0,
                    status="FILLED",
                    reason=reason,
                    agent_core=agent_core,
                    execution_mode="SIMULATION"
                )
                memory.record_trade(record)
                memory.log("Simulator", f"Executed SPOT BUY {qty:.4f} {asset} at ${exec_price:.4f} (${amount_usdt:.2f})", LogLevel.SUCCESS)

                return {
                    "success": True,
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "side": "BUY",
                    "price": round(exec_price, 4),
                    "quantity": round(qty, 6),
                    "amount_usdt": round(amount_usdt, 2),
                    "fee": round(fee, 4),
                    "execution_mode": "SIMULATION"
                }

            elif side == "SELL":
                current_qty = self.balances.get(asset, 0.0)
                if quantity is None:
                    if amount_usdt is not None:
                        quantity = amount_usdt / exec_price
                    else:
                        quantity = current_qty

                if current_qty < quantity or quantity <= 0:
                    return {
                        "success": False,
                        "error": f"Insufficient {asset}. Required: {quantity:.6f}, Available: {current_qty:.6f}"
                    }

                gross_return = quantity * exec_price
                fee = gross_return * self.fee_rate
                net_usdt = gross_return - fee

                pos = self.positions.get(symbol, {"avg_entry_price": exec_price})
                pnl = (exec_price - pos["avg_entry_price"]) * quantity
                self.realized_pnl += pnl

                self.balances[asset] -= quantity
                self.balances["USDT"] += net_usdt

                if self.balances[asset] <= 0.000001:
                    self.positions.pop(symbol, None)

                trade_id = str(uuid.uuid4())[:8]
                record = TradeRecord(
                    id=trade_id,
                    symbol=symbol,
                    side="SELL",
                    order_type="MARKET",
                    amount_usdt=round(gross_return, 2),
                    price=round(exec_price, 4),
                    quantity=round(quantity, 6),
                    fee=round(fee, 4),
                    pnl=round(pnl, 2),
                    status="FILLED",
                    reason=reason,
                    agent_core=agent_core,
                    execution_mode="SIMULATION"
                )
                memory.record_trade(record)
                memory.log("Simulator", f"Executed SPOT SELL {quantity:.4f} {asset} at ${exec_price:.4f} (PnL: ${pnl:.2f})", LogLevel.SUCCESS)

                return {
                    "success": True,
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "side": "SELL",
                    "price": round(exec_price, 4),
                    "quantity": round(quantity, 6),
                    "amount_usdt": round(gross_return, 2),
                    "pnl": round(pnl, 2),
                    "fee": round(fee, 4),
                    "execution_mode": "SIMULATION"
                }

    def execute_futures_order(
        self,
        symbol: str,
        side: str,  # BUY (Long) | SELL (Short)
        amount_usdt: float,
        leverage: int = 10,
        reason: str = "Mix Futures Order",
        agent_core: str = "Core 6 - Tokenized US Stocks Agent"
    ) -> Dict[str, Any]:
        """Execute simulated futures contract order (Supports Crypto and 7x24 Tokenized US Equities)."""
        symbol = symbol.upper()
        side = side.upper()

        with self._lock:
            if self.kill_switch_triggered and "KILL-SWITCH" not in reason:
                return {"success": False, "error": "Kill switch active. Futures execution blocked."}

            current_price = market_data.get_ticker_price(symbol) or 100.0
            margin_req = amount_usdt / leverage
            fee = amount_usdt * 0.0006

            existing_pos = self.futures_positions.get(symbol)
            qty = amount_usdt / current_price

            # If an existing position is open and new order is opposite side -> Close / Reduce position
            if existing_pos and existing_pos["side"] != side:
                close_qty = min(existing_pos["quantity"], qty)
                entry_price = existing_pos["entry_price"]

                if existing_pos["side"] == "BUY":
                    pnl = (current_price - entry_price) * close_qty
                else:
                    pnl = (entry_price - current_price) * close_qty

                fraction = close_qty / existing_pos["quantity"] if existing_pos["quantity"] > 0 else 1.0
                released_margin = existing_pos["margin"] * fraction

                self.realized_pnl += pnl
                self.futures_margin_balance += (released_margin + pnl - fee)

                remaining_qty = existing_pos["quantity"] - close_qty
                if remaining_qty <= 0.00001:
                    self.futures_positions.pop(symbol, None)
                    self.futures_leverage.pop(symbol, None)
                else:
                    existing_pos["quantity"] = remaining_qty
                    existing_pos["margin"] = existing_pos["margin"] - released_margin

                trade_id = str(uuid.uuid4())[:8]
                record = TradeRecord(
                    id=trade_id,
                    symbol=symbol,
                    side=f"FUTURES_CLOSE_{existing_pos['side']}",
                    order_type="MARKET",
                    amount_usdt=round(close_qty * current_price, 2),
                    price=round(current_price, 4),
                    quantity=round(close_qty, 4),
                    fee=round(fee, 4),
                    pnl=round(pnl, 2),
                    status="FILLED",
                    reason=reason,
                    agent_core=agent_core,
                    execution_mode="SIMULATION"
                )
                memory.record_trade(record)
                memory.log("Simulator", f"Closed/Reduced Futures {existing_pos['side']} {symbol}, closed qty: {close_qty:.4f}, PnL: ${pnl:.2f}", LogLevel.SUCCESS)

                return {
                    "success": True,
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "side": f"CLOSE_{existing_pos['side']}",
                    "leverage": existing_pos["leverage"],
                    "notional_usdt": round(close_qty * current_price, 2),
                    "pnl": round(pnl, 2),
                    "entry_price": round(entry_price, 4),
                    "exit_price": round(current_price, 4),
                    "quantity": round(close_qty, 4),
                    "execution_mode": "SIMULATION"
                }

            elif existing_pos and existing_pos["side"] == side:
                # Add to existing position (dollar cost averaging / pyramid)
                if self.futures_margin_balance < (margin_req + fee):
                    return {
                        "success": False,
                        "error": f"Insufficient Futures Margin. Required: ${margin_req + fee:.2f}, Available: ${self.futures_margin_balance:.2f}"
                    }
                total_qty = existing_pos["quantity"] + qty
                weighted_entry = ((existing_pos["quantity"] * existing_pos["entry_price"]) + (qty * current_price)) / total_qty
                existing_pos["quantity"] = total_qty
                existing_pos["entry_price"] = weighted_entry
                existing_pos["margin"] += margin_req
                self.futures_margin_balance -= (margin_req + fee)
            else:
                # Open fresh position
                if self.futures_margin_balance < (margin_req + fee):
                    return {
                        "success": False,
                        "error": f"Insufficient Futures Margin. Required: ${margin_req + fee:.2f}, Available: ${self.futures_margin_balance:.2f}"
                    }
                self.futures_margin_balance -= (margin_req + fee)
                self.futures_positions[symbol] = {
                    "symbol": symbol,
                    "side": side,
                    "quantity": qty,
                    "entry_price": current_price,
                    "leverage": leverage,
                    "margin": margin_req
                }
                self.futures_leverage[symbol] = leverage

            trade_id = str(uuid.uuid4())[:8]
            record = TradeRecord(
                id=trade_id,
                symbol=symbol,
                side=f"FUTURES_{side}",
                order_type="MARKET",
                amount_usdt=round(amount_usdt, 2),
                price=round(current_price, 4),
                quantity=round(qty, 4),
                fee=round(fee, 4),
                pnl=0.0,
                status="FILLED",
                reason=reason,
                agent_core=agent_core,
                execution_mode="SIMULATION"
            )
            memory.record_trade(record)
            memory.log("Simulator", f"Opened Futures {side} {symbol} {leverage}x, notional: ${amount_usdt:.2f}", LogLevel.SUCCESS)

            return {
                "success": True,
                "trade_id": trade_id,
                "symbol": symbol,
                "side": side,
                "leverage": leverage,
                "notional_usdt": round(amount_usdt, 2),
                "margin_usdt": round(margin_req, 2),
                "entry_price": round(current_price, 4),
                "quantity": round(qty, 4),
                "execution_mode": "SIMULATION"
            }

    def close_futures_position(
        self,
        symbol: str,
        side: Optional[str] = None,
        reason: str = "Close Futures Position",
        agent_core: str = "Core 5 - Execution Agent"
    ) -> Dict[str, Any]:
        """Close an active futures position (LONG or SHORT).

        If no active position exists for the symbol, returns found=False and
        message="You don't have any running future trade".
        """
        with self._lock:
            sym_clean = symbol.upper().strip()
            # Match symbol in futures_positions
            matched_sym = None
            target_pos = None

            if sym_clean in self.futures_positions:
                matched_sym = sym_clean
                target_pos = self.futures_positions[sym_clean]
            elif f"{sym_clean}USDT" in self.futures_positions:
                matched_sym = f"{sym_clean}USDT"
                target_pos = self.futures_positions[f"{sym_clean}USDT"]
            else:
                for k, v in self.futures_positions.items():
                    if k.replace("USDT", "") == sym_clean.replace("USDT", ""):
                        matched_sym = k
                        target_pos = v
                        break

            if not target_pos or not matched_sym:
                return {
                    "success": False,
                    "found": False,
                    "symbol": symbol,
                    "message": "You don't have any running future trade"
                }

            # Optional side validation (BUY/LONG vs SELL/SHORT)
            pos_side = target_pos.get("side", "BUY")
            if side:
                side_req = "BUY" if side.upper() in ["BUY", "LONG"] else ("SELL" if side.upper() in ["SELL", "SHORT"] else side.upper())
                if pos_side != side_req:
                    return {
                        "success": False,
                        "found": False,
                        "symbol": matched_sym,
                        "message": "You don't have any running future trade"
                    }

            current_price = market_data.get_ticker_price(matched_sym) or target_pos["entry_price"]
            entry_price = target_pos["entry_price"]
            close_qty = target_pos["quantity"]
            leverage = target_pos.get("leverage", 10)
            margin = target_pos.get("margin", 0.0)

            if pos_side == "BUY":
                pnl = (current_price - entry_price) * close_qty
            else:
                pnl = (entry_price - current_price) * close_qty

            notional = close_qty * current_price
            fee = notional * 0.0006

            self.realized_pnl += pnl
            self.futures_margin_balance += (margin + pnl - fee)

            self.futures_positions.pop(matched_sym, None)
            self.futures_leverage.pop(matched_sym, None)

            trade_id = str(uuid.uuid4())[:8]
            record = TradeRecord(
                id=trade_id,
                symbol=matched_sym,
                side=f"FUTURES_CLOSE_{pos_side}",
                order_type="MARKET",
                amount_usdt=round(notional, 2),
                price=round(current_price, 4),
                quantity=round(close_qty, 4),
                fee=round(fee, 4),
                pnl=round(pnl, 2),
                status="FILLED",
                reason=reason,
                agent_core=agent_core,
                execution_mode="SIMULATION"
            )
            memory.record_trade(record)
            memory.log("Simulator", f"Closed Futures {pos_side} {matched_sym}, qty: {close_qty:.4f}, exit: ${current_price:.2f}, PnL: ${pnl:.2f}", LogLevel.SUCCESS)

            return {
                "success": True,
                "found": True,
                "trade_id": trade_id,
                "symbol": matched_sym,
                "side": f"CLOSE_{pos_side}",
                "closed_position_side": "LONG" if pos_side == "BUY" else "SHORT",
                "leverage": leverage,
                "notional_usdt": round(notional, 2),
                "pnl": round(pnl, 2),
                "entry_price": round(entry_price, 4),
                "exit_price": round(current_price, 4),
                "quantity": round(close_qty, 4),
                "fee": round(fee, 4),
                "execution_mode": "SIMULATION",
                "message": f"Successfully closed {pos_side} futures position for {matched_sym} at ${current_price:,.2f} with PnL of ${pnl:+.2f} USDT."
            }

    def trigger_emergency_kill_switch(self) -> Dict[str, Any]:
        """Emergency circuit breaker: liquidates all positions into USDT and halts trading."""
        with self._lock:
            closed_spot = []
            closed_futures = []

            # 1. Liquidate Spot holdings to USDT
            for asset, qty in list(self.balances.items()):
                if asset == "USDT" or qty <= 0.000001:
                    continue
                sym = f"{asset}USDT"
                res = self.execute_spot_order(
                    sym,
                    "SELL",
                    quantity=qty,
                    reason="EMERGENCY KILL-SWITCH",
                    agent_core="Core 4 - Risk Guardian"
                )
                closed_spot.append({"symbol": sym, "result": res})

            # 2. Close Futures positions and audit records
            for sym, f_pos in list(self.futures_positions.items()):
                current_price = market_data.get_ticker_price(sym) or f_pos["entry_price"]
                entry_price = f_pos["entry_price"]
                qty = f_pos["quantity"]
                side = f_pos["side"]
                pnl = (current_price - entry_price) * qty if side == "BUY" else (entry_price - current_price) * qty
                self.realized_pnl += pnl
                self.futures_margin_balance += (f_pos["margin"] + pnl)

                trade_id = str(uuid.uuid4())[:8]
                record = TradeRecord(
                    id=trade_id,
                    symbol=sym,
                    side=f"FUTURES_CLOSE_{side}",
                    order_type="MARKET",
                    amount_usdt=round(qty * current_price, 2),
                    price=round(current_price, 4),
                    quantity=round(qty, 4),
                    fee=0.0,
                    pnl=round(pnl, 2),
                    status="FILLED",
                    reason="EMERGENCY KILL-SWITCH",
                    agent_core="Core 4 - Risk Guardian",
                    execution_mode="SIMULATION"
                )
                memory.record_trade(record)
                closed_futures.append({"symbol": sym, "pnl": round(pnl, 2)})

            self.futures_positions.clear()
            self.futures_leverage.clear()

            # 3. Lock future order execution
            self.kill_switch_triggered = True
            memory.log("RiskGuardian", "EMERGENCY KILL-SWITCH TRIGGERED. All positions liquidated to USDT.", LogLevel.ERROR)

            return {
                "status": "KILL_SWITCH_ACTIVE",
                "message": "All spot and futures positions liquidated to stablecoins. Trading halted.",
                "closed_spot_count": len(closed_spot),
                "closed_futures_count": len(closed_futures),
                "portfolio": self.get_portfolio_summary()
            }

    def deactivate_kill_switch(self) -> Dict[str, Any]:
        with self._lock:
            self.kill_switch_triggered = False
            memory.log("RiskGuardian", "Emergency Kill-Switch deactivated. Trading resumed.", LogLevel.INFO)
            return {"status": "ACTIVE", "message": "Kill-switch deactivated. Normal operations resumed."}


# Global Simulator Singleton
simulator = PaperTradingSimulator()
