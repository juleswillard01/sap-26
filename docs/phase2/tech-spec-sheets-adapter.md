# Spécification Technique du SheetsAdapter — Phase 2

**Auteur** : Winston (System Architect)
**Date** : Mars 2026
**Version** : 1.0
**Statut** : Spécification détaillée
**PRD** : 01-product-requirements.md
**Architecture** : SCHEMAS.html (Schéma 4, 5, 6)

---

## Résumé Exécutif

Le **SheetsAdapter** est le composant critique de persistance de données dans SAP-Facture. Il abstrait l'accès à Google Sheets API v4 via la librairie `gspread`, centralisant toutes les lectures/écritures sur les **8 onglets** du Spreadsheet.

**Enjeux clés** :
- **Single Source of Truth** : Aucune DB SQL, tout dans Google Sheets
- **Zéro chevauchement** : 3 onglets data brute éditables + 5 onglets formules calculés
- **Minimalisation des API calls** : Batch operations, caching local, 1 appel par opération
- **Résilience** : Gestion quota exhausted, network timeouts, sheet locked
- **Testabilité** : Mocks complets gspread, fixtures reproducibles

**Scope phase 2** : Implémentation complète du SheetsAdapter + tests unitaires.

---

## 1. Architecture du Composant

### 1.1 Responsabilités

Le SheetsAdapter centralise **toutes les opérations de lecture/écriture** dans Google Sheets pour :
- **InvoiceService** → lire clients, écrire/mettre à jour factures
- **ClientService** → lire/écrire clients
- **PaymentTracker** → lire factures, mettre à jour statuts
- **BankReconciliation** → lire transactions, écrire lettrage + balances
- **NovaReporting** → lire clients/factures pour calcul metrics

### 1.2 Principes de Design

| Principe | Justification |
|----------|---------------|
| **Single Responsibility** | Une classe = abstraction API Sheets, zéro logique métier |
| **Cache-First** | Lire cache avant API, TTL configurable (défaut 5 min) |
| **Batch Operations** | Grouper CRUD multiples en 1 appel API |
| **No Formula Overwrite** | Jamais modifier onglets calculés (Lettrage, Balances, etc.) |
| **Explicit Types** | Dataclasses Pydantic pour chaque modèle |
| **Resilient Defaults** | Retry exponential, graceful degradation |

### 1.3 Dépendances

```python
# Dépendances obligatoires
gspread>=6.1.0          # Google Sheets API client
google-auth>=2.25.0     # OAuth2 service account
google-auth-oauthlib    # OAuth2 flows
pydantic>=2.0.0         # Data validation
python-dotenv>=1.0.0    # Config .env

# Optionnel (tests)
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
```

---

## 2. Modèle de Données — Structure des Onglets

### 2.1 Onglets Data Brute (Éditables)

#### Onglet 1 : Clients
```
Colonnes :
  A: client_id (ID unique, généré ou importé)
  B: nom
  C: prenom
  D: email
  E: telephone
  F: adresse
  G: code_postal
  H: ville
  I: urssaf_id (NULL si pas encore inscrit)
  J: statut_urssaf (INSCRIT, EN_ATTENTE, ERREUR)
  K: date_inscription
  L: actif (true/false)

Exemple ligne :
  1 | Alice Dupont | alice@email.com | ... | null | EN_ATTENTE | 2026-03-01 | true
```

**Modèle Pydantic** :
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ClientRow(BaseModel):
    client_id: str = Field(min_length=1)
    nom: str
    prenom: str
    email: str
    telephone: Optional[str] = None
    adresse: str
    code_postal: str
    ville: str
    urssaf_id: Optional[str] = None
    statut_urssaf: str = Field(pattern="^(INSCRIT|EN_ATTENTE|ERREUR)$")
    date_inscription: Optional[str] = None  # ISO format YYYY-MM-DD
    actif: bool = True
```

#### Onglet 2 : Factures
```
Colonnes :
  A: facture_id (clé unique)
  B: client_id (FK → Clients)
  C: type_unite (HEURE, FORFAIT, etc.)
  D: nature_code (code URSSAF, ex. 120 pour apprentissage)
  E: quantite (nb heures ou montant)
  F: montant_unitaire (euros)
  G: montant_total (=E*F, formule optionnelle)
  H: date_debut
  I: date_fin
  J: description
  K: statut (BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, ANNULE, ERREUR, EXPIRE, REJETE)
  L: urssaf_demande_id (ID demande paiement URSSAF)
  M: date_soumission_urssaf
  N: date_validation_client
  O: pdf_drive_id (ID fichier PDF stocké Google Drive)

Exemple ligne :
  INV-2026-001 | client-1 | HEURE | 120 | 10 | 25.00 | 250.00 | 2026-03-01 | 2026-03-31 | Cours mars | PAYE | dem-12345 | 2026-03-02 | 2026-03-05 | drive-file-xxx
```

**Modèle Pydantic** :
```python
class InvoiceRow(BaseModel):
    facture_id: str = Field(min_length=1)
    client_id: str
    type_unite: str  # HEURE, FORFAIT
    nature_code: str  # Code URSSAF
    quantite: float = Field(gt=0)
    montant_unitaire: float = Field(gt=0)
    montant_total: float = Field(gt=0)  # Optionnel : peut être formule
    date_debut: str  # YYYY-MM-DD
    date_fin: str
    description: str
    statut: str = Field(
        pattern="^(BROUILLON|SOUMIS|CREE|EN_ATTENTE|VALIDE|PAYE|RAPPROCHE|ANNULE|ERREUR|EXPIRE|REJETE)$"
    )
    urssaf_demande_id: Optional[str] = None
    date_soumission_urssaf: Optional[str] = None
    date_validation_client: Optional[str] = None
    pdf_drive_id: Optional[str] = None
```

#### Onglet 3 : Transactions
```
Colonnes :
  A: transaction_id (clé unique, ex. swan-txn-12345)
  B: swan_id (ID virement depuis API Swan)
  C: date_valeur (date du virement)
  D: montant (euros, positif = crédit)
  E: libelle (descriptif du virement, ex. "URSSAF Virement...")
  F: type (CREDIT, DEBIT, etc.)
  G: source (URSSAF, AUTRE, etc.)
  H: facture_id (FK → Factures, optionnel, rempli après lettrage)
  I: statut_lettrage (NON_LETTREE, LETTRE, A_VERIFIER, PAS_DE_MATCH)
  J: date_import (date d'import depuis Swan)

Exemple ligne :
  txn-1 | swan-2026-0001 | 2026-03-10 | 250.00 | URSSAF Virement professionnel | CREDIT | URSSAF | INV-2026-001 | LETTRE | 2026-03-11
```

**Modèle Pydantic** :
```python
class TransactionRow(BaseModel):
    transaction_id: str = Field(min_length=1)
    swan_id: str
    date_valeur: str  # YYYY-MM-DD
    montant: float
    libelle: str
    type: str  # CREDIT, DEBIT
    source: str  # URSSAF, AUTRE
    facture_id: Optional[str] = None
    statut_lettrage: str = Field(
        pattern="^(NON_LETTREE|LETTRE|A_VERIFIER|PAS_DE_MATCH)$",
        default="NON_LETTREE"
    )
    date_import: str  # YYYY-MM-DD
```

---

### 2.2 Onglets Calculés (Formules, Lecture Seule)

**Important** : Le SheetsAdapter **ne doit jamais écrire** dans ces onglets (sauf initialisation). Les formules Google Sheets se recalculent automatiquement quand data brute change.

#### Onglet 4 : Lettrage
```
Colonnes (générées par formules) :
  A: facture_id (=Factures.A)
  B: montant_facture (=Factures.G)
  C: txn_id (=Transactions.A)
  D: txn_montant (=Transactions.D)
  E: ecart (=ABS(B-D))
  F: score_confiance (=IF(B=D,50) + IF(date<3j,30) + IF(libelle=URSSAF,20))
  G: statut (=IF(score>=80, "AUTO", IF(score>=50, "A_VERIFIER", "PAS_DE_MATCH")))

Logique :
  - Pour chaque facture PAYEE, chercher 1 transaction match
  - Match = montant exact + date ±5j + libelle URSSAF
  - Score >= 80 → LETTRE AUTO
  - Score < 80 → A_VERIFIER (Jules valide manuellement)
  - Pas de match → PAS_DE_MATCH
```

**Note pour le code** : SheetsAdapter lit cet onglet (pour valider lettrage), ne l'écrit jamais.

#### Onglet 5 : Balances
```
Colonnes (générées par formules) :
  A: mois (ex. 2026-03)
  B: nb_factures (=COUNTIF(...))
  C: ca_total (=SUMIF(...))
  D: recu_urssaf (=SUMIF(onglet Transactions, montant, date=mois))
  E: solde (=C-D)
  F: nb_non_lettrees (=COUNTIF(...))
  G: nb_en_attente (=COUNTIF(...))

Logique : Agrégation mensuelle du CA et des virements reçus.
```

#### Onglet 6 : Metrics NOVA
```
Colonnes (générées par formules) :
  A: trimestre (ex. T1-2026)
  B: nb_intervenants (=1, valeur statique pour Jules)
  C: heures_effectuees (=SUMIF(Factures.C, type=HEURE))
  D: nb_particuliers (=COUNTA(UNIQUE(Factures.client_id)))
  E: ca_trimestre (=SUMIF(Factures.G, date=trimestre))
  F: deadline_saisie (=DATE_AJOUT(date_fin_trim, 30))

Logique : Calcul metrics NOVA pour déclaration trimestrielle.
```

#### Onglet 7 : Cotisations
```
Colonnes (générées par formules) :
  A: mois (ex. 2026-03)
  B: ca_encaisse (=SUMIF(Factures, montant, date=mois, statut=PAYE))
  C: taux_charges (=25.8%)
  D: montant_charges (=B*C)
  E: date_limite (=DATE_AJOUT(fin_mois, 15))
  F: cumul_ca (=SUM(B:B))
  G: net_apres_charges (=cumul_ca - SUM(D:D))

Logique : Calcul charges sociales mensuelles (micro-entrepreneur 25.8%).
```

#### Onglet 8 : Fiscal IR
```
Colonnes (générées par formules) :
  A: revenu_apprentissage (=SUMIF(Factures, montant, nature_code=120, statut=PAYE))
  B: seuil_exo_apprentissage (=18000.00)
  C: ca_micro (=SUM(Factures.montant, statut=PAYE))
  D: abattement_bnc (=34%)
  E: revenu_imposable (=MAX(0, (C - (C*D)) - A))
  F: tranches_ir (consulter barème fiscal 2026)
  G: taux_marginal (ex. 11%)
  H: simulation_vl (=E * 2.2%)

Logique : Simulation fiscale annuelle pour déclaration IR.
```

---

## 3. Interface Python du SheetsAdapter

### 3.1 Signature Classe

```python
from __future__ import annotations

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field

import gspread
from google.oauth2.service_account import Credentials
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration cache local."""
    ttl_seconds: int = 300  # 5 minutes par défaut
    enabled: bool = True
    max_size_mb: int = 50


class SheetsAdapter:
    """
    Abstraction Google Sheets API v4 pour SAP-Facture.

    Gère 8 onglets :
    - Data brute (éditables) : Clients, Factures, Transactions
    - Calculés (formules) : Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR
    """

    # Constantes : IDs et ranges de chaque onglet
    SHEET_IDS = {
        "Clients": 0,
        "Factures": 1,
        "Transactions": 2,
        "Lettrage": 3,
        "Balances": 4,
        "Metrics NOVA": 5,
        "Cotisations": 6,
        "Fiscal IR": 7,
    }

    SHEET_HEADERS = {
        "Clients": [
            "client_id", "nom", "prenom", "email", "telephone",
            "adresse", "code_postal", "ville", "urssaf_id",
            "statut_urssaf", "date_inscription", "actif"
        ],
        "Factures": [
            "facture_id", "client_id", "type_unite", "nature_code",
            "quantite", "montant_unitaire", "montant_total",
            "date_debut", "date_fin", "description", "statut",
            "urssaf_demande_id", "date_soumission_urssaf",
            "date_validation_client", "pdf_drive_id"
        ],
        "Transactions": [
            "transaction_id", "swan_id", "date_valeur", "montant",
            "libelle", "type", "source", "facture_id",
            "statut_lettrage", "date_import"
        ],
        "Lettrage": [
            "facture_id", "montant_facture", "txn_id", "txn_montant",
            "ecart", "score_confiance", "statut"
        ],
        "Balances": [
            "mois", "nb_factures", "ca_total", "recu_urssaf",
            "solde", "nb_non_lettrees", "nb_en_attente"
        ],
        "Metrics NOVA": [
            "trimestre", "nb_intervenants", "heures_effectuees",
            "nb_particuliers", "ca_trimestre", "deadline_saisie"
        ],
        "Cotisations": [
            "mois", "ca_encaisse", "taux_charges", "montant_charges",
            "date_limite", "cumul_ca", "net_apres_charges"
        ],
        "Fiscal IR": [
            "revenu_apprentissage", "seuil_exo_apprentissage", "ca_micro",
            "abattement_bnc", "revenu_imposable", "tranches_ir",
            "taux_marginal", "simulation_vl"
        ]
    }

    def __init__(
        self,
        spreadsheet_id: str,
        credentials_path: Optional[str] = None,
        credentials_json: Optional[str] = None,
        cache_config: Optional[CacheConfig] = None,
    ) -> None:
        """
        Initialiser SheetsAdapter.

        Args:
            spreadsheet_id: ID Google Sheets (de l'URL)
            credentials_path: Chemin vers credentials.json service account
            credentials_json: Contenu JSON base64 ou raw (priority > credentials_path)
            cache_config: Configuration cache local
        """
        self.spreadsheet_id = spreadsheet_id
        self.cache_config = cache_config or CacheConfig()
        self._cache: dict[str, tuple[list[dict], datetime]] = {}

        # Authentification
        self._auth_client = self._authenticate(credentials_path, credentials_json)

        # Ouvrir Spreadsheet
        try:
            self.workbook = self._auth_client.open_by_key(spreadsheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Spreadsheet {spreadsheet_id} not found")
            raise
        except Exception as e:
            logger.error(f"Failed to open spreadsheet: {e}")
            raise

    def _authenticate(
        self,
        credentials_path: Optional[str],
        credentials_json: Optional[str],
    ) -> gspread.Client:
        """Authentifier auprès de Google Sheets API."""
        try:
            if credentials_json:
                # JSON brut (priorité haute)
                creds_dict = json.loads(credentials_json)
            elif credentials_path:
                # Fichier chemin
                with open(credentials_path) as f:
                    creds_dict = json.load(f)
            else:
                raise ValueError("credentials_path ou credentials_json requis")

            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
            )
            client = gspread.authorize(credentials)
            logger.info("Google Sheets authentication successful")
            return client
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def _get_sheet(self, sheet_name: str) -> gspread.Worksheet:
        """Récupérer worksheet par nom, avec fallback."""
        try:
            return self.workbook.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{sheet_name}' not found")
            raise

    def _is_cache_valid(self, key: str) -> bool:
        """Vérifier si cache entry est valide."""
        if key not in self._cache or not self.cache_config.enabled:
            return False
        data, timestamp = self._cache[key]
        elapsed = (datetime.now() - timestamp).total_seconds()
        return elapsed < self.cache_config.ttl_seconds

    def _get_cache(self, key: str) -> Optional[list[dict]]:
        """Récupérer data du cache si valide."""
        if self._is_cache_valid(key):
            logger.debug(f"Cache hit: {key}")
            return self._cache[key][0]
        return None

    def _set_cache(self, key: str, data: list[dict]) -> None:
        """Stocker data dans cache."""
        if self.cache_config.enabled:
            self._cache[key] = (data, datetime.now())

    def _invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """Invalider cache par pattern ou tout."""
        if pattern:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for k in keys_to_delete:
                del self._cache[k]
        else:
            self._cache.clear()

    # ===== OPERATIONS CLIENTS =====

    def read_clients(self) -> list[ClientRow]:
        """
        Lire tous les clients de l'onglet Clients.

        Returns:
            Liste objets ClientRow validés.

        Raises:
            gspread.exceptions.APIError si quota exceeded ou network timeout
        """
        cache_key = "clients:all"
        cached = self._get_cache(cache_key)
        if cached:
            return [ClientRow(**row) for row in cached]

        try:
            sheet = self._get_sheet("Clients")
            rows = sheet.get_all_records()  # Headers + data
            self._set_cache(cache_key, rows)

            # Valider chaque ligne avec Pydantic
            clients = [ClientRow(**row) for row in rows]
            logger.info(f"Read {len(clients)} clients from Sheets")
            return clients
        except gspread.exceptions.APIError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                logger.error("Google Sheets quota exceeded")
                # Fallback : retourner cache périmé si dispo
                if cache_key in self._cache:
                    return [ClientRow(**row) for row in self._cache[cache_key][0]]
            raise

    def read_client_by_id(self, client_id: str) -> Optional[ClientRow]:
        """Lire un client spécifique par ID."""
        try:
            clients = self.read_clients()
            return next((c for c in clients if c.client_id == client_id), None)
        except Exception as e:
            logger.error(f"Failed to read client {client_id}: {e}")
            raise

    def write_client(self, client: ClientRow) -> None:
        """
        Ajouter ou mettre à jour un client.

        Stratégie :
        - Si client_id existe → UPDATE ligne
        - Sinon → APPEND nouvelle ligne
        """
        try:
            sheet = self._get_sheet("Clients")
            existing = self.read_client_by_id(client.client_id)

            client_dict = client.model_dump(exclude_unset=True)
            values = [client_dict.get(h, "") for h in self.SHEET_HEADERS["Clients"]]

            if existing:
                # Trouver numéro de ligne (headers + data index)
                all_clients = self.read_clients()
                row_idx = next(
                    (i + 2 for i, c in enumerate(all_clients) if c.client_id == client_id),
                    None
                )
                if row_idx:
                    sheet.update(f"A{row_idx}:L{row_idx}", [values], value_input_option="USER_ENTERED")
                    logger.info(f"Updated client {client.client_id}")
            else:
                # Ajouter nouvelle ligne
                sheet.append_row(values, value_input_option="USER_ENTERED")
                logger.info(f"Created client {client.client_id}")

            self._invalidate_cache("clients")
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to write client {client.client_id}: {e}")
            raise

    # ===== OPERATIONS FACTURES =====

    def read_invoices(self) -> list[InvoiceRow]:
        """Lire toutes les factures."""
        cache_key = "invoices:all"
        cached = self._get_cache(cache_key)
        if cached:
            return [InvoiceRow(**row) for row in cached]

        try:
            sheet = self._get_sheet("Factures")
            rows = sheet.get_all_records()
            self._set_cache(cache_key, rows)

            invoices = [InvoiceRow(**row) for row in rows]
            logger.info(f"Read {len(invoices)} invoices from Sheets")
            return invoices
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read invoices: {e}")
            raise

    def read_invoices_by_status(self, status: str) -> list[InvoiceRow]:
        """Lire factures filtrées par statut."""
        invoices = self.read_invoices()
        return [inv for inv in invoices if inv.statut == status]

    def read_invoices_by_client(self, client_id: str) -> list[InvoiceRow]:
        """Lire factures d'un client."""
        invoices = self.read_invoices()
        return [inv for inv in invoices if inv.client_id == client_id]

    def write_invoice(self, invoice: InvoiceRow) -> None:
        """Ajouter ou mettre à jour une facture."""
        try:
            sheet = self._get_sheet("Factures")
            existing = self.read_invoices()
            existing_ids = [inv.facture_id for inv in existing]

            invoice_dict = invoice.model_dump(exclude_unset=True)
            values = [invoice_dict.get(h, "") for h in self.SHEET_HEADERS["Factures"]]

            if invoice.facture_id in existing_ids:
                # UPDATE
                row_idx = next(
                    (i + 2 for i, inv in enumerate(existing) if inv.facture_id == invoice.facture_id),
                    None
                )
                if row_idx:
                    sheet.update(f"A{row_idx}:O{row_idx}", [values], value_input_option="USER_ENTERED")
                    logger.info(f"Updated invoice {invoice.facture_id}")
            else:
                # APPEND
                sheet.append_row(values, value_input_option="USER_ENTERED")
                logger.info(f"Created invoice {invoice.facture_id}")

            self._invalidate_cache("invoices")
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to write invoice {invoice.facture_id}: {e}")
            raise

    def update_invoice_status(self, facture_id: str, new_status: str) -> None:
        """Mettre à jour uniquement le statut d'une facture."""
        try:
            invoices = self.read_invoices()
            row_idx = next(
                (i + 2 for i, inv in enumerate(invoices) if inv.facture_id == facture_id),
                None
            )
            if row_idx:
                sheet = self._get_sheet("Factures")
                sheet.update(f"K{row_idx}", [[new_status]], value_input_option="USER_ENTERED")
                logger.info(f"Updated invoice {facture_id} status to {new_status}")
                self._invalidate_cache("invoices")
            else:
                logger.warning(f"Invoice {facture_id} not found")
        except Exception as e:
            logger.error(f"Failed to update status {facture_id}: {e}")
            raise

    # ===== OPERATIONS TRANSACTIONS =====

    def read_transactions(self) -> list[TransactionRow]:
        """Lire toutes les transactions."""
        cache_key = "transactions:all"
        cached = self._get_cache(cache_key)
        if cached:
            return [TransactionRow(**row) for row in cached]

        try:
            sheet = self._get_sheet("Transactions")
            rows = sheet.get_all_records()
            self._set_cache(cache_key, rows)

            transactions = [TransactionRow(**row) for row in rows]
            logger.info(f"Read {len(transactions)} transactions from Sheets")
            return transactions
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read transactions: {e}")
            raise

    def read_transactions_by_date_range(
        self,
        start_date: str,  # YYYY-MM-DD
        end_date: str,
    ) -> list[TransactionRow]:
        """Lire transactions filtrées par plage date."""
        transactions = self.read_transactions()
        return [
            txn for txn in transactions
            if start_date <= txn.date_valeur <= end_date
        ]

    def write_transactions(self, transactions: list[TransactionRow]) -> None:
        """
        Écrire batch transactions depuis Swan.

        Stratégie : remplacer complètement l'onglet Transactions
        (les transactions ne changent jamais une fois importées)
        """
        try:
            sheet = self._get_sheet("Transactions")

            # Effacer existantes (garder headers)
            sheet.clear()

            # Récrire headers
            headers = self.SHEET_HEADERS["Transactions"]
            sheet.append_row(headers, value_input_option="USER_ENTERED")

            # Ajouter transactions par batch
            if transactions:
                rows = [
                    [
                        txn.model_dump().get(h, "")
                        for h in headers
                    ]
                    for txn in transactions
                ]
                # Batch : 100 lignes par appel
                for i in range(0, len(rows), 100):
                    batch = rows[i:i+100]
                    sheet.append_rows(batch, value_input_option="USER_ENTERED")

                logger.info(f"Wrote {len(transactions)} transactions to Sheets")

            self._invalidate_cache("transactions")
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to write transactions: {e}")
            raise

    # ===== OPERATIONS LETTRAGE (Lecture seule, pas d'écriture) =====

    def read_lettrage(self) -> list[dict]:
        """
        Lire onglet Lettrage (calculé par formules).

        Returns:
            Liste dictionnaires (facture_id, montant_facture, txn_id, score, statut, etc.)
        """
        cache_key = "lettrage:all"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            sheet = self._get_sheet("Lettrage")
            rows = sheet.get_all_records()
            self._set_cache(cache_key, rows)

            logger.info(f"Read {len(rows)} lettrage rows from Sheets")
            return rows
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read lettrage: {e}")
            raise

    # ===== OPERATIONS BALANCES (Lecture seule) =====

    def read_balances(self) -> list[dict]:
        """Lire onglet Balances (agrégation mensuelle)."""
        cache_key = "balances:all"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            sheet = self._get_sheet("Balances")
            rows = sheet.get_all_records()
            self._set_cache(cache_key, rows)

            logger.info(f"Read {len(rows)} balance rows from Sheets")
            return rows
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read balances: {e}")
            raise

    # ===== OPERATIONS METRICS NOVA (Lecture seule) =====

    def read_metrics_nova(self) -> list[dict]:
        """Lire onglet Metrics NOVA (trimestriel)."""
        cache_key = "metrics_nova:all"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            sheet = self._get_sheet("Metrics NOVA")
            rows = sheet.get_all_records()
            self._set_cache(cache_key, rows)

            logger.info(f"Read {len(rows)} NOVA metrics from Sheets")
            return rows
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read NOVA metrics: {e}")
            raise

    # ===== OPERATIONS COTISATIONS (Lecture seule) =====

    def read_cotisations(self) -> list[dict]:
        """Lire onglet Cotisations (charges mensuelles)."""
        cache_key = "cotisations:all"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            sheet = self._get_sheet("Cotisations")
            rows = sheet.get_all_records()
            self._set_cache(cache_key, rows)

            logger.info(f"Read {len(rows)} cotisations rows from Sheets")
            return rows
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read cotisations: {e}")
            raise

    # ===== OPERATIONS FISCAL IR (Lecture seule) =====

    def read_fiscal_ir(self) -> list[dict]:
        """Lire onglet Fiscal IR (simulation annuelle)."""
        cache_key = "fiscal_ir:all"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            sheet = self._get_sheet("Fiscal IR")
            rows = sheet.get_all_records()
            self._set_cache(cache_key, rows)

            logger.info(f"Read {len(rows)} fiscal IR rows from Sheets")
            return rows
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read fiscal IR: {e}")
            raise

    # ===== UTILITIES =====

    def clear_cache(self) -> None:
        """Vider complètement le cache local."""
        self._invalidate_cache()
        logger.info("Cache cleared")

    def health_check(self) -> bool:
        """Vérifier que la connexion Sheets est active."""
        try:
            self.workbook.batch_get(["Clients!A1"])
            logger.info("Sheets health check: OK")
            return True
        except Exception as e:
            logger.error(f"Sheets health check failed: {e}")
            return False
```

---

## 4. Stratégie Batch Read/Write

### 4.1 Minimisation des API Calls

**Objectif** : 1 appel API par opération logique, jamais 1 appel par ligne.

#### Exemple 1 : Lire tous les clients (1 appel)
```python
# ✓ BON : 1 appel API
clients = adapter.read_clients()
# Résultat : gspread.Worksheet.get_all_records() (single batch call)

# ✗ MAUVAIS : N appels API
for i in range(1, 1000):
    client = adapter.workbook.sheet1.cell(i, 1).value
```

#### Exemple 2 : Écrire batch de transactions (1 appel par 100 lignes)
```python
# ✓ BON : 1 appel par batch de 100 lignes
transactions = [TransactionRow(...), TransactionRow(...), ...]
adapter.write_transactions(transactions)
# Résultat : sheet.append_rows(batch, ...) (groupé par 100)

# ✗ MAUVAIS : 1 appel par transaction
for txn in transactions:
    adapter.write_transaction(txn)  # N appels!
```

#### Exemple 3 : Mettre à jour statut facture (1 appel)
```python
# ✓ BON : 1 appel API
adapter.update_invoice_status("INV-001", "VALIDE")
# Résultat : sheet.update(cell_range, [[value]], ...)

# ✗ MAUVAIS : relire tous + réécrire tout
invoices = adapter.read_invoices()
# ... find and update ...
adapter.write_invoices(invoices)  # N lignes!
```

### 4.2 Rate Limiting & Backoff

Google Sheets API impose des quotas : ~500 requêtes/100s par projet.

```python
import time
from functools import wraps

def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
):
    """Décorateur retry exponential avec jitter."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except gspread.exceptions.APIError as e:
                    if attempt == max_retries - 1:
                        logger.error(f"{func.__name__} failed after {max_retries} retries")
                        raise

                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed, "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
        return wrapper
    return decorator

# Appliquer au lecteur Sheets
@retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
def read_clients_with_retry(self) -> list[ClientRow]:
    return self.read_clients()
```

---

## 5. Stratégie de Cache Local

### 5.1 Architecture Cache

```python
self._cache: dict[str, tuple[list[dict], datetime]] = {
    "clients:all": (data, timestamp),
    "invoices:all": (data, timestamp),
    "transactions:all": (data, timestamp),
    "lettrage:all": (data, timestamp),
    ...
}
```

| Clé Cache | TTL | Stratégie |
|-----------|-----|-----------|
| `clients:all` | 5 min | Lire depuis API, cache <5min |
| `invoices:all` | 5 min | Lire depuis API, cache <5min |
| `transactions:all` | 5 min | Lire depuis API, cache <5min |
| `lettrage:all` | 5 min | Lire depuis API, cache <5min |
| `balances:all` | 5 min | Lire depuis API, cache <5min |
| Autres onglets | 5 min | Idem |

### 5.2 Invalidation Cache

**Règle** : Quand on écrit, invalider caches concernés.

```python
def write_invoice(self, invoice: InvoiceRow) -> None:
    sheet = self._get_sheet("Factures")
    # ... écrire dans Sheets ...

    # Invalider caches affectés
    self._invalidate_cache("invoices")  # Pattern match
    self._invalidate_cache("balances")  # Balances peut être recalculées

def write_transactions(self, transactions: list[TransactionRow]) -> None:
    sheet = self._get_sheet("Transactions")
    # ... écrire dans Sheets ...

    # Invalider caches
    self._invalidate_cache("transactions")
    self._invalidate_cache("lettrage")  # Lettrage se recalcule
    self._invalidate_cache("balances")  # Balances peut être recalculées
```

### 5.3 Fallback Cache Périmé

En cas de **quota exceeded** (RESOURCE_EXHAUSTED), retourner cache périmé si dispo :

```python
def read_clients(self) -> list[ClientRow]:
    cache_key = "clients:all"
    cached = self._get_cache(cache_key)
    if cached:
        return [ClientRow(**row) for row in cached]

    try:
        sheet = self._get_sheet("Clients")
        rows = sheet.get_all_records()
        self._set_cache(cache_key, rows)
        return [ClientRow(**row) for row in rows]
    except gspread.exceptions.APIError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            logger.warning("Quota exceeded, using stale cache")
            if cache_key in self._cache:
                data, _ = self._cache[cache_key]
                return [ClientRow(**row) for row in data]
        raise
```

**Impact** : Mieux servir stale data qu'erreur totale.

---

## 6. Gestion des Formules Sheets

### 6.1 Onglets Calculés (Lecture Seule)

Les 5 onglets suivants sont **générés automatiquement par des formules Google Sheets** :
- **Lettrage** : matching factures ↔ transactions
- **Balances** : agrégation mensuelle CA/virements
- **Metrics NOVA** : trimestriel, pour déclaration
- **Cotisations** : charges sociales mensuelles
- **Fiscal IR** : simulation IR annuelle

**Règle cardinale** : Le SheetsAdapter ne doit **jamais écrire** dans ces onglets.

### 6.2 Initialisation des Formules

À la création du Spreadsheet, initialiser les formules une fois :

```python
def init_formulas(self) -> None:
    """Initialiser formules des onglets calculés (à faire 1 seule fois)."""

    # Onglet Lettrage
    lettrage_sheet = self._get_sheet("Lettrage")
    lettrage_sheet.clear()
    lettrage_sheet.append_row([
        "facture_id", "montant_facture", "txn_id", "txn_montant",
        "ecart", "score_confiance", "statut"
    ])
    # Les formules sont rédigées en Google Sheets UI, pas ici

    # Onglet Balances
    balances_sheet = self._get_sheet("Balances")
    balances_sheet.clear()
    balances_sheet.append_row([
        "mois", "nb_factures", "ca_total", "recu_urssaf",
        "solde", "nb_non_lettrees", "nb_en_attente"
    ])
    # Formules : =SUMIF(...), =COUNTIF(...), etc.

    # Etc.
    logger.info("Formulas initialized")
```

### 6.3 Lecture Seule des Formules

SheetsAdapter expose des méthodes pour lire ces onglets :

```python
def read_lettrage(self) -> list[dict]:
    """Lire résultats lettrage (formules calculées)."""
    return self._get_sheet("Lettrage").get_all_records()

def read_balances(self) -> list[dict]:
    """Lire résultats balances (formules calculées)."""
    return self._get_sheet("Balances").get_all_records()
```

---

## 7. Authentification Google — Service Account

### 7.1 Setup Service Account

1. **Google Cloud Console** : Créer projet "SAP-Facture"
2. **APIs activées** :
   - Google Sheets API v4
   - Google Drive API
3. **Service Account** : Créer compte service, générer clé JSON
4. **Partage Spreadsheet** : Donner access au email du service account (xxx@xxx.iam.gserviceaccount.com)

### 7.2 Format Credentials

Fichier `credentials.json` (structure Google standard) :

```json
{
  "type": "service_account",
  "project_id": "sap-facture-123456",
  "private_key_id": "abcd1234...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
  "client_email": "sap-facture@sap-facture-123456.iam.gserviceaccount.com",
  "client_id": "1234567890...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

### 7.3 Variables d'Environnement

```bash
# .env (jamais committé)
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json
# OU
GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'

GOOGLE_SHEETS_ID=1a2b3c4d5e6f7g8h9i0j
```

### 7.4 Code Initialisation

```python
import os
from dotenv import load_dotenv

load_dotenv()

adapter = SheetsAdapter(
    spreadsheet_id=os.getenv("GOOGLE_SHEETS_ID"),
    credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH"),
    # ou credentials_json=os.getenv("GOOGLE_CREDENTIALS_JSON")
)
```

---

## 8. Structure du Spreadsheet

### 8.1 Spreadsheet ID et Ranges Nommés

```
Google Sheets URL: https://docs.google.com/spreadsheets/d/1a2b3c4d5e6f7g8h9i0j/edit

Spreadsheet ID: 1a2b3c4d5e6f7g8h9i0j

Onglets (Worksheets) :
┌─────────────┬──────────┬─────────────┐
│ Nom         │ gid      │ Plage       │
├─────────────┼──────────┼─────────────┤
│ Clients     │ 0        │ A1:L1000    │
│ Factures    │ 1        │ A1:O1000    │
│ Transactions│ 2        │ A1:J1000    │
│ Lettrage    │ 3        │ A1:G1000    │
│ Balances    │ 4        │ A1:G1000    │
│ Metrics NOVA│ 5        │ A1:F1000    │
│ Cotisations │ 6        │ A1:G1000    │
│ Fiscal IR   │ 7        │ A1:H1000    │
└─────────────┴──────────┴─────────────┘
```

### 8.2 Named Ranges (optionnel)

Utile pour formules complexes :

```
ClientsData      = Clients!A2:L
FacturesData     = Factures!A2:O
TransactionsData = Transactions!A2:J
LettrageData     = Lettrage!A2:G
```

### 8.3 Protections de Feuille

Pour éviter édits manuels accidentels :

```python
# À faire dans Google Sheets UI :
# Onglets éditables : Clients, Factures, Transactions (warn only)
# Onglets calculés : Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR (locked)
```

---

## 9. Gestion des Erreurs

### 9.1 Erreurs Courantes & Stratégies

| Erreur | Cause | Stratégie |
|--------|-------|-----------|
| `RESOURCE_EXHAUSTED` | Quota API dépassé | Retry exponential + fallback cache périmé |
| `DEADLINE_EXCEEDED` | Timeout réseau | Retry exponential (3x) |
| `PERMISSION_DENIED` | Service account pas autorisé | Log + skip (ne pas retry) |
| `NOT_FOUND` | Spreadsheet/worksheet supprimé | Log + exception (nécessite intervention) |
| `ALREADY_EXISTS` | Onglet dupliqué | Log + continue |
| `INVALID_ARGUMENT` | Plage ou donnée invalide | Validate avant écrire (Pydantic) |

### 9.2 Exception Handling Pydantic

```python
def read_clients(self) -> list[ClientRow]:
    sheet = self._get_sheet("Clients")
    rows = sheet.get_all_records()

    clients = []
    for i, row in enumerate(rows):
        try:
            client = ClientRow(**row)
            clients.append(client)
        except ValidationError as e:
            logger.error(f"Invalid client row {i+2}: {e}")
            # Choix : skip ou raise ?
            # Pour MVP : skip et continue
            continue

    return clients
```

### 9.3 Logging Structuré

```python
logger = logging.getLogger(__name__)

# Format
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Exemples
logger.info("Read 42 clients from Sheets", extra={"sheet": "Clients", "count": 42})
logger.warning("Quota exceeded, using stale cache", extra={"age_seconds": 600})
logger.error("Failed to write invoice", exc_info=True)
```

---

## 10. Patterns de Test

### 10.1 Mock gspread

```python
import pytest
from unittest.mock import Mock, MagicMock, patch
from sheets_adapter import SheetsAdapter, ClientRow, InvoiceRow

@pytest.fixture
def mock_gspread_client():
    """Mock client gspread."""
    client = MagicMock()
    workbook = MagicMock()
    worksheet = MagicMock()

    # Mock get_all_records()
    worksheet.get_all_records.return_value = [
        {
            "client_id": "client-1",
            "nom": "Alice",
            "prenom": "Dupont",
            "email": "alice@example.com",
            "telephone": None,
            "adresse": "123 Rue de la Paix",
            "code_postal": "75000",
            "ville": "Paris",
            "urssaf_id": None,
            "statut_urssaf": "EN_ATTENTE",
            "date_inscription": "2026-03-01",
            "actif": True,
        }
    ]

    workbook.worksheet.return_value = worksheet
    client.open_by_key.return_value = workbook

    return client, workbook, worksheet

@pytest.fixture
def mock_credentials():
    """Mock Google credentials."""
    with patch("sheets_adapter.Credentials.from_service_account_info"):
        with patch("sheets_adapter.gspread.authorize") as mock_auth:
            mock_client = MagicMock()
            mock_auth.return_value = mock_client
            yield mock_client
```

### 10.2 Fixture SheetsAdapter

```python
@pytest.fixture
def sheets_adapter(mock_gspread_client, mock_credentials):
    """Créer adapter avec mocks."""
    client, workbook, worksheet = mock_gspread_client

    adapter = SheetsAdapter(
        spreadsheet_id="fake-id-123",
        credentials_json='{"type": "service_account", "project_id": "test"}',
    )

    # Overrider client auth
    adapter._auth_client = client
    adapter.workbook = workbook

    return adapter
```

### 10.3 Test Cases

```python
class TestSheetsAdapterRead:
    """Tests lecture."""

    def test_read_clients_returns_valid_list(self, sheets_adapter):
        """Lire clients retourne liste ClientRow."""
        clients = sheets_adapter.read_clients()

        assert len(clients) == 1
        assert clients[0].client_id == "client-1"
        assert clients[0].nom == "Alice"

    def test_read_clients_uses_cache(self, sheets_adapter):
        """Cache valide retourne data cached."""
        # 1er appel
        clients1 = sheets_adapter.read_clients()

        # 2e appel (cache doit être valide, donc pas d'appel API)
        sheets_adapter._get_sheet("Clients").get_all_records.reset_mock()
        clients2 = sheets_adapter.read_clients()

        # Vérifier que get_all_records() n'a pas été appelé 2e fois
        sheets_adapter._get_sheet("Clients").get_all_records.assert_not_called()

    def test_read_clients_invalid_row_raises_validation_error(self, sheets_adapter):
        """Ligne invalide lève ValidationError."""
        sheets_adapter._get_sheet("Clients").get_all_records.return_value = [
            {"client_id": "", "nom": "Test"}  # client_id vide = invalide
        ]

        with pytest.raises(ValidationError):
            sheets_adapter.read_clients()


class TestSheetsAdapterWrite:
    """Tests écriture."""

    def test_write_client_appends_new_client(self, sheets_adapter):
        """Écrire client neuf → append."""
        new_client = ClientRow(
            client_id="client-2",
            nom="Bob",
            prenom="Martin",
            email="bob@example.com",
            adresse="456 Avenue",
            code_postal="75001",
            ville="Paris",
            urssaf_id=None,
            statut_urssaf="EN_ATTENTE",
            date_inscription="2026-03-02",
            actif=True,
        )

        sheets_adapter.write_client(new_client)

        # Vérifier que append_row() a été appelé
        sheets_adapter._get_sheet("Clients").append_row.assert_called_once()

    def test_write_invoice_invalidates_cache(self, sheets_adapter):
        """Écrire facture invalidate cache."""
        invoice = InvoiceRow(
            facture_id="INV-001",
            client_id="client-1",
            type_unite="HEURE",
            nature_code="120",
            quantite=10.0,
            montant_unitaire=25.0,
            montant_total=250.0,
            date_debut="2026-03-01",
            date_fin="2026-03-31",
            description="Test",
            statut="BROUILLON",
        )

        # Remplir cache
        sheets_adapter.read_invoices()
        assert "invoices:all" in sheets_adapter._cache

        # Écrire
        sheets_adapter.write_invoice(invoice)

        # Vérifier cache invalidé
        assert "invoices:all" not in sheets_adapter._cache


class TestSheetsAdapterError:
    """Tests gestion erreurs."""

    def test_quota_exceeded_uses_stale_cache(self, sheets_adapter):
        """Quota exceeded → fallback cache périmé."""
        # Remplir cache
        clients1 = sheets_adapter.read_clients()

        # Forcer erreur quota
        sheets_adapter._get_sheet("Clients").get_all_records.side_effect = \
            gspread.exceptions.APIError("RESOURCE_EXHAUSTED")

        # Invalider cache (le rendre périmé)
        sheets_adapter._cache["clients:all"] = (
            sheets_adapter._cache["clients:all"][0],
            datetime.now() - timedelta(hours=1)  # 1h old
        )

        # Relire : doit retourner stale cache sans raise
        clients2 = sheets_adapter.read_clients()
        assert len(clients2) == 1
```

### 10.4 Integration Test avec Spreadsheet Réel

```python
@pytest.mark.integration
def test_sheets_adapter_with_real_spreadsheet():
    """Test avec Spreadsheet réel (sandbox test suite)."""
    import os

    spreadsheet_id = os.getenv("TEST_SPREADSHEET_ID")
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

    if not spreadsheet_id:
        pytest.skip("TEST_SPREADSHEET_ID not set")

    adapter = SheetsAdapter(
        spreadsheet_id=spreadsheet_id,
        credentials_path=credentials_path,
    )

    # Vérifier connexion
    assert adapter.health_check()

    # Lire clients
    clients = adapter.read_clients()
    assert isinstance(clients, list)

    # Écrire test client
    test_client = ClientRow(
        client_id=f"test-{datetime.now().timestamp()}",
        nom="Test",
        prenom="User",
        email="test@example.com",
        adresse="Test",
        code_postal="75000",
        ville="Paris",
        urssaf_id=None,
        statut_urssaf="EN_ATTENTE",
        date_inscription=datetime.now().strftime("%Y-%m-%d"),
        actif=True,
    )
    adapter.write_client(test_client)

    # Vérifier client écrit
    read_client = adapter.read_client_by_id(test_client.client_id)
    assert read_client is not None
    assert read_client.nom == "Test"
```

---

## 11. Considérations Opérationnelles

### 11.1 Déploiement

```bash
# Installation dépendances
pip install gspread>=6.1.0 google-auth>=2.25.0 pydantic>=2.0.0

# Configuration
export GOOGLE_SHEETS_ID=1a2b3c4d5e6f7g8h9i0j
export GOOGLE_CREDENTIALS_PATH=/secrets/credentials.json

# Tests
pytest tests/test_sheets_adapter.py -v --cov=sheets_adapter
```

### 11.2 Monitoring

```python
def setup_monitoring() -> None:
    """Configurer métriques pour observabilité."""
    import logging.handlers

    # Log rotation (daily, max 10 fichiers)
    handler = logging.handlers.RotatingFileHandler(
        "logs/sheets_adapter.log",
        maxBytes=10_000_000,
        backupCount=10,
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logging.getLogger("sheets_adapter").addHandler(handler)

    # Metrics (optionnel : Prometheus, DataDog, etc.)
    # adapter.read_latency_seconds
    # adapter.quota_usage_pct
    # adapter.cache_hit_ratio
```

### 11.3 Quotas Google Sheets API

**Limites** :
- 500 requêtes / 100 secondes par projet
- 40 000 requêtes / jour par utilisateur

**Stratégie MVP** : Batch opérations, cache 5min → facile respex quotas.

### 11.4 Incident Response

Cas d'échec :

```
Symptôme: APIError RESOURCE_EXHAUSTED
→ Attendre 100s, retry
→ Si persiste: diminuer fréquence polling (4h → 8h)

Symptôme: Spreadsheet corrompu (headers manquants)
→ Revert backup manuel de Sheets
→ Alert DevOps

Symptôme: Service account révoqué
→ Régénérer credentials
→ Redéployer .env
```

---

## 12. Roadmap Futures Améliorations

### Phase 3

- **WebHooks URSSAF** : Recevoir events au lieu de polling 4h
- **Sync bidirectionnel** : Changes Sheets → API, API → Sheets
- **Audit trail** : Logger qui a modifié quoi, quand
- **Offline mode** : Workqueue local si connexion perdue

### Considérations Performance

- **Pagination** : Pour sheets > 10k lignes, implémenter pagination
- **Lazy loading** : Charger onglets seulement si accès
- **Compression cache** : Compresser cache > 50 MB

---

## Annexe A : Diagramme Séquence

```
┌─────────┐          ┌──────────────┐          ┌────────────────┐
│InvoiceS │          │SheetsAdapter │          │Google Sheets   │
└────┬────┘          └──────┬───────┘          │API v4          │
     │                      │                   └────────┬────────┘
     │ write_invoice()      │                           │
     ├──────────────────────>                           │
     │                      │ Cache valid?              │
     │                      ├──────────────────┐        │
     │                      │ (5 min TTL)      │        │
     │                      │<─────────────────┘        │
     │                      │ read_clients()            │
     │                      ├───────────────────────────>
     │                      │  [API CALL 1]             │
     │                      │                           │
     │                      │<───────────────────────────
     │                      │ [{client_1}, ...]         │
     │                      │ Cache updated             │
     │                      │ update_invoice()          │
     │                      ├───────────────────────────>
     │                      │  [API CALL 2]             │
     │                      │<───────────────────────────
     │                      │ OK                        │
     │<─────────────────────┤                           │
     │ Success              │                           │
     │                      │ Invalidate cache          │
     │                      │ ("invoices", "balances")  │
```

---

## Annexe B : Configuration Exemple

```python
# src/config.py
from pydantic_settings import BaseSettings

class GoogleSheetsConfig(BaseSettings):
    """Configuration Google Sheets."""

    spreadsheet_id: str
    credentials_path: Optional[str] = None
    credentials_json: Optional[str] = None
    cache_ttl_seconds: int = 300
    cache_enabled: bool = True
    cache_max_size_mb: int = 50

    class Config:
        env_prefix = "GOOGLE_"
        env_file = ".env"

# Usage
from src.sheets_adapter import SheetsAdapter, CacheConfig

config = GoogleSheetsConfig()
adapter = SheetsAdapter(
    spreadsheet_id=config.spreadsheet_id,
    credentials_json=config.credentials_json,
    cache_config=CacheConfig(
        ttl_seconds=config.cache_ttl_seconds,
        enabled=config.cache_enabled,
        max_size_mb=config.cache_max_size_mb,
    ),
)
```

---

## Conclusion

Le **SheetsAdapter** est le fondement technique de SAP-Facture. Sa conception prioritise :

1. **Centralisation** : Unique point d'accès à Google Sheets
2. **Efficacité** : Batch opérations, cache 5min, 1 appel par op
3. **Résilience** : Retry exponential, fallback cache, graceful degradation
4. **Testabilité** : Mocks complets, fixtures, tests d'intégration
5. **Clarté** : Type hints strictes, Pydantic validation, logging structuré

**Scope Phase 2** : Implémenter cette spec en entier + 80% couverture tests.

---

**Version** : 1.0
**Date** : Mars 2026
**Auteur** : Winston (BMAD System Architect)
**Statut** : Spécification validée, prêt pour implémentation Phase 2
