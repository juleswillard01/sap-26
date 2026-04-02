"""Claive setup — check and install all dependencies for the orchestrator."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

console = Console()

GLOBAL_CLAUDE = Path.home() / ".claude"
CONFIG_LAYERS = Path(__file__).parent / "config" / "config-layers.yaml"
AGENTS_YAML = Path(__file__).parent / "config" / "agents.yaml"


@dataclass
class CheckResult:
    name: str
    category: str
    status: str  # ok, missing, error
    fix_cmd: str = ""


def load_config() -> dict:
    if CONFIG_LAYERS.exists():
        return yaml.safe_load(CONFIG_LAYERS.read_text())
    return {}


def check_binary(name: str) -> bool:
    return shutil.which(name) is not None


def check_plugin_installed(plugin: str) -> bool:
    result = subprocess.run(
        ["claude", "plugin", "list"],
        capture_output=True,
        text=True,
    )
    return plugin in result.stdout


def check_marketplace(name: str) -> bool:
    result = subprocess.run(
        ["claude", "plugin", "marketplace", "list"],
        capture_output=True,
        text=True,
    )
    return name in result.stdout


def check_skill(name: str) -> bool:
    global_skills = GLOBAL_CLAUDE / "skills" / name / "SKILL.md"
    project_skills = Path.cwd() / ".claude" / "skills" / name / "SKILL.md"
    return global_skills.exists() or project_skills.exists()


def check_hook(name: str) -> bool:
    for ext in (".py", ".sh", ".js"):
        if (GLOBAL_CLAUDE / "hooks" / f"{name}{ext}").exists():
            return True
    return False


def check_command(name: str) -> bool:
    parts = name.split("/")
    for base in [GLOBAL_CLAUDE / "commands", Path.cwd() / ".claude" / "commands"]:
        candidate = base / "/".join(parts[:-1]) / f"{parts[-1]}.md"
        if candidate.exists():
            return True
    return False


def run_checks() -> list[CheckResult]:
    results: list[CheckResult] = []

    # --- Binaries ---
    for bin_name, install in [
        ("claude", "curl -fsSL https://claude.ai/install | sh"),
        ("git", "apt install git"),
        ("python3", "apt install python3"),
        ("ruff", "uv tool install ruff"),
        ("pre-commit", "uv tool install pre-commit"),
        ("kitty", "apt install kitty"),
        ("jq", "apt install jq"),
    ]:
        results.append(
            CheckResult(
                name=bin_name,
                category="binary",
                status="ok" if check_binary(bin_name) else "missing",
                fix_cmd=install,
            )
        )

    # --- Plugins ---
    for plugin in [
        "context7@claude-plugins-official",
        "linear@claude-plugins-official",
        "superpowers@claude-plugins-official",
        "playwright@claude-plugins-official",
        "security-guidance@claude-plugins-official",
        "frontend-design@claude-plugins-official",
    ]:
        results.append(
            CheckResult(
                name=plugin,
                category="plugin",
                status="ok" if check_plugin_installed(plugin) else "missing",
                fix_cmd=f"claude plugin install {plugin}",
            )
        )

    # --- Marketplaces ---
    for mp, repo in [
        ("agentsys", "agent-sh/agentsys"),
        ("claude-code-skills", "alirezarezvani/claude-skills"),
        ("superpowers-marketplace", "obra/superpowers-marketplace"),
    ]:
        results.append(
            CheckResult(
                name=mp,
                category="marketplace",
                status="ok" if check_marketplace(mp) else "missing",
                fix_cmd=f"claude plugin marketplace add {repo}",
            )
        )

    # --- AgentSys ---
    results.append(
        CheckResult(
            name="agentsys (npx)",
            category="tool",
            status="ok" if check_binary("npx") else "missing",
            fix_cmd="npm install -g npm && npx agentsys --tool claude",
        )
    )

    # --- Skills (global) ---
    for skill in [
        "first-principles",
        "config-auditor",
        "project-bootstrap",
        "agent-designer",
        "api-test-suite-builder",
        "ci-cd-pipeline-builder",
        "codebase-onboarding",
        "database-designer",
        "dependency-auditor",
        "docker-development",
        "env-secrets-manager",
        "git-worktree-manager",
        "llm-cost-optimizer",
    ]:
        results.append(
            CheckResult(
                name=skill,
                category="skill",
                status="ok" if check_skill(skill) else "missing",
                fix_cmd=f"cp -r ~/.claude/plugins/marketplaces/claude-code-skills/engineering/{skill} ~/.claude/skills/",
            )
        )

    # --- Hooks ---
    for hook in [
        "security_gate",
        "python_ruff_format",
        "memory_auto_capture",
        "cost_tracker",
        "session_summary",
        "pre_compact_context",
        "remote-command-guard",
        "db-guard",
        "rate-limiter",
        "output-secret-filter",
        "security-auto-trigger",
        "work-tracker-prompt",
        "work-tracker-tool",
        "work-tracker-stop",
        "session-wrap-suggest",
    ]:
        results.append(
            CheckResult(
                name=hook,
                category="hook",
                status="ok" if check_hook(hook) else "missing",
                fix_cmd=f"cp /tmp/claude-forge/hooks/{hook}.sh ~/.claude/hooks/ || echo 'source not found'",
            )
        )

    # --- Commands ---
    for cmd in [
        "memory/reflect",
        "memory/housekeeping",
        "memory/search",
    ]:
        results.append(
            CheckResult(
                name=cmd,
                category="command",
                status="ok" if check_command(cmd) else "missing",
                fix_cmd="mkdir -p ~/.claude/commands/memory",
            )
        )

    # --- Pre-commit config ---
    precommit_cfg = Path.cwd() / ".pre-commit-config.yaml"
    results.append(
        CheckResult(
            name=".pre-commit-config.yaml",
            category="config",
            status="ok" if precommit_cfg.exists() else "missing",
            fix_cmd="pre-commit install",
        )
    )

    # --- Kitty remote control ---
    kitty_conf = Path.home() / ".config" / "kitty" / "kitty.conf"
    has_remote = False
    if kitty_conf.exists():
        has_remote = "allow_remote_control" in kitty_conf.read_text()
    results.append(
        CheckResult(
            name="kitty remote control",
            category="config",
            status="ok" if has_remote else "missing",
            fix_cmd='echo "allow_remote_control yes" >> ~/.config/kitty/kitty.conf',
        )
    )

    # --- Orchestrator files ---
    for f in ["config/agents.yaml", "inject.py", "lib/kitty.py", "lib/costs.py", "orchestrate.py"]:
        fpath = Path(__file__).parent / f
        results.append(
            CheckResult(
                name=f"claive/{f}",
                category="orchestrator",
                status="ok" if fpath.exists() else "missing",
                fix_cmd="git checkout claive",
            )
        )

    return results


def cmd_check() -> None:
    results = run_checks()

    table = Table(title="Claive Health Check")
    table.add_column("Status", style="bold", width=4)
    table.add_column("Category", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Fix", style="yellow")

    ok = 0
    missing = 0
    for r in results:
        if r.status == "ok":
            table.add_row("[green]OK", r.category, r.name, "")
            ok += 1
        else:
            table.add_row("[red]MISS", r.category, r.name, r.fix_cmd)
            missing += 1

    console.print(table)
    console.print(f"\n[green]{ok} OK[/green] · [red]{missing} missing[/red]")

    if missing > 0:
        console.print("\n[yellow]Run 'python setup.py install' to fix missing items[/yellow]")


def cmd_install() -> None:
    results = run_checks()
    missing = [r for r in results if r.status == "missing"]

    if not missing:
        console.print("[green]Everything is installed.[/green]")
        return

    console.print(f"[yellow]Installing {len(missing)} missing items...[/yellow]\n")

    for r in missing:
        console.print(f"[cyan]Installing {r.name}...[/cyan]")
        console.print(f"  [dim]$ {r.fix_cmd}[/dim]")

        result = subprocess.run(
            r.fix_cmd,
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("  [green]OK[/green]")
        else:
            console.print(f"  [red]FAILED: {result.stderr[:100]}[/red]")

    console.print("\n[yellow]Run 'python setup.py check' to verify[/yellow]")


def cmd_doctor() -> None:
    console.print("[bold]Running full diagnostic...[/bold]\n")
    cmd_check()

    console.print("\n[bold]Testing hooks...[/bold]")
    for hook in [
        "security_gate",
        "memory_auto_capture",
        "cost_tracker",
        "pre_compact_context",
        "python_ruff_format",
        "session_summary",
    ]:
        hook_path = GLOBAL_CLAUDE / "hooks" / f"{hook}.py"
        if hook_path.exists():
            result = subprocess.run(
                f"echo '{{}}' | python3 {hook_path}",
                shell=True,
                capture_output=True,
                text=True,
            )
            status = "[green]OK" if result.returncode == 0 else f"[red]FAIL: {result.stderr[:60]}"
            console.print(f"  {hook}: {status}")

    console.print("\n[bold]Testing orchestrator...[/bold]")
    orch = Path(__file__).parent / "orchestrate.py"
    if orch.exists():
        result = subprocess.run(
            [sys.executable, str(orch), "agents"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent),
        )
        if result.returncode == 0:
            console.print("  orchestrate.py agents: [green]OK[/green]")
        else:
            console.print("  orchestrate.py agents: [red]FAIL[/red]")

    console.print("\n[bold]Testing Kitty grid...[/bold]")
    result = subprocess.run(
        ["kitty", "@", "ls"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            windows = sum(
                1
                for ow in data
                for tab in ow.get("tabs", [])
                for win in tab.get("windows", [])
                if win.get("title", "") in ("A", "B", "C", "D", "E", "F", "G", "H")
            )
            console.print(f"  Grid windows: [green]{windows}/8[/green]")
        except json.JSONDecodeError:
            console.print("  Grid: [red]parse error[/red]")
    else:
        console.print("  Kitty remote: [red]not available[/red]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("Usage: python setup.py [check|install|doctor]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "check":
        cmd_check()
    elif cmd == "install":
        cmd_install()
    elif cmd == "doctor":
        cmd_doctor()
    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        sys.exit(1)
