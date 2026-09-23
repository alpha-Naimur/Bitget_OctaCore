"""Configuration management module for Bitget OctaCore with root .env support."""

import os
from enum import Enum
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve root and backend .env paths
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent if (BACKEND_DIR.parent / "submission").exists() or (BACKEND_DIR.parent / ".env").exists() else BACKEND_DIR
ENV_PATH = BACKEND_DIR / ".env" if (BACKEND_DIR / ".env").exists() else (ROOT_DIR / ".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)
if (ROOT_DIR / ".env").exists() and ROOT_DIR != BACKEND_DIR:
    load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)


class ExecutionMode(str, Enum):
    SIMULATION = "SIMULATION"
    TESTNET = "TESTNET"
    MAINNET = "MAINNET"
    SUB_ACCOUNT = "SUB_ACCOUNT"


class LLMProvider(str, Enum):
    QWEN = "qwen"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    RULE_BASED = "rule_based"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Execution Mode
    EXECUTION_MODE: ExecutionMode = Field(default=ExecutionMode.SIMULATION)

    # Bitget Agentic Account OAuth (Primary Authentication - Recommended)
    BITGET_OAUTH_ENABLED: bool = True
    BITGET_OAUTH_TOKEN_PATH: Optional[str] = None  # Defaults to ~/.bitget/oauth_token.json

    # Bitget API Credentials (Fallback / Legacy UTA v3)
    BITGET_API_KEY: Optional[str] = None
    BITGET_SECRET_KEY: Optional[str] = None
    BITGET_PASSPHRASE: Optional[str] = None
    BITGET_SUB_ACCOUNT_UID: Optional[str] = None

    # Bitget API Endpoints
    BITGET_REST_URL: str = "https://api.bitget.com"
    BITGET_DEMO_REST_URL: str = "https://api.bitget.com"
    BITGET_WS_URL: str = "wss://ws.bitget.com/v2/ws/public"

    # LLM Settings
    LLM_PROVIDER: LLMProvider = Field(default=LLMProvider.QWEN)
    LLM_MODEL: str = "qwen3.8-max"
    LLM_TEMPERATURE: float = 0.2

    # Alibaba Cloud Qwen (Official Sponsor for Bitget Hackathon S2)
    BITGET_QWEN_API_KEY: Optional[str] = None
    QWEN_BASE_URL: str = "https://hackathon.bitgetops.com/v1"

    # Google GenAI / Gemini
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "qwen/qwen-2.5-72b-instruct"

    # Risk Guardian Guardrails
    MAX_POSITION_SIZE_USD: float = 1000.0
    MAX_DRAWDOWN_PERCENT: float = 5.0
    MAX_SINGLE_ORDER_USD: float = 500.0
    DAILY_TRADE_LIMIT: int = 100
    MAX_SLIPPAGE_PERCENT: float = 1.0
    EMERGENCY_KILL_SWITCH_ACTIVE: bool = False

    # Simulator Defaults
    SIMULATOR_INITIAL_USDT: float = 10000.0
    SIMULATOR_FUTURES_MARGIN_USDT: float = 2000.0

    # News Sentinel & Macro Radar
    NEWS_SENTINEL_ENABLED: bool = True
    NEWS_POLL_INTERVAL_SECONDS: int = 60


# Global singleton instance
settings = Settings()
