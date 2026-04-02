#!/usr/bin/env node
/**
 * PostToolUse hook: Auto-capture tool calls to observations.md
 * Simplified claude-mem pattern (no daemon, no SQLite, just append to markdown).
 */

const fs = require("fs");
const path = require("path");

const OBSERVATIONS = path.join(
  process.env.CLAUDE_PROJECT_DIR || process.cwd(),
  "claude-config", "memory", "observations.md"
);

const SKIP_TOOLS = ["SlashCommand", "Skill", "TodoWrite", "AskUserQuestion", "TaskCreate", "TaskUpdate", "TaskList"];

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const data = JSON.parse(input || "{}");
    const toolName = data?.tool_name || "";

    if (SKIP_TOOLS.includes(toolName)) {
      process.exit(0);
    }

    // Only capture significant tool calls
    const toolInput = data?.tool_input || {};
    const filePath = toolInput.file_path || toolInput.path || "";

    if (!filePath && toolName !== "Bash") {
      process.exit(0);
    }

    const now = new Date().toISOString().slice(0, 10);
    const tag = toolName.toLowerCase();
    const detail = filePath
      ? `${toolName} on ${path.basename(filePath)}`
      : `${toolName}: ${(toolInput.command || "").substring(0, 80)}`;

    const entry = `- ${now} [${tag}]: ${detail}\n`;

    if (fs.existsSync(OBSERVATIONS)) {
      fs.appendFileSync(OBSERVATIONS, entry);
    }
  } catch {
    // Silently ignore
  }
  process.exit(0);
});
