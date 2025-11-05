#!/usr/bin/env python3
"""View conversation logs with formatting."""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def format_log(log_path: Path) -> str:
    """Format a single log file."""
    with open(log_path) as f:
        data = json.load(f)

    lines = []
    lines.append("=" * 80)
    lines.append(f"Agent: {data.get('agent', 'unknown').upper()}")
    lines.append(f"Model: {data.get('model', 'unknown')}")
    lines.append(f"Time: {data.get('timestamp', 'unknown')}")
    lines.append("=" * 80)

    # Fallback info
    if data.get('fallback_used'):
        lines.append(f"⚠️  Fallback: {data.get('original_model')} → {data.get('model')}")
        lines.append(f"   Reason: {data.get('fallback_reason')}")

    # Tokens
    lines.append(f"🔢 Tokens: {data.get('total_tokens', 0)} " +
                 f"(prompt: {data.get('prompt_tokens', 0)}, " +
                 f"completion: {data.get('completion_tokens', 0)})")
    lines.append(f"⏱️  Duration: {data.get('duration_ms', 0):.0f}ms")

    lines.append("\n📝 Prompt:")
    lines.append("-" * 80)
    lines.append(data.get('prompt', ''))

    lines.append("\n💬 Response:")
    lines.append("-" * 80)
    lines.append(data.get('response', ''))
    lines.append("-" * 80)

    return "\n".join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/view_logs.py <log-file>       # View specific log")
        print("  python scripts/view_logs.py last             # View last conversation")
        print("  python scripts/view_logs.py last-chain       # View last chain (all stages)")
        print("  python scripts/view_logs.py recent [N]       # View N recent logs (default: 5)")
        sys.exit(1)

    command = sys.argv[1]
    conversations_dir = Path(__file__).parent.parent / "data" / "CONVERSATIONS"

    if not conversations_dir.exists():
        print(f"❌ Conversations directory not found: {conversations_dir}")
        sys.exit(1)

    # Get all log files sorted by modification time
    log_files = sorted(conversations_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not log_files:
        print("❌ No conversation logs found")
        sys.exit(1)

    if command == "last":
        # Show last conversation
        print(format_log(log_files[0]))

    elif command == "last-chain":
        # Find last chain - logs with same date/time prefix but different agents
        last_log = log_files[0]
        # Extract timestamp prefix (YYYYMMDD_HHMMSS)
        timestamp_prefix = last_log.stem[:15]  # 20251105_082948

        # Find all logs with same timestamp
        chain_logs = [f for f in log_files if f.stem.startswith(timestamp_prefix)]

        if len(chain_logs) == 1:
            print("ℹ️  Last conversation was not a chain (single agent)")
            print(format_log(chain_logs[0]))
        else:
            # Sort by agent order: builder, critic, closer
            agent_order = {"builder": 1, "critic": 2, "closer": 3}
            chain_logs.sort(key=lambda f: agent_order.get(f.stem.split("-")[-2], 99))

            print(f"🔗 Last Chain - {len(chain_logs)} stages")
            print(f"📝 Timestamp: {timestamp_prefix}")
            print()

            for log_file in chain_logs:
                print(format_log(log_file))
                print("\n")

    elif command == "recent":
        # Show N recent logs
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

        print(f"📊 Last {limit} conversations:")
        print()

        for log_file in log_files[:limit]:
            # Extract info
            stem = log_file.stem  # 20251105_082948-closer-30c880cd
            parts = stem.split("-")
            timestamp_str = parts[0]  # 20251105_082948
            agent = parts[1] if len(parts) > 1 else "unknown"

            # Parse timestamp
            try:
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = timestamp_str

            # Load minimal info
            with open(log_file) as f:
                data = json.load(f)

            prompt_preview = data.get('prompt', '')[:60]
            model = data.get('model', 'unknown')

            print(f"{time_str} | {agent:10} | {model:30} | {prompt_preview}...")

    elif Path(command).exists():
        # Direct file path
        print(format_log(Path(command)))

    else:
        print(f"❌ Unknown command or file not found: {command}")
        print("Use 'last', 'last-chain', 'recent [N]', or provide a log file path")
        sys.exit(1)


if __name__ == "__main__":
    main()
