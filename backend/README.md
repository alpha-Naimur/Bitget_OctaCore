# ⚡ Bitget OctaCore - Backend Service

This directory contains the Python 3.12 FastAPI backend for **Bitget OctaCore Institutional AI Trading Desk**.

## 🌟 Key Features
- **8 Autonomous Cores**: Market Intelligence, Quant Analytics, Backtesting, Risk Guardian, Order Execution, Tokenized Stocks Radar, Sub-Account Router, and News Sentinel.
- **Multi-Provider LLM Intelligence**: Official sponsor Alibaba Cloud Qwen (`qwen3.8-max` via Bitget Hackathon proxy), Google Gemini 2.5 Flash, and OpenRouter auto-fallbacks.
- **Position Lifecycle Management**: Native `close_futures_position` de-risking and closing with accurate PnL accounting, preventing accidental spot order creation.
- **Bitget UTA v3 Integration**: Native support for Bitget's Unified Trading Account (`/api/v3/account/assets`, `/api/v3/trade/place-order`).
- **Agentic OAuth 2.0 Flow**: Seamless authentication with RSA-2048 encryption for sub-accounts.
- **WebSocket Streaming**: Real-time telemetry feed at `/ws` for tickers, risk limits, audit logs, and equity curves.
- **Emergency Kill-Switch**: Sub-second liquidation of crypto and tokenized equity positions to USDT stablecoins.

---

## 🚀 Running Locally

```bash
# 1. Navigate into backend directory
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch FastAPI backend
python main.py --web
```
*Backend runs on `http://127.0.0.1:8000` by default (or respects `$PORT` and `$HOST`).*

---

## 🧪 Running Tests (35 Tests, 100% Pass Rate)

```bash
# From within the backend directory:
python -m pytest tests/ -v
```

---

## 🐳 Container Deployment

The backend includes a production-ready `Dockerfile`, `railway.json`, and `render.yaml`.

### Railway (1-Click)
1. In Railway, set **Root Directory** to `backend` (or deploy from repository root).
2. Configure environment variables (`EXECUTION_MODE`, `BITGET_OAUTH_ENABLED`, `GEMINI_API_KEY`).
3. Railway automatically detects `Dockerfile` and deploys the backend container.

### Render
1. Create a Web Service pointing to your repo.
2. Set **Root Directory** to `backend`.
3. Select **Docker** environment.
4. Set Health Check Path to `/api/status`.
