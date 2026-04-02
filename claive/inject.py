"""Assemble context from vault files for a specific agent."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

VAULT = Path(__file__).parent.parent / "main" / "claude-config"
AGENTS_YAML = Path(__file__).parent / "config" / "agents.yaml"


def assemble(agent_name: str, task: str) -> str:
    agents = yaml.safe_load(AGENTS_YAML.read_text())
    if agent_name not in agents:
        available = ", ".join(agents.keys())
        sys.exit(f"Unknown agent: {agent_name}. Available: {available}")

    parts: list[str] = []
    for rel_path in agents[agent_name]["inject"]:
        full_path = VAULT / rel_path
        if full_path.exists():
            parts.append(f"# {rel_path}\n\n{full_path.read_text().strip()}")
        else:
            parts.append(f"# {rel_path}\n\n[FILE NOT FOUND]")

    context = "\n\n---\n\n".join(parts)
    return f"{context}\n\n---\n\n# Task\n\n{task}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: python inject.py <agent> <task>")
    print(assemble(sys.argv[1], sys.argv[2]))
