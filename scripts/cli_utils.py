#!/usr/bin/env python3
"""Shared CLI utilities for agent_runner.py and chain_runner.py."""

import re
import sys
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

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

    return resolved


def read_file_with_validation(file_path: str) -> str:
    """Read file with validation and error handling."""
    resolved = validate_path_basic(file_path)

    if not resolved.exists():
        console.print(f"\n[bold red]❌ File not found:[/bold red] {file_path}")
        sys.exit(1)

    if not resolved.is_file():
        console.print(f"\n[bold red]❌ Not a file:[/bold red] {file_path}")
        sys.exit(1)

    max_size = 10 * 1024 * 1024  # 10MB
    if resolved.stat().st_size > max_size:
        size_mb = resolved.stat().st_size / 1024 / 1024
        console.print(f"\n[bold red]❌ File too large:[/bold red] {size_mb:.1f}MB")
        console.print(f"   Maximum allowed: 10MB")
        sys.exit(1)

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
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = len(enc.encode(text))
        cost = tokens * 0.000003  # Average across providers
        return tokens, cost
    except Exception:
        tokens = len(text) // 4
        cost = tokens * 0.000003
        return tokens, cost


def show_error_with_solution(error_msg: str):
    """Display error with context-aware solution."""
    console.print(f"\n[bold red]❌ Error:[/bold red] {error_msg}")
    error_lower = error_msg.lower()

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
