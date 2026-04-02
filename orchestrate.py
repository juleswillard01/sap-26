"""Main orchestrator — spawn Claude agents in Kitty with injected context."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from lib.kitty import KittyOrchestrator

VAULT = Path(__file__).parent.parent / "main" / "claude-config"
AGENTS_YAML = Path(__file__).parent / "config" / "agents.yaml"
WORKTREES = {"A": "A", "B": "B", "C": "C", "D": "D"}

console = Console()
orch = KittyOrchestrator()


def assemble_context(agent_name: str) -> str:
    """Read vault files for an agent and concatenate."""
    agents = yaml.safe_load(AGENTS_YAML.read_text())
    if agent_name not in agents:
        return ""

    parts: list[str] = []
    for rel_path in agents[agent_name].get("inject", []):
        full_path = VAULT / rel_path
        if full_path.exists():
            parts.append(full_path.read_text().strip())
    return "\n\n---\n\n".join(parts)


@click.group()
def cli() -> None:
    """Claive — Claude Code orchestrator via Kitty."""


@cli.command()
@click.argument("agent")
@click.argument("worktree", type=click.Choice(list(WORKTREES.keys())))
@click.argument("task")
def spawn(agent: str, worktree: str, task: str) -> None:
    """Spawn a Claude agent in a Kitty split."""
    agents = yaml.safe_load(AGENTS_YAML.read_text())
    if agent not in agents:
        console.print(f"[red]Unknown agent: {agent}[/red]")
        console.print(f"Available: {', '.join(agents.keys())}")
        return

    context = assemble_context(agent)
    prompt = f"{context}\n\n---\n\n# Task\n\n{task}" if context else task

    console.print(f"[cyan]Spawning {agent}[/cyan] in [yellow]{worktree}[/yellow]")
    orch.spawn_interactive(agent, worktree, prompt)
    console.print("[green]Done[/green]")


@cli.command()
@click.argument("tasks", nargs=-1)
def batch(tasks: tuple[str, ...]) -> None:
    """Spawn 4 agents in parallel on A/B/C/D.

    Usage: python orchestrate.py batch "architect:Design AIS" "tdd:Write tests" "reviewer:Review code" "security:Audit"
    """
    agents_config = yaml.safe_load(AGENTS_YAML.read_text())
    worktree_keys = list(WORKTREES.keys())
    batch_agents = []

    for i, task_str in enumerate(tasks[:4]):
        parts = task_str.split(":", 1)
        if len(parts) != 2:
            console.print(f"[red]Bad format: {task_str}. Use agent:task[/red]")
            continue

        agent_name, task = parts[0].strip(), parts[1].strip()
        if agent_name not in agents_config:
            console.print(f"[red]Unknown agent: {agent_name}[/red]")
            continue

        context = assemble_context(agent_name)
        prompt = f"{context}\n\n---\n\n# Task\n\n{task}" if context else task

        batch_agents.append(
            {
                "name": agent_name,
                "worktree": worktree_keys[i],
                "prompt": prompt,
            }
        )

    if batch_agents:
        console.print(f"[cyan]Spawning {len(batch_agents)} agents...[/cyan]")
        orch.spawn_batch(batch_agents)
        console.print(f"[green]{len(batch_agents)} agents running[/green]")


@cli.command()
def agents() -> None:
    """List available agents."""
    agents_config = yaml.safe_load(AGENTS_YAML.read_text())
    table = Table(title="Available Agents")
    table.add_column("Agent", style="cyan")
    table.add_column("Model", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Context Files", style="dim")

    for name, cfg in agents_config.items():
        table.add_row(
            name,
            cfg.get("model", "sonnet"),
            cfg.get("description", ""),
            str(len(cfg.get("inject", []))),
        )
    console.print(table)


@cli.command()
def status() -> None:
    """Show running agents."""
    st = orch.status()
    if not st:
        console.print("[dim]No agents running[/dim]")
        return

    table = Table(title="Running Agents")
    table.add_column("Agent", style="cyan")
    table.add_column("Worktree", style="yellow")
    for name, info in st.items():
        table.add_row(name, info["worktree"])
    console.print(table)


@cli.command()
def costs() -> None:
    """Show cost tracking summary."""
    sys.path.insert(0, str(Path(__file__).parent / "lib"))
    from dashboard import show_costs

    show_costs()


@cli.command()
def stop() -> None:
    """Close all agent windows."""
    orch.close_all()
    console.print("[green]All agents stopped[/green]")


if __name__ == "__main__":
    cli()
