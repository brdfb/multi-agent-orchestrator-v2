"""Memory storage backend implementations."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import BASE_DIR

# Memory data directory
MEMORY_DIR = BASE_DIR / "data" / "MEMORY"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class SQLiteBackend:
    """SQLite storage backend for conversation memory."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize SQLite backend.

        Args:
            db_path: Path to SQLite database file (default: data/MEMORY/conversations.db)
        """
        self.db_path = db_path or (MEMORY_DIR / "conversations.db")
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create conversations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent TEXT NOT NULL,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                duration_ms REAL,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                cost_usd REAL,
                fallback_used BOOLEAN DEFAULT 0,
                original_model TEXT,
                fallback_reason TEXT,
                session_id TEXT,
                tags TEXT,
                error TEXT
            )
        """
        )

        # Create indexes for fast queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp DESC)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent ON conversations(agent)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model ON conversations(model)")

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def store(self, conversation: Dict[str, Any]) -> int:
        """
        Store conversation to database.

        Args:
            conversation: Conversation data dictionary

        Returns:
            Row ID of inserted conversation
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Extract fields
        timestamp = conversation.get("timestamp", datetime.now(timezone.utc).isoformat())
        agent = conversation.get("agent", "unknown")
        model = conversation.get("model", "unknown")
        provider = conversation.get("provider", "unknown")
        prompt = conversation.get("prompt", "")
        response = conversation.get("response", "")
        duration_ms = conversation.get("duration_ms", 0)
        prompt_tokens = conversation.get("prompt_tokens", 0)
        completion_tokens = conversation.get("completion_tokens", 0)
        total_tokens = conversation.get("total_tokens", 0)
        cost_usd = conversation.get("estimated_cost_usd") or conversation.get(
            "cost_usd", 0.0
        )
        fallback_used = conversation.get("fallback_used", False)
        original_model = conversation.get("original_model")
        fallback_reason = conversation.get("fallback_reason")
        session_id = conversation.get("session_id")
        tags = json.dumps(conversation.get("tags", []))
        error = conversation.get("error")

        cursor.execute(
            """
            INSERT INTO conversations (
                timestamp, agent, model, provider, prompt, response,
                duration_ms, prompt_tokens, completion_tokens, total_tokens,
                cost_usd, fallback_used, original_model, fallback_reason,
                session_id, tags, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timestamp,
                agent,
                model,
                provider,
                prompt,
                response,
                duration_ms,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost_usd,
                fallback_used,
                original_model,
                fallback_reason,
                session_id,
                tags,
                error,
            ),
        )

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return row_id

    def get_recent(
        self, limit: int = 10, agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversations.

        Args:
            limit: Maximum number of conversations to return
            agent: Filter by agent name (optional)

        Returns:
            List of conversation dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if agent:
            cursor.execute(
                """
                SELECT * FROM conversations
                WHERE agent = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (agent, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM conversations
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def search(
        self,
        query: Optional[str] = None,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search conversations with filters.

        Args:
            query: Keyword to search in prompt/response
            agent: Filter by agent name
            model: Filter by model name
            from_date: Filter from date (ISO format)
            to_date: Filter to date (ISO format)
            session_id: Filter by session ID
            limit: Maximum results

        Returns:
            List of matching conversations
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build query dynamically
        where_clauses = []
        params = []

        if query:
            where_clauses.append("(prompt LIKE ? OR response LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])

        if agent:
            where_clauses.append("agent = ?")
            params.append(agent)

        if model:
            where_clauses.append("model = ?")
            params.append(model)

        if from_date:
            where_clauses.append("timestamp >= ?")
            params.append(from_date)

        if to_date:
            where_clauses.append("timestamp <= ?")
            params.append(to_date)

        if session_id:
            where_clauses.append("session_id = ?")
            params.append(session_id)

        # Construct SQL
        sql = "SELECT * FROM conversations"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def get_by_id(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation dict or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        conn.close()

        return self._row_to_dict(row) if row else None

    def delete(self, conversation_id: int) -> bool:
        """
        Delete conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Statistics dictionary
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Total conversations
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cursor.fetchone()[0]

        # Total tokens
        cursor.execute("SELECT SUM(total_tokens) FROM conversations")
        total_tokens = cursor.fetchone()[0] or 0

        # Total cost
        cursor.execute("SELECT SUM(cost_usd) FROM conversations")
        total_cost = cursor.fetchone()[0] or 0.0

        # By agent
        cursor.execute(
            """
            SELECT agent, COUNT(*) as count, SUM(total_tokens) as tokens
            FROM conversations
            GROUP BY agent
        """
        )
        by_agent = {row[0]: {"count": row[1], "tokens": row[2]} for row in cursor}

        # By model
        cursor.execute(
            """
            SELECT model, COUNT(*) as count, SUM(total_tokens) as tokens
            FROM conversations
            GROUP BY model
        """
        )
        by_model = {row[0]: {"count": row[1], "tokens": row[2]} for row in cursor}

        conn.close()

        return {
            "total_conversations": total_conversations,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "by_agent": by_agent,
            "by_model": by_model,
        }

    def cleanup(self, days: int) -> int:
        """
        Delete conversations older than specified days.

        Args:
            days: Delete conversations older than this many days

        Returns:
            Number of conversations deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

        cursor.execute(
            "DELETE FROM conversations WHERE timestamp < ?", (cutoff_date.isoformat(),)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count

    def update_embedding(self, conversation_id: int, embedding_blob: bytes) -> bool:
        """
        Update embedding for a conversation.

        Args:
            conversation_id: ID of conversation to update
            embedding_blob: Serialized embedding (BLOB)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE conversations SET embedding = ? WHERE id = ?",
                (embedding_blob, conversation_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def query_candidates(
        self,
        agent: Optional[str] = None,
        exclude_session_id: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Query candidate conversations for context retrieval.

        Optimized for fetching candidates that will be scored and filtered
        by the memory engine.

        Args:
            agent: Filter by agent (None = all agents)
            exclude_session_id: Exclude conversations from this session
            limit: Maximum candidates to return

        Returns:
            List of conversation dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build query
        where_clauses = []
        params = []

        if agent:
            where_clauses.append("agent = ?")
            params.append(agent)

        if exclude_session_id:
            where_clauses.append("(session_id IS NULL OR session_id != ?)")
            params.append(exclude_session_id)

        # Construct SQL
        sql = "SELECT * FROM conversations"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary."""
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "agent": row["agent"],
            "model": row["model"],
            "provider": row["provider"],
            "prompt": row["prompt"],
            "response": row["response"],
            "duration_ms": row["duration_ms"],
            "prompt_tokens": row["prompt_tokens"],
            "completion_tokens": row["completion_tokens"],
            "total_tokens": row["total_tokens"],
            "cost_usd": row["cost_usd"],
            "fallback_used": bool(row["fallback_used"]),
            "original_model": row["original_model"],
            "fallback_reason": row["fallback_reason"],
            "session_id": row["session_id"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "error": row["error"],
            "embedding": row["embedding"] if "embedding" in row.keys() else None,
        }
