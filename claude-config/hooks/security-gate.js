#!/usr/bin/env node
/**
 * PreToolUse hook: Block dangerous commands before execution.
 * Pattern from claude-forge 6-layer security.
 */

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const data = JSON.parse(input || "{}");
    const toolName = data?.tool_name || "";
    const toolInput = data?.tool_input || {};

    // Only check Bash commands
    if (toolName !== "Bash") {
      process.stdout.write(JSON.stringify({ decision: "approve" }));
      process.exit(0);
    }

    const cmd = toolInput.command || "";
    const blocked = [
      /rm\s+-rf\s+[\/~]/,
      /sudo\s+/,
      /chmod\s+777/,
      />\s*\/dev\/sd/,
      /mkfs\./,
      /dd\s+if=/,
      /:(){ :\|:& };:/,
    ];

    const secretPatterns = [
      /cat\s+\.env/,
      /echo.*password/i,
      /echo.*secret/i,
      /echo.*token/i,
      /curl.*-H.*Authorization/,
    ];

    for (const pattern of blocked) {
      if (pattern.test(cmd)) {
        process.stdout.write(JSON.stringify({
          decision: "deny",
          reason: `Blocked dangerous command: ${cmd.substring(0, 50)}`
        }));
        process.exit(0);
      }
    }

    for (const pattern of secretPatterns) {
      if (pattern.test(cmd)) {
        process.stdout.write(JSON.stringify({
          decision: "deny",
          reason: `Blocked potential secret exposure: ${cmd.substring(0, 50)}`
        }));
        process.exit(0);
      }
    }

    process.stdout.write(JSON.stringify({ decision: "approve" }));
  } catch {
    process.stdout.write(JSON.stringify({ decision: "approve" }));
  }
  process.exit(0);
});
