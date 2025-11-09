"""
Session Manager for Multi-Agent Orchestrator

Handles session ID generation, validation, storage, and cleanup.
Supports CLI (PID-based), UI (browser-based), and API (custom) sessions.

Features:
- Auto-session generation (duration-based for CLI, per-tab for UI)
- Input validation (SQL injection prevention, XSS prevention)
- Probabilistic cleanup (10% of requests)
- Thread-safe operations
"""

import json
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any
from uuid import uuid4


# Singleton lock for thread safety
_session_db_lock = Lock()


class SessionManager:
    """
    Manages conversation sessions across CLI, UI, and API interfaces.

    Singleton pattern with lazy initialization.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.db_path = Path("data/MEMORY/conversations.db")
            self._initialized = True

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        source: str = "cli",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get existing session or create new one.

        Args:
            session_id: Optional session ID (will be validated)
            source: 'cli', 'ui', or 'api'
            metadata: Additional metadata to store (JSON-serializable)

        Returns:
            Session ID (validated)

        Raises:
            ValueError: If session_id validation fails
        """
        if session_id:
            # Validate user-provided session_id
            self.validate_session_id(session_id)
        else:
            # Auto-generate based on source
            if source == "cli":
                session_id = self.generate_cli_session_id(metadata or {})
            elif source == "ui":
                session_id = self.generate_ui_session_id()
            else:
                # API or unknown source
                session_id = f"api-{uuid4()}"

        # Save or update session
        self.save_session(session_id, source, metadata or {})

        return session_id

    def generate_cli_session_id(self, metadata: Dict[str, Any]) -> str:
        """
        Generate CLI session ID with duration-based reuse.

        Strategy:
        - Check for recent session from same PID (within 2 hours)
        - If found → reuse existing session
        - If not found → create new session

        This prevents mid-conversation session breaks while still
        resetting after idle periods.

        Args:
            metadata: Metadata dict (must contain 'pid' or will use os.getpid())

        Returns:
            Session ID (format: cli-{pid}-{timestamp})
        """
        pid = metadata.get('pid', os.getpid())

        # Check for recent session from this terminal
        recent_session = self._get_recent_cli_session(pid=pid, within_hours=2)

        if recent_session:
            # Reuse existing session (activity within 2 hours)
            return recent_session['session_id']
        else:
            # Create new session
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"cli-{pid}-{timestamp}"

    def generate_ui_session_id(self) -> str:
        """
        Generate UI session ID.

        Format: ui-{uuid}

        Note: Web UI manages sessions via browser sessionStorage.
        This method is used as fallback if sessionStorage fails.

        Returns:
            Session ID
        """
        return f"ui-{uuid4()}"

    def validate_session_id(self, session_id: str) -> bool:
        """
        Validate session_id for security and correctness.

        Security rules:
        - Max length: 64 characters
        - Allowed chars: a-zA-Z0-9_-
        - No special characters (SQL injection prevention)
        - No path traversal attempts
        - No null bytes

        Args:
            session_id: Session ID to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not session_id:
            raise ValueError("session_id cannot be empty")

        if len(session_id) > 64:
            raise ValueError("session_id too long (max 64 chars)")

        # Allow only alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise ValueError(
                "Invalid characters in session_id (allowed: a-z, A-Z, 0-9, _, -)"
            )

        # Additional check for null bytes (paranoid)
        if '\x00' in session_id:
            raise ValueError("Null byte in session_id")

        return True

    def save_session(
        self,
        session_id: str,
        source: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Save or update session with probabilistic cleanup.

        Args:
            session_id: Validated session ID
            source: 'cli', 'ui', or 'api'
            metadata: Metadata dict (will be JSON-encoded)

        Cleanup runs randomly (10% probability) to spread load.
        """
        with _session_db_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                # Save/update session
                cursor.execute("""
                    INSERT INTO sessions (session_id, source, metadata, last_active)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(session_id)
                    DO UPDATE SET
                        last_active = CURRENT_TIMESTAMP,
                        metadata = excluded.metadata
                """, (session_id, source, json.dumps(metadata)))

                conn.commit()

                # Probabilistic cleanup (10% of requests)
                if random.random() < 0.1:
                    self._cleanup_old_sessions(cursor, conn)

            finally:
                conn.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session dict or None if not found
        """
        with _session_db_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    SELECT session_id, created_at, last_active, source, metadata
                    FROM sessions
                    WHERE session_id = ?
                """, (session_id,))

                row = cursor.fetchone()

                if row:
                    return {
                        'session_id': row[0],
                        'created_at': row[1],
                        'last_active': row[2],
                        'source': row[3],
                        'metadata': json.loads(row[4]) if row[4] else {}
                    }

                return None

            finally:
                conn.close()

    def _get_recent_cli_session(
        self,
        pid: int,
        within_hours: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        Find most recent session from this terminal within time window.

        Args:
            pid: Process ID
            within_hours: Time window (default: 2 hours)

        Returns:
            Session dict or None if not found
        """
        cutoff = datetime.now() - timedelta(hours=within_hours)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        with _session_db_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    SELECT session_id, created_at, last_active, source, metadata
                    FROM sessions
                    WHERE source = 'cli'
                      AND metadata LIKE ?
                      AND datetime(last_active) > datetime(?)
                    ORDER BY last_active DESC
                    LIMIT 1
                """, (f'%"pid":{pid}%', cutoff_str))

                row = cursor.fetchone()

                if row:
                    return {
                        'session_id': row[0],
                        'created_at': row[1],
                        'last_active': row[2],
                        'source': row[3],
                        'metadata': json.loads(row[4]) if row[4] else {}
                    }

                return None

            finally:
                conn.close()

    def _cleanup_old_sessions(
        self,
        cursor: sqlite3.Cursor,
        conn: sqlite3.Connection,
        hours: int = 24
    ) -> int:
        """
        Delete sessions older than N hours.

        Called probabilistically (10% of saves) to avoid overhead.
        Average: 1 cleanup per 10 requests.

        Args:
            cursor: Database cursor
            conn: Database connection
            hours: Age threshold (default: 24 hours)

        Returns:
            Number of sessions deleted
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            DELETE FROM sessions
            WHERE datetime(last_active) < datetime(?)
        """, (cutoff_str,))

        deleted = cursor.rowcount
        conn.commit()

        if deleted > 0:
            # Could log here if logging is enabled
            pass

        return deleted

    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """
        Manually trigger cleanup of old sessions.

        Args:
            hours: Age threshold (default: 24 hours)

        Returns:
            Number of sessions deleted
        """
        with _session_db_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                deleted = self._cleanup_old_sessions(cursor, conn, hours)
                return deleted

            finally:
                conn.close()


# Singleton instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get or create SessionManager singleton."""
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager()

    return _session_manager
