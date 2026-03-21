# Brainstorming — SAP-Facture

## Idées Explorées

### Pourquoi un orchestrateur et pas un outil de facturation ?
AIS (avance-immediate.fr, 99€/an) fait déjà la facturation URSSAF. Le recréer serait :
- Réinventer la roue (AIS a l'habilitation API, pas Jules)
- 2-4 mois pour obtenir sa propre habilitation URSSAF
- Maintenir un outil de facturation complet (mentions légales, numérotation, etc.)

L'orchestrateur comble les GAPS que AIS ne couvre pas :
- Rapprochement bancaire (AIS ne se connecte pas à la banque)
- Vue unifiée (Jules switch entre 4 outils)
- Alertes proactives (factures oubliées > 36h)
- Reporting NOVA automatisé

### Alternatives étudiées et rejetées

| Alternative | Pourquoi rejetée |
|-------------|-----------------|
| API URSSAF directe | Habilitation 2-4 mois, AIS le fait déjà |
| Bridge API (PSD2) | Jules n'a pas accès, Indy utilise Bridge en interne |
| Remplacement d'AIS | Trop de scope, AIS fait bien son job |
| PDF factures WeasyPrint | AIS génère déjà les PDF |
| Base de données SQL | Google Sheets suffit pour ~200 factures/an |

### Pistes Futures (pas dans le MVP)

#### Attestation Fiscale Intelligente
AIS génère l'attestation, mais SAP-Facture pourrait :
- Vérifier la cohérence (montants, dates, clients)
- Alerter si des données manquent avant le 31 mars
- Pré-remplir le formulaire NOVA avec les données Sheets

#### Dashboard Prédictif
- Prédire le CA du trimestre basé sur les tendances
- Alerter si le seuil micro-entrepreneur approche (77 700€)
- Simuler l'impact fiscal de chaque nouvelle facture

#### Multi-Services SAP
Jules fait des cours particuliers, mais le système pourrait supporter :
- Ménage, jardinage, aide aux personnes âgées
- Chaque service a des codes nature différents
- AIS gère ça, SAP-Facture pourrait catégoriser

#### Automatisation NOVA
- Le portail NOVA (nova.entreprises.gouv.fr) n'a pas d'API
- Playwright pourrait remplir le formulaire NOVA automatiquement
- Risque : changement UI du portail gouvernemental

#### Facturation Électronique 2026-2027
- Obligation de réception e-factures sept 2026
- Obligation d'émission sept 2027
- AIS devra être compatible Factur-X
- SAP-Facture pourrait vérifier la conformité

### Décisions Techniques

#### Polars vs Pandas
Choix : Polars
- Plus rapide pour les petits datasets
- API plus moderne et type-safe
- Patito bridge Pydantic ↔ Polars nativement

#### Playwright vs Selenium
Choix : Playwright
- Auto-wait intégré (moins de flakiness)
- Headless par défaut
- Meilleur support des sessions/cookies
- playwright.sync_api pour la simplicité

#### Google Sheets vs SQLite
Choix : Google Sheets
- Jules peut éditer directement
- Formules natives pour les calculs
- Embeds pubhtml pour le dashboard
- ~200 factures/an = pas besoin de BDD

#### Click vs Typer pour le CLI
Choix : Click
- Plus mature et documenté
- Rich pour l'affichage
- Pas besoin des features avancées de Typer

### Questions Ouvertes
1. Comment gérer la 2FA d'AIS si elle est activée ? (TOTP ? SMS ?)
2. Que faire si Indy change son interface d'export ?
3. Faut-il un mode "dry run" pour sap sync/reconcile ?
4. Comment versionner les formules Google Sheets ?
5. Faut-il un webhook/notification Discord en plus de l'email ?

---

## Opportunités d'Optimisation

### Optimisation Lettrage
- Émettre des frais de port/frais si montant ≠ facture
- Détecter les paiements partiels (flaguer pour vérification manuelle)
- Historique des lettres erronées pour améliorer le scoring

### Résilience et Disaster Recovery
- Backup automatique des Sheets vers CSV local (hourly)
- Snapshot versionnés dans git (Sheets → JSONL → git)
- Rôle lecture seule Google pour le backup (évite les deadlocks)

### Intégration Email
- Parser les emails reçus d'URSSAF/AIS (webhooks IMAP)
- Extraire statuts directement du corps des emails
- Bypass Playwright si l'email est plus rapide

### Tests E2E
- Sandbox AIS / Indy de test (si dispo)
- Docker Compose avec data fixtures
- Simulation timers et transitions d'état

### Performance
- Cache Google Sheets : 30s TTL → 5 min si dataset > 500 lignes
- Batch scraping AIS : paginer par mois au lieu d'une grosse requête
- Index Sheets par facture_id pour lookups O(1)

---

## Décisions Repoussées au V2

- **Devis** : AIS gère déjà, V2 si besoin de tracking
- **Acomptes** : Complexité factures + acomptes, demander à Jules d'abord
- **Retards de paiement** : Intérêts de retard URSSAF, V2 si pertinent
- **Facturation Récurrente** : Templatiser dans Sheets, scripter plus tard
- **Webhooks AIS/Indy** : Pas d'API, V2 si elles arrivent
- **Mobile App** : Desktop web Google Sheets suffit (responsive design)

---

## Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|-----------|
| AIS change UI scraping | Moyen | Critique | Versionner sélecteurs, logs d'erreur, screenshots |
| Indy CSV format change | Faible | Moyen | Parser robuste + tests fixtures |
| Google Sheets quota atteint | Très faible | Faible | Monitoring quota, throttling |
| 2FA AIS bloque sync | Moyen | Critique | Créer compte sans 2FA ou TOTP secrets |
| Email trop lent/réseau | Faible | Faible | Retry + async, notification Discord webhook |
| Breach données Sheets | Très faible | Critique | Partage drive restreint, audit logs |

---

## Principes de Conception

### Simplicité Avant Complétude
- MVP scoped : sync AIS + Indy + lettrage + rappel 36h
- Pas d'UI, Sheets c'est l'UI
- Pas d'authentification, .env suffit

### Invisible to Jules
- Cron qui tourne en arrière-plan (Docker)
- Notifications seulement si besoin (36h reminder, erreur sync)
- Zéro intervention manuelle pour sync/reconcile

### Source de Vérité Unique
- Sheets est la BDD
- Pas de cache local mutable
- Logs pour l'audit, Sheets pour l'état

### Crash Resilience
- Idempotent sync : 2× sap sync = même résultat
- Partial failures : sync AIS échoue, reconcile Indy marche seul
- Manual recovery : Jules peut corriger Sheets + relancer sync

---

## Glossaire Technique

| Terme | Définition |
|-------|-----------|
| **Lettrage** | Appariement facture ↔ transaction bancaire |
| **Demande** | Facture soumise à URSSAF dans AIS |
| **Scraping** | Extraction de données via Playwright (headless browser) |
| **Sync** | Import statuts AIS → maj Sheets |
| **Reconcile** | Import Indy transactions + lettrage automatique |
| **Score Confiance** | Poids match transaction-facture (0-100) |
| **BROUILLON** | Facture créée dans AIS, pas encore soumise |
| **SOUMIS** | Demande envoyée à URSSAF |
| **EN_ATTENTE** | URSSAF traite la demande |
| **PAYE** | URSSAF a viré le montant |
| **RAPPROCHE** | Transaction identifiée et lettrée |

