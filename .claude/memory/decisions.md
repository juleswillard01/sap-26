# Décisions Techniques

### 2026-03-20 — Pivot vers avance-immediate.fr
**Contexte** : Schéma initial prévoyait API URSSAF directe + facturation custom
**Décision** : Déléguer facturation + URSSAF à avance-immediate.fr (offre tout-en-un 99€/an)
**Raison** : Coût (8€/mois), fiabilité (certifié URSSAF), focus sur la valeur ajoutée

### 2026-03-20 — Google Sheets comme backend
**Contexte** : Choix entre SQLite, PostgreSQL, ou Google Sheets
**Décision** : Google Sheets via gspread (8 onglets)
**Raison** : Jules peut éditer manuellement, formules natives pour calculs, embeds pour dashboard
