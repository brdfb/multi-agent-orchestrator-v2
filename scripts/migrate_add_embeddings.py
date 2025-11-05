#!/usr/bin/env python3
"""
Database migration: Add embedding column to conversations table.

Usage:
    python scripts/migrate_add_embeddings.py
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_memory_config


def migrate():
    """Add embedding column to conversations table."""
    config = load_memory_config()
    db_path = Path(__file__).parent.parent / config["memory"]["db_path"]

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("   Run a conversation first to create the database.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [col[1] for col in cursor.fetchall()]

    if "embedding" in columns:
        print("✅ Column 'embedding' already exists - migration not needed")
        conn.close()
        return

    print("🔄 Adding 'embedding' column to conversations table...")

    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN embedding BLOB")
        conn.commit()
        print("✅ Migration successful!")
        print("   Column 'embedding' added to conversations table")

        # Show stats
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total = cursor.fetchone()[0]
        print(f"   Total conversations: {total}")
        print(f"   Note: Existing conversations have NULL embeddings (will be generated on demand)")

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
