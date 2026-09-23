"""Unit tests for Bitget Agentic Account OAuth 2.0 implementation."""

import base64
import json
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from src.bitget.oauth import BitgetOAuthManager, oauth_manager
from src.bitget.client import BitgetClient


def test_rsa_keypair_generation():
    """Verify ephemeral RSA-2048 keypair generation and SPKI serialization."""
    private_key, public_key_b64 = BitgetOAuthManager.generate_session_keypair()

    assert isinstance(private_key, rsa.RSAPrivateKey)
    assert private_key.key_size == 2048
    assert len(public_key_b64) > 100

    # Ensure public key decodes from base64
    der_bytes = base64.b64decode(public_key_b64)
    assert len(der_bytes) > 200


def test_rsa_split_codec_decryption():
    """Verify split-codec RSA-2048 PKCS#1 v1.5 decryption matches Bitget specification."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    mock_account = {
        "userId": "100928374",
        "apiKey": "bg_agent_live_key_9988",
        "secretKey": "super_secret_hmac_sha256_key_data",
        "passphrase": "agent_passphrase_123"
    }
    payload_str = json.dumps(mock_account)
    payload_bytes = payload_str.encode("utf-8")

    # In Bitget protocol, if payload is longer than 200 bytes, it's chunked into 256-byte blocks
    # Max plaintext size for 2048-bit RSA with PKCS1 v1.5 padding is 245 bytes
    chunk_size = 100
    cipher_chunks = []
    for i in range(0, len(payload_bytes), chunk_size):
        chunk = payload_bytes[i : i + chunk_size]
        encrypted_block = public_key.encrypt(chunk, padding.PKCS1v15())
        assert len(encrypted_block) == 256
        cipher_chunks.append(encrypted_block)

    full_ciphertext = b"".join(cipher_chunks)
    b64url_cipher = base64.urlsafe_b64encode(full_ciphertext).decode("utf-8")

    decrypted = BitgetOAuthManager.decrypt_account_data(b64url_cipher, private_key)

    assert decrypted["userId"] == "100928374"
    assert decrypted["apiKey"] == "bg_agent_live_key_9988"
    assert decrypted["secretKey"] == "super_secret_hmac_sha256_key_data"
    assert decrypted["passphrase"] == "agent_passphrase_123"


def test_oauth_credentials_storage_lifecycle(tmp_path: Path):
    """Test saving, loading, status reporting, and revoking OAuth credentials."""
    test_token_path = tmp_path / ".bitget" / "oauth_token.json"
    manager = BitgetOAuthManager(token_path=test_token_path)

    # Initial state: unauthenticated
    assert manager.load_credentials() is None
    status_initial = manager.get_auth_status()
    assert status_initial["authorized"] is False

    # Save credentials
    sample_creds = {
        "userId": "99281726",
        "apiKey": "bg_agent_key_abc123",
        "secretKey": "sec_key_xyz",
        "passphrase": "pass_secure_9",
        "obtainedAt": "2026-09-17T12:00:00Z"
    }
    manager.save_credentials(sample_creds)

    # Load credentials
    loaded = manager.load_credentials()
    assert loaded is not None
    assert loaded["userId"] == "99281726"
    assert loaded["apiKey"] == "bg_agent_key_abc123"

    # Status check
    status = manager.get_auth_status()
    assert status["authorized"] is True
    assert status["user_id"] == "99281726"
    assert status["api_key_masked"] == "bg_a...c123"

    # Revoke
    assert manager.revoke_credentials() is True
    assert not test_token_path.exists()
    assert manager.load_credentials() is None


def test_start_oauth_flow():
    """Verify start_oauth_flow sets up callback listener and valid authorize URL."""
    manager = BitgetOAuthManager()
    flow = manager.start_oauth_flow()

    try:
        assert "session_id" in flow
        assert "authorize_url" in flow
        assert "callback_port" in flow
        assert flow["callback_port"] > 1024

        auth_url = flow["authorize_url"]
        assert "https://www.bitget.com" in auth_url
        assert "publicKey=" in auth_url
        assert "clientServerIpAddress=127.0.0.1" in auth_url
        assert f"clientServerPort={flow['callback_port']}" in auth_url
    finally:
        manager._cleanup_session(flow["session_id"])


def test_client_loads_oauth_credentials(tmp_path: Path, monkeypatch):
    """Verify BitgetClient prioritizes OAuth tokens over .env fallback."""
    test_token_path = tmp_path / "oauth_token.json"
    sample_creds = {
        "userId": "888777",
        "apiKey": "bg_oauth_client_key",
        "secretKey": "oauth_client_secret",
        "passphrase": "oauth_passphrase",
        "obtainedAt": "2026-09-17T12:00:00Z"
    }
    test_token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_token_path, "w", encoding="utf-8") as f:
        json.dump(sample_creds, f)

    test_manager = BitgetOAuthManager(token_path=test_token_path)
    monkeypatch.setattr("src.bitget.client.oauth_manager", test_manager)

    client = BitgetClient()
    assert client.auth_source == "AGENTIC_OAUTH"
    assert client.api_key == "bg_oauth_client_key"
    assert client.api_secret == "oauth_client_secret"
    assert client.passphrase == "oauth_passphrase"
    assert client.user_id == "888777"
    assert client.has_valid_credentials() is True
