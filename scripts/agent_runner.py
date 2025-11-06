#!/usr/bin/env python3
"""CLI tool for running agents."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_env_source
from core.agent_runtime import AgentRuntime


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/agent_runner.py <agent> <prompt>")
        print("  agent: auto, builder, critic, closer")
        print('  prompt: "Your question or task"')
        print()
        print("Examples:")
        print('  python scripts/agent_runner.py auto "Analyze security risks"')
        print('  python scripts/agent_runner.py builder "Create a REST API"')
        print('  python scripts/agent_runner.py critic "Review this code: ..."')
        sys.exit(1)

    agent = sys.argv[1].lower()
    prompt = sys.argv[2]

    # Validate agent
    valid_agents = ["auto", "builder", "critic", "closer"]
    if agent not in valid_agents:
        print(f"Error: Invalid agent '{agent}'")
        print(f"Valid agents: {', '.join(valid_agents)}")
        sys.exit(1)

    # Validate prompt
    if not prompt or not prompt.strip():
        print("Error: Prompt cannot be empty")
        print("Please provide a valid prompt for the agent to process")
        sys.exit(1)

    # Show environment source
    env_source = get_env_source()
    if env_source == "environment":
        print("🔑 API keys: environment variables")
    elif env_source == "dotenv":
        print("📁 API keys: .env file")
    else:
        print("⚠️  Warning: No API keys detected")

    print(f"Running agent: {agent}")
    print(f"Prompt: {prompt}")
    print("-" * 80)

    # Run agent
    runtime = AgentRuntime()
    result = runtime.run(agent=agent, prompt=prompt)

    # Display result
    if result.error:
        print(f"\n❌ Error: {result.error}")
        sys.exit(1)

    print(f"\n✅ Agent: {result.agent}")
    print(f"📊 Model: {result.model}")

    # Show fallback information if used
    if result.fallback_used:
        print(f"⚠️  Fallback: {result.original_model} → {result.model}")
        print(f"   Reason: {result.fallback_reason}")

    print(f"⏱️  Duration: {result.duration_ms:.0f}ms")
    print(
        f"🔢 Tokens: {result.total_tokens} (prompt: {result.prompt_tokens}, completion: {result.completion_tokens})"
    )
    print(f"📁 Log file: {result.log_file}")
    print()
    print("Response:")
    print("-" * 80)
    print(result.response)
    print("-" * 80)


if __name__ == "__main__":
    main()
