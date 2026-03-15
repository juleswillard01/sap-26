# Spécifications UX — SAP-Facture Phase 2

**Version** : 1.0
**Date** : Mars 2026
**Auteur** : Winston (System Architect)
**Contexte** : Basé sur SCHEMAS.html et Phase 1 (user-journey.md, system-components.md)

---

## Table des matières

1. [Inventaire des Écrans](#1-inventaire-des-écrans)
2. [Architecture Navigation (Sitemap)](#2-architecture-navigation-sitemap)
3. [Spécifications par Écran](#3-spécifications-par-écran)
4. [Patterns d'Interaction](#4-patterns-dinteraction)
5. [Composants UI Réutilisables](#5-composants-ui-réutilisables)
6. [Responsive Design & Considérations Mobiles](#6-responsive-design--considérations-mobiles)
7. [Indicateurs Temps Réel vs Calculés](#7-indicateurs-temps-réel-vs-calculés)
8. [Accessibilité & Standards](#8-accessibilité--standards)

---

## 1. Inventaire des Écrans

### Écrans Prioritaires Phase 2

| Écran | URL | Rôle | Criticité | État |
|-------|-----|------|-----------|------|
| Dashboard Factures | `/` | Vue synthétique + actions rapides | Haute | MVP |
| Liste Factures | `/invoices` | Tableau détaillé filtrable | Haute | MVP |
| Création/Édition Facture | `/invoices/create`, `/invoices/{id}/edit` | Formulaire facture | Haute | MVP |
| Détail Facture | `/invoices/{id}` | Affichage complet + actions | Haute | MVP |
| Gestion Clients | `/clients` | CRUD clients + inscription URSSAF | Moyenne | MVP |
| Formulaire Client | `/clients/create`, `/clients/{id}/edit` | Saisie données client | Moyenne | MVP |
| Rapprochement Bancaire | `/reconcile` | Lettrage auto + validation manuelle | Moyenne | Phase 2 |
| Dashboard Métrique (iframes) | `/metrics` | Lettrage, Balances, NOVA, Cotisations, Fiscal | Basse | Phase 2 |
| Détail Réconciliation | `/reconcile/{facture_id}` | Validation 1-to-1 facture ↔ transaction | Basse | Phase 2 |

---

## 2. Architecture Navigation (Sitemap)

```
SAP-Facture
├── / (Dashboard — Landing)
│   ├── Widgets : CA total, factures en attente, transactions entrantes
│   ├── Raccourcis : Créer facture, Sync URSSAF, Lettrage
│   └── iframes Sheets intégrées (optionnel)
│
├── /invoices (Liste Factures)
│   ├── Tableau factures avec filtres (statut, client, date)
│   ├── Tri multi-colonnes
│   ├── Actions : Créer, Éditer, Voir détail, Télécharger PDF
│   └── Export CSV
│
├── /invoices/create (Créer Facture — formulaire)
│   ├── Sélection client (select + search)
│   ├── Auto-création client si nouveau
│   ├── Saisie : heures, tarif, dates, description
│   ├── Aperçu PDF
│   ├── Actions : Brouillon, Soumettre URSSAF
│   └── Validation live
│
├── /invoices/{id} (Détail Facture)
│   ├── Affichage complet facture (PDF preview)
│   ├── Statut + timeline
│   ├── Actions contextuelles (Éditer, Re-soumettre, Annuler, Télécharger)
│   └── Historique statuts
│
├── /invoices/{id}/edit (Éditer Facture)
│   ├── Formulaire pre-rempli
│   ├── Restrictions selon statut
│   ├── Validation
│   └── Actions : Sauvegarder, Annuler
│
├── /clients (Gestion Clients)
│   ├── Liste clients (table ou cards)
│   ├── Statuts URSSAF (INSCRIT, A_INSCRIRE, ERREUR)
│   ├── Tri/filtres
│   ├── Actions : Créer, Éditer, Inscrire (si besoin), Supprimer
│   └── Historique factures par client
│
├── /clients/create | /clients/{id}/edit (Formulaire Client)
│   ├── Champs : nom, email, adresse, tel, CP, ville
│   ├── Validation email live
│   ├── Actions : Créer, Inscrire URSSAF, Annuler
│   └── Feedback URSSAF inscription
│
├── /reconcile (Rappro Bancaire)
│   ├── Vue synthétique : AUTO (X), A_VERIFIER (Y), PAS_DE_MATCH (Z)
│   ├── Tableau factures PAYEE non-lettrees
│   ├── Colonne propositions (transaction match)
│   ├── Scoring confiance visible
│   ├── Actions : Rafraîchir (Swan), Valider manuellement, Ignorer
│   └── Lien à détails
│
├── /reconcile/{facture_id} (Détail Réconciliation)
│   ├── Facture gauche | Transaction droite
│   ├── Score confiance détaillé (montant, date, libelle)
│   ├── Actions : Confirmer match, Rejeter, Chercher autre
│   └── Historique tentatives matching
│
└── /metrics (Dashboard Métrique)
    ├── iframe Sheets : Lettrage (public HTML)
    ├── iframe Sheets : Balances (public HTML)
    ├── iframe Sheets : Metrics NOVA (public HTML)
    ├── iframe Sheets : Cotisations (public HTML)
    ├── iframe Sheets : Fiscal IR (public HTML)
    └── Lien direct Google Sheets (édition)
```

---

## 3. Spécifications par Écran

### 3.1 Dashboard Factures — `/`

#### Responsabilité
Vue synthétique de la santé financière : CA, factures en cours, transactions attendues.

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ SAP-Facture — Dashboard                                     │
│ ┌──────────────────────┐  ┌──────────────────────────────┐ │
│ │ 🟢 CA Total (Mois)   │  │ 🔵 Factures En Attente      │ │
│ │ 950,00 €             │  │ 3 (validation URSSAF < 48h) │ │
│ │ +15% vs mois passé   │  │ Montant : 210,00 €          │ │
│ └──────────────────────┘  └──────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────┐  ┌──────────────────────────────┐ │
│ │ 💳 Virements Swan    │  │ 🚨 Factures Expirées        │ │
│ │ Ce mois : 500,00 €   │  │ 0 à re-soumettre            │ │
│ │ Attendu : 210,00 €   │  │ Voir détail                 │ │
│ └──────────────────────┘  └──────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Actions Rapides                                         │ │
│ │ [+ Créer Facture] [↻ Sync URSSAF] [📋 Lettrage]        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Factures Récentes (dernières 5)                         │ │
│ │ Client       | Montant  | Statut      | Date Création   │ │
│ │─────────────────────────────────────────────────────────│ │
│ │ Alice B      | 30,00 €  | 🟢 PAYE     | 15/03 14:32    │ │
│ │ Bob C        | 45,00 €  | 🔵 EN_ATTENTE | 14/03 10:15  │ │
│ │ Charlie D    | 50,00 €  | 🟠 VALIDE   | 13/03 15:45    │ │
│ │ [Voir plus...]                                          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Onglets Sheets iframes — optionnel Phase 2]            │ │
│ │ ├── Lettrage (pubhtml embed)                            │ │
│ │ ├── Balances (pubhtml embed)                            │ │
│ │ ├── NOVA (pubhtml embed)                                │ │
│ │ └── Lien « Voir tous les onglets »                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Composant | Type | Donnée | Source |
|-----------|------|--------|--------|
| **CA Total (Mois)** | Card KPI | SUM(Factures PAYEE, mois courant) | Sheets Factures |
| **% vs mois passé** | Indicateur trend | (CA_mois - CA_mois_prev) / CA_mois_prev | Sheets Factures |
| **Factures En Attente** | Card KPI | COUNT(Factures EN_ATTENTE) | Sheets Factures |
| **Montant En Attente** | Card KPI | SUM(Factures EN_ATTENTE) | Sheets Factures |
| **Virements Swan** | Card KPI | SUM(Transactions, mois courant) | Sheets Transactions |
| **Montant Attendu** | Card KPI | SUM(Factures PAYE non-lettrees) | Sheets Lettrage |
| **Factures Expirées** | Card Alert | COUNT(Factures EXPIRE) | Sheets Factures |
| **Tableau Récent** | List 5 rows | Factures triées date DESC, limit 5 | Sheets Factures |

#### Actions

- **[+ Créer Facture]** → `/invoices/create`
- **[↻ Sync URSSAF]** → POST `/api/sync` (polling immédiat, feedback en toast)
- **[📋 Lettrage]** → `/reconcile`
- **Clic ligne tableau** → `/invoices/{id}`

#### Données Affichées

- Nom client, montant, statut (couleur), date création
- Badges statut avec icônes (🟢 PAYE, 🔵 EN_ATTENTE, 🟠 VALIDE, 🔴 ERREUR, ⚫ BROUILLON)

#### Comportement Temps Réel

- Cards KPI rafraîchies au chargement (GET `/api/dashboard`)
- Polling optionnel 30s (websocket future, phase 3)
- Toast notification si sync URSSAF détecte changement statut

---

### 3.2 Liste Factures — `/invoices`

#### Responsabilité
Tableau complet factures avec filtres, tri, et actions masse.

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ Factures                                               │     │
│                                                              │
│ [+ Créer Facture]  [CSV Export]  [↻ Rafraîchir]            │
│                                                              │
│ Filtres:                                                     │
│ [Statut ▼ : Tous]  [Client ▼ : --]  [Date ▼ : Ce mois]  │
│ [Montant min: __] [Montant max: __]  [🔍 Recherche]        │
│                                                              │
│ Tri : ID ↑  Client ↓  Montant ↑  Statut  Date ↓            │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ ID | Client  | Montant | Statut      | Date Création    ││
│ │────────────────────────────────────────────────────────── ││
│ │ F1 │ Alice B │ 30,00€  │ 🟢 PAYE     │ 15/03 14:32    ││
│ │ F2 │ Bob C   │ 45,00€  │ 🔵 EN_ATTR  │ 14/03 10:15    ││
│ │ F3 │ Charlie │ 50,00€  │ 🟠 VALIDE   │ 13/03 15:45    ││
│ │ F4 │ Diana E │ 40,00€  │ ⚫ BROUIL   │ 12/03 09:00    ││
│ │ F5 │ Eve F   │ 55,00€  │ 🔴 ERREUR  │ 11/03 16:30    ││
│ │    │ [...]                                              ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Affichage : 1-10 de 47  [< Précédent] [Suivant >]         │
│                                                              │
│ Total affiché : 260,00 €                                    │
│ [Ajouter dans carrée 1..]                                   │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Composant | Type | Détail |
|-----------|------|--------|
| **Bouton Créer** | Primary Button | Bleu, icône `+` |
| **Export CSV** | Secondary Button | Gris, icône téléchargement |
| **Filtres** | Dropdown + Input | Statut, Client, Date, Montant |
| **Barre Recherche** | Text Input | Recherche sur client, ID, description |
| **Tableau** | DataGrid | 7 colonnes, pagination, tri multi |
| **Badges Statut** | Chips/Badges | Couleur par statut (cf. palette) |
| **Pagination** | Controls | Previous/Next + page info |
| **Total** | Summary | Somme factures visibles |

#### Actions par Ligne

- **Clic client** → Filtre par client
- **Clic statut** → Filtre par statut
- **Clic date** → `/invoices/{id}` (détail)
- **Bouton actions (...)** :
  - Voir détail → `/invoices/{id}`
  - Éditer → `/invoices/{id}/edit` (si BROUILLON)
  - Télécharger PDF
  - Re-soumettre (si ERREUR ou EXPIRE)
  - Annuler (si BROUILLON)

#### Données Affichées

| Colonne | Format | Source |
|---------|--------|--------|
| ID | `F{auto-increment}` | Sheets Factures |
| Client | Nom (lien) | Sheets Clients |
| Montant | `{montant},00 €` | Sheets Factures |
| Statut | Badge couleur | Sheets Factures |
| Date Création | `DD/MM HH:MM` | Sheets Factures |
| Actions | Menu ... | UI |

#### Filtres Disponibles

- **Statut** : BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, REJETE, EXPIRE, ANNULE
- **Client** : Dropdown (liste clients)
- **Date** : Ce mois, 3 mois, 6 mois, Année, Personnalisé
- **Montant** : Input min/max

---

### 3.3 Créer/Éditer Facture — `/invoices/create` & `/invoices/{id}/edit`

#### Responsabilité
Formulaire création facture avec validation live et aperçu.

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ Créer une Facture                                           │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Section 1 : CLIENT                                      │ │
│ │ ┌────────────────────────────────────────────────────┐ │ │
│ │ │ Sélectionnez un client *                           │ │ │
│ │ │ [Alice B ▼]                                        │ │ │
│ │ │ Pas de client ? [+ Ajouter rapide]                │ │ │
│ │ └────────────────────────────────────────────────────┘ │ │
│ │                                                         │ │
│ │ Infos client (lecture seule) :                         │ │
│ │ Alice B | alice@example.com | 75 Rue X, 75001 Paris  │ │
│ │ Statut URSSAF : ✓ INSCRITE                            │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Section 2 : DÉTAILS FACTURE                            │ │
│ │ ┌─────────────────────────────────────────────────────┐ │
│ │ │ Type d'unité *                                      │ │
│ │ │ [Heure ▼]                                          │ │
│ │ │ (Options: Heure, Cours, Forfait)                  │ │
│ │ └─────────────────────────────────────────────────────┘ │
│ │                                                         │ │
│ │ ┌─────────────────────────────────────────────────────┐ │
│ │ │ Nature Code *                                       │ │
│ │ │ [BNC — Service Enseignement ▼]                    │ │
│ │ │ (Options: BNC-Service, BNC-Conseil, etc.)         │ │
│ │ └─────────────────────────────────────────────────────┘ │
│ │                                                         │ │
│ │ Quantité *        │ Tarif Unitaire *   │ Montant Total   │
│ │ [1,5 heure]      │ [30,00 €]          │ [45,00 €]       │
│ │ ✓ OK             │ ✓ OK               │ (auto-calc)     │
│ │                                                         │ │
│ │ Date Début du Service *  │ Date Fin *                   │
│ │ [15/03/2026]             │ [15/03/2026]                 │
│ │ ✓ OK                     │ ✓ OK                         │
│ │                                                         │ │
│ │ Description (optionnel)                                 │
│ │ [Cours Maths, Algèbre Linéaire niveau ________________ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Aperçu PDF (optionnel)                                  │ │
│ │ ┌─────────────────────────────────────────────────────┐ │
│ │ │ [Facture_F1_20260315.pdf]                           │ │
│ │ │ Généré : 15/03 14:32 | Taille: 150 KB              │ │
│ │ │ [👁️ Aperçu] [📥 Télécharger]                        │ │
│ │ └─────────────────────────────────────────────────────┘ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Actions                                                 │ │
│ │ [Sauvegarder en Brouillon] [Soumettre à URSSAF] [Ann.] │ │
│ │ ✓ Brouillon sauvegardé (draft ID: F1)                  │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Composant | Type | Validation |
|-----------|------|-----------|
| **Client Select** | Autocomplete Dropdown | Requis, avec search |
| **Type d'unité** | Dropdown (Heure/Cours/Forfait) | Requis |
| **Nature Code** | Dropdown (BNC codes) | Requis, pre-filled BNC-Service |
| **Quantité** | Number Input | > 0, format décimal (1.5) |
| **Tarif Unitaire** | Currency Input | > 0 |
| **Montant Total** | Display (auto-calc) | = Quantité × Tarif |
| **Date Début** | Date Input | Format YYYY-MM-DD |
| **Date Fin** | Date Input | >= Date Début |
| **Description** | Textarea | Optionnel, max 500 chars |
| **PDF Preview** | Card avec badge | Affiche après première sauvegarde |

#### Validation Live

- **Quantité/Tarif** : Non-empty, > 0 → checkmark ✓
- **Montant Total** : Auto-calculé, affichage immédiat
- **Dates** : Date Fin >= Date Début, format valide
- **Client** : Vérifier inscription URSSAF (badge ✓ ou ⚠️ "À inscrire")
- **Erreur URSSAF** : Si client pas inscrit et inscription échoue → message rouge

#### Actions

- **[+ Ajouter rapide]** → Modal mini-form créer client
- **[Sauvegarder en Brouillon]** → POST `/api/invoices` (statut=BROUILLON) → toast succès
- **[Soumettre à URSSAF]** → POST `/api/invoices/{id}/submit` → polling + feedback
- **[Annuler]** → Retour `/invoices` (confirmation si changements)

#### État Édition (si `/invoices/{id}/edit`)

- Champs **pré-remplis** depuis Sheets
- Restrictions selon **statut** :
  - BROUILLON : tous champs éditable
  - SOUMIS/CREE/EN_ATTENTE : champs **lock** (sauf description)
  - Autres statuts : formulaire **disabled**
- Bouton "Re-soumettre" visible si ERREUR ou EXPIRE

---

### 3.4 Détail Facture — `/invoices/{id}`

#### Responsabilité
Affichage complet facture avec PDF, statut, historique, et actions contextuelles.

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ Facture F1 — Alice B                                [← Retour]│
│                                                              │
│ ┌──────────────────────────┐  ┌──────────────────────────┐ │
│ │ Statut                   │  │ Timeline                 │ │
│ │ 🟢 PAYE                  │  │ 15/03 14:32 - BROUILLON │ │
│ │ Mis à jour : 15/03 19:15│  │ 15/03 14:45 - SOUMIS    │ │
│ │                          │  │ 15/03 15:00 - CREE      │ │
│ │                          │  │ 15/03 20:30 - VALIDE    │ │
│ │                          │  │ 16/03 10:15 - PAYE      │ │
│ └──────────────────────────┘  └──────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Infos Facture                                           │ │
│ │ Client : Alice B | Email : alice@ex.com | Tél: 06..    │ │
│ │ Montant Total : 45,00 € | Quantité : 1.5 h             │ │
│ │ Nature : BNC-Service | Période : 15/03-15/03          │ │
│ │ ID Demande URSSAF : URD-2026-001234                    │ │
│ │ Description : Cours Maths, Algèbre                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ PDF Facture                                             │ │
│ │ ┌─────────────────────────────────────────────────────┐ │
│ │ │ [Preview PDF — miniature]                           │ │
│ │ │ [Facture_F1_20260315.pdf — 150 KB]                 │ │
│ │ │ Généré : 15/03 14:32                                │ │
│ │ └─────────────────────────────────────────────────────┘ │
│ │ [👁️ Voir en plein écran] [📥 Télécharger]              │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Rappro Bancaire (si PAYE)                              │ │
│ │ Statut Lettrage : ✓ LETTRE AUTO (16/03 12:00)         │ │
│ │ Score Confiance : 95/100                                │ │
│ │ Transaction Swan : VIRT-FRANCE-12345, 45,00€, 16/03   │ │
│ │ [Voir détail lettrage]                                 │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Actions                                                 │ │
│ │ [✏️ Éditer] [🔄 Sync] [📋 Lettrage] [❌ Annuler]       │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Composant | Contenu | Source |
|-----------|---------|--------|
| **Breadcrumb** | Factures > F1 | UI (navigation) |
| **Badge Statut** | Couleur + texte + date mise à jour | Sheets Factures |
| **Timeline** | Historique statuts avec timestamps | Sheets Factures (calc) |
| **Card Info** | Client, montant, nature, période | Sheets Factures + Clients |
| **Card PDF** | Aperçu miniature + lien DL | Google Drive |
| **Card Lettrage** | Statut, score, transaction Swan | Sheets Lettrage |

#### Actions Contextuelles

Les actions changent selon **statut** :

| Statut | Actions Disponibles |
|--------|-------------------|
| BROUILLON | [✏️ Éditer] [Soumettre URSSAF] [❌ Annuler] |
| SOUMIS | [🔄 Sync] [❌ Annuler] |
| CREE/EN_ATTENTE | [🔄 Sync] [❌ Annuler] |
| VALIDE | [🔄 Sync] |
| PAYE | [🔄 Sync] [📋 Lettrage] |
| RAPPROCHE | [Voir détail lettrage] |
| REJETE | [✏️ Éditer] [🔄 Re-soumettre] |
| EXPIRE | [✏️ Éditer] [🔄 Re-soumettre] |
| ANNULE | (lecture seule) |

---

### 3.5 Gestion Clients — `/clients`

#### Responsabilité
Liste clients avec gestion URSSAF et historique factures.

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ Clients                                                      │
│                                                              │
│ [+ Ajouter Client] [CSV Export]  [🔍 Recherche ___________]│
│                                                              │
│ Filtres:                                                     │
│ [Statut URSSAF ▼ : Tous] [Trier ▼ : Nom A-Z]              │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Nom        │ Email                │ Statut URSSAF  │ Act ││
│ │────────────────────────────────────────────────────────── ││
│ │ Alice B    │ alice@example.com    │ ✓ INSCRITE     │ ...││
│ │ Bob C      │ bob@example.com      │ ✓ INSCRITE     │ ...││
│ │ Charlie D  │ charlie@example.com  │ ⚠️ A_INSCRIRE  │ ...││
│ │ Diana E    │ diana@example.com    │ ✓ INSCRITE     │ ...││
│ │ Eve F      │ eve@example.com      │ 🔴 ERREUR      │ ...││
│ │ [...]                                                   ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Menu actions (...) :                                         │
│ ├── [👁️ Voir détail]                                        │
│ ├── [✏️ Éditer]                                             │
│ ├── [📋 Historique factures]                               │
│ ├── [🚀 Inscrire URSSAF] (si A_INSCRIRE)                   │
│ └── [🗑️ Supprimer]                                         │
│                                                              │
│ Affichage : 1-10 de 12  [< Précédent] [Suivant >]         │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Composant | Type | Détail |
|-----------|------|--------|
| **Tableau** | DataGrid | 4 colonnes + actions |
| **Badges Statut** | Chips | ✓ INSCRITE (vert), ⚠️ A_INSCRIRE (orange), 🔴 ERREUR (rouge) |
| **Menu Actions** | Dropdown | Voir, Éditer, Inscrire, Supprimer |
| **Filtres** | Dropdown | Statut URSSAF |
| **Tri** | Dropdown | Nom, Date ajout, Nb factures |

#### Actions

- **[+ Ajouter Client]** → `/clients/create`
- **[Voir détail]** → Modal ou page `/clients/{id}`
- **[Éditer]** → `/clients/{id}/edit`
- **[Historique factures]** → Modal avec tableau factures du client
- **[Inscrire URSSAF]** → POST `/api/clients/{id}/register` → loading + toast succès/erreur
- **[Supprimer]** → Confirmation modal → DELETE (si pas factures liées)

---

### 3.6 Formulaire Client — `/clients/create` & `/clients/{id}/edit`

#### Responsabilité
Créer ou modifier données client + trigger inscription URSSAF.

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ Ajouter un Client                                           │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Nom *                          │ Prénom *                │ │
│ │ [________________]             │ [________________]       │ │
│ │ ✓ OK                          │ ✓ OK                     │ │
│ │                                                         │ │
│ │ Email * (vérifié URSSAF)       │ Téléphone (optionnel)   │ │
│ │ [____@example.com]             │ [06______________]      │ │
│ │ ✓ Format email valide         │                         │ │
│ │                                                         │ │
│ │ Adresse *                      │ Code Postal *           │ │
│ │ [Rue X, Apt Y _________]       │ [75001]                 │ │
│ │ ✓ OK                          │ ✓ OK                     │ │
│ │                                                         │ │
│ │ Ville *                        │ Pays (def: France)      │ │
│ │ [Paris____________]            │ [France]                │ │
│ │ ✓ OK                          │ (pré-rempli)            │ │
│ │                                                         │ │
│ │ Notes (optionnel, internal)                              │ │
│ │ [Étudiant ENS, heures fixes le lundi]__________          │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Statut URSSAF                                           │ │
│ │ État : ⚠️ A_INSCRIRE                                    │ │
│ │ [🚀 Inscrire Maintenant] (optionnel, créer d'abord)    │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Actions                                                 │ │
│ │ [Créer Client] [Annuler]                                │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Champ | Type | Validation |
|-------|------|-----------|
| **Nom** | Text Input | Requis, min 2 chars |
| **Prénom** | Text Input | Optionnel |
| **Email** | Email Input | Requis, format email valide (regexp), vérification SMTP optionnelle |
| **Téléphone** | Tel Input | Optionnel, format `06/07 XX XX XX XX` |
| **Adresse** | Text Input | Requis, min 5 chars |
| **Code Postal** | Text Input | Format `\d{5}` |
| **Ville** | Text Input | Requis |
| **Pays** | Select | Default: France, éditable |
| **Notes** | Textarea | Optionnel, max 500 chars |
| **Statut URSSAF** | Display + Button | Lecture seule + bouton inscription |

#### Validation Live

- **Email** : Format valide + tooltip "Cet email sera utilisé par URSSAF"
- **Code Postal** : 5 chiffres
- **Adresse/Ville** : Non-vide

#### Actions

- **[Créer Client]** → POST `/api/clients` → redirection `/clients/{id}` avec toast
- **[Inscrire Maintenant]** → POST `/api/clients/{id}/register` (optionnel après création)
- **[Annuler]** → Retour `/clients`

---

### 3.7 Rapprochement Bancaire — `/reconcile`

#### Responsabilité
Vue synthétique lettrage auto/manuel avec scoring et actions de validation.

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ Rapprochement Bancaire                                      │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Résumé Lettrage                                         │ │
│ │ ✓ Letterés AUTO    : 15 factures (525,00 €)             │ │
│ │ ⚠️ A VERIFIER     : 3 factures (105,00 €)              │ │
│ │ ❌ PAS DE MATCH    : 2 factures (70,00 €)              │ │
│ │ ────────────────────────────────────────────────────────│ │
│ │ Total PAYE (depuis Swan) : 20 factures (700,00 €)      │ │
│ │ Total LETTRÉ : 18 factures (630,00 €)                  │ │
│ │ Non-lettrés : 2 factures (70,00 €) — en attente virement│ │
│ │                                                         │ │
│ │ [↻ Rafraîchir depuis Swan] [🔗 Voir Onglet Lettrage]  │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Factures A VERIFIER — Action Requise                   │ │
│ │                                                         │ │
│ │ Facture | Montant | Score | Proposition          |Action│ │
│ │─────────────────────────────────────────────────────────│ │
│ │ F10     │ 50,00 € │ 75    │ VIRT-X, 50€, 16/03  │ ✓ ❌│ │
│ │ F11     │ 30,00 € │ 60    │ VIRT-Y, 30€, 16/03  │ ✓ ❌│ │
│ │ F12     │ 25,00 € │ 50    │ No match found      │ 🔍  │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Factures AUTO-LETTRÉES                                  │ │
│ │ Masquer/Montrer détails (15 factures)                   │ │
│ │ [Afficher les détails]                                  │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Factures NON MATCHÉES                                   │ │
│ │ En attente d'un virement Swan                           │ │
│ │                                                         │ │
│ │ F13 │ 40,00 € │ Aucun match │ 15/03 |  (attendre)     │ │
│ │ F14 │ 30,00 € │ Aucun match │ 14/03 |  (attendre)     │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Composant | Type | Données |
|-----------|------|--------|
| **Card Résumé** | KPI Cards (3 colonnes) | AUTO, A_VERIFIER, PAS_DE_MATCH counts + montants |
| **Total PAYE** | Display | SUM(Factures PAYE) |
| **Total LETTRÉ** | Display | SUM(Factures RAPPROCHE) |
| **Tableau A_VERIFIER** | DataGrid | 5 colonnes + actions |
| **Tableau AUTO** | Collapsible | Détails (voir détails link) |
| **Tableau PAS_DE_MATCH** | Collapsible | Factures attendant virement |

#### Actions

**Pour chaque ligne A_VERIFIER :**
- **[✓]** → POST `/api/reconcile/{facture_id}/confirm` → statut RAPPROCHE
- **[❌]** → POST `/api/reconcile/{facture_id}/reject` → statut PAS_DE_MATCH
- **[Clic ligne]** → `/reconcile/{facture_id}` (détail 1-to-1)

**Globales :**
- **[↻ Rafraîchir]** → POST `/api/reconcile/refresh` (appel Swan + calcul scoring)
- **[🔗 Voir onglet Lettrage]** → Lien iframe Sheets (lecture)

---

### 3.8 Détail Réconciliation — `/reconcile/{facture_id}`

#### Responsabilité
Comparaison visuelle facture ↔ transaction avec scoring détaillé et actions.

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ Détail Lettrage — Facture F10                      [← Retour]│
│                                                              │
│ ┌──────────────────────────────┐  ┌──────────────────────┐ │
│ │ FACTURE                      │  │ TRANSACTION SWAN      │ │
│ │                              │  │                      │ │
│ │ ID: F10                      │  │ ID: VIRT-FRANCE-001 │ │
│ │ Client: Alice B              │  │ Date: 16/03 14:00   │ │
│ │ Montant: 50,00 €             │  │ Montant: 50,00 €    │ │
│ │ Date Facture: 15/03          │  │ Libellé: VIRT FRANCE│ │
│ │ Type: BNC-Service            │  │ Type: Virement      │ │
│ │                              │  │ Compte: Swan (...)  │ │
│ │ Description: Cours Maths     │  │                      │ │
│ │                              │  │                      │ │
│ └──────────────────────────────┘  └──────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Scoring Confiance                                       │ │
│ │                                                         │ │
│ │ ✓ Montant Exact (50,00€ = 50,00€)        : +50 pts    │ │
│ │ ✓ Date proche (écart 1 jour)             : +30 pts    │ │
│ │ ✓ Libellé contient "VIRT" (pattern OK)   : +20 pts    │ │
│ │                                                         │ │
│ │ SCORE TOTAL : 100/100 — Très Confiant    │ │
│ │ Recommandation : ✓ Accepter ce matching  │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Actions                                                 │ │
│ │ [✓ Accepter le Matching] [❌ Rejeter] [🔍 Chercher autre]
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Composant | Type | Contenu |
|-----------|------|---------|
| **Card Facture** | Info Card | ID, Client, Montant, Dates, Description |
| **Card Transaction** | Info Card | ID Swan, Montant, Date, Libellé |
| **Scoring Breakdown** | List | Chaque critère + points |
| **Confidence Badge** | Badge | Texte + couleur selon score |
| **Boutons Actions** | Buttons | Accepter, Rejeter, Chercher |

#### Données

- **Montant Exact** : +50 si `facture.montant == transaction.montant`
- **Date Proche** : +30 si écart < 3 jours, +20 si < 5 jours
- **Libellé** : +20 si libellé contient "URSSAF" ou pattern connu

**Score Total >= 80 = "Très Confiant", < 80 = "A Vérifier"**

#### Actions

- **[✓ Accepter]** → POST `/api/reconcile/{facture_id}/confirm` → redirect `/reconcile`
- **[❌ Rejeter]** → POST `/api/reconcile/{facture_id}/reject` → statut PAS_DE_MATCH
- **[🔍 Chercher autre]** → Modal avec liste transactions non-matchées (filtre montant approx)

---

### 3.9 Dashboard Métriques (iframes) — `/metrics`

#### Responsabilité
Affichage des onglets Google Sheets publics (Lettrage, Balances, NOVA, Cotisations, Fiscal).

#### Wireframe Textuel

```
┌─────────────────────────────────────────────────────────────┐
│ Dashboard Métriques                                         │
│                                                              │
│ [Lettrage] [Balances] [NOVA] [Cotisations] [Fiscal]        │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Onglet : LETTRAGE (pubhtml embed)                       │ │
│ │                                                         │ │
│ │ [Iframe Google Sheets — pubhtml embed, readonly]       │ │
│ │ Colonnes : Facture ID | Montant Facture | Txn ID |    │ │
│ │            Montant Txn | Écart | Score Confiance |     │ │
│ │            Statut (AUTO / A_VERIFIER / PAS_DE_MATCH)   │ │
│ │                                                         │ │
│ │ [Rows affichent les lettrage auto-calculés]            │ │
│ │                                                         │ │
│ │ [Lien : "Éditer dans Google Sheets"]                   │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Balances Tab]                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Mois | Nb Factures | CA Total | Reçu URSSAF | Solde|    │
│ │ [Tableau calcul mensuel]                                │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [NOVA Tab]                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Trimestre | Nb Intervenants | Heures | Nb Particuliers │ │
│ │ CA Trimestre | Deadline Saisie                         │ │
│ │ [Tableau trimestriel NOVA]                             │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Cotisations Tab]                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Mois | CA Encaissé | Taux Charges | Montant Charges   │ │
│ │ Cumul CA | Net Après Charges                           │ │
│ │ [Tableau mensuel charges 25.8%]                        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Fiscal IR Tab]                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Revenu Apprentissage | Seuil Exo | CA Micro            │ │
│ │ Abattement 34% | Revenu Imposable | Tranches IR       │ │
│ │ Taux Marginal | Simulation VL 2.2%                     │ │
│ │ [Tableau simulation fiscale]                           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Lien global : Ouvrir Google Sheets]                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Composants

| Onglet | Source | Type | Mode |
|--------|--------|------|------|
| **Lettrage** | Sheets pubhtml | Iframe embed | Readonly (formules) |
| **Balances** | Sheets pubhtml | Iframe embed | Readonly (formules) |
| **NOVA** | Sheets pubhtml | Iframe embed | Readonly (formules) |
| **Cotisations** | Sheets pubhtml | Iframe embed | Readonly (formules) |
| **Fiscal IR** | Sheets pubhtml | Iframe embed | Readonly (formules) |

#### Implémentation

```html
<!-- Exemple pour onglet Lettrage -->
<iframe
  src="https://docs.google.com/spreadsheets/d/SHEET_ID/pubhtml?gid=LETTRAGE_GID&single=true&widget=true&headers=false"
  width="100%"
  height="600px"
  frameborder="0"
/>
```

**À fournir par Jules :**
- `SHEET_ID` : ID feuille Google (depuis URL)
- `LETTRAGE_GID` : GID onglet Lettrage (depuis URL `#gid=123`)
- Idem pour autres onglets (Balances, NOVA, Cotisations, Fiscal)

---

## 4. Patterns d'Interaction

### 4.1 Pattern Création Facture → Soumission → Feedback

```
┌─ Utilisateur clique [+ Créer Facture]
│
├─ Affichage formulaire (/invoices/create)
│  ├─ Chargement liste clients (GET /api/clients)
│  └─ UI ready
│
├─ Utilisateur saisit données (client, heures, tarif, etc.)
│  ├─ Validation live de chaque champ
│  └─ Montant auto-calculé
│
├─ Utilisateur clique [Sauvegarder en Brouillon]
│  ├─ POST /api/invoices {données}
│  ├─ Réponse : {id, statut=BROUILLON, pdf_url}
│  ├─ Toast succès : "Facture sauvegardée (F1)"
│  ├─ Affichage lien PDF
│  └─ UI reste formulaire (prêt pour soumettre ou éditer)
│
├─ Utilisateur clique [Soumettre à URSSAF]
│  ├─ Validation côté client (check client inscrit URSSAF)
│  ├─ POST /api/invoices/{id}/submit
│  │  ├─ Backend appelle URSSAFClient.create_payment_request()
│  │  ├─ En cas succès : {id_demande, statut=CREE}
│  │  └─ En cas erreur : {error: "Email client invalide"}
│  ├─ Toast succès : "Facture soumise, ID: URD-2026-001234"
│  ├─ Redirect /invoices/{id} (détail avec statut SOUMIS)
│  └─ Timer 48h visible si besoin
│
├─ Système polling (cron 4h)
│  ├─ GET URSSAF /demandes-paiement/{id_demande}
│  ├─ Statut retourné : EN_ATTENTE → VALIDE → PAYE
│  ├─ Mise à jour Sheets
│  ├─ Dashboard rafraîchi à next poll utilisateur
│  └─ Email rappel T+36h si besoin
│
└─ Utilisateur revient voir dashboard
   ├─ Voit facture statut PAYE
   ├─ Clique [📋 Lettrage] → /reconcile
   └─ Valide lettrage (voir pattern suivant)
```

### 4.2 Pattern Lettrage Bancaire

```
┌─ Utilisateur clique [📋 Lettrage] ou [↻ Rapprochement]
│
├─ Affichage page /reconcile
│  ├─ GET /api/reconcile/status → Résumé (AUTO, A_VERIFIER, PAS_DE_MATCH)
│  ├─ GET /api/invoices?statut=PAYE → Factures payées
│  ├─ GET /api/swan/transactions → Transactions Swan (derniers 30j)
│  ├─ Backend BankReconciliation.reconcile()
│  │  ├─ Matching algorithme (montant, date, libellé)
│  │  ├─ Scoring (score >= 80 → AUTO, sinon A_VERIFIER)
│  │  └─ Écriture onglet Lettrage (Sheets)
│  └─ UI affiche résumé + tableau A_VERIFIER
│
├─ Pour chaque ligne A_VERIFIER :
│  ├─ Utilisateur voit : Facture | Montant | Score | Proposition
│  ├─ Option 1 : Clique [✓] → Accepter
│  │  └─ POST /api/reconcile/{facture_id}/confirm → RAPPROCHE
│  ├─ Option 2 : Clique [❌] → Rejeter
│  │  └─ POST /api/reconcile/{facture_id}/reject → PAS_DE_MATCH
│  ├─ Option 3 : Clique [Clic ligne] → Détail /reconcile/{facture_id}
│  │  ├─ Affichage : Facture gauche | Transaction droite
│  │  ├─ Scoring détaillé visible
│  │  └─ Actions : Accepter, Rejeter, Chercher autre
│  │      └─ Chercher autre : Modal avec transactions alternatives
│  └─ Toast feedback : "Facture lettée (score 95)"
│
├─ Balances onglet auto-mise à jour (formules Sheets)
│  └─ Montants non-lettrés baissent
│
└─ Utilisateur clique [🔗 Voir onglet Lettrage] → /metrics (iframe Sheets)
   └─ Vérification visuelle lettrage final
```

### 4.3 Pattern Erreur & Retry

```
┌─ Utilisateur soumet facture à URSSAF
│  └─ API URSSAF retourne 400 : "Email client invalide"
│
├─ UI affiche erreur rouge
│  ├─ Message utilisateur : "Erreur : Email client invalide. Corrigez et re-tentez."
│  ├─ Suggestion : "Allez sur Gestion Clients et corrigez l'email"
│  └─ Statut Sheets : Reste BROUILLON (pas changé)
│
├─ Utilisateur clique [Corriger dans Gestion Clients]
│  ├─ Va sur /clients/{client_id}/edit
│  ├─ Corrige email
│  ├─ Sauvegarde
│  └─ Toast : "Client mis à jour"
│
├─ Utilisateur revient sur /invoices/{id}/edit
│  ├─ Clique [Soumettre URSSAF] à nouveau
│  ├─ API accepte → {id_demande, statut=CREE}
│  ├─ Toast succès : "Facture soumise"
│  └─ Redirect /invoices/{id}
│
└─ Workflow reprend normalement
```

### 4.4 Pattern Rappel T+36h

```
┌─ Facture créée T+0
│  ├─ Statut : CREE (ou EN_ATTENTE après email URSSAF)
│  └─ Timer : 48h avant expiration
│
├─ PaymentTracker cron à T+36h
│  ├─ Check : facture EN_ATTENTE depuis > 36h ?
│  ├─ Oui → NotificationService.send_reminder()
│  └─ Email à Jules : "Facture client X en attente de validation, 12h restants"
│
├─ Jules reçoit email
│  ├─ Lit : "Client X n'a pas validé"
│  ├─ Clique lien → /invoices/{id}
│  └─ Optionnel : appelle client pour relancer
│
├─ Utilisateur consulte dashboard
│  ├─ Facture visible en orange (EN_ATTENTE)
│  ├─ Badge "⚠️ À valider (12h restants)"
│  └─ Peut cliquer [↻ Sync] pour forcing check statut
│
├─ Deux scénarios :
│  ├─ A) Client valide finalement
│  │  └─ Polling détecte VALIDE → PAYE → Workflow normal
│  └─ B) Délai 48h dépasse
│     └─ Statut devient EXPIRE → Facture visible rouge → [🔄 Re-soumettre]
│
└─ Jules clique [🔄 Re-soumettre]
   ├─ POST /api/invoices/{id}/resubmit
   ├─ Nouvelle demande URSSAF créée
   └─ Workflow reprend
```

---

## 5. Composants UI Réutilisables

### 5.1 Palette Couleurs

```
Statuts Facture (badges) :

🟢 PAYE        : #10b981 (vert — succès)
🔵 EN_ATTENTE  : #3b82f6 (bleu — info)
🟠 VALIDE      : #f59e0b (orange — warning)
⚫ BROUILLON    : #6b7280 (gris — neutre)
🔴 ERREUR      : #ef4444 (rouge — danger)
🟡 EXPIRE      : #fbbf24 (jaune — alert)
⚪ SOUMIS      : #9ca3af (gris-clair — processing)
🟣 RAPPROCHE   : #8b5cf6 (violet — complete)

Background :
- Primaire : #0f172a (dark slate-900)
- Secondary : #1e293b (dark slate-800)
- Accent : #38bdf8 (cyan-400)
- Accent2 : #a78bfa (violet-400)
- Text : #e2e8f0 (slate-100)
- Muted : #94a3b8 (slate-400)
```

### 5.2 Composants Tailwind

| Composant | Classe | Usage |
|-----------|--------|-------|
| **Card** | `bg-slate-800 rounded-lg border border-slate-700 p-4` | Info containers |
| **Button Primary** | `bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded` | Créer, Soumettre |
| **Button Secondary** | `bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded` | Annuler, Éditer |
| **Button Danger** | `bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded` | Supprimer, Annuler |
| **Input** | `bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white` | Form inputs |
| **Badge Statut** | `inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold` | Status indicators |
| **Alert Success** | `bg-green-900/20 border border-green-700 rounded p-3 text-green-200` | Toast success |
| **Alert Error** | `bg-red-900/20 border border-red-700 rounded p-3 text-red-200` | Toast error |
| **Table** | `w-full border-collapse` | Data grids |
| **Spinner** | `animate-spin` (SVG) | Loading states |

### 5.3 Icônes & Symboles

| Symbole | Usage |
|---------|-------|
| `+` | Créer |
| `✏️` | Éditer |
| `❌` | Supprimer/Annuler |
| `✓` | Confirmer/Valider |
| `↻` | Rafraîchir/Sync |
| `👁️` | Voir/Aperçu |
| `📥` | Télécharger |
| `📤` | Envoyer |
| `📋` | Lettrage/Reconcile |
| `🔍` | Recherche |
| `🚀` | Action urgente (inscription) |
| `⚠️` | Attention/Warning |
| `🔴🟠🟢🔵` | Couleur statut |

---

## 6. Responsive Design & Considérations Mobiles

### 6.1 Breakpoints Tailwind

```css
Mobile-First :
sm:  640px  (small phones)
md:  768px  (tablets)
lg:  1024px (desktop)
xl:  1280px (wide desktop)
```

### 6.2 Adaptations par Écran

#### Dashboard (/)

**Desktop (lg+)** : 4 KPI cards (2×2) + tableau 5 colonnes
**Tablet (md)** : 2 KPI cards stacked + tableau 3 colonnes
**Mobile (sm)** : 1 KPI card + tableau 2 colonnes + scroll horizontal

#### Liste Factures (/invoices)

**Desktop (lg+)** : Tableau complet (7 colonnes) + filtres horizontaux
**Tablet (md)** : Tableau condensé (4 colonnes) + filtres sous forme dropdown
**Mobile (sm)** : Liste cards au lieu de tableau
```
┌──────────────────┐
│ Alice B          │
│ 30,00 € 🟢 PAYE  │
│ 15/03 14:32      │
│ [Actions ...]    │
└──────────────────┘
```

#### Formulaires (create/edit)

**Desktop (lg+)** : 2 colonnes (côte à côte)
**Tablet (md)** : 1.5 colonnes (adaptation dynamique)
**Mobile (sm)** : 1 colonne (full stack)

Marges/espacements : `p-4` (mobile) → `p-8` (desktop)

### 6.3 Focus Phase 2 : Desktop First

- **MVP Phase 2** : Desktop + Tablet optimisé
- **Phase 3** : Full mobile responsive + PWA
- **Accepté** : Mobile OK mais pas prioritaire (Julius peut utiliser PC après cours)

---

## 7. Indicateurs Temps Réel vs Calculés

### 7.1 Temps Réel (Actualisé à Chaque Chargement)

Ces données sont **fetchées de Sheets ou APIs externes** lors du chargement/refresh :

| Indicateur | Source | Fréquence | Affichage |
|-----------|--------|-----------|-----------|
| **CA Total (Mois)** | SUM(Factures PAYEE, mois) | Chargement page | Card KPI dashboard |
| **Nb Factures En Attente** | COUNT(Factures EN_ATTENTE) | Chargement page | Card dashboard |
| **Montant En Attente** | SUM(Factures EN_ATTENTE) | Chargement page | Card dashboard |
| **Virements Swan** | API Swan GraphQL | Clic [↻ Rafraîchir] | Card dashboard |
| **Statut Facture** | GET URSSAF /demandes-paiement/{id} | Clic [↻ Sync] | Badge détail facture |
| **Liste Transactions Swan** | SwanClient.get_transactions() | Clic [Rappro] | Tableau reconcile |

### 7.2 Calculés (Formules Sheets — Semi-Temps Réel)

Ces données sont **calculées par des formules Google Sheets** :

| Indicateur | Formule | Actualisation | Affichage |
|-----------|---------|---------------|-----------|
| **Montant Total Facture** | = Quantité × Tarif | Saisie immédiate (frontend) | Formulaire create |
| **Balances Mensuelles** | = SUM(Factures mois) | Après update Factures | Onglet Balances (iframe) |
| **Score Confiance (Lettrage)** | = IF montant exact (+50) + IF date < 3j (+30) + IF libelle URSSAF (+20) | Après matching | Onglet Lettrage (iframe) |
| **Cotisations Mensuelles** | = CA × 25.8% | Après update CA | Onglet Cotisations (iframe) |
| **Fiscal IR (Simulation)** | = (CA × 0.66) × tranches IR | Trimestriel | Onglet Fiscal (iframe) |
| **Metrics NOVA** | = COUNT intervenants, SUM heures, etc. | Trimestriel | Onglet NOVA (iframe) |

### 7.3 Caching & Stratégie Refresh

```
Frontend Caching (FastAPI) :
- Dashboard KPI : Cache 5 min (GET /api/dashboard)
- Liste clients : Cache 1 min
- Liste factures : Cache 2 min

Backend Polling (Cron) :
- PaymentTracker : 4 heures (URSSAF statut)
- BankReconciliation : Manuel (user-triggered) ou 1x/jour auto

User Manual Actions :
- [↻ Sync URSSAF] : Force polling immédiat (< 30 sec)
- [↻ Lettrage] : Force réconciliation immédiate
- [↻ Rafraîchir] : Vide cache + re-fetch

Google Sheets :
- Formules iframes : Recalculées en temps réel par Google
- Onglets pubhtml : Actualisées automatiquement
```

---

## 8. Accessibilité & Standards

### 8.1 WCAG 2.1 AA Compliance

| Critère | Implémentation |
|---------|----------------|
| **Contrast Ratio** | Min 4.5:1 (texte normal) — Vérifier avec palette couleurs |
| **Keyboard Navigation** | Tab order logique (Tab) + Escape pour modals |
| **ARIA Labels** | `aria-label` sur boutons icons, `aria-describedby` sur inputs errors |
| **Form Labels** | `<label for="input-id">` lié explicitement |
| **Error Messages** | Affichés rouge + textuel (pas couleur seule) |
| **Focus Indicators** | `:focus-visible` outline (ne pas supprimer) |
| **Semantic HTML** | `<button>` vs `<div>`, `<nav>`, `<main>`, `<table>` |
| **Alt Text** | Images décoratives : `alt=""`, images importantes : alt descriptif |

### 8.2 Dark Mode (Déjà appliqué)

- Palette Tailwind utilisée respecte contraste dark theme
- Texte clair sur fond sombre (#0f172a → #e2e8f0)
- Pas de texte blanc sur fond blanc

### 8.3 Responsive Text

```css
/* Utiliser rem au lieu de px pour scalabilité */
h1: text-3xl (48px)
h2: text-2xl (36px)
h3: text-xl (24px)
body: text-base (16px)
small: text-sm (14px)

/* Min font-size : 12px (lisibilité) */
```

### 8.4 Touch Targets (Mobile Phase 3)

- Min 44×44px pour boutons cliquables
- Spacing entre boutons : min 8px

---

## Conclusion

Cette spécification UX Phase 2 couvre l'intégralité de l'interface utilisateur SAP-Facture sur desktop/tablet. Les écrans sont organisés logiquement, les patterns d'interaction sont clairement documentés, et les composants réutilisables assurent une cohérence visuelle.

### Points Clés de Livrable Phase 2 :

✓ **9 écrans** principaux avec wireframes textuels
✓ **Navigation sitemap** complète
✓ **Composants Tailwind** spécifiés (couleurs, spacing)
✓ **Patterns d'interaction** (création, lettrage, erreur, rappel)
✓ **Données & sources** (Sheets vs API temps réel)
✓ **Responsive design** (desktop-first, mobile Phase 3)
✓ **Accessibilité** (WCAG 2.1 AA)
✓ **Indicateurs temps réel vs calculés** explicités
✓ **iframes Google Sheets** intégrés pour métriques

**Prochaines étapes** :
1. Développement FastAPI SSR + Jinja2 templates
2. Intégration Tailwind CSS
3. Tests UI/UX avec Jules
4. Phase 3 : Responsive mobile complet + PWA

---

**Document Version** : 1.0
**Date** : Mars 2026
**Auteur** : Winston (BMAD System Architect)
**Approuvé par** : Jules Willard
