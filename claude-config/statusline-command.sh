#!/usr/bin/env bash
# Claude Code status line — mirrors Jules' PS1 + Claude context info

input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // "?"')
model=$(echo "$input" | jq -r '.model.display_name // "?"')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Git info: [project => branch]
git_info=""
if git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1; then
  project=$(basename "$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null)")
  branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
  if [ -n "$project" ] && [ -n "$branch" ]; then
    git_info=" [$project => $branch]"
  fi
fi

# Context usage badge
ctx_part=""
if [ -n "$used" ]; then
  used_int=$(printf '%.0f' "$used")
  ctx_part=" ctx:${used_int}%"
fi

printf '\033[32m%s@%s \033[34m%s\033[33m%s\033[36m%s\033[0m \033[35m%s\033[0m' \
  "$(whoami)" "$(hostname -s)" "$cwd" "$git_info" "$ctx_part" "$model"
