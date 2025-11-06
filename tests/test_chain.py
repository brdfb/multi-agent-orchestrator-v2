"""Test chain execution."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_runtime import AgentRuntime, RunResult


def test_chain_returns_three_results():
    """Test that chain returns 4 results with multi-critic consensus (v0.9.0+)."""
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

        # v0.9.0+: builder → individual critics → multi-critic consensus → closer (4 results)
        assert len(results) == 4
        assert results[0].agent == "builder"
        assert results[1].agent == "critic"  # Individual critic (mocked)
        assert results[2].agent == "multi-critic"  # Consensus result
        assert results[3].agent == "closer"


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

        # v0.9.0+: With multi-critic enabled, individual critics run + consensus
        # Expected: builder → [individual critics] → multi-critic consensus
        assert "builder" in agents_called
        # Dynamic selection may choose 1-3 critics, so check for any critic execution
        assert any("critic" in agent for agent in agents_called)
