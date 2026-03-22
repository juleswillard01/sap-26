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

## AIS REST API — Critères Qualité

### Fonctionnel
| Critère | Attendu | Outil |
|---------|---------|-------|
| Login réussit | Token format token_XXXXX-XXXXX-... (200 OK) | httpx mock + test |
| Read collection | Retourne data.items (liste) | httpx mock + test |
| Auth error | 401 ou boolean: false sur endpoint protégé | httpx mock + test |
| Retry backoff | 3 tentatives, délai exponentiel (2s, 4s, 8s) | tenacity + test |
| Timeout | 30s max par requête httpx | httpx settings |

### Sécurité
| Critère | Vérification |
|---------|-------------|
| Pas de credentials dans logs | grep email/password dans tests/ logs → 0 |
| Token mémoire only | Pas de stockage fichier persistant |
| HTTPS obligatoire | Pas d'appels http:// non-test (base_url validation) |
| Pydantic validation | Réponses API parsées avant utilisation |
| Pas de eval/exec | grep eval/exec dans src/adapters/ais_adapter.py → 0 |

### Code
| Critère | Seuil | Outil |
|---------|-------|-------|
| Coverage src/adapters/ais_adapter.py | ≥ 80% | pytest --cov=src.adapters.ais_adapter |
| Ruff check | 0 erreurs | ruff check src/adapters/ais_adapter.py |
| Ruff format | 0 fichiers non formatés | ruff format --check src/adapters/ais_adapter.py |
| Pyright strict | 0 type errors | pyright --strict src/adapters/ais_adapter.py |
| Pas de print() | 0 dans src/adapters/ais_adapter.py | grep -r "print(" → 0 |
| Taille fichier | < 300 lignes | wc -l |
| Taille fonctions | < 50 lignes max | wc -l per fonction |
| Type hints | 100% signatures (params + return) | pyright strict |
