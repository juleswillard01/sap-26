"""Rich dashboard for cost tracking and agent status."""

from __future__ import annotations

from costs import summary
from rich.console import Console
from rich.table import Table


def show_costs() -> None:
    console = Console()
    data = summary()

    console.print(f"\n[bold]Total: ${data['total_usd']}[/bold] ({data['sessions']} sessions)\n")

    if data["by_agent"]:
        table = Table(title="Cost by Agent")
        table.add_column("Agent", style="cyan")
        table.add_column("Cost (USD)", style="green", justify="right")
        for agent, cost in sorted(data["by_agent"].items(), key=lambda x: -x[1]):
            table.add_row(agent, f"${cost}")
        console.print(table)

    if data["by_story"]:
        table = Table(title="Cost by Story")
        table.add_column("Story", style="cyan")
        table.add_column("Cost (USD)", style="green", justify="right")
        for story, cost in sorted(data["by_story"].items(), key=lambda x: -x[1]):
            table.add_row(story, f"${cost}")
        console.print(table)


if __name__ == "__main__":
    show_costs()
