"""Test logging utilities."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logging_utils import mask_sensitive_data, write_json


def test_mask_api_keys():
    """Test that API keys are masked."""
    text = "My key is sk-abc123def456 and OPENAI_API_KEY=secret123"
    masked = mask_sensitive_data(text)

    assert "sk-abc123def456" not in masked
    assert "secret123" not in masked
    assert "***MASKED***" in masked


def test_write_json_creates_file():
    """Test that write_json creates a file."""
    record = {
        "agent": "builder",
        "model": "openai/gpt-4o-mini",
        "provider": "openai",
        "prompt": "Test prompt",
        "response": "Test response",
        "duration_ms": 100.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }

    filepath = write_json(record)

    assert filepath.exists()
    assert filepath.suffix == ".json"
    assert "builder" in filepath.name

    # Cleanup
    filepath.unlink()


def test_write_json_masks_sensitive_data():
    """Test that sensitive data is masked in logs."""
    record = {
        "agent": "test",
        "model": "test/model",
        "provider": "test",
        "prompt": "My API key is sk-secret123",
        "response": "ANTHROPIC_API_KEY=another_secret",
        "duration_ms": 100.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }

    filepath = write_json(record)

    # Read and verify
    import json

    with open(filepath, "r") as f:
        saved = json.load(f)

    assert "sk-secret123" not in saved["prompt"]
    assert "another_secret" not in saved["response"]
    assert "***MASKED***" in saved["prompt"]

    # Cleanup
    filepath.unlink()
