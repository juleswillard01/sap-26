# Composants Système — SAP-Facture

**Source de vérité** : SCHEMAS.html (Schéma 4 — Architecture Système)

---

## 1. Inventaire des Composants

### Couche Présentation
| Composant | Technologie | Responsabilité |
|-----------|------------|-----------------|
| **FastAPI SSR** | FastAPI + Jinja2 + Tailwind | Interface web server-side rendering, pages HTML dynamiques |
| **Dashboard iframes** | Sheets embeds (pubhtml) | Affichage des onglets Google Sheets en lecture (Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal) |
| **Click CLI** | Python Click | Interface ligne de commande : `sap submit`, `sap sync`, `sap export` |

### Couche Métier
| Composant | Responsabilité | Déclencheur |
|-----------|-----------------|------------|
| **InvoiceService** | Création, validation et suivi des factures | Web (POST /invoices) ou CLI (sap submit) |
| **ClientService** | Inscription de nouveaux clients auprès d'URSSAF, gestion identités | Web (POST /clients) ou premier chargement facture client |
| **PaymentTracker** | Polling automatique tous les 4h du statut URSSAF, gestion T+36h reminder | Cron scheduler (toutes les 4h) |
| **BankReconciliation** | Lettrage automatique factures ↔ transactions Swan, scoring confiance | Web (POST /reconcile) ou CLI (sap reconcile) |
| **NotificationService** | Envoi emails reminder aux clients T+36h, coordonneur alertes | Appelé par PaymentTracker |
| **NovaReporting** | Calcul metrics trimestrielles (heures, participants, CA) pour NOVA | Utilisé par iframes Sheets |

### Couche Data Access
| Composant | Technologie | Responsabilité |
|-----------|------------|-----------------|
| **SheetsAdapter** | gspread + Google Sheets API v4 | Abstraction lecture/écriture dans Google Sheets (8 onglets) |

### Couche Intégrations (Adapters)
| Composant | API | Responsabilité |
|-----------|-----|-----------------|
| **URSSAFClient** | API URSSAF (OAuth2 + REST) | Authentification OAuth2, inscription clients, soumission demandes paiement, polling statuts |
| **SwanClient** | API Swan (GraphQL) | Récupération liste transactions bancaires pour rapprochement |
| **PDFGenerator** | WeasyPrint + Google Drive API | Génération PDF factures avec logo, stockage sur Google Drive |
| **EmailNotifier** | SMTP | Envoi emails (reminders, notifications) |

---

## 2. Responsabilités Détaillées

### InvoiceService
**Qui l'appelle** : FastAPI Web, Click CLI

**Responsabilités** :
- Créer une facture brouillon (validation champs client, heures, tarif)
- Générer le PDF via PDFGenerator
- Soumettre la facture à URSSAF via URSSAFClient (créer demande de paiement)
- Écrire/mettre à jour la facture dans onglet Factures via SheetsAdapter
- Valider le payload avant envoi URSSAF

**Flux typique** :
1. Jules remplit form : client, heures, tarif, dates
2. Validation locale (montant positif, client inscrit, champs requis)
3. Génération PDF (logo + détails)
4. Appel URSSAF POST `/demandes-paiement` → obtient `id_demande` et `statut=CREE`
5. Écriture dans Sheets onglet Factures avec statut SOUMIS

---

### ClientService
**Qui l'appelle** : InvoiceService, FastAPI Web

**Responsabilités** :
- Inscrire un nouveau client auprès d'URSSAF (si pas encore inscrit)
- Récupérer l'`id_technique` retourné par URSSAF
- Stocker les données client dans Sheets onglet Clients
- Valider existence client dans BDD fiscale URSSAF

**Flux typique** :
1. Jules ajoute client, ou crée facture premier client
2. Check : `client.urssaf_id` existe dans Sheets ?
3. Si non → Appel URSSAF POST `/particuliers` {nom, email, adresse}
4. URSSAF retourne `id_technique` (ou erreur si client pas connu de l'impôt)
5. Écriture dans Sheets onglet Clients

---

### PaymentTracker
**Qui l'appelle** : Cron scheduler (toutes les 4h)

**Responsabilités** :
- Lire les factures avec statut SOUMIS ou CREE ou EN_ATTENTE depuis Sheets
- Pour chaque facture, appeler URSSAF GET `/demandes-paiement/{id}` pour connaître statut
- Mettre à jour statut dans Sheets (VALIDE, PAYE, REJETE, EXPIRE)
- Déterminer si T+36h écoulées sans validation → trigger NotificationService
- Émettre reminders si client n'a pas validé

**Flux typique** :
```
Cron (4h) → Lire Sheets Factures (SOUMIS, CREE, EN_ATTENTE)
           → Pour chaque facture :
             - GET URSSAF /demandes-paiement/{id}
             - Mettre à jour statut dans Sheets
             - Si T+36h et statut EN_ATTENTE → NotificationService.send_reminder()
           → Si statut PAYE → trigger BankReconciliation
```

---

### BankReconciliation
**Qui l'appelle** : FastAPI Web (sap reconcile), CLI, ou manuel Jules

**Responsabilités** :
- Récupérer transactions Swan via SwanClient (GET /transactions)
- Importer dans Sheets onglet Transactions
- Pour chaque facture PAYEE : chercher transaction correspondante
  - Montant exact match 100% facture ?
  - Date dans +/- 5j du paiement URSSAF ?
  - Libelle contient "URSSAF" ?
- Scoring confiance (montant=+50, date<3j=+30, libelle=+20)
- Écrire résultat dans onglet Lettrage (AUTO / A_VERIFIER / PAS_DE_MATCH)
- Mettre à jour onglet Balances (soldes, non-lettrées)

**Flux typique** :
```
Facture statut PAYE (dans Sheets) → Chercher dans Transactions Swan
  → Match ? Montant + date + libelle
  → Score >= 80 → LETTRE AUTO
  → Score < 80 → A_VERIFIER (Jules valide)
  → Pas match → PAS_DE_MATCH (attendre autre virement)
→ Mettre à jour Lettrage, Balances
```

---

### NotificationService
**Qui l'appelle** : PaymentTracker

**Responsabilités** :
- Envoyer emails reminder aux clients à T+36h sans validation
- Envoyer notifications d'erreur URSSAF si besoin
- Coordonne avec EmailNotifier pour SMTP

**Flux typique** :
```
PaymentTracker détecte facture EN_ATTENTE depuis 36h
→ NotificationService.send_reminder(client.email, facture)
→ EmailNotifier envoie email SMTP
→ Log dans Sheets (optionnel)
```

---

### NovaReporting
**Qui l'appelle** : Onglets Sheets (formules), FastAPI iframes

**Responsabilités** :
- Calculer metrics trimestrielles pour déclaration NOVA
- Lire données brutes : Clients, Factures
- Calculer : nb intervenants (1), heures effectuées, nb particuliers, CA trimestre
- Remplir onglet Metrics NOVA (lecture depuis Sheets)

**Remarque** : Ce composant expose des données calculées dans Sheets, pas de logique serveur lourd

---

### SheetsAdapter
**Qui l'appelle** : Tous les services métier

**Responsabilités** :
- Abstraction pour lire/écrire dans Google Sheets API v4 via gspread
- Gérer authentification (credentials Google)
- CRUD sur 8 onglets : Clients, Factures, Transactions, Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR
- Gestion erreurs API (retry, timeouts)

**Opérations principales** :
```
read_clients() → liste clients du sheet Clients
write_invoice(...) → ajouter/mettre à jour ligne onglet Factures
read_invoices_by_status(status) → filtrer factures par statut
read_transactions(start_date, end_date) → transactions Swan dans plage
write_reconciliation(...) → écrire lettrage dans onglet Lettrage
update_balance(...) → mettre à jour onglet Balances
```

---

### URSSAFClient
**Qui l'appelle** : InvoiceService, ClientService, PaymentTracker

**Responsabilités** :
- Authentification OAuth2 (POST /oauth/token, refresh token)
- POST /particuliers → inscrire client
- POST /demandes-paiement → créer demande paiement
- GET /demandes-paiement/{id} → récupérer statut
- Gestion erreurs API, retry, logs

**Paramètres sensibles** : `URSSAF_CLIENT_ID`, `URSSAF_CLIENT_SECRET` (stockés dans `.env`)

---

### SwanClient
**Qui l'appelle** : BankReconciliation

**Responsabilités** :
- Récupérer liste transactions bancaires via API Swan (GraphQL ou REST)
- Parser réponse, filtrer par date/montant
- Retourner structure standardisée (date, montant, libelle, type)

**Paramètres sensibles** : `SWAN_API_KEY` (dans `.env`)

---

### PDFGenerator
**Qui l'appelle** : InvoiceService

**Responsabilités** :
- Générer PDF facture à partir template HTML + données
- Inclure logo Jules
- Appeler Google Drive API pour stocker PDF
- Retourner lien publik Google Drive (optionnel)

**Technologie** : WeasyPrint (conversion HTML → PDF)

---

### EmailNotifier
**Qui l'appelle** : NotificationService

**Responsabilités** :
- Envoyer emails via serveur SMTP
- Templates emails (reminder T+36h, confirmation, erreurs)
- Logging envois

**Paramètres sensibles** : `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (dans `.env`)

---

## 3. Dépendances entre Composants

```
┌─ FastAPI Web / Click CLI
│
├──> InvoiceService
│    ├──> SheetsAdapter (write Factures)
│    ├──> URSSAFClient (POST /demandes-paiement)
│    └──> PDFGenerator (generate + upload Google Drive)
│
├──> ClientService
│    ├──> SheetsAdapter (read/write Clients)
│    └──> URSSAFClient (POST /particuliers)
│
├──> PaymentTracker (cron 4h)
│    ├──> SheetsAdapter (read Factures, write Factures)
│    ├──> URSSAFClient (GET /demandes-paiement/{id})
│    └──> NotificationService (send_reminder)
│         └──> EmailNotifier (SMTP)
│
├──> BankReconciliation
│    ├──> SwanClient (GET /transactions)
│    └──> SheetsAdapter (write Lettrage, Balances)
│
└──> NovaReporting
     └──> SheetsAdapter (read Clients, Factures)
```

**Graph complet** :

```
┌────────────────────────────────────────────────────────────────┐
│ POINTS D'ENTREE (Jules, Google Sheets, Cron)                   │
│ - Navigateur Web (FastAPI SSR)                                 │
│ - Terminal CLI (Click)                                         │
│ - Google Sheets edit direct (SheetsAdapter)                    │
│ - Cron scheduler (PaymentTracker 4h, reminders)               │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│ COUCHE METIER                                                  │
│ - InvoiceService → SheetsAdapter, URSSAFClient, PDFGenerator  │
│ - ClientService → SheetsAdapter, URSSAFClient                 │
│ - PaymentTracker → SheetsAdapter, URSSAFClient, Notif         │
│ - BankReconciliation → SheetsAdapter, SwanClient              │
│ - NotificationService → EmailNotifier                         │
│ - NovaReporting → SheetsAdapter                               │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│ COUCHE DATA ACCESS & INTEGRATIONS                             │
│ - SheetsAdapter (gspread) ↔ Google Sheets API v4              │
│ - URSSAFClient ↔ API URSSAF (OAuth2 + REST)                   │
│ - SwanClient ↔ API Swan (GraphQL)                             │
│ - PDFGenerator ↔ Google Drive API                             │
│ - EmailNotifier ↔ SMTP                                        │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│ BACKEND DATA : Google Sheets (8 onglets)                       │
│ - Clients, Factures, Transactions (données brutes)            │
│ - Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal (calc)│
└────────────────────────────────────────────────────────────────┘
```

---

## 4. APIs Externes Utilisées

### API URSSAF
**Endpoint** : `portailapi.urssaf.fr`

**Authentification** : OAuth2 (client_id + client_secret dans `.env`)

**Appels** :
| Opération | Méthode | Endpoint | Appelant | Fréquence |
|-----------|---------|----------|----------|-----------|
| Obtenir token | POST | /oauth/token | URSSAFClient | À l'initialisation + refresh |
| Inscrire client | POST | /particuliers | ClientService | 1x par nouveau client |
| Créer demande paiement | POST | /demandes-paiement | InvoiceService | 1x par facture soumise |
| Récupérer statut | GET | /demandes-paiement/{id} | PaymentTracker | Cron 4h |

---

### API Swan
**Endpoint** : `docs.swan.io` (API GraphQL ou REST)

**Authentification** : Bearer token API_KEY dans `.env`

**Appel** :
| Opération | Méthode | But | Appelant |
|-----------|---------|-----|----------|
| Récupérer transactions | GET /transactions | Lettrage factures ↔ virements | BankReconciliation |

---

### Google Sheets API v4
**Endpoint** : `sheets.googleapis.com`

**Authentification** : Service account JSON (credentials dans `.env` ou variables)

**Utilisation** :
- Lecture/écriture toutes les données (8 onglets)
- Appelant : SheetsAdapter (utilisé par tous les services)

---

### Google Drive API
**Endpoint** : `drive.googleapis.com`

**Authentification** : Service account JSON

**Utilisation** :
- Upload PDFs factures
- Appelant : PDFGenerator

---

### Serveur SMTP
**Paramètres** : `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`

**Authentification** : SMTP credentials dans `.env`

**Utilisation** :
- Envoi emails reminders T+36h
- Appelant : EmailNotifier

---

## 5. Points d'Entrée Utilisateur

### Navigateur Web (FastAPI SSR)
**URL** : `http://localhost:8000` (dev) ou domaine production

**Pages** :
- `/` → Dashboard factures (liste + filtres)
- `/invoices/create` → Formulaire créer facture
- `/clients` → Gestion clients
- `/reconcile` → Interface rappro bancaire
- `/metrics` → Dashboard iframes (Sheets embeds)

**Technologie** : FastAPI + Jinja2 templates + Tailwind CSS

---

### Terminal CLI (Click)
**Commandes** :
```bash
sap submit [options]      # Créer + soumettre facture URSSAF
sap sync                   # Synchroniser statuts URSSAF (polling)
sap reconcile             # Lancer lettrage bancaire
sap export --format csv   # Exporter factures CSV
```

**Technologie** : Python Click framework

---

### Google Sheets Edit Direct
**Accès direct** : Jules peut éditer onglets Clients, Factures, Transactions directement dans Sheets

**Onglets éditables** :
- Clients : ajouter/corriger données clients (si client pas encore soumis URSSAF)
- Factures : corriger détails si facture pas encore soumise
- Transactions : marquer matching ou corriger libellé

**Remarque** : SheetsAdapter doit gérer les edits manuels (pas de conflit avec API)

---

### Cron Scheduler
**Tâches planifiées** :
- `PaymentTracker.poll()` → Toutes les 4h
- `NotificationService.send_reminders()` → À T+36h pour chaque facture EN_ATTENTE

**Technologie** : APScheduler ou systemd timer

---

## 6. Flux de Données entre Couches

### Flux 1 : Création Facture (Web ou CLI)

```
Jules (Web/CLI)
    ↓
FastAPI POST /invoices | CLI sap submit
    ↓
InvoiceService.create_invoice()
    ├──> SheetsAdapter.read_client(client_id) → données client
    ├──> Valider (heures, tarif, dates)
    ├──> PDFGenerator.generate_pdf(facture) → PDF bytes
    │   └──> PDFGenerator.upload_drive() → Google Drive
    ├──> URSSAFClient.create_payment_request(facture) → {id_demande, statut=CREE}
    └──> SheetsAdapter.write_invoice(facture, statut=SOUMIS)
         └──> Google Sheets onglet Factures
    ↓
✓ Facture créée, statut SOUMIS, URSSAF notifié
```

---

### Flux 2 : Polling Statut URSSAF (Cron 4h)

```
Cron scheduler
    ↓
PaymentTracker.poll_all()
    ├──> SheetsAdapter.read_invoices(status=[SOUMIS, CREE, EN_ATTENTE])
    └──> Pour chaque facture :
         ├──> URSSAFClient.get_payment_request_status(id_demande)
         │   → retourne {statut: VALIDE | PAYE | REJETE | EXPIRE}
         ├──> SheetsAdapter.update_invoice(facture, new_status)
         │   └──> Google Sheets updated
         ├──> If statut == PAYE → trigger BankReconciliation
         └──> If time_elapsed >= 36h and status == EN_ATTENTE
              └──> NotificationService.send_reminder(client)
                   └──> EmailNotifier.send_email(SMTP)
    ↓
✓ Statuts à jour, reminders envoyés si besoin
```

---

### Flux 3 : Rappro Bancaire (Web/CLI)

```
Jules (Web /reconcile ou CLI sap reconcile)
    ↓
FastAPI POST /reconcile | CLI sap reconcile
    ↓
BankReconciliation.reconcile()
    ├──> SwanClient.get_transactions(date_range) → liste transactions
    ├──> SheetsAdapter.write_transactions(transactions)
    │   └──> Google Sheets onglet Transactions
    └──> Pour chaque facture PAYEE :
         ├──> Chercher transaction match (montant, date, libelle)
         ├──> Calcul score (montant=+50, date=+30, libelle=+20)
         ├──> If score >= 80 → SheetsAdapter.write_reconciliation(AUTO)
         ├──> Else if score >= 50 → SheetsAdapter.write_reconciliation(A_VERIFIER)
         └──> Else → SheetsAdapter.write_reconciliation(PAS_DE_MATCH)
    ├──> SheetsAdapter.update_balances()
    │   └──> Google Sheets onglet Balances (recalculé formules)
    ↓
✓ Lettrage effectué, balances mises à jour
```

---

### Flux 4 : Inscription Client (Automatique si besoin)

```
InvoiceService.create_invoice() ou Jules POST /clients
    ↓
ClientService.ensure_client_exists(client_id)
    ├──> SheetsAdapter.read_client(client_id)
    └──> If urssaf_id == NULL :
         ├──> URSSAFClient.register_client({nom, email, adresse})
         │   ↓
         │   URSSAF API (OAuth2 + REST)
         │   ↓
         │   → {id_technique} ou Erreur
         └──> If success :
              └──> SheetsAdapter.write_client(id_technique, statut=INSCRIT)
    ↓
✓ Client inscrit URSSAF, prêt pour factures
```

---

### Flux 5 : Rapport NOVA (Trimestriel)

```
NovaReporting.calculate_metrics(trimestre)
    ├──> SheetsAdapter.read_clients()
    ├──> SheetsAdapter.read_invoices(date_range=trimestre, statut=PAYE)
    └──> Calcul : {nb_intervenants=1, heures, nb_particuliers, ca}
         └──> SheetsAdapter.write_metrics_nova(trimestre, metrics)
              └──> Google Sheets onglet Metrics NOVA (formules)
    ↓
Jules voit onglet Metrics NOVA via Dashboard iframe (pubhtml)
```

---

## 7. Diagramme Couches (Résumé)

```
┌───────────────────────────────────────────────────────────────┐
│ PRESENTATION LAYER                                            │
│ ┌────────────────┐  ┌──────────────┐  ┌─────────────┐       │
│ │ FastAPI SSR    │  │ Dashboard    │  │ Click CLI   │       │
│ │ (Jinja2 +      │  │ (iframes)    │  │ (commands)  │       │
│ │ Tailwind)      │  │              │  │             │       │
│ └────────────────┘  └──────────────┘  └─────────────┘       │
└───────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────────┐
│ BUSINESS LOGIC LAYER                                          │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ InvoiceServ  │  │ ClientServ   │  │ PaymentTrack │       │
│ └──────────────┘  └──────────────┘  └──────────────┘       │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ BankReconc   │  │ NotifServ    │  │ NovaReporting│       │
│ └──────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────────┐
│ DATA ACCESS LAYER                                             │
│ ┌──────────────────────────────────────────────────┐        │
│ │ SheetsAdapter (gspread + Google Sheets API v4)  │        │
│ └──────────────────────────────────────────────────┘        │
└───────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────────┐
│ INTEGRATION LAYER                                             │
│ ┌────────────┐  ┌──────────┐  ┌──────┐  ┌────────┐         │
│ │URSSAFClient│  │SwanClient│  │PDFGen│  │EmailNotif        │
│ └────────────┘  └──────────┘  └──────┘  └────────┘         │
└───────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────────┐
│ EXTERNAL SERVICES                                             │
│ ┌────────────┐  ┌──────────┐  ┌───────┐  ┌──────┐          │
│ │ API URSSAF │  │ API Swan │  │Google │  │ SMTP │          │
│ │            │  │          │  │Sheets │  │      │          │
│ └────────────┘  └──────────┘  └───────┘  └──────┘          │
│ │ API URSSAF │  │ API Swan │  │Google │  │ SMTP │          │
│ │ OAuth2+REST│  │ GraphQL  │  │Drive  │  │      │          │
│ └────────────┘  └──────────┘  └───────┘  └──────┘          │
└───────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────────┐
│ BACKEND DATA : GOOGLE SHEETS (8 onglets)                     │
│ Data brute : Clients, Factures, Transactions                │
│ Calcul (formules) : Lettrage, Balances, Metrics, Cotisations│
│ Fiscal IR                                                     │
└───────────────────────────────────────────────────────────────┘
```

---

## 8. Stockage Sensibles & Configuration

### Variables d'Environnement (.env, jamais committé)

```
# URSSAF OAuth2
URSSAF_CLIENT_ID=xxx
URSSAF_CLIENT_SECRET=xxx
URSSAF_API_BASE_URL=https://portailapi.urssaf.fr

# Swan API
SWAN_API_KEY=xxx
SWAN_API_BASE_URL=https://api.swan.io

# Google Credentials (JSON base64 ou path)
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
GOOGLE_SHEETS_ID=xxxxx
SHEETS_DRIVE_FOLDER_ID=xxxxx

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xx@gmail.com
SMTP_PASSWORD=xxx

# App Config
APP_DEBUG=false
APP_LOG_LEVEL=INFO
```

### Stockage PDFs
- **Localisation** : Google Drive folder (credentials service account)
- **Accès** : Via PDFGenerator (Google Drive API)
- **Partage** : Liens publics (optionnel, via pubhtml)

### Données Clients
- **Localisation** : Google Sheets onglet Clients
- **Champs sensibles** : Emails, adresses (visibles dans Sheets)
- **Sécurité** : Accès contrôlé via Google OAuth2 (Jules seul)

---

## 9. Points Clés d'Architecture

1. **Google Sheets = Single Source of Truth**
   - Pas de base de données SQL
   - SheetsAdapter centralise tous les appels API Sheets
   - Onglets data brute (Clients, Factures, Transactions)
   - Onglets calcul avec formules (Lettrage, Balances, Metrics NOVA, etc.)

2. **Monolith FastAPI + CLI**
   - Pas de microservices (MVP)
   - Une seule application, deux interfaces (Web + CLI)
   - Partage même logique métier

3. **Polling URSSAF (cron 4h)**
   - PaymentTracker ne reçoit pas webhooks URSSAF
   - Check actif statut à intervalles réguliers
   - Reminders T+36h si client n'a pas validé

4. **Lettrage Semi-Automatique**
   - BankReconciliation propose matches (AUTO / A_VERIFIER / PAS_DE_MATCH)
   - Jules peut valider manuellement dans Sheets
   - Balances recalculées via formules

5. **Intégrations Asynchrones**
   - PDFGenerator utilise Google Drive (upload async)
   - EmailNotifier utilise SMTP (envoie mails)
   - Toutes via adapters (URSSAFClient, SwanClient, etc.)

6. **No SQL Database**
   - Zero schema SQL
   - Zero migrations
   - All data in Google Sheets
   - Trade-off: scalabilité limitée > OK pour MVP

---

## 10. Matrice Dépendances

| Composant | Dépend de | Appelé par |
|-----------|-----------|-----------|
| InvoiceService | SheetsAdapter, URSSAFClient, PDFGenerator | FastAPI, CLI |
| ClientService | SheetsAdapter, URSSAFClient | InvoiceService, FastAPI |
| PaymentTracker | SheetsAdapter, URSSAFClient, NotificationService | Cron |
| BankReconciliation | SheetsAdapter, SwanClient | FastAPI, CLI |
| NotificationService | EmailNotifier | PaymentTracker |
| NovaReporting | SheetsAdapter | FastAPI iframes |
| SheetsAdapter | (Google Sheets API) | TOUS les services |
| URSSAFClient | (API URSSAF) | InvoiceService, ClientService, PaymentTracker |
| SwanClient | (API Swan) | BankReconciliation |
| PDFGenerator | (Google Drive API) | InvoiceService |
| EmailNotifier | (SMTP) | NotificationService |

---

**Document généré depuis SCHEMAS.html (Schéma 4 — Architecture Système)**
**Version** : 1.0
**Date** : Mars 2026
