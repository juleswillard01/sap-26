# Evaluation Google Integration — Criteres & Metriques

**Date**: 2026-03-21
**Companion de**: `docs/plan-google.md`

---

## 1. Criteres d'Evaluation par Phase

### Phase 1: LettrageService

| Critere | Seuil PASS | Seuil FAIL | Methode de verification |
|---------|-----------|-----------|------------------------|
| **Scoring exact CDC §3.2** | +50 montant, +30 date, +20 libelle | Tout autre scoring | Tests parametrises avec cas A/B/C/D du CDC |
| **Fenetre temporelle** | +/- 5 jours de date_paiement | Fenetre differente | Test avec transactions a J-5, J-3, J+1, J+6 |
| **Seuil LETTRE_AUTO** | Score >= 80 | Score != 80 | Tests boundary: 79 (A_VERIFIER), 80 (LETTRE_AUTO) |
| **Transition PAYE -> RAPPROCHE** | Auto si LETTRE_AUTO | Pas de transition | Test e2e: facture PAYE + match -> RAPPROCHE |
| **Dedup transactions** | Skip si indy_id+date+montant deja present | Doublons inseres | Test avec import CSV identique 2x |
| **Immutabilite** | Rejeter update date_valeur/montant/libelle | Accepter modification | Test update_transaction sur champs proteges |
| **Coverage tests** | >= 80% | < 80% | `pytest --cov=src/services/lettrage_service --cov-fail-under=80` |
| **Happy path** | Cas A (100pts), Cas B (80pts) | Echec | 2 tests parametrises |
| **Edge cases** | Cas C (20pts), Cas D (0pts) | Echec | 2 tests parametrises |
| **Performance** | < 100ms pour 400 txn x 50 factures | > 1s | Benchmark avec Polars |

**Cas de test CDC**:
```
Cas A: 90EUR facture, 90EUR txn, 1j ecart, "URSSAF" → 100 → LETTRE_AUTO
Cas B: 90EUR facture, 90EUR txn, 1j ecart, "Virement" → 80 → LETTRE_AUTO
Cas C: 89EUR facture, 90EUR txn, 6j ecart, "URSSAF" → 20 → A_VERIFIER
Cas D: Aucune transaction dans +/-5j → 0 → PAS_DE_MATCH
```

---

### Phase 2: Batch Updates & FK Validation

| Critere | Seuil PASS | Seuil FAIL | Methode |
|---------|-----------|-----------|---------|
| **Batch update invoices** | 10+ factures en 1 appel API | 1 appel par facture | Mock gspread.batch_update |
| **FK validation client_id** | Rejeter si client_id inexistant | Accepter FK invalide | Test add_invoice avec client inexistant |
| **FK validation facture_id** | Rejeter si facture_id inexistant dans Transactions | Accepter FK invalide | Test update_transaction |
| **State machine enforcement** | Rejeter transition invalide (ex: BROUILLON->PAYE) | Accepter transition illegale | Tests parametrises 12 transitions interdites |
| **Immutabilite apres import** | date_valeur, montant, libelle read-only | Modification acceptee | Test update avec champs proteges |
| **Rate limit** | 60 req/min respecte | Depassement | Test avec 100 writes rapides |
| **Cache invalidation** | Cache invalide apres write | Stale data | Test read-write-read sequence |
| **Coverage** | >= 80% | < 80% | pytest --cov |

---

### Phase 3: Notifications Lifecycle

| Critere | Seuil PASS | Seuil FAIL | Methode |
|---------|-----------|-----------|---------|
| **T+36h detection** | Email envoye a Jules quand facture EN_ATTENTE > 36h | Pas d'email | freezegun test a T+36h01m |
| **T+48h transition** | Statut -> EXPIRE apres 48h | Reste EN_ATTENTE | freezegun test a T+48h01m |
| **Template rendering** | HTML + plaintext, variables interpolees | Template crash | Test render avec contexte complet |
| **Langue FR** | Sujet/corps en francais, dates DD/MM/YYYY | Anglais ou format US | Inspection visuelle + test regex |
| **Lien AIS** | URL directe vers demande AIS dans email | Pas de lien | Test presence URL dans body |
| **SMTP retry** | 3 tentatives sur SMTPServerDisconnected | Crash au 1er echec | Mock side_effect [Error, Error, Success] |
| **Pas de spam** | Max 1 email par facture par cycle | Emails dupliques | Test avec meme facture 2 cycles |
| **Coverage** | >= 80% | < 80% | pytest --cov |

**Templates a valider**:
- [ ] `reminder_t36h.html` — Variables: facture_id, client_name, montant, heures_attente, ais_url
- [ ] `expired_t48h.html` — Variables: facture_id, client_name, montant, date_creation
- [ ] `payment_received.html` — Variables: facture_id, montant, date_paiement, reference_virement
- [ ] `reconciled.html` — Variables: facture_id, montant_facture, montant_transaction, score
- [ ] `error_alert.html` — Variables: facture_id, error_message, timestamp
- [ ] `sync_failed.html` — Variables: sync_type, error_message, timestamp

---

### Phase 4: sap init

| Critere | Seuil PASS | Seuil FAIL | Methode |
|---------|-----------|-----------|---------|
| **8 onglets crees** | Clients, Factures, Transactions, Lettrage, Balances, NOVA, Cotisations, Fiscal IR | < 8 onglets | Mock gspread.add_worksheet x 8 |
| **Headers corrects** | Colonnes CDC pour chaque onglet | Colonnes manquantes/incorrectes | Comparer avec SCHEMA_* dans sheets_schema.py |
| **Formules injectees** | Formules dans onglets calcules (Lettrage, Balances, etc.) | Pas de formules | Verifier contenu cells formule |
| **Data validation** | Dropdowns pour statuts (11 etats facture, 4 statuts lettrage) | Pas de validation | Mock add_data_validation |
| **Idempotent** | Re-run ne casse pas les donnees existantes | Ecrase donnees | Test init sur spreadsheet deja peuple |
| **Formatage conditionnel** | A_VERIFIER orange, PAS_DE_MATCH rouge | Pas de couleur | Mock add_conditional_format |
| **Coverage** | >= 80% | < 80% | pytest --cov |

---

### Phase 5: DriveAdapter (Phase 2+)

| Critere | Seuil PASS | Seuil FAIL | Methode |
|---------|-----------|-----------|---------|
| **Upload PDF** | Retourne Drive file_id | Echec silencieux | Mock files().create().execute() |
| **Folder hierarchy** | Year/Month cree si inexistant | Flat dump | Test create_folder_hierarchy |
| **Dedup MD5** | Skip si meme hash deja present | Re-upload | Test avec meme PDF 2x |
| **Metadata** | facture_id, client_id dans appProperties | Pas de metadata | Test get_file_metadata |
| **Memes credentials** | Service account partage avec Sheets | Credentials separees | Config verification |
| **Coverage** | >= 80% | < 80% | pytest --cov |

---

## 2. Quality Gates Globaux

### Gate 25% — Architecture

- [ ] Plan existe et documente (`docs/plan-google.md`)
- [ ] Schemas CDC references pour chaque phase
- [ ] Interfaces definies (signatures LettrageService, DriveAdapter)
- [ ] Decision Lettrage: Python calcule, Sheets affiche
- [ ] Decision Drive: differe Phase 2+
- [ ] Decision Auth: hybride SA + app password

### Gate 50% — Integration

- [ ] LettrageService implemente et teste
- [ ] Batch updates fonctionnels
- [ ] FK validation active
- [ ] `ruff check src/ tests/` passe
- [ ] `pyright src/` passe (strict)
- [ ] Coverage >= 80%

### Gate 75% — Qualite

- [ ] Templates email rendus correctement (FR)
- [ ] Notifications lifecycle wired (T+36h, T+48h, PAYE, RAPPROCHE)
- [ ] `sap init` cree 8 onglets complets
- [ ] Edge cases testes (boundary values, empty inputs, max limits)
- [ ] Pas de `print()` dans src/
- [ ] Pas de secrets hardcodes
- [ ] Performance: < 100ms pour scoring 400 transactions

### Gate 100% — Livraison

- [ ] `sap reconcile` e2e: import Indy -> lettrage -> notification
- [ ] `sap sync` e2e: scrape AIS -> update Sheets -> detect overdue -> email
- [ ] `sap init` e2e: creation spreadsheet complet
- [ ] `sap status` affiche resume correct
- [ ] Docker build reussit
- [ ] Documentation a jour (docstrings publiques)

---

## 3. Metriques de Performance

| Metrique | Cible | Mesure | Outil |
|----------|-------|--------|-------|
| Temps scoring 400 txn | < 100ms | `timeit` | pytest-benchmark |
| Appels API Sheets/sync | <= 5 | Compteur dans logs | Structured logging |
| Cache hit rate | > 80% | `get_cache_stats()` | SheetsAdapter |
| Temps total `sap sync` | < 30s | CLI timer | `time python -m src.cli sync` |
| Temps total `sap reconcile` | < 15s | CLI timer | `time python -m src.cli reconcile` |
| Emails envoyes/sync | 0-5 | Log count | EmailNotifier logs |

---

## 4. Metriques de Qualite Code

| Metrique | Cible | Outil |
|----------|-------|-------|
| Coverage total | >= 80% | `pytest --cov=src --cov-fail-under=80` |
| Coverage LettrageService | >= 90% | `pytest --cov=src/services/lettrage_service` |
| Ruff violations | 0 | `ruff check src/ tests/` |
| Pyright errors | 0 | `pyright --strict src/` |
| Lignes/fichier | < 400 | `wc -l` |
| Lignes/fonction | < 50 | Review manuelle |
| Indent levels | < 3 | Ruff rules |
| print() dans src/ | 0 | `grep -r "print(" src/` |

---

## 5. Matrice de Test par Composant

### SheetsAdapter (existant, a completer)

| Scenario | Type | Status | Priorite |
|----------|------|--------|----------|
| get_all_clients() retourne DataFrame | Unit | FAIT | — |
| get_all_invoices() retourne DataFrame | Unit | FAIT | — |
| get_all_transactions() retourne DataFrame | Unit | FAIT | — |
| add_client() append en batch | Unit | FAIT | — |
| add_invoice() append en batch | Unit | FAIT | — |
| add_transactions() dedup par indy_id | Unit | FAIT | — |
| update_invoice() update row specifique | Unit | FAIT | — |
| **update_invoices_batch()** | Unit | **A FAIRE** | HAUTE |
| **update_transactions_batch()** | Unit | **A FAIRE** | HAUTE |
| **FK validation client_id** | Unit | **A FAIRE** | HAUTE |
| **State machine validation** | Unit | **A FAIRE** | HAUTE |
| **Immutabilite champs transaction** | Unit | **A FAIRE** | HAUTE |
| Cache TTL 30s expire | Unit | FAIT | — |
| Rate limit 60 req/min | Unit | FAIT | — |
| Circuit breaker open/close | Unit | FAIT | — |

### LettrageService (nouveau)

| Scenario | Type | Status | Priorite |
|----------|------|--------|----------|
| Cas A: montant exact + date 1j + URSSAF = 100 | Unit | A FAIRE | CRITIQUE |
| Cas B: montant exact + date 1j + pas URSSAF = 80 | Unit | A FAIRE | CRITIQUE |
| Cas C: montant diff + date 6j + URSSAF = 20 | Unit | A FAIRE | CRITIQUE |
| Cas D: aucune transaction = PAS_DE_MATCH | Unit | A FAIRE | CRITIQUE |
| Boundary: score 79 = A_VERIFIER | Unit | A FAIRE | HAUTE |
| Boundary: score 80 = LETTRE_AUTO | Unit | A FAIRE | HAUTE |
| Multiple matches: meilleur score gagne | Unit | A FAIRE | HAUTE |
| Transaction deja lettree: skip | Unit | A FAIRE | HAUTE |
| Facture pas PAYE: skip | Unit | A FAIRE | HAUTE |
| Transition PAYE -> RAPPROCHE auto | Unit | A FAIRE | HAUTE |
| Performance: 400 txn < 100ms | Perf | A FAIRE | MOYENNE |

### NotificationService (existant, a completer)

| Scenario | Type | Status | Priorite |
|----------|------|--------|----------|
| Detect overdue > 36h | Unit | FAIT | — |
| Detect overdue = 35h (pas d'alerte) | Unit | FAIT | — |
| Multiple overdue | Unit | FAIT | — |
| **T+48h -> transition EXPIRE** | Unit | **A FAIRE** | HAUTE |
| **Template rendering FR** | Unit | **A FAIRE** | HAUTE |
| **Email envoye via EmailNotifier** | Integration | **A FAIRE** | HAUTE |
| **Pas de spam (1 email/facture/cycle)** | Unit | **A FAIRE** | MOYENNE |
| **Lien AIS dans email** | Unit | **A FAIRE** | MOYENNE |

### GmailReader (existant, complet)

| Scenario | Type | Status | Priorite |
|----------|------|--------|----------|
| Connect IMAP | Unit | FAIT | — |
| Extract 6-digit code | Unit | FAIT | — |
| Timeout 60s | Unit | FAIT | — |
| Sender filter "indy" | Unit | FAIT | — |
| Multipart MIME parsing | Unit | FAIT | — |
| Invalid credentials | Unit | FAIT | — |

### DriveAdapter (nouveau, Phase 2+)

| Scenario | Type | Status | Priorite |
|----------|------|--------|----------|
| Upload PDF | Unit | A FAIRE | BASSE |
| Create folder hierarchy | Unit | A FAIRE | BASSE |
| Dedup MD5 | Unit | A FAIRE | BASSE |
| File metadata | Unit | A FAIRE | BASSE |
| Permission denied 403 | Unit | A FAIRE | BASSE |
| Quota exceeded 429 | Unit | A FAIRE | BASSE |

---

## 6. Criteres de Rejet

Un delivrable est **REJETE** si:

1. Coverage < 80% sur le module concerne
2. Test CDC scoring ne correspond pas aux cas A/B/C/D
3. `ruff check` ou `pyright` echouent
4. `print()` present dans `src/`
5. Secret hardcode dans le code
6. Transition etat invalide acceptee
7. FK invalide acceptee sur write
8. Champ immutable modifie sans erreur
9. Email envoye sans template (f-string brut)
10. Formule Sheets diverge du calcul Python (incoherence)

---

## 7. Definition of Done

Une phase est **DONE** quand:

- [ ] Tous les tests de la matrice passent
- [ ] Coverage >= 80% sur les fichiers touches
- [ ] `ruff check --fix src/ tests/` passe
- [ ] `pyright --strict src/` passe (0 errors)
- [ ] Pas de `print()` dans `src/`
- [ ] Docstrings sur fonctions publiques
- [ ] Commit atomique: `feat(scope): description [CDC §X.Y]`
- [ ] Quality gate correspondant passe (25/50/75/100%)

---

## Gmail 2FA Auto-Inject — Critères Spécifiques

### Scénarios de test (15)

| # | Test | Composant | Type |
|---|---|---|---|
| 1 | IMAP connexion réussie avec app password | GmailReader | Happy |
| 2 | Select label "Indy-2FA" fonctionne | GmailReader | Happy |
| 3 | Extraction code 6 chiffres depuis plaintext | GmailReader | Happy |
| 4 | Extraction code depuis email HTML | GmailReader | Happy |
| 5 | Polling 5s interval, code arrive après 10s | GmailReader | Timing |
| 6 | Timeout 60s retourne None | GmailReader | Error |
| 7 | Filtre sender "indy" uniquement | GmailReader | Filter |
| 8 | Label introuvable → fallback INBOX | GmailReader | Fallback |
| 9 | Credentials invalides → erreur claire | GmailReader | Error |
| 10 | Détection page 2FA après submit | nodriver | Happy |
| 11 | Injection code dans input 2FA | nodriver | Happy |
| 12 | Click bouton vérifier | nodriver | Happy |
| 13 | Dashboard atteint après 2FA | nodriver | Happy |
| 14 | Flow complet login → 2FA → dashboard | Integration | E2E |
| 15 | Pas de credentials dans les logs | Sécurité | Security |

### Performance

| Métrique | Target |
|---|---|
| IMAP connexion | < 3s |
| Polling email (typique) | < 15s |
| Extraction code | < 1s |
| Injection 2FA + submit | < 5s |
| Flow total auto-login | < 90s |
| Réutilisation session headless | < 5s |

### Coverage

- gmail_reader.py : >= 85%
- indy_auto_login.py : >= 80%
