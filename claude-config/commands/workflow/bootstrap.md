# Bootstrap la config Claude Code pour un nouveau projet

Poser ces 8 questions en une seule fois :

1. Nom du projet et description one-line ?
2. Langage/framework principal ?
3. Services externes intégrés ?
4. Database/data store ?
5. Déploiement ?
6. Décisions déjà verrouillées ?
7. Ce qui est explicitement HORS scope / INTERDIT ?
8. Approche testing ?

Après les réponses, générer :
- `CLAUDE.md` (< 100 lignes)
- `.claude/settings.json` (overrides projet)
- `.claude/rules/` (5 fichiers max, < 200L chacun)
- `.claude/skills/` (au minimum un skill domaine avec refs/)
- `.claude/memory/` (MEMORY.md + project_vision.md + decisions.md)
- `docs/specs/README.md` (index des specs)
- Branche git `cahier-des-charges`

Puis exécuter `/workflow:audit-project` pour valider.
