"""Claive Heartbeat — OODA loop for autonomous orchestration."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

SAP_ROOT = Path(__file__).parent.parent / "main"
VAULT = SAP_ROOT / "claude-config"
AGENTS_YAML = Path(__file__).parent / "config" / "agents.yaml"
COST_LOG = Path(__file__).parent / "state" / "costs.jsonl"
HEARTBEAT_LOG = Path(__file__).parent / "state" / "heartbeat.jsonl"
BUDGET_LIMIT = 20.0  # USD par jour


def run(cmd: list[str], cwd: str | None = None) -> str:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
        ).stdout.strip()
    except Exception:
        return ""


# ── OBSERVE ──────────────────────────────────────────────


def observe() -> dict:
    """Gather current state from all sources."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "git": {},
        "memory": {},
        "costs": {},
        "worktrees": {},
    }

    # Git status
    state["git"]["branch"] = run(["git", "branch", "--show-current"], cwd=str(SAP_ROOT))
    state["git"]["dirty_files"] = len(
        run(["git", "status", "--porcelain"], cwd=str(SAP_ROOT)).splitlines()
    )
    state["git"]["last_commit"] = run(["git", "log", "--oneline", "-1"], cwd=str(SAP_ROOT))

    # Memory state
    hot = VAULT / "memory" / "hot-memory.md"
    obs = VAULT / "memory" / "observations.md"
    if hot.exists():
        state["memory"]["hot_lines"] = len(hot.read_text().splitlines())
    if obs.exists():
        state["memory"]["observations_count"] = len(
            [l for l in obs.read_text().splitlines() if l.startswith("- ")]
        )

    # Cost tracking
    if COST_LOG.exists():
        entries = [json.loads(l) for l in COST_LOG.read_text().splitlines() if l.strip()]
        today = datetime.now().strftime("%Y-%m-%d")
        today_entries = [
            e for e in entries if datetime.fromtimestamp(e["ts"]).strftime("%Y-%m-%d") == today
        ]
        state["costs"]["total_usd"] = round(sum(e.get("cost_usd", 0) for e in entries), 2)
        state["costs"]["today_usd"] = round(sum(e.get("cost_usd", 0) for e in today_entries), 2)
        state["costs"]["sessions"] = len(entries)
    else:
        state["costs"] = {"total_usd": 0, "today_usd": 0, "sessions": 0}

    # Worktree status
    for wt in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        wt_path = Path(__file__).parent.parent / wt
        if wt_path.exists():
            branch = run(["git", "branch", "--show-current"], cwd=str(wt_path))
            dirty = len(run(["git", "status", "--porcelain"], cwd=str(wt_path)).splitlines())
            state["worktrees"][wt] = {"branch": branch, "dirty": dirty}

    return state


# ── ORIENT ───────────────────────────────────────────────


def orient(state: dict) -> list[dict]:
    """Analyze state and identify issues/opportunities."""
    findings = []

    # Budget check
    if state["costs"]["today_usd"] >= BUDGET_LIMIT:
        findings.append(
            {
                "type": "alert",
                "severity": "critical",
                "message": f"Budget daily depasse: ${state['costs']['today_usd']} / ${BUDGET_LIMIT}",
                "action": "stop_all",
            }
        )

    # Hot memory overflow
    if state["memory"].get("hot_lines", 0) > 50:
        findings.append(
            {
                "type": "maintenance",
                "severity": "medium",
                "message": f"hot-memory.md trop long: {state['memory']['hot_lines']} lignes (max 50)",
                "action": "housekeeping",
            }
        )

    # Observations overflow (needs /reflect)
    if state["memory"].get("observations_count", 0) > 100:
        findings.append(
            {
                "type": "maintenance",
                "severity": "medium",
                "message": f"observations.md a {state['memory']['observations_count']} entrees — /reflect needed",
                "action": "reflect",
            }
        )

    # Dirty worktrees (uncommitted work)
    for wt, info in state.get("worktrees", {}).items():
        if info["dirty"] > 10:
            findings.append(
                {
                    "type": "alert",
                    "severity": "high",
                    "message": f"Worktree {wt} ({info['branch']}): {info['dirty']} fichiers non commites",
                    "action": "review_worktree",
                    "worktree": wt,
                }
            )

    # Main branch dirty
    if state["git"]["dirty_files"] > 5:
        findings.append(
            {
                "type": "alert",
                "severity": "medium",
                "message": f"Main: {state['git']['dirty_files']} fichiers non commites",
                "action": "commit_main",
            }
        )

    return findings


# ── DECIDE ───────────────────────────────────────────────


def decide(findings: list[dict]) -> list[dict]:
    """Decide which actions to take based on findings."""
    actions = []

    for f in findings:
        if f["action"] == "stop_all":
            actions.append(
                {"cmd": "echo", "args": ["BUDGET EXCEEDED — no agents spawned"], "priority": 0}
            )
            return actions  # stop everything

        if f["action"] == "housekeeping":
            actions.append({"cmd": "memory", "args": ["housekeeping"], "priority": 2})

        if f["action"] == "reflect":
            actions.append({"cmd": "memory", "args": ["reflect"], "priority": 2})

        if f["action"] == "review_worktree":
            actions.append(
                {
                    "cmd": "spawn",
                    "args": [
                        "reviewer",
                        f["worktree"],
                        f"Review uncommitted changes in worktree {f['worktree']}",
                    ],
                    "priority": 1,
                }
            )

    # Sort by priority (0 = highest)
    actions.sort(key=lambda a: a.get("priority", 5))
    return actions


# ── ACT ──────────────────────────────────────────────────


def act(actions: list[dict], dry_run: bool = True) -> None:
    """Execute decided actions."""
    for a in actions:
        if a["cmd"] == "echo":
            console.print(f"[red bold]{a['args'][0]}[/red bold]")

        elif a["cmd"] == "spawn":
            agent, worktree, task = a["args"]
            console.print(f"[cyan]SPAWN {agent} → {worktree}:[/cyan] {task}")
            if not dry_run:
                subprocess.run(
                    [
                        "python3",
                        str(Path(__file__).parent / "orchestrate.py"),
                        "spawn",
                        agent,
                        worktree,
                        task,
                    ],
                    cwd=str(Path(__file__).parent),
                )

        elif a["cmd"] == "memory":
            subcmd = a["args"][0]
            console.print(f"[yellow]MEMORY /{subcmd}[/yellow]")
            # Memory commands are Claude Code slash commands — log for manual execution
            if not dry_run:
                console.print(f"  → Run /memory:{subcmd} in Claude Code")


def log_heartbeat(state: dict, findings: list[dict], actions: list[dict]) -> None:
    """Append heartbeat to log."""
    entry = {
        "ts": time.time(),
        "costs_today": state["costs"]["today_usd"],
        "findings": len(findings),
        "actions": len(actions),
        "worktrees_dirty": sum(1 for w in state.get("worktrees", {}).values() if w["dirty"] > 0),
    }
    HEARTBEAT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with HEARTBEAT_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# ── DISPLAY ──────────────────────────────────────────────


def display_state(state: dict, findings: list[dict], actions: list[dict]) -> None:
    """Rich display of current state."""
    now = datetime.now().strftime("%H:%M:%S")

    # State table
    table = Table(title=f"Heartbeat {now}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Branch", state["git"]["branch"])
    table.add_row("Last commit", state["git"]["last_commit"])
    table.add_row("Dirty files (main)", str(state["git"]["dirty_files"]))
    table.add_row("Cost today", f"${state['costs']['today_usd']}")
    table.add_row("Cost total", f"${state['costs']['total_usd']}")
    table.add_row("Observations", str(state["memory"].get("observations_count", 0)))
    table.add_row("Hot memory lines", str(state["memory"].get("hot_lines", 0)))
    table.add_row("Active worktrees", str(len(state.get("worktrees", {}))))
    console.print(table)

    # Findings
    if findings:
        for f in findings:
            color = {"critical": "red", "high": "yellow", "medium": "blue"}.get(
                f["severity"], "white"
            )
            console.print(f"  [{color}][{f['severity'].upper()}][/{color}] {f['message']}")
    else:
        console.print("  [green]No issues found[/green]")

    # Actions
    if actions:
        console.print(
            Panel(
                "\n".join(
                    f"{'→ ' + a['cmd'] + ' ' + ' '.join(str(x) for x in a['args'])}"
                    for a in actions
                ),
                title="Actions",
            )
        )


# ── CLI ──────────────────────────────────────────────────


@click.command()
@click.option("--interval", "-i", default=300, help="Seconds between heartbeats (default 5min)")
@click.option("--once", is_flag=True, help="Run once and exit")
@click.option("--execute", is_flag=True, help="Actually execute actions (default: dry-run)")
@click.option("--budget", "-b", default=20.0, help="Daily budget USD")
def main(interval: int, once: bool, execute: bool, budget: float) -> None:
    """Claive Heartbeat — OODA loop for autonomous orchestration."""
    global BUDGET_LIMIT
    BUDGET_LIMIT = budget

    console.print(
        f"[bold]Claive Heartbeat[/bold] — interval:{interval}s budget:${budget} {'LIVE' if execute else 'DRY-RUN'}\n"
    )

    while True:
        state = observe()
        findings = orient(state)
        actions = decide(findings)

        display_state(state, findings, actions)
        act(actions, dry_run=not execute)
        log_heartbeat(state, findings, actions)

        if once:
            break

        console.print(f"\n[dim]Next heartbeat in {interval}s...[/dim]\n")
        time.sleep(interval)


if __name__ == "__main__":
    main()
