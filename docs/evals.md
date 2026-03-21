# Évaluations — SAP-Facture

## Critères de Qualité Code

### Lint & Types
| Critère | Seuil | Outil |
|---------|-------|-------|
| Lint errors | 0 | `uv run ruff check src/ tests/` |
| Format | 0 fichiers non formatés | `uv run ruff format --check` |
| Type errors | 0 | `uv run pyright src/` |

### Tests
| Critère | Seuil | Outil |
|---------|-------|-------|
| Coverage | ≥ 80% | `uv run pytest --cov=src --cov-fail-under=80` |
| Tests passants | 100% | `uv run pytest tests/` |
| Pas de print() | 0 dans src/ | `grep -r "print(" src/` |

### Architecture
| Critère | Vérification |
|---------|-------------|
| Pas de création facture | grep "create_invoice" → 0 |
| Pas de soumission URSSAF | grep "submit.*urssaf" → 0 |
| Playwright LECTURE seule | Pas de form fill dans adapters AIS/Indy (sauf login) |
| Machine à états correcte | 11 états, transitions validées |

## Critères Fonctionnels

### sap sync (AIS → Sheets)
| Test | Attendu |
|------|---------|
| Login AIS réussi | Session établie, pas d'erreur |
| Scrape statuts | Tous les statuts extraits correctement |
| Détection changements | Statuts modifiés détectés vs Sheets |
| Maj Sheets | Onglet Factures mis à jour |
| Alerte T+36h | Email envoyé si facture en attente > 36h |

### sap reconcile (Indy → Sheets → Lettrage)
| Test | Attendu |
|------|---------|
| Login Indy réussi | Session établie |
| Export Journal CSV | Fichier CSV téléchargé |
| Parse CSV | Données normalisées |
| Import Transactions | Onglet Transactions mis à jour, dedup indy_id |
| Lettrage scoring | Score calculé pour chaque facture PAYÉE |
| Rapprochement | LETTRE_AUTO si score ≥ 80 |

### sap status
| Test | Attendu |
|------|---------|
| Résumé affiché | Factures en attente, solde, impayés |
| Données fraîches | Basé sur dernier sync |

## Critères de Performance
| Métrique | Seuil |
|----------|-------|
| Temps sync AIS | < 30s |
| Temps reconcile Indy | < 60s |
| Cache hit rate | > 70% sur reads identiques |
| Rate limit respect | 0 erreur 429 |

## Critères RGPD
| Critère | Vérification |
|---------|-------------|
| Pas de données bancaires dans logs | grep montant/IBAN dans logs → 0 |
| Screenshots sans données sensibles | Vérifier io/cache/ |
| .env pas commité | .gitignore vérifié |
| Credentials pas en clair | grep password/secret dans src/ → 0 |
