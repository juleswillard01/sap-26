# Spécifications UX - SAP-Facture MVP

**Pour**: Jules Willard (Micro-entrepreneur SAP)
**De**: Winston (BMAD UX Designer)
**Date**: 14 Mars 2026
**Statut**: ✅ MVP UX Specifications
**Langue**: Français

---

## Table des Matières

1. [Philosophie Design](#philosophie-design)
2. [Structure Navigation](#structure-navigation)
3. [Système Design](#système-design)
4. [Écrans MVP](#écrans-mvp)
   - [Authentification](#authentification)
   - [Dashboard](#dashboard)
   - [Factures - Liste](#factures--liste)
   - [Factures - Créer/Modifier](#factures--créermodifier)
   - [Factures - Détail](#factures--détail)
   - [Clients - Liste](#clients--liste)
   - [Clients - Créer/Modifier](#clients--créermodifier)
   - [Rapprochement Bancaire](#rapprochement-bancaire)
   - [Paramètres](#paramètres)
5. [Composants Réutilisables](#composants-réutilisables)
6. [États et Transitions](#états-et-transitions)
7. [Interactions HTMX](#interactions-htmx)
8. [Guide Accessibilité](#guide-accessibilité)

---

## Philosophie Design

### Principes Directeurs

**1. Efficacité Avant Esthétique**
- Réduire le temps par facture de 20 min → 5 min
- Max 3 clics pour actions courantes
- Pas de frills inutiles (pas d'animations, pas de dégradés)

**2. Clarté Professionnelle**
- Apparence comptable/respectable
- Langage clair (pas de jargon sauf URSSAF nécessaire)
- Données bien organisées en tableaux

**3. Confiance et Sécurité**
- Afficher statuts explicitement (qui a validé quoi)
- Confirmations avant actions destructives
- Audit trail visible (logs de soumission)

**4. Desktop-First, Mobile-Ready**
- Optimisé pour écran PC (1280px+)
- Responsive simple (pile verticale sur mobile)
- Pas de hover-only interactions

**5. Accessibilité**
- Contrast ratio 4.5:1 minimum
- Labels associés aux inputs
- Breadcrumbs pour navigation
- Clavier navigable (Tab, Enter, Escape)

---

## Structure Navigation

### Layout Global

```
┌─────────────────────────────────────────────────────────────────┐
│  LOGO     SAP-Facture      [User: Jules]  [⚙️ Paramètres] [Déconnexion]   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────────────────────┐ │
│  │ MENU LATÉRAL        │  │                                     │ │
│  │                     │  │   CONTENU PRINCIPAL                 │ │
│  │ • Dashboard         │  │                                     │ │
│  │ • Factures          │  │   (Écran actuel)                   │ │
│  │ • Clients           │  │                                     │ │
│  │ • Rapprochement     │  │                                     │ │
│  │                     │  │                                     │ │
│  │ ──────────────────  │  │                                     │ │
│  │ • Paramètres        │  │                                     │ │
│  │ • Docs & Support    │  │                                     │ │
│  │                     │  │                                     │ │
│  └─────────────────────┘  └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Navigation Primaire (Sidebar)

```
Élément          URL                 Icône  Statut
─────────────────────────────────────────────────
Dashboard        /                   📊     Accueil
Factures         /invoices           📄     Gestion
Clients          /clients            👥     Gestion
Rapprochement    /reconciliation      🔄     Sync bancaire
────────────────────────────────────────────────
Paramètres       /settings           ⚙️      Config
```

### Navigation Secondaire (In-Screen)

- **Breadcrumbs** en haut de page (ex: `Dashboard > Factures > Détail #123`)
- **Tabs** pour sections multiples dans un écran
- **Buttons** pour actions (créer, modifier, supprimer)

### Responsive Sidebar

- **Desktop (≥1280px)**: Sidebar permanent à gauche
- **Tablet (768-1279px)**: Sidebar collapsible (hamburger menu)
- **Mobile (<768px)**: Sidebar en drawer (slide from left)

---

## Système Design

### Palette Couleurs

**Primaire**: Bleu professionnel (confiance, comptabilité)
```
Bleu Principal:     #0066CC (RGB: 0, 102, 204)
Bleu Clair:         #E6F0FF (RGB: 230, 240, 255)
Bleu Foncé:         #003D99 (RGB: 0, 61, 153) — hover/active
```

**Accent**: Vert succès (validation, paiement)
```
Vert Principal:     #22C55E (RGB: 34, 197, 94)
Vert Clair:         #DCFCE7 (RGB: 220, 252, 231)
```

**Sémantique**:
```
Alerte (warning):   #EAB308 (jaune) — en attente validation
Erreur:             #EF4444 (rouge) — rejet URSSAF
Info:               #0066CC (bleu) — notifications
Succès:             #22C55E (vert) — soumis, payé
```

**Neutres**:
```
Fond:               #FFFFFF
Fond Alt:           #F9FAFB (gris très clair)
Border:             #E5E7EB (gris léger)
Text Principal:     #1F2937 (gris foncé)
Text Secondaire:    #6B7280 (gris moyen)
Disabled:           #D1D5DB (gris pâle)
```

### Typographie

**Police**: System font stack (maximum compatibilité, zero external fonts)
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

**Hiérarchie**:
```
Titre Page (h1):        24px, 700 bold, couleur #1F2937
Titre Section (h2):     20px, 600 semi-bold, couleur #1F2937
Titre Sous (h3):        16px, 600 semi-bold, couleur #1F2937
Body Text:              14px, 400 regular, couleur #1F2937
Text Secondaire:        14px, 400 regular, couleur #6B7280
Label Form:             13px, 500 medium, couleur #1F2937
Petit texte:            12px, 400 regular, couleur #6B7280
```

### Spacing

**Base**: 4px (modulo)
```
xs:  4px   (gaps étroits)
sm:  8px   (padding petit)
md:  16px  (padding standard)
lg:  24px  (section spacing)
xl:  32px  (grand spacing)
```

### Composants Standards

#### Boutons

**Primaire** (actions principales)
```
Bg: #0066CC, Text: white
Hover: #003D99
Padding: 10px 16px, Border-radius: 6px
Font: 14px semi-bold
```

**Secondaire** (actions alternatives)
```
Bg: #E5E7EB, Text: #1F2937
Hover: #D1D5DB
Padding: 10px 16px, Border-radius: 6px
Font: 14px semi-bold
```

**Danger** (supprimer, annuler)
```
Bg: #EF4444, Text: white
Hover: #DC2626
Padding: 10px 16px, Border-radius: 6px
Font: 14px semi-bold
```

**Success** (valider, soumettre)
```
Bg: #22C55E, Text: white
Hover: #16A34A
Padding: 10px 16px, Border-radius: 6px
Font: 14px semi-bold
```

#### Inputs

```
Border: 1px solid #E5E7EB
Border-radius: 6px
Padding: 10px 12px
Font: 14px
Focus: border #0066CC 2px, box-shadow: 0 0 0 3px #E6F0FF
Disabled: bg #F9FAFB, color #D1D5DB
```

#### Tables

```
Border-collapse: collapse
Header bg: #F9FAFB
Row hover: bg #F9FAFB (léger)
Border: 1px solid #E5E7EB
Padding: 12px
```

#### Cards / Boxes

```
Bg: white
Border: 1px solid #E5E7EB
Border-radius: 8px
Padding: 16px
Box-shadow: 0 1px 3px rgba(0,0,0,0.1)
```

#### Badges / Tags

```
Padding: 4px 8px
Font: 12px semi-bold
Border-radius: 4px

Statut:
- Draft:    bg #F3F4F6, text #6B7280
- Soumis:   bg #DBEAFE, text #1E40AF
- Validé:   bg #DCFCE7, text #166534
- Payé:     bg #DCFCE7, text #166534
- Erreur:   bg #FEE2E2, text #991B1B
- Attente:  bg #FEF3C7, text #92400E
```

---

## Écrans MVP

### 1. Authentification

#### 1.1 Login Page

**URL**: `/login`
**Rôle**: Point d'entrée utilisateur
**Technologie**: Form POST + server-side validation

**Wireframe**:
```
┌────────────────────────────────────────┐
│                                        │
│         [LOGO SAP-Facture]             │
│                                        │
│         Connexion                      │
│         ──────────────────────         │
│                                        │
│   Email ou identifiant:                │
│   ┌──────────────────────────────┐    │
│   │ [email@example.com]          │    │
│   └──────────────────────────────┘    │
│                                        │
│   Mot de passe:                        │
│   ┌──────────────────────────────┐    │
│   │ [••••••••••]                 │    │
│   └──────────────────────────────┘    │
│                                        │
│   ☐ Rester connecté                    │
│                                        │
│   ┌──────────────────────────────┐    │
│   │    Se connecter              │    │
│   └──────────────────────────────┘    │
│                                        │
│   [Mot de passe oublié?]               │
│   [Créer un compte] (Phase 2)          │
│                                        │
│   ──────────────────────────────────   │
│   Besoin d'aide? [contact support]     │
│                                        │
└────────────────────────────────────────┘
```

**Composants**:
- Logo SAP-Facture (120x40px, top center)
- Titre "Connexion" (24px, #1F2937)
- Input email (full width, placeholder "Email ou identifiant")
- Input password (full width, type="password")
- Checkbox "Rester connecté" (optional MVP)
- Button "Se connecter" (full width, primary)
- Link "Mot de passe oublié?" (text, right-aligned)
- Footer avec support link

**Données Affichées**:
- Email/username input
- Password input
- Remember me toggle (optional)

**Actions Disponibles**:
- Soumettre login (POST /login)
- Forgot password flow (Phase 2)
- Create account (Phase 2)

**États**:
- **Default**: Champs vides, prêt à saisir
- **Loading**: Button désactivé, spinner, "Connexion..."
- **Error**: Bordure rouge input, message "Email ou mot de passe invalide"
- **Success**: Redirect vers dashboard

**Validation**:
- Email: format valide
- Password: requis, min 6 caractères (côté serveur)
- Erreur générique si échec (sécurité: ne pas révéler si email existe)

**Navigation**:
- Redirect `/` → `/login` si non authentifié
- Après succès → `/` (dashboard)

---

#### 1.2 Oubli Mot de Passe (Phase 2)

**URL**: `/forgot-password`
**État**: Non-MVP, placeholder pour Phase 2

---

### 2. Dashboard

**URL**: `/`
**Rôle**: Accueil, vue d'ensemble rapide
**Technologie**: FastAPI SSR + Jinja2 + HTMX polling (auto-sync statuts)

**Wireframe**:
```
┌─────────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐  DASHBOARD - Jules Willard                        │
│ │  SAP Fact.   │  Bienvenue! Voici ton aperçu rapide.              │
│ │              │                                                    │
│ │ • Dashboard  │  ┌─────────────────────────────────────────────┐  │
│ │ • Factures   │  │ STATISTIQUES RAPIDES (Mois Courant)         │  │
│ │ • Clients    │  ├─────────────────────────────────────────────┤  │
│ │ • Rappro.    │  │ Factures créées:  8        CA Total: €2400 │  │
│ │              │  │ En attente:       3        À payer:  €600   │  │
│ │              │  │ Payées:           5        Payé:    €1800   │  │
│ │              │  └─────────────────────────────────────────────┘  │
│ │              │                                                    │
│ │ ────────────│  ┌─────────────────────────────────────────────┐  │
│ │ • Paramètres│  │ ACTIONS RAPIDES                             │  │
│ │              │  │                                             │  │
│ │              │  │ [+ Nouvelle Facture]  [+ Nouveau Client]   │  │
│ │              │  │ [Sync URSSAF]         [Voir Rapprochement] │  │
│ │              │  │                                             │  │
│ │              │  └─────────────────────────────────────────────┘  │
│ └──────────────┘                                                    │
│                  ┌─────────────────────────────────────────────┐   │
│                  │ FACTURES RÉCENTES (10 dernières)            │   │
│                  ├─────────────────────────────────────────────┤   │
│                  │ #  │ Client      │ Montant │ Date    │ Status │   │
│                  │────┼─────────────┼─────────┼─────────┼────────│   │
│                  │125 │ ABC Corp    │ €400    │ 14/03   │ Payée  │   │
│                  │124 │ Client XYZ  │ €300    │ 12/03   │ Validé │   │
│                  │123 │ Nouveau Cl. │ €250    │ 10/03   │ Attente│   │
│                  │... │ ...         │ ...     │ ...     │ ...    │   │
│                  │                                                  │   │
│                  │ [Voir Toutes les Factures →]                   │   │
│                  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Composants**:
- **Header**: "DASHBOARD - [User Name]" + texte accueil
- **Stats Box**: 4 métriques (3 colonnes)
  - Factures créées (mois)
  - Factures en attente
  - Factures payées
  - CA total / À payer / Payé
- **Actions Rapides**: 4 buttons (2x2 grid)
  - Nouvelle facture
  - Nouveau client
  - Sync URSSAF
  - Voir rapprochement
- **Table Récente**: 10 dernières factures
  - Colonne: # | Client | Montant | Date | Statut
  - Clickable rows → détail facture
- **Footer**: "Voir Toutes les Factures →" link

**Données Affichées**:
- Nombre factures mois courant
- Nombre factures en attente validation
- Nombre factures payées
- CA total, montant en attente, montant payé
- Liste 10 factures récentes (id, client, montant, date, statut)

**Actions Disponibles**:
- [+ Nouvelle Facture] → `/invoices/create`
- [+ Nouveau Client] → `/clients/create`
- [Sync URSSAF] → POST endpoint avec HTMX swap
- [Voir Rapprochement] → `/reconciliation`
- Click row → `/invoices/{id}` (détail)
- [Voir Toutes] → `/invoices` (liste complète)

**États**:
- **Loading**: Skeleton loaders pour stats + table
- **Empty** (aucune facture): "Aucune facture pour le moment. [Créer la première]"
- **Error**: Message erreur sync URSSAF avec retry button
- **Normal**: Données visibles, actions activées

**HTMX Interactions**:
- `hx-trigger="load"` → auto-load stats on page load
- `hx-trigger="every 4h"` → auto-sync statuts factures (polling)
- `hx-swap="innerHTML"` → update stats box silencieusement
- `hx-indicator` → spinner sur bouton Sync

**Navigation**:
- Sidebar click "Dashboard" → `/`
- Accueil après login

---

### 3. Factures - Liste

**URL**: `/invoices`
**Rôle**: Vue toutes factures avec filtres et actions en masse
**Technologie**: FastAPI SSR + table server-side + HTMX filtering

**Wireframe**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐ FACTURES                                           │
│ │  SAP Fact.   │                                                    │
│ │              │ > Dashboard > Factures                             │
│ │ • Dashboard  │                                                    │
│ │ • Factures   │ [+ Nouvelle Facture]  [Export CSV]                │
│ │ • Clients    │                                                    │
│ │ • Rappro.    │ ┌─ FILTRES ─────────────────────────────────────┐ │
│ │              │ │ Status: [Tous ▼]  Client: [______]  Mois: [__▼]│ │
│ │              │ │ [Appliquer Filtres]                             │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │ ────────────│                                                    │
│ │ • Paramètres│ ┌────────────────────────────────────────────────┐ │
│ │              │ │ #   │ Client    │ Montant│Date    │Status    │ │
│ │              │ ├────────────────────────────────────────────────┤ │
│ │              │ │123  │ ABC Corp  │ €300   │14/03   │ ✓ Payée  │ │
│ │              │ │124  │ XYZ Ltd   │ €250   │12/03   │ ✓ Validé │ │
│ │              │ │125  │ New Cust  │ €400   │10/03   │ ⏳ Attente│ │
│ │              │ │126  │ ABC Corp  │ €150   │09/03   │ ✓ Payée  │ │
│ │              │ │127  │ Test Co   │ €500   │08/03   │ ❌ Erreur │ │
│ │              │ │128  │ ABC Corp  │ €180   │07/03   │ ✓ Payée  │ │
│ │              │ │129  │ Another   │ €290   │06/03   │ ✓ Validé │ │
│ │              │ │...  │ ...       │ ...    │ ...    │ ...      │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ Pagination: [< Préc] Page 1/3 [Suiv >]            │
│ │              │                                                    │
│ │              │ Affichage: 25 factures par page                   │
│ │              │                                                    │
│ └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Composants**:
- **Breadcrumbs**: `Dashboard > Factures`
- **Titre**: "FACTURES" (24px)
- **Action buttons**:
  - [+ Nouvelle Facture] (primary, blue)
  - [Export CSV] (secondary)
- **Filter Panel**:
  - Dropdown Status (Tous, Attente, Validé, Payé, Erreur)
  - Input Client (autocomplete avec HTMX)
  - Dropdown Mois (Tous, Janvier, Février, ...)
  - Button [Appliquer Filtres]
  - Button [Réinitialiser] (secondary)
- **Table**:
  - Headers: # | Client | Montant | Date | Statut
  - Rows clickable (hover highlight)
  - Badges statut avec couleurs sémantiques
- **Pagination**:
  - Prev/Next links
  - "Page X/Y"
  - Items per page selector (25/50/100)

**Données Affichées**:
- Invoice #
- Client name
- Amount (HT ou TTC, préciser)
- Date (DD/MM format)
- Status badge

**Actions Disponibles**:
- Click row → `/invoices/{id}` (détail)
- [+ Nouvelle Facture] → `/invoices/create`
- [Export CSV] → POST endpoint, download file
- Filter + apply → GET `/invoices?status=...&client=...&month=...`
- Pagination links → GET `/invoices?page=...`

**États**:
- **Empty**: "Aucune facture trouvée. [Créer une nouvelle]"
- **Loading**: Table skeleton + spinner
- **Filtered**: Affiche filtre appliqué, bouton [Réinitialiser]
- **Normal**: Toutes données visibles

**HTMX Interactions**:
- `hx-trigger="change"` sur filter inputs → auto-apply filters (swap table body)
- `hx-confirm` sur export → "Exporter N factures en CSV?"
- Pagination: `hx-boost` sur links (replace table section)

**Navigation**:
- Sidebar "Factures" → `/invoices`
- From dashboard "Voir Toutes" link
- From invoice detail [Retour Liste] button

---

### 4. Factures - Créer/Modifier

**URL**: `/invoices/create` (créer) | `/invoices/{id}/edit` (modifier)
**Rôle**: Formulaire création/modification facture
**Technologie**: FastAPI SSR + Jinja2 forms + client-side validation + HTMX client autocomplete

**Wireframe (Créer)**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐ CRÉER FACTURE                                      │
│ │  SAP Fact.   │                                                    │
│ │              │ > Dashboard > Factures > Créer                     │
│ │ • Dashboard  │                                                    │
│ │ • Factures   │ ┌────────────────────────────────────────────────┐ │
│ │ • Clients    │ │ CLIENT                                         │ │
│ │ • Rappro.    │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ Sélectionner client ou créer nouveau     │  │ │
│ │              │ │ │ [Existing Clients▼]                      │  │ │
│ │              │ │ │ - ABC Corp (email@abc.fr)                │  │ │
│ │              │ │ │ - XYZ Ltd  (contact@xyz.fr)              │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │ Ou: [+ Créer Nouveau Client] (toggle)         │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ DÉTAILS INTERVENTION                          │ │
│ │              │ │                                                │ │
│ │              │ │ Date début:  [DD/MM/YYYY ▼]                   │ │
│ │              │ │ Date fin:    [DD/MM/YYYY ▼]                   │ │
│ │              │ │                                                │ │
│ │              │ │ Type unité:  ○ Heures  ○ Forfait              │ │
│ │              │ │ Quantité:    [_______] (heures ou nb)         │ │
│ │              │ │                                                │ │
│ │              │ │ Nature service (code URSSAF):                 │ │
│ │              │ │ [Sélectionner▼]                              │ │
│ │              │ │ - 001: Cours individuels                     │ │
│ │              │ │ - 002: Tutorat                               │ │
│ │              │ │ - 003: Aide aux devoirs                      │ │
│ │              │ │                                                │ │
│ │              │ │ Description:                                  │ │
│ │              │ │ ┌──────────────────────────────────────────┐ │ │
│ │              │ │ │ Cours particulier maths, niveau 3e      │ │ │
│ │              │ │ └──────────────────────────────────────────┘ │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ MONTANTS                                       │ │
│ │              │ │                                                │ │
│ │              │ │ Montant HT:   [_________] €                   │ │
│ │              │ │ Taux TVA:     [Exempté ▼] (6%, 20%, etc)      │ │
│ │              │ │ Montant TTC:  €____ (auto-calculated)         │ │
│ │              │ │                                                │ │
│ │              │ │ ☐ Générer PDF après soumission                │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ VALIDATION AVANT SOUMISSION                  │ │
│ │              │ │ ☑ Client sélectionné      ✓                   │ │
│ │              │ │ ☑ Dates remplies          ✓                   │ │
│ │              │ │ ☑ Quantité > 0            ✓                   │ │
│ │              │ │ ☑ Montant HT valide       ✓                   │ │
│ │              │ │ ☑ Nature URSSAF définie   ⚠ (warning)         │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ [Enregistrer Brouillon]  [Enregistrer et Soumettre] │
│ │              │ [Annuler]                                          │
│ │              │                                                    │
│ └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Composants**:
- **Section CLIENT**:
  - Dropdown "Sélectionner client" avec HTMX autocomplete
  - Toggle "[+ Créer Nouveau Client]" → affiche inline form
    - Nom client
    - Email
    - SIRET/SIREN (optional)
    - Téléphone (optional)

- **Section DÉTAILS INTERVENTION**:
  - Date début picker (DD/MM/YYYY ou calendar)
  - Date fin picker
  - Radio "Type unité" (Heures vs Forfait)
  - Input "Quantité" (number, min 0.5 step 0.5)
  - Dropdown "Nature service" (avec codes URSSAF)
  - Textarea "Description" (200 chars max, counter)

- **Section MONTANTS**:
  - Input "Montant HT" (currency, decimal)
  - Dropdown "Taux TVA" (Exempté, 6%, 20%, autre)
  - Display "Montant TTC" (read-only, auto-calculated)
  - Checkbox "Générer PDF après soumission"

- **Section VALIDATION**:
  - Checklist visuelle (✓/✗/⚠) des pré-requis URSSAF
  - Messages d'aide contextuels

- **Buttons**:
  - [Enregistrer Brouillon] (primary, grey)
  - [Enregistrer et Soumettre] (primary, green) — si validation OK
  - [Annuler] (secondary, text)

**Données Affichées**:
- Client dropdown + new client form
- Date début/fin
- Type unité (radio)
- Quantité
- Nature service code
- Description
- Montant HT
- TVA rate
- Montant TTC (calculated)

**Actions Disponibles**:
- Select client → load client details (HTMX)
- Toggle "Créer nouveau client" → show inline form
- Change montant HT → recalc TTC (JS ou HTMX)
- Select TVA rate → recalc TTC
- Submit "Enregistrer Brouillon" → POST `/invoices` state=DRAFT
- Submit "Enregistrer et Soumettre" → POST `/invoices` + POST URSSAF API
- Cancel → go back to `/invoices` (confirm if unsaved)

**États**:
- **New**: Tous champs vides, sauf client pré-rempli si vient de client detail
- **Edit**: Tous champs pré-remplis, (modifié = ◆ badge sur titre)
- **Validating**: Spinner sur validation checklist
- **Submitted**: Redirect vers détail facture avec toast "Facture créée et soumise"
- **Error**: Message erreur spécifique (client manquant, etc)

**Validation**:
- **Client**: requis
- **Dates**: requis, date fin >= date début
- **Quantité**: > 0
- **Montant HT**: > 0
- **Nature URSSAF**: requis si soumission, warning sinon
- **Description**: optional
- Erreurs affichées inline (border rouge + help text)

**HTMX Interactions**:
- Client dropdown: `hx-trigger="input"` → HTMX GET `/api/clients/search?q=...` (live search)
- Montant TTC recalc: `hx-trigger="change"` on HT ou TVA inputs → POST endpoint recalc (ou JS)
- Nature service dropdown: lazy-load URSSAF codes on focus (once per session)
- New client form toggle: `hx-swap="outerHTML"` to show/hide form

**Navigation**:
- From `/invoices` → [+ Nouvelle Facture]
- From `/invoices/{id}` → [Modifier] button
- [Annuler] → back to previous page (or `/invoices`)

---

### 5. Factures - Détail

**URL**: `/invoices/{id}`
**Rôle**: Vue complète facture, actions URSSAF, PDF download
**Technologie**: FastAPI SSR + weasyprint PDF generation + HTMX live status polling

**Wireframe**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐ FACTURE #125                                       │
│ │  SAP Fact.   │                                                    │
│ │              │ > Dashboard > Factures > #125                      │
│ │ • Dashboard  │                                                    │
│ │ • Factures   │ [Modifier] [Télécharger PDF] [Plus ▼]              │
│ │ • Clients    │                                                    │
│ │ • Rappro.    │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ STATUS: En attente validation  (⏳ depuis 2h)  │ │
│ │              │ │                                                │ │
│ │              │ │ URSSAF ID: URSSAF-2026-03-14-001              │ │
│ │              │ │ Soumise à:  URSSAF (SAP)                      │ │
│ │              │ │ Date soumission: 14/03/2026 10:15             │ │
│ │              │ │                                                │ │
│ │              │ │ Client validation URL: [Afficher URL]          │ │
│ │              │ │ (Envoyer au client via email)                 │ │
│ │              │ │                                                │ │
│ │              │ │ [✉️ Envoyer rappel client]  [🔄 Refresh]      │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ DÉTAILS FACTURE                               │ │
│ │              │ │                                                │ │
│ │              │ │ Numéro:       #125                            │ │
│ │              │ │ Client:       XYZ Ltd (contact@xyz.fr)        │ │
│ │              │ │ Date:         12-14/03/2026                   │ │
│ │              │ │ Nature:       Cours individuels               │ │
│ │              │ │ Quantité:     3 heures                        │ │
│ │              │ │ Description:  Cours maths niveau 2de          │ │
│ │              │ │                                                │ │
│ │              │ │ Montant HT:   €300.00                         │ │
│ │              │ │ TVA (0%):     €0.00                           │ │
│ │              │ │ ──────────────────────                        │ │
│ │              │ │ Montant TTC:  €300.00                         │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ TIMELINE URSSAF                               │ │
│ │              │ │                                                │ │
│ │              │ │ ✓ 14/03 10:15  Facture soumise à URSSAF       │ │
│ │              │ │ ✓ 14/03 10:20  Reçue par URSSAF (ACK)         │ │
│ │              │ │ ⏳ 14/03 10:20  En attente validation client   │ │
│ │              │ │    (Expire dans: 34 heures)                   │ │
│ │              │ │ ◇ 16/03 ?      Paiement URSSAF (si validée)   │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ AUDIT LOG                                     │ │
│ │              │ │                                                │ │
│ │              │ │ 14/03 10:15  Jules: Facture créée (DRAFT)     │ │
│ │              │ │ 14/03 10:17  Jules: Soumise à URSSAF          │ │
│ │              │ │ 14/03 10:20  Système: ACK reçu (status sync)  │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ [Retour Liste]  [Modifier] [Supprimer] (phase 2) │
│ │              │                                                    │
│ └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Composants**:
- **Header avec Actions**:
  - Titre "FACTURE #XXX" (24px)
  - [Modifier] button (secondary)
  - [Télécharger PDF] button (primary)
  - [Plus ▼] dropdown:
    - Dupliquer (créer facture similaire)
    - Télécharger ZIP (PDF + données)
    - Signaler erreur (contact support)
    - (Supprimer en phase 2)

- **Status Card** (highlight color based on status):
  - Badge statut big + timestamp ("En attente validation depuis 2h")
  - URSSAF ID
  - Soumise à (date, heure)
  - Client validation URL (clickable, copy-to-clipboard)
  - [✉️ Envoyer rappel client] button
  - [🔄 Refresh] button (manual status sync)

- **Details Section**:
  - 2-column layout
  - Left: Numéro, Client, Dates
  - Right: Nature, Quantité, Description
  - Bottom: Montants (HT, TVA, TTC) with totals

- **Timeline URSSAF**:
  - Vertical timeline avec checkmarks/spinners
  - Events: submission, ACK, validation client, payment
  - Time remaining or deadline

- **Audit Log** (collapsible):
  - Qui, quand, quoi (read-only)
  - Tous modifications tracées

- **Footer Buttons**:
  - [Retour Liste]
  - [Modifier]
  - [Supprimer] (phase 2, soft delete)

**Données Affichées**:
- Invoice number, status, URSSAF ID
- Client details
- Intervention dates, nature, quantity
- Description
- Amount details (HT, TVA, TTC)
- URSSAF submission timestamp
- Client validation URL
- Timeline events
- Audit log entries

**Actions Disponibles**:
- [Modifier] → `/invoices/{id}/edit`
- [Télécharger PDF] → GET `/invoices/{id}/pdf` (download weasyprint PDF)
- [✉️ Envoyer rappel] → POST endpoint + HTMX toast "Email envoyé"
- [🔄 Refresh] → POST `/invoices/{id}/sync` → HTMX swap status section
- [Dupliquer] → POST `/invoices/{id}/duplicate` → redirect `/invoices/create` pre-filled
- [Retour Liste] → `/invoices`

**États**:
- **Draft**: Status "Brouillon", only [Modifier] + [Supprimer] available
- **Submitted**: Status "Soumise", [Refresh] + [Email rappel] active, timeline visible
- **Waiting**: Status "En attente", countdown visible, email button prominent
- **Validated**: Status "Validée", timeline shows client validation ✓
- **Paid**: Status "Payée", amount highlight green, timeline complete
- **Error**: Status "Erreur", red highlight, error message + [Modifier] to correct
- **Loading** (sync): Spinner on [Refresh] button

**HTMX Interactions**:
- `hx-trigger="load"` → auto-load status section on page load
- `hx-trigger="every 4h"` → auto-sync status (background poll)
- `hx-swap="innerHTML"` → update status card + timeline silencieusement
- `hx-confirm` on "Envoyer rappel" → "Envoyer email de rappel au client?"
- Refresh button: `hx-indicator` spinner

**Navigation**:
- From `/invoices` → click row
- From `/invoices/create` → success redirect
- Breadcrumbs → back to `/invoices`

**Accessibilité**:
- Status card: aria-live="polite" for status updates
- Timeline: ordered list `<ol>` for semantics
- Copy-to-clipboard button: keyboard accessible (Enter)

---

### 6. Clients - Liste

**URL**: `/clients`
**Rôle**: Vue tous clients, actions gestion
**Technologie**: FastAPI SSR + HTMX search + soft delete confirmation

**Wireframe**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐ CLIENTS                                            │
│ │  SAP Fact.   │                                                    │
│ │              │ > Dashboard > Clients                              │
│ │ • Dashboard  │                                                    │
│ │ • Factures   │ [+ Nouveau Client]  [Importer CSV] (phase 2)       │
│ │ • Clients    │                                                    │
│ │ • Rappro.    │ ┌─ RECHERCHE ────────────────────────────────────┐ │
│ │              │ │ Chercher: [_____________]    [X Réinitialiser] │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ Nom            │ Email              │ Nb Fact. │ │
│ │              │ ├────────────────────────────────────────────────┤ │
│ │              │ │ ABC Corp       │ contact@abc.fr     │ 8 (€2400)│ │
│ │              │ │ XYZ Ltd        │ contact@xyz.fr     │ 3 (€750) │ │
│ │              │ │ New Customer   │ new@example.com    │ 1 (€300) │ │
│ │              │ │ Another Org    │ hello@another.com  │ 2 (€600) │ │
│ │              │ │ ...            │ ...                │ ...      │ │
│ │              │                                                    │
│ │              │ [Pagination]                                       │
│ │              │                                                    │
│ │              │ Affichage: 50 clients par page                     │
│ │              │ Total: 12 clients                                  │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ Clic sur client pour: voir détail, modifier,  │ │
│ │              │ │ ou archiver (soft delete).                    │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Composants**:
- **Titre**: "CLIENTS" (24px)
- **Buttons**:
  - [+ Nouveau Client] (primary)
  - [Importer CSV] (secondary, phase 2)
- **Search Bar**:
  - Input text (HTMX trigger on input)
  - [X Réinitialiser] button (clear search)
- **Table**:
  - Columns: Nom | Email | Nb Factures (total montant)
  - Rows clickable (hover highlight)
  - Soft-deleted clients: grisés avec "Archivé"
- **Pagination**: standard

**Données Affichées**:
- Client name
- Email address
- Number of invoices + total amount

**Actions Disponibles**:
- Click row → `/clients/{id}` (détail)
- [+ Nouveau Client] → `/clients/create`
- Search → GET `/clients?search=...` (HTMX swap table)
- [X Réinitialiser] → GET `/clients` (reload)

**États**:
- **Empty**: "Aucun client encore. [+ Créer le premier]"
- **Searched**: Affiche résultats filtrés
- **Normal**: Tous clients

**HTMX Interactions**:
- Input search: `hx-trigger="input debounce:500ms"` → HTMX GET and swap table
- Rows: `hx-boost` for navigation to client detail

**Navigation**:
- Sidebar "Clients" → `/clients`

---

### 7. Clients - Créer/Modifier

**URL**: `/clients/create` | `/clients/{id}/edit`
**Rôle**: Formulaire création/modification client
**Technologie**: FastAPI SSR + Jinja2 forms

**Wireframe**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐ NOUVEAU CLIENT                                     │
│ │  SAP Fact.   │                                                    │
│ │              │ > Dashboard > Clients > Créer                      │
│ │ • Dashboard  │                                                    │
│ │ • Factures   │ ┌────────────────────────────────────────────────┐ │
│ │ • Clients    │ │ INFORMATIONS CLIENT                            │ │
│ │ • Rappro.    │ │                                                │ │
│ │              │ │ Nom client: *                                  │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [Nom Entreprise ou Particulier]        │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ Email: *                                       │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [email@example.com]                    │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ Téléphone:                                     │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [+33 6 XX XX XX XX]                    │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ SIRET/SIREN (si entreprise):                  │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [14 chiffres ou 9 chiffres]            │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ Adresse (optionnel):                           │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [Rue, numéro]                          │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ Code Postal:  [_____] Ville:  [__________]   │ │
│ │              │ │                                                │ │
│ │              │ │ Notes (optionnel):                             │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [Ex: Tarif négocié, horaires flexibles] │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ * = champs requis                              │ │
│ │              │ │                                                │ │
│ │              │ │ [Enregistrer] [Annuler]                       │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Composants**:
- **Title**: "NOUVEAU CLIENT" (24px) ou "MODIFIER CLIENT" si édition
- **Form Inputs**:
  - Nom client (required, max 150 chars)
  - Email (required, must be valid)
  - Téléphone (optional, format E.164)
  - SIRET/SIREN (optional, validation format)
  - Adresse (optional)
  - Code Postal + Ville (optional, linked)
  - Notes (optional, textarea)
- **Buttons**:
  - [Enregistrer] (primary)
  - [Annuler] (secondary)

**Données Affichées**:
- Same as form inputs

**Actions Disponibles**:
- Submit form → POST `/clients` (create) or PATCH `/clients/{id}` (update)
- Cancel → back to `/clients`

**États**:
- **New**: Champs vides, title "NOUVEAU CLIENT"
- **Edit**: Champs pré-remplis, title "MODIFIER CLIENT"
- **Loading**: Spinner on [Enregistrer], disabled
- **Success**: Toast "Client enregistré", redirect `/clients/{id}` (nouveau) ou `/clients` (modifié)
- **Error**: Affiche erreur inline (ex: email doublon, format SIRET invalide)

**Validation**:
- Nom: required, max 150 chars
- Email: required, valid email format, unique
- SIRET: if provided, valid 14-digit format
- SIREN: if provided, valid 9-digit format
- Phone: if provided, valid phone format
- Errors displayed inline with red borders

**Navigation**:
- From `/clients` → [+ Nouveau Client]
- From `/clients/{id}` → [Modifier] button
- [Annuler] → `/clients`

---

### 8. Rapprochement Bancaire

**URL**: `/reconciliation`
**Rôle**: Matcher transactions URSSAF avec paiements Swan
**Technologie**: FastAPI SSR + HTMX polling + Swan GraphQL sync

**Wireframe**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐ RAPPROCHEMENT BANCAIRE                             │
│ │  SAP Fact.   │                                                    │
│ │              │ > Dashboard > Rapprochement                        │
│ │ • Dashboard  │                                                    │
│ │ • Factures   │ ┌─ SYNCHRONISATION ──────────────────────────────┐ │
│ │ • Clients    │ │ Dernière synchro: 14/03 10:20 (il y a 5 min)   │ │
│ │ • Rappro.    │ │ [🔄 Synchroniser maintenant]  [Paramètres Swan]│ │
│ │              │ │ Status: OK (22 transactions chargées)          │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ FACTURES EN ATTENTE PAIEMENT                  │ │
│ │              │ │                                                │ │
│ │              │ │ #  │ Client   │ Montant │ Date URSSAF│ Status │ │
│ │              │ ├────────────────────────────────────────────────┤ │
│ │              │ │121 │ ABC Corp │ €300    │ 14/03       │ ⏳    │ │
│ │              │ │122 │ XYZ Ltd  │ €250    │ 12/03       │ ⏳    │ │
│ │              │ │123 │ NewCo    │ €400    │ 10/03       │ ⏳    │ │
│ │              │ │                                                │ │
│ │              │ │ (3 factures en attente)                         │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ TRANSACTIONS SWAN RÉCENTES                    │ │
│ │              │ │                                                │ │
│ │              │ │ Date  │ Débit │ Crédit │ Description    │ Match│ │
│ │              │ ├────────────────────────────────────────────────┤ │
│ │              │ │14/03  │       │ €300   │ URSSAF SAP #121│ ✓   │ │
│ │              │ │12/03  │       │ €250   │ URSSAF SAP #122│ ✓   │ │
│ │              │ │10/03  │       │ €400   │ Virement URSSAF│ ✓   │ │
│ │              │ │09/03  │ €100  │        │ Client refund  │ ✗   │ │
│ │              │ │                                                │ │
│ │              │ │ [Voir Toutes les Transactions]                 │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │ STATISTIQUES MOIS COURANT                     │ │
│ │              │ │                                                │ │
│ │              │ │ Paiées (URSSAF): 5 factures = €1800           │ │
│ │              │ │ En attente:      3 factures = €950            │ │
│ │              │ │ Imputables Swan: €1800 (100% matchées)        │ │
│ │              │ │ Différence:      €0 (équilibré)               │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ [Exporter rapport rapprochement]  [Voir logs]     │ │
│ │              │                                                    │
│ └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Composants**:
- **Sync Status Card**:
  - "Dernière synchro: [timestamp]"
  - [🔄 Synchroniser maintenant] button (with HTMX)
  - [Paramètres Swan] link → `/settings#swan` (optional)
  - Status message + count ("OK, 22 transactions")

- **Factures en Attente**:
  - Table: # | Client | Montant | Date URSSAF | Statut
  - Rows: factures non encore payées
  - If empty: "Toutes les factures attendues sont payées! 🎉"

- **Transactions Swan Récentes**:
  - Table: Date | Débit | Crédit | Description | Match (✓/✗)
  - Rows clickable (details Swan txn)
  - Show match indicator (if automatically matched to invoice)
  - Link [Voir Toutes]

- **Statistiques**:
  - Paiées (URSSAF): nb + montant
  - En attente: nb + montant
  - Imputables Swan: montant + % matchées
  - Différence: montant (highlight red if non-zero)

- **Buttons**:
  - [Exporter rapport rapprochement] → CSV/PDF download
  - [Voir logs] → show recent sync logs (modal ou page)

**Données Affichées**:
- Last sync timestamp
- Pending invoices count + amounts
- Recent Swan transactions
- Match status for each transaction
- Monthly statistics

**Actions Disponibles**:
- [🔄 Synchroniser] → POST `/reconciliation/sync` (HTMX)
  - Triggers Swan GraphQL fetch
  - Triggers URSSAF status polling
  - Auto-matches transactions
  - Updates page with results
- Click transaction row → modal with Swan transaction details
- [Exporter rapport] → POST `/reconciliation/export` (download)
- [Voir logs] → GET `/reconciliation/logs` (modal)
- [Paramètres Swan] → `/settings#swan` (add Swan API key)

**États**:
- **Empty**: No pending invoices (success message)
- **Syncing**: Spinner on [Synchroniser], disable button
- **Synced**: Updated timestamp, results shown
- **Error**: "Swan connection failed" + retry button
- **Unmatched**: Red highlight on unmatched transactions with manual match option (phase 2)

**HTMX Interactions**:
- [🔄 Synchroniser] button: `hx-post="/reconciliation/sync"` with `hx-indicator`
- Response: `hx-swap="innerHTML"` on status card + transactions section
- Auto-sync: `hx-trigger="every 1h"` for background polling
- Modal: `hx-target="#modal"` for transaction details

**Navigation**:
- Sidebar "Rapprochement" → `/reconciliation`
- From dashboard [Voir Rapprochement] link
- Context: financial view, separate from invoicing flow

---

### 9. Paramètres

**URL**: `/settings`
**Rôle**: Configuration utilisateur, intégrations, logo upload
**Technologie**: FastAPI SSR + file upload (weasyprint) + secrets encryption

**Wireframe**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐ PARAMÈTRES                                         │
│ │  SAP Fact.   │                                                    │
│ │              │ > Dashboard > Paramètres                           │
│ │ • Dashboard  │                                                    │
│ │ • Factures   │ ┌─ TABS ────────────────────────────────────────┐ │
│ │ • Clients    │ │ [Profil] [Logo] [URSSAF] [Swan] [Sécurité]   │ │
│ │ • Rappro.    │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ TAB: PROFIL                                        │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │                                                │ │
│ │              │ │ Prénom Nom: *                                  │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [Jules Willard]                        │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ Email de contact: *                            │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [jules@example.com]                    │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ Téléphone: *                                   │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [+33 6 XX XX XX XX]                    │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ Mot de passe:                                  │ │
│ │              │ │ [Changer mot de passe]                        │ │
│ │              │ │                                                │ │
│ │              │ │ [Enregistrer] [Annuler]                       │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ TAB: LOGO                                          │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │                                                │ │
│ │              │ │ [Logo Actuel]                                  │ │
│ │              │ │   ┌─────────────────┐                         │ │
│ │              │ │   │   [LOGO IMG]    │                         │ │
│ │              │ │   └─────────────────┘                         │ │
│ │              │ │                                                │ │
│ │              │ │ [Uploader nouveau logo]  [Supprimer]           │ │
│ │              │ │                                                │ │
│ │              │ │ Format: JPG, PNG. Max 2 MB. Aspect ratio 16:9. │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ TAB: URSSAF                                        │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │                                                │ │
│ │              │ │ Mode URSSAF:  ○ Sandbox  ○ Production          │ │
│ │              │ │                                                │ │
│ │              │ │ ID Prestataire (optionnel):                    │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [Si tu as déjà un ID URSSAF]          │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ OAuth Credentials (AUTO-Gérés, non éditables): │ │
│ │              │ │ • Portefeuille ID: [XXXXX] (set after 1st auth)│ │
│ │              │ │ • Access Token expire: 14/03/2026 23:59       │ │
│ │              │ │ • [Réautoriser] (si expiré)                  │ │
│ │              │ │                                                │ │
│ │              │ │ [Enregistrer]                                  │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ TAB: SWAN                                          │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │                                                │ │
│ │              │ │ Statut connexion: ❌ Non configuré             │ │
│ │              │ │                                                │ │
│ │              │ │ Swan API Key: *                                │ │
│ │              │ │ ┌──────────────────────────────────────────┐  │ │
│ │              │ │ │ [••••••••••••••••••••••]               │  │ │
│ │              │ │ │ [Voir/Masquer]                         │  │ │
│ │              │ │ └──────────────────────────────────────────┘  │ │
│ │              │ │                                                │ │
│ │              │ │ [Tester connexion]  [Obtenir clé]              │ │
│ │              │ │                                                │ │
│ │              │ │ [Enregistrer]                                  │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ TAB: SÉCURITÉ                                      │
│ │              │ ┌────────────────────────────────────────────────┐ │
│ │              │ │                                                │ │
│ │              │ │ Authentification à deux facteurs (2FA):        │ │
│ │              │ │ ☐ Activée (Phase 2)                           │ │
│ │              │ │                                                │ │
│ │              │ │ Audit Log:                                     │ │
│ │              │ │ [Voir audit log complet]                       │ │
│ │              │ │ • 14/03 10:20 Jules: Création facture #125    │ │
│ │              │ │ • 14/03 10:17 Jules: Soumission URSSAF        │ │
│ │              │ │                                                │ │
│ │              │ │ Danger Zone:                                   │ │
│ │              │ │ [Déconnexion de tous les appareils]           │ │
│ │              │ │ [Télécharger mes données]  (RGPD)             │ │
│ │              │ │ [Supprimer mon compte]  (phase 2)             │ │
│ │              │ │                                                │ │
│ │              │ └────────────────────────────────────────────────┘ │
│ │              │                                                    │
│ │              │ [Enregistrer] [Annuler]                           │
│ │              │                                                    │
│ │              │ [Déconnexion]                                     │
│ │              │                                                    │
│ └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Composants**:
- **Tabs**:
  - Profil
  - Logo
  - URSSAF
  - Swan
  - Sécurité

- **TAB: PROFIL**:
  - Input: Prénom Nom
  - Input: Email de contact
  - Input: Téléphone
  - Link: [Changer mot de passe] → modal (old pwd, new pwd, confirm)
  - Buttons: [Enregistrer], [Annuler]

- **TAB: LOGO**:
  - Current logo preview (if exists)
  - File upload input (drag & drop)
  - Buttons: [Uploader], [Supprimer]
  - Requirements text (format, size, aspect ratio)

- **TAB: URSSAF**:
  - Radio: Mode Sandbox vs Production
  - Input: ID Prestataire (optional, editable only if not yet authenticated)
  - Display: Portefeuille ID, Access Token expiry
  - Button: [Réautoriser] (if token expired)
  - Button: [Enregistrer]

- **TAB: SWAN**:
  - Status indicator (configured/not configured)
  - Input: Swan API Key (password type, masked)
  - Toggle: [Voir/Masquer]
  - Buttons: [Tester connexion], [Obtenir clé] (link to Swan docs)
  - Button: [Enregistrer]

- **TAB: SÉCURITÉ**:
  - Checkbox: 2FA (disabled for MVP)
  - Audit Log section (read-only, collapsible)
  - Danger Zone:
    - [Déconnexion de tous les appareils]
    - [Télécharger mes données] (RGPD)
    - [Supprimer mon compte] (phase 2)
  - Footer: [Déconnexion] button

**Données Affichées**:
- User profile (name, email, phone)
- Logo image
- URSSAF credentials status (not secrets, only public info)
- Swan connection status
- Audit log entries

**Actions Disponibles**:
- **Profil**: Update name, email, phone → POST `/settings/profile`
- **Logo**: Upload new logo → POST `/settings/logo` (multipart)
- **Logo**: Delete logo → DELETE `/settings/logo`
- **URSSAF**: Select mode (sandbox/prod) → POST `/settings/urssaf`
- **URSSAF**: Reauthorize → redirect to URSSAF OAuth flow
- **Swan**: Update API key → POST `/settings/swan`
- **Swan**: Test connection → POST `/settings/swan/test` (HTMX)
- **Sécurité**: Logout all devices → POST `/auth/logout-all`
- **Sécurité**: Download data → GET `/export/data` (JSON/CSV)
- **Sécurité**: View audit log → GET `/settings/audit-log` (modal)
- **Main footer**: [Déconnexion] → GET `/logout`

**États**:
- **Loading**: Spinner on save buttons
- **Saved**: Toast "Paramètres enregistrés"
- **Error**: Message erreur inline (ex: invalid API key format)
- **Logo uploading**: Progress bar (nice-to-have)
- **Swan testing**: Spinner while testing connection

**Validation**:
- Name: required, max 150 chars
- Email: required, valid email format
- Phone: valid phone format if provided
- URSSAF mode: required
- Swan API key: required if using Swan, valid format
- Logo: max 2 MB, JPG/PNG only, validated server-side

**HTMX Interactions**:
- [Tester connexion] Swan: `hx-post="/settings/swan/test"` with `hx-indicator` spinner
- Response shows "✓ Connexion OK" or error message
- File upload: `hx-encoding="multipart/form-data"`

**Navigation**:
- Topbar "⚙️ Paramètres" → `/settings`
- From anywhere via settings icon

---

## Composants Réutilisables

### Buttons

Tous les buttons suivent ce style:

**Primaire** (actions principales):
```html
<button class="btn btn-primary">Action</button>
```

**Secondaire** (actions alternatives):
```html
<button class="btn btn-secondary">Alternative</button>
```

**Success** (validation, submission):
```html
<button class="btn btn-success">Valider</button>
```

**Danger** (suppression, risque):
```html
<button class="btn btn-danger">Supprimer</button>
```

**Disabled**:
```html
<button class="btn btn-primary" disabled>Désactivé</button>
```

### Status Badges

```html
<!-- Draft -->
<span class="badge badge-draft">Brouillon</span>

<!-- Submitted -->
<span class="badge badge-submitted">Soumise</span>

<!-- Waiting -->
<span class="badge badge-waiting">En attente</span>

<!-- Validated -->
<span class="badge badge-validated">Validée</span>

<!-- Paid -->
<span class="badge badge-paid">Payée</span>

<!-- Error -->
<span class="badge badge-error">Erreur</span>
```

### Form Elements

```html
<!-- Input -->
<div class="form-group">
  <label for="name">Nom *</label>
  <input type="text" id="name" name="name" required>
  <span class="error">Erreur</span>
</div>

<!-- Textarea -->
<div class="form-group">
  <label for="description">Description</label>
  <textarea id="description" name="description" rows="4"></textarea>
</div>

<!-- Select -->
<div class="form-group">
  <label for="status">Statut</label>
  <select id="status" name="status">
    <option value="">-- Sélectionner --</option>
    <option value="draft">Brouillon</option>
    <option value="submitted">Soumise</option>
  </select>
</div>

<!-- Radio -->
<div class="form-group">
  <label>Type unité *</label>
  <label class="radio">
    <input type="radio" name="unit_type" value="hours" required>
    Heures
  </label>
  <label class="radio">
    <input type="radio" name="unit_type" value="forfait">
    Forfait
  </label>
</div>

<!-- Checkbox -->
<label class="checkbox">
  <input type="checkbox" name="agree">
  J'accepte les conditions
</label>
```

### Tables

```html
<table class="table">
  <thead>
    <tr>
      <th>#</th>
      <th>Client</th>
      <th>Montant</th>
      <th>Date</th>
      <th>Statut</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>123</td>
      <td>ABC Corp</td>
      <td>€300</td>
      <td>14/03</td>
      <td><span class="badge badge-paid">Payée</span></td>
    </tr>
  </tbody>
</table>
```

### Cards

```html
<div class="card">
  <div class="card-header">
    <h3>Titre Card</h3>
  </div>
  <div class="card-body">
    Contenu
  </div>
  <div class="card-footer">
    <button class="btn btn-primary">Action</button>
  </div>
</div>
```

### Alerts

```html
<!-- Info -->
<div class="alert alert-info">
  ℹ️ Information
</div>

<!-- Success -->
<div class="alert alert-success">
  ✓ Succès
</div>

<!-- Warning -->
<div class="alert alert-warning">
  ⚠️ Attention
</div>

<!-- Error -->
<div class="alert alert-error">
  ❌ Erreur
</div>
```

---

## États et Transitions

### Invoice State Machine

```
┌─────────┐
│ DRAFT   │ (user creates, not submitted)
└────┬────┘
     │ [Enregistrer et Soumettre]
     ↓
┌─────────────┐
│ SUBMITTED   │ (sent to URSSAF, awaiting client validation)
└────┬────────┘
     │ [Client validates on URSSAF portal]
     ↓
┌─────────────┐
│ VALIDATED   │ (client confirmed, awaiting URSSAF payment)
└────┬────────┘
     │ [URSSAF processes payment]
     ↓
┌─────────────┐
│ PAID        │ (payment received, complete)
└─────────────┘

     ┌────────────────────────┐
     │ [Error during submit]  │
     ↓                        │
┌──────────┐                 │
│ ERROR    │ (needs correction)
└────┬─────┘
     │ [Modify and re-submit]
     ↓ (retries transition to SUBMITTED)
```

### Page Load States

**For all pages**:
```
┌─────────────────┐
│ Initial Request │
└────────┬────────┘
         │
         ↓
┌──────────────────┐
│ Loading Skeleton │ (if > 200ms)
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ Content Rendered │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ Interactive      │ (buttons, forms ready)
└──────────────────┘
```

### Form States

```
┌──────────────┐
│ Empty Form   │ (inputs cleared, ready for input)
└────┬─────────┘
     │ [user types]
     ↓
┌──────────────┐
│ Filled Form  │ (some or all inputs filled)
└────┬─────────┘
     │ [user submits]
     ↓
┌──────────────┐
│ Submitting   │ (button disabled, spinner)
└────┬─────────┘
     │
     ├─→ Success → Toast → Redirect
     │
     └─→ Error → Show error message → allow retry
```

---

## Interactions HTMX

### General HTMX Strategy

**Philosophy**: Server-side rendering + HTMX for interactivity
- No full page reloads for simple actions (filter, sync, etc)
- HTMX makes requests → server returns HTML snippet → swap into page
- Graceful degradation: forms still work without HTMX (POST redirect)

### Common HTMX Patterns

**Pattern 1: Live Search**
```html
<input type="text" name="search"
  hx-trigger="input debounce:500ms"
  hx-get="/clients/search"
  hx-target="#results"
  hx-swap="innerHTML">
```

**Pattern 2: Button Action with Spinner**
```html
<button hx-post="/invoices/sync"
  hx-target="#status-section"
  hx-swap="innerHTML"
  hx-indicator="#spinner">
  🔄 Synchroniser
</button>
<div id="spinner" class="spinner" style="display:none">Loading...</div>
```

**Pattern 3: Confirmation Dialog**
```html
<button hx-post="/invoices/{id}/delete"
  hx-confirm="Êtes-vous sûr de vouloir supprimer cette facture?">
  Supprimer
</button>
```

**Pattern 4: Auto-refresh Every N Hours**
```html
<div hx-trigger="load, every 4h"
  hx-get="/dashboard/stats"
  hx-swap="innerHTML">
  Stats content
</div>
```

**Pattern 5: Modal Form**
```html
<button hx-get="/clients/create"
  hx-target="#modal"
  hx-swap="innerHTML">
  + Nouveau Client
</button>

<div id="modal"></div>
```

### Specific Screen HTMX Usage

**Dashboard**:
- Stats auto-sync every 4 hours (unobtrusive background)
- Click "Sync URSSAF" → POST with spinner

**Invoice List**:
- Filter dropdowns trigger GET with debounce
- Pagination links: `hx-boost` for smooth nav
- Export button confirms before POST

**Invoice Create**:
- Client dropdown: live search on input
- Amount TTC: recalculate on HT/TVA change (optional JS or HTMX)
- Validation checklist: live update as form fills

**Invoice Detail**:
- Refresh button: POST sync with spinner
- Status section: auto-refresh every 4 hours background
- "Envoyer rappel" button: POST with confirmation modal

**Reconciliation**:
- Sync button: POST with spinner, updates transactions table
- Auto-sync: every 1 hour background poll

---

## Guide Accessibilité

### Principes

1. **Contrast**: Minimum 4.5:1 ratio for text (WCAG AA)
2. **Keyboard Navigation**: All interactive elements accessible via Tab, Enter, Escape
3. **Labels**: All inputs must have associated `<label>` elements
4. **Semantic HTML**: Use `<button>`, `<a>`, `<table>`, `<nav>` properly
5. **ARIA**: Add ARIA attributes where needed (aria-label, aria-live, aria-expanded)
6. **Focus**: Visible focus indicator (outline or border)

### Checklist par Écran

**Tous les écrans**:
- [ ] Logo/title visible and clickable (home link)
- [ ] Navigation sidebar accessible and labeled
- [ ] Skip link for keyboard users (optional, nice-to-have)
- [ ] Focus order logical (top to bottom, left to right)
- [ ] Focus visible (outline or border highlight)
- [ ] Error messages linked to form fields

**Forms**:
- [ ] Labels associated with inputs via `<label for="...">`
- [ ] Required fields marked with `*` and `required` attribute
- [ ] Error messages displayed inline with red border
- [ ] Success messages announced to screen readers (aria-live)

**Tables**:
- [ ] Proper `<thead>`, `<tbody>`, `<th>` structure
- [ ] Row headers if needed (row titles)
- [ ] Sortable columns: add `aria-sort` attribute

**Modals**:
- [ ] Focus trapped inside modal (Tab cycles within modal)
- [ ] Escape key closes modal
- [ ] `role="dialog"` and `aria-labelledby` on modal container
- [ ] Close button always visible and accessible

**Dynamic Content (HTMX)**:
- [ ] Use `aria-live="polite"` or `aria-live="assertive"` for dynamic updates
- [ ] Announce loading state to screen readers
- [ ] Announce completion state (success/error)

### Color Contrast Verification

**Text on Light Background**:
- Primary text (#1F2937) on white: 12.4:1 ✓
- Secondary text (#6B7280) on white: 7.1:1 ✓

**Status Badges**:
- Validate each badge color combo against backgrounds
- Test with tools like WebAIM Contrast Checker

### Keyboard Navigation

**Tab order**:
```
Logo (home)
  → Sidebar links
  → Main content links/buttons
  → Footer links
```

**Escape key**: Closes modals, collapses menus

**Enter key**: Submits forms, activates buttons

---

## Responsive Breakdown

### Desktop (≥1280px)

- Sidebar permanent left (200px fixed)
- Main content: full width - sidebar width
- Tables: full columns visible
- Inputs: default width
- Buttons: inline (not stacked)

### Tablet (768px - 1279px)

- Sidebar collapsible (hamburger menu icon top-left)
- Main content: full viewport width when sidebar closed
- Tables: scrollable horizontally if needed
- Inputs: full width on forms
- Buttons: inline if space allows, else stacked

### Mobile (<768px)

- Sidebar: drawer (slide from left)
- Main content: full width
- Tables: simplified (show key columns, hide non-essential)
- Inputs: full width, larger touch targets (44px+ min)
- Buttons: full width stacked

### Images and Icons

- All icons: SVG or system icons (no images)
- Logo: SVG, scales responsively
- Profile images: future (Phase 2), placeholder avatar

---

## Notes Supplémentaires

### Performance

- No heavy JavaScript frameworks (only HTMX + minimal JS)
- Page load: < 2 seconds (measured on 4G)
- Form submission: < 1 second response time
- API calls cached when appropriate (invoices, clients)

### Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- No IE11 support

### Testing Recommendations

**Manual Testing**:
- [ ] Test each screen in desktop, tablet, mobile viewport
- [ ] Test all buttons, links, form submissions
- [ ] Test HTMX interactions (search, sync, filters)
- [ ] Test keyboard navigation (Tab, Enter, Escape)
- [ ] Test form validation (empty fields, invalid formats)
- [ ] Test error states (network errors, validation errors)

**Automated Testing** (Phase 2):
- Unit tests for form validation
- Integration tests for HTMX interactions
- E2E tests for critical flows (create invoice, submit URSSAF)

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 14 Mars 2026 | 1.0 | Initial UX specifications for MVP |

---

**Document**: UX Specifications - SAP-Facture
**Auteur**: Winston (BMAD UX Designer)
**Date Création**: 14 Mars 2026
**Statut**: ✅ MVP Ready
**Language**: Français
**Architecture Reference**: FastAPI SSR + Jinja2 + HTMX + Tailwind CSS
