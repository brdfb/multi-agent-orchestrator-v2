"""Configuration and settings management."""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
CONVERSATIONS_DIR = DATA_DIR / "CONVERSATIONS"

# Ensure directories exist
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

# Load .env only if it exists (optional for development)
# Environment variables take precedence over .env file
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=False)  # Don't override existing env vars


def get_env_source() -> str:
    """
    Detect where API keys are loaded from.

    Returns:
        String indicating the source of environment variables
    """
    has_env_keys = any(
        os.getenv(key)
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    )

    if not has_env_keys:
        return "none"

    env_file = BASE_DIR / ".env"
    if env_file.exists():
        # Check if keys match .env file content
        with open(env_file, "r") as f:
            env_content = f.read()
            # Simple heuristic: if .env has uncommented keys, assume it's the source
            if any(f"{key}=" in env_content and not f"#{key}=" in line
                   for line in env_content.split("\n")
                   for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]):
                return "dotenv"

    return "environment"  # Shell export, CI, or system env


def load_agents_config() -> Dict[str, Any]:
    """Load agents configuration from YAML."""
    config_path = CONFIG_DIR / "agents.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_api_key(provider: str) -> str:
    """Get API key for a provider from environment."""
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }

    env_var = key_map.get(provider.lower())
    if not env_var:
        raise ValueError(f"Unknown provider: {provider}")

    key = os.getenv(env_var)
    if not key:
        raise ValueError(f"Missing API key: {env_var} not set in environment")

    return key


# Cost estimation table (USD per 1M tokens)
COST_TABLE = {
    "anthropic/claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "openai/gpt-4o": {"input": 2.5, "output": 10.0},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "google/gemini-1.5-pro": {"input": 1.25, "output": 5.0},
    "google/gemini-1.5-flash": {"input": 0.075, "output": 0.3},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost for a model call (approximate)."""
    costs = COST_TABLE.get(model, {"input": 1.0, "output": 3.0})

    input_cost = (prompt_tokens / 1_000_000) * costs["input"]
    output_cost = (completion_tokens / 1_000_000) * costs["output"]

    return input_cost + output_cost
