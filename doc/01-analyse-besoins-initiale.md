# Analyse des Besoins - Solution URSSAF pour Micro-Entreprise SAP

**Date**: 14 mars 2026
**Product Owner**: Sarah (BMAD)
**Status**: Analyse initiale en attente de clarification

---

## 1. Contexte et Hypothèses de Base

### Situation de Jules
- **Statut**: Micro-entrepreneur en Services à la Personne (SAP)
- **Structure**: Solo (opérateur unique)
- **Régime fiscal**: Micro-entreprise (chiffre d'affaires limité ~70k€)
- **Accès API**: OAuth 2.0 URSSAF configuré (Client ID + Client Secret)
- **Comptabilité**: Indy (plateforme en ligne)

### Hypothèses à Tester
1. Jules facture principalement à titre horaire (HEURE) ou forfaitaire (FORFAIT)?
2. Nombre de clients moyen par mois?
3. Fréquence des interventions (factures par mois)?
4. Actuellement, comment facto-t-il? (Excel, papier, autre?)
5. Qui doit valider les factures côté URSSAF (clients, Jules lui-même)?

---

## 2. Décomposition du Problème

### 2.1 Processus Métier Actuel (supposé)

```
[Jules intervient] → [Crée facture] → [Envoie au client] → [Client valide URSSAF]
                                                              ↓
                                        [URSSAF paie Jules 2j après "Payée"]
                                                              ↓
                                           [Indy enregistre paiement]
```

**Points de friction identifiés:**
- Création manuelle de factures (risque d'erreurs format URSSAF)
- Pas de suivi automatisé du statut
- Relance manuelle si client n'a pas validé
- Réconciliation manuel Indy ↔ URSSAF (2 systèmes, 2 statuts)

### 2.2 Domaines Clés

| Domaine | Périmètre Probable | Priorité |
|---------|-------------------|----------|
| **Gestion clients** | Nom, email, SIREN/SIRET, contacts | Moyenne |
| **Création de factures** | Formulaire avec champs URSSAF obligatoires | HAUTE |
| **Submission URSSAF** | Intégration API, gestion erreurs, retry | HAUTE |
| **Suivi statuts** | Dashboard simple : "En attente", "Validée", "Payée" | HAUTE |
| **Notifications** | Email rappel si client n'a pas validé (48h) | Moyenne |
| **Export/Indy** | CSV/JSON pour import Indy | Basse (Phase 2) |
| **Historique** | Archive des factures envoyées | Moyenne |

---

## 3. Scoring Qualité Initial (avant clarification)

Évaluation de notre compréhension actuelle :

### Business Value & Goals: **12/30**
- ✓ Problème clair : simplifier la facturation URSSAF
- ✗ Pas de métriques de succès définies
- ✗ ROI non quantifié

**Gap**: Combien de temps Jules gaspille par mois en gestion facturation?

### Functional Requirements: **10/25**
- ✓ Flux métier général compris
- ✗ Détails des workflows manquent
- ✗ Edge cases non identifiés

**Gap**: Quelle est la fréquence réelle? Quels sont les pires scénarios?

### User Experience: **8/20**
- ✓ Profil utilisateur clair (solo user, faible tech affinity?)
- ✗ Préférences UI non connues
- ✗ Parcours exact pas validé

**Gap**: Jules préfère-t-il CLI, web, mobile? Connexion Indy voulue?

### Technical Constraints: **10/15**
- ✓ API URSSAF connue
- ✓ Tech stack envisagé (OAuth 2.0)
- ✗ Performance / sécurité non définis

**Gap**: Besoin d'audit sécurité des credentials URSSAF?

### Scope & Priorities: **6/10**
- ✓ MVP vaguement tracé
- ✗ Phase 2 floue
- ✗ Dépendances externes non listées

**Gap**: Indy est-elle blocking pour MVP?

---

**Scoring Total : 46/100** ⚠️ *Trop bas — clarification obligatoire*

---

## 4. Questions Clés à Poser à Jules

### A. Volume & Fréquence
1. **Combien de clients différents par mois?** (5, 10, 30+?)
2. **Combien de factures par mois?** (10, 50, 200?)
3. **Montant moyen par facture?** (50€, 500€, 2000€?)
4. **Facturation en heures ou forfait?** (HEURE/FORFAIT URSSAF)
5. **Qui sont les clients?** (particuliers, petites entreprises, collectivités?)

### B. Processus Existant
6. **Actuellement, comment crées-tu les factures?** (Excel, Word, Indy, papier?)
7. **Combien de temps par facture?** (5 min, 30 min, 1h?)
8. **Erreurs URSSAF fréquentes?** (format, données manquantes?)
9. **Comment tu fais le suivi de paiement?** (manuel, email, relance?)

### C. Intégrations
10. **Utilises-tu déjà Indy activement?** (saisie quotidienne, ou juste consultation?)
11. **Veux-tu une synchro auto Indy ↔ URSSAF?** (dépendance sur Indy?)
12. **Besoin d'export pour comptable/expert?** (CSV, PDF, XML?)

### D. Préférences Interface
13. **Préfères-tu : web app, desktop, CLI?**
14. **Un accès par mot de passe, ou OAuth?**
15. **Besoin de mobile (consultation factures) ou desktop suffit?**

### E. Timeline & Autres
16. **Quand veux-tu démarrer facturation URSSAF?** (urgent, 1 mois, flexible?)
17. **Besoin de données historiques import?** (factures existantes à importer?)
18. **As-tu un comptable/expert-comptable qui audit cela?** (implications conformité?)

---

## 5. MVP Préliminaire (à valider avec Jules)

### Scope MVP Phase 1 (Semaines 1-2)

**User Stories Prioritaires:**

1. **Authentification & Sécurité**
   - OAuth 2.0 URSSAF (login, token refresh)
   - Stockage sécurisé credentials (env vars, vault?)

2. **Gestion Clients Minimale**
   - Créer/modifier client (email, SIREN/SIRET)
   - Liste clients existants

3. **Création de Facture**
   - Formulaire web simple
   - Pré-remplissage client
   - Champs obligatoires URSSAF (unit type, dates, nature code)
   - Validation client-side + server-side

4. **Submission URSSAF**
   - Bouton "Envoyer facture"
   - Appel API URSSAF
   - Gestion erreurs / retry
   - Confirmation numéro facture

5. **Dashboard Minimal**
   - Liste factures (dernières 10)
   - Statuts (Brouillon, Envoyée, En attente validation, Payée)
   - Montant total/mois
   - Lien détail facture

### Scope Phase 2 (Post-MVP)
- Notifications email
- Export Indy (CSV)
- Historique complet avec recherche
- Dashboard analytics (CA/mois, moyenne facture)
- Gestion planning interventions
- Intégration API Indy

---

## 6. Risques Identifiés

| Risque | Probabilité | Impact | Mitigation |
|--------|------------|--------|------------|
| Erreurs format API URSSAF → rejets | Haute | Haute | Validation stricte, logs détaillés, test API sandbox |
| Credentials OAuth compromise | Moyenne | Critique | Vault sécurisé, rotation keys, audit logs |
| Clients ne valident pas facture (48h limit) | Moyenne | Moyenne | Email rappel auto à 24h/36h |
| Réconciliation URSSAF vs Indy complexe | Moyenne | Basse | Phase 2, export CSV d'abord |
| Volume croissance rapide | Basse | Moyenne | Architecture scalable dès départ (async jobs) |

---

## 7. Prochaines Étapes

**Pour approfondir l'analyse:**
1. Entretien avec Jules sur les 18 questions clés
2. Consultation API URSSAF Swagger/docs
3. Audit Indy API (capacités export)
4. Prototype UI rapide (wireframes)
5. Définition tech stack + architecture
6. Scoring qualité révisé post-clarification

---

**Document**: Analyse initiale
**Auteur**: Sarah (BMAD Product Owner)
**Version**: 0.1
**Statut**: En attente de clarification client
