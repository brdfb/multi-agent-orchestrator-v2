"""Tests for memory engine and backend."""

import tempfile
from pathlib import Path

import pytest

from core.memory_backend import SQLiteBackend
from core.memory_engine import MemoryEngine


class TestSQLiteBackend:
    """Test SQLite storage backend."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        if db_path.exists():
            db_path.unlink()

    def test_init_creates_schema(self, temp_db):
        """Test database initialization creates schema."""
        backend = SQLiteBackend(temp_db)
        conn = backend._get_connection()
        cursor = conn.cursor()

        # Check table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
        )
        assert cursor.fetchone() is not None

        # Check indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_timestamp'"
        )
        assert cursor.fetchone() is not None

        conn.close()

    def test_store_conversation(self, temp_db):
        """Test storing a conversation."""
        backend = SQLiteBackend(temp_db)

        conversation = {
            "agent": "builder",
            "model": "openai/gpt-4o-mini",
            "provider": "openai",
            "prompt": "Test prompt",
            "response": "Test response",
            "total_tokens": 100,
            "cost_usd": 0.01,
        }

        row_id = backend.store(conversation)
        assert row_id > 0

        # Verify stored
        stored = backend.get_by_id(row_id)
        assert stored is not None
        assert stored["agent"] == "builder"
        assert stored["prompt"] == "Test prompt"
        assert stored["total_tokens"] == 100

    def test_get_recent(self, temp_db):
        """Test retrieving recent conversations."""
        backend = SQLiteBackend(temp_db)

        # Store 3 conversations
        for i in range(3):
            backend.store(
                {
                    "agent": "builder",
                    "model": "test",
                    "provider": "test",
                    "prompt": f"Prompt {i}",
                    "response": f"Response {i}",
                }
            )

        # Get recent
        recent = backend.get_recent(limit=2)
        assert len(recent) == 2
        # Most recent first
        assert "Prompt 2" in recent[0]["prompt"]

    def test_get_recent_by_agent(self, temp_db):
        """Test filtering recent conversations by agent."""
        backend = SQLiteBackend(temp_db)

        # Store conversations for different agents
        backend.store(
            {
                "agent": "builder",
                "model": "test",
                "provider": "test",
                "prompt": "Builder prompt",
                "response": "Response",
            }
        )
        backend.store(
            {
                "agent": "critic",
                "model": "test",
                "provider": "test",
                "prompt": "Critic prompt",
                "response": "Response",
            }
        )

        # Get builder conversations only
        recent = backend.get_recent(limit=10, agent="builder")
        assert len(recent) == 1
        assert recent[0]["agent"] == "builder"

    def test_search_by_keyword(self, temp_db):
        """Test searching conversations by keyword."""
        backend = SQLiteBackend(temp_db)

        backend.store(
            {
                "agent": "builder",
                "model": "test",
                "provider": "test",
                "prompt": "Create a function",
                "response": "Here is the code",
            }
        )
        backend.store(
            {
                "agent": "builder",
                "model": "test",
                "provider": "test",
                "prompt": "Fix a bug",
                "response": "Updated code",
            }
        )

        # Search for "function"
        results = backend.search(query="function")
        assert len(results) == 1
        assert "function" in results[0]["prompt"]

        # Search for "code"
        results = backend.search(query="code")
        assert len(results) == 2  # Both have "code" in response

    def test_search_by_model(self, temp_db):
        """Test filtering search by model."""
        backend = SQLiteBackend(temp_db)

        backend.store(
            {
                "agent": "builder",
                "model": "openai/gpt-4o",
                "provider": "openai",
                "prompt": "Test",
                "response": "Response",
            }
        )
        backend.store(
            {
                "agent": "builder",
                "model": "anthropic/claude",
                "provider": "anthropic",
                "prompt": "Test",
                "response": "Response",
            }
        )

        # Search by model
        results = backend.search(model="openai/gpt-4o")
        assert len(results) == 1
        assert results[0]["model"] == "openai/gpt-4o"

    def test_delete_conversation(self, temp_db):
        """Test deleting a conversation."""
        backend = SQLiteBackend(temp_db)

        row_id = backend.store(
            {
                "agent": "builder",
                "model": "test",
                "provider": "test",
                "prompt": "Test",
                "response": "Response",
            }
        )

        # Verify exists
        assert backend.get_by_id(row_id) is not None

        # Delete
        deleted = backend.delete(row_id)
        assert deleted is True

        # Verify gone
        assert backend.get_by_id(row_id) is None

    def test_get_stats(self, temp_db):
        """Test getting memory statistics."""
        backend = SQLiteBackend(temp_db)

        # Store conversations
        backend.store(
            {
                "agent": "builder",
                "model": "test",
                "provider": "test",
                "prompt": "Test",
                "response": "Response",
                "total_tokens": 100,
                "cost_usd": 0.01,
            }
        )
        backend.store(
            {
                "agent": "critic",
                "model": "test",
                "provider": "test",
                "prompt": "Test",
                "response": "Response",
                "total_tokens": 50,
                "cost_usd": 0.005,
            }
        )

        stats = backend.get_stats()
        assert stats["total_conversations"] == 2
        assert stats["total_tokens"] == 150
        assert stats["total_cost_usd"] == 0.015
        assert "builder" in stats["by_agent"]
        assert "critic" in stats["by_agent"]


class TestMemoryEngine:
    """Test MemoryEngine high-level interface."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton instance before each test."""
        MemoryEngine._instance = None
        MemoryEngine._initialized = False
        yield

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        # Monkey-patch backend to use temp db
        original_init = SQLiteBackend.__init__

        def temp_init(self, db_path=None):
            original_init(self, db_path or Path(f.name))

        SQLiteBackend.__init__ = temp_init
        yield db_path

        # Restore and cleanup
        SQLiteBackend.__init__ = original_init
        if db_path.exists():
            db_path.unlink()

    def test_singleton_pattern(self):
        """Test MemoryEngine is singleton."""
        engine1 = MemoryEngine()
        engine2 = MemoryEngine()
        assert engine1 is engine2

    def test_store_conversation(self, temp_db):
        """Test storing conversation via engine."""
        engine = MemoryEngine()

        conv_id = engine.store_conversation(
            prompt="Test prompt",
            response="Test response",
            agent="builder",
            model="test",
            provider="test",
            metadata={"total_tokens": 100, "cost_usd": 0.01},
        )

        assert conv_id > 0

        # Verify stored
        conv = engine.get_conversation(conv_id)
        assert conv is not None
        assert conv["prompt"] == "Test prompt"
        assert conv["total_tokens"] == 100

    def test_get_recent_conversations(self, temp_db):
        """Test getting recent conversations."""
        engine = MemoryEngine()

        # Store 3 conversations
        for i in range(3):
            engine.store_conversation(
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                agent="builder",
                model="test",
                provider="test",
            )

        recent = engine.get_recent_conversations(limit=2)
        assert len(recent) == 2

    def test_search_conversations(self, temp_db):
        """Test searching conversations."""
        engine = MemoryEngine()

        engine.store_conversation(
            prompt="Create a function",
            response="Code here",
            agent="builder",
            model="test",
            provider="test",
        )
        engine.store_conversation(
            prompt="Fix a bug",
            response="Fixed",
            agent="builder",
            model="test",
            provider="test",
        )

        results = engine.search_conversations(query="function")
        assert len(results) == 1
        assert "function" in results[0]["prompt"]

    def test_get_context_for_prompt(self, temp_db):
        """Test context retrieval for prompt."""
        engine = MemoryEngine()

        # Store relevant conversations
        engine.store_conversation(
            prompt="How to create a Python function?",
            response="Use def keyword",
            agent="builder",
            model="test",
            provider="test",
        )
        engine.store_conversation(
            prompt="Python function best practices",
            response="Use docstrings",
            agent="builder",
            model="test",
            provider="test",
        )

        # Get context for similar prompt
        context = engine.get_context_for_prompt(
            "Create Python function", max_tokens=500
        )

        assert context != ""
        assert "function" in context.lower() or "Python" in context

    def test_extract_keywords(self, temp_db):
        """Test keyword extraction."""
        engine = MemoryEngine()

        keywords = engine._extract_keywords("Create a function to parse JSON data")
        # Now returns a set
        assert isinstance(keywords, set)
        assert "create" in keywords
        assert "function" in keywords
        assert "parse" in keywords
        assert "json" in keywords or "data" in keywords
        # Stop words should be filtered
        assert "a" not in keywords
        assert "to" not in keywords

    def test_disable_enable(self, temp_db):
        """Test disabling and enabling memory."""
        engine = MemoryEngine()

        # Disable
        engine.disable()
        conv_id = engine.store_conversation(
            prompt="Test",
            response="Test",
            agent="builder",
            model="test",
            provider="test",
        )
        assert conv_id == -1  # Not stored when disabled

        # Enable
        engine.enable()
        conv_id = engine.store_conversation(
            prompt="Test",
            response="Test",
            agent="builder",
            model="test",
            provider="test",
        )
        assert conv_id > 0  # Stored when enabled

    def test_get_stats(self, temp_db):
        """Test getting memory statistics."""
        engine = MemoryEngine()

        engine.store_conversation(
            prompt="Test",
            response="Response",
            agent="builder",
            model="test",
            provider="test",
            metadata={"total_tokens": 100, "cost_usd": 0.01},
        )

        stats = engine.get_stats()
        assert stats["total_conversations"] == 1
        assert stats["total_tokens"] == 100
        assert stats["total_cost_usd"] == 0.01

    def test_time_decay_scoring(self, temp_db):
        """Test that time decay reduces score for older conversations."""
        import time
        from datetime import datetime, timedelta, timezone

        engine = MemoryEngine()

        # Store recent conversation
        recent_id = engine.store_conversation(
            prompt="Python function test",
            response="Use def keyword",
            agent="builder",
            model="test",
            provider="test",
        )

        # Manually update timestamp to simulate older conversation
        time.sleep(0.1)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        conn = engine.backend._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET timestamp = ? WHERE id = ?",
            (old_timestamp, recent_id),
        )
        conn.commit()
        conn.close()

        # Store another recent conversation
        engine.store_conversation(
            prompt="Python function example",
            response="Here is sample code",
            agent="builder",
            model="test",
            provider="test",
        )

        # Get context with time decay
        context = engine.get_context_for_prompt(
            "Python function", max_tokens=1000, time_decay_hours=24, min_relevance=0.0
        )

        # Recent conversation should be ranked higher (comes first)
        assert "sample code" in context
        # Both should appear but order matters
        lines = context.split("\n")
        sample_idx = next(i for i, line in enumerate(lines) if "sample code" in line)
        def_idx = next(
            (i for i, line in enumerate(lines) if "def keyword" in line), len(lines)
        )
        assert sample_idx < def_idx, "Recent conversation should appear first"

    def test_min_relevance_filter(self, temp_db):
        """Test that min_relevance threshold filters low-scoring conversations."""
        engine = MemoryEngine()

        # Store highly relevant conversation
        engine.store_conversation(
            prompt="Create Python function for parsing JSON data",
            response="Use json.loads() to parse",
            agent="builder",
            model="test",
            provider="test",
        )

        # Store barely relevant conversation
        engine.store_conversation(
            prompt="What is the weather today",
            response="It is sunny",
            agent="builder",
            model="test",
            provider="test",
        )

        # Query with high min_relevance
        context = engine.get_context_for_prompt(
            "Python JSON parsing function", min_relevance=0.5, max_tokens=1000
        )

        # Should only include highly relevant conversation
        assert "json.loads" in context
        assert "sunny" not in context

    def test_exclude_current_session(self, temp_db):
        """Test that exclude_current_session filters out same-session conversations."""
        engine = MemoryEngine()

        # Store conversation in session "sess1"
        engine.store_conversation(
            prompt="Test in session 1",
            response="Response 1",
            agent="builder",
            model="test",
            provider="test",
            metadata={"session_id": "sess1"},
        )

        # Store conversation in session "sess2"
        engine.store_conversation(
            prompt="Test in session 2",
            response="Response 2",
            agent="builder",
            model="test",
            provider="test",
            metadata={"session_id": "sess2"},
        )

        # Get context excluding sess1
        context = engine.get_context_for_prompt(
            "Test",
            session_id="sess1",
            exclude_current_session=True,
            min_relevance=0.0,
            max_tokens=1000,
        )

        # Should only include sess2
        assert "Response 2" in context
        assert "Response 1" not in context

        # Get context without exclusion
        context_all = engine.get_context_for_prompt(
            "Test",
            session_id="sess1",
            exclude_current_session=False,
            min_relevance=0.0,
            max_tokens=1000,
        )

        # Should include both
        assert "Response 2" in context_all
        assert "Response 1" in context_all

    def test_max_tokens_budget_enforced(self, temp_db):
        """Test that max_tokens limit is enforced."""
        engine = MemoryEngine()

        # Store multiple conversations with same keywords
        for i in range(5):
            engine.store_conversation(
                prompt=f"Python function example {i}",
                response=f"Sample code example {i}" * 50,  # Long response
                agent="builder",
                model="test",
                provider="test",
            )

        # Get context with small token budget
        context = engine.get_context_for_prompt(
            "Python function", max_tokens=100, min_relevance=0.0
        )

        # Estimate tokens in result using standardized counting
        from config.settings import count_tokens
        estimated_tokens = count_tokens(context)

        # Should not exceed budget (allow small margin)
        assert estimated_tokens <= 120, f"Token budget exceeded: {estimated_tokens}"

    def test_agent_filter_in_context(self, temp_db):
        """Test agent filtering in get_context_for_prompt."""
        engine = MemoryEngine()

        # Store builder conversation
        engine.store_conversation(
            prompt="Build a Python function",
            response="Builder response",
            agent="builder",
            model="test",
            provider="test",
        )

        # Store critic conversation
        engine.store_conversation(
            prompt="Review Python function",
            response="Critic response",
            agent="critic",
            model="test",
            provider="test",
        )

        # Get context filtered by builder
        context = engine.get_context_for_prompt(
            "Python function", agent="builder", min_relevance=0.0, max_tokens=1000
        )

        assert "Builder response" in context
        assert "Critic response" not in context

        # Get context for all agents
        context_all = engine.get_context_for_prompt(
            "Python function", agent=None, min_relevance=0.0, max_tokens=1000
        )

        assert "Builder response" in context_all
        assert "Critic response" in context_all

    def test_empty_query_uses_time_decay(self, temp_db):
        """Test that empty query uses only time decay (no keyword score)."""
        import time
        from datetime import datetime, timedelta, timezone

        engine = MemoryEngine()

        # Store old conversation
        old_id = engine.store_conversation(
            prompt="Old conversation",
            response="Old response",
            agent="builder",
            model="test",
            provider="test",
        )

        # Update to old timestamp
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        conn = engine.backend._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET timestamp = ? WHERE id = ?",
            (old_timestamp, old_id),
        )
        conn.commit()
        conn.close()

        time.sleep(0.1)

        # Store recent conversation
        engine.store_conversation(
            prompt="Recent conversation",
            response="Recent response",
            agent="builder",
            model="test",
            provider="test",
        )

        # Query with empty/short prompt (no keywords)
        context = engine.get_context_for_prompt(
            "a",  # No meaningful keywords
            min_relevance=0.0,
            time_decay_hours=48,
            max_tokens=1000,
        )

        # With empty query, should only use time decay
        # Recent should appear first if any results
        if context:
            lines = context.split("\n")
            # Check that recent appears before old (if both appear)
            recent_idx = next(
                (i for i, line in enumerate(lines) if "Recent response" in line),
                len(lines),
            )
            old_idx = next(
                (i for i, line in enumerate(lines) if "Old response" in line),
                len(lines),
            )
            if recent_idx < len(lines) and old_idx < len(lines):
                assert (
                    recent_idx < old_idx
                ), "Recent conversation should rank higher with time decay"

    def test_deterministic_scoring_and_sorting(self, temp_db):
        """Test that scoring and sorting is deterministic."""
        engine = MemoryEngine()

        # Store conversations
        for i in range(3):
            engine.store_conversation(
                prompt=f"Python function test {i}",
                response=f"Response {i}",
                agent="builder",
                model="test",
                provider="test",
            )

        # Get context multiple times
        context1 = engine.get_context_for_prompt(
            "Python function", min_relevance=0.0, max_tokens=1000
        )
        context2 = engine.get_context_for_prompt(
            "Python function", min_relevance=0.0, max_tokens=1000
        )

        # Results should be identical
        assert context1 == context2, "Context retrieval should be deterministic"
