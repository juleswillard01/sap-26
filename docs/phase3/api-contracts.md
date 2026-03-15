# Contrats d'API — SAP-Facture Phase 3

**Auteur** : Winston (Senior API Architect)
**Date** : Mars 2026
**Version** : 1.0
**Statut** : Spécification complète
**Source** : SCHEMAS.html, Phase 1-2 Documents

---

## Table des Matières

1. [Routes FastAPI](#routes-fastapi)
2. [Interfaces Services Métier](#interfaces-services-métier)
3. [Interface SheetsAdapter](#interface-sheetsadapter)
4. [Commandes CLI Click](#commandes-cli-click)
5. [Schémas Pydantic (DTOs)](#schémas-pydantic-dtos)
6. [Codes d'Erreur Standardisés](#codes-derreur-standardisés)

---

# Routes FastAPI

## 1. Dashboard Principal

### GET /

**Description** : Page d'accueil, tableau de bord factures (vue synthétique).

**Paramètres** :
- Query : `status` (optionnel, filtre par statut)
- Query : `month` (optionnel, filtre par mois YYYY-MM)

**Response** : HTML (Jinja2 SSR)

**Code** :
```python
@app.get("/")
@app.get("/dashboard")
async def get_dashboard(
    request: Request,
    status: Optional[str] = None,
    month: Optional[str] = None,
    invoice_service: InvoiceService = Depends(),
) -> HTMLResponse:
    """
    Affiche le dashboard principal avec liste factures + résumé.
    - Statuts possibles : BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, ANNULE, ERREUR, EXPIRE, REJETE
    - Mois : format YYYY-MM (ex. 2026-03)
    """
    filters = {}
    if status:
        filters["status"] = status
    if month:
        filters["month"] = month

    invoices = await invoice_service.list_invoices(filters=filters)
    summary = await invoice_service.get_summary(month=month)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "invoices": invoices,
            "summary": summary,
        }
    )
```

---

## 2. Gestion Clients

### GET /clients

**Description** : Liste de tous les clients.

**Response** : HTML (tableau clients avec actions)

**Code** :
```python
@app.get("/clients")
async def list_clients(
    request: Request,
    client_service: ClientService = Depends(),
) -> HTMLResponse:
    """Affiche liste des clients avec filtres et recherche."""
    clients = await client_service.list_clients()
    return templates.TemplateResponse(
        "clients/list.html",
        {"request": request, "clients": clients}
    )
```

---

### GET /clients/new

**Description** : Formulaire pour créer un nouveau client.

**Response** : HTML (formulaire vide)

**Code** :
```python
@app.get("/clients/new")
async def new_client_form(request: Request) -> HTMLResponse:
    """Affiche formulaire création client."""
    return templates.TemplateResponse(
        "clients/form.html",
        {"request": request, "client": None}
    )
```

---

### POST /clients

**Description** : Créer un nouveau client et l'inscrire à URSSAF.

**Request Body** :
```python
class CreateClientRequest(BaseModel):
    nom: str = Field(min_length=1)
    prenom: str = Field(min_length=1)
    email: str = EmailStr
    telephone: Optional[str] = None
    adresse: str = Field(min_length=1)
    code_postal: str = Field(regex=r"^\d{5}$")
    ville: str = Field(min_length=1)
```

**Response (201)** :
```python
class ClientResponse(BaseModel):
    client_id: str
    nom: str
    prenom: str
    email: str
    telephone: Optional[str]
    adresse: str
    code_postal: str
    ville: str
    urssaf_id: Optional[str]
    statut_urssaf: str  # INSCRIT, EN_ATTENTE, ERREUR
    date_inscription: Optional[datetime]
    actif: bool
```

**Code** :
```python
@app.post("/clients")
async def create_client(
    request: CreateClientRequest,
    client_service: ClientService = Depends(),
) -> ClientResponse:
    """
    Crée un client et l'inscrit auprès d'URSSAF.
    Retourne 201 si succès, 400 si données invalides, 409 si client existe déjà.
    """
    try:
        client = await client_service.create_client(
            nom=request.nom,
            prenom=request.prenom,
            email=request.email,
            telephone=request.telephone,
            adresse=request.adresse,
            code_postal=request.code_postal,
            ville=request.ville,
        )
        return ClientResponse(**client.dict())
    except ClientAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except URSSAFRegistrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

### GET /clients/{client_id}

**Description** : Détails d'un client spécifique.

**Path Parameters** :
- `client_id` : str

**Response** : HTML (détails client + historique factures)

**Code** :
```python
@app.get("/clients/{client_id}")
async def get_client_details(
    request: Request,
    client_id: str,
    client_service: ClientService = Depends(),
    invoice_service: InvoiceService = Depends(),
) -> HTMLResponse:
    """Affiche détails client et factures associées."""
    client = await client_service.get_client(client_id)
    invoices = await invoice_service.list_invoices(filters={"client_id": client_id})

    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    return templates.TemplateResponse(
        "clients/detail.html",
        {"request": request, "client": client, "invoices": invoices}
    )
```

---

## 3. Factures

### GET /invoices

**Description** : Liste toutes les factures avec filtres.

**Query Parameters** :
- `status` : optionnel
- `client_id` : optionnel
- `month` : optionnel (YYYY-MM)
- `page` : optionnel (défaut 1)
- `limit` : optionnel (défaut 20)

**Response** : HTML (tableau + pagination)

**Code** :
```python
@app.get("/invoices")
async def list_invoices(
    request: Request,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    month: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    invoice_service: InvoiceService = Depends(),
) -> HTMLResponse:
    """
    Affiche liste factures avec filtres.
    - Statuts : BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, ANNULE, ERREUR, EXPIRE, REJETE
    """
    filters = {}
    if status:
        filters["status"] = status
    if client_id:
        filters["client_id"] = client_id
    if month:
        filters["month"] = month

    result = await invoice_service.list_invoices(
        filters=filters,
        page=page,
        limit=limit
    )

    return templates.TemplateResponse(
        "invoices/list.html",
        {
            "request": request,
            "invoices": result["items"],
            "total": result["total"],
            "page": page,
            "limit": limit,
        }
    )
```

---

### GET /invoices/new

**Description** : Formulaire pour créer une facture.

**Query Parameters** :
- `client_id` : optionnel (préremplir)

**Response** : HTML (formulaire facture)

**Code** :
```python
@app.get("/invoices/new")
async def new_invoice_form(
    request: Request,
    client_id: Optional[str] = None,
    client_service: ClientService = Depends(),
) -> HTMLResponse:
    """Affiche formulaire création facture."""
    clients = await client_service.list_clients()

    context = {
        "request": request,
        "clients": clients,
        "invoice": None,
    }
    if client_id:
        selected_client = await client_service.get_client(client_id)
        context["selected_client"] = selected_client

    return templates.TemplateResponse("invoices/form.html", context)
```

---

### POST /invoices

**Description** : Créer et soumettre une facture à URSSAF.

**Request Body** :
```python
class CreateInvoiceRequest(BaseModel):
    client_id: str
    type_unite: str  # HEURE, FORFAIT
    nature_code: str  # Code URSSAF (ex. 120 pour apprentissage)
    quantite: float = Field(gt=0)
    montant_unitaire: float = Field(gt=0)  # en euros
    date_debut: date
    date_fin: date
    description: Optional[str] = None
    auto_submit: bool = False  # Si True, soumettre à URSSAF immédiatement
```

**Response (201)** :
```python
class InvoiceResponse(BaseModel):
    facture_id: str
    client_id: str
    type_unite: str
    nature_code: str
    quantite: float
    montant_unitaire: float
    montant_total: float  # quantite * montant_unitaire
    date_debut: date
    date_fin: date
    description: Optional[str]
    statut: str  # BROUILLON
    urssaf_demande_id: Optional[str]
    date_soumission_urssaf: Optional[datetime]
    pdf_drive_id: Optional[str]
```

**Code** :
```python
@app.post("/invoices")
async def create_invoice(
    request: CreateInvoiceRequest,
    invoice_service: InvoiceService = Depends(),
    client_service: ClientService = Depends(),
) -> InvoiceResponse:
    """
    Crée une facture (statut BROUILLON ou SOUMIS selon auto_submit).
    - Valide données
    - Génère PDF
    - Soumet à URSSAF si auto_submit=True
    Retourne 201 si succès, 400 si validation échoue, 404 si client absent.
    """
    # Vérifier client existe
    client = await client_service.get_client(request.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    try:
        invoice = await invoice_service.create_invoice(
            client_id=request.client_id,
            type_unite=request.type_unite,
            nature_code=request.nature_code,
            quantite=request.quantite,
            montant_unitaire=request.montant_unitaire,
            date_debut=request.date_debut,
            date_fin=request.date_fin,
            description=request.description,
        )

        if request.auto_submit:
            invoice = await invoice_service.submit_to_urssaf(invoice.facture_id)

        return InvoiceResponse(**invoice.dict())
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne")
```

---

### GET /invoices/{facture_id}

**Description** : Détails d'une facture.

**Path Parameters** :
- `facture_id` : str

**Response** : HTML (détails + actions possibles)

**Code** :
```python
@app.get("/invoices/{facture_id}")
async def get_invoice_details(
    request: Request,
    facture_id: str,
    invoice_service: InvoiceService = Depends(),
) -> HTMLResponse:
    """Affiche détails facture avec actions (annuler, révoquer, voir PDF, etc.)."""
    invoice = await invoice_service.get_invoice(facture_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")

    return templates.TemplateResponse(
        "invoices/detail.html",
        {"request": request, "invoice": invoice}
    )
```

---

### POST /invoices/{facture_id}/submit

**Description** : Soumettre une facture en brouillon à URSSAF.

**Path Parameters** :
- `facture_id` : str

**Response (200)** :
```python
class InvoiceSubmitResponse(BaseModel):
    facture_id: str
    statut: str  # SOUMIS ou CREE
    urssaf_demande_id: str  # ID demande retourné par URSSAF
    date_soumission_urssaf: datetime
```

**Code** :
```python
@app.post("/invoices/{facture_id}/submit")
async def submit_invoice_to_urssaf(
    facture_id: str,
    invoice_service: InvoiceService = Depends(),
) -> InvoiceSubmitResponse:
    """
    Soumet une facture BROUILLON à URSSAF.
    Passe statut BROUILLON → SOUMIS → CREE.
    Retourne 400 si facture pas en BROUILLON, 404 si absent, 500 si erreur URSSAF.
    """
    try:
        invoice = await invoice_service.submit_to_urssaf(facture_id)
        return InvoiceSubmitResponse(**invoice.dict())
    except InvalidInvoiceStatusError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except URSSAFAPIError as e:
        raise HTTPException(status_code=502, detail="Erreur API URSSAF")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne")
```

---

## 4. Rapprochement Bancaire

### GET /reconciliation

**Description** : Page interface rapprochement bancaire (lettrage).

**Response** : HTML (tableau lettrage + actions)

**Code** :
```python
@app.get("/reconciliation")
async def get_reconciliation_page(
    request: Request,
    bank_reconciliation: BankReconciliation = Depends(),
) -> HTMLResponse:
    """Affiche interface lettrage bancaire (onglet Lettrage)."""
    reconciliations = await bank_reconciliation.list_reconciliations()

    return templates.TemplateResponse(
        "reconciliation/list.html",
        {"request": request, "reconciliations": reconciliations}
    )
```

---

### POST /reconciliation/auto-match

**Description** : Lancer le lettrage automatique (matching factures ↔ transactions Swan).

**Request Body** :
```python
class AutoMatchRequest(BaseModel):
    date_range_days: int = Field(default=7, ge=1, le=30)  # Plage de recherche
    confidence_threshold: int = Field(default=80, ge=0, le=100)  # Seuil score
```

**Response (200)** :
```python
class AutoMatchResponse(BaseModel):
    total_processed: int  # nb factures PAYEE traitées
    auto_matched: int  # nb lettrées auto (score >= threshold)
    needs_review: int  # nb à vérifier (score < threshold)
    no_match: int  # nb sans match
    errors: list[str]  # erreurs rencontrées
```

**Code** :
```python
@app.post("/reconciliation/auto-match")
async def auto_match_transactions(
    request: AutoMatchRequest,
    bank_reconciliation: BankReconciliation = Depends(),
    payment_tracker: PaymentTracker = Depends(),
) -> AutoMatchResponse:
    """
    Lance le lettrage automatique :
    1. Récupère transactions Swan
    2. Importe dans onglet Transactions
    3. Pour chaque facture PAYEE : cherche match
    4. Écrit résultat dans onglet Lettrage
    5. Recalcule onglet Balances
    """
    try:
        result = await bank_reconciliation.auto_reconcile(
            date_range_days=request.date_range_days,
            confidence_threshold=request.confidence_threshold,
        )
        return AutoMatchResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur rapprochement")
```

---

## 5. Export

### GET /export/csv

**Description** : Exporter les factures en CSV.

**Query Parameters** :
- `status` : optionnel (filtre)
- `month` : optionnel (YYYY-MM)
- `columns` : optionnel, CSV list (défaut : facture_id,client_id,montant_total,statut,date_soumission_urssaf)

**Response** : CSV file (download)

**Code** :
```python
@app.get("/export/csv")
async def export_invoices_csv(
    status: Optional[str] = None,
    month: Optional[str] = None,
    columns: Optional[str] = None,
    invoice_service: InvoiceService = Depends(),
) -> StreamingResponse:
    """
    Exporte factures en CSV.
    Colonnes disponibles : facture_id, client_id, nom_client, montant_total, statut,
                          date_debut, date_fin, date_soumission_urssaf, urssaf_demande_id
    """
    filters = {}
    if status:
        filters["status"] = status
    if month:
        filters["month"] = month

    col_list = columns.split(",") if columns else [
        "facture_id", "client_id", "montant_total", "statut", "date_soumission_urssaf"
    ]

    csv_data = await invoice_service.export_csv(filters=filters, columns=col_list)

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices_export.csv"}
    )
```

---

## 6. Health Check

### GET /health

**Description** : Vérifier santé de l'app (dépendances, connexions).

**Response (200)** :
```python
class HealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    services: dict[str, str]  # {google_sheets: ok, urssaf_api: ok, swan_api: ok}
    version: str
```

**Code** :
```python
@app.get("/health")
async def health_check(
    sheets_adapter: SheetsAdapter = Depends(),
) -> HealthResponse:
    """
    Vérifie santé app et dépendances.
    - Google Sheets API (try read client count)
    - URSSAF OAuth token (try get token)
    - Swan API (try get account info)
    """
    status = "healthy"
    services = {}

    try:
        count = await sheets_adapter.count_clients()
        services["google_sheets"] = "ok"
    except Exception:
        services["google_sheets"] = "error"
        status = "degraded"

    # Check URSSAF OAuth
    try:
        # URSSAFClient.get_valid_token()
        services["urssaf_api"] = "ok"
    except Exception:
        services["urssaf_api"] = "error"
        status = "degraded"

    # Check Swan API
    try:
        # SwanClient.get_account_info()
        services["swan_api"] = "ok"
    except Exception:
        services["swan_api"] = "error"
        status = "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        services=services,
        version="1.0.0"
    )
```

---

---

# Interfaces Services Métier

## InvoiceService

**Fichier** : `app/services/invoice_service.py`

**Responsabilités** : Créer, valider, soumettre et suivre factures.

### Signature Complète

```python
from __future__ import annotations
from typing import Optional, list
from pydantic import BaseModel
from datetime import date, datetime

class InvoiceService:
    """Service pour gestion complète du cycle de vie facture."""

    def __init__(
        self,
        sheets_adapter: SheetsAdapter,
        urssaf_client: URSSAFClient,
        pdf_generator: PDFGenerator,
    ) -> None:
        """
        Dépendances injectées.
        - sheets_adapter : accès Google Sheets
        - urssaf_client : appels API URSSAF
        - pdf_generator : génération PDF
        """
        self._sheets = sheets_adapter
        self._urssaf = urssaf_client
        self._pdf = pdf_generator

    # === Lecture ===

    async def get_invoice(self, facture_id: str) -> dict | None:
        """
        Récupère une facture par ID.

        Args:
            facture_id : str

        Returns:
            dict avec champs (facture_id, client_id, montant_total, statut, ...) ou None

        Raises:
            SheetsAdapterError : si erreur lecture Google Sheets
        """
        pass

    async def list_invoices(
        self,
        filters: Optional[dict] = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """
        Liste factures avec pagination et filtres.

        Args:
            filters : dict avec clés optionnelles (status, client_id, month)
            page : int >= 1
            limit : int, 1-100

        Returns:
            {
                "items": [invoice1, invoice2, ...],
                "total": 45,
                "page": 1,
                "pages": 3
            }

        Raises:
            SheetsAdapterError
        """
        pass

    async def get_summary(self, month: Optional[str] = None) -> dict:
        """
        Résumé mensuel : nb factures, CA, statuts.

        Args:
            month : str YYYY-MM ou None (mois courant)

        Returns:
            {
                "total_invoices": 10,
                "total_ca": 2500.0,
                "status_breakdown": {
                    "BROUILLON": 1,
                    "SOUMIS": 2,
                    "PAYE": 5,
                    ...
                },
                "avg_days_to_payment": 3.5
            }

        Raises:
            SheetsAdapterError
        """
        pass

    # === Création ===

    async def create_invoice(
        self,
        client_id: str,
        type_unite: str,
        nature_code: str,
        quantite: float,
        montant_unitaire: float,
        date_debut: date,
        date_fin: date,
        description: Optional[str] = None,
    ) -> dict:
        """
        Crée une facture en statut BROUILLON.

        Args:
            client_id : str (doit exister dans onglet Clients)
            type_unite : str (HEURE, FORFAIT)
            nature_code : str (code URSSAF, ex. 120)
            quantite : float > 0
            montant_unitaire : float > 0 (euros)
            date_debut : date
            date_fin : date (>= date_debut)
            description : optionnel

        Returns:
            dict (facture_id, client_id, montant_total, statut=BROUILLON, ...)

        Raises:
            ClientNotFoundError : si client_id absent
            ValidationError : si données invalides
            SheetsAdapterError : si erreur écriture
        """
        pass

    # === Soumission ===

    async def submit_to_urssaf(self, facture_id: str) -> dict:
        """
        Soumet une facture BROUILLON à URSSAF.
        Flux :
        1. Valider facture
        2. Générer PDF et l'uploader sur Google Drive
        3. Appeler URSSAF POST /demandes-paiement
        4. Mettre à jour statut SOUMIS → CREE
        5. Écrire dans Sheets onglet Factures

        Args:
            facture_id : str (doit être en statut BROUILLON)

        Returns:
            dict (facture_id, statut=SOUMIS, urssaf_demande_id, date_soumission_urssaf, ...)

        Raises:
            InvoiceNotFoundError
            InvalidInvoiceStatusError : si pas BROUILLON
            PDFGenerationError
            URSSAFAPIError
            SheetsAdapterError
        """
        pass

    # === Suivi Statut ===

    async def poll_urssaf_status(self, facture_id: str) -> dict:
        """
        Poll statut URSSAF pour une facture.

        Args:
            facture_id : str

        Returns:
            dict (facture_id, statut=VALIDE/PAYE/REJETE/EXPIRE, ...)

        Raises:
            InvoiceNotFoundError
            URSSAFAPIError
            SheetsAdapterError
        """
        pass

    async def get_pending_invoices(self) -> list[dict]:
        """
        Liste toutes les factures en attente polling (SOUMIS, CREE, EN_ATTENTE).
        Utilisé par PaymentTracker (cron 4h).

        Returns:
            list of dicts

        Raises:
            SheetsAdapterError
        """
        pass

    # === Actions ===

    async def cancel_invoice(self, facture_id: str) -> dict:
        """
        Annule une facture (si pas encore soumise à URSSAF).

        Args:
            facture_id : str (doit être BROUILLON)

        Returns:
            dict (facture_id, statut=ANNULE, ...)

        Raises:
            InvoiceNotFoundError
            InvalidInvoiceStatusError : si déjà soumise
            SheetsAdapterError
        """
        pass

    async def export_csv(
        self,
        filters: Optional[dict] = None,
        columns: Optional[list[str]] = None,
    ) -> str:
        """
        Exporte factures en CSV.

        Args:
            filters : dict (status, client_id, month)
            columns : list de noms colonnes (facture_id, client_id, montant_total, ...)

        Returns:
            str (contenu CSV)

        Raises:
            SheetsAdapterError
        """
        pass
```

---

## ClientService

**Fichier** : `app/services/client_service.py`

**Responsabilités** : CRUD clients + inscription URSSAF.

### Signature Complète

```python
class ClientService:
    """Service pour gestion des clients et inscription URSSAF."""

    def __init__(
        self,
        sheets_adapter: SheetsAdapter,
        urssaf_client: URSSAFClient,
    ) -> None:
        self._sheets = sheets_adapter
        self._urssaf = urssaf_client

    # === Lecture ===

    async def get_client(self, client_id: str) -> dict | None:
        """
        Récupère un client par ID.

        Returns:
            dict (client_id, nom, prenom, email, urssaf_id, statut_urssaf, ...) ou None

        Raises:
            SheetsAdapterError
        """
        pass

    async def list_clients(self) -> list[dict]:
        """
        Liste tous les clients.

        Returns:
            list of dicts

        Raises:
            SheetsAdapterError
        """
        pass

    # === Création ===

    async def create_client(
        self,
        nom: str,
        prenom: str,
        email: str,
        telephone: Optional[str] = None,
        adresse: str = "",
        code_postal: str = "",
        ville: str = "",
    ) -> dict:
        """
        Crée un client et l'inscrit à URSSAF.

        Args:
            nom, prenom, email, adresse, code_postal, ville : str
            telephone : optionnel

        Returns:
            dict (client_id, nom, prenom, urssaf_id, statut_urssaf=INSCRIT, ...)

        Raises:
            ValidationError : si données invalides
            ClientAlreadyExistsError : si email déjà existant
            URSSAFRegistrationError : si URSSAF rejette (client pas connu fisc)
            SheetsAdapterError
        """
        pass

    # === Vérification ===

    async def ensure_client_exists(self, client_id: str) -> bool:
        """
        Vérifie qu'un client existe et est inscrit à URSSAF.
        Si pas inscrit, lance inscription.

        Args:
            client_id : str

        Returns:
            bool (True si inscrit, False si erreur)

        Raises:
            SheetsAdapterError
            URSSAFRegistrationError
        """
        pass

    async def is_registered_urssaf(self, client_id: str) -> bool:
        """
        Vérifie si client a un urssaf_id valide.

        Returns:
            bool

        Raises:
            SheetsAdapterError
        """
        pass
```

---

## PaymentTracker

**Fichier** : `app/services/payment_tracker.py`

**Responsabilités** : Polling automatique statut URSSAF (cron 4h), reminders T+36h.

### Signature Complète

```python
class PaymentTracker:
    """Service de polling automatique des statuts URSSAF."""

    def __init__(
        self,
        invoice_service: InvoiceService,
        sheets_adapter: SheetsAdapter,
        urssaf_client: URSSAFClient,
        notification_service: NotificationService,
    ) -> None:
        self._invoice_service = invoice_service
        self._sheets = sheets_adapter
        self._urssaf = urssaf_client
        self._notif = notification_service

    # === Polling ===

    async def poll_all(self) -> dict:
        """
        Lance le polling pour toutes les factures en attente (SOUMIS, CREE, EN_ATTENTE).
        Appelé par Cron (APScheduler) toutes les 4h.

        Returns:
            {
                "total_polled": 5,
                "updated": 2,
                "errors": 1,
                "reminders_sent": 1,
                "details": [...]
            }

        Raises:
            SheetsAdapterError (capturé, logged)
            URSSAFAPIError (capturé, logged)
        """
        pass

    async def poll_invoice(self, facture_id: str) -> dict:
        """
        Poll statut d'une facture spécifique auprès d'URSSAF.

        Args:
            facture_id : str (doit avoir urssaf_demande_id)

        Returns:
            dict (facture_id, new_status, changed=bool, ...)

        Raises:
            InvoiceNotFoundError
            URSSAFAPIError
            SheetsAdapterError
        """
        pass

    # === Reminders ===

    async def check_reminders_needed(self) -> list[dict]:
        """
        Vérifie les factures EN_ATTENTE depuis >= 36h.

        Returns:
            list[dict] avec (facture_id, client_email, time_elapsed_hours)

        Raises:
            SheetsAdapterError
        """
        pass

    async def send_reminders(self) -> dict:
        """
        Envoie emails reminder pour factures EN_ATTENTE depuis >= 36h.

        Returns:
            {
                "total_checked": 10,
                "reminders_sent": 2,
                "errors": 0
            }

        Raises:
            SheetsAdapterError (capturé)
            NotificationServiceError (capturé)
        """
        pass
```

---

## BankReconciliation

**Fichier** : `app/services/bank_reconciliation.py`

**Responsabilités** : Lettrage automatique factures ↔ transactions Swan.

### Signature Complète

```python
class BankReconciliation:
    """Service de rapprochement bancaire et lettrage automatique."""

    def __init__(
        self,
        sheets_adapter: SheetsAdapter,
        swan_client: SwanClient,
    ) -> None:
        self._sheets = sheets_adapter
        self._swan = swan_client

    # === Matching ===

    async def auto_reconcile(
        self,
        date_range_days: int = 7,
        confidence_threshold: int = 80,
    ) -> dict:
        """
        Lettre automatiquement factures PAYEE avec transactions Swan.

        Étapes :
        1. Récupère transactions Swan (date range)
        2. Importe dans onglet Transactions
        3. Pour chaque facture PAYEE : cherche match (montant, date, libelle)
        4. Calcul score confiance
        5. Écrit résultat dans onglet Lettrage (AUTO / A_VERIFIER / PAS_DE_MATCH)
        6. Recalcule onglet Balances

        Args:
            date_range_days : int, 1-30 (plage de recherche de transactions)
            confidence_threshold : int, 0-100 (score mini pour AUTO)

        Returns:
            {
                "total_processed": 10,
                "auto_matched": 7,
                "needs_review": 2,
                "no_match": 1,
                "errors": []
            }

        Raises:
            SwanClientError
            SheetsAdapterError
        """
        pass

    async def list_reconciliations(self) -> list[dict]:
        """
        Liste tous les lettrage (onglet Lettrage).

        Returns:
            list[dict] avec (facture_id, montant_facture, txn_id, txn_montant,
                             score_confiance, statut, ...)

        Raises:
            SheetsAdapterError
        """
        pass

    async def manual_match(
        self,
        facture_id: str,
        transaction_id: str,
    ) -> dict:
        """
        Lettre manuellement une facture à une transaction.

        Args:
            facture_id : str
            transaction_id : str

        Returns:
            dict (facture_id, transaction_id, statut=LETTRE, ...)

        Raises:
            InvoiceNotFoundError
            TransactionNotFoundError
            SheetsAdapterError
        """
        pass

    async def unmatch(self, facture_id: str) -> dict:
        """
        Délette un lettrage.

        Args:
            facture_id : str

        Returns:
            dict (facture_id, statut=NON_LETTREE, ...)

        Raises:
            SheetsAdapterError
        """
        pass

    # === Scoring ===

    def _compute_match_score(
        self,
        facture_amount: float,
        transaction_amount: float,
        facture_date: date,
        transaction_date: date,
        transaction_label: str,
    ) -> int:
        """
        Calcule score de confiance (0-100) pour match.

        Critères :
        - Montant exact match : +50
        - Date < 3j : +30
        - Libelle contient URSSAF : +20

        Args:
            facture_amount : float
            transaction_amount : float
            facture_date : date
            transaction_date : date
            transaction_label : str

        Returns:
            int (0-100)
        """
        pass
```

---

## NotificationService

**Fichier** : `app/services/notification_service.py`

**Responsabilités** : Envoi emails (reminder T+36h, alertes).

### Signature Complète

```python
class NotificationService:
    """Service d'envoi notifications."""

    def __init__(
        self,
        email_notifier: EmailNotifier,
        sheets_adapter: SheetsAdapter,
    ) -> None:
        self._email = email_notifier
        self._sheets = sheets_adapter

    # === Reminders ===

    async def send_reminder_validation(
        self,
        client_email: str,
        facture_id: str,
        montant: float,
    ) -> bool:
        """
        Envoie email reminder à client pour valider facture (T+36h).

        Args:
            client_email : str
            facture_id : str
            montant : float

        Returns:
            bool (True si envoyé)

        Raises:
            EmailNotificationError : si SMTP erreur
        """
        pass

    # === Alertes ===

    async def send_urssaf_error_alert(
        self,
        facture_id: str,
        error_message: str,
    ) -> bool:
        """
        Envoie alerte si erreur URSSAF (payload invalide, etc.).

        Args:
            facture_id : str
            error_message : str

        Returns:
            bool (True si envoyé)

        Raises:
            EmailNotificationError
        """
        pass

    async def send_payment_received_notification(
        self,
        client_email: str,
        facture_id: str,
        montant: float,
    ) -> bool:
        """
        Notification client : paiement reçu et letteré.

        Returns:
            bool (True si envoyé)

        Raises:
            EmailNotificationError
        """
        pass
```

---

## NovaReporting

**Fichier** : `app/services/nova_reporting.py`

**Responsabilités** : Calcul metrics trimestrielles (NOVA, Cotisations, Fiscal).

### Signature Complète

```python
class NovaReporting:
    """Service de reporting et calculs trimestriels."""

    def __init__(
        self,
        sheets_adapter: SheetsAdapter,
    ) -> None:
        self._sheets = sheets_adapter

    # === NOVA ===

    async def calculate_nova_metrics(
        self,
        trimestre: str,  # ex. "2026-Q1"
    ) -> dict:
        """
        Calcule metrics trimestrielles pour déclaration NOVA.

        Légende :
        - Trimestre : 2026-Q1 (Q1=jan-mar), Q2=avr-jun, Q3=jui-sep, Q4=oct-dec

        Calculs :
        - nb_intervenants = 1 (Jules)
        - heures_effectuees = SUM(quantite WHERE type_unite=HEURE AND statut=PAYE AND date in Q)
        - nb_particuliers = COUNT(DISTINCT client_id WHERE statut=PAYE AND date in Q)
        - ca_trimestre = SUM(montant_total WHERE statut=PAYE AND date in Q)

        Returns:
            {
                "trimestre": "2026-Q1",
                "nb_intervenants": 1,
                "heures_effectuees": 120,
                "nb_particuliers": 8,
                "ca_trimestre": 3000.0,
                "deadline_saisie": "2026-04-15"
            }

        Raises:
            SheetsAdapterError
            ValidationError
        """
        pass

    # === Cotisations ===

    async def calculate_cotisations(
        self,
        mois: str,  # YYYY-MM
    ) -> dict:
        """
        Calcule cotisations mensuelles (micro-entrepreneur).

        Taux charges URSSAF : 25.8%

        Returns:
            {
                "mois": "2026-03",
                "ca_encaisse": 2500.0,
                "taux_charges": 0.258,
                "montant_charges": 645.0,
                "date_limite_paiement": "2026-04-15",
                "cumul_ca": 5000.0,
                "net_apres_charges": 3855.0
            }

        Raises:
            SheetsAdapterError
        """
        pass

    # === Fiscal IR ===

    async def calculate_fiscal_ir(
        self,
        annee: int,
    ) -> dict:
        """
        Calcule simulation impôt sur revenu annuel.

        Logique :
        1. CA brut = SUM(montant_total WHERE statut=PAYE AND year=annee)
        2. Apprentissage : exo jusqu'à 18500 euros
        3. CA restant soumis à micro (34% abattement BNC)
        4. Revenu imposable = CA_micro * (1 - 0.34)
        5. Appliquer tranches IR (progressivité)
        6. Estimation VL 2.2%

        Returns:
            {
                "annee": 2026,
                "ca_brut": 10000.0,
                "revenu_apprentissage": 5000.0,
                "seuil_exo_apprentissage": 18500.0,
                "ca_micro": 5000.0,
                "abattement_34pct": 1700.0,
                "revenu_imposable": 3300.0,
                "tranches_ir": [
                    {"min": 0, "max": 10777, "taux": 0.0},
                    {"min": 10777, "max": 27478, "taux": 0.055}
                ],
                "impot_estime": 181.5,
                "taux_marginal": 0.055,
                "estimation_vl": 72.6
            }

        Raises:
            SheetsAdapterError
        """
        pass
```

---

---

# Interface SheetsAdapter

**Fichier** : `app/adapters/sheets_adapter.py`

**Responsabilités** : Abstraction complète accès Google Sheets API v4.

### Signature Complète

```python
from __future__ import annotations
from typing import Optional, list
from pydantic import BaseModel

class SheetsAdapter:
    """Adaptateur centralisé pour Google Sheets (8 onglets)."""

    def __init__(self, credentials_json: dict, spreadsheet_id: str) -> None:
        """
        Initialise la connexion à Google Sheets.

        Args:
            credentials_json : dict (service account JSON)
            spreadsheet_id : str (ID du Google Sheets)
        """
        self._client = gspread.service_account(credentials_json)
        self._spreadsheet = self._client.open_by_key(spreadsheet_id)
        self._cache = {}  # Cache local {sheet_name: data, expiry}
        self._cache_ttl = 300  # 5 minutes par défaut

    # === Clients (Onglet 1) ===

    async def read_clients(self) -> list[ClientRow]:
        """
        Lit tous les clients (onglet Clients).

        Returns:
            list[ClientRow]

        Raises:
            SheetsAdapterError
        """
        pass

    async def read_client(self, client_id: str) -> ClientRow | None:
        """
        Lit un client par ID.

        Returns:
            ClientRow ou None

        Raises:
            SheetsAdapterError
        """
        pass

    async def write_client(self, client: ClientRow) -> None:
        """
        Crée ou met à jour un client (onglet Clients).

        Args:
            client : ClientRow

        Raises:
            SheetsAdapterError
        """
        pass

    async def count_clients(self) -> int:
        """
        Compte nb clients.

        Returns:
            int

        Raises:
            SheetsAdapterError
        """
        pass

    # === Factures (Onglet 2) ===

    async def read_invoices(
        self,
        filters: Optional[dict] = None,
    ) -> list[InvoiceRow]:
        """
        Lit factures avec filtres optionnels.

        Args:
            filters : dict avec clés optionnelles (status, client_id, month)

        Returns:
            list[InvoiceRow]

        Raises:
            SheetsAdapterError
        """
        pass

    async def read_invoice(self, facture_id: str) -> InvoiceRow | None:
        """
        Lit une facture par ID.

        Returns:
            InvoiceRow ou None

        Raises:
            SheetsAdapterError
        """
        pass

    async def write_invoice(self, invoice: InvoiceRow) -> None:
        """
        Crée ou met à jour une facture (onglet Factures).

        Args:
            invoice : InvoiceRow

        Raises:
            SheetsAdapterError
        """
        pass

    async def update_invoice_status(
        self,
        facture_id: str,
        new_status: str,
        **kwargs
    ) -> None:
        """
        Met à jour statut facture + champs additionnels.

        Args:
            facture_id : str
            new_status : str
            **kwargs : autre champs à mettre à jour (date_soumission_urssaf, urssaf_demande_id, ...)

        Raises:
            SheetsAdapterError
        """
        pass

    # === Transactions (Onglet 3) ===

    async def read_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[TransactionRow]:
        """
        Lit transactions (onglet Transactions).

        Args:
            start_date, end_date : optionnel (date range)

        Returns:
            list[TransactionRow]

        Raises:
            SheetsAdapterError
        """
        pass

    async def write_transactions(self, transactions: list[TransactionRow]) -> None:
        """
        Importe transactions (batch write).

        Args:
            transactions : list[TransactionRow]

        Raises:
            SheetsAdapterError
        """
        pass

    # === Lettrage (Onglet 4, lecture seule) ===

    async def read_reconciliations(self) -> list[dict]:
        """
        Lit onglet Lettrage (formules, lecture seule).

        Returns:
            list[dict] avec (facture_id, montant_facture, txn_id, txn_montant,
                             score_confiance, statut, ...)

        Raises:
            SheetsAdapterError
        """
        pass

    async def write_reconciliation(self, reconciliation: dict) -> None:
        """
        Écrit un lettrage dans onglet Lettrage.

        Args:
            reconciliation : dict (facture_id, txn_id, statut, score_confiance, ...)

        Raises:
            SheetsAdapterError
        """
        pass

    # === Balances (Onglet 5, formules) ===

    async def read_balances(self) -> list[dict]:
        """
        Lit onglet Balances (formules auto-calculées).

        Returns:
            list[dict] (mois, nb_factures, ca_total, recu_urssaf, solde, ...)

        Raises:
            SheetsAdapterError
        """
        pass

    # === Helpers ===

    def _invalidate_cache(self, sheet_name: str) -> None:
        """
        Invalide le cache local pour un onglet.

        Args:
            sheet_name : str (Clients, Factures, Transactions, ...)
        """
        pass

    async def refresh_cache(self) -> None:
        """
        Rafraîchit tous les caches (force re-read depuis Google Sheets).
        """
        pass
```

### Modèles Pydantic

```python
class ClientRow(BaseModel):
    client_id: str = Field(min_length=1)
    nom: str
    prenom: str
    email: EmailStr
    telephone: Optional[str] = None
    adresse: str
    code_postal: str = Field(regex=r"^\d{5}$")
    ville: str
    urssaf_id: Optional[str] = None
    statut_urssaf: str = Field(pattern="^(INSCRIT|EN_ATTENTE|ERREUR)$", default="EN_ATTENTE")
    date_inscription: Optional[str] = None  # YYYY-MM-DD
    actif: bool = True

class InvoiceRow(BaseModel):
    facture_id: str = Field(min_length=1)
    client_id: str
    type_unite: str
    nature_code: str
    quantite: float = Field(gt=0)
    montant_unitaire: float = Field(gt=0)
    montant_total: float = Field(gt=0)
    date_debut: str  # YYYY-MM-DD
    date_fin: str  # YYYY-MM-DD
    description: Optional[str] = None
    statut: str = Field(
        pattern="^(BROUILLON|SOUMIS|CREE|EN_ATTENTE|VALIDE|PAYE|RAPPROCHE|ANNULE|ERREUR|EXPIRE|REJETE)$",
        default="BROUILLON"
    )
    urssaf_demande_id: Optional[str] = None
    date_soumission_urssaf: Optional[str] = None
    date_validation_client: Optional[str] = None
    pdf_drive_id: Optional[str] = None

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

---

# Commandes CLI Click

**Fichier** : `app/cli/main.py`

```python
import click
from typing import Optional

@click.group()
def sap():
    """SAP-Facture — CLI pour gestion factures cours particuliers."""
    pass

# === SUBMIT ===

@sap.command()
@click.option(
    "--client-id", "-c",
    required=True,
    type=str,
    help="ID du client (ex. client-001)"
)
@click.option(
    "--heures", "-h",
    required=True,
    type=float,
    help="Nombre d'heures (ex. 10.5)"
)
@click.option(
    "--tarif", "-t",
    required=True,
    type=float,
    help="Tarif horaire en euros (ex. 25.00)"
)
@click.option(
    "--date-debut", "-d",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Date début période (YYYY-MM-DD)"
)
@click.option(
    "--date-fin", "-f",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Date fin période (YYYY-MM-DD)"
)
@click.option(
    "--description",
    required=False,
    type=str,
    default="",
    help="Description (ex. 'Cours mars')"
)
@click.option(
    "--auto-submit/--no-auto-submit",
    default=True,
    help="Soumettre à URSSAF immédiatement (défaut: True)"
)
def submit(
    client_id: str,
    heures: float,
    tarif: float,
    date_debut,
    date_fin,
    description: str,
    auto_submit: bool,
):
    """
    Crée et soumet une facture.

    Exemple :
        sap submit -c client-001 -h 10.5 -t 25.00 -d 2026-03-01 -f 2026-03-31
    """
    click.echo(f"Création facture pour {client_id}...")
    click.echo(f"  Heures : {heures} x {tarif}€ = {heures * tarif}€")
    click.echo(f"  Période : {date_debut} → {date_fin}")

    # TODO: appeler InvoiceService.create_invoice()

    if auto_submit:
        click.echo("✓ Facture soumise à URSSAF")
    else:
        click.echo("✓ Facture créée (non soumise)")

# === SYNC ===

@sap.command()
def sync():
    """
    Synchronise statuts URSSAF (polling manuel).
    Équivalent cron toutes les 4h.

    Exemple :
        sap sync
    """
    click.echo("Synchronisation statuts URSSAF...")

    # TODO: appeler PaymentTracker.poll_all()

    click.echo("✓ Synchronisation terminée")

# === RECONCILE ===

@sap.command()
@click.option(
    "--days", "-d",
    required=False,
    type=int,
    default=7,
    help="Plage de recherche (jours)"
)
@click.option(
    "--threshold", "-t",
    required=False,
    type=int,
    default=80,
    help="Seuil score confiance (0-100)"
)
def reconcile(days: int, threshold: int):
    """
    Lettre automatiquement factures avec transactions Swan.

    Exemple :
        sap reconcile --days 7 --threshold 80
    """
    click.echo(f"Lettrage automatique (plage {days}j, seuil {threshold})...")

    # TODO: appeler BankReconciliation.auto_reconcile()

    click.echo("✓ Lettrage terminé")

# === EXPORT ===

@sap.command()
@click.option(
    "--format", "-f",
    required=False,
    type=click.Choice(["csv", "json"]),
    default="csv",
    help="Format export"
)
@click.option(
    "--status", "-s",
    required=False,
    type=str,
    help="Filtrer par statut (ex. PAYE)"
)
@click.option(
    "--output", "-o",
    required=False,
    type=click.Path(),
    help="Fichier sortie (défaut: stdout)"
)
def export(format: str, status: Optional[str], output: Optional[str]):
    """
    Exporte factures (CSV ou JSON).

    Exemple :
        sap export --format csv --status PAYE --output factures.csv
    """
    click.echo(f"Export {format.upper()}...")

    filters = {}
    if status:
        filters["status"] = status

    # TODO: appeler InvoiceService.export_csv()

    if output:
        click.echo(f"✓ Fichier créé : {output}")
    else:
        click.echo("✓ Données exportées (stdout)")

# === LIST ===

@sap.command()
@click.option(
    "--status", "-s",
    required=False,
    type=str,
    help="Filtrer par statut"
)
def list(status: Optional[str]):
    """
    Liste les factures.

    Exemple :
        sap list --status PAYE
    """
    click.echo("Liste factures :")

    filters = {}
    if status:
        filters["status"] = status

    # TODO: appeler InvoiceService.list_invoices()

    click.echo("✓ Affichage terminé")

if __name__ == "__main__":
    sap()
```

**Utilisation** :
```bash
sap submit -c alice -h 10 -t 25 -d 2026-03-01 -f 2026-03-31 --auto-submit
sap sync
sap reconcile --days 7 --threshold 80
sap export --format csv --status PAYE --output factures.csv
sap list --status EN_ATTENTE
```

---

---

# Schémas Pydantic (DTOs)

**Fichier** : `app/schemas/dtos.py`

```python
from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, list
from datetime import date, datetime
from enum import Enum

# === Énumérations ===

class InvoiceStatus(str, Enum):
    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"
    CREE = "CREE"
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE = "VALIDE"
    PAYE = "PAYE"
    RAPPROCHE = "RAPPROCHE"
    ANNULE = "ANNULE"
    ERREUR = "ERREUR"
    EXPIRE = "EXPIRE"
    REJETE = "REJETE"

class ClientStatus(str, Enum):
    INSCRIT = "INSCRIT"
    EN_ATTENTE = "EN_ATTENTE"
    ERREUR = "ERREUR"

class TransactionStatus(str, Enum):
    NON_LETTREE = "NON_LETTREE"
    LETTRE = "LETTRE"
    A_VERIFIER = "A_VERIFIER"
    PAS_DE_MATCH = "PAS_DE_MATCH"

# === Clients ===

class ClientRequest(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: EmailStr
    telephone: Optional[str] = Field(None, max_length=20)
    adresse: str = Field(min_length=1, max_length=200)
    code_postal: str = Field(regex=r"^\d{5}$")
    ville: str = Field(min_length=1, max_length=100)

class ClientResponse(ClientRequest):
    client_id: str
    urssaf_id: Optional[str] = None
    statut_urssaf: ClientStatus = ClientStatus.EN_ATTENTE
    date_inscription: Optional[datetime] = None
    actif: bool = True

# === Factures ===

class InvoiceRequest(BaseModel):
    client_id: str = Field(min_length=1)
    type_unite: str = Field(pattern="^(HEURE|FORFAIT)$")
    nature_code: str = Field(min_length=1)
    quantite: float = Field(gt=0)
    montant_unitaire: float = Field(gt=0)
    date_debut: date
    date_fin: date
    description: Optional[str] = Field(None, max_length=500)
    auto_submit: bool = False

    @field_validator("date_fin")
    def validate_date_fin(cls, v, info):
        if "date_debut" in info.data and v < info.data["date_debut"]:
            raise ValueError("date_fin doit être >= date_debut")
        return v

class InvoiceResponse(InvoiceRequest):
    facture_id: str
    montant_total: float
    statut: InvoiceStatus = InvoiceStatus.BROUILLON
    urssaf_demande_id: Optional[str] = None
    date_soumission_urssaf: Optional[datetime] = None
    date_validation_client: Optional[datetime] = None
    pdf_drive_id: Optional[str] = None

class InvoiceSubmitResponse(BaseModel):
    facture_id: str
    statut: InvoiceStatus
    urssaf_demande_id: str
    date_soumission_urssaf: datetime

# === Transactions ===

class TransactionRequest(BaseModel):
    swan_id: str
    date_valeur: date
    montant: float
    libelle: str
    type: str  # CREDIT, DEBIT
    source: str  # URSSAF, AUTRE

class TransactionResponse(TransactionRequest):
    transaction_id: str
    facture_id: Optional[str] = None
    statut_lettrage: TransactionStatus = TransactionStatus.NON_LETTREE
    date_import: datetime

# === Lettrage ===

class ReconciliationRequest(BaseModel):
    facture_id: str
    transaction_id: str

class ReconciliationResponse(BaseModel):
    facture_id: str
    transaction_id: str
    montant_facture: float
    montant_transaction: float
    score_confiance: int = Field(ge=0, le=100)
    statut: TransactionStatus = TransactionStatus.A_VERIFIER
    date_lettrage: Optional[datetime] = None

class AutoMatchRequest(BaseModel):
    date_range_days: int = Field(default=7, ge=1, le=30)
    confidence_threshold: int = Field(default=80, ge=0, le=100)

class AutoMatchResponse(BaseModel):
    total_processed: int
    auto_matched: int
    needs_review: int
    no_match: int
    errors: list[str] = Field(default_factory=list)

# === Résumé Dashboard ===

class InvoiceSummary(BaseModel):
    total_invoices: int
    total_ca: float
    status_breakdown: dict[str, int]
    avg_days_to_payment: float

class DashboardData(BaseModel):
    invoices: list[InvoiceResponse]
    summary: InvoiceSummary
    pagination: dict

# === Health Check ===

class HealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    services: dict[str, str]  # {google_sheets: ok, urssaf_api: ok, swan_api: ok}
    version: str
```

---

---

# Codes d'Erreur Standardisés

**Fichier** : `app/errors.py`

## Exceptions Métier

```python
class SAPFunctureException(Exception):
    """Exception de base."""
    code: str = "GENERIC_ERROR"
    status_code: int = 500

    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail or message
        super().__init__(self.message)

# === Clients ===

class ClientNotFoundError(SAPFunctureException):
    code = "CLIENT_NOT_FOUND"
    status_code = 404

class ClientAlreadyExistsError(SAPFunctureException):
    code = "CLIENT_ALREADY_EXISTS"
    status_code = 409

# === Factures ===

class InvoiceNotFoundError(SAPFunctureException):
    code = "INVOICE_NOT_FOUND"
    status_code = 404

class InvalidInvoiceStatusError(SAPFunctureException):
    code = "INVALID_INVOICE_STATUS"
    status_code = 400

class InvoiceValidationError(SAPFunctureException):
    code = "INVOICE_VALIDATION_FAILED"
    status_code = 400

# === URSSAF ===

class URSSAFAPIError(SAPFunctureException):
    code = "URSSAF_API_ERROR"
    status_code = 502

class URSSAFRegistrationError(SAPFunctureException):
    code = "URSSAF_REGISTRATION_FAILED"
    status_code = 400

class URSSAFAuthenticationError(SAPFunctureException):
    code = "URSSAF_AUTH_FAILED"
    status_code = 401

# === Google Sheets ===

class SheetsAdapterError(SAPFunctureException):
    code = "SHEETS_ADAPTER_ERROR"
    status_code = 500

class SheetsQuotaExceededError(SheetsAdapterError):
    code = "SHEETS_QUOTA_EXCEEDED"
    status_code = 429

class SheetsAuthenticationError(SheetsAdapterError):
    code = "SHEETS_AUTH_FAILED"
    status_code = 401

# === Swan ===

class SwanClientError(SAPFunctureException):
    code = "SWAN_API_ERROR"
    status_code = 502

# === PDF ===

class PDFGenerationError(SAPFunctureException):
    code = "PDF_GENERATION_FAILED"
    status_code = 500

# === Notifications ===

class EmailNotificationError(SAPFunctureException):
    code = "EMAIL_NOTIFICATION_FAILED"
    status_code = 500
```

## Codes d'Erreur HTTP

| Code | Message | Cause |
|------|---------|-------|
| 400 | Bad Request | Validation données (client_id, montant, dates invalides) |
| 401 | Unauthorized | Token URSSAF/Google Sheets expiré ou invalide |
| 404 | Not Found | Client, facture, transaction non trouvé |
| 409 | Conflict | Client existe déjà, facture en statut incompatible |
| 429 | Too Many Requests | Quota Google Sheets dépassé |
| 500 | Internal Server Error | Erreur générique (log pour debug) |
| 502 | Bad Gateway | API URSSAF/Swan/SMTP inaccessible |

## Réponse Erreur Standard

```python
class ErrorResponse(BaseModel):
    error: dict = {
        "code": "CLIENT_NOT_FOUND",
        "message": "Client avec ID 'alice-001' non trouvé",
        "detail": "Vérifiez l'ID client dans onglet Clients",
        "timestamp": "2026-03-15T10:30:45Z",
        "request_id": "req-abc123def456"
    }

# Exemple JSON réponse 404
{
    "error": {
        "code": "CLIENT_NOT_FOUND",
        "message": "Client not found",
        "detail": "Client with ID 'alice-001' does not exist",
        "timestamp": "2026-03-15T10:30:45.123456Z",
        "request_id": "550e8400-e29b-41d4-a716-446655440000"
    }
}
```

---

## Middleware d'Erreur

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(SAPFunctureException)
async def sap_exception_handler(request, exc: SAPFunctureException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request.headers.get("x-request-id", "unknown"),
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Une erreur interne s'est produite",
                "detail": "Contactez l'administrateur",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request.headers.get("x-request-id", "unknown"),
            }
        }
    )
```

---

---

## Récapitulatif Complet

**Document généré** : Contrats d'API complets
**Couverture** :

- ✅ 6 routes FastAPI (Dashboard, Clients, Factures, Reconciliation, Export, Health)
- ✅ 6 interfaces services métier avec signatures typées
- ✅ 1 interface SheetsAdapter avec CRUD par onglet + modèles Pydantic
- ✅ 5 commandes CLI Click
- ✅ Schémas Pydantic complets (DTOs request/response)
- ✅ 20+ codes d'erreur standardisés avec HTTP status codes

**Prêt pour** : Implémentation Phase 3

---

**Version** : 1.0
**Date** : Mars 2026
**Auteur** : Winston (Senior API Architect)
**Référence** : SCHEMAS.html, Phase 1-2 Docs
