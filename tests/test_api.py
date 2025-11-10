"""Test FastAPI endpoints."""

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.server import app
from core.agent_runtime import RunResult

client = TestClient(app)


def test_health_endpoint():
    """Test health check returns 200 with comprehensive metrics."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()

    # Status should be one of the valid health states
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

    # Core fields
    assert data["service"] == "multi-agent-orchestrator"
    assert data["version"] == "1.0.1"  # Updated for v1.0.1 hotfixes
    assert "timestamp" in data

    # Provider info
    assert "providers" in data
    assert "available_providers" in data
    assert "total_available" in data

    # New monitoring fields
    assert "memory" in data
    assert "system" in data
    assert "stats_24h" in data

    # Memory should have these fields
    assert "enabled" in data["memory"]
    assert "database_connected" in data["memory"]

    # System metrics
    assert "uptime_seconds" in data["system"]
    assert "data_directory_size_mb" in data["system"]

    # 24h stats
    assert "total_tokens" in data["stats_24h"]


def test_ask_endpoint_empty_prompt():
    """Test /ask with empty prompt returns 422."""
    response = client.post("/ask", json={"agent": "builder", "prompt": ""})
    assert response.status_code == 422


def test_ask_endpoint_invalid_agent():
    """Test /ask with invalid agent returns 400."""
    response = client.post("/ask", json={"agent": "invalid", "prompt": "test"})
    assert response.status_code == 400


def test_ask_endpoint_success():
    """Test /ask endpoint returns 200 with valid request."""
    mock_result = RunResult(
        agent="builder",
        model="openai/gpt-4o-mini",
        provider="openai",
        prompt="test",
        response="test response",
        duration_ms=100.0,
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        timestamp="2024-01-01T00:00:00",
        log_file="test.json",
    )

    with patch("api.server.runtime.run", return_value=mock_result):
        response = client.post("/ask", json={"agent": "builder", "prompt": "test"})

        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "builder"
        assert data["response"] == "test response"


def test_metrics_endpoint():
    """Test /metrics endpoint returns valid structure."""
    response = client.get("/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "total_requests" in data
    assert "total_tokens" in data
    assert "total_cost_usd" in data
    assert "avg_duration_ms" in data


def test_logs_endpoint():
    """Test /logs endpoint returns list."""
    response = client.get("/logs?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
