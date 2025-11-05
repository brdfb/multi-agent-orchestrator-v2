#!/usr/bin/env python3
"""CLI tool for running multi-agent chains."""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_env_source
from core.agent_runtime import AgentRuntime


def format_stage_result(result, stage_num: int, total_stages: int) -> str:
    """Format a single stage result."""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append(f"STAGE {stage_num}/{total_stages}: {result.agent.upper()}")
    lines.append("=" * 80)

    if result.error:
        lines.append(f"\n❌ Error: {result.error}")
        return "\n".join(lines)

    lines.append(f"\n📊 Model: {result.model}")

    # Show fallback information if used
    if result.fallback_used:
        lines.append(f"⚠️  Fallback: {result.original_model} → {result.model}")
        lines.append(f"   Reason: {result.fallback_reason}")

    lines.append(f"⏱️  Duration: {result.duration_ms:.0f}ms")
    lines.append(f"🔢 Tokens: {result.total_tokens} (prompt: {result.prompt_tokens}, completion: {result.completion_tokens})")
    lines.append(f"📁 Log: {result.log_file}")

    lines.append("\nResponse:")
    lines.append("-" * 80)
    if result.response:
        # Show full response (no truncation)
        lines.append(result.response)
    else:
        lines.append("[No response]")
    lines.append("-" * 80)

    return "\n".join(lines)


def print_stage_result(result, stage_num: int, total_stages: int):
    """Print formatted result for a single stage."""
    print(format_stage_result(result, stage_num, total_stages))


def main():
    """Main CLI entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Multi-Agent Chain Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mao-chain "Design a REST API"
  mao-chain "Review code" builder critic
  mao-chain "Analyze system" --save-to report.md
  mao-chain  (interactive mode)
        """
    )
    parser.add_argument("prompt", nargs="?", help="The prompt to process")
    parser.add_argument("stages", nargs="*", help="Custom stages (e.g., builder critic)")
    parser.add_argument("--save-to", "-o", metavar="FILE", help="Save output to file")

    # If no args, go interactive
    if len(sys.argv) == 1:
        print("🔗 Multi-Agent Chain Runner")
        print("=" * 80)
        print()
        try:
            prompt = input("Enter your prompt: ").strip()
            if not prompt:
                print("❌ Error: Prompt cannot be empty")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\n\n❌ Cancelled")
            sys.exit(0)
        stages = None
        save_to = None
    else:
        args = parser.parse_args()
        prompt = args.prompt
        stages = args.stages if args.stages else None
        save_to = args.save_to

        if not prompt:
            parser.print_help()
            sys.exit(1)

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
    print()

    # Progress callback
    def show_progress(stage_num, total, agent_name):
        print(f"🔄 Stage {stage_num}/{total}: Running {agent_name.upper()}...", flush=True)

    # Run chain with progress indicators
    runtime = AgentRuntime()

    try:
        results = runtime.chain(prompt=prompt, stages=stages, progress_callback=show_progress)
    except Exception as e:
        print(f"\n❌ Chain failed: {str(e)}")
        sys.exit(1)

    # Collect output for saving
    output_lines = []

    # Display results (and collect if saving)
    total = len(results)
    for idx, result in enumerate(results, 1):
        stage_output = format_stage_result(result, idx, total)
        print(stage_output)
        if save_to:
            output_lines.append(stage_output)

    # Summary
    summary_lines = []
    summary_lines.append("\n" + "=" * 80)
    summary_lines.append("CHAIN SUMMARY")
    summary_lines.append("=" * 80)

    total_duration = sum(r.duration_ms for r in results)
    total_tokens = sum(r.total_tokens for r in results)
    errors = [r for r in results if r.error]

    summary_lines.append(f"\n✅ Stages completed: {len(results) - len(errors)}/{total}")
    summary_lines.append(f"⏱️  Total duration: {total_duration:.0f}ms ({total_duration/1000:.1f}s)")
    summary_lines.append(f"🔢 Total tokens: {total_tokens}")

    if errors:
        summary_lines.append(f"\n❌ Errors: {len(errors)}")
        for err_result in errors:
            summary_lines.append(f"   - {err_result.agent}: {err_result.error}")

    summary_lines.append("\n✅ Chain completed successfully!")

    # Print summary
    summary = "\n".join(summary_lines)
    print(summary)
    if save_to:
        output_lines.append(summary)

    # Save to file if requested
    if save_to:
        try:
            output_path = Path(save_to)
            with open(output_path, "w", encoding="utf-8") as f:
                # Add header
                f.write(f"# Chain Execution Report\n\n")
                f.write(f"**Prompt:** {prompt}\n\n")
                f.write(f"**Stages:** {' → '.join(stages or ['builder', 'critic', 'closer'])}\n\n")
                f.write("---\n\n")
                # Write all collected output
                f.write("\n\n".join(output_lines))
            print(f"\n💾 Output saved to: {output_path.absolute()}")
        except Exception as e:
            print(f"\n⚠️  Failed to save output: {e}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
