# Phase PLAN du Golden Workflow

Lance 10 Agent tools en parallèle dans un seul message :

1. **Brainstorm requirements** — lister toutes les exigences explicites et implicites
2. **Brainstorm edge cases** — identifier les cas limites et scenarios d'erreur
3. **Brainstorm dependencies** — mapper les dépendances internes et externes
4. **Architect data model** — concevoir les structures de données (Pydantic models)
5. **Architect API design** — concevoir les endpoints/CLI commands
6. **Architect file structure** — proposer l'arborescence fichiers
7. **Security review** — identifier les risques de sécurité dès la conception
8. **Test strategy** — définir les scénarios de test par requirement
9. **Performance analysis** — identifier les goulots potentiels
10. **Prior art search** — chercher des patterns existants dans le codebase

Après les 10 agents, synthétiser en :
- `plan.md` — plan d'implémentation avec tâches numérotées
- `evals.md` — critères de validation pour chaque tâche

**Ne PAS écrire de code.** Attendre validation utilisateur du plan.
Créer la branche git : `groupe-feature` depuis main.
