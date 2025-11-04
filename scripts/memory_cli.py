#!/usr/bin/env python3
"""CLI for memory system operations."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
from datetime import datetime

from core.memory_engine import MemoryEngine


def format_conversation(conv: dict, show_full: bool = False) -> str:
    """Format conversation for display."""
    timestamp = conv.get("timestamp", "")
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    agent = conv.get("agent", "unknown")
    model = conv.get("model", "unknown")
    prompt = conv.get("prompt", "")
    response = conv.get("response", "")

    # Truncate if not showing full
    if not show_full:
        prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
        response = response[:200] + "..." if len(response) > 200 else response

    lines = [
        f"ID: {conv.get('id', 'N/A')}",
        f"Time: {timestamp}",
        f"Agent: {agent} | Model: {model}",
        f"Tokens: {conv.get('total_tokens', 0)}",
        f"Prompt: {prompt}",
        f"Response: {response}",
    ]

    return "\n".join(lines)


def cmd_search(args):
    """Search conversations."""
    memory = MemoryEngine()

    results = memory.search_conversations(
        query=args.query, agent=args.agent, model=args.model, limit=args.limit
    )

    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} results:\n")
    for i, conv in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(format_conversation(conv, show_full=args.full))


def cmd_recent(args):
    """Show recent conversations."""
    memory = MemoryEngine()

    results = memory.get_recent_conversations(limit=args.limit, agent=args.agent)

    if not results:
        print("No conversations found.")
        return

    print(f"Recent {len(results)} conversations:\n")
    for i, conv in enumerate(results, 1):
        print(f"\n--- Conversation {i} ---")
        print(format_conversation(conv, show_full=args.full))


def cmd_stats(args):
    """Show memory statistics."""
    memory = MemoryEngine()
    stats = memory.get_stats()

    print("=== Memory Statistics ===\n")
    print(f"Total Conversations: {stats['total_conversations']}")
    print(f"Total Tokens: {stats['total_tokens']:,}")
    print(f"Total Cost: ${stats['total_cost_usd']:.4f}")

    if stats["by_agent"]:
        print("\nBy Agent:")
        for agent, data in stats["by_agent"].items():
            print(
                f"  {agent}: {data['count']} conversations, {data['tokens']:,} tokens"
            )

    if stats["by_model"]:
        print("\nBy Model:")
        for model, data in stats["by_model"].items():
            print(
                f"  {model}: {data['count']} conversations, {data['tokens']:,} tokens"
            )


def cmd_delete(args):
    """Delete a conversation."""
    memory = MemoryEngine()

    if args.confirm or input(f"Delete conversation {args.id}? [y/N]: ").lower() == "y":
        deleted = memory.delete_conversation(args.id)
        if deleted:
            print(f"✓ Deleted conversation {args.id}")
        else:
            print(f"✗ Conversation {args.id} not found")
    else:
        print("Cancelled.")


def cmd_cleanup(args):
    """Cleanup old conversations."""
    memory = MemoryEngine()

    if (
        args.confirm
        or input(f"Delete conversations older than {args.days} days? [y/N]: ").lower()
        == "y"
    ):
        deleted_count = memory.cleanup_old_conversations(args.days)
        print(f"✓ Deleted {deleted_count} conversations")
    else:
        print("Cancelled.")


def cmd_export(args):
    """Export conversations."""
    memory = MemoryEngine()

    results = memory.search_conversations(
        from_date=args.from_date, to_date=args.to_date, limit=args.limit
    )

    if args.format == "json":
        output = json.dumps(results, indent=2)
        print(output)
    elif args.format == "csv":
        # Simple CSV output
        if results:
            keys = [
                "id",
                "timestamp",
                "agent",
                "model",
                "prompt",
                "response",
                "total_tokens",
            ]
            print(",".join(keys))
            for r in results:
                values = [str(r.get(k, "")).replace(",", ";") for k in keys]
                print(",".join(values))
    else:
        print(f"Unknown format: {args.format}")


def main():
    parser = argparse.ArgumentParser(description="Memory system CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search conversations")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--agent", help="Filter by agent")
    search_parser.add_argument("--model", help="Filter by model")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")
    search_parser.add_argument("--full", action="store_true", help="Show full text")

    # Recent command
    recent_parser = subparsers.add_parser("recent", help="Show recent conversations")
    recent_parser.add_argument("--limit", type=int, default=10, help="Max results")
    recent_parser.add_argument("--agent", help="Filter by agent")
    recent_parser.add_argument("--full", action="store_true", help="Show full text")

    # Stats command
    subparsers.add_parser("stats", help="Show memory statistics")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete conversation")
    delete_parser.add_argument("id", type=int, help="Conversation ID")
    delete_parser.add_argument(
        "-y", "--confirm", action="store_true", help="Skip confirmation"
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup old conversations")
    cleanup_parser.add_argument(
        "--days", type=int, default=90, help="Delete older than N days"
    )
    cleanup_parser.add_argument(
        "-y", "--confirm", action="store_true", help="Skip confirmation"
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export conversations")
    export_parser.add_argument("--from-date", help="From date (ISO format)")
    export_parser.add_argument("--to-date", help="To date (ISO format)")
    export_parser.add_argument(
        "--format", default="json", choices=["json", "csv"], help="Output format"
    )
    export_parser.add_argument("--limit", type=int, default=1000, help="Max results")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "search": cmd_search,
        "recent": cmd_recent,
        "stats": cmd_stats,
        "delete": cmd_delete,
        "cleanup": cmd_cleanup,
        "export": cmd_export,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
