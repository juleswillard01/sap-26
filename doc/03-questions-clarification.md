# Questions de Clarification - Entretien Interactif avec Jules

**Objectif**: Élever le score de qualité des requirements de 46/100 → 90+/100

---

## Bloc 1: VOLUME & FRÉQUENCE (Business Value)

Ces questions visent à quantifier la valeur commerciale réelle et le ROI.

### Q1.1 - Factures par Mois
**Question**: En moyenne, combien de factures tu crées et envoies par mois?
- [ ] < 5 factures/mois
- [ ] 5-15 factures/mois
- [ ] 15-50 factures/mois
- [ ] 50+ factures/mois

**Pourquoi c'est important**: Détermine si automation vaut l'effort. <5/mois = peut-être overengineering.

---

### Q1.2 - Temps Actuel par Facture
**Question**: Aujourd'hui, combien de temps tu investis pour créer et envoyer **une** facture?
- [ ] < 5 minutes
- [ ] 5-10 minutes
- [ ] 10-20 minutes
- [ ] > 20 minutes
- [ ] Honnêtement aucune idée, je dois compter

**Pourquoi**: `(temps/facture) × (factures/mois) = temps/mois gaspillé`. Si 10 factures × 15min = 2.5h/mois → ROI? Si 100 factures × 5min = 8h/mois → forte ROI.

---

### Q1.3 - Types de Charges
**Question**: Tes interventions SAP, c'est plutôt:
- [ ] **Horaire** (tu factures 20€/h, 30€/h, etc.)
- [ ] **Forfaitaire** (client paie 150€ pour une intervention, peu importe durée)
- [ ] **Mix** (certains clients horaires, d'autres forfait)
- [ ] **Autre** (abonnement mensuel, autre modèle?)

**Pourquoi**: Impact sur structure facture URSSAF (champ `typeUnite`), complexité validation.

---

### Q1.4 - Étendue Clients
**Question**: Combien de **clients différents** tu as en général sur un mois?
- [ ] 1-3 clients
- [ ] 4-10 clients
- [ ] 11-30 clients
- [ ] 30+ clients

**Pourquoi**: Si 3 clients réutilisés = besoin fort de gestion client. Si 50 clients uniques/mois = complexité de data.

---

### Q1.5 - Montants Typiques
**Question**: Montant moyen d'une facture (TTC)?
- [ ] < 50€
- [ ] 50-200€
- [ ] 200-500€
- [ ] 500€+

**Pourquoi**: Montants petits = tolère erreurs, montants élevés = besoin validation stricte.

---

## Bloc 2: PROCESSUS EXISTANT & PAIN POINTS (Functional Requirements)

Questions pour comprendre workflows actuels et frustrations.

### Q2.1 - Outils Actuels
**Question**: Actuellement, comment tu crées tes factures?
- [ ] Excel (tableau manuel)
- [ ] Word (template qu'tu complètes)
- [ ] Indy directement
- [ ] Papier à remplir / scanner
- [ ] Autre logiciel: ___________
- [ ] Pas de vraie facture, juste notes

**Pourquoi**: Définit baseline, tâches à automatiser.

---

### Q2.2 - Erreurs Fréquentes
**Question**: Quelles erreurs tu fais **souvent** lors de facturation?
- [ ] Oublier un champ obligatoire
- [ ] Montants incorrects (calcul, TVA?)
- [ ] Dates d'intervention mal saisies
- [ ] Email client manquant ou incorrect
- [ ] Format URSSAF incorrect (codes nature, NOVA?)
- [ ] Doublon factures (facture deux fois le même)
- [ ] Je fais peu d'erreurs, c'est plutôt du temps perdu

**Pourquoi**: Révèle opportunités de validation/automatisation.

---

### Q2.3 - Suivi Paiements
**Question**: Comment tu fais le suivi qu'un client a validé et qu'URSSAF a payé?
- [ ] Rien, je découvre à la banque
- [ ] Je check manuellement le portail URSSAF
- [ ] Je demande au client
- [ ] Email URSSAF ou client me notifie
- [ ] Indy me notifie automatiquement
- [ ] Autre: ____________

**Pourquoi**: Détermine besoin de notifications/dashboard.

---

### Q2.4 - Relances Clients
**Question**: Quand un client valide pas sa facture à temps (délai 48h URSSAF), tu fais:
- [ ] Rien, tu attends
- [ ] Tu appelles/emails le client
- [ ] Tu laisse tomber la facture
- [ ] Jamais eu ce problème
- [ ] Je le fait après quelques jours d'oubli

**Pourquoi**: Besoin de rappels automatiques?

---

### Q2.5 - Réconciliation
**Question**: Combien de temps par mois tu inverses à réconcilier URSSAF ↔ Indy ↔ Banque?
- [ ] 0 minutes (je fais rien)
- [ ] < 30 min
- [ ] 30 min - 1h
- [ ] 1-2h
- [ ] > 2h

**Pourquoi**: Si temps investi = besoin possible d'intégration Indy.

---

## Bloc 3: INTÉGRATIONS & OUTILLAGE (Technical Constraints)

Comprendre l'écosystème réel de Jules.

### Q3.1 - Utilisation Indy
**Question**: Tu utilises Indy actuellement?
- [ ] Oui, quotidiennement (saisie factures, bank import, etc.)
- [ ] Oui, occasionnellement (consultation, export)
- [ ] Rarement, juste pour avoir
- [ ] Je l'ai pas encore utilisé vraiment
- [ ] Non, j'utilise autre chose: ___________

**Pourquoi**: Détermine si Indy intégration critique ou bonus.

---

### Q3.2 - Besoin d'Intégration Indy MVP
**Question**: Pour MVP, crois-tu avoir **besoin** que ta facture URSSAF soit auto-synchro dans Indy?
- [ ] OUI, critique (sinon je dois saisir deux fois)
- [ ] Serait nice, mais je peux saisir manuellement dans Indy
- [ ] NON, je m'en fous, phases séparées OK
- [ ] Hesitant, je comprends pas bien comment ça marchait

**Pourquoi**: Dépendance MVP sur Indy API.

---

### Q3.3 - Import Historique
**Question**: As-tu des factures passées (déjà créées/envoyées) que tu veux importer?
- [ ] OUI, ~_____ factures à importer
- [ ] Non, je pars de zéro
- [ ] Peut-être quelques-unes, pas urgent

**Pourquoi**: Effort initial d'import.

---

### Q3.4 - Besoin Export
**Question**: Besoin de pouvoir exporter factures (CSV, PDF, XML) pour:
- [ ] Audit comptable régulier
- [ ] Déclaration fiscale
- [ ] Autre: ___________
- [ ] Pas besoin, Indy suffit

**Pourquoi**: Phase 2 ou MVP?

---

## Bloc 4: PRÉFÉRENCES INTERFACE & INTERACTION (UX)

### Q4.1 - Type d'Interface
**Question**: Tu préfères accéder à la solution par:
- [ ] **Web app** (accès navigateur, peut être sur desktop/mobile)
- [ ] **Desktop app** (installée sur PC/Mac)
- [ ] **CLI** (commande ligne, style terminal)
- [ ] **Mobile app** (priorité smartphone)
- [ ] Pas de préférence, montre-moi les options

**Pourquoi**: Impact tech stack.

---

### Q4.2 - Contexte d'Utilisation
**Question**: Généralement, où tu crées factures?
- [ ] Bureau, sur PC ordinateur
- [ ] Sur le terrain (smartphone/tablette)
- [ ] À la maison, flexible
- [ ] Mélange des trois

**Pourquoi**: Responsive design prioritaire ou web desktop suffit?

---

### Q4.3 - Authentification
**Question**: Préférence auth:
- [ ] **Mot de passe local** (login/password créé dans l'app)
- [ ] **OAuth URSSAF** (login via tes creds URSSAF)
- [ ] **SSO** (intégration autre service)
- [ ] Pas de préférence, fais logique

**Pourquoi**: Sécurité vs. friction trade-off.

---

### Q4.4 - Aide/Onboarding
**Question**: Premier fois utiliser l'app, tu préfères:
- [ ] Tutoriel pas-à-pas (wizard)
- [ ] Documentation/FAQ
- [ ] Call avec moi pour expliquer
- [ ] Learn by doing, feedback si erreur

**Pourquoi**: Effort formation.

---

## Bloc 5: TIMING & CONTRAINTES (Scope)

### Q5.1 - Deadline MVP
**Question**: Tu voudrais avoir une solution fonctionnelle pour commencer à facturer URSSAF quand?
- [ ] URGENT, cette semaine si possible
- [ ] Dans 1-2 semaines
- [ ] Dans 1 mois
- [ ] Dans 2-3 mois
- [ ] Pas urgent, flexible

**Pourquoi**: Impact roadmap / ressources.

---

### Q5.2 - Volume Growth
**Question**: Penses-tu que ton volume factures va:
- [ ] Rester stable (~même factures/mois)
- [ ] Croître modérément (2x dans 1 an)
- [ ] Croître rapidement (5x+ dans 1 an)
- [ ] Incertain, dépend opportunités

**Pourquoi**: Architecture dès départ ou MVP et refacto OK?

---

### Q5.3 - Multi-User Future
**Question**: Futurement, crois-tu avoir besoin:
- [ ] Reste solo (jamais multi-user)
- [ ] Peut-être 1-2 collaborateurs plus tard (année 2?)
- [ ] Oui, probable quelques personne l'année prochaine
- [ ] Oui, scalable multi-team

**Pourquoi**: Auth, permissions, data isolation dès départ?

---

### Q5.4 - Comptable/Audit
**Question**: Tu as un comptable/expert qui te suit?
- [ ] Oui, régulier (mensuel ou trimestriel)
- [ ] Oui, ponctuellement (une fois par an)
- [ ] Non, je gère tout seul
- [ ] Hésitant, pas encore structuré

**Pourquoi**: Besoin audit trail strict? Format export?

---

## Bloc 6: SCÉNARIOS EDGE CASES & RISQUES (Requirements Completeness)

### Q6.1 - Facture Annulée/Corrigée
**Question**: Qu'est-ce qui se passe si tu dois corriger/annuler facture déjà envoyée URSSAF?
- [ ] Ça ne m'arrive jamais
- [ ] Facture être annulée, nouvelle facture envoyée
- [ ] Je dois créer facture d'avoirs/correction
- [ ] Pas sûr, ça m'angoisse

**Pourquoi**: Workflow d'erreur important.

---

### Q6.2 - Données Sensibles
**Question**: T'es-tu préoccupé par sécurité/confidentialité datas clients?
- [ ] OUI, important (données clients à protéger)
- [ ] Moyen (normal, j'accepte risques standard)
- [ ] Non, pas vraiment inquiet
- [ ] Déjà réglé par Indy

**Pourquoi**: Chiffrement, audit, RGPD considerations.

---

### Q6.3 - Downtime Tolérance
**Question**: Si la solution était indisponible 1h (urgence technique):
- [ ] Problème grave, je peux pas facturer
- [ ] Ennuyant, mais j'attends
- [ ] OK si < 24h
- [ ] Dépend quand (si client en attente = grave)

**Pourquoi**: SLA requirements.

---

## Synthèse des Réponses

Après avoir répondu aux 30+ questions ci-dessus, on pourra:
1. Mapper chaque réponse à requirement spécifique
2. Scorer qualité des requirements
3. Valider MVP vs Phase 2
4. Identifier risques critiques
5. Établir roadmap précis

---

**Document de Clarification**
**Status**: À remplir conjointement Jules + Sarah
**Prochaine étape**: Entretien + scoring révisé
