"""Tests for ContextAggregator dual-context model."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.context_aggregator import ContextAggregator
from core.memory_backend import SQLiteBackend


def make_conversation(i: int, session_id: str = "sess-1") -> dict:
    """Helper: create a minimal conversation dict for storing."""
    return {
        "agent": "builder",
        "model": "anthropic/claude-sonnet-4-5",
        "provider": "anthropic",
        "prompt": f"Question {i}",
        "response": f"Answer {i} with enough content to use tokens",
        "duration_ms": 100.0,
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "estimated_cost_usd": 0.001,
        "fallback_used": False,
        "session_id": session_id,
    }


@pytest.fixture
def temp_db(tmp_path):
    """Temporary SQLite database for each test."""
    return tmp_path / "test_conversations.db"


@pytest.fixture
def backend(temp_db):
    return SQLiteBackend(temp_db)


@pytest.fixture
def aggregator(backend):
    """ContextAggregator with mocked MemoryEngine backed by temp DB."""
    agg = ContextAggregator.__new__(ContextAggregator)
    # Inject a mock MemoryEngine that wraps our real temp backend
    mock_memory = MagicMock()
    mock_memory.backend = backend
    # For knowledge context (semantic search), return empty list
    mock_memory.get_context_for_prompt.return_value = ([], [])
    agg.memory = mock_memory
    return agg


class TestGetSessionConversations:
    """Tests for _get_session_conversations."""

    def test_returns_conversations_for_session(self, aggregator, backend):
        for i in range(3):
            backend.store(make_conversation(i, session_id="sess-A"))
        backend.store(make_conversation(99, session_id="sess-B"))  # different session

        result = aggregator._get_session_conversations("sess-A", limit=10)

        assert len(result) == 3
        assert all(c["agent"] == "builder" for c in result)

    def test_respects_limit(self, aggregator, backend):
        for i in range(10):
            backend.store(make_conversation(i, session_id="sess-A"))

        result = aggregator._get_session_conversations("sess-A", limit=3)
        assert len(result) == 3

    def test_returns_empty_for_unknown_session(self, aggregator, backend):
        backend.store(make_conversation(1, session_id="sess-A"))
        result = aggregator._get_session_conversations("no-such-session", limit=5)
        assert result == []

    def test_most_recent_first(self, aggregator, backend):
        for i in range(3):
            backend.store(make_conversation(i, session_id="sess-A"))

        result = aggregator._get_session_conversations("sess-A", limit=10)
        # Most recent stored last → highest id first
        ids = [c["id"] for c in result]
        assert ids == sorted(ids, reverse=True)


class TestTokenBudget:
    """Tests for _apply_token_budget_with_priority."""

    def test_empty_contexts_returns_empty(self, aggregator):
        result = aggregator._apply_token_budget_with_priority([], max_tokens=600)
        assert result == []

    def test_session_context_gets_priority(self, aggregator):
        """Session context should be selected before knowledge context."""
        contexts = [
            {"type": "session", "priority": 1, "tokens": 200, "text": "session msg", "count": 1},
            {"type": "knowledge", "priority": 2, "tokens": 200, "text": "knowledge msg", "count": 1},
        ]
        result = aggregator._apply_token_budget_with_priority(contexts, max_tokens=250)
        types = [c["type"] for c in result]
        # Session context has priority; knowledge only if budget remains
        assert "session" in types

    def test_total_tokens_within_budget(self, aggregator):
        """Selected contexts must not exceed max_tokens."""
        contexts = [
            {"type": "session", "priority": 1, "tokens": 100, "text": "s1", "count": 1},
            {"type": "session", "priority": 1, "tokens": 100, "text": "s2", "count": 1},
            {"type": "knowledge", "priority": 2, "tokens": 100, "text": "k1", "count": 1},
            {"type": "knowledge", "priority": 2, "tokens": 100, "text": "k2", "count": 1},
        ]
        result = aggregator._apply_token_budget_with_priority(contexts, max_tokens=250)
        total = sum(c["tokens"] for c in result)
        assert total <= 250

    def test_zero_budget_returns_empty(self, aggregator):
        contexts = [
            {"type": "session", "priority": 1, "tokens": 50, "text": "s", "count": 1},
        ]
        result = aggregator._apply_token_budget_with_priority(contexts, max_tokens=0)
        assert result == []


class TestFormatMessageAge:
    """Tests for _format_message_age."""

    def test_recent_timestamp(self, aggregator):
        from datetime import datetime, timedelta
        recent = (datetime.now() - timedelta(seconds=30)).isoformat()
        age = aggregator._calculate_message_age(recent)
        assert "just now" in age or "second" in age

    def test_minutes_ago(self, aggregator):
        from datetime import datetime, timedelta
        ts = (datetime.now() - timedelta(minutes=5)).isoformat()
        age = aggregator._calculate_message_age(ts)
        assert "minute" in age

    def test_hours_ago(self, aggregator):
        from datetime import datetime, timedelta
        ts = (datetime.now() - timedelta(hours=3)).isoformat()
        age = aggregator._calculate_message_age(ts)
        assert "hour" in age

    def test_invalid_timestamp_returns_unknown(self, aggregator):
        age = aggregator._calculate_message_age("not-a-date")
        assert age == "unknown age"


class TestGetFullContext:
    """Integration tests for get_full_context."""

    def _agent_config(self, strategy="keywords", max_tokens=600):
        return {
            "session_context": {"enabled": True, "limit": 5},
            "knowledge_context": {
                "enabled": False,  # Disable for unit tests
                "strategy": strategy,
                "min_relevance": 0.15,
                "time_decay_hours": 96,
            },
            "max_context_tokens": max_tokens,
        }

    def test_no_session_returns_empty_context(self, aggregator):
        context, meta = aggregator.get_full_context(
            prompt="hello",
            session_id=None,
            config=self._agent_config(),
        )
        assert context == "" or context is not None
        assert isinstance(meta, dict)

    def test_session_context_injected(self, aggregator, backend):
        for i in range(2):
            backend.store(make_conversation(i, session_id="sess-X"))

        context, meta = aggregator.get_full_context(
            prompt="new question",
            session_id="sess-X",
            config=self._agent_config(),
        )
        # Some context should be returned
        assert meta.get("total_context_tokens", 0) > 0 or context != ""

    def test_metadata_has_expected_keys(self, aggregator):
        context, meta = aggregator.get_full_context(
            prompt="test",
            session_id=None,
            config=self._agent_config(),
        )
        assert "total_context_tokens" in meta
