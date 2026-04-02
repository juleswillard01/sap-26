# Audit la config globale ~/.claude/

Vérifier les 10 points :

1. **CLAUDE.md** < 200 lignes, setup/build/test commands, tags `<important>`
2. **settings.json** : sécurité, permissions granulaires, statusLine
3. **Agents** : scope clair, tools restreints, modèle justifié
4. **Skills** : frontmatter YAML, description = trigger, section Gotchas
5. **Commands** : préfixées `groupe:commande`, pattern orchestration
6. **Hooks** : pas `--unsafe-fixes`, Stop hook présent, PostToolUse format
7. **Plugins** : pas de conflits, budget tokens OK
8. **MCP** : devrait être vide (zero MCP)
9. **Memory** : MEMORY.md index, decisions.md à jour
10. **Sécurité** : pas de skip-dangerous, deny sur secrets

**Produire le rapport avec ✅/⚠️/❌ et actions priorisées.**
