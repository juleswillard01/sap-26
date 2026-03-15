# Index — Analyse Modèle de Données SAP-Facture

**Analyste** : Claude
**Source** : SCHEMAS.html — SCHEMA 5 ("Modèle de Données — Google Sheets")
**Date** : 15 mars 2026
**Statut** : Analyse complète — 3 documents créés

---

## Documents Créés (This Analysis)

### 1. MODELE-DONNEES-SYNTHESE.md ← **COMMENCER ICI**

**Fichier** : `/home/jules/Documents/3-git/SAP/main/docs/phase1/MODELE-DONNEES-SYNTHESE.md`
**Longueur** : ~3000 mots (8-10 pages)
**Niveau** : Exécutif + Technique

**Contenu** :
- Vue d'ensemble (8 onglets Google Sheets)
- Architecture relationnel (flux données)
- Détail des 8 onglets (colonnes, types, formules)
- Relations entre onglets
- Volumes & performance
- Protections & éditions (matrice)
- 2 cas d'usage complets (scénarios)
- Formules clés (snippets)
- Checklist implémentation
- Résumé TLDR

**Pourquoi lire** : Vue complète en 1 document, prêt pour implémentation immédiate

---

### 2. 00-quick-ref.md

**Fichier** : `/home/jules/Documents/3-git/SAP/main/docs/phase1/00-quick-ref.md`
**Longueur** : ~600 mots (2 pages)
**Niveau** : Démarrage rapide

**Contenu** :
- Les 8 onglets en tableau simple
- Exemples de données numériques
- Matrices éditable vs lecture seule
- Cas d'usage 1, 2, 3 (résumés)
- Volumes
- Lien vers version complète

**Pourquoi lire** : Si tu as 5 minutes, c'est pour toi

---

### 3. formules-sheets.md

**Fichier** : `/home/jules/Documents/3-git/SAP/main/docs/phase1/formules-sheets.md`
**Longueur** : ~1000 mots (3 pages formules)
**Niveau** : Implémentation

**Contenu** :
- Formules Google Sheets ligne par ligne
- Onglet LETTRAGE : scoring (code Excel)
- Onglet BALANCES : agrégations SUMIFS
- Onglet METRICS NOVA : trimestriel
- Onglet COTISATIONS : charges sociales
- Onglet FISCAL IR : simulation IR
- Récapitulatif complexité par onglet
- Notes performance
- Testing checklist

**Pourquoi lire** : Si tu codes les formules Google Sheets

---

### 4. 05-data-model.md (Document Exhaustif)

**Fichier** : `/home/jules/Documents/3-git/SAP/main/docs/phase1/05-data-model.md`
**Longueur** : 1039 lignes (très détaillé)
**Niveau** : Référence complète

**Contenu** :
- Chaque onglet détaillé (15-25 lignes par onglet)
- Contraintes & règles par colonne
- Exemples numériques pour chaque onglet
- Statuts & transitions complètes (machine à états)
- Interdépendances (diagrammes relationnels)
- Cas d'usage détaillés (jour par jour)
- Volumes & croissance (5 ans)
- Formules détaillées avec contexte
- Checklist implémentation Phase 1-2-3

**Pourquoi lire** : Besoin d'une référence exhaustive pour développement

---

## Quoi Lire Quand

### Je suis Jules (non-technique)

1. **00-quick-ref.md** (2 pages, 5 min)
   - Comprendre les 8 onglets
   - Voir des exemples simples

### Je suis développeur (implementation rapide)

1. **MODELE-DONNEES-SYNTHESE.md** (10 pages, 20 min)
   - Vue complète architecture
   - Formules clés à implémenter

2. **formules-sheets.md** (3 pages, 15 min)
   - Code Excel/Sheets spécifique
   - Optimisations performance

3. **05-data-model.md** (référence)
   - Détails quand tu rencontres une question

### Je fais de la code review

1. **MODELE-DONNEES-SYNTHESE.md** (10 pages)
   - Vérifier conformité architecture

2. **05-data-model.md** (sections pertinentes)
   - Vérifier contraintes par onglet

---

## Structure Logique

```
Quoi ? (Vue d'ensemble)
  └─ MODELE-DONNEES-SYNTHESE.md section 1-2

Quoi en détail ? (Chaque onglet)
  └─ MODELE-DONNEES-SYNTHESE.md section 3-4
  └─ 05-data-model.md sections 1-8

Comment implémente-t-on ? (Formules)
  └─ formules-sheets.md
  └─ MODELE-DONNEES-SYNTHESE.md section 8

Quand on a une question spécifique ?
  └─ 05-data-model.md (table de matières)
  └─ Recherche par onglet/colonne
```

---

## Points Clés à Retenir

### Les 8 Onglets

| # | Nom | Type | Rôle |
|---|-----|------|------|
| 1 | CLIENTS | Data brute | Qui tu factures |
| 2 | FACTURES | Data brute | Tes factures (cycle de vie) |
| 3 | TRANSACTIONS | Data brute | Virements reçus (Swan) |
| 4 | LETTRAGE | Calculé | Matching auto factures ↔ virements |
| 5 | BALANCES | Calculé | KPIs mensuels (CA, solde, etc.) |
| 6 | METRICS NOVA | Calculé | Reporting trimestriel URSSAF |
| 7 | COTISATIONS | Calculé | Charges sociales (25.8%) |
| 8 | FISCAL IR | Calculé | Simulation impôt annuel |

### Flux Données Clé

```
Clients + Factures + Transactions (brutes, éditables)
    ↓ (formules)
Lettrage (score, matching)
    ↓
Balances (KPIs mensuels)
Metrics NOVA (trimestriel)
Cotisations (charges)
Fiscal IR (simulation IR)
```

### Scoring Lettrage (100 pts max)

```
Montant exact   → +50
Même jour       → +30
Libellé URSSAF  → +20
─────────────────────
Score >= 80     → AUTO (confiance)
50-79           → A_VERIFIER (Jules confirme)
< 50            → PAS_DE_MATCH (attendre virement)
```

### Volumes

- **Clients** : 4-10 actifs/mois
- **Factures** : 15-50/mois
- **Transactions** : 10-30/mois
- **Total data** : < 500 KB (Google Sheets handles 10M cells)

---

## Fichiers Associés (Phase 1 Global)

**Autres docs phase1 pertinentes** (créés avant cette analyse):

- `02-billing-flow.md` : Flux facturation (complémente MODELE)
- `03-urssaf-api-requirements.md` : API URSSAF (source de données)
- `06-bank-reconciliation.md` : Lettrage détaillé (complémente section 4)
- `07-invoice-lifecycle.md` : Machine à états (complémente section 3)

**Pour cette analyse, tu peux les ignorer** : MODELE-DONNEES-SYNTHESE.md est auto-suffisant

---

## Tâches Implémentation

### Phase 1 : Google Sheets Setup

- [ ] Créer 8 onglets avec noms exacts
- [ ] Ajouter colonnes (voir MODELE section 3)
- [ ] Implémenter formules (voir formules-sheets.md)
- [ ] Protéger onglets calculés
- [ ] Formats (devise, dates, enums)

**Durée estimée** : 2-3 heures

### Phase 2 : Intégration App

- [ ] SheetsAdapter (gspread API)
- [ ] CRUD Clients, Factures, Transactions
- [ ] Trigger Lettrage (matching)
- [ ] Maj Balances

**Durée estimée** : 1-2 jours

### Phase 3 : Tests & Validation

- [ ] Tests cas d'usage complets
- [ ] Validation formules
- [ ] Performance tests

**Durée estimée** : 1 jour

---

## Questions Fréquentes

**Q: Par où je commence à implémenter ?**
A: MODELE-DONNEES-SYNTHESE.md section 9 (checklist phase 1)

**Q: Où je trouve la formule pour le scoring ?**
A: formules-sheets.md section "LETTRAGE — Scoring" OU MODELE section 8

**Q: Pourquoi 8 onglets et pas une base de données ?**
A: Google Sheets suffisant pour volumes (< 500 KB), plus simple à déployer sans serveur

**Q: Comment ça marche le matching lettrage ?**
A: MODELE section 4 (scoring + fenêtre ±5j) + cas d'usage sections 7

**Q: Quand est-ce que facture devient RAPPROCHE ?**
A: Une fois matchée (lettrage AUTO ou A_VERIFIER confirmé par Jules)

---

## Feedback & Révisions

**Cette analyse (3 documents)** :
- ✅ Complète (8 onglets détaillés)
- ✅ Pragmatique (prêt pour implémentation)
- ✅ Source de vérité : SCHEMAS.html SCHEMA 5
- ⏳ Peut être enrichi avec : exemples screenshots, tests unitaires

---

## Prochaines Étapes (Après cette Analyse)

1. ✅ **Modèle de données analysé**

2. ⏳ **Product Requirements Document (PRD)**
   - User stories (Jules perspective)
   - Acceptance criteria
   - Success metrics

3. ⏳ **Architecture Technique**
   - Python services
   - Google Sheets API integration
   - URSSAF API flow

4. ⏳ **Flux Métier Détaillé**
   - Scénarios étape par étape
   - Décisions (règles métier)

---

**Index créé** : 15 mars 2026
**Analyste** : Claude
**Statut** : 3 documents analysant le modèle de données SAP-Facture
**Qualité** : Prêt pour développement Phase 1
