"""Kitty terminal orchestration — spawn Claude in existing grid windows."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class KittyOrchestrator:
    """Send commands to existing Kitty windows (grid tab with A/B/C/D)."""

    base_path: Path = field(default_factory=lambda: Path.home() / "Documents" / "3-git" / "SAP")

    def _kitty(self, *args: str) -> str:
        result = subprocess.run(
            ["kitty", "@", *args],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _get_windows(self) -> list[dict]:
        """Get all kitty windows."""
        output = self._kitty("ls")
        try:
            data = json.loads(output)
            windows = []
            for os_win in data:
                for tab in os_win.get("tabs", []):
                    for win in tab.get("windows", []):
                        windows.append(win)
            return windows
        except json.JSONDecodeError:
            return []

    def _find_window_by_title(self, title: str) -> dict | None:
        """Find a window by its title."""
        for win in self._get_windows():
            if win.get("title", "") == title:
                return win
        return None

    def _find_window_by_cwd(self, cwd_suffix: str) -> dict | None:
        """Find a window whose cwd ends with the given suffix."""
        for win in self._get_windows():
            if win.get("cwd", "").endswith(cwd_suffix):
                return win
        return None

    def send_to_window(self, window_title: str, text: str) -> bool:
        """Send text input to an existing window by title."""
        self._kitty("send-text", f"--match=title:{window_title}", text + "\n")
        return True

    def spawn_claude_in_window(self, worktree: str, prompt: str) -> bool:
        """Launch claude in an existing grid window (A/B/C/D).

        Writes prompt to a temp file to avoid shell length limits.
        """
        cwd = self.base_path / worktree
        if not cwd.exists():
            return False

        # Split prompt into system (context) and task
        # Write to temp files to avoid shell length limits
        system_file = Path(f"/tmp/claude-system-{worktree}.md")
        task_file = Path(f"/tmp/claude-task-{worktree}.md")

        # Everything before "# Task" is system context, after is the task
        if "\n# Task\n" in prompt:
            system, task = prompt.split("\n# Task\n", 1)
        else:
            system = ""
            task = prompt

        system_file.write_text(system.strip())
        task_file.write_text(task.strip())

        launcher = Path(f"/tmp/claude-launch-{worktree}.sh")
        lines = [
            "#!/bin/bash",
            f"cd {cwd}",
            f'claude --system-prompt "$(cat {system_file})" "$(cat {task_file})"',
        ]
        launcher.write_text("\n".join(lines) + "\n")
        launcher.chmod(0o755)

        self._kitty("send-text", f"--match=title:{worktree}", f"bash {launcher}\n")
        return True

    def spawn_batch(self, agents: list[dict]) -> int:
        """Spawn Claude in multiple existing windows.

        agents: [{"name": "architect", "worktree": "A", "prompt": "..."}]
        """
        count = 0
        for agent in agents:
            ok = self.spawn_claude_in_window(agent["worktree"], agent["prompt"])
            if ok:
                count += 1
        return count

    def list_grid_windows(self) -> list[dict]:
        """List windows in the grid tab (A/B/C/D)."""
        results = []
        for win in self._get_windows():
            title = win.get("title", "")
            if title in ("A", "B", "C", "D", "E", "F", "G", "H"):
                results.append(
                    {
                        "title": title,
                        "cwd": win.get("cwd", ""),
                        "is_focused": win.get("is_focused", False),
                    }
                )
        return results
