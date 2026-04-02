#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const MEMORY_DIR = path.join(process.env.HOME, ".claude", "memory");
const SESSIONS_LOG = path.join(MEMORY_DIR, "sessions.log");

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const data = JSON.parse(input || "{}");
    const cwd = data?.cwd || process.cwd();
    const sessionId = data?.session_id || "unknown";
    const now = new Date().toISOString().replace("T", " ").slice(0, 16);
    const project = path.basename(cwd);

    fs.mkdirSync(MEMORY_DIR, { recursive: true });
    fs.appendFileSync(SESSIONS_LOG, `[${now}] session=${sessionId} project=${project} cwd=${cwd}\n`);
  } catch {
    // Silently ignore
  }
  process.exit(0);
});
