"""Kitty terminal orchestration — replaces tmux for agent spawning."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentWindow:
    name: str
    worktree: Path
    kitty_id: int = 0
    pid: int = 0


@dataclass
class KittyOrchestrator:
    """Manage Claude Code sessions in Kitty tabs/splits."""

    base_path: Path = field(default_factory=lambda: Path.home() / "Documents" / "3-git" / "SAP")
    tab_title: str = "Agents"
    windows: dict[str, AgentWindow] = field(default_factory=dict)

    def _kitty(self, *args: str) -> str:
        result = subprocess.run(
            ["kitty", "@", *args],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def create_tab(self) -> None:
        """Create a new Kitty tab for agents."""
        self._kitty("launch", "--type=tab", f"--title={self.tab_title}")

    def spawn_agent(self, agent_name: str, worktree: str, prompt: str) -> AgentWindow:
        """Spawn a Claude Code session in a new Kitty split."""
        cwd = self.base_path / worktree

        if not cwd.exists():
            raise FileNotFoundError(f"Worktree not found: {cwd}")

        output = self._kitty(
            "launch",
            "--type=window",
            f"--title={agent_name}",
            f"--cwd={cwd}",
            "--keep-focus",
            "claude",
            "--print",
            prompt,
        )

        window = AgentWindow(name=agent_name, worktree=cwd)
        self.windows[agent_name] = window
        return window

    def spawn_interactive(self, agent_name: str, worktree: str, prompt: str) -> AgentWindow:
        """Spawn an interactive Claude session (not --print)."""
        cwd = self.base_path / worktree

        if not cwd.exists():
            raise FileNotFoundError(f"Worktree not found: {cwd}")

        self._kitty(
            "launch",
            "--type=window",
            f"--title={agent_name}",
            f"--cwd={cwd}",
            "claude",
            "-p",
            prompt,
        )

        window = AgentWindow(name=agent_name, worktree=cwd)
        self.windows[agent_name] = window
        return window

    def spawn_batch(self, agents: list[dict]) -> list[AgentWindow]:
        """Spawn multiple agents in one tab with splits.

        agents: [{"name": "architect", "worktree": "A", "prompt": "..."}]
        """
        self.create_tab()
        results = []
        for agent in agents:
            w = self.spawn_agent(agent["name"], agent["worktree"], agent["prompt"])
            results.append(w)
        return results

    def list_windows(self) -> list[dict]:
        """List all Kitty windows."""
        output = self._kitty("ls")
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return []

    def close_agent(self, agent_name: str) -> None:
        """Close a specific agent window."""
        if agent_name in self.windows:
            self._kitty("close-window", f"--match=title:{agent_name}")
            del self.windows[agent_name]

    def close_all(self) -> None:
        """Close all agent windows."""
        for name in list(self.windows.keys()):
            self.close_agent(name)

    def status(self) -> dict:
        """Get status of all agent windows."""
        return {
            name: {"worktree": str(w.worktree), "active": True} for name, w in self.windows.items()
        }
