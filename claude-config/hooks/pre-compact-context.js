#!/usr/bin/env node
/**
 * Stop hook: Save critical context before compaction.
 * Writes current task state to .claude/specs/current-task-context.md
 */

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const OUTPUT = path.join(
  process.env.CLAUDE_PROJECT_DIR || process.cwd(),
  ".claude", "specs", "current-task-context.md"
);

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd();

    let branch = "";
    try {
      branch = execFileSync("git", ["branch", "--show-current"], { cwd, encoding: "utf-8" }).trim();
    } catch { branch = "unknown"; }

    let diff = "";
    try {
      diff = execFileSync("git", ["diff", "--stat"], { cwd, encoding: "utf-8" }).trim();
    } catch { diff = ""; }

    const now = new Date().toISOString().slice(0, 16);

    const content = `# Task Context (auto-saved ${now})\n\n## Branch\n${branch}\n\n## Changed Files\n\`\`\`\n${diff || "no changes"}\n\`\`\`\n\n## Resume Instructions\nRead this file to restore context after compaction.\nCheck git log for recent commits and git diff for pending changes.\n`;

    const dir = path.dirname(OUTPUT);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(OUTPUT, content);
  } catch {
    // Silently ignore
  }
  process.exit(0);
});
