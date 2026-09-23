"""Memory, state management, event bus, and audited Paper Trading logger."""

import json
import os
import sys
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent if (BACKEND_DIR.parent / "submission").exists() else BACKEND_DIR
SUBMISSION_DIR = ROOT_DIR / "submission"
PAPER_LOG_PATH = SUBMISSION_DIR / "paper_trading_log.json"


class LogLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    SUCCESS = "SUCCESS"


class LogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    component: str
    message: str
    level: LogLevel = LogLevel.INFO


class TradeRecord(BaseModel):
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    symbol: str
    side: str  # BUY | SELL
    order_type: str = "MARKET"  # MARKET | LIMIT
    amount_usdt: float
    price: float
    quantity: float
    fee: float = 0.0
    pnl: float = 0.0
    status: str = "FILLED"  # FILLED | REJECTED | CANCELLED
    reason: str = "Quantitative Signal"
    agent_core: str = "Core 5 - Execution Agent"
    execution_mode: str = "SIMULATION"


class SystemMemory:
    """Thread-safe centralized memory, event subscriber bus, and activity store."""

    def __init__(self, max_logs: int = 1000):
        self._lock = threading.RLock()
        self.logs: List[LogEntry] = []
        self.trades: List[TradeRecord] = []
        self.max_logs = max_logs
        self.listeners: List[Callable[[LogEntry], None]] = []
        self.trade_listeners: List[Callable[[TradeRecord], None]] = []
        
        # Ensure submission directory exists
        SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
        self._load_persisted_trades()

    def log(self, component: str, message: str, level: LogLevel = LogLevel.INFO) -> LogEntry:
        """Add system log entry and notify listeners."""
        entry = LogEntry(component=component, message=message, level=level)
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > self.max_logs:
                self.logs.pop(0)

        # Broadcast outside of lock to avoid deadlocks
        for listener in list(self.listeners):
            try:
                listener(entry)
            except Exception:
                pass
        return entry

    def record_trade(self, trade: TradeRecord):
        """Record trade execution and persist to paper trading submission log."""
        with self._lock:
            self.trades.append(trade)
            self._save_persisted_trades()

        for listener in list(self.trade_listeners):
            try:
                listener(trade)
            except Exception:
                pass

    def get_recent_logs(self, count: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [l.model_dump() for l in self.logs[-count:]]

    def get_trade_history(self, count: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [t.model_dump() for t in self.trades[-count:]]

    def get_paper_trading_metrics(self) -> Dict[str, Any]:
        """Compute performance metrics required for Track 2 Agentic Trading judging."""
        with self._lock:
            trades = [t for t in self.trades if t.status == "FILLED"]
            if not trades:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate_pct": 0.0,
                    "realized_pnl_usdt": 0.0,
                    "profit_factor": 0.0,
                    "avg_trade_pnl": 0.0,
                    "total_volume_usdt": 0.0
                }

            winning = [t for t in trades if t.pnl > 0]
            losing = [t for t in trades if t.pnl < 0]
            gross_profit = sum(t.pnl for t in winning)
            gross_loss = abs(sum(t.pnl for t in losing))
            profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
            realized_pnl = sum(t.pnl for t in trades)
            total_vol = sum(t.amount_usdt for t in trades)

            # Win rate and avg PnL are evaluated on closed/realized roundtrips
            closed_trades = [t for t in trades if t.pnl != 0.0 or "SELL" in t.side or "CLOSE" in t.side]
            closed_count = len(closed_trades)

            return {
                "total_trades": len(trades),
                "closed_trades": closed_count,
                "winning_trades": len(winning),
                "losing_trades": len(losing),
                "win_rate_pct": round((len(winning) / closed_count) * 100, 2) if closed_count > 0 else 0.0,
                "realized_pnl_usdt": round(realized_pnl, 2),
                "profit_factor": profit_factor,
                "avg_trade_pnl": round(realized_pnl / closed_count, 2) if closed_count > 0 else 0.0,
                "total_volume_usdt": round(total_vol, 2)
            }

    def _save_persisted_trades(self):
        """Save trade history to submission/paper_trading_log.json."""
        if "pytest" in sys.modules:
            return
        try:
            metrics = self.get_paper_trading_metrics()
            payload = {
                "system": "Bitget OctaCore - Track 2 Agentic Trading",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "performance_summary": metrics,
                "trades": [t.model_dump() for t in self.trades]
            }
            with open(PAPER_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            pass

    def _load_persisted_trades(self):
        """Load trade history if existing log found."""
        if not PAPER_LOG_PATH.exists():
            # Create template with sample initial audit entry
            self._save_persisted_trades()
            return

        try:
            with open(PAPER_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                trades_data = data.get("trades", [])
                self.trades = [TradeRecord(**item) for item in trades_data]
        except Exception:
            self.trades = []

    def clear(self):
        with self._lock:
            self.logs.clear()
            self.trades.clear()
            self._save_persisted_trades()


# Global memory singleton
memory = SystemMemory()
