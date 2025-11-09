#!/usr/bin/env python3
"""
Rollback script: Remove session tracking (v0.11.0 → v0.10.x)

This script removes session tracking features and reverts to the pre-v0.11.0 schema.

WARNING: This will delete all session metadata!

Changes:
1. Drops sessions table
2. Removes session_id column from conversations table
3. Removes related indexes

Data preserved:
- All conversation data (prompt, response, tokens, etc.)
- Embeddings

Data lost:
- Session metadata
- session_id values in conversations

Safe to run multiple times (idempotent).
"""

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def rollback():
    """Rollback session tracking migration."""
    db_path = Path("data/MEMORY/conversations.db")

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    # Backup first!
    backup_path = db_path.with_suffix(f'.db.backup.rollback.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    shutil.copy2(db_path, backup_path)
    print(f"📦 Backup created: {backup_path}")
    print()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Start transaction
        print("🔄 Starting rollback transaction...")
        cursor.execute("BEGIN TRANSACTION")

        # Drop sessions table
        print("📊 Dropping sessions table...")
        cursor.execute("DROP TABLE IF EXISTS sessions")
        print("✓ sessions table dropped")

        # Drop session-related indexes
        print("🔍 Dropping session indexes...")

        cursor.execute("DROP INDEX IF EXISTS idx_session_id")
        cursor.execute("DROP INDEX IF EXISTS idx_session")
        cursor.execute("DROP INDEX IF EXISTS idx_sessions_last_active")
        print("✓ session indexes dropped")

        # Remove session_id column from conversations
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        print("🔄 Removing session_id column from conversations...")

        # Get current data
        cursor.execute("SELECT COUNT(*) FROM conversations")
        row_count = cursor.fetchone()[0]
        print(f"  Found {row_count} conversations")

        # Create backup table without session_id
        cursor.execute("""
            CREATE TABLE conversations_backup AS
            SELECT
                id, timestamp, agent, model, provider,
                prompt, response, duration_ms,
                prompt_tokens, completion_tokens, total_tokens,
                cost_usd, fallback_used, original_model, fallback_reason,
                tags, error, embedding
            FROM conversations
        """)
        print("✓ Backup table created")

        # Drop original table
        cursor.execute("DROP TABLE conversations")
        print("✓ Original conversations table dropped")

        # Rename backup to conversations
        cursor.execute("ALTER TABLE conversations_backup RENAME TO conversations")
        print("✓ Table renamed")

        # Recreate original indexes
        print("🔍 Recreating original indexes...")
        cursor.execute("CREATE INDEX idx_timestamp ON conversations(timestamp DESC)")
        cursor.execute("CREATE INDEX idx_agent ON conversations(agent)")
        cursor.execute("CREATE INDEX idx_model ON conversations(model)")
        print("✓ Original indexes recreated")

        # Verify
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'session_id' in columns:
            raise Exception("session_id column still exists after rollback!")

        print()
        print("✓ Verified: session_id column removed")

        # Commit transaction
        cursor.execute("COMMIT")
        print()
        print("✅ Rollback complete!")

        # Show final state
        print()
        print("📊 Final database state:")

        cursor.execute("SELECT COUNT(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        print(f"  conversations: {conv_count} rows")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print(f"  tables: {', '.join([t[0] for t in tables])}")

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name='conversations'
            ORDER BY name
        """)
        indexes = cursor.fetchall()
        print(f"  conversations indexes: {', '.join([idx[0] for idx in indexes if idx[0]])}")

        print()
        print("Next steps:")
        print("  1. Restart API server (if running)")
        print("  2. Verify system works without session tracking")
        print("  3. Delete backup if everything works correctly")
        print()
        print(f"Backup available at: {backup_path}")

    except Exception as e:
        cursor.execute("ROLLBACK")
        print()
        print(f"❌ Rollback failed: {e}")
        print()
        print(f"📦 Restore from backup:")
        print(f"   cp {backup_path} {db_path}")
        print()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Session Tracking Rollback (v0.11.0 → v0.10.x)")
    print("=" * 60)
    print()
    print("⚠️  WARNING: This will REMOVE all session data!")
    print()
    print("Data preserved:")
    print("  ✓ All conversation history")
    print("  ✓ Embeddings")
    print("  ✓ Metadata (tokens, cost, etc.)")
    print()
    print("Data lost:")
    print("  ✗ Session metadata")
    print("  ✗ session_id values")
    print()

    confirm = input("Continue with rollback? (type 'yes' to confirm): ")

    if confirm.lower() != "yes":
        print()
        print("Rollback cancelled.")
        sys.exit(0)

    print()
    rollback()
