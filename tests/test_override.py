"""Test model override functionality."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_runtime import AgentRuntime
from core.llm_connector import LLMResponse


def test_override_model_used():
    """Test that override_model is used when provided."""
    runtime = AgentRuntime()

    model_used = None

    def mock_call(model, system, user, temperature, max_tokens, fallback_order=None):
        nonlocal model_used
        model_used = model
        return LLMResponse(
            text="response",
            model=model,
            provider=model.split("/")[0],
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            duration_ms=100.0,
        )

    with patch.object(runtime.connector, "call", side_effect=mock_call):
        with patch("core.agent_runtime.write_json") as mock_write:
            mock_write.return_value = Path("test.json")

            result = runtime.run(
                "builder", "test", override_model="google/gemini-1.5-flash"
            )

            # Verify override model was used
            assert model_used == "google/gemini-1.5-flash"
            assert result.model == "google/gemini-1.5-flash"


def test_default_model_used_without_override():
    """Test that default model is used when no override."""
    runtime = AgentRuntime()

    model_used = None

    def mock_call(model, system, user, temperature, max_tokens, fallback_order=None):
        nonlocal model_used
        model_used = model
        return LLMResponse(
            text="response",
            model=model,
            provider=model.split("/")[0],
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            duration_ms=100.0,
        )

    with patch.object(runtime.connector, "call", side_effect=mock_call):
        with patch("core.agent_runtime.write_json") as mock_write:
            mock_write.return_value = Path("test.json")

            _ = runtime.run("builder", "test")

            # Verify default model from config was used
            assert "claude" in model_used.lower() or "gpt" in model_used.lower()
