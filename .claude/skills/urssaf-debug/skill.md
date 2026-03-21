---
name: urssaf-debug
description: Debug l'intégration URSSAF/avance-immediate. Utiliser quand une soumission échoue, un token expire, ou un statut ne se met pas à jour.
---

# URSSAF Debug — Diagnostic Intégration

Tu diagnostiques un problème d'intégration URSSAF pour : $ARGUMENTS

## Étape 1 — Identifier le problème
1. Lire les logs récents (`io/cache/error_*.png` si screenshots)
2. Vérifier la config : `src/config.py` → credentials avance-immediate
3. Identifier le type de problème :
   - Connexion ? (login échoue)
   - Soumission ? (payload invalide)
   - Polling ? (statut bloqué)
   - Token ? (expired/invalid)

## Étape 2 — Diagnostiquer
- Connexion : vérifier email/password dans `.env`, tester login manuellement
- Soumission : vérifier le payload contre `.claude/rules/urssaf-api.md`
- Polling : vérifier le cron, les dernières réponses
- Token : vérifier expires_in, refresh timing

## Étape 3 — Corriger
1. Si test → écrire un test de régression
2. Corriger le code
3. Vérifier : `uv run pytest -k urssaf`
4. Documenter la cause dans les logs

## Checks rapides
```bash
# Vérifier la config
uv run python -c "from src.config import get_settings; s = get_settings(); print('Email:', bool(s.avance_immediate_email))"

# Lancer les tests URSSAF
uv run pytest tests/ -k "urssaf or avance" -v

# Vérifier les screenshots d'erreur
ls -la io/cache/error_*.png 2>/dev/null || echo "Pas de screenshots"
```
