"""Tests for Bitget UTA v3 REST Client and HMAC-SHA256 signature verification."""

import base64
import hashlib
import hmac
import pytest
from src.bitget.client import BitgetClient, format_bitget_error


def test_hmac_signature_generation():
    client = BitgetClient(api_key="test_key", api_secret="test_secret", passphrase="test_passphrase")
    timestamp = "1726500000000"
    method = "POST"
    path = "/api/v2/spot/trade/place-order"
    body = '{"symbol":"BTCUSDT","side":"buy"}'

    sig = client._generate_signature(timestamp, method, path, body)

    # Compute expected
    expected_sign_str = timestamp + "POST" + path + body
    mac = hmac.new(b"test_secret", expected_sign_str.encode("utf-8"), hashlib.sha256)
    expected_sig = base64.b64encode(mac.digest()).decode("utf-8")

    assert sig == expected_sig


def test_bitget_error_formatting():
    msg1 = format_bitget_error(40014, "decrypt error", "/api/v2/spot/account/assets")
    assert "OAuth" in msg1

    msg2 = format_bitget_error(40001, "access key error")
    assert "Agentic" in msg2 or "OAuth" in msg2

    msg3 = format_bitget_error(40017, "permission denied")
    assert "permissions" in msg3


def test_public_ticker_query():
    client = BitgetClient()
    # Query public spot tickers without credentials
    res = client.get_spot_tickers("BTCUSDT")
    assert res.get("success") is True
    assert "data" in res
