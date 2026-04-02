"""Token and cost tracking per agent/session."""

from __future__ import annotations

import json
import time
from pathlib import Path

COST_LOG = Path(__file__).parent.parent / "state" / "costs.jsonl"

PRICING = {  # USD per 1M tokens
    "opus": {"input": 15, "output": 75},
    "sonnet": {"input": 3, "output": 15},
    "haiku": {"input": 0.25, "output": 1.25},
}


def log_usage(
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    story: str = "",
) -> dict:
    prices = PRICING.get(model, PRICING["sonnet"])
    cost = (input_tokens / 1_000_000) * prices["input"] + (output_tokens / 1_000_000) * prices[
        "output"
    ]
    entry = {
        "ts": time.time(),
        "agent": agent,
        "story": story,
        "model": model,
        "in": input_tokens,
        "out": output_tokens,
        "cost_usd": round(cost, 4),
    }
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def summary() -> dict:
    if not COST_LOG.exists():
        return {"total_usd": 0, "by_agent": {}, "by_story": {}, "sessions": 0}

    entries = [json.loads(line) for line in COST_LOG.read_text().splitlines() if line.strip()]
    total = sum(e["cost_usd"] for e in entries)

    by_agent: dict[str, float] = {}
    by_story: dict[str, float] = {}
    for e in entries:
        by_agent[e["agent"]] = by_agent.get(e["agent"], 0) + e["cost_usd"]
        if e.get("story"):
            by_story[e["story"]] = by_story.get(e["story"], 0) + e["cost_usd"]

    return {
        "total_usd": round(total, 2),
        "by_agent": {k: round(v, 2) for k, v in by_agent.items()},
        "by_story": {k: round(v, 2) for k, v in by_story.items()},
        "sessions": len(entries),
    }


if __name__ == "__main__":
    import pprint

    pprint.pprint(summary())
