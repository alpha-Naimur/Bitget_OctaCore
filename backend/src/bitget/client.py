"""Bitget UTA v3 REST API Client with HMAC-SHA256 authenticated request signing."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional
import requests
from src.core.config import settings, ExecutionMode
from src.core.memory import memory, LogLevel
from src.bitget.oauth import oauth_manager


def format_bitget_error(code: Any, msg: str, endpoint: str = "") -> str:
    """Format raw Bitget error codes into actionable operational guidance."""
    try:
        code_int = int(code)
    except (ValueError, TypeError):
        code_int = 0

    if code_int == 40014:
        return (
            f"Bitget Error [40014]: Decryption failure or invalid passphrase on {endpoint}. "
            "Please re-authorize via Agentic OAuth (run 'login' in CLI or 'python main.py --login')."
        )
    elif code_int == 40001:
        return (
            f"Bitget Error [40001]: Access-key does not exist on {endpoint}. "
            "Your Agentic account token may have expired. Run 'python main.py --login' to refresh OAuth credentials."
        )
    elif code_int == 40003:
        return (
            f"Bitget Error [40003]: Invalid signature for {endpoint}. "
            "System clock skew or incorrect credential secret. Re-authenticate via 'python main.py --login'."
        )
    elif code_int == 40017:
        return (
            f"Bitget Error [40017]: API key lacks required permissions for {endpoint}. "
            "Ensure 'Trade' permissions are enabled for your Agentic sub-account."
        )
    elif code_int == 40085:
        return (
            f"Bitget Error [40085]: You are in Unified Account mode, and the Classic Account API is not supported at this time on {endpoint}. "
            "Switching automatically to Unified Trading Account (UTA v3) endpoint."
        )
    elif code_int == 40009:
        return f"Bitget Error [40009]: IP address is not whitelisted for this API key on {endpoint}."
    
    return f"Bitget Error [{code}]: {msg}"


class BitgetClient:
    """Client for Bitget UTA REST APIs (Public Market Data, Signed Spot, and Signed Mix Futures)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        mode: Optional[ExecutionMode] = None
    ):
        self.mode = mode or settings.EXECUTION_MODE
        self.api_key = ""
        self.api_secret = ""
        self.passphrase = ""
        self.user_id = ""
        self.auth_source = "UNAUTHENTICATED"

        self.is_unified_account = True  # Bitget Agentic sub-accounts operate in Unified Trading Account (UTA) mode

        if api_key is not None or api_secret is not None or passphrase is not None:
            self.api_key = api_key or ""
            self.api_secret = api_secret or ""
            self.passphrase = passphrase or ""
            self.auth_source = "EXPLICIT"
        else:
            self.reload_credentials()
        
        self.base_url = (
            settings.BITGET_DEMO_REST_URL if self.mode == ExecutionMode.TESTNET else settings.BITGET_REST_URL
        )

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Bitget-OctaCore/2.0",
            "Content-Type": "application/json",
            "locale": "en-US"
        })

    def reload_credentials(self) -> None:
        """Reload credentials: check Agentic OAuth token first, then fallback to environment variables."""
        if getattr(settings, "BITGET_OAUTH_ENABLED", True):
            oauth_creds = oauth_manager.load_credentials()
            if oauth_creds:
                self.api_key = oauth_creds.get("apiKey", "")
                self.api_secret = oauth_creds.get("secretKey", "")
                self.passphrase = oauth_creds.get("passphrase", "")
                self.user_id = oauth_creds.get("userId", "")
                self.auth_source = "AGENTIC_OAUTH"
                return

        # Fallback to static .env keys if configured
        if settings.BITGET_API_KEY and settings.BITGET_SECRET_KEY and settings.BITGET_PASSPHRASE:
            self.api_key = settings.BITGET_API_KEY
            self.api_secret = settings.BITGET_SECRET_KEY
            self.passphrase = settings.BITGET_PASSPHRASE
            self.user_id = settings.BITGET_SUB_ACCOUNT_UID or ""
            self.auth_source = "ENV_STATIC"
        else:
            self.api_key = ""
            self.api_secret = ""
            self.passphrase = ""
            self.user_id = ""
            self.auth_source = "UNAUTHENTICATED"

    def configure(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        mode: Optional[ExecutionMode] = None
    ):
        """Update API credentials and execution mode dynamically."""
        if mode:
            self.mode = mode
            self.base_url = (
                settings.BITGET_DEMO_REST_URL if self.mode == ExecutionMode.TESTNET else settings.BITGET_REST_URL
            )
        if api_key is not None:
            self.api_key = api_key
            self.auth_source = "EXPLICIT"
        if api_secret is not None:
            self.api_secret = api_secret
        if passphrase is not None:
            self.passphrase = passphrase

    def authenticate_with_oauth(
        self,
        open_browser: bool = True,
        timeout_seconds: float = 300.0,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger interactive Bitget Agentic OAuth login and reload credentials upon success."""
        res = oauth_manager.authenticate_interactive(
            open_browser=open_browser,
            timeout_seconds=timeout_seconds,
            base_url=base_url
        )
        if res.get("success"):
            self.reload_credentials()
        return res

    def get_auth_status(self) -> Dict[str, Any]:
        """Return comprehensive authentication status."""
        has_creds = self.has_valid_credentials()
        return {
            "authenticated": has_creds,
            "auth_source": self.auth_source,
            "user_id": self.user_id or "N/A",
            "api_key_masked": f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "****",
            "token_file": str(oauth_manager.token_path) if self.auth_source == "AGENTIC_OAUTH" else "N/A"
        }

    def has_valid_credentials(self) -> bool:
        """Check if minimum API key credentials are configured."""
        return bool(self.api_key and self.api_secret and self.passphrase)

    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """Construct HMAC-SHA256 signature for Bitget UTA v3 API: base64(hmac(ts + method + path + body))."""
        sign_str = timestamp + method.upper() + request_path + body
        mac = hmac.new(self.api_secret.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode("utf-8")

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        signed: bool = False
    ) -> Dict[str, Any]:
        """Execute HTTP request with optional HMAC-SHA256 signing."""
        url = f"{self.base_url}{endpoint}"
        query_str = ""
        if params:
            # Sort params for consistent path query formatting
            query_parts = [f"{k}={v}" for k, v in params.items()]
            query_str = "?" + "&".join(query_parts)
            request_path = endpoint + query_str
        else:
            request_path = endpoint

        headers = {
            "Content-Type": "application/json",
            "locale": "en-US"
        }

        body_str = ""
        if data and method.upper() in ("POST", "PUT"):
            body_str = json.dumps(data)

        if signed:
            if not self.has_valid_credentials():
                return {
                    "success": False,
                    "error": (
                        "Bitget API credentials not configured. Please authorize with Agentic OAuth: "
                        "run 'login' in the CLI or execute 'python main.py --login'."
                    )
                }
            timestamp = str(int(time.time() * 1000))
            signature = self._generate_signature(timestamp, method, request_path, body_str)
            headers.update({
                "ACCESS-KEY": self.api_key,
                "ACCESS-SIGN": signature,
                "ACCESS-TIMESTAMP": timestamp,
                "ACCESS-PASSPHRASE": self.passphrase
            })
            if self.mode == ExecutionMode.TESTNET:
                # Bitget Demo / Paper trading header if in sandbox environment
                headers["papertrading"] = "1"

        try:
            resp = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                data=body_str if body_str else None,
                headers=headers,
                timeout=3.0
            )
            raw = resp.json() if resp.text else {}
            code = raw.get("code")
            msg = raw.get("msg", "")

            # Auto-detect Unified Trading Account mode from exchange error
            if code == "40085" or "Unified Account mode" in msg:
                self.is_unified_account = True

            # Bitget uses "00000" for success in v2/v3, or 200 HTTP code
            if code in ("00000", 0, "0", 200) or (resp.status_code == 200 and code is None):
                return {"success": True, "data": raw.get("data", raw)}
            else:
                formatted_err = format_bitget_error(code, msg, endpoint)
                return {"success": False, "code": code, "msg": msg, "error": formatted_err}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Network/HTTP Exception: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Bitget Client Error: {str(e)}"}

    # ==========================================
    # PUBLIC MARKET DATA
    # ==========================================
    def get_spot_tickers(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Fetch spot tickers."""
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/api/v2/spot/market/tickers", params=params)

    def get_futures_tickers(self, product_type: str = "USDT-FUTURES") -> Dict[str, Any]:
        """Fetch futures tickers (Crypto + 7x24 Tokenized US Equities)."""
        params = {"productType": product_type}
        return self._request("GET", "/api/v2/mix/market/tickers", params=params)

    def get_candles(
        self,
        symbol: str,
        granularity: str = "1H",
        limit: int = 100,
        is_futures: bool = True
    ) -> Dict[str, Any]:
        """Fetch OHLCV candle history for Spot or Mix Futures."""
        if is_futures:
            params = {
                "symbol": symbol,
                "productType": "USDT-FUTURES",
                "granularity": granularity,
                "limit": str(limit)
            }
            return self._request("GET", "/api/v2/mix/market/candles", params=params)
        else:
            params = {
                "symbol": symbol,
                "granularity": granularity.lower(),
                "limit": str(limit)
            }
            return self._request("GET", "/api/v2/spot/market/candles", params=params)

    def get_order_book(self, symbol: str, limit: int = 20, is_futures: bool = True) -> Dict[str, Any]:
        """Fetch order book depth."""
        if is_futures:
            params = {
                "symbol": symbol,
                "productType": "USDT-FUTURES",
                "limit": str(limit)
            }
            return self._request("GET", "/api/v2/mix/market/merge-depth", params=params)
        else:
            params = {
                "symbol": symbol,
                "type": "step0",
                "limit": str(limit)
            }
            return self._request("GET", "/api/v2/spot/market/orderbook", params=params)

    # ==========================================
    # SIGNED ACCOUNT & ASSETS (UTA v3 & Classic v2)
    # ==========================================
    def get_spot_account_assets(self) -> Dict[str, Any]:
        """Fetch account asset balances (supports Unified Trading Account v3 & Classic v2)."""
        if self.is_unified_account:
            uta_res = self._request("GET", "/api/v3/account/assets", signed=True)
            if uta_res.get("success"):
                uta_data = uta_res.get("data", {})
                assets = list(uta_data.get("assets", []))

                # Also query funding account assets and consolidate
                try:
                    funding_res = self._request("GET", "/api/v3/account/funding-assets", signed=True)
                    if funding_res.get("success"):
                        funding_list = funding_res.get("data", [])
                        if isinstance(funding_list, list):
                            for fa in funding_list:
                                coin = fa.get("coin", "").upper()
                                avail = float(fa.get("available") or fa.get("balance") or 0.0)
                                if avail > 0:
                                    existing = next((a for a in assets if a.get("coin", "").upper() == coin), None)
                                    if existing:
                                        curr_avail = float(existing.get("available") or 0.0)
                                        existing["available"] = str(curr_avail + avail)
                                    else:
                                        assets.append({
                                            "coin": coin,
                                            "available": str(avail),
                                            "frozen": fa.get("frozen", "0"),
                                            "balance": fa.get("balance", str(avail))
                                        })
                except Exception:
                    pass

                return {
                    "success": True,
                    "account_mode": "UTA_V3",
                    "data": assets,
                    "equity": {
                        "accountEquity": uta_data.get("accountEquity", "0"),
                        "usdtEquity": uta_data.get("usdtEquity", "0"),
                        "unrealisedPnl": uta_data.get("unrealisedPnl", "0"),
                        "effEquity": uta_data.get("effEquity", "0")
                    }
                }
            elif uta_res.get("code") in ("40404", 40404):
                self.is_unified_account = False
                return self._request("GET", "/api/v2/spot/account/assets", signed=True)
            return uta_res
        else:
            classic_res = self._request("GET", "/api/v2/spot/account/assets", signed=True)
            if classic_res.get("code") == "40085":
                self.is_unified_account = True
                return self.get_spot_account_assets()
            return classic_res

    def get_futures_account(self, product_type: str = "USDT-FUTURES") -> Dict[str, Any]:
        """Fetch futures account information, equity, margin, and balances."""
        if self.is_unified_account:
            uta_res = self._request("GET", "/api/v3/account/assets", signed=True)
            if uta_res.get("success"):
                uta_data = uta_res.get("data", {})
                return {
                    "success": True,
                    "account_mode": "UTA_V3",
                    "data": [{
                        "marginCoin": "USDT",
                        "accountEquity": uta_data.get("usdtEquity") or uta_data.get("accountEquity", "0"),
                        "usdtEquity": uta_data.get("usdtEquity", "0"),
                        "unrealizedPL": uta_data.get("usdtUnrealisedPnl") or uta_data.get("unrealisedPnl", "0"),
                        "available": uta_data.get("effEquity") or uta_data.get("usdtEquity", "0"),
                        "marginRatio": uta_data.get("mgnRatio", "0"),
                        "crossedMaxAvailable": uta_data.get("effEquity", "0")
                    }]
                }
            elif uta_res.get("code") in ("40404", 40404):
                self.is_unified_account = False
                params = {"productType": product_type}
                return self._request("GET", "/api/v2/mix/account/accounts", params=params, signed=True)
            return uta_res
        else:
            params = {"productType": product_type}
            res = self._request("GET", "/api/v2/mix/account/accounts", params=params, signed=True)
            if res.get("code") == "40085":
                self.is_unified_account = True
                return self.get_futures_account(product_type)
            return res

    def get_futures_positions(self, product_type: str = "USDT-FUTURES") -> Dict[str, Any]:
        """Fetch open futures positions (unrealized PnL, leverage, entry price)."""
        if self.is_unified_account:
            params = {"category": product_type}
            res = self._request("GET", "/api/v3/position/current-position", params=params, signed=True)
            if res.get("success"):
                pos_data = res.get("data", {})
                pos_list = pos_data.get("list", []) if isinstance(pos_data, dict) else (pos_data if isinstance(pos_data, list) else [])
                return {"success": True, "data": pos_list, "account_mode": "UTA_V3"}
            elif res.get("code") in ("40404", 40404):
                self.is_unified_account = False
                params = {"productType": product_type}
                return self._request("GET", "/api/v2/mix/position/all-position", params=params, signed=True)
            return res
        else:
            params = {"productType": product_type}
            res = self._request("GET", "/api/v2/mix/position/all-position", params=params, signed=True)
            if res.get("code") == "40085":
                self.is_unified_account = True
                return self.get_futures_positions(product_type)
            return res

    # ==========================================
    # SIGNED ORDER EXECUTION (UTA v3 & Classic v2)
    # ==========================================
    def place_spot_order(
        self,
        symbol: str,
        side: str,  # buy | sell
        order_type: str = "market",
        size: Optional[str] = None,
        price: Optional[str] = None
    ) -> Dict[str, Any]:
        """Place spot order on Bitget (supports UTA v3 & Classic v2)."""
        if self.is_unified_account:
            payload: Dict[str, Any] = {
                "category": "SPOT",
                "symbol": symbol,
                "side": side.lower(),
                "orderType": order_type.lower(),
                "qty": str(size) if size else "0"
            }
            if price and order_type.lower() == "limit":
                payload["price"] = str(price)
            res = self._request("POST", "/api/v3/trade/place-order", data=payload, signed=True)
            if res.get("code") == "40085":
                self.is_unified_account = False
            else:
                return res

        classic_payload: Dict[str, Any] = {
            "symbol": symbol,
            "side": side.lower(),
            "orderType": order_type.lower(),
            "force": "normal"
        }
        if size:
            classic_payload["size"] = str(size)
        if price and order_type.lower() == "limit":
            classic_payload["price"] = str(price)

        classic_res = self._request("POST", "/api/v2/spot/trade/place-order", data=classic_payload, signed=True)
        if classic_res.get("code") == "40085":
            self.is_unified_account = True
            return self.place_spot_order(symbol, side, order_type, size, price)
        return classic_res

    def place_futures_order(
        self,
        symbol: str,
        side: str,  # buy | sell
        order_type: str = "market",
        size: str = "1",
        price: Optional[str] = None,
        margin_mode: str = "crossed",
        product_type: str = "USDT-FUTURES"
    ) -> Dict[str, Any]:
        """Place mix futures order (Crypto or Tokenized US Stocks)."""
        if self.is_unified_account:
            payload: Dict[str, Any] = {
                "category": product_type,
                "symbol": symbol,
                "side": side.lower(),
                "orderType": order_type.lower(),
                "qty": str(size),
                "posSide": "long" if side.lower() == "buy" else "short"
            }
            if price and order_type.lower() == "limit":
                payload["price"] = str(price)
            res = self._request("POST", "/api/v3/trade/place-order", data=payload, signed=True)
            if res.get("code") == "40085":
                self.is_unified_account = False
            else:
                return res

        classic_payload: Dict[str, Any] = {
            "symbol": symbol,
            "productType": product_type,
            "marginMode": margin_mode,
            "side": side.lower(),
            "orderType": order_type.lower(),
            "size": str(size),
            "tradeSide": "open" if side.lower() == "buy" else "close"
        }
        if price and order_type.lower() == "limit":
            classic_payload["price"] = str(price)

        classic_res = self._request("POST", "/api/v2/mix/order/place-order", data=classic_payload, signed=True)
        if classic_res.get("code") == "40085":
            self.is_unified_account = True
            return self.place_futures_order(symbol, side, order_type, size, price, margin_mode, product_type)
        return classic_res

    def set_futures_leverage(
        self,
        symbol: str,
        leverage: int,
        product_type: str = "USDT-FUTURES"
    ) -> Dict[str, Any]:
        """Set leverage for futures contract."""
        payload = {
            "symbol": symbol,
            "productType": product_type,
            "leverage": str(leverage),
            "marginCoin": "USDT"
        }
        return self._request("POST", "/api/v2/mix/account/set-leverage", data=payload, signed=True)


# Global Bitget Client Singleton
bitget_client = BitgetClient()
