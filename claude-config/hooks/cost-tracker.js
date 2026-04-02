#!/usr/bin/env node
/**
 * PostToolUse hook: Track token usage per tool call.
 * Appends to claive/state/costs.jsonl
 */

const fs = require("fs");
const path = require("path");

const COST_LOG = path.join(
  process.env.HOME || "",
  "Documents", "3-git", "SAP", "claive", "state", "costs.jsonl"
);

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const data = JSON.parse(input || "{}");
    const usage = data?.tool_response?.usage || data?.usage || null;

    if (!usage) {
      process.exit(0);
    }

    const entry = {
      ts: Date.now() / 1000,
      tool: data?.tool_name || "unknown",
      in: usage.input_tokens || 0,
      out: usage.output_tokens || 0,
    };

    const dir = path.dirname(COST_LOG);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.appendFileSync(COST_LOG, JSON.stringify(entry) + "\n");
  } catch {
    // Silently ignore
  }
  process.exit(0);
});
