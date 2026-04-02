# Audit la config du projet courant .claude/

Vérifier les 10 points :

1. **CLAUDE.md projet** < 200 lignes, pas de duplication avec global
2. **settings.json** : overrides justifiés, pas de conflit avec global
3. **Rules** : < 200 lignes chacune, pas de scopes obsolètes
4. **Skills** : progressive disclosure, refs/scripts/examples, Gotchas
5. **Agents** : devrait être ZERO (Superpowers gère le workflow)
6. **Commands** : devrait être ZERO (commands globales suffisent)
7. **Memory** : decisions à jour
8. **Incohérences** : comptages, transitions, références croisées
9. **Fichiers MD éparpillés** : tout dans docs/ ou .claude/
10. **Config services externes** : documentée dans un skill

**Produire le rapport avec ✅/⚠️/❌ et actions priorisées.**
