# ⚡ Bitget OctaCore - Frontend Deployment Guide (Vercel)

This directory contains the standalone, edge-ready frontend for **Bitget OctaCore Institutional AI Trading Desk**.

It is completely decoupled from the Python FastAPI backend, optimized for ultra-fast CDN delivery on **Vercel**, and features:
- **Pure-Black Neon Glassmorphism UI** (Tailored for institutional high-frequency desk monitoring).
- **Dynamic Backend Resolver (`config.js`)**: Seamlessly connects to any deployed backend via URL param (`?backend=...`), interactive UI modal, or Vercel rewrites.
- **WebSocket Resilience & Telemetry Polling Fallback**: Never freezes if WebSockets are interrupted or blocked by proxies.
- **1-Click Bitget OAuth Onboarding**: Direct visual modal for switching between Simulation Sandbox and Live Bitget Sub-Account.

---

## 🚀 Quick Deploy to Vercel (2 Options)

### Option 1: Deploy via Vercel CLI (Recommended & Fastest)

From your local machine or terminal:

```bash
# 1. Navigate into the frontend folder
cd frontend

# 2. Deploy directly to Vercel
npx vercel
```

Follow the interactive prompts:
- **Set up and deploy?** `Y`
- **Which scope?** (Select your personal or team account)
- **Link to existing project?** `N`
- **Project name:** `bitget-octacore` (or your preferred name)
- **In which directory is your code located?** `./`
- **Want to modify settings?** `N`

To deploy to production:
```bash
npx vercel --prod
```

---

### Option 2: Deploy via Vercel Web Dashboard & GitHub

1. Push your repository to **GitHub**.
2. Log in to [Vercel Dashboard](https://vercel.com/new).
3. Click **"Add New..."** -> **"Project"** and select your GitHub repository.
4. In the **Configure Project** screen:
   - **Root Directory**: Click *Edit* and select `frontend`.
   - **Framework Preset**: Leave as `Other` (or `Vite`).
   - **Build & Output Settings**: Leave empty (static HTML/JS does not require a compile step).
5. Click **Deploy**.

---

## 🔗 Connecting Frontend to the Python Backend (The Developer Way)

Because Bitget OctaCore runs background AI agent loops, autonomous risk guardians, and WebSocket telemetry streams, the Python backend runs as a container service in `backend/` (e.g. **Railway**, **Render**, **Fly.io**, or your own VPS).

You can link your Vercel frontend to your deployed backend using standard developer patterns:

### Method 1: Vercel Reverse Proxy Rewrites (Recommended for Production)
To route all `/api/*` and `/ws` calls transparently under your Vercel domain without exposing CORS:
Edit [`frontend/vercel.json`](file:///d:/development/Bitget%20Hackathon%20P2/frontend/vercel.json):
```json
{
  "rewrites": [
    {
      "source": "/api/:match*",
      "destination": "https://YOUR-BACKEND.up.railway.app/api/:match*"
    },
    {
      "source": "/ws",
      "destination": "https://YOUR-BACKEND.up.railway.app/ws"
    }
  ]
}
```

### Method 2: Global Configuration Variable
In [`frontend/config.js`](file:///d:/development/Bitget%20Hackathon%20P2/frontend/config.js) or via a CI/CD build script:
```javascript
window.__OCTACORE_BACKEND__ = "https://your-backend.up.railway.app";
```

### Method 3: Developer Query Parameter (Testing Only)
For ad-hoc preview tests without changing configuration:
```text
https://bitget-octacore.vercel.app/?backend=https://your-backend.up.railway.app
```

---

## 🐳 Deploying the Python Backend Container

A production multi-stage `Dockerfile`, `render.yaml`, and `railway.json` are already included in the project root:

### Deploy to Railway (1-Click)
1. Open [Railway.app](https://railway.app/new).
2. Choose **Deploy from GitHub repo** and select this repository.
3. Railway will detect `railway.json` and build the `Dockerfile` automatically.
4. Add your Environment Variables in Railway:
   - `EXECUTION_MODE`: `SUB_ACCOUNT` (or `SIMULATION`)
   - `BITGET_OAUTH_ENABLED`: `true`
   - `LLM_PROVIDER`: `gemini` (or `qwen`, `openrouter`)
   - `GEMINI_API_KEY`: *(your Gemini key)*

### Deploy to Render
1. Open [Render.com](https://dashboard.render.com/select-repo?type=blueprint).
2. Select your repository. Render will automatically read `render.yaml`.
3. Add secret keys (`GEMINI_API_KEY`, etc.) in the dashboard.

---

## 💻 Local Development Workflow

### Run Monolithic Mode (Single Command)
You can still run frontend and backend together locally:
```bash
python main.py --web
```
Opens the dashboard at `http://127.0.0.1:8000/`.

### Run Decoupled Frontend Dev Server
To test static hosting locally before deploying to Vercel:
```bash
cd frontend
npm install
npm run dev
# Dashboard launches on http://localhost:5173
```
