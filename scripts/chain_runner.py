#!/usr/bin/env python3
"""CLI tool for running multi-agent chains."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_env_source
from core.agent_runtime import AgentRuntime


def print_stage_result(result, stage_num: int, total_stages: int):
    """Print formatted result for a single stage."""
    print("\n" + "=" * 80)
    print(f"STAGE {stage_num}/{total_stages}: {result.agent.upper()}")
    print("=" * 80)

    if result.error:
        print(f"\n❌ Error: {result.error}")
        return

    print(f"\n📊 Model: {result.model}")

    # Show fallback information if used
    if result.fallback_used:
        print(f"⚠️  Fallback: {result.original_model} → {result.model}")
        print(f"   Reason: {result.fallback_reason}")

    print(f"⏱️  Duration: {result.duration_ms:.0f}ms")
    print(f"🔢 Tokens: {result.total_tokens} (prompt: {result.prompt_tokens}, completion: {result.completion_tokens})")
    print(f"📁 Log: {result.log_file}")

    print("\nResponse:")
    print("-" * 80)
    if result.response:
        # Truncate very long responses for readability
        if len(result.response) > 2000:
            print(result.response[:2000])
            print(f"\n... [truncated {len(result.response) - 2000} characters] ...")
        else:
            print(result.response)
    else:
        print("[No response]")
    print("-" * 80)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/chain_runner.py <prompt> [stages...]")
        print()
        print("Examples:")
        print('  python scripts/chain_runner.py "Design a REST API"')
        print('  python scripts/chain_runner.py "Review this code" builder critic')
        print()
        print("Default stages: builder → critic → closer")
        sys.exit(1)

    prompt = sys.argv[1]
    stages = sys.argv[2:] if len(sys.argv) > 2 else None

    # Validate stages if provided
    if stages:
        valid_agents = ["builder", "critic", "closer"]
        for stage in stages:
            if stage not in valid_agents:
                print(f"Error: Invalid agent '{stage}'")
                print(f"Valid agents: {', '.join(valid_agents)}")
                sys.exit(1)

    # Show environment source
    env_source = get_env_source()
    if env_source == "environment":
        print("🔑 API keys: environment variables")
    elif env_source == "dotenv":
        print("📁 API keys: .env file")
    else:
        print("⚠️  Warning: No API keys detected")

    stage_list = stages or ["builder", "critic", "closer"]
    print(f"🔗 Running chain: {' → '.join(stage_list)}")
    print(f"📝 Prompt: {prompt}")

    # Run chain
    runtime = AgentRuntime()

    try:
        results = runtime.chain(prompt=prompt, stages=stages)
    except Exception as e:
        print(f"\n❌ Chain failed: {str(e)}")
        sys.exit(1)

    # Display results
    total = len(results)
    for idx, result in enumerate(results, 1):
        print_stage_result(result, idx, total)

    # Summary
    print("\n" + "=" * 80)
    print("CHAIN SUMMARY")
    print("=" * 80)

    total_duration = sum(r.duration_ms for r in results)
    total_tokens = sum(r.total_tokens for r in results)
    errors = [r for r in results if r.error]

    print(f"\n✅ Stages completed: {len(results) - len(errors)}/{total}")
    print(f"⏱️  Total duration: {total_duration:.0f}ms ({total_duration/1000:.1f}s)")
    print(f"🔢 Total tokens: {total_tokens}")

    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for err_result in errors:
            print(f"   - {err_result.agent}: {err_result.error}")
        sys.exit(1)

    print("\n✅ Chain completed successfully!")


if __name__ == "__main__":
    main()
