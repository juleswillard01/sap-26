---
name: Golden workflow strict — pas de vibecoding
description: Suivre le golden workflow a la lettre, ne pas sauter d'etapes, ne pas prendre de decisions sans validation
type: feedback
---

Ne JAMAIS vibecoder. Suivre le golden workflow strictement dans l'ordre :
0. CDC — valider contre docs/CDC.md, deleguer au cdc-validator
1. Plan — deleguer a l'architect, ADR si decision technique majeure
2. TDD — tests AVANT le code, RED puis GREEN
3. Review — lint + typecheck + code-reviewer + security-auditor
4. Verify — quality gate
5. Commit — conventionnel, atomique
6. Refactor — nettoyage post-commit

**Why:** Jules a reproche que je sautais directement a l'implementation sans suivre le process. Le golden workflow est le contrat de qualite du projet SAP-Facture.

**How to apply:** A chaque feature, lancer `/golden-workflow <tache>`. Deleguer aux agents specialises (cdc-validator, architect, tdd-engineer, code-reviewer, etc.). Ne jamais coder sans plan valide. Ne jamais commiter sans lint+typecheck+tests verts.
