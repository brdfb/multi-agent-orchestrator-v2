#!/usr/bin/env python3
"""CLI tool for running multi-agent chains."""
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
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import re

console = Console()


def validate_path_basic(path: str) -> Path:
    """Basic sanity checks for file paths (not enterprise security)."""
    resolved = Path(path).resolve()

    # Block obvious sensitive files
    blocked = ['.env', '.git', '.ssh', 'id_rsa', 'credentials', 'password']
    if any(b in str(resolved).lower() for b in blocked):
        matched = [b for b in blocked if b in str(resolved).lower()]
        console.print(f"\n[bold red]🔒 Blocked:[/bold red] {path}")
        console.print(f"   Matches blocked pattern: {matched}")
        console.print("   Security policy prevents accessing this file")
        sys.exit(1)

    # Warn if outside CWD (but allow)
    if not str(resolved).startswith(str(Path.cwd())):
        console.print(f"\n[yellow]⚠️  Reading outside project:[/yellow] {resolved}")
        # Allow it - just informational

    return resolved


def read_file_with_validation(file_path: str) -> str:
    """Read file with validation and error handling."""
    # Validate path
    resolved = validate_path_basic(file_path)

    # Check existence
    if not resolved.exists():
        console.print(f"\n[bold red]❌ File not found:[/bold red] {file_path}")
        sys.exit(1)

    # Check if it's a file
    if not resolved.is_file():
        console.print(f"\n[bold red]❌ Not a file:[/bold red] {file_path}")
        sys.exit(1)

    # Check size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    if resolved.stat().st_size > max_size:
        size_mb = resolved.stat().st_size / 1024 / 1024
        console.print(f"\n[bold red]❌ File too large:[/bold red] {size_mb:.1f}MB")
        console.print(f"   Maximum allowed: 10MB")
        sys.exit(1)

    # Read file
    try:
        with open(resolved, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        console.print(f"\n[bold red]❌ Cannot read file:[/bold red] Not a text file (binary?)")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]❌ Error reading file:[/bold red] {e}")
        sys.exit(1)


def estimate_input_cost(text: str, model: str) -> tuple[int, float]:
    """Estimate tokens and cost for input text."""
    try:
        import tiktoken
        # Use generic encoding (works for most models)
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = len(enc.encode(text))

        # Rough cost estimate (input tokens)
        # GPT-4o: $0.0025 per 1K input tokens
        # Claude: $0.003 per 1K input tokens
        cost = tokens * 0.000003  # Average

        return tokens, cost
    except:
        # Fallback: rough estimate
        tokens = len(text) // 4
        cost = tokens * 0.000003
        return tokens, cost


def show_error_with_solution(error_msg: str):
    """Display error with context-aware solution."""
    console.print(f"\n[bold red]❌ Error:[/bold red] {error_msg}")

    error_lower = error_msg.lower()

    if "api key" in error_lower or "authentication" in error_lower:
        console.print("\n[bold cyan]💡 Solution:[/bold cyan]")
        console.print("Add API key to your [yellow].env[/yellow] file:")
        console.print("  [green]ANTHROPIC_API_KEY[/green]=sk-ant-...")
        console.print("  [green]OPENAI_API_KEY[/green]=sk-...")
    elif "model" in error_lower and "not found" in error_lower:
        console.print("\n[bold cyan]💡 Solution:[/bold cyan]")
        console.print("Try current models: [green]claude-sonnet-4-5[/green], [green]gpt-4o[/green]")
    elif "rate limit" in error_lower:
        console.print("\n[bold cyan]💡 Solution:[/bold cyan]")
        console.print("Wait 30-60 seconds or try a different provider")
    else:
        console.print("\n[bold cyan]💡 Need Help?[/bold cyan]")
        console.print("Check logs or report: [blue]https://github.com/brdfb/multi-agent-orchestrator-v2/issues[/blue]")


def display_response(response: str):
    """Display response with syntax highlighting."""
    if '```' in response:
        parts = re.split(r'(```\w*\n.*?```)', response, flags=re.DOTALL)
        for part in parts:
            if part.startswith('```'):
                match = re.match(r'```(\w+)?\n(.*?)```', part, re.DOTALL)
                if match:
                    lang = match.group(1) or 'python'
                    code = match.group(2).strip()
                    syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
                    console.print(syntax)
            elif part.strip():
                console.print(part.strip())
    else:
        console.print(response)


def print_stage_result(result, stage_num: int, total_stages: int):
    """Print formatted result for a single stage with rich formatting."""
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print(f"[bold white]STAGE {stage_num}/{total_stages}:[/bold white] [bold green]{result.agent.upper()}[/bold green]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]")

    if result.error:
        show_error_with_solution(result.error)
        return

    console.print(f"\n[bold]📊 Model:[/bold] [yellow]{result.model}[/yellow]")

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

        console.print(f"[bold magenta]🧠 Memory:[/bold magenta] {result.injected_context_tokens} tokens")
        if session_tokens > 0:
            console.print(f"   [dim]├─ Session: {session_tokens} tokens ({session_msgs} msgs)[/dim]")
        if knowledge_tokens > 0:
            console.print(f"   [dim]└─ Knowledge: {knowledge_tokens} tokens ({knowledge_msgs} msgs)[/dim]")

    console.print(f"[bold]⏱️  Duration:[/bold] {result.duration_ms:.0f}ms")
    console.print(f"[bold]🔢 Tokens:[/bold] {result.total_tokens} [dim](prompt: {result.prompt_tokens}, completion: {result.completion_tokens})[/dim]")
    console.print(f"[bold]📁 Log:[/bold] [dim]{result.log_file}[/dim]")

    console.print("\n[bold]Response:[/bold]")
    console.print("─" * console.width)
    if result.response:
        display_response(result.response)
    else:
        console.print("[dim][No response][/dim]")
    console.print("─" * console.width)


def main():
    """Main CLI entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Multi-Agent Chain Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mao-chain "Design a REST API"
  mao-chain --file design.md builder critic
  mao-chain "Review code" --save-to report.md
  mao-chain "Task" --model gpt-4o --max-usd 1.00
  mao-chain  (interactive mode)
        """
    )
    parser.add_argument("prompt", nargs="?", help="The prompt to process (or use --file)")
    parser.add_argument("stages", nargs="*", help="Custom stages (e.g., builder critic)")

    # File I/O
    parser.add_argument("--file", type=str, help="Read prompt from file")
    parser.add_argument("--save-to", "-o", metavar="FILE", help="Save output to file")

    # Model override
    parser.add_argument("--model", type=str, help="Override default models for all stages")

    # Cost guardrails
    parser.add_argument("--max-usd", type=float, help="Abort if estimated cost exceeds threshold")
    parser.add_argument("--max-input-tokens", type=int, help="Reject prompts over N tokens")
    parser.add_argument("--force", action="store_true", help="Bypass cost limits (logged)")

    # If no args, go interactive
    if len(sys.argv) == 1:
        console.print("\n[bold cyan]🔗 Multi-Agent Chain Runner[/bold cyan]")
        console.print("[cyan]" + "=" * 80 + "[/cyan]")
        console.print()
        try:
            prompt = input("Enter your prompt: ").strip()
            if not prompt:
                console.print("[bold red]❌ Error:[/bold red] Prompt cannot be empty")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[yellow]❌ Cancelled[/yellow]")
            sys.exit(0)
        stages = None
        save_to = None
        override_model = None
        args = None  # No args in interactive mode
    else:
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

        stages = args.stages if args.stages else None
        save_to = args.save_to
        override_model = args.model

    # Validate stages if provided
    if stages:
        valid_agents = ["builder", "critic", "closer"]
        for stage in stages:
            if stage not in valid_agents:
                console.print(f"[bold red]Error:[/bold red] Invalid agent '{stage}'")
                console.print(f"Valid agents: {', '.join(valid_agents)}")
                sys.exit(1)

    # Validate model override (only if args exists - not in interactive mode)
    if args and override_model:
        # Check if provider is enabled
        provider = override_model.split('/')[0] if '/' in override_model else 'openai'
        if not is_provider_enabled(provider):
            console.print(f"\n[bold red]❌ Provider '{provider}' is disabled[/bold red]")
            available = get_available_providers()
            console.print(f"   Available providers: {', '.join(available)}")
            sys.exit(1)

    # Cost guardrails - pre-flight check (only if args exists)
    if args and (args.max_input_tokens or args.max_usd):
        input_tokens, estimated_cost = estimate_input_cost(prompt, override_model or "gpt-4o")

        # Token limit check
        if args.max_input_tokens and input_tokens > args.max_input_tokens:
            if not args.force:
                console.print(f"\n[bold red]❌ Input exceeds limit:[/bold red] {input_tokens} > {args.max_input_tokens} tokens")
                console.print(f"   Estimated cost: [yellow]${estimated_cost:.3f}[/yellow]")
                console.print(f"   Use [cyan]--force[/cyan] to override")
                sys.exit(1)
            else:
                console.print(f"\n[yellow]⚠️  FORCE:[/yellow] Bypassing token limit ({input_tokens} > {args.max_input_tokens})")

        # Cost limit check (chain typically 3x single agent cost)
        if args.max_usd:
            chain_estimated_cost = estimated_cost * 3  # Rough chain estimate
            if chain_estimated_cost > args.max_usd:
                if not args.force:
                    console.print(f"\n[bold red]❌ Estimated chain cost exceeds budget:[/bold red] ~${chain_estimated_cost:.3f} > ${args.max_usd:.2f}")
                    console.print(f"   Input tokens: {input_tokens}")
                    console.print(f"   Chain multiplier: ~3x single agent")
                    console.print(f"   Use [cyan]--force[/cyan] to override or reduce prompt size")
                    sys.exit(1)
                else:
                    console.print(f"\n[yellow]⚠️  FORCE:[/yellow] Bypassing cost limit (~${chain_estimated_cost:.3f} > ${args.max_usd:.2f})")

    # Show environment source
    env_source = get_env_source()
    if env_source == "environment":
        console.print("🔑 API keys: environment variables")
    elif env_source == "dotenv":
        console.print("📁 API keys: .env file")
    else:
        console.print("[yellow]⚠️  Warning: No API keys detected[/yellow]")

    stage_list = stages or ["builder", "critic", "closer"]
    console.print(f"[bold]🔗 Running chain:[/bold] [cyan]{' → '.join(stage_list)}[/cyan]")
    if args and args.file:
        console.print(f"[bold]📄 Input file:[/bold] [yellow]{args.file}[/yellow]")
    console.print(f"[bold]📝 Prompt:[/bold] {prompt[:100]}..." if len(prompt) > 100 else f"[bold]📝 Prompt:[/bold] {prompt}")
    if override_model:
        console.print(f"[bold]🔧 Model override:[/bold] [yellow]{override_model}[/yellow]")
    console.print()

    # Progress callback with rich formatting
    def show_progress(stage_num, total, agent_name):
        console.print(f"[bold yellow]🔄 Stage {stage_num}/{total}:[/bold yellow] Running [cyan]{agent_name.upper()}[/cyan]...")

    # Auto-generate CLI session (v0.11.0)
    session_manager = get_session_manager()
    session_id = session_manager.get_or_create_session(
        source="cli",
        metadata={"pid": os.getpid()}
    )

    # Run chain with progress indicators
    runtime = AgentRuntime()

    try:
        results = runtime.chain(
            prompt=prompt,
            stages=stages,
            progress_callback=show_progress,
            session_id=session_id,  # v0.11.0
            override_model=override_model  # v0.13.0
        )
    except Exception as e:
        console.print(f"\n[bold red]❌ Chain failed:[/bold red] {str(e)}")
        sys.exit(1)

    # Display results
    total = len(results)
    for idx, result in enumerate(results, 1):
        print_stage_result(result, idx, total)

    # Summary with rich formatting
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print("[bold white]CHAIN SUMMARY[/bold white]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]")

    total_duration = sum(r.duration_ms for r in results)
    total_tokens = sum(r.total_tokens for r in results)
    errors = [r for r in results if r.error]

    console.print(f"\n[bold green]✅ Stages completed:[/bold green] {len(results) - len(errors)}/{total}")
    console.print(f"[bold]⏱️  Total duration:[/bold] {total_duration:.0f}ms ({total_duration/1000:.1f}s)")
    console.print(f"[bold]🔢 Total tokens:[/bold] {total_tokens}")

    if errors:
        console.print(f"\n[bold red]❌ Errors:[/bold red] {len(errors)}")
        for err_result in errors:
            console.print(f"   [dim]- {err_result.agent}: {err_result.error}[/dim]")
    else:
        console.print("\n[bold green]✅ Chain completed successfully![/bold green]")

    # Save to file if requested
    if save_to:
        try:
            # Validate write path
            validate_path_basic(save_to)

            output_path = Path(save_to)
            with open(output_path, "w", encoding="utf-8") as f:
                # Add header
                f.write(f"# Chain Execution Report\n\n")
                f.write(f"**Prompt:** {prompt}\n\n")
                f.write(f"**Stages:** {' → '.join(stages or ['builder', 'critic', 'closer'])}\n\n")
                f.write("---\n\n")

                # Write each stage result
                for idx, result in enumerate(results, 1):
                    f.write(f"\n## Stage {idx}/{total}: {result.agent.upper()}\n\n")
                    if result.error:
                        f.write(f"**Error:** {result.error}\n\n")
                    else:
                        f.write(f"**Model:** {result.model}\n")
                        f.write(f"**Duration:** {result.duration_ms:.0f}ms\n")
                        f.write(f"**Tokens:** {result.total_tokens} (prompt: {result.prompt_tokens}, completion: {result.completion_tokens})\n\n")
                        if result.fallback_used:
                            f.write(f"**Fallback:** {result.original_model} → {result.model} ({result.fallback_reason})\n\n")
                        f.write("**Response:**\n\n")
                        f.write(result.response)
                        f.write("\n\n---\n")

                # Summary
                f.write(f"\n## Summary\n\n")
                f.write(f"- Stages completed: {len(results) - len(errors)}/{total}\n")
                f.write(f"- Total duration: {total_duration:.0f}ms ({total_duration/1000:.1f}s)\n")
                f.write(f"- Total tokens: {total_tokens}\n")
                if errors:
                    f.write(f"\n### Errors\n\n")
                    for err_result in errors:
                        f.write(f"- {err_result.agent}: {err_result.error}\n")

            console.print(f"\n[bold green]💾 Output saved to:[/bold green] [dim]{output_path.absolute()}[/dim]")
        except Exception as e:
            console.print(f"\n[bold yellow]⚠️  Failed to save output:[/bold yellow] {e}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
