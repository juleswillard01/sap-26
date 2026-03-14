# Priorisation des Scénarios Métier

## Vue d'ensemble: Parcours Utilisateur Jules

### Scénario Principal: "Créer et Soumettre une Facture"

```
[Jules a une intervention]
    ↓
[Ouvre app → Dashboard]
    ↓
[Clique "Nouvelle Facture"]
    ↓
[Sélectionne client existant OU crée nouveau]
    ↓
[Remplit détails intervention]
    - Date/heure (ou forfait)
    - Montant
    - Description service
    - Nature service (code URSSAF)
    ↓
[Valide avant d'envoyer]
    - Checklist: tous champs URSSAF présents?
    ↓
[Clique "Envoyer à URSSAF"]
    - API authentication auto
    - Submission
    ↓
[Confirmation ou erreur]
    - ✓ "Facture #12345 envoyée"
    - ✗ "Erreur: données manquantes" + détails
    ↓
[Facture visible dans Dashboard en "En attente validation"]
    ↓
[48h: client valide sur portail URSSAF]
    ↓
[Jules voit status "Validée"]
    ↓
[+2j: URSSAF paie]
    ↓
[Jules voit status "Payée" + montant]
```

---

## Scénarios Secondaires

### Scénario 2: "Relancer un Client"
**Quand**: Facture en attente > 36h sans validation client
**Workflow**:
```
Dashboard affiche badge "Action urgente" sur facture
Jules clique → option "Envoyer rappel client"
Email auto envoyé au client
Jules peut aussi envoyer message personnalisé
```

### Scénario 3: "Consulter Historique Mensuel"
**Quand**: Jules prépare déclaration fiscale ou budget
**Workflow**:
```
Vue "Factures" → filtre mois
Voir liste + totaux
Export CSV possible
Visualiser trend CA
```

### Scénario 4: "Gestion Clients"
**Quand**: Nouveau client, ou MAJ coordonnées
**Workflow**:
```
Menu "Clients"
Ajouter: formulaire (nom, email, SIREN/SIRET, téléphone)
Modifier: éditer champs
Supprimer: archive (jamais vraiment delete)
Voir historique interventions par client
```

### Scénario 5: "Gérer Erreurs Submission"
**Quand**: API URSSAF rejette facture
**Workflow**:
```
Dashboard: facture en "Erreur"
Jules clique → voit message d'erreur détaillé
Propose corrections (form pré-rempli)
Resoumission manuelle
```

---

## Matrice Priorité vs Complexité

| Scénario | User Story | Priorité | Complexité | Effort (jours) | MVP? |
|----------|-----------|----------|-----------|----------------|------|
| Créer facture | Create invoice form | HAUTE | Moyenne | 2-3 | OUI |
| Soumettre URSSAF | Submit to API | HAUTE | Moyenne | 2-3 | OUI |
| Voir status | Dashboard + polling | HAUTE | Basse | 1-2 | OUI |
| Nouveau client | Client create form | Haute | Basse | 0.5-1 | OUI |
| Client existing | Client select/edit | Moyenne | Basse | 0.5-1 | OUI |
| Historique factures | Invoice list + filters | Moyenne | Basse | 1-2 | OUI |
| Relances auto | Email reminder job | Moyenne | Moyenne | 1-2 | NON (Phase 1.5) |
| Export CSV | Export invoices | Basse | Basse | 0.5 | NON (Phase 2) |
| Gestion erreurs API | Error handling + retry | HAUTE | Basse | 1 | OUI |
| Authentification OAuth | OAuth flow setup | HAUTE | Moyenne | 1-2 | OUI |

---

## Champs URSSAF Obligatoires Identifiés

**À valider avec Jules/API docs, mais probablement:**

### Par Facture
- `dateDebut` : date de début intervention
- `dateFin` : date de fin intervention
- `nature` : nature du service (code URSSAF)
- `typeUnite` : HEURE ou FORFAIT
- `quantite` : nombre heures ou forfaits
- `montantHT` : montant HT
- `montantTTC` : montant TTC
- `numeroFacture` : identifiant unique facture

### Par Intervenant (Jules)
- `codeIntervenant` : soit NOVA (préfixe SAP + 9 chiffres SIREN) soit SIRET
- `email` : contact Jules
- `nomEntreprise` : nom micro-entreprise

### Par Client
- `email` : adresse client (pour validation)
- `nomClient` : nom client
- `sirenClient` : SIREN client (si entreprise)

---

## Hypothèses de Design (à valider)

### UI/UX
- [ ] **Web app** (pas mobile first, mais responsive OK)
- [ ] **Interface simple**: max 3 clicks pour action courante
- [ ] **Dashboard**: 1ère chose vue après login
- [ ] **Formulaires**: pré-remplissage client automatique
- [ ] **Validation**: client-side rapide + server-side strict

### Data
- [ ] **Chiffrement**: credentials OAuth en BD (jamais en clear)
- [ ] **Audit**: log toute submission URSSAF
- [ ] **Archivage**: factures jamais supprimées, soft delete
- [ ] **Backups**: stratégie backup régulière

### Intégrations
- [ ] **URSSAF OAuth**: client credentials flow
- [ ] **URSSAF API**: REST (not GraphQL)
- [ ] **Indy**: Phase 2 seulement
- [ ] **Email**: service externe (SendGrid, AWS SES?)

### Scaling
- [ ] **Utilisateurs**: 1 (Jules) pour MVP; multi-user Phase 3+
- [ ] **Factures**: ~500/an (micro-entreprise) → pas bottleneck
- [ ] **Reliability**: 99.5% (SAP critique)
- [ ] **Latency**: API appel < 5s (user tolérance)

---

## Questions de Clarification Prioritaires

**Bloc 1 (Volume et Cas d'usage):**
1. Combien factures/mois typiquement?
2. Combien clients différents?
3. Horaire ou forfait (ou mix)?

**Bloc 2 (Intégrations souhaités):**
4. Indy connecté requis pour MVP?
5. Besoin import historique factures?
6. Export pour comptable nécessaire?

**Bloc 3 (Préférences):**
7. Interface web, desktop, ou CLI?
8. Multi-user future ou solo garantie?
9. Besoin notifications/SMS ou email suffit?

**Bloc 4 (Timing):**
10. Deadline pour MVP fonctionnel?
11. Charges de travail par client (fixe vs variable)?

---

Attente: Jules clarify points ci-dessus avant fin spec fonctionnelle.

