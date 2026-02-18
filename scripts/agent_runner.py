#!/usr/bin/env python3
"""CLI tool for running agents."""
import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_env_source, is_provider_enabled, get_available_providers
from core.agent_runtime import AgentRuntime
from core.session_manager import get_session_manager
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from scripts.cli_utils import (
    validate_path_basic,
    read_file_with_validation,
    estimate_input_cost,
    show_error_with_solution,
    display_response,
    console,
)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Orchestrator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s builder "Create a REST API"
  %(prog)s builder --file prompt.md
  %(prog)s builder "Task" --model gpt-4o
  %(prog)s builder "Task" --max-usd 0.50
  %(prog)s builder "Review code" --file code.py --save-to review.md
        """
    )

    parser.add_argument("agent", choices=["auto", "builder", "critic", "closer"],
                       help="Agent to use")
    parser.add_argument("prompt", nargs="?", default=None,
                       help="Prompt for the agent (or use --file)")

    # File I/O
    parser.add_argument("--file", type=str,
                       help="Read prompt from file")
    parser.add_argument("--save-to", type=str,
                       help="Save response to file")

    # Model override
    parser.add_argument("--model", type=str,
                       help="Override agent's default model")

    # Cost guardrails
    parser.add_argument("--max-usd", type=float,
                       help="Abort if estimated cost exceeds threshold")
    parser.add_argument("--max-input-tokens", type=int,
                       help="Reject prompts over N tokens")
    parser.add_argument("--force", action="store_true",
                       help="Bypass cost limits (logged)")

    args = parser.parse_args()

    # Get prompt from file or argument
    if args.file:
        prompt = read_file_with_validation(args.file)
        # Optionally combine with additional prompt
        if args.prompt:
            prompt = f"{prompt}\n\n{args.prompt}"
    elif args.prompt:
        prompt = args.prompt
    else:
        console.print("\n[bold red]❌ Error:[/bold red] Must provide either prompt or --file")
        parser.print_help()
        sys.exit(1)

    agent = args.agent.lower()

    # Validate prompt
    if not prompt or not prompt.strip():
        console.print("\n[bold red]❌ Error:[/bold red] Prompt cannot be empty")
        sys.exit(1)

    # Validate model override
    override_model = None
    if args.model:
        # Check if provider is enabled
        provider = args.model.split('/')[0] if '/' in args.model else 'openai'
        if not is_provider_enabled(provider):
            console.print(f"\n[bold red]❌ Provider '{provider}' is disabled[/bold red]")
            available = get_available_providers()
            console.print(f"   Available providers: {', '.join(available)}")
            sys.exit(1)
        override_model = args.model

    # Cost guardrails - pre-flight check
    input_tokens, estimated_cost = estimate_input_cost(prompt, args.model or "gpt-4o")

    # Token limit check
    if args.max_input_tokens and input_tokens > args.max_input_tokens:
        if not args.force:
            console.print(f"\n[bold red]❌ Input exceeds limit:[/bold red] {input_tokens} > {args.max_input_tokens} tokens")
            console.print(f"   Estimated cost: [yellow]${estimated_cost:.3f}[/yellow]")
            console.print(f"   Use [cyan]--force[/cyan] to override")
            sys.exit(1)
        else:
            console.print(f"\n[yellow]⚠️  FORCE:[/yellow] Bypassing token limit ({input_tokens} > {args.max_input_tokens})")

    # Cost limit check
    if args.max_usd:
        if estimated_cost > args.max_usd:
            if not args.force:
                console.print(f"\n[bold red]❌ Estimated cost exceeds budget:[/bold red] ${estimated_cost:.3f} > ${args.max_usd:.2f}")
                console.print(f"   Input tokens: {input_tokens}")
                console.print(f"   Use [cyan]--force[/cyan] to override or reduce prompt size")
                sys.exit(1)
            else:
                console.print(f"\n[yellow]⚠️  FORCE:[/yellow] Bypassing cost limit (${estimated_cost:.3f} > ${args.max_usd:.2f})")

    # Show environment source
    env_source = get_env_source()
    if env_source == "environment":
        console.print("🔑 API keys: environment variables")
    elif env_source == "dotenv":
        console.print("📁 API keys: .env file")
    else:
        console.print("⚠️  Warning: No API keys detected")

    console.print(f"Running agent: [cyan]{agent}[/cyan]")
    if args.file:
        console.print(f"Input file: [yellow]{args.file}[/yellow]")
    console.print(f"Prompt length: [dim]{len(prompt)} chars, ~{input_tokens} tokens[/dim]")
    if override_model:
        console.print(f"Model override: [yellow]{override_model}[/yellow]")
    console.print("-" * 80)

    # Auto-generate CLI session (v0.11.0)
    session_manager = get_session_manager()
    session_id = session_manager.get_or_create_session(
        source="cli",
        metadata={"pid": os.getpid()}
    )

    # Run agent
    runtime = AgentRuntime()
    result = runtime.run(
        agent=agent,
        prompt=prompt,
        session_id=session_id,
        override_model=override_model
    )

    # Display result
    if result.error:
        show_error_with_solution(result.error)
        sys.exit(1)

    # Success header
    console.print(f"\n[bold green]✅ Agent:[/bold green] [cyan]{result.agent}[/cyan]")
    console.print(f"[bold]📊 Model:[/bold] [yellow]{result.model}[/yellow]")

    # Show fallback information if used
    if result.fallback_used:
        console.print(f"[bold yellow]⚠️  Fallback:[/bold yellow] {result.original_model} → {result.model}")
        console.print(f"   [dim]Reason: {result.fallback_reason}[/dim]")

    # Show memory context if injected
    if hasattr(result, 'injected_context_tokens') and result.injected_context_tokens > 0:
        session_tokens = getattr(result, 'session_context_tokens', 0)
        knowledge_tokens = getattr(result, 'knowledge_context_tokens', 0)
        session_msgs = getattr(result, 'session_messages', 0)
        knowledge_msgs = getattr(result, 'knowledge_messages', 0)

        console.print(f"\n[bold magenta]🧠 Memory:[/bold magenta] {result.injected_context_tokens} tokens injected")
        if session_tokens > 0:
            console.print(f"   [dim]├─ Session: {session_tokens} tokens ({session_msgs} messages)[/dim]")
        if knowledge_tokens > 0:
            console.print(f"   [dim]└─ Knowledge: {knowledge_tokens} tokens ({knowledge_msgs} messages)[/dim]")

    # Performance metrics
    console.print(f"\n[bold]⏱️  Duration:[/bold] {result.duration_ms:.0f}ms")
    console.print(
        f"[bold]🔢 Tokens:[/bold] {result.total_tokens} [dim](prompt: {result.prompt_tokens}, completion: {result.completion_tokens})[/dim]"
    )
    console.print(f"[bold]📁 Log file:[/bold] [dim]{result.log_file}[/dim]")

    # Response with syntax highlighting
    console.print("\n[bold]Response:[/bold]")
    console.print("─" * console.width)
    display_response(result.response)
    console.print("─" * console.width)

    # Save to file if requested
    if args.save_to:
        # Validate write path
        validate_path_basic(args.save_to)

        try:
            with open(args.save_to, 'w', encoding='utf-8') as f:
                f.write(result.response)
            console.print(f"\n[bold green]💾 Saved to:[/bold green] {args.save_to}")
        except Exception as e:
            console.print(f"\n[bold red]❌ Failed to save:[/bold red] {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
