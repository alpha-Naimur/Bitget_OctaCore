"""Bitget Agentic Account OAuth 2.0 implementation.

Implements the official Bitget Agentic sub-account authentication protocol:
- Ephemeral RSA-2048 keypair generation (SPKI public key / PKCS#8 private key).
- Ephemeral local callback server to capture the OAuth redirect with dataKey.
- Decryption of RSA split-codec ciphertext from Bitget's getAgentAccountData endpoint.
- Local credential storage at ~/.bitget/oauth_token.json interoperable with @bitget-ai/bitget-agent-mcp.
"""

import base64
import json
import os
import threading
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from src.core.config import settings
from src.core.memory import LogLevel, memory

# Default paths and endpoints aligned with official @bitget-ai/bitget-agent-sdk
DEFAULT_OAUTH_TOKEN_DIR = Path.home() / ".bitget"
DEFAULT_OAUTH_TOKEN_PATH = DEFAULT_OAUTH_TOKEN_DIR / "oauth_token.json"

DEFAULT_AUTH_BASE_URL = "https://www.bitget.com"
DEFAULT_AUTH_PATH = "/account/center/agent-subaccount-oauth"
DEFAULT_API_BASE_URL = "https://www.bitget.com"
DEFAULT_ACCOUNT_DATA_PATH = "/v1/user/public/getAgentAccountData"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the OAuth redirect callback."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stdout access logging."""
        pass

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)

        server: "OAuthCallbackServer" = self.server  # type: ignore

        if "dataKey" in params and params["dataKey"]:
            data_key = params["dataKey"][0]
            server.captured_data_key = data_key

            # Return a polished completion page to the user's browser
            html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Bitget Agentic Account - Authorized</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #0b0e11; color: #eaecef; }
        .card { background: #181a20; padding: 40px; border-radius: 12px; text-align: center; max-width: 460px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); border: 1px solid #2b313a; }
        .icon { font-size: 54px; color: #00F0FF; margin-bottom: 16px; }
        h1 { margin: 0 0 12px 0; font-size: 24px; color: #00F0FF; }
        p { color: #848e9c; line-height: 1.6; font-size: 15px; }
        .badge { display: inline-block; padding: 6px 14px; background: rgba(0,240,255,0.1); color: #00F0FF; border-radius: 20px; font-weight: bold; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">&#10004;</div>
        <h1>Bitget Agentic Authorized</h1>
        <p>Your AI Agent has successfully received the authorization credentials. You can now close this browser window and return to your terminal.</p>
        <div class="badge">Isolated Sub-Account Active</div>
    </div>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
            server.callback_event.set()
        else:
            err_msg = "Error: Missing dataKey parameter in OAuth callback."
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(err_msg.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(err_msg.encode("utf-8"))


class OAuthCallbackServer(HTTPServer):
    """Ephemeral HTTP server for intercepting the OAuth callback."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        super().__init__((host, port), OAuthCallbackHandler)
        self.captured_data_key: Optional[str] = None
        self.callback_event = threading.Event()


@dataclass
class OAuthSession:
    """Represents an active in-flight OAuth authorization session."""
    session_id: str
    private_key: rsa.RSAPrivateKey
    public_key_b64: str
    server: OAuthCallbackServer
    server_thread: threading.Thread
    port: int
    created_at: float
    authorize_url: str


class BitgetOAuthManager:
    """Manages the full lifecycle of Bitget Agentic Account OAuth 2.0 authentication."""

    def __init__(self, token_path: Optional[Path] = None):
        self.token_path: Path = token_path or self._resolve_token_path()
        self._active_sessions: Dict[str, OAuthSession] = {}
        self._lock = threading.Lock()

    def _resolve_token_path(self) -> Path:
        """Resolve token storage path from settings or default ~/.bitget/oauth_token.json."""
        if getattr(settings, "BITGET_OAUTH_TOKEN_PATH", None):
            return Path(settings.BITGET_OAUTH_TOKEN_PATH)
        return DEFAULT_OAUTH_TOKEN_PATH

    @staticmethod
    def generate_session_keypair() -> Tuple[rsa.RSAPrivateKey, str]:
        """Generate ephemeral RSA-2048 keypair. Returns (private_key, spki_public_key_b64)."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        spki_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_b64 = base64.b64encode(spki_der).decode("utf-8")
        return private_key, public_key_b64

    @staticmethod
    def _to_standard_base64(url_safe_b64: str) -> str:
        """Convert URL-safe base64 to standard base64 with padding."""
        padded = url_safe_b64.replace("-", "+").replace("_", "/")
        remainder = len(padded) % 4
        if remainder != 0:
            padded += "=" * (4 - remainder)
        return padded

    @classmethod
    def decrypt_account_data(cls, ciphertext_b64url: str, private_key: rsa.RSAPrivateKey) -> Dict[str, Any]:
        """Decrypt split-codec RSA-2048 PKCS#1 v1.5 ciphertext returned by Bitget getAgentAccountData."""
        std_b64 = cls._to_standard_base64(ciphertext_b64url)
        ciphertext_bytes = base64.b64decode(std_b64)

        key_size_bytes = 256  # 2048 bits / 8
        if len(ciphertext_bytes) == 0 or len(ciphertext_bytes) % key_size_bytes != 0:
            raise ValueError(
                f"Unexpected ciphertext length ({len(ciphertext_bytes)} bytes). "
                f"Must be a non-zero multiple of RSA key size ({key_size_bytes} bytes)."
            )

        decrypted_chunks = []
        for offset in range(0, len(ciphertext_bytes), key_size_bytes):
            block = ciphertext_bytes[offset : offset + key_size_bytes]
            decrypted_chunk = private_key.decrypt(block, padding.PKCS1v15())
            decrypted_chunks.append(decrypted_chunk)

        plaintext = b"".join(decrypted_chunks).decode("utf-8")
        return json.loads(plaintext)

    def start_oauth_flow(
        self,
        base_url: Optional[str] = None,
        locale: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start local callback listener and construct Bitget Agentic OAuth URL."""
        with self._lock:
            # Generate new RSA session keys
            private_key, public_key_b64 = self.generate_session_keypair()

            # Start ephemeral callback server
            server = OAuthCallbackServer(host="127.0.0.1", port=0)
            assigned_port = server.server_port

            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
                name=f"BitgetOAuthServer-{assigned_port}"
            )
            thread.start()

            session_id = f"sess_{int(time.time())}_{assigned_port}"
            auth_base = base_url or DEFAULT_AUTH_BASE_URL
            
            # Allow explicit locale if requested (e.g., 'zh-CN', 'en'); default to English/browser standard path
            if locale and locale != "en":
                auth_path = f"/{locale}/account/center/agent-subaccount-oauth"
            else:
                auth_path = DEFAULT_AUTH_PATH

            authorize_url = (
                f"{auth_base}{auth_path}"
                f"?publicKey={public_key_b64}"
                f"&clientServerIpAddress=127.0.0.1"
                f"&clientServerPort={assigned_port}"
            )

            session = OAuthSession(
                session_id=session_id,
                private_key=private_key,
                public_key_b64=public_key_b64,
                server=server,
                server_thread=thread,
                port=assigned_port,
                created_at=time.time(),
                authorize_url=authorize_url
            )
            self._active_sessions[session_id] = session

            memory.log(
                "OAuth",
                f"OAuth session {session_id} initiated on port {assigned_port}",
                LogLevel.INFO
            )

            return {
                "session_id": session_id,
                "authorize_url": authorize_url,
                "callback_port": assigned_port,
                "status": "AWAITING_BROWSER_AUTH"
            }

    def check_oauth_session(
        self,
        session_id: str,
        api_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Non-blocking status check for web/polling clients. Returns COMPLETED, PENDING, or ERROR."""
        session = self._active_sessions.get(session_id)
        if not session:
            # Check if credentials were already saved
            creds = self.load_credentials()
            if creds:
                return {
                    "success": True,
                    "status": "COMPLETED",
                    "user_id": creds.get("userId"),
                    "api_key_masked": self._mask_key(creds.get("apiKey", "")),
                    "obtained_at": creds.get("obtainedAt")
                }
            return {"success": False, "status": "ERROR", "error": f"Session {session_id} not found."}

        server = session.server
        if not server.captured_data_key:
            return {"success": True, "status": "PENDING", "session_id": session_id}

        # Data key captured! Exchange it with Bitget API
        data_key = server.captured_data_key
        api_base = api_base_url or DEFAULT_API_BASE_URL
        endpoint_url = f"{api_base}{DEFAULT_ACCOUNT_DATA_PATH}"

        try:
            resp = requests.post(
                endpoint_url,
                json={"dataKey": data_key},
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )

            if not resp.ok:
                return {
                    "success": False,
                    "status": "ERROR",
                    "error": f"getAgentAccountData failed with HTTP {resp.status_code}: {resp.text}"
                }

            resp_json = resp.json()
            if resp_json.get("code") != "200" or not resp_json.get("data"):
                err_msg = resp_json.get("msg", "No data returned from getAgentAccountData")
                return {
                    "success": False,
                    "status": "ERROR",
                    "error": f"Bitget API Error: {err_msg}"
                }

            ciphertext = resp_json["data"]
            account_data = self.decrypt_account_data(ciphertext, session.private_key)

            credentials = {
                "userId": str(account_data.get("userId", "")),
                "apiKey": account_data.get("apiKey", ""),
                "secretKey": account_data.get("secretKey", ""),
                "passphrase": account_data.get("passphrase", ""),
                "obtainedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

            self.save_credentials(credentials)
            self._cleanup_session(session_id)

            return {
                "success": True,
                "status": "COMPLETED",
                "user_id": credentials["userId"],
                "api_key_masked": self._mask_key(credentials["apiKey"]),
                "obtained_at": credentials["obtainedAt"],
                "credentials_file": str(self.token_path)
            }
        except Exception as e:
            return {"success": False, "status": "ERROR", "error": f"OAuth exchange exception: {str(e)}"}

    def wait_for_oauth_callback(
        self,
        session_id: str,
        timeout_seconds: float = 300.0,
        api_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Wait for the user to complete authorization in browser, exchange dataKey, and save credentials."""
        session = self._active_sessions.get(session_id)
        if not session:
            return {"success": False, "error": f"Session {session_id} not found."}

        server = session.server
        try:
            # Wait for redirect event
            got_callback = server.callback_event.wait(timeout=timeout_seconds)
            if not got_callback or not server.captured_data_key:
                return {
                    "success": False,
                    "error": "Timed out waiting for Bitget OAuth browser approval."
                }

            data_key = server.captured_data_key
            memory.log("OAuth", f"Captured dataKey for session {session_id}. Requesting credentials...", LogLevel.INFO)

            # Exchange dataKey for encrypted credentials
            api_base = api_base_url or DEFAULT_API_BASE_URL
            endpoint_url = f"{api_base}{DEFAULT_ACCOUNT_DATA_PATH}"

            resp = requests.post(
                endpoint_url,
                json={"dataKey": data_key},
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )

            if not resp.ok:
                return {
                    "success": False,
                    "error": f"getAgentAccountData HTTP request failed with status {resp.status_code}: {resp.text}"
                }

            resp_json = resp.json()
            if resp_json.get("code") != "200" or not resp_json.get("data"):
                err_msg = resp_json.get("msg", "No data returned from getAgentAccountData")
                return {
                    "success": False,
                    "error": f"Bitget API Error: {err_msg}. Please restart the OAuth flow."
                }

            ciphertext = resp_json["data"]
            account_data = self.decrypt_account_data(ciphertext, session.private_key)

            credentials = {
                "userId": str(account_data.get("userId", "")),
                "apiKey": account_data.get("apiKey", ""),
                "secretKey": account_data.get("secretKey", ""),
                "passphrase": account_data.get("passphrase", ""),
                "obtainedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

            self.save_credentials(credentials)

            memory.log(
                "OAuth",
                f"Agentic account credentials securely saved for UID: {credentials['userId']}",
                LogLevel.INFO
            )

            return {
                "success": True,
                "user_id": credentials["userId"],
                "api_key_masked": self._mask_key(credentials["apiKey"]),
                "obtained_at": credentials["obtainedAt"],
                "credentials_file": str(self.token_path)
            }

        except Exception as e:
            return {"success": False, "error": f"OAuth processing exception: {str(e)}"}
        finally:
            self._cleanup_session(session_id)

    def authenticate_interactive(
        self,
        open_browser: bool = True,
        timeout_seconds: float = 300.0,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convenience method to execute full interactive OAuth flow."""
        start_res = self.start_oauth_flow(base_url=base_url)
        session_id = start_res["session_id"]
        auth_url = start_res["authorize_url"]

        if open_browser:
            try:
                webbrowser.open(auth_url)
            except Exception as e:
                memory.log("OAuth", f"Failed to auto-open browser: {e}. User can open URL manually.", LogLevel.WARN)

        return self.wait_for_oauth_callback(session_id, timeout_seconds=timeout_seconds)

    def _cleanup_session(self, session_id: str) -> None:
        """Stop callback server and purge session."""
        with self._lock:
            session = self._active_sessions.pop(session_id, None)
            if session:
                try:
                    session.server.shutdown()
                    session.server.server_close()
                except Exception:
                    pass

    def save_credentials(self, creds: Dict[str, Any]) -> None:
        """Save credentials to disk with restricted permissions."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)

    def load_credentials(self) -> Optional[Dict[str, Any]]:
        """Load credentials from local disk if existing and valid."""
        if not self.token_path.exists():
            return None
        try:
            with open(self.token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("apiKey") and data.get("secretKey") and data.get("passphrase"):
                return data
            return None
        except Exception as e:
            memory.log("OAuth", f"Failed to read credentials file {self.token_path}: {e}", LogLevel.WARN)
            return None

    def revoke_credentials(self) -> bool:
        """Delete local OAuth credentials file."""
        if self.token_path.exists():
            try:
                self.token_path.unlink()
                memory.log("OAuth", f"Revoked local OAuth credentials at {self.token_path}", LogLevel.INFO)
                return True
            except Exception as e:
                memory.log("OAuth", f"Failed to delete credentials file: {e}", LogLevel.ERROR)
                return False
        return True

    def get_auth_status(self) -> Dict[str, Any]:
        """Check current OAuth authentication status."""
        creds = self.load_credentials()
        if creds:
            return {
                "authorized": True,
                "auth_type": "AGENTIC_OAUTH",
                "user_id": creds.get("userId", "N/A"),
                "api_key_masked": self._mask_key(creds.get("apiKey", "")),
                "obtained_at": creds.get("obtainedAt", "Unknown"),
                "credentials_file": str(self.token_path)
            }
        return {
            "authorized": False,
            "auth_type": "UNAUTHORIZED",
            "credentials_file": str(self.token_path),
            "message": "No Agentic OAuth token found. Run 'login' or execute python main.py --login."
        }

    @staticmethod
    def _mask_key(key: str) -> str:
        """Mask an API key for safe terminal display."""
        if not key:
            return "N/A"
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"


# Global singleton instance
oauth_manager = BitgetOAuthManager()
