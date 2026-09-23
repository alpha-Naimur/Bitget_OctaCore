"""FastAPI REST and WebSocket server for Bitget OctaCore Institutional Dashboard."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.core.config import settings, ExecutionMode
from src.core.memory import memory, LogLevel
from src.core.orchestrator import orchestrator
from src.bitget.client import bitget_client
from src.bitget.oauth import oauth_manager
from src.bitget.trading_engine import trading_engine
from src.bitget.market_data import market_data
from src.bitget.sub_account import sub_account_manager
from src.bitget.simulator import simulator

# Skill imports
from bitget_skills_hub.agentic_trading.tools import (
    execute_spot_order as agentic_spot,
    execute_futures_order as agentic_futures,
    execute_smart_dca as agentic_dca
)
from bitget_skills_hub.quant_engine.tools import get_quant_risk_metrics, get_time_series_regime, get_composite_alpha_score
from bitget_skills_hub.backtesting.tools import run_strategy_backtest
from bitget_skills_hub.risk_guardian.tools import get_risk_firewall_status, trigger_emergency_kill_switch, deactivate_kill_switch
from bitget_skills_hub.news_sentinel.tools import fetch_breaking_crypto_news

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
INDEX_HTML = STATIC_DIR / "index.html"

app = FastAPI(
    title="Bitget OctaCore API",
    description="Institutional Multi-Agent AI Trading Operating System for Bitget AI Hackathon S2",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
connected_websockets = set()


@app.get("/")
async def get_index():
    """Serve pure-black glassmorphism dashboard."""
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return JSONResponse({"message": "Bitget OctaCore API online. UI build in progress."})


@app.get("/config.js")
async def get_config_js():
    """Serve dynamic config resolver for local execution."""
    config_file = STATIC_DIR / "config.js"
    if config_file.exists():
        return FileResponse(config_file, media_type="application/javascript")
    return JSONResponse({"error": "config.js not found"}, status_code=404)


@app.get("/api/status")
async def get_system_status():
    """Return system health, active mode, and status of all 8 cores."""
    exec_status = trading_engine.get_execution_status()
    cores = orchestrator.get_cores_status()
    risk = get_risk_firewall_status()

    return {
        "system": "Bitget OctaCore",
        "hackathon": "Bitget AI Base Camp Hackathon S2",
        "track": "Track 2: Agentic Trading",
        "execution_status": exec_status,
        "cores": cores,
        "risk_firewall": risk,
        "llm_provider": settings.LLM_PROVIDER.value,
        "llm_model": settings.LLM_MODEL
    }


@app.get("/api/firewall/status")
async def get_firewall_telemetry():
    """Return Risk Guardian firewall status, limits, and live telemetry."""
    return get_risk_firewall_status()


@app.get("/api/portfolio")
async def get_portfolio():
    """Return real-time portfolio metrics, equity, available cash, and holdings."""
    return trading_engine.get_portfolio()


@app.get("/api/market-overview")
async def get_market_overview():
    """Return live tickers for Crypto and 7x24 Tokenized US Equities."""
    return market_data.get_market_overview()


@app.get("/api/ta/{symbol}")
async def get_symbol_ta(symbol: str, interval: str = "1H"):
    """Return live Technical Analysis for symbol."""
    return market_data.compute_technical_analysis(symbol=symbol, granularity=interval)


@app.get("/api/quant/{symbol}")
async def get_symbol_quant(symbol: str):
    """Return institutional factor metrics (VaR, CVaR, Hurst Exponent, Alpha Score)."""
    quant = get_quant_risk_metrics(symbol)
    regime = get_time_series_regime(symbol)
    alpha = get_composite_alpha_score(symbol)
    return {
        "symbol": symbol.upper(),
        "quant_metrics": quant,
        "regime": regime,
        "alpha_score": alpha
    }


@app.get("/api/backtest")
async def run_backtest(
    symbol: str = "NVDAUSDT",
    strategy: str = "RSI_MEAN_REVERSION",
    capital: float = 10000.0
):
    """Run historical backtest simulation and return equity curve data."""
    return run_strategy_backtest(symbol=symbol, strategy_name=strategy, initial_capital=capital)


@app.get("/api/sub-account")
async def get_sub_account():
    """Return sub-account permissions, isolation status, and UID."""
    return sub_account_manager.get_sub_account_status()


@app.post("/api/sub-account/toggle-privacy")
async def toggle_privacy():
    """Toggle UID privacy masking."""
    masked = sub_account_manager.toggle_privacy_mask()
    return {"privacy_masked": masked, "display_uid": sub_account_manager.get_display_uid()}


# ==========================================
# BITGET AGENTIC ACCOUNT OAUTH & MODE ENDPOINTS
# ==========================================
@app.get("/api/auth/status")
async def get_auth_status_endpoint():
    """Return current Bitget Agentic OAuth status and active execution mode."""
    status = oauth_manager.get_auth_status()
    status["execution_mode"] = settings.EXECUTION_MODE.value
    status["has_credentials"] = bitget_client.has_valid_credentials()
    status["display_uid"] = sub_account_manager.get_display_uid()
    status["auth_source"] = "oauth" if status.get("authorized") else ("env" if bitget_client.has_valid_credentials() else "none")
    return status


@app.post("/api/auth/oauth/start")
async def start_oauth_endpoint(payload: Optional[Dict[str, Any]] = Body(default={})):
    """Start Bitget Agentic OAuth 2.0 flow and return browser authorization URL."""
    locale = payload.get("locale", "en") if payload else "en"
    res = await asyncio.to_thread(oauth_manager.start_oauth_flow, locale=locale)
    if "authorize_url" in res and "auth_url" not in res:
        res["auth_url"] = res["authorize_url"]
    return res


@app.get("/api/auth/oauth/check")
async def check_oauth_endpoint(session_id: str = Query(...)):
    """Poll status of an in-flight OAuth flow session."""
    res = await asyncio.to_thread(oauth_manager.check_oauth_session, session_id=session_id)
    if res.get("status") == "COMPLETED" and res.get("success"):
        bitget_client.reload_credentials()
        settings.EXECUTION_MODE = ExecutionMode.SUB_ACCOUNT
    # Populate convenient standard aliases
    if "user_id" in res and "sub_uid" not in res:
        res["sub_uid"] = res["user_id"]
    if "error" in res and "message" not in res:
        res["message"] = res["error"]
    return res


@app.post("/api/auth/mode")
async def switch_execution_mode(payload: Dict[str, Any] = Body(...)):
    """Switch execution mode between SIMULATION and SUB_ACCOUNT."""
    new_mode_str = payload.get("mode", "SIMULATION").upper()
    try:
        new_mode = ExecutionMode(new_mode_str)
    except ValueError:
        return JSONResponse({"error": f"Invalid mode {new_mode_str}"}, status_code=400)

    if new_mode == ExecutionMode.SUB_ACCOUNT and not bitget_client.has_valid_credentials():
        return JSONResponse(
            {
                "success": False,
                "error": "No authorized Agentic Account found. Please connect via OAuth first."
            },
            status_code=400
        )

    settings.EXECUTION_MODE = new_mode
    memory.log("WebAPI", f"Switched execution mode to {new_mode.value}", LogLevel.INFO)
    return {
        "success": True,
        "mode": settings.EXECUTION_MODE.value,
        "sub_account_uid": sub_account_manager.get_display_uid(),
        "has_credentials": bitget_client.has_valid_credentials()
    }


@app.post("/api/auth/logout")
async def logout_oauth_endpoint():
    """Revoke local OAuth token and fallback to SIMULATION mode."""
    success = oauth_manager.revoke_credentials()
    bitget_client.reload_credentials()
    settings.EXECUTION_MODE = ExecutionMode.SIMULATION
    memory.log("WebAPI", "User logged out of Agentic Sub-Account. Returned to SIMULATION mode.", LogLevel.INFO)
    return {
        "success": success,
        "mode": settings.EXECUTION_MODE.value,
        "authorized": False
    }


@app.post("/api/chat")
async def post_chat(payload: Dict[str, Any] = Body(...)):
    """Interactive AI Chat with tool call visualization."""
    prompt = payload.get("message", "")
    if not prompt:
        return JSONResponse({"error": "Empty message"}, status_code=400)
    result = await asyncio.to_thread(orchestrator.process_command, prompt)
    return result


@app.post("/api/order/spot")
async def place_spot(payload: Dict[str, Any] = Body(...)):
    """Place spot order with mandatory Pre-Trade Risk Guardian verification."""
    symbol = payload.get("symbol", "BTCUSDT")
    side = payload.get("side", "BUY")
    amount = float(payload.get("amount_usdt", 100.0))
    reason = payload.get("reason", "Manual UI Execution")
    return await asyncio.to_thread(agentic_spot, symbol=symbol, side=side, amount_usdt=amount, reason=reason)


@app.post("/api/order/futures")
async def place_futures(payload: Dict[str, Any] = Body(...)):
    """Place futures contract order (Crypto or Tokenized US Stocks) with Risk Guardian check."""
    symbol = payload.get("symbol", "NVDAUSDT")
    side = payload.get("side", "BUY")
    amount = float(payload.get("amount_usdt", 100.0))
    leverage = int(payload.get("leverage", 10))
    reason = payload.get("reason", "Manual UI Futures Execution")
    return await asyncio.to_thread(agentic_futures, symbol=symbol, side=side, amount_usdt=amount, leverage=leverage, reason=reason)


@app.post("/api/smart-dca")
async def place_smart_dca(payload: Dict[str, Any] = Body(...)):
    """Trigger Volatility-Scaled Smart DCA accumulation."""
    symbol = payload.get("symbol", "BTCUSDT")
    amount = float(payload.get("base_amount_usdt", 100.0))
    return await asyncio.to_thread(agentic_dca, symbol=symbol, base_dca_amount_usdt=amount)


@app.post("/api/kill-switch/trigger")
async def trigger_kill():
    """Emergency Kill Switch."""
    return trigger_emergency_kill_switch()


@app.post("/api/kill-switch/deactivate")
async def lift_kill():
    """Deactivate Kill Switch."""
    return deactivate_kill_switch()


@app.get("/api/paper-trading/export")
async def export_paper_log():
    """Export the audited paper trading log for Hackathon Track 2 submission."""
    metrics = memory.get_paper_trading_metrics()
    trades = memory.get_trade_history(100)
    return {
        "system": "Bitget OctaCore",
        "competition": "Bitget AI Base Camp Hackathon S2",
        "track": "Track 2: Agentic Trading",
        "metrics": metrics,
        "trades": trades
    }


@app.get("/api/logs")
async def get_logs(count: int = 50):
    """Return recent system activity logs."""
    return memory.get_recent_logs(count=count)


@app.get("/api/news")
async def get_news():
    """Return breaking news and macro events."""
    return fetch_breaking_crypto_news()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Stream real-time ticker prices, logs, and portfolio state to client."""
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            # Send periodic telemetry updates using thread pool to prevent event loop blocking
            overview = await asyncio.to_thread(market_data.get_market_overview)
            portfolio = await asyncio.to_thread(trading_engine.get_portfolio)
            recent_logs = memory.get_recent_logs(count=20)
            paper_metrics = memory.get_paper_trading_metrics()

            payload = {
                "type": "TELEMETRY_UPDATE",
                "market": overview,
                "portfolio": portfolio,
                "logs": recent_logs,
                "paper_metrics": paper_metrics
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(2.0)
    except (WebSocketDisconnect, asyncio.CancelledError):
        connected_websockets.discard(websocket)
    except Exception:
        connected_websockets.discard(websocket)
