---
name: project-bootstrap
description: >
  Bootstrapper la config Claude Code d'un nouveau projet. TRIGGER :
  nouveau projet, "init project", "setup claude", "configure ce projet",
  ou quand aucun CLAUDE.md projet n'existe dans le répertoire courant.
---

# Project Bootstrap

Interview l'utilisateur puis génère une config projet complète.

## Interview (8 questions, toutes en une fois)
1. Nom du projet et description one-line ?
2. Langage/framework principal ?
3. Services externes intégrés ?
4. Database/data store ?
5. Déploiement ?
6. Décisions verrouillées ?
7. Hors scope / interdit ?
8. Approche testing ?

## Génération
Après réponses, créer :
- `CLAUDE.md` < 100 lignes
- `.claude/settings.json` (overrides projet)
- `.claude/rules/` (5 fichiers max, < 200L chacun)
- `.claude/skills/<domaine>/SKILL.md` (au minimum un skill avec refs/)
- `.claude/memory/` (MEMORY.md + project_vision.md + decisions.md)
- `docs/specs/README.md`
- Branche git `cahier-des-charges`

## Gotchas
- Settings projet MERGE avec global — n'ajouter que ce qui diffère
- Ne pas dupliquer les rules globales
- CLAUDE.md DOIT rester sous 100 lignes
