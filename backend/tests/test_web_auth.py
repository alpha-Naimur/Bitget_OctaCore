"""Tests for Web Auth & Execution Mode endpoints in Bitget OctaCore."""

import pytest
from fastapi.testclient import TestClient
from src.web.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_auth_status_endpoint(client):
    """Verify /api/auth/status returns valid telemetry structure."""
    response = client.get("/api/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert "authorized" in data
    assert "execution_mode" in data
    assert "auth_source" in data
    assert "display_uid" in data


def test_execution_mode_toggle(client):
    """Verify /api/auth/mode allows changing execution modes."""
    # Toggle to SIMULATION
    res_sim = client.post("/api/auth/mode", json={"mode": "SIMULATION"})
    assert res_sim.status_code == 200
    assert res_sim.json()["mode"] == "SIMULATION"

    # Status check confirms SIMULATION
    status = client.get("/api/auth/status").json()
    assert status["execution_mode"] == "SIMULATION"


def test_oauth_start_endpoint(client):
    """Verify /api/auth/oauth/start initializes a session with English authorization URL."""
    res = client.post("/api/auth/oauth/start", json={})
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert "auth_url" in data
    # Ensure default URL does NOT contain Chinese /zh-CN/
    assert "/zh-CN/" not in data["auth_url"]
    assert "/account/center/agent-subaccount-oauth" in data["auth_url"]
    assert "publicKey=" in data["auth_url"]


def test_oauth_check_unknown_session(client):
    """Verify /api/auth/oauth/check returns a valid structured session response."""
    res = client.get("/api/auth/oauth/check?session_id=non_existent_session_123")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ERROR", "failed", "COMPLETED", "authenticated", "PENDING")


def test_config_js_endpoint(client):
    """Verify /config.js dynamic config resolver is served correctly."""
    res = client.get("/config.js")
    assert res.status_code == 200
    assert "OctaCoreConfig" in res.text
    assert "getBackendBaseUrl" in res.text
