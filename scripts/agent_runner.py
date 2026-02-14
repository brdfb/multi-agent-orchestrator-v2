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
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown

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

    # Context-aware solutions
    if "api key" in error_lower or "authentication" in error_lower or "unauthorized" in error_lower:
        console.print("\n[bold cyan]💡 Solution:[/bold cyan]")
        console.print("Add API key to your [yellow].env[/yellow] file:")
        console.print("  [green]ANTHROPIC_API_KEY[/green]=sk-ant-...")
        console.print("  [green]OPENAI_API_KEY[/green]=sk-...")
        console.print("  [green]GOOGLE_API_KEY[/green]=...")
        console.print("\nThen restart: [yellow]make run-api[/yellow]")

    elif "model" in error_lower and ("not found" in error_lower or "deprecated" in error_lower):
        console.print("\n[bold cyan]💡 Solution:[/bold cyan]")
        console.print("The model is no longer available. Try these current models:")
        console.print("  [green]claude-sonnet-4-5[/green] (Anthropic, latest)")
        console.print("  [green]gpt-4o[/green] (OpenAI, latest)")
        console.print("  [green]gemini-2.5-flash[/green] (Google, latest)")

    elif "rate limit" in error_lower or "too many requests" in error_lower or "429" in error_lower:
        console.print("\n[bold cyan]💡 Solution:[/bold cyan]")
        console.print("You've exceeded the API rate limit. Options:")
        console.print("  • Wait 30-60 seconds and try again")
        console.print("  • Use a different model provider")
        console.print("  • Upgrade your API plan for higher limits")

    elif "network" in error_lower or "connection" in error_lower:
        console.print("\n[bold cyan]💡 Solution:[/bold cyan]")
        console.print("Network connection issue. Check:")
        console.print("  • Is the API server running? [yellow]make run-api[/yellow]")
        console.print("  • Is your internet connection working?")
        console.print("  • Are you behind a firewall?")

    elif "timeout" in error_lower:
        console.print("\n[bold cyan]💡 Solution:[/bold cyan]")
        console.print("Request timed out. This usually means:")
        console.print("  • The prompt was too complex (try simplifying)")
        console.print("  • The LLM provider is slow (try a different model)")
        console.print("  • Network latency issues")

    else:
        console.print("\n[bold cyan]💡 Need Help?[/bold cyan]")
        console.print("Troubleshooting steps:")
        console.print("  • Check API server logs for details")
        console.print("  • Verify API keys are set correctly")
        console.print("  • Report issues: [blue]https://github.com/brdfb/multi-agent-orchestrator-v2/issues[/blue]")


def display_response(response: str):
    """Display response with syntax highlighting for code blocks."""
    import re

    # Check if response contains code blocks
    code_block_pattern = r'```(\w+)?\n(.*?)```'

    if '```' in response:
        # Split by code blocks
        parts = re.split(r'(```\w*\n.*?```)', response, flags=re.DOTALL)

        for part in parts:
            if part.startswith('```'):
                # Extract language and code
                match = re.match(r'```(\w+)?\n(.*?)```', part, re.DOTALL)
                if match:
                    lang = match.group(1) or 'python'
                    code = match.group(2).strip()

                    # Display with syntax highlighting
                    syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
                    console.print(syntax)
            elif part.strip():
                # Regular text (markdown)
                console.print(part.strip())
    else:
        # No code blocks, just print as markdown
        console.print(response)


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
