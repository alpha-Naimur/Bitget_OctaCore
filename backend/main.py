"""Unified entry point for Bitget OctaCore (Web UI, Terminal CLI, or MCP Server)."""

import argparse
import os
import sys
import uvicorn
import pytest

# Ensure UTF-8 stdout on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure AppLocker/Application Control DLL blocking on pyarrow does not crash pandas
try:
    import pyarrow  # noqa: F401
except (ImportError, Exception):
    sys.modules["pyarrow"] = None


def main():
    parser = argparse.ArgumentParser(description="Bitget OctaCore - Track 2: Agentic Trading")
    parser.add_argument("--web", action="store_true", help="Launch FastAPI institutional web dashboard")
    parser.add_argument("--cli", action="store_true", help="Launch interactive Rich terminal CLI")
    parser.add_argument("--mcp", action="store_true", help="Launch stdio Model Context Protocol (MCP) server")
    parser.add_argument("--login", "--oauth", dest="oauth_login", action="store_true", help="Authenticate with Bitget Agentic Account via OAuth 2.0")
    parser.add_argument("--auth-status", action="store_true", help="Display current Agentic OAuth authentication status")
    parser.add_argument("--logout", action="store_true", help="Revoke and delete local OAuth credentials")
    parser.add_argument("--test", action="store_true", help="Run automated pytest verification suite")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Web dashboard port (default: 8000 or $PORT)")
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "127.0.0.1"), help="Web dashboard host (default: 127.0.0.1 or $HOST)")
    parser.add_argument("--reload", action="store_true", default=False if os.environ.get("PORT") else True, help="Enable Uvicorn auto-reload")

    args = parser.parse_args()

    if args.oauth_login:
        from src.bitget.client import bitget_client
        print("[*] Initiating Bitget Agentic Account OAuth 2.0 flow...")
        res = bitget_client.authenticate_with_oauth(open_browser=True, timeout_seconds=300.0)
        if res.get("success"):
            print(f"[✔] Authorization complete! Sub-Account UID: {res.get('user_id')}")
            print(f"[*] Credentials saved to: {res.get('credentials_file')}")
        else:
            print(f"[✘] OAuth failed: {res.get('error')}")
            sys.exit(1)
    elif args.auth_status:
        from src.bitget.oauth import oauth_manager
        status = oauth_manager.get_auth_status()
        print("\n--- Bitget Agentic Account Status ---")
        for k, v in status.items():
            print(f"  {k}: {v}")
        print("------------------------------------\n")
    elif args.logout:
        from src.bitget.oauth import oauth_manager
        if oauth_manager.revoke_credentials():
            print("[✔] Successfully logged out. Local OAuth credentials removed.")
        else:
            print("[✘] Failed to remove credentials.")
            sys.exit(1)
    elif args.cli:
        from src.cli import run_cli_loop
        run_cli_loop()
    elif args.mcp:
        from src.mcp.mcp_server import run_mcp_stdio
        run_mcp_stdio()
    elif args.test:
        sys.exit(pytest.main(["tests", "-v"]))
    else:
        # Default to web dashboard
        print(f"[*] Starting Bitget OctaCore Web Dashboard on http://{args.host}:{args.port} ...")
        uvicorn.run("src.web.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
