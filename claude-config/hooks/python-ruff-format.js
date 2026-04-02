#!/usr/bin/env node
/**
 * PostToolUse hook: Auto-format Python files with ruff after Edit/Write
 */

const { spawnSync } = require("child_process");
const fs = require("fs");

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const data = JSON.parse(input || "{}");
    const filePath = data?.tool_input?.file_path || data?.tool_response?.file_path || "";

    if (!filePath.endsWith(".py") || !fs.existsSync(filePath)) {
      process.exit(0);
    }

    // ruff format
    spawnSync("ruff", ["format", filePath], { stdio: "pipe" });

    // ruff check --fix (safe fixes only, NO --unsafe-fixes)
    spawnSync("ruff", ["check", "--fix", filePath], { stdio: "pipe" });
  } catch {
    // Silently ignore errors
  }
  process.exit(0);
});
