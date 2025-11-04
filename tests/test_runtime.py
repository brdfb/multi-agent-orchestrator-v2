"""Test agent runtime with mocked LLM calls."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_runtime import AgentRuntime
from core.llm_connector import LLMResponse


def test_router_returns_valid_agent():
    """Test that router returns builder, critic, or closer."""
    runtime = AgentRuntime()

    # Mock LLM response
    mock_response = LLMResponse(
        text="builder",
        model="openai/gpt-4o-mini",
        provider="openai",
        prompt_tokens=10,
        completion_tokens=1,
        total_tokens=11,
        duration_ms=100.0,
    )

    with patch.object(runtime.connector, "call", return_value=mock_response):
        agent = runtime.route("Create a REST API")
        assert agent in ["builder", "critic", "closer"]


def test_router_defaults_to_builder_on_invalid():
    """Test that router defaults to builder on invalid response."""
    runtime = AgentRuntime()

    # Mock invalid response
    mock_response = LLMResponse(
        text="invalid_agent",
        model="openai/gpt-4o-mini",
        provider="openai",
        prompt_tokens=10,
        completion_tokens=1,
        total_tokens=11,
        duration_ms=100.0,
    )

    with patch.object(runtime.connector, "call", return_value=mock_response):
        agent = runtime.route("Some task")
        assert agent == "builder"


def test_run_with_mock():
    """Test run() with mocked LLM."""
    runtime = AgentRuntime()

    mock_response = LLMResponse(
        text="This is a test response",
        model="anthropic/claude-3-5-sonnet-20241022",
        provider="anthropic",
        prompt_tokens=50,
        completion_tokens=20,
        total_tokens=70,
        duration_ms=250.0,
    )

    with patch.object(runtime.connector, "call", return_value=mock_response):
        with patch("core.agent_runtime.write_json") as mock_write:
            mock_write.return_value = Path("test.json")

            result = runtime.run("builder", "Test prompt")

            assert result.agent == "builder"
            assert result.response == "This is a test response"
            assert result.total_tokens == 70
            assert result.error is None
