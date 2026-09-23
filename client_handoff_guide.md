# 📦 Bitget OctaCore - Client Handoff & Production Shipping Guide

This guide is prepared specifically for **handing off the Bitget OctaCore project to your client or end-user**. It contains everything they need to run, configure, and deploy the system smoothly.

---

## 🌟 1. What Has Been Built

**Bitget OctaCore** is an institutional-grade, multi-agent autonomous trading desk designed for Bitget AI Base Camp Hackathon S2 (Track 2: Agentic Trading).

### Core Capabilities
- **8 Autonomous Agent Cores**: Market Intelligence, Quantitative Analytics, Backtesting, Risk Guardian, Execution Engine, Tokenized Stocks Radar, Sub-Account Isolation, and Macro News Sentinel.
- **7×24 Tokenized US Equities Engine**: Continuous round-the-clock trading of equities (`NVDA`, `AAPL`, `TSLA`, `SPY`, `QQQ`) using Bitget UTA v3 instruments.
- **Interactive 7×24 Ticker Streamer & Dynamic Asset Selection**: Real-time cross-panel synchronization between ticker bar, live telemetry chart, and AI Agent Desk for instant multi-asset switching (`NVDA`, `AAPL`, `TSLA`, `SPY`, `BTC`, `ETH`, etc.).
- **Position Lifecycle Management & De-risking**: Full futures position management with native `close_futures_position`, supporting natural language commands ("close btc long", "de-risk my eth future") with zero accidental spot order execution.
- **Multi-Provider LLM Intelligence**: Alibaba Cloud Qwen (`qwen3.8-max` via Bitget's Hackathon endpoint), Google Gemini 2.5 Flash, and OpenRouter auto-fallbacks.
- **Bitget Unified Trading Account (UTA v3)**: Full native integration with `/api/v3/account/assets` and `/api/v3/trade/place-order`.
- **1-Click Agentic Sub-Account OAuth 2.0**: Zero manual key copying; authenticates securely via browser OAuth with RSA-2048 encryption.
- **Mathematical Risk Firewall & Emergency Kill-Switch**: Hard-coded order caps, position size ceilings, and sub-second position liquidation to USDT.
- **Pure-Black Neon Glassmorphism Dashboard**: Ultra-responsive institutional UI with real-time WebSocket ticker telemetry.

---

## 🏛️ 2. Clean Architecture Overview

The repository is structured as a symmetrical monorepo:

```text
Bitget_OctaCore/
├── frontend/             # 🌐 Standalone Vercel Frontend (Static Edge Delivery)
│   ├── index.html        # Institutional Trading Desk UI
│   ├── config.js         # Dynamic Backend & WebSocket Resolver
│   ├── vercel.json       # Edge Rewrites Proxy & Security Headers
│   ├── package.json      # Dev & Serve Scripts
│   └── README.md         # Vercel Deployment Instructions
│
├── backend/              # ⚙️ Dedicated Python FastAPI Trading Backend
│   ├── src/              # 8-Core Engines, UTA v3 Client & API Routes
│   ├── bitget_skills_hub/# Agentic Trading Skills Hub
│   ├── tests/            # Automated Pytest Test Suite (35 Tests)
│   ├── main.py           # Backend Server Launcher
│   ├── requirements.txt  # Python Dependencies
│   ├── Dockerfile        # Production Multi-Stage Container
│   ├── railway.json      # Railway 1-Click Manifest
│   ├── render.yaml       # Render Blueprint
│   ├── .env.example      # Environment Template
│   └── README.md         # Backend Deployment Guide
│
├── submission/           # 📄 Official Hackathon Submission Package & Audit Logs
├── main.py               # 🚀 Root Convenience Runner (delegates to backend/main.py)
├── pytest.ini            # 🧪 Root Pytest Config (runs backend/tests)
├── requirements.txt      # Root Dependencies Reference
├── .env.example          # Root Environment Template
└── README.md             # Complete Technical Documentation
```

---

## 🚀 3. Quick Start for the Client (Local Run)

Your client can run the entire system locally in under 60 seconds:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the system (Launches backend and serves dashboard)
python main.py --web
```
The dashboard will open automatically at **`http://127.0.0.1:8000`**.

### Authenticating with Bitget
To link a Bitget sub-account, the client simply runs:
```bash
python main.py --login
```
Or clicks the **🔑 Connect Sub-Account** button directly on the web dashboard. A browser tab will open Bitget's official authorization page. Upon approval, credentials are automatically exchanged and stored locally.

---

## ☁️ 4. Production Cloud Deployment (Client Handoff)

Because OctaCore is an autonomous trading system with 24/7 background agent loops and persistent WebSockets, the production deployment is split into:
1. **Frontend on Vercel** (Blazing fast edge CDN).
2. **Backend on Railway or Render** (Persistent 24/7 container).

### Step A: Deploy Backend to Railway (Recommended)
1. Push repository to GitHub.
2. In [Railway.app](https://railway.app), click **New Project** -> **Deploy from GitHub repo**.
3. Set **Root Directory** to `backend`.
4. Add Environment Variables in Railway:
   - `EXECUTION_MODE`: `SUB_ACCOUNT` (or `SIMULATION`)
   - `BITGET_OAUTH_ENABLED`: `true`
   - `LLM_PROVIDER`: `gemini` (or `qwen`, `openrouter`)
   - `GEMINI_API_KEY`: *(client's Gemini API key)*
5. Railway will build the container and provide a public URL (e.g. `https://octacore-backend.up.railway.app`).

### Step B: Deploy Frontend to Vercel
1. In [Vercel](https://vercel.com/new), import the GitHub repository.
2. In the project settings, set **Root Directory** to `frontend`.
3. In [`frontend/vercel.json`](frontend/vercel.json), replace the destination URL with the Railway backend URL:
   ```json
   "rewrites": [
     {
       "source": "/api/:match*",
       "destination": "https://octacore-backend.up.railway.app/api/:match*"
     },
     {
       "source": "/ws",
       "destination": "https://octacore-backend.up.railway.app/ws"
     }
   ]
   ```
4. Click **Deploy**. Vercel will host the frontend globally with instant updates.

---

## 🛡️ 5. Security & Pre-Flight Verification

| Check | Status | Verification Detail |
| :--- | :--- | :--- |
| **No Leaked Secrets** | ✅ PASSED | `.gitignore` strictly ignores `.env`, `.env.*`, `.bitget/`, `*.pem`, and `*.key`. |
| **Clean Examples** | ✅ PASSED | Both `.env.example` files contain only blank placeholder keys. |
| **Unit & Integration Tests** | ✅ PASSED | **35/35 tests passed** with 100% pass rate (`python -m pytest`). |
| **Bitget UTA v3 Error [40085]** | ✅ RESOLVED | Native support for Bitget Unified Trading Accounts. |
| **WebSocket Fallback** | ✅ VERIFIED | Frontend automatically degrades to 3s polling if WebSockets are blocked. |
| **Kill-Switch Readiness** | ✅ VERIFIED | Emergency liquidation terminates positions instantly. |

---

## 🎯 6. Delivery Summary for Your Client

When handing over the codebase, you can share:
1. **The Repository**: Clean, modular `frontend/` and `backend/`.
2. **This Handoff Guide**: Clear 1-command startup and 1-click cloud deployment.
3. **Submission Package**: Located in [`submission/HACKATHON_SUBMISSION.md`](submission/HACKATHON_SUBMISSION.md) with verified paper trading logs.
