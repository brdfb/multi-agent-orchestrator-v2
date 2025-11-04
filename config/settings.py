"""Configuration and settings management."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

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


# Provider management
def _is_truthy(value: Optional[str]) -> bool:
    """Check if environment variable value is truthy."""
    if not value:
        return False
    return value.lower() in ("1", "true", "yes", "on")


def is_provider_enabled(provider: str) -> bool:
    """
    Check if a provider is enabled based on API key availability and feature flags.

    Args:
        provider: Provider name (openai, anthropic, google, openrouter)

    Returns:
        True if provider is enabled, False otherwise
    """
    provider = provider.lower()

    # Check for explicit disable flag
    disable_flags = {
        "openai": "DISABLE_OPENAI",
        "anthropic": "DISABLE_ANTHROPIC",
        "google": "DISABLE_GOOGLE",
        "openrouter": "DISABLE_OPENROUTER",
    }

    disable_flag = disable_flags.get(provider)
    if disable_flag and _is_truthy(os.getenv(disable_flag)):
        return False

    # Check if API key exists
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }

    env_var = key_map.get(provider)
    if not env_var:
        return False

    return bool(os.getenv(env_var))


def get_available_providers() -> List[str]:
    """
    Get list of available (enabled) providers.

    Returns:
        List of enabled provider names
    """
    all_providers = ["openai", "anthropic", "google", "openrouter"]
    return [p for p in all_providers if is_provider_enabled(p)]


def get_provider_status() -> Dict[str, Dict[str, Any]]:
    """
    Get detailed status for all providers.

    Returns:
        Dict with provider status information
    """
    providers = ["openai", "anthropic", "google", "openrouter"]
    status = {}

    for provider in providers:
        enabled = is_provider_enabled(provider)
        has_key = bool(
            os.getenv(
                {
                    "openai": "OPENAI_API_KEY",
                    "anthropic": "ANTHROPIC_API_KEY",
                    "google": "GOOGLE_API_KEY",
                    "openrouter": "OPENROUTER_API_KEY",
                }.get(provider)
            )
        )

        disabled_by_flag = _is_truthy(os.getenv(f"DISABLE_{provider.upper()}"))

        status[provider] = {
            "enabled": enabled,
            "has_api_key": has_key,
            "disabled_by_flag": disabled_by_flag,
        }

    return status


def get_env_source() -> str:
    """
    Detect where API keys are loaded from and show provider status.

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
            if any(
                f"{key}=" in env_content and f"#{key}=" not in line
                for line in env_content.split("\n")
                for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
            ):
                return "dotenv"

    return "environment"  # Shell export, CI, or system env


def load_agents_config() -> Dict[str, Any]:
    """Load agents configuration from YAML."""
    config_path = CONFIG_DIR / "agents.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_memory_config() -> Dict[str, Any]:
    """Load memory system configuration from YAML."""
    config_path = CONFIG_DIR / "memory.yaml"
    if not config_path.exists():
        # Return defaults if config doesn't exist
        return {
            "memory": {
                "enabled": True,
                "backend": "sqlite",
                "db_path": "data/MEMORY/conversations.db",
                "context": {
                    "enabled_default": True,
                    "max_context_tokens_default": 500,
                    "max_snippet_tokens": 120,
                    "strategy_default": "keywords",
                    "joiner": "\n---\n",
                    "prompt_header": "[MEMORY CONTEXT - Relevant past conversations]\n",
                },
            }
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class ProviderUnavailableError(Exception):
    """Raised when a provider is unavailable (disabled or missing API key)."""

    pass


def get_api_key(provider: str, optional: bool = False) -> Optional[str]:
    """
    Get API key for a provider from environment.

    Args:
        provider: Provider name (openai, anthropic, google, openrouter)
        optional: If True, return None instead of raising error when key is missing

    Returns:
        API key string or None (if optional=True and key missing)

    Raises:
        ValueError: Unknown provider
        ProviderUnavailableError: Provider disabled or missing key (if optional=False)
    """
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }

    env_var = key_map.get(provider.lower())
    if not env_var:
        raise ValueError(f"Unknown provider: {provider}")

    # Check if provider is disabled
    if not is_provider_enabled(provider):
        if optional:
            return None
        raise ProviderUnavailableError(
            f"Provider '{provider}' is disabled or missing API key"
        )

    key = os.getenv(env_var)
    if not key:
        if optional:
            return None
        raise ProviderUnavailableError(
            f"Missing API key: {env_var} not set in environment"
        )

    return key


# Cost estimation table (USD per 1M tokens)
COST_TABLE = {
    "anthropic/claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "openai/gpt-4o": {"input": 2.5, "output": 10.0},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "google/gemini-1.5-pro": {"input": 1.25, "output": 5.0},
    "google/gemini-1.5-flash": {"input": 0.075, "output": 0.3},
    "google/gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Free tier
    "google/gemini-2.0-pro-exp": {"input": 0.0, "output": 0.0},  # Experimental
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost for a model call (approximate)."""
    costs = COST_TABLE.get(model, {"input": 1.0, "output": 3.0})

    input_cost = (prompt_tokens / 1_000_000) * costs["input"]
    output_cost = (completion_tokens / 1_000_000) * costs["output"]

    return input_cost + output_cost
