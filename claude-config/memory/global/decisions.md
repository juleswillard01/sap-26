# Décisions Techniques

## 2026-03-22 : Reconstruction config
- Remplacé Everything Claude Code par Superpowers
- Réduit à 2 agents globaux (python SSR, devops) — tous Opus
- Supprimé tous les MCP servers (zero MCP)
- Extrait CLAUDE.md monolithique en skills modulaires
- Supprimé skipDangerousModePermissionPrompt + wrapper dangerous
- Retiré --unsafe-fixes du hook ruff
- Commands préfixées groupe:commande
- Golden Workflow 6 étapes (PLAN→TDD→REVIEW→VERIFY→COMMIT→REFACTOR)
