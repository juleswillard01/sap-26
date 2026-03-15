# SAP-Facture

Plateforme de facturation URSSAF pour micro-entrepreneurs en services a la personne.

## Source de verite

Le schema fonctionnel et l'architecture SI sont definis dans :

**[docs/schemas/SCHEMAS.html](docs/schemas/SCHEMAS.html)**

Ce fichier contient les 8 diagrammes Mermaid qui decrivent :
1. Parcours utilisateur quotidien
2. Flux de facturation end-to-end
3. Sequence API URSSAF (OAuth + REST)
4. Architecture systeme (FastAPI + Google Sheets)
5. Modele de donnees (8 onglets Sheets)
6. Rapprochement bancaire Swan/URSSAF
7. Machine a etats (cycle de vie facture)
8. Scope MVP vs phases futures

## Methodologie

Le projet suit la methode BMAD v6. Voir `bmad/config.yaml` et `docs/bmm-workflow-status.yaml`.

## Archive

Le prototype v1 (FastAPI/SQLite) est archive dans `archive/sap-facture-prototype-v1.zip`.
