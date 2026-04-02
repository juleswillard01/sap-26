---
name: SCHEMAS.html is untouchable source of truth
description: Never modify SCHEMAS.html - it's the validated SI mockup that drives all architecture decisions
type: feedback
---

SCHEMAS.html ne doit JAMAIS etre modifie. C'est la maquette SI validee par Jules.

**Why:** Jules a investi du temps a designer ces schemas fonctionnels (8 diagrammes Mermaid). Ils representent l'architecture cible reelle : Google Sheets backend, 8 onglets, iframes dashboard, SheetsAdapter, etc. Le prototype v1 qui a devie de cette architecture a ete archive.

**How to apply:** Toute architecture, PRD, ou implementation doit s'aligner sur SCHEMAS.html. Si un ecart est detecte, c'est le code qui doit changer, pas le schema.
