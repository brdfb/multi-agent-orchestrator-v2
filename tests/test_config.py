"""Test configuration loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_agents_config


def test_config_loads():
    """Test that agents.yaml loads successfully."""
    config = load_agents_config()
    assert config is not None
    assert "default_model" in config
    assert "agents" in config


def test_config_has_required_agents():
    """Test that all required agents are defined."""
    config = load_agents_config()
    agents = config["agents"]

    required_agents = ["builder", "critic", "closer", "router"]
    for agent in required_agents:
        assert agent in agents, f"Missing agent: {agent}"


def test_agent_config_structure():
    """Test that agent configs have required fields."""
    config = load_agents_config()

    for agent_name, agent_config in config["agents"].items():
        assert "model" in agent_config, f"{agent_name} missing model"
        assert "system" in agent_config, f"{agent_name} missing system prompt"
        assert "description" in agent_config, f"{agent_name} missing description"
