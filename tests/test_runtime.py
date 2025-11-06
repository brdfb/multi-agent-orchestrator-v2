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


def test_intelligent_truncate():
    """Test intelligent truncation fallback."""
    runtime = AgentRuntime()

    # Short text - no truncation
    short_text = "This is a short text."
    result = runtime._intelligent_truncate(short_text, 100)
    assert result == short_text

    # Long text with sentence boundary
    long_text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    result = runtime._intelligent_truncate(long_text, 40)
    assert result.endswith(".")
    assert len(result) <= 45  # Allow some margin
    assert "First sentence" in result

    # Long text without good sentence boundary
    no_punctuation = "a" * 100
    result = runtime._intelligent_truncate(no_punctuation, 50)
    assert result.endswith("...")
    assert len(result) <= 53


def test_compress_semantic():
    """Test semantic compression with mock LLM."""
    runtime = AgentRuntime()

    long_output = """
    I recommend using PostgreSQL for the database because it provides ACID guarantees
    which are essential for financial transactions. However, this comes with the trade-off
    of more complex horizontal scaling compared to NoSQL solutions like MongoDB.

    For authentication, I suggest JWT tokens with 15-minute expiry and refresh tokens
    stored in Redis for fast session lookup.

    Open question: How should we handle PostgreSQL failover in production?
    """ * 10  # Make it long

    # Mock compression response
    mock_compressed = """{
  "key_decisions": ["PostgreSQL for database", "JWT with 15-min expiry"],
  "rationale": {"PostgreSQL": "ACID guarantees for transactions", "JWT": "Stateless auth"},
  "trade_offs": ["PostgreSQL harder to scale horizontally than MongoDB"],
  "open_questions": ["PostgreSQL failover strategy?"],
  "technical_specs": {"database": "PostgreSQL", "auth": "JWT", "cache": "Redis"}
}"""

    mock_response = LLMResponse(
        text=mock_compressed,
        model="gemini/gemini-flash-latest",
        provider="google",
        prompt_tokens=500,
        completion_tokens=100,
        total_tokens=600,
        duration_ms=200.0,
    )

    with patch.object(runtime.connector, "call", return_value=mock_response):
        result = runtime._compress_semantic(long_output, max_tokens=500)
        assert "key_decisions" in result
        assert "PostgreSQL" in result
        assert len(result) < len(long_output)  # Should be compressed


def test_compress_semantic_fallback():
    """Test semantic compression falls back to truncation on error."""
    runtime = AgentRuntime()

    long_text = "a" * 5000

    # Mock failed compression
    mock_response = LLMResponse(
        text="",
        model="gemini/gemini-flash-latest",
        provider="google",
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        duration_ms=100.0,
        error="API error",
    )

    with patch.object(runtime.connector, "call", return_value=mock_response):
        result = runtime._compress_semantic(long_text, max_tokens=500)
        # Should fallback to intelligent truncation
        assert len(result) <= 2100  # 500 tokens * 4 chars + "..."
        assert isinstance(result, str)


def test_extract_critical_issues_with_keywords():
    """Test extraction of critical issues based on keywords."""
    runtime = AgentRuntime()

    critique_text = """
    Issue 1: API Gateway - Technology Choice (Kong)

    Problem: While Kong is a valid API Gateway, it's a relatively heavy solution.
    Impact: Increased operational overhead, potentially higher latency.

    CRITICAL: Missing authentication validation in WebSocket server.
    This is a SECURITY vulnerability that must be fixed immediately.

    Issue 2: Document Service - CRDT Implementation Details

    ERROR: The code uses the wrong CRDT library. Should use Yjs instead of custom implementation.
    This is INCORRECT and will cause data corruption.
    """

    result = runtime._extract_critical_issues(critique_text)

    assert result is not None
    assert "CRITICAL" in result or "SECURITY" in result
    assert "ERROR" in result or "INCORRECT" in result


def test_extract_critical_issues_no_issues():
    """Test that no issues are extracted from positive feedback."""
    runtime = AgentRuntime()

    critique_text = """
    The implementation looks good overall. The architecture is sound,
    and the code follows best practices. I have no major concerns.

    Some minor suggestions:
    - Consider adding more comments
    - Could add more unit tests
    """

    result = runtime._extract_critical_issues(critique_text)
    assert result is None


def test_extract_critical_issues_with_config():
    """Test that critical issue extraction uses config keywords."""
    runtime = AgentRuntime()

    # Verify config is loaded
    refinement_config = runtime.config.get("refinement", {})
    assert "critical_keywords" in refinement_config
    assert "CRITICAL" in refinement_config["critical_keywords"]
    assert "ERROR" in refinement_config["critical_keywords"]


def test_extract_critical_issues_edge_cases():
    """Test edge cases for critical issue extraction."""
    runtime = AgentRuntime()

    # Empty text
    assert runtime._extract_critical_issues("") is None
    assert runtime._extract_critical_issues(None) is None

    # Text with lowercase keywords (should still match via uppercase conversion)
    text_lowercase = "This is a critical bug that needs fixing."
    result = runtime._extract_critical_issues(text_lowercase)
    assert result is not None
    assert "critical" in result.lower()


def test_refinement_config_loaded():
    """Test that refinement configuration is properly loaded."""
    runtime = AgentRuntime()

    refinement_config = runtime.config.get("refinement", {})

    # Check all expected config keys exist
    assert "enabled" in refinement_config
    assert "max_iterations" in refinement_config
    assert "min_critical_issues" in refinement_config
    assert "critical_keywords" in refinement_config

    # Verify types
    assert isinstance(refinement_config["enabled"], bool)
    assert isinstance(refinement_config["max_iterations"], int)
    assert isinstance(refinement_config["critical_keywords"], list)

    # Verify expected values (v0.8.0: multi-iteration)
    assert refinement_config["max_iterations"] == 3  # Multi-iteration refinement


def test_check_convergence_no_issues():
    """Test convergence when no critical issues found."""
    runtime = AgentRuntime()

    # No current issues = converged (success)
    converged, reason = runtime._check_convergence(None, "previous issues")
    assert converged is True
    assert "No critical issues" in reason


def test_check_convergence_first_iteration():
    """Test that first iteration always continues."""
    runtime = AgentRuntime()

    # First iteration (previous_issues = None) = always continue
    converged, reason = runtime._check_convergence("some issues", None)
    assert converged is False
    assert "First iteration" in reason


def test_check_convergence_progress():
    """Test convergence detection with progress (fewer issues)."""
    runtime = AgentRuntime()

    previous_issues = """
    Issue 1: Problem A
    Issue 2: Problem B
    Issue 3: Problem C
    """

    current_issues = """
    Issue 1: Problem A
    """

    # Fewer issues = progress = continue
    converged, reason = runtime._check_convergence(current_issues, previous_issues)
    assert converged is False
    assert "Progress detected" in reason
    assert "3 → 1" in reason  # Shows issue count reduction


def test_check_convergence_no_progress():
    """Test convergence when no progress is made."""
    runtime = AgentRuntime()

    previous_issues = """
    Issue 1: Problem A
    Issue 2: Problem B
    """

    current_issues = """
    Issue 1: Problem X
    Issue 2: Problem Y
    Issue 3: Problem Z
    """

    # More issues = no progress = stop
    converged, reason = runtime._check_convergence(current_issues, previous_issues)
    assert converged is True
    assert "No progress" in reason
    assert "2 → 3" in reason  # Shows issue count increase


def test_check_convergence_same_count():
    """Test convergence when issue count stays the same."""
    runtime = AgentRuntime()

    previous_issues = """
    Issue 1: Problem A
    Issue 2: Problem B
    """

    current_issues = """
    Issue 1: Problem X
    Issue 2: Problem Y
    """

    # Same count = no progress = stop
    converged, reason = runtime._check_convergence(current_issues, previous_issues)
    assert converged is True
    assert "No progress" in reason


def test_multi_critic_config_loaded():
    """Test that multi-critic configuration is properly loaded."""
    runtime = AgentRuntime()

    multi_critic_config = runtime.config.get("multi_critic", {})

    # Check all expected config keys exist
    assert "enabled" in multi_critic_config
    assert "critics" in multi_critic_config
    assert "consensus" in multi_critic_config
    assert "parallel_execution" in multi_critic_config

    # Verify critics list
    critics = multi_critic_config.get("critics", [])
    assert isinstance(critics, list)
    assert len(critics) == 3
    assert "security-critic" in critics
    assert "performance-critic" in critics
    assert "code-quality-critic" in critics

    # Verify consensus config
    consensus = multi_critic_config.get("consensus", {})
    assert "threshold" in consensus
    assert "weights" in consensus
    assert consensus["threshold"] == 2

    # Verify weights
    weights = consensus.get("weights", {})
    assert weights["security-critic"] == 1.5
    assert weights["performance-critic"] == 1.0
    assert weights["code-quality-critic"] == 0.8


def test_merge_critic_consensus():
    """Test consensus merging with different weights."""
    runtime = AgentRuntime()

    critic_results = [
        ("security-critic", "SECURITY ISSUE: Missing input validation\nSECURITY ISSUE: Hardcoded credentials"),
        ("performance-critic", "PERFORMANCE ISSUE: N+1 query detected\nPERFORMANCE ISSUE: Missing database index"),
        ("code-quality-critic", "QUALITY ISSUE: Violation of SRP principle\nQUALITY ISSUE: High cyclomatic complexity"),
    ]

    consensus = runtime._merge_critic_consensus(critic_results)

    # Check that all critics are included
    assert "SECURITY-CRITIC" in consensus.upper()
    assert "PERFORMANCE-CRITIC" in consensus.upper()
    assert "CODE-QUALITY-CRITIC" in consensus.upper()

    # Check that consensus header exists
    assert "MULTI-CRITIC CONSENSUS" in consensus

    # Check that security critic is marked as high priority
    assert "HIGH PRIORITY" in consensus or "⚠️" in consensus

    # Check that all issues are preserved
    assert "Missing input validation" in consensus or "MISSING INPUT VALIDATION" in consensus
    assert "N+1 query" in consensus or "N+1 QUERY" in consensus
    assert "SRP principle" in consensus or "SRP PRINCIPLE" in consensus


def test_merge_critic_consensus_empty():
    """Test consensus merging with no critic results."""
    runtime = AgentRuntime()

    # Empty results should return empty string
    consensus = runtime._merge_critic_consensus([])
    assert consensus == ""


def test_merge_critic_consensus_single():
    """Test consensus merging with single critic."""
    runtime = AgentRuntime()

    critic_results = [
        ("security-critic", "SECURITY ISSUE: SQL injection vulnerability"),
    ]

    consensus = runtime._merge_critic_consensus(critic_results)

    assert "MULTI-CRITIC CONSENSUS" in consensus
    assert "SECURITY-CRITIC" in consensus.upper()
    assert "SQL injection" in consensus or "SQL INJECTION" in consensus


def test_run_multi_critic_disabled():
    """Test that multi-critic returns empty when disabled."""
    runtime = AgentRuntime()

    # Temporarily disable multi-critic
    original_enabled = runtime.config.get("multi_critic", {}).get("enabled", False)
    runtime.config["multi_critic"]["enabled"] = False

    try:
        consensus, results = runtime._run_multi_critic("Test response", "Test prompt")
        assert consensus == ""
        assert results == []
    finally:
        # Restore original state
        runtime.config["multi_critic"]["enabled"] = original_enabled


def test_run_multi_critic_with_mock():
    """Test multi-critic execution with mocked LLM calls."""
    runtime = AgentRuntime()

    # Mock responses for each critic
    mock_responses = {
        "security-critic": LLMResponse(
            text="SECURITY ISSUE: Missing authentication",
            model="openai/gpt-4o",
            provider="openai",
            prompt_tokens=50,
            completion_tokens=20,
            total_tokens=70,
            duration_ms=200.0,
        ),
        "performance-critic": LLMResponse(
            text="PERFORMANCE ISSUE: Inefficient algorithm",
            model="gemini/gemini-2.5-pro",
            provider="google",
            prompt_tokens=50,
            completion_tokens=20,
            total_tokens=70,
            duration_ms=180.0,
        ),
        "code-quality-critic": LLMResponse(
            text="QUALITY ISSUE: Poor error handling",
            model="openai/gpt-4o-mini",
            provider="openai",
            prompt_tokens=50,
            completion_tokens=20,
            total_tokens=70,
            duration_ms=150.0,
        ),
    }

    def mock_call_side_effect(model, **kwargs):
        # Determine which critic based on model
        if "gpt-4o" in model and "mini" not in model:
            return mock_responses["security-critic"]
        elif "gemini-2.5-pro" in model:
            return mock_responses["performance-critic"]
        elif "gpt-4o-mini" in model:
            return mock_responses["code-quality-critic"]
        return mock_responses["security-critic"]

    with patch.object(runtime.connector, "call", side_effect=mock_call_side_effect):
        with patch("core.agent_runtime.write_json") as mock_write:
            mock_write.return_value = Path("test.json")

            consensus, results = runtime._run_multi_critic("Test builder output", "Test prompt")

            # Check that all critics ran
            assert len(results) == 3

            # Check that consensus includes all issues
            assert "SECURITY ISSUE" in consensus or "Missing authentication" in consensus
            assert "PERFORMANCE ISSUE" in consensus or "Inefficient algorithm" in consensus
            assert "QUALITY ISSUE" in consensus or "Poor error handling" in consensus

            # Check token aggregation
            total_tokens = sum(r.total_tokens for r in results)
            assert total_tokens == 210  # 70 * 3
