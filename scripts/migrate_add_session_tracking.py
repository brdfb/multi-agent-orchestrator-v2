#!/usr/bin/env python3
"""
Migration script: Add session tracking support (v0.11.0)

This script adds the sessions table and ensures proper schema for session tracking.

Changes:
1. Verifies session_id column exists in conversations table (should already exist)
2. Creates sessions table for session metadata
3. Creates indexes for performance

Safe to run multiple times (idempotent).
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def check_table_exists(cursor, table_name):
    """Check if table exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def check_column_exists(cursor, table_name, column_name):
    """Check if column exists in table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)


def check_index_exists(cursor, index_name):
    """Check if index exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def migrate():
    """Run migration to add session tracking support."""
    db_path = Path("data/MEMORY/conversations.db")

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("   Run the system first to create the database, then run this migration.")
        sys.exit(1)

    # Backup first
    backup_path = db_path.with_suffix(f'.db.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"📦 Backup created: {backup_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        print("🔍 Checking current schema...")

        # Check conversations table
        if not check_table_exists(cursor, "conversations"):
            print("❌ conversations table does not exist!")
            sys.exit(1)

        print("✓ conversations table exists")

        # Check session_id column
        if check_column_exists(cursor, "conversations", "session_id"):
            print("✓ session_id column already exists")
        else:
            print("🔄 Adding session_id column...")
            cursor.execute("ALTER TABLE conversations ADD COLUMN session_id TEXT")
            print("✓ session_id column added")

        # Check session_id index
        if check_index_exists(cursor, "idx_session_id") or check_index_exists(cursor, "idx_session"):
            print("✓ session_id index already exists")
        else:
            print("🔄 Creating session_id index...")
            cursor.execute("CREATE INDEX idx_session_id ON conversations(session_id)")
            print("✓ session_id index created")

        # Check sessions table
        if check_table_exists(cursor, "sessions"):
            print("✓ sessions table already exists")
        else:
            print("🔄 Creating sessions table...")
            cursor.execute("""
                CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            print("✓ sessions table created")

        # Create index on sessions.last_active for cleanup queries
        if check_index_exists(cursor, "idx_sessions_last_active"):
            print("✓ sessions.last_active index already exists")
        else:
            print("🔄 Creating sessions.last_active index...")
            cursor.execute("CREATE INDEX idx_sessions_last_active ON sessions(last_active)")
            print("✓ sessions.last_active index created")

        # Commit changes
        conn.commit()

        # Verify migration
        print()
        print("📊 Verifying migration...")

        cursor.execute("SELECT COUNT(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        print(f"✓ conversations table: {conv_count} rows")

        cursor.execute("SELECT COUNT(*) FROM sessions")
        sess_count = cursor.fetchone()[0]
        print(f"✓ sessions table: {sess_count} rows")

        # Show indexes
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name='conversations'
            ORDER BY name
        """)
        indexes = cursor.fetchall()
        print(f"✓ conversations indexes: {', '.join([idx[0] for idx in indexes if idx[0]])}")

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name='sessions'
            ORDER BY name
        """)
        indexes = cursor.fetchall()
        print(f"✓ sessions indexes: {', '.join([idx[0] for idx in indexes if idx[0]])}")

        print()
        print("✅ Migration complete!")
        print()
        print("Next steps:")
        print("  1. Restart API server (if running)")
        print("  2. Test session tracking with CLI/UI")
        print("  3. Monitor for any issues")
        print()
        print(f"Backup available at: {backup_path}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        print(f"📦 Restore from backup: {backup_path}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Session Tracking Migration (v0.11.0)")
    print("=" * 60)
    print()

    migrate()
