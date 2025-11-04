"""Test chain execution."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_runtime import AgentRuntime, RunResult


def test_chain_returns_three_results():
    """Test that chain returns 3 results by default."""
    runtime = AgentRuntime()

    # Mock results for each stage
    mock_results = [
        RunResult(
            agent="builder",
            model="test/model",
            provider="test",
            prompt="test",
            response="builder response",
            duration_ms=100.0,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            timestamp="2024-01-01T00:00:00",
            log_file="test1.json",
        ),
        RunResult(
            agent="critic",
            model="test/model",
            provider="test",
            prompt="test",
            response="critic response",
            duration_ms=100.0,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            timestamp="2024-01-01T00:00:00",
            log_file="test2.json",
        ),
        RunResult(
            agent="closer",
            model="test/model",
            provider="test",
            prompt="test",
            response="closer response",
            duration_ms=100.0,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            timestamp="2024-01-01T00:00:00",
            log_file="test3.json",
        ),
    ]

    call_count = 0

    def mock_run(agent, prompt, override_model=None):
        nonlocal call_count
        result = mock_results[call_count]
        call_count += 1
        return result

    with patch.object(runtime, "run", side_effect=mock_run):
        results = runtime.chain("test prompt")

        assert len(results) == 3
        assert results[0].agent == "builder"
        assert results[1].agent == "critic"
        assert results[2].agent == "closer"


def test_chain_validates_agent_names():
    """Test that chain executes correct agents in order."""
    runtime = AgentRuntime()

    agents_called = []

    def mock_run(agent, prompt, override_model=None):
        agents_called.append(agent)
        return RunResult(
            agent=agent,
            model="test/model",
            provider="test",
            prompt=prompt,
            response=f"{agent} response",
            duration_ms=100.0,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            timestamp="2024-01-01T00:00:00",
            log_file=f"test-{agent}.json",
        )

    with patch.object(runtime, "run", side_effect=mock_run):
        runtime.chain("test", stages=["builder", "critic"])

        assert agents_called == ["builder", "critic"]
