"""Logging utilities for conversation tracking."""
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from config.settings import CONVERSATIONS_DIR, estimate_cost


def mask_sensitive_data(text: str) -> str:
    """Mask API keys and sensitive data in text."""
    patterns = [
        (r"(sk-[a-zA-Z0-9]{8,})", "sk-***MASKED***"),
        (r"(API[_-]?KEY[=:\s]+)([^\s]+)", r"\1***MASKED***"),
        (r"(ANTHROPIC[_-]?API[_-]?KEY[=:\s]+)([^\s]+)", r"\1***MASKED***"),
        (r"(OPENAI[_-]?API[_-]?KEY[=:\s]+)([^\s]+)", r"\1***MASKED***"),
        (r"(GOOGLE[_-]?API[_-]?KEY[=:\s]+)([^\s]+)", r"\1***MASKED***"),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def write_json(record: Dict[str, Any]) -> Path:
    """
    Write conversation record to JSON file.

    Args:
        record: Dictionary containing conversation data

    Returns:
        Path to written file
    """
    # Ensure directory exists
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    agent = record.get("agent", "unknown")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}-{agent}-{unique_id}.json"
    filepath = CONVERSATIONS_DIR / filename

    # Mask sensitive data
    if "prompt" in record:
        record["prompt"] = mask_sensitive_data(record["prompt"])
    if "response" in record:
        record["response"] = mask_sensitive_data(record["response"])

    # Add cost estimate
    if "model" in record and "prompt_tokens" in record and "completion_tokens" in record:
        record["estimated_cost_usd"] = estimate_cost(
            record["model"], record["prompt_tokens"], record["completion_tokens"]
        )

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return filepath


def read_logs(limit: int = 20) -> list[Dict[str, Any]]:
    """
    Read recent conversation logs.

    Args:
        limit: Maximum number of logs to return

    Returns:
        List of conversation records
    """
    if not CONVERSATIONS_DIR.exists():
        return []

    # Get all JSON files, sorted by modification time (newest first)
    files = sorted(CONVERSATIONS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

    logs = []
    for filepath in files[:limit]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                log = json.load(f)
                log["filename"] = filepath.name
                logs.append(log)
        except Exception:
            continue

    return logs


def get_metrics() -> Dict[str, Any]:
    """
    Calculate aggregate metrics from all logs.

    Returns:
        Dictionary with metrics
    """
    logs = read_logs(limit=1000)  # Last 1000 logs

    if not logs:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_duration_ms": 0.0,
            "agents_used": {},
        }

    total_requests = len(logs)
    total_tokens = sum(log.get("total_tokens", 0) for log in logs)
    total_cost = sum(log.get("estimated_cost_usd", 0.0) for log in logs)
    durations = [log.get("duration_ms", 0) for log in logs if log.get("duration_ms")]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    # Count agent usage
    agents_used = {}
    for log in logs:
        agent = log.get("agent", "unknown")
        agents_used[agent] = agents_used.get(agent, 0) + 1

    return {
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "avg_duration_ms": round(avg_duration, 2),
        "agents_used": agents_used,
    }
