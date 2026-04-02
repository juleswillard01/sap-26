"""Assemble context from vault files for a specific agent."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

VAULT = Path(__file__).parent.parent / "main" / "claude-config"
CLAIVE = Path(__file__).parent
AGENTS_YAML = CLAIVE / "config" / "agents.yaml"


def assemble(agent_name: str, task: str) -> str:
    agents = yaml.safe_load(AGENTS_YAML.read_text())
    if agent_name not in agents:
        available = ", ".join(agents.keys())
        sys.exit(f"Unknown agent: {agent_name}. Available: {available}")

    config = agents[agent_name]
    parts: list[str] = []

    # Standard inject: relative to vault (claude-config/)
    for rel_path in config.get("inject", []):
        full_path = VAULT / rel_path
        if full_path.exists():
            parts.append(f"# {rel_path}\n\n{full_path.read_text().strip()}")

    # Raw inject: relative to claive/ (for self-development)
    for rel_path in config.get("inject_raw", []):
        full_path = CLAIVE / rel_path.replace("../claive/", "")
        if full_path.exists():
            parts.append(f"# {full_path.name}\n\n```python\n{full_path.read_text().strip()}\n```")

    context = "\n\n---\n\n".join(parts)

    # Instructions from YAML (agent-specific or defaults)
    defaults = agents.get("defaults", {})
    instructions = config.get("instructions", defaults.get("instructions", ""))

    # Assemble: context (system) + instructions + task
    task_block = (
        f"# Instructions\n\n{instructions.strip()}\n\n# Task\n\n{task}"
        if instructions
        else f"# Task\n\n{task}"
    )
    return f"{context}\n\n---\n\n{task_block}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: python inject.py <agent> <task>")
    print(assemble(sys.argv[1], sys.argv[2]))
