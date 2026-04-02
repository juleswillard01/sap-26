---
name: config-auditor
description: >
  Auditer une config Claude Code. TRIGGER : "audit config", "review setup",
  "check ma config", "optimize config", ou quand on demande d'évaluer
  la qualité de la configuration Claude Code.
---

# Config Auditor

Checklist systématique en 10 points.

## 1. CLAUDE.md
- [ ] < 200 lignes ?
- [ ] Setup/build/test commands ?
- [ ] Tags `<important if="...">` ?

## 2. Settings
- [ ] Pas de skipDangerousModePermissionPrompt ?
- [ ] Permissions granulaires (allow/ask/deny) ?
- [ ] statusLine configurée ?

## 3. Agents
- [ ] Scope clair, non-overlapping ?
- [ ] Tools restreints au nécessaire ?

## 4. Skills
- [ ] YAML frontmatter ?
- [ ] Section Gotchas ?

## 5. Commands
- [ ] Préfixées groupe:commande ?

## 6. Hooks
- [ ] Pas de --unsafe-fixes ?
- [ ] Stop hook présent ?

## 7. Plugins
- [ ] Pas de conflits ?

## 8. MCP
- [ ] Minimum nécessaire ?

## 9. Memory
- [ ] MEMORY.md index ?
- [ ] decisions.md à jour ?

## 10. Sécurité
- [ ] Secrets en deny ?
- [ ] Pas de force-push allowed ?

## Gotchas
- Toujours checker global ET projet — ils mergent
- Les plugins injectent du contexte au démarrage
