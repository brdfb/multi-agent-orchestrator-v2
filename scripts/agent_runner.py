#!/usr/bin/env python3
"""CLI tool for running agents."""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_env_source
from core.agent_runtime import AgentRuntime
from core.session_manager import get_session_manager
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


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

    # Auto-generate CLI session (v0.11.0)
    session_manager = get_session_manager()
    session_id = session_manager.get_or_create_session(
        source="cli",
        metadata={"pid": os.getpid()}
    )

    # Run agent
    runtime = AgentRuntime()
    result = runtime.run(agent=agent, prompt=prompt, session_id=session_id)

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


if __name__ == "__main__":
    main()
