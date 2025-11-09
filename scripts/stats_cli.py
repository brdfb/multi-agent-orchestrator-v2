#!/usr/bin/env python3
"""CLI tool for viewing usage statistics and cost tracking."""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory_engine import MemoryEngine
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.panel import Panel
from rich import box

console = Console()


def format_cost(cost_usd: float) -> str:
    """Format cost in USD."""
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    return f"${cost_usd:.2f}"


def format_number(n: int) -> str:
    """Format large numbers with commas."""
    return f"{n:,}"


def get_stats_by_agent(memory, days: int = None) -> Dict:
    """Get statistics grouped by agent."""
    query = """
        SELECT
            agent,
            COUNT(*) as count,
            SUM(total_tokens) as total_tokens,
            SUM(cost_usd) as total_cost,
            AVG(total_tokens) as avg_tokens,
            AVG(duration_ms) as avg_duration_ms
        FROM conversations
    """

    params = []
    if days:
        query += " WHERE timestamp >= ?"
        cutoff = datetime.now() - timedelta(days=days)
        params.append(cutoff.isoformat())

    query += " GROUP BY agent ORDER BY count DESC"

    conn = memory.backend._get_connection()
    try:
        cursor = conn.execute(query, params)
        results = cursor.fetchall()

        return [
            {
                'agent': row[0],
                'count': row[1],
                'total_tokens': row[2] or 0,
                'total_cost': row[3] or 0.0,
                'avg_tokens': row[4] or 0,
                'avg_duration_ms': row[5] or 0
            }
            for row in results
        ]
    finally:
        conn.close()


def get_stats_by_model(memory, days: int = None) -> Dict:
    """Get statistics grouped by model."""
    query = """
        SELECT
            model,
            provider,
            COUNT(*) as count,
            SUM(total_tokens) as total_tokens,
            SUM(prompt_tokens) as prompt_tokens,
            SUM(completion_tokens) as completion_tokens,
            SUM(cost_usd) as total_cost
        FROM conversations
    """

    params = []
    if days:
        query += " WHERE timestamp >= ?"
        cutoff = datetime.now() - timedelta(days=days)
        params.append(cutoff.isoformat())

    query += " GROUP BY model, provider ORDER BY count DESC"

    conn = memory.backend._get_connection()
    try:
        cursor = conn.execute(query, params)
        results = cursor.fetchall()

        return [
            {
                'model': row[0],
                'provider': row[1],
                'count': row[2],
                'total_tokens': row[3] or 0,
                'prompt_tokens': row[4] or 0,
                'completion_tokens': row[5] or 0,
                'total_cost': row[6] or 0.0
            }
            for row in results
        ]
    finally:
        conn.close()


def get_overall_stats(memory, days: int = None) -> Dict:
    """Get overall statistics."""
    query = """
        SELECT
            COUNT(*) as total_conversations,
            SUM(total_tokens) as total_tokens,
            SUM(prompt_tokens) as prompt_tokens,
            SUM(completion_tokens) as completion_tokens,
            SUM(cost_usd) as total_cost,
            AVG(duration_ms) as avg_duration_ms,
            COUNT(DISTINCT agent) as unique_agents,
            COUNT(DISTINCT model) as unique_models,
            SUM(CASE WHEN fallback_used = 1 THEN 1 ELSE 0 END) as fallback_count
        FROM conversations
    """

    params = []
    if days:
        query += " WHERE timestamp >= ?"
        cutoff = datetime.now() - timedelta(days=days)
        params.append(cutoff.isoformat())

    conn = memory.backend._get_connection()
    try:
        cursor = conn.execute(query, params)
        row = cursor.fetchone()

        return {
            'total_conversations': row[0] or 0,
            'total_tokens': row[1] or 0,
            'prompt_tokens': row[2] or 0,
            'completion_tokens': row[3] or 0,
            'total_cost': row[4] or 0.0,
            'avg_duration_ms': row[5] or 0,
            'unique_agents': row[6] or 0,
            'unique_models': row[7] or 0,
            'fallback_count': row[8] or 0
        }
    finally:
        conn.close()


def display_overall_stats(stats: Dict, days: int = None):
    """Display overall statistics panel."""
    period = f"Last {days} days" if days else "All time"

    content = f"""[bold]Total Conversations:[/bold] {format_number(stats['total_conversations'])}
[bold]Total Tokens:[/bold] {format_number(stats['total_tokens'])} [dim](prompt: {format_number(stats['prompt_tokens'])}, completion: {format_number(stats['completion_tokens'])})[/dim]
[bold]Total Cost:[/bold] {format_cost(stats['total_cost'])}
[bold]Avg Duration:[/bold] {stats['avg_duration_ms']:.0f}ms
[bold]Unique Agents:[/bold] {stats['unique_agents']}
[bold]Unique Models:[/bold] {stats['unique_models']}
[bold]Fallback Usage:[/bold] {stats['fallback_count']} times"""

    panel = Panel(content, title=f"[bold cyan]📊 Overall Statistics ({period})[/bold cyan]", border_style="cyan")
    console.print(panel)


def display_agent_stats(agent_stats: List[Dict], total_conversations: int):
    """Display agent statistics with bars."""
    console.print(f"\n[bold cyan]🤖 Breakdown by Agent[/bold cyan]")
    console.print("─" * console.width)

    # Create table
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Agent", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Usage %", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Avg Tokens", justify="right")
    table.add_column("Total Cost", justify="right")
    table.add_column("Avg Duration", justify="right")

    for stat in agent_stats:
        percentage = (stat['count'] / total_conversations * 100) if total_conversations > 0 else 0
        table.add_row(
            stat['agent'],
            format_number(stat['count']),
            f"{percentage:.1f}%",
            format_number(stat['total_tokens']),
            f"{stat['avg_tokens']:.0f}",
            format_cost(stat['total_cost']),
            f"{stat['avg_duration_ms']:.0f}ms"
        )

    console.print(table)

    # Visual usage bars
    console.print(f"\n[bold]Usage Distribution:[/bold]")
    max_count = max(s['count'] for s in agent_stats) if agent_stats else 1

    for stat in agent_stats:
        bar_width = int((stat['count'] / max_count) * 40) if max_count > 0 else 0
        bar = "█" * bar_width
        percentage = (stat['count'] / total_conversations * 100) if total_conversations > 0 else 0
        console.print(f"  [cyan]{stat['agent']:10}[/cyan] {bar} [dim]{percentage:.1f}% ({format_number(stat['count'])} requests)[/dim]")


def display_model_stats(model_stats: List[Dict], total_tokens: int):
    """Display model statistics."""
    console.print(f"\n[bold cyan]🔧 Breakdown by Model[/bold cyan]")
    console.print("─" * console.width)

    # Create table
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Model", style="yellow")
    table.add_column("Provider", style="dim")
    table.add_column("Count", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Token %", justify="right")
    table.add_column("Total Cost", justify="right")

    for stat in model_stats:
        percentage = (stat['total_tokens'] / total_tokens * 100) if total_tokens > 0 else 0
        # Shorten model name for display
        model_display = stat['model'].replace('anthropic/', '').replace('openai/', '').replace('gemini/', '')
        table.add_row(
            model_display,
            stat['provider'],
            format_number(stat['count']),
            format_number(stat['total_tokens']),
            f"{percentage:.1f}%",
            format_cost(stat['total_cost'])
        )

    console.print(table)


def display_cost_trends(memory, days: int = 30):
    """Display cost trends over time."""
    query = """
        SELECT
            DATE(timestamp) as date,
            SUM(cost_usd) as daily_cost,
            COUNT(*) as daily_count
        FROM conversations
        WHERE timestamp >= ?
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
    """

    cutoff = datetime.now() - timedelta(days=days)

    conn = memory.backend._get_connection()
    try:
        cursor = conn.execute(query, [cutoff.isoformat()])
        results = cursor.fetchall()

        if not results:
            return

        console.print(f"\n[bold cyan]📈 Cost Trends (Last {days} Days)[/bold cyan]")
        console.print("─" * console.width)

        max_cost = max(row[1] for row in results if row[1]) if results else 1

        for row in results:
            date = row[0]
            daily_cost = row[1] or 0.0
            daily_count = row[2] or 0

            bar_width = int((daily_cost / max_cost) * 30) if max_cost > 0 else 0
            bar = "█" * bar_width

            console.print(f"  [dim]{date}[/dim] {bar} [green]{format_cost(daily_cost)}[/green] [dim]({daily_count} requests)[/dim]")
    finally:
        conn.close()


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-Agent Orchestrator - Usage Statistics & Cost Tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mao-stats                    # All-time statistics
  mao-stats --days 7           # Last 7 days
  mao-stats --days 30 --trends # Last 30 days with trends
        """
    )
    parser.add_argument("--days", "-d", type=int, help="Filter by last N days")
    parser.add_argument("--trends", "-t", action="store_true", help="Show cost trends over time")

    args = parser.parse_args()

    # Get memory engine
    memory = MemoryEngine()

    # Get statistics
    overall = get_overall_stats(memory, args.days)
    agent_stats = get_stats_by_agent(memory, args.days)
    model_stats = get_stats_by_model(memory, args.days)

    # Display statistics
    console.print()
    display_overall_stats(overall, args.days)

    if agent_stats:
        display_agent_stats(agent_stats, overall['total_conversations'])

    if model_stats:
        display_model_stats(model_stats, overall['total_tokens'])

    if args.trends:
        display_cost_trends(memory, args.days or 30)

    console.print()


if __name__ == "__main__":
    main()
