"""Tests for SessionManager lifecycle, validation, and session reuse."""

import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from core.session_manager import SessionManager, get_session_manager


@pytest.fixture(autouse=True)
def fresh_session_manager(tmp_path):
    """Reset singleton and use a temp DB for each test."""
    # Reset singleton state
    SessionManager._instance = None
    SessionManager._initialized = False

    manager = SessionManager()
    manager.db_path = tmp_path / "test_sessions.db"

    # Init the DB schema (sessions table)
    import sqlite3
    conn = sqlite3.connect(str(manager.db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
            source TEXT NOT NULL,
            metadata TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session_source ON sessions(source)")
    conn.commit()
    conn.close()

    # Clear thread-local connection cache so the new db_path is used
    import core.session_manager as sm_module
    sm_module._thread_local_session.session_conns = {}

    yield manager

    # Cleanup thread-local connections
    conns = getattr(sm_module._thread_local_session, 'session_conns', {})
    for c in conns.values():
        try:
            c.close()
        except Exception:
            pass
    sm_module._thread_local_session.session_conns = {}

    # Reset singleton
    SessionManager._instance = None
    SessionManager._initialized = False


class TestSessionIDValidation:
    """Tests for validate_session_id."""

    def test_valid_alphanumeric(self, fresh_session_manager):
        assert fresh_session_manager.validate_session_id("abc123") is True

    def test_valid_with_hyphens_and_underscores(self, fresh_session_manager):
        assert fresh_session_manager.validate_session_id("cli-12345-20241101") is True

    def test_empty_raises(self, fresh_session_manager):
        with pytest.raises(ValueError, match="cannot be empty"):
            fresh_session_manager.validate_session_id("")

    def test_too_long_raises(self, fresh_session_manager):
        with pytest.raises(ValueError, match="too long"):
            fresh_session_manager.validate_session_id("a" * 65)

    def test_special_chars_raises(self, fresh_session_manager):
        with pytest.raises(ValueError, match="Invalid characters"):
            fresh_session_manager.validate_session_id("bad session!")

    def test_null_byte_raises(self, fresh_session_manager):
        # Null byte fails either the regex check or the explicit null-byte check
        with pytest.raises(ValueError):
            fresh_session_manager.validate_session_id("valid\x00byte")

    def test_sql_injection_attempt_raises(self, fresh_session_manager):
        with pytest.raises(ValueError):
            fresh_session_manager.validate_session_id("'; DROP TABLE sessions; --")


class TestSessionIDGeneration:
    """Tests for session ID formats."""

    def test_cli_session_format(self, fresh_session_manager):
        sid = fresh_session_manager.generate_cli_session_id({"pid": 1234})
        assert sid.startswith("cli-1234-")
        assert len(sid) <= 64

    def test_ui_session_format(self, fresh_session_manager):
        sid = fresh_session_manager.generate_ui_session_id()
        assert sid.startswith("ui-")
        assert len(sid) <= 64

    def test_api_session_auto_generated(self, fresh_session_manager):
        sid = fresh_session_manager.get_or_create_session(source="api")
        assert sid.startswith("api-")


class TestCliSessionReuse:
    """Tests for CLI session reuse logic."""

    def test_same_pid_reuses_session(self, fresh_session_manager):
        """Same PID within 2 hours → reuse existing session."""
        sid1 = fresh_session_manager.get_or_create_session(
            source="cli", metadata={"pid": 9999}
        )
        sid2 = fresh_session_manager.get_or_create_session(
            source="cli", metadata={"pid": 9999}
        )
        assert sid1 == sid2

    def test_different_pid_creates_new_session(self, fresh_session_manager):
        """Different PIDs → different sessions."""
        sid1 = fresh_session_manager.get_or_create_session(
            source="cli", metadata={"pid": 1001}
        )
        sid2 = fresh_session_manager.get_or_create_session(
            source="cli", metadata={"pid": 1002}
        )
        assert sid1 != sid2

    def test_expired_session_creates_new(self, fresh_session_manager):
        """Session older than 2h → create new session."""
        import sqlite3
        import json

        # Manually insert an old session with pid=8888
        old_time = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        old_sid = "cli-8888-old"
        conn = sqlite3.connect(str(fresh_session_manager.db_path))
        conn.execute(
            "INSERT INTO sessions (session_id, source, metadata, last_active, created_at) VALUES (?, ?, ?, ?, ?)",
            (old_sid, "cli", json.dumps({"pid": 8888}), old_time, old_time)
        )
        conn.commit()
        conn.close()

        # Reset thread-local so fresh connection picks up the inserted row
        import core.session_manager as sm_module
        if hasattr(sm_module._thread_local_session, 'session_conn'):
            sm_module._thread_local_session.session_conn = None

        new_sid = fresh_session_manager.get_or_create_session(
            source="cli", metadata={"pid": 8888}
        )
        assert new_sid != old_sid


class TestSaveAndGetSession:
    """Tests for save_session and get_session."""

    def test_save_and_retrieve(self, fresh_session_manager):
        fresh_session_manager.save_session("test-sess-1", "api", {"user": "alice"})
        session = fresh_session_manager.get_session("test-sess-1")
        assert session is not None
        assert session["session_id"] == "test-sess-1"
        assert session["source"] == "api"
        assert session["metadata"]["user"] == "alice"

    def test_get_unknown_session_returns_none(self, fresh_session_manager):
        result = fresh_session_manager.get_session("non-existent-id")
        assert result is None

    def test_upsert_updates_last_active(self, fresh_session_manager):
        fresh_session_manager.save_session("upsert-test", "cli", {})
        s1 = fresh_session_manager.get_session("upsert-test")

        time.sleep(0.05)
        fresh_session_manager.save_session("upsert-test", "cli", {"updated": True})
        s2 = fresh_session_manager.get_session("upsert-test")

        assert s2["last_active"] >= s1["last_active"]
        assert s2["metadata"].get("updated") is True


class TestCleanup:
    """Tests for _cleanup_old_sessions."""

    def test_cleanup_deletes_old_sessions(self, fresh_session_manager):
        import sqlite3, json
        old_time = (datetime.now() - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(str(fresh_session_manager.db_path))
        conn.execute(
            "INSERT INTO sessions (session_id, source, metadata, last_active, created_at) VALUES (?, ?, ?, ?, ?)",
            ("old-sess", "cli", json.dumps({}), old_time, old_time)
        )
        conn.commit()
        conn.close()

        import core.session_manager as sm_module
        if hasattr(sm_module._thread_local_session, 'session_conn'):
            sm_module._thread_local_session.session_conn = None

        deleted = fresh_session_manager.cleanup_old_sessions(hours=24)
        assert deleted >= 1

    def test_cleanup_keeps_recent_sessions(self, fresh_session_manager):
        fresh_session_manager.save_session("recent-sess", "api", {})
        deleted = fresh_session_manager.cleanup_old_sessions(hours=24)
        assert deleted == 0
        assert fresh_session_manager.get_session("recent-sess") is not None


class TestGetSessionManager:
    """Test singleton factory function."""

    def test_returns_same_instance(self):
        # Note: singleton reset happens in fixture for fresh_session_manager
        # This test uses the global singleton directly
        m1 = get_session_manager()
        m2 = get_session_manager()
        assert m1 is m2
