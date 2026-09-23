"""Tests for Master Agent Orchestrator and specialist cores."""

import pytest
from src.core.orchestrator import orchestrator


def test_cores_status():
    cores = orchestrator.get_cores_status()
    assert len(cores) == 8
    for c in cores:
        assert c["status"] == "ACTIVE"


def test_orchestrator_query_processing():
    res = orchestrator.process_command("Analyze NVDAUSDT technicals and order book")
    assert "response" in res
    assert res["cores_active"] == 8
    assert "NVDAUSDT" in res["response"] or "NVDA" in res["response"]


def test_orchestrator_stock_radar_intent():
    res = orchestrator.process_command("Scan tokenized US stocks")
    resp_lower = res["response"].lower()
    assert "7x24" in resp_lower or "us equities" in resp_lower or "tokenized" in resp_lower


def test_openrouter_fallback_when_genai_qwen_unavailable(monkeypatch):
    from src.core.llm_client import llm_agent
    from src.core.config import settings, LLMProvider

    # Simulate Qwen and Gemini unavailable
    monkeypatch.setattr(llm_agent, "_try_call_qwen", lambda prompt: None)
    monkeypatch.setattr(llm_agent, "_try_call_gemini", lambda prompt: None)
    monkeypatch.setattr(
        llm_agent,
        "_try_call_openrouter",
        lambda prompt: {
            "provider": "OpenRouter (qwen/qwen-2.5-72b-instruct)",
            "response": "Institutional multi-asset analysis successfully synthesized via OpenRouter.",
            "tool_calls": []
        }
    )

    # When provider is default (qwen) but qwen and gemini are unavailable
    monkeypatch.setattr(settings, "LLM_PROVIDER", LLMProvider.QWEN)
    res = llm_agent.run_agent_turn("Evaluate market risk for NVDAUSDT")
    assert "OpenRouter" in res["provider"]
    assert "OpenRouter" in res["response"]


def test_openrouter_mock_client_tool_execution(monkeypatch):
    from src.core.llm_client import llm_agent
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.tool_calls = None
    mock_choice.message.content = "Synthesized analysis via OpenRouter Ling Flash."
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_resp

    monkeypatch.setattr(llm_agent, "openrouter_client", mock_client)
    res = llm_agent._try_call_openrouter("Analyze BTCUSDT")
    assert res is not None
    assert "OpenRouter" in res["provider"]
    assert res["response"] == "Synthesized analysis via OpenRouter Ling Flash."


def test_cascade_fallback_to_deterministic_when_all_fail(monkeypatch):
    from src.core.llm_client import llm_agent

    # Simulate all LLM providers failing / unavailable
    monkeypatch.setattr(llm_agent, "_try_call_qwen", lambda prompt: None)
    monkeypatch.setattr(llm_agent, "_try_call_gemini", lambda prompt: None)
    monkeypatch.setattr(llm_agent, "_try_call_openrouter", lambda prompt: None)

    res = llm_agent.run_agent_turn("Scan tokenized US stocks")
    assert "Deterministic Fallback" in res["provider"]
    assert "7x24" in res["response"] or "US Equities" in res["response"]
