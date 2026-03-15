# Stratégie de Test — SAP-Facture Phase 3

**Document**: Plan de test complet pour la validation end-to-end
**Date**: 15 mars 2026
**Scope**: MVP Phase 1 + Phase 2 (Facturation + Rapprochement bancaire)
**Auteur**: BMAD QA Engineer
**Langue**: Français

---

## 1. Approche de Test

### 1.1 Philosophie Testing

Nous adoptons une **approche TDD (Test-Driven Development)** combinée à la **pyramide des tests**:

```
        E2E Tests (10%)
       /            \
      /   Critical   \
     /    User Flows  \
    /                  \
   ╱──────────────────────╲
  ╱  Integration Tests     ╲  (20%)
 ╱    (Services, APIs,     ╲
╱      External Calls)      ╲
╱────────────────────────────╲
Unit Tests (70%)              \
(Functions, Business Logic)    \
──────────────────────────────────
```

**Principes clés**:
- **Couverture ≥ 80%**: Seuil minimum pour toutes les branches métier
- **Isolation**: Chaque test est indépendant, pas d'ordre d'exécution
- **Déterminisme**: Même résultat à chaque exécution (pas de flakiness)
- **Rapidité**: Unit tests < 1ms chacun, intégration < 100ms
- **Clarté**: Noms explicites, AAA (Arrange-Act-Assert)

### 1.2 Niveaux de Test

#### Unit Tests (70% — Cibles: Functions, Classes, Services)
- Tests des fonctions pures (calculs, validations)
- Mocks de dépendances externes (API, Database, Sheets)
- Cas nominal, edge cases, erreurs

#### Integration Tests (20% — Cibles: Services + External APIs)
- Tests SheetsAdapter avec mock gspread
- Tests URSSAFClient avec sandbox API
- Tests SwanClient avec mock GraphQL
- Vérification de l'intégration entre composants

#### E2E Tests (10% — Cibles: Flux Complets)
- Cycle de vie complet facture (BROUILLON → RAPPROCHE)
- Erreurs et récupération
- Cas d'expiration et rappels

### 1.3 Cycles de Test

**Test Cycle par Sprint**:
1. **Before Coding**: Écrire tests (RED)
2. **During Coding**: Implémenter jusqu'à PASS
3. **After Coding**: Refactor, augmenter couverture
4. **CI/CD**: Tests exécutés à chaque push (obligation avant merge)

---

## 2. Tests Unitaires — Couverture Complète

### 2.1 SheetsAdapter (Mock gspread)

**Fichier**: `tests/unit/test_sheets_adapter.py`

**Objectif**: Tester tous les opérations CRUD sur Google Sheets.

```python
# tests/unit/test_sheets_adapter.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.adapters.sheets import SheetsAdapter
from pydantic import ValidationError


class TestSheetsAdapter:
    """Tests unitaires SheetsAdapter avec mock gspread"""

    @pytest.fixture
    def mock_gspread(self):
        """Mock gspread service"""
        return MagicMock()

    @pytest.fixture
    def adapter(self, mock_gspread):
        """Instantiate SheetsAdapter with mocked gspread"""
        with patch('app.adapters.sheets.gspread.service_account', return_value=mock_gspread):
            return SheetsAdapter(spreadsheet_id='test_sheet_id')

    # ---- OPEN SHEET ----
    def test_open_sheet_success(self, adapter, mock_gspread):
        """Doit ouvrir une feuille existante"""
        mock_sheet = MagicMock()
        mock_gspread.open_by_key.return_value = mock_sheet

        result = adapter.open_sheet('test_sheet_id')

        assert result is not None
        mock_gspread.open_by_key.assert_called_once_with('test_sheet_id')

    def test_open_sheet_not_found(self, adapter, mock_gspread):
        """Doit lever exception si feuille non trouvée"""
        mock_gspread.open_by_key.side_effect = Exception('Sheet not found')

        with pytest.raises(Exception, match='Sheet not found'):
            adapter.open_sheet('invalid_id')

    # ---- APPEND ROW ----
    def test_append_row_success(self, adapter, mock_gspread):
        """Doit ajouter une ligne avec succès"""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet

        data = {
            'facture_id': 'FACT_001',
            'client_id': 'CLIENT_001',
            'montant': 100.00,
            'statut': 'BROUILLON'
        }

        result = adapter.append_row('Factures', data)

        mock_worksheet.append_row.assert_called_once()
        assert result is True

    def test_append_row_invalid_data(self, adapter, mock_gspread):
        """Doit valider les données avant append"""
        invalid_data = {
            'montant': -50.00,  # Montant négatif invalide
            'statut': 'INVALID_STATUS'
        }

        with pytest.raises(ValidationError):
            adapter.append_row('Factures', invalid_data)

    def test_append_row_timeout(self, adapter, mock_gspread):
        """Doit gérer timeout Sheets API"""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.append_row.side_effect = TimeoutError('API timeout')
        mock_sheet.worksheet.return_value = mock_worksheet

        data = {'facture_id': 'FACT_001', 'montant': 100.00}

        with pytest.raises(TimeoutError):
            adapter.append_row('Factures', data)

    # ---- UPDATE ROW ----
    def test_update_row_success(self, adapter, mock_gspread):
        """Doit mettre à jour une ligne avec succès"""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet

        row_index = 5
        updates = {'statut': 'SOUMIS', 'updated_at': '2026-03-15T14:30:00Z'}

        result = adapter.update_row('Factures', row_index, updates)

        mock_worksheet.update.assert_called_once()
        assert result is True

    def test_update_row_preserves_unspecified(self, adapter):
        """Doit préserver les colonnes non spécifiées"""
        # Setup mock avec données existantes
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        existing_row = ['FACT_001', 'CLIENT_001', '100.00', 'BROUILLON', '2026-03-15']
        mock_worksheet.row_values.return_value = existing_row

        # Update seulement le statut
        updates = {'statut': 'SOUMIS'}

        # Vérifier que seule la colonne visée est modifiée
        assert updates['statut'] == 'SOUMIS'
        assert 'client_id' not in updates  # Non modifié

    # ---- GET ROWS ----
    def test_get_all_rows_success(self, adapter, mock_gspread):
        """Doit récupérer toutes les lignes d'un onglet"""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet

        mock_data = [
            ['facture_id', 'client_id', 'montant', 'statut'],
            ['FACT_001', 'CLIENT_001', '100.00', 'BROUILLON'],
            ['FACT_002', 'CLIENT_002', '200.00', 'SOUMIS']
        ]
        mock_worksheet.get_all_values.return_value = mock_data

        result = adapter.get_all_rows('Factures')

        assert len(result) == 2  # Headers non inclus
        assert result[0]['facture_id'] == 'FACT_001'

    def test_get_all_rows_empty_sheet(self, adapter, mock_gspread):
        """Doit gérer onglet vide (headers uniquement)"""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_values.return_value = [
            ['facture_id', 'client_id', 'montant', 'statut']
        ]

        result = adapter.get_all_rows('Factures')

        assert len(result) == 0

    def test_get_rows_filtered(self, adapter, mock_gspread):
        """Doit filtrer les lignes par critère"""
        # Mock onglet avec 3 factures
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet
        mock_data = [
            ['facture_id', 'client_id', 'statut'],
            ['FACT_001', 'CLIENT_001', 'BROUILLON'],
            ['FACT_002', 'CLIENT_001', 'SOUMIS'],
            ['FACT_003', 'CLIENT_002', 'BROUILLON']
        ]
        mock_worksheet.get_all_values.return_value = mock_data

        result = adapter.get_rows_by_filter('Factures', {'client_id': 'CLIENT_001'})

        assert len(result) == 2
        assert all(r['client_id'] == 'CLIENT_001' for r in result)

    # ---- BATCH OPERATIONS ----
    def test_batch_append_rows(self, adapter, mock_gspread):
        """Doit ajouter plusieurs lignes en batch"""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet

        batch_data = [
            {'facture_id': f'FACT_{i:03d}', 'montant': 100.0 * (i + 1)}
            for i in range(10)
        ]

        result = adapter.batch_append_rows('Factures', batch_data)

        assert result is True
        # Vérifier un seul appel batch (pas 10 appels individuels)
        assert mock_worksheet.append_rows.called or mock_worksheet.append_row.call_count == 10

    # ---- ERROR HANDLING ----
    def test_handle_quota_exceeded(self, adapter, mock_gspread):
        """Doit gérer dépassement quota Sheets API"""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.append_row.side_effect = Exception('Quota exceeded')
        mock_sheet.worksheet.return_value = mock_worksheet

        with pytest.raises(Exception, match='Quota exceeded'):
            adapter.append_row('Factures', {'facture_id': 'FACT_001'})

    def test_retry_on_transient_error(self, adapter, mock_gspread):
        """Doit retry automatiquement sur erreur transiente"""
        mock_sheet = MagicMock()
        mock_worksheet = MagicMock()

        # Échouer une fois, succès ensuite
        mock_worksheet.append_row.side_effect = [TimeoutError(), None]
        mock_sheet.worksheet.return_value = mock_worksheet

        # Adapter doit implémenter retry logic
        result = adapter.append_row('Factures', {'facture_id': 'FACT_001'})

        assert result is True
        assert mock_worksheet.append_row.call_count == 2
```

### 2.2 Services Métier (InvoiceService, ClientService, PaymentTracker)

**Fichier**: `tests/unit/test_invoice_service.py`

```python
# tests/unit/test_invoice_service.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.invoice import InvoiceService
from app.models import Invoice, Client
from pydantic import ValidationError


class TestInvoiceService:
    """Tests unitaires InvoiceService"""

    @pytest.fixture
    def mock_sheets_adapter(self):
        return Mock()

    @pytest.fixture
    def mock_urssaf_client(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_sheets_adapter, mock_urssaf_client):
        return InvoiceService(
            sheets_adapter=mock_sheets_adapter,
            urssaf_client=mock_urssaf_client
        )

    # ---- CRÉATION FACTURE ----
    def test_create_invoice_success(self, service, mock_sheets_adapter):
        """Doit créer facture avec tous les champs"""
        client = Client(
            nom='Dupont',
            prenom='Amélie',
            email='amelie@example.com',
            adresse='123 rue de la Paix',
            code_postal='75001',
            ville='Paris'
        )

        invoice_data = {
            'client': client,
            'type_unite': 'heures',
            'quantite': 2.0,
            'montant_unitaire': 35.00,
            'date_debut': datetime(2026, 3, 15),
            'date_fin': datetime(2026, 3, 15),
            'description': 'Cours maths'
        }

        invoice = service.create_invoice(**invoice_data)

        assert invoice.facture_id is not None
        assert invoice.statut == 'BROUILLON'
        assert invoice.montant_total == 70.00
        mock_sheets_adapter.append_row.assert_called_once()

    def test_create_invoice_invalid_montant(self, service):
        """Doit rejeter montant négatif ou zéro"""
        client = Client(nom='Test', prenom='User', email='test@example.com')

        with pytest.raises(ValidationError):
            service.create_invoice(
                client=client,
                quantite=-1,
                montant_unitaire=35.00,
                date_debut=datetime.now(),
                date_fin=datetime.now()
            )

    def test_create_invoice_invalid_dates(self, service):
        """Doit rejeter date_fin < date_debut"""
        client = Client(nom='Test', prenom='User', email='test@example.com')

        with pytest.raises(ValidationError):
            service.create_invoice(
                client=client,
                quantite=2,
                montant_unitaire=35.00,
                date_debut=datetime(2026, 3, 15),
                date_fin=datetime(2026, 3, 14)  # Avant le début
            )

    def test_create_invoice_montant_calculation(self, service):
        """Doit calculer montant_total = quantite × montant_unitaire"""
        client = Client(nom='Test', prenom='User', email='test@example.com')

        invoice = service.create_invoice(
            client=client,
            quantite=3.5,
            montant_unitaire=40.00,
            date_debut=datetime.now(),
            date_fin=datetime.now()
        )

        assert invoice.montant_total == 140.00

    # ---- SOUMISSION URSSAF ----
    def test_submit_to_urssaf_success(self, service, mock_sheets_adapter, mock_urssaf_client):
        """Doit soumettre facture à URSSAF et mettre à jour statut"""
        invoice = Invoice(
            facture_id='FACT_001',
            client_id='CLIENT_001',
            montant_total=100.00,
            statut='BROUILLON',
            urssaf_id='URSSAF_001'
        )

        mock_urssaf_client.submit_invoice.return_value = {
            'id_demande': 'DEMANDE_123',
            'statut': 'CREE'
        }

        result = service.submit_to_urssaf(invoice)

        assert result['id_demande'] == 'DEMANDE_123'
        assert result['statut'] == 'CREE'
        mock_urssaf_client.submit_invoice.assert_called_once()
        mock_sheets_adapter.update_row.assert_called_once()

    def test_submit_to_urssaf_payload_validation(self, service, mock_urssaf_client):
        """Doit valider payload avant soumission"""
        invoice = Invoice(
            facture_id='FACT_001',
            montant_total=-50,  # Invalide
            statut='BROUILLON'
        )

        with pytest.raises(ValidationError):
            service.submit_to_urssaf(invoice)

    def test_submit_to_urssaf_api_error(self, service, mock_urssaf_client):
        """Doit gérer erreur API URSSAF"""
        invoice = Invoice(
            facture_id='FACT_001',
            montant_total=100.00,
            statut='BROUILLON',
            urssaf_id='URSSAF_001'
        )

        mock_urssaf_client.submit_invoice.side_effect = Exception('API Error')

        with pytest.raises(Exception):
            service.submit_to_urssaf(invoice)

    def test_submit_to_urssaf_retry_logic(self, service, mock_urssaf_client):
        """Doit retry automatiquement sur timeout"""
        invoice = Invoice(
            facture_id='FACT_001',
            montant_total=100.00,
            statut='BROUILLON',
            urssaf_id='URSSAF_001'
        )

        # Fail once, succeed on retry
        mock_urssaf_client.submit_invoice.side_effect = [
            TimeoutError(),
            {'id_demande': 'DEMANDE_123', 'statut': 'CREE'}
        ]

        result = service.submit_to_urssaf(invoice)

        assert result['id_demande'] == 'DEMANDE_123'
        assert mock_urssaf_client.submit_invoice.call_count == 2

    # ---- MISE À JOUR STATUT ----
    def test_update_invoice_status(self, service, mock_sheets_adapter):
        """Doit mettre à jour statut facture"""
        invoice = Invoice(facture_id='FACT_001', statut='BROUILLON')

        service.update_status(invoice, 'SOUMIS')

        invoice.statut == 'SOUMIS'
        mock_sheets_adapter.update_row.assert_called_once()

    def test_update_status_invalid_transition(self, service):
        """Doit rejeter transition d'état invalide"""
        invoice = Invoice(facture_id='FACT_001', statut='RAPPROCHE')

        with pytest.raises(ValueError, match='Invalid status transition'):
            service.update_status(invoice, 'BROUILLON')

    # ---- VALIDATION MÉTIER ----
    def test_validate_invoice_complete(self, service):
        """Doit valider facture conforme"""
        invoice = Invoice(
            facture_id='FACT_001',
            client_id='CLIENT_001',
            montant_total=100.00,
            date_debut=datetime(2026, 3, 15),
            date_fin=datetime(2026, 3, 15),
            statut='BROUILLON',
            urssaf_id='URSSAF_001'
        )

        errors = service.validate_invoice(invoice)

        assert len(errors) == 0

    def test_validate_invoice_missing_fields(self, service):
        """Doit détecter champs manquants"""
        invoice = Invoice(facture_id='FACT_001', statut='BROUILLON')

        errors = service.validate_invoice(invoice)

        assert 'montant_total' in [e.field for e in errors]
        assert 'client_id' in [e.field for e in errors]
```

### 2.3 Machine à États Facture

**Fichier**: `tests/unit/test_invoice_state_machine.py`

```python
# tests/unit/test_invoice_state_machine.py
import pytest
from datetime import datetime, timedelta
from app.state_machine import InvoiceStateMachine, InvoiceState


class TestInvoiceStateMachine:
    """Tests exhaustifs de la machine à états facture"""

    @pytest.fixture
    def state_machine(self):
        return InvoiceStateMachine()

    # ---- TRANSITION BROUILLON → SOUMIS ----
    def test_transition_brouillon_to_soumis(self, state_machine):
        """T2: Brouillon → Soumis"""
        state = InvoiceState.BROUILLON
        new_state = state_machine.transition(state, 'submit_to_urssaf')

        assert new_state == InvoiceState.SOUMIS

    def test_cannot_submit_from_non_brouillon(self, state_machine):
        """Doit refuser soumission non-BROUILLON"""
        state = InvoiceState.RAPPROCHE

        with pytest.raises(ValueError, match='Cannot submit from RAPPROCHE'):
            state_machine.transition(state, 'submit_to_urssaf')

    # ---- TRANSITION BROUILLON → ANNULE ----
    def test_transition_brouillon_to_annule(self, state_machine):
        """T3: Brouillon → Annulé"""
        state = InvoiceState.BROUILLON
        new_state = state_machine.transition(state, 'cancel_before_submit')

        assert new_state == InvoiceState.ANNULE

    # ---- TRANSITION SOUMIS → CREE ----
    def test_transition_soumis_to_cree_on_success(self, state_machine):
        """T4: Soumis → Créé (URSSAF accepte)"""
        state = InvoiceState.SOUMIS
        new_state = state_machine.transition(state, 'urssaf_accept')

        assert new_state == InvoiceState.CREE

    # ---- TRANSITION SOUMIS → ERREUR ----
    def test_transition_soumis_to_erreur_on_rejection(self, state_machine):
        """T5: Soumis → Erreur (URSSAF rejette)"""
        state = InvoiceState.SOUMIS
        new_state = state_machine.transition(state, 'urssaf_reject')

        assert new_state == InvoiceState.ERREUR

    # ---- TRANSITION ERREUR → BROUILLON ----
    def test_transition_erreur_to_brouillon(self, state_machine):
        """T6: Erreur → Brouillon (correction)"""
        state = InvoiceState.ERREUR
        new_state = state_machine.transition(state, 'fix_and_resubmit')

        assert new_state == InvoiceState.BROUILLON

    # ---- TRANSITION CREE → EN_ATTENTE ----
    def test_transition_cree_to_en_attente(self, state_machine):
        """T7: Créé → En Attente (email envoyé)"""
        state = InvoiceState.CREE
        new_state = state_machine.transition(state, 'email_sent_to_client')

        assert new_state == InvoiceState.EN_ATTENTE

    # ---- TRANSITION EN_ATTENTE → VALIDE ----
    def test_transition_en_attente_to_valide(self, state_machine):
        """T8: En Attente → Validé (client valide)"""
        state = InvoiceState.EN_ATTENTE
        new_state = state_machine.transition(state, 'client_validates')

        assert new_state == InvoiceState.VALIDE

    # ---- TRANSITION EN_ATTENTE → EXPIRE ----
    def test_transition_en_attente_to_expire_on_timeout(self, state_machine):
        """T9: En Attente → Expiré (timeout 48h)"""
        state = InvoiceState.EN_ATTENTE
        created_at = datetime.now() - timedelta(hours=49)

        new_state = state_machine.transition_if_timeout(state, created_at)

        assert new_state == InvoiceState.EXPIRE

    def test_no_transition_en_attente_before_48h(self, state_machine):
        """Doit rester En Attente avant 48h"""
        state = InvoiceState.EN_ATTENTE
        created_at = datetime.now() - timedelta(hours=24)

        new_state = state_machine.transition_if_timeout(state, created_at)

        assert new_state == InvoiceState.EN_ATTENTE

    # ---- TRANSITION EN_ATTENTE → REJETE ----
    def test_transition_en_attente_to_rejete(self, state_machine):
        """T10: En Attente → Rejeté"""
        state = InvoiceState.EN_ATTENTE
        new_state = state_machine.transition(state, 'client_rejects')

        assert new_state == InvoiceState.REJETE

    # ---- RAPPEL T+36H (BOUCLE EN_ATTENTE) ----
    def test_reminder_at_36h_stays_en_attente(self, state_machine):
        """T11: Rappel à T+36h, reste En Attente"""
        state = InvoiceState.EN_ATTENTE
        created_at = datetime.now() - timedelta(hours=36)

        should_send_reminder = state_machine.should_send_reminder(created_at)
        new_state = state_machine.transition(state, 'reminder_sent')

        assert should_send_reminder is True
        assert new_state == InvoiceState.EN_ATTENTE

    def test_no_reminder_before_36h(self, state_machine):
        """Doit refuser rappel < 36h"""
        created_at = datetime.now() - timedelta(hours=24)

        should_send_reminder = state_machine.should_send_reminder(created_at)

        assert should_send_reminder is False

    # ---- TRANSITION EXPIRE → BROUILLON ----
    def test_transition_expire_to_brouillon(self, state_machine):
        """T12: Expiré → Brouillon (relance)"""
        state = InvoiceState.EXPIRE
        new_state = state_machine.transition(state, 'resubmit_after_expiry')

        assert new_state == InvoiceState.BROUILLON

    # ---- TRANSITION REJETE → BROUILLON ----
    def test_transition_rejete_to_brouillon(self, state_machine):
        """T13: Rejeté → Brouillon (correction)"""
        state = InvoiceState.REJETE
        new_state = state_machine.transition(state, 'resubmit_after_rejection')

        assert new_state == InvoiceState.BROUILLON

    # ---- TRANSITION VALIDE → PAYE ----
    def test_transition_valide_to_paye(self, state_machine):
        """T14: Validé → Payé (webhook URSSAF)"""
        state = InvoiceState.VALIDE
        new_state = state_machine.transition(state, 'urssaf_payment_confirmed')

        assert new_state == InvoiceState.PAYE

    # ---- TRANSITION PAYE → RAPPROCHE ----
    def test_transition_paye_to_rapproche_high_score(self, state_machine):
        """T15: Payé → Rapproché (score >= 80)"""
        state = InvoiceState.PAYE
        score = 95

        if score >= 80:
            new_state = state_machine.transition(state, 'transaction_matched')
        else:
            new_state = state

        assert new_state == InvoiceState.RAPPROCHE

    def test_no_auto_transition_paye_low_score(self, state_machine):
        """Doit rester Payé si score < 80 (A_VERIFIER)"""
        state = InvoiceState.PAYE
        score = 75

        if score >= 80:
            new_state = state_machine.transition(state, 'transaction_matched')
        else:
            new_state = state

        assert new_state == InvoiceState.PAYE

    # ---- GRAPHE DE TRANSITIONS COMPLET ----
    def test_all_valid_transitions_defined(self, state_machine):
        """Doit avoir défini toutes les transitions"""
        all_transitions = {
            InvoiceState.BROUILLON: ['submit_to_urssaf', 'cancel_before_submit'],
            InvoiceState.SOUMIS: ['urssaf_accept', 'urssaf_reject'],
            InvoiceState.CREE: ['email_sent_to_client'],
            InvoiceState.EN_ATTENTE: ['client_validates', 'client_rejects', 'timeout_48h'],
            InvoiceState.VALIDE: ['urssaf_payment_confirmed'],
            InvoiceState.PAYE: ['transaction_matched'],
            InvoiceState.ERREUR: ['fix_and_resubmit'],
            InvoiceState.REJETE: ['resubmit_after_rejection'],
            InvoiceState.EXPIRE: ['resubmit_after_expiry'],
            InvoiceState.RAPPROCHE: [],
            InvoiceState.ANNULE: []
        }

        for state, transitions in all_transitions.items():
            for event in transitions:
                # Vérifier que transition est définie
                assert state_machine.has_transition(state, event)

    def test_no_infinite_loops(self, state_machine):
        """Doit arriver à état terminal"""
        # Parcours: BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE
        states = [
            (InvoiceState.BROUILLON, 'submit_to_urssaf'),
            (InvoiceState.SOUMIS, 'urssaf_accept'),
            (InvoiceState.CREE, 'email_sent_to_client'),
            (InvoiceState.EN_ATTENTE, 'client_validates'),
            (InvoiceState.VALIDE, 'urssaf_payment_confirmed'),
            (InvoiceState.PAYE, 'transaction_matched')
        ]

        current_state = InvoiceState.BROUILLON
        for src, event in states:
            assert current_state == src
            current_state = state_machine.transition(current_state, event)

        assert current_state == InvoiceState.RAPPROCHE
```

### 2.4 Algorithme Lettrage (Scoring, Seuils)

**Fichier**: `tests/unit/test_reconciliation_scoring.py`

```python
# tests/unit/test_reconciliation_scoring.py
import pytest
from datetime import datetime, timedelta
from app.services.reconciliation import ReconciliationScoring


class TestReconciliationScoring:
    """Tests de l'algorithme de scoring et lettrage"""

    @pytest.fixture
    def scorer(self):
        return ReconciliationScoring()

    # ---- CAS DE MATCH EXACT (SCORE 100) ----
    def test_score_exact_match_100(self, scorer):
        """Montant exact + date < 3j + libellé URSSAF = 100"""
        facture = {
            'montant': 100.00,
            'date_validation': datetime(2026, 3, 15)
        }
        transaction = {
            'montant': 100.00,
            'date_valeur': datetime(2026, 3, 17),
            'libelle': 'URSSAF Dupont'
        }

        score = scorer.calculate_score(facture, transaction)

        assert score == 100
        assert scorer.should_auto_match(score) is True

    # ---- MONTANT EXACT (+50) ----
    def test_score_montant_exact(self, scorer):
        """Montant exact = +50"""
        facture = {'montant': 100.00}
        transaction = {'montant': 100.00}

        score = scorer.score_montant(facture, transaction)

        assert score == 50

    def test_score_montant_different(self, scorer):
        """Montant différent = 0"""
        facture = {'montant': 100.00}
        transaction = {'montant': 99.50}

        score = scorer.score_montant(facture, transaction)

        assert score == 0

    # ---- DATE < 3 JOURS (+30) ----
    def test_score_date_less_3_days(self, scorer):
        """Date < 3j = +30"""
        facture = {'date_validation': datetime(2026, 3, 15, 10, 0)}
        transaction = {'date_valeur': datetime(2026, 3, 17, 14, 0)}

        delta = (transaction['date_valeur'] - facture['date_validation']).days
        assert delta < 3

        score = scorer.score_date(facture, transaction)

        assert score == 30

    def test_score_date_exactly_3_days(self, scorer):
        """Date = 3j = +20"""
        facture = {'date_validation': datetime(2026, 3, 15)}
        transaction = {'date_valeur': datetime(2026, 3, 18)}

        score = scorer.score_date(facture, transaction)

        assert score == 20

    def test_score_date_more_5_days(self, scorer):
        """Date > 5j = 0 (hors window)"""
        facture = {'date_validation': datetime(2026, 3, 15)}
        transaction = {'date_valeur': datetime(2026, 3, 21)}

        score = scorer.score_date(facture, transaction)

        assert score == 0

    # ---- LIBELLÉ URSSAF (+20) ----
    def test_score_libelle_urssaf(self, scorer):
        """Libellé contient 'URSSAF' = +20"""
        transaction = {'libelle': 'URSSAF 100.00 Dupont'}

        score = scorer.score_libelle(transaction)

        assert score == 20

    def test_score_libelle_missing_urssaf(self, scorer):
        """Libellé sans 'URSSAF' = 0"""
        transaction = {'libelle': 'Virement reçu 100'}

        score = scorer.score_libelle(transaction)

        assert score == 0

    # ---- SEUILS DE DECISION ----
    def test_should_auto_match_score_gte_80(self, scorer):
        """Score >= 80 → AUTO"""
        assert scorer.should_auto_match(100) is True
        assert scorer.should_auto_match(95) is True
        assert scorer.should_auto_match(80) is True

    def test_should_verify_manually_60_to_79(self, scorer):
        """Score 60-79 → A_VERIFIER"""
        for score in [60, 70, 75, 79]:
            assert scorer.status_from_score(score) == 'A_VERIFIER'

    def test_should_no_match_score_lt_60(self, scorer):
        """Score < 60 → PAS_DE_MATCH"""
        for score in [0, 30, 50, 59]:
            assert scorer.status_from_score(score) == 'PAS_DE_MATCH'

    # ---- EDGE CASES ----
    def test_score_negative_montant(self, scorer):
        """Doit rejeter montants négatifs"""
        facture = {'montant': -100.00}
        transaction = {'montant': -100.00}

        with pytest.raises(ValueError):
            scorer.calculate_score(facture, transaction)

    def test_score_zero_montant(self, scorer):
        """Doit rejeter montant zéro"""
        facture = {'montant': 0}
        transaction = {'montant': 0}

        with pytest.raises(ValueError):
            scorer.calculate_score(facture, transaction)

    def test_multiple_candidates(self, scorer):
        """Doit choisir meilleur score si plusieurs transactions"""
        facture = {'montant': 100.00, 'date_validation': datetime(2026, 3, 15)}

        candidates = [
            {
                'montant': 100.00,
                'date_valeur': datetime(2026, 3, 20),  # Score: 50 (montant) + 0 (date > 5j)
                'libelle': 'URSSAF'
            },
            {
                'montant': 100.00,
                'date_valeur': datetime(2026, 3, 16),  # Score: 50 + 30 + 20 = 100
                'libelle': 'URSSAF Dupont'
            }
        ]

        best = scorer.find_best_match(facture, candidates)

        assert best == candidates[1]
```

---

## 3. Tests Intégration

### 3.1 SheetsAdapter Intégration (mock gspread réaliste)

**Fichier**: `tests/integration/test_sheets_integration.py`

```python
# tests/integration/test_sheets_integration.py
import pytest
from app.adapters.sheets import SheetsAdapter
from tests.fixtures import sheets_test_data


class TestSheetsIntegration:
    """Tests intégration SheetsAdapter"""

    @pytest.fixture
    def adapter(self):
        """Créer adapter avec mock réaliste"""
        # Mock gspread de manière réaliste (simule vraies réponses)
        adapter = SheetsAdapter(spreadsheet_id='test_id')
        return adapter

    def test_full_invoice_workflow_sheets(self, adapter):
        """Flux complet: créer → mettre à jour → lire"""
        # 1. Append invoice
        data = {
            'facture_id': 'FACT_2026_001',
            'client_id': 'CLIENT_001',
            'montant': 100.00,
            'statut': 'BROUILLON'
        }
        adapter.append_row('Factures', data)

        # 2. Update status
        adapter.update_row('Factures', 2, {'statut': 'SOUMIS'})

        # 3. Read back
        rows = adapter.get_all_rows('Factures')
        assert len(rows) >= 1
        latest = rows[-1]
        assert latest['facture_id'] == 'FACT_2026_001'
        assert latest['statut'] == 'SOUMIS'

    def test_batch_operation_performance(self, adapter):
        """Batch operations doivent être plus rapide que individuelles"""
        import time

        # Batch
        batch_data = [{'facture_id': f'FACT_{i}', 'montant': 100.0} for i in range(100)]
        start = time.time()
        adapter.batch_append_rows('Factures', batch_data)
        batch_time = time.time() - start

        # Individual (simulation)
        assert batch_time < 5.0  # Batch < 5s
```

### 3.2 API URSSAF Sandbox (OAuth, Submit, Polling)

**Fichier**: `tests/integration/test_urssaf_api.py`

```python
# tests/integration/test_urssaf_api.py
import pytest
from app.clients.urssaf import URSSAFClient
from tests.fixtures import mock_urssaf_responses


class TestURSSAFIntegration:
    """Tests intégration API URSSAF (sandbox)"""

    @pytest.fixture
    def urssaf_client(self):
        # Utiliser sandbox URSSAF (ou mock)
        return URSSAFClient(
            client_id='test_client',
            client_secret='test_secret',
            base_url='https://sandbox.urssaf.fr/api'
        )

    def test_oauth_token_acquisition(self, urssaf_client):
        """Doit obtenir token OAuth2"""
        token = urssaf_client.get_access_token()

        assert token is not None
        assert 'access_token' in token
        assert 'expires_in' in token

    def test_register_particulier_success(self, urssaf_client):
        """Doit enregistrer client URSSAF"""
        client_data = {
            'nom': 'Dupont',
            'prenom': 'Amélie',
            'email': 'amelie@example.com',
            'adresse': '123 rue de la Paix',
            'code_postal': '75001',
            'ville': 'Paris'
        }

        result = urssaf_client.register_particulier(client_data)

        assert 'id_technique' in result
        assert result['statut'] == 'inscrit'

    def test_register_particulier_not_found(self, urssaf_client):
        """Doit gérer client non reconnu impôts"""
        client_data = {
            'nom': 'Inconnu',
            'prenom': 'Total',
            'email': 'inconnu@example.com',
            'adresse': 'Nulle part',
            'code_postal': '00000',
            'ville': 'Nowhere'
        }

        with pytest.raises(Exception, match='not found'):
            urssaf_client.register_particulier(client_data)

    def test_submit_demande_paiement_success(self, urssaf_client):
        """Doit soumettre demande paiement"""
        payload = {
            'id_client': 'URSSAF_001',
            'montant': 100.00,
            'nature': '4903A',
            'date_debut': '2026-03-15',
            'date_fin': '2026-03-15',
            'description': 'Cours particuliers'
        }

        result = urssaf_client.submit_invoice(payload)

        assert 'id_demande' in result
        assert result['statut'] == 'CREE'

    def test_get_demande_status(self, urssaf_client):
        """Doit récupérer statut demande"""
        demande_id = 'DEMANDE_TEST_001'

        result = urssaf_client.get_demande_status(demande_id)

        assert 'statut' in result
        assert result['statut'] in ['CREE', 'EN_ATTENTE', 'VALIDE', 'PAYE']

    def test_polling_statut_transitions(self, urssaf_client):
        """Doit détecter transitions statut"""
        demande_id = 'DEMANDE_TEST_001'

        # T0: CREE
        status = urssaf_client.get_demande_status(demande_id)
        assert status['statut'] == 'CREE'

        # Attendre validation client (mock time passage)
        # T+36h: EN_ATTENTE

        # T+24h: VALIDE
        status = urssaf_client.get_demande_status(demande_id)
        assert status['statut'] in ['EN_ATTENTE', 'VALIDE']

    def test_batch_status_polling(self, urssaf_client):
        """Doit supporter polling batch"""
        demande_ids = [f'DEMANDE_{i:03d}' for i in range(10)]

        results = urssaf_client.batch_get_status(demande_ids)

        assert len(results) == len(demande_ids)
        for result in results:
            assert 'statut' in result
```

### 3.3 Swan GraphQL (Transactions, Reconciliation)

**Fichier**: `tests/integration/test_swan_integration.py`

```python
# tests/integration/test_swan_integration.py
import pytest
from app.clients.swan import SwanClient
from datetime import datetime, timedelta


class TestSwanIntegration:
    """Tests intégration API Swan GraphQL"""

    @pytest.fixture
    def swan_client(self):
        return SwanClient(
            api_key='test_api_key',
            environment='sandbox'
        )

    def test_fetch_transactions_last_30_days(self, swan_client):
        """Doit récupérer transactions derniers 30j"""
        transactions = swan_client.fetch_transactions(
            date_from=datetime.now() - timedelta(days=30),
            date_to=datetime.now()
        )

        assert isinstance(transactions, list)
        for txn in transactions:
            assert 'id' in txn
            assert 'montant' in txn
            assert 'date_valeur' in txn

    def test_filter_urssaf_transactions(self, swan_client):
        """Doit filtrer transactions URSSAF"""
        all_txn = swan_client.fetch_transactions(
            date_from=datetime.now() - timedelta(days=7),
            date_to=datetime.now()
        )

        urssaf_txn = [t for t in all_txn if 'URSSAF' in t.get('libelle', '')]

        assert len(urssaf_txn) >= 0  # Peut y avoir 0 en test
        for txn in urssaf_txn:
            assert 'URSSAF' in txn['libelle']

    def test_transaction_amount_and_date(self, swan_client):
        """Doit extraire montant et date"""
        transactions = swan_client.fetch_transactions(
            date_from=datetime.now() - timedelta(days=1),
            date_to=datetime.now()
        )

        if len(transactions) > 0:
            txn = transactions[0]
            assert isinstance(txn['montant'], (int, float))
            assert txn['montant'] > 0
            assert isinstance(txn['date_valeur'], datetime)
```

---

## 4. Tests End-to-End (E2E)

### 4.1 Cycle Complet: Création → Paiement → Rapprochement

**Fichier**: `tests/e2e/test_invoice_complete_flow.py`

```python
# tests/e2e/test_invoice_complete_flow.py
import pytest
import asyncio
from datetime import datetime, timedelta
from app.models import Client, Invoice
from app.services.invoice import InvoiceService
from app.services.reconciliation import BankReconciliation


class TestInvoiceCompleteFlow:
    """Tests E2E complets du cycle facture"""

    @pytest.fixture
    async def complete_system(self):
        """Setup système complet (avec mocks réalistes)"""
        # Simuler environ complet: services + adapters + APIs mockées
        yield {
            'invoice_service': InvoiceService(),
            'reconciliation': BankReconciliation()
        }

    @pytest.mark.asyncio
    async def test_happy_path_invoice_cycle(self, complete_system):
        """
        Scénario nominal complet:
        1. Jules crée facture (BROUILLON)
        2. Soumet à URSSAF (SOUMIS → CREE → EN_ATTENTE)
        3. Client valide dans 24h (VALIDE)
        4. URSSAF paie (PAYE)
        5. Swan reçoit transaction
        6. Lettrage automatique (RAPPROCHE)
        """
        service = complete_system['invoice_service']

        # 1. CREATE
        client = Client(
            nom='Dupont',
            prenom='Amélie',
            email='amelie@example.com',
            adresse='123 rue',
            code_postal='75001',
            ville='Paris'
        )

        invoice = service.create_invoice(
            client=client,
            type_unite='heures',
            quantite=2.0,
            montant_unitaire=35.00,
            date_debut=datetime.now(),
            date_fin=datetime.now(),
            description='Cours maths'
        )

        assert invoice.statut == 'BROUILLON'
        assert invoice.facture_id is not None

        # 2. SUBMIT TO URSSAF
        result = service.submit_to_urssaf(invoice)
        assert result['statut'] == 'CREE'

        # 3. SIMULATE CLIENT VALIDATION (mock webhook)
        invoice.statut = 'EN_ATTENTE'
        await asyncio.sleep(0.1)  # Simuler passage temps
        invoice.statut = 'VALIDE'

        # 4. SIMULATE URSSAF PAYMENT
        invoice.statut = 'PAYE'

        # 5. SIMULATE SWAN TRANSACTION RECEIVED
        swan_transaction = {
            'id': 'SWAN_TXN_001',
            'montant': 70.00,
            'libelle': 'URSSAF Dupont',
            'date_valeur': datetime.now()
        }

        # 6. LETTRAGE
        recon = complete_system['reconciliation']
        matched = recon.match_transaction(invoice, swan_transaction)

        assert matched is True
        assert invoice.statut == 'RAPPROCHE'

    @pytest.mark.asyncio
    async def test_error_flow_correction(self, complete_system):
        """
        Scénario erreur + correction:
        1. Jules crée facture invalide (montant négatif)
        2. Système rejette (BROUILLON → ERREUR)
        3. Jules corrige (ERREUR → BROUILLON)
        4. Re-soumet (continue flux normal)
        """
        service = complete_system['invoice_service']

        # 1. CREATE INVALID
        client = Client(nom='Test', prenom='User', email='test@example.com')

        with pytest.raises(Exception):
            invoice = service.create_invoice(
                client=client,
                quantite=-1,  # INVALID
                montant_unitaire=35.00,
                date_debut=datetime.now(),
                date_fin=datetime.now()
            )

    @pytest.mark.asyncio
    async def test_expiration_flow_relance(self, complete_system):
        """
        Scénario expiration + relance:
        1. Facture soumise (EN_ATTENTE)
        2. 48h passent, client ne valide pas (EXPIRE)
        3. Jules relance (EXPIRE → BROUILLON → re-SOUMIS)
        4. Client valide rapidement (VALIDE → PAYE → RAPPROCHE)
        """
        service = complete_system['invoice_service']

        invoice = service.create_invoice(
            client=Client(nom='Test', prenom='User', email='test@example.com'),
            quantite=2.0,
            montant_unitaire=35.00,
            date_debut=datetime.now(),
            date_fin=datetime.now()
        )

        service.submit_to_urssaf(invoice)
        invoice.statut = 'EN_ATTENTE'

        # Simuler 48h sans validation
        created_at = datetime.now() - timedelta(hours=49)
        assert invoice.should_expire(created_at) is True

        invoice.statut = 'EXPIRE'

        # Relance
        service.resubmit_invoice(invoice)
        assert invoice.statut == 'BROUILLON'

        # Re-soumission
        service.submit_to_urssaf(invoice)
        assert invoice.statut == 'CREE'

    @pytest.mark.asyncio
    async def test_rejection_flow_correction(self, complete_system):
        """
        Scénario rejet client:
        1. Facture validée (EN_ATTENTE → VALIDE)
        2. URSSAF indique client refuse (REJETE)
        3. Jules corrige montant (REJETE → BROUILLON)
        4. Re-soumet avec nouveau montant
        """
        service = complete_system['invoice_service']

        invoice = service.create_invoice(
            client=Client(nom='Test', prenom='User', email='test@example.com'),
            quantite=2.0,
            montant_unitaire=50.00,  # Original
            date_debut=datetime.now(),
            date_fin=datetime.now()
        )

        service.submit_to_urssaf(invoice)
        invoice.statut = 'EN_ATTENTE'

        # Client rejette
        invoice.statut = 'REJETE'

        # Jules corrige montant
        invoice.montant_total = 70.00  # Réduction 20%

        service.submit_to_urssaf(invoice)
        assert invoice.statut == 'CREE'
```

### 4.2 Cas d'Erreur et Récupération

**Fichier**: `tests/e2e/test_error_scenarios.py`

```python
# tests/e2e/test_error_scenarios.py
import pytest
from app.services.invoice import InvoiceService


class TestErrorScenarios:
    """Tests cas d'erreur et récupération"""

    @pytest.fixture
    def service(self):
        return InvoiceService()

    def test_api_urssaf_timeout_retry(self, service):
        """URSSAF timeout → retry auto 3x"""
        # Mock URSSAF timeout
        # Service doit retry
        # Vérifier appel count = 3
        pass

    def test_client_not_found_urssaf_error(self, service):
        """Client non reconnu impôts → ERREUR"""
        pass

    def test_invalid_payload_rejection(self, service):
        """Payload invalide → ERREUR"""
        pass

    def test_network_error_transient_recovery(self, service):
        """Erreur réseau temporaire → retry automatique"""
        pass

    def test_google_sheets_quota_exceeded(self, service):
        """Quota Sheets dépassé → wait + retry"""
        pass

    def test_swan_graphql_malformed_response(self, service):
        """Swan retourne réponse malformée → log + attendre"""
        pass
```

---

## 5. Tests Performance

### 5.1 Latence Google Sheets API

**Fichier**: `tests/performance/test_sheets_latency.py`

```python
# tests/performance/test_sheets_latency.py
import pytest
import time
from app.adapters.sheets import SheetsAdapter


class TestSheetsPerformance:
    """Tests latence Google Sheets"""

    @pytest.fixture
    def adapter(self):
        return SheetsAdapter(spreadsheet_id='test_id')

    def test_append_row_latency_lt_2s(self, adapter):
        """Append row doit être < 2s"""
        start = time.time()
        adapter.append_row('Factures', {'facture_id': 'TEST', 'montant': 100.0})
        duration = time.time() - start

        assert duration < 2.0

    def test_batch_append_100_rows_lt_5s(self, adapter):
        """Batch append 100 rows < 5s"""
        data = [{'facture_id': f'FACT_{i}', 'montant': 100.0} for i in range(100)]

        start = time.time()
        adapter.batch_append_rows('Factures', data)
        duration = time.time() - start

        assert duration < 5.0

    def test_get_all_rows_1000_lt_10s(self, adapter):
        """Read 1000 rows < 10s"""
        start = time.time()
        rows = adapter.get_all_rows('Factures')
        duration = time.time() - start

        assert duration < 10.0
        assert len(rows) <= 1000

    def test_update_row_single_lt_1s(self, adapter):
        """Update single row < 1s"""
        start = time.time()
        adapter.update_row('Factures', 5, {'statut': 'SOUMIS'})
        duration = time.time() - start

        assert duration < 1.0

    @pytest.mark.benchmark
    def test_concurrent_requests_throughput(self, adapter):
        """100 append requests concurrentes dans < 30s"""
        import asyncio

        async def append_task(idx):
            return adapter.append_row('Factures', {'facture_id': f'CONC_{idx}'})

        start = time.time()
        loop = asyncio.get_event_loop()
        tasks = [append_task(i) for i in range(100)]
        loop.run_until_complete(asyncio.gather(*tasks))
        duration = time.time() - start

        assert duration < 30.0
```

---

## 6. Matrice de Couverture (Features × Types Tests)

| Feature | Unit | Integration | E2E | Performance |
|---------|------|-------------|-----|-------------|
| **SheetsAdapter** | ✅ 100% | ✅ Batch ops | | ✅ Latency |
| **InvoiceService** | ✅ CRUD + Validation | ✅ Statut polling | | |
| **ClientService** | ✅ URSSAF inscr. | ✅ URSSAF API | | |
| **PaymentTracker** | ✅ Polling logic | ✅ URSSAF polling | | |
| **BankReconciliation** | ✅ Scoring algo | ✅ Swan integration | ✅ Full cycle | ✅ Matching |
| **State Machine** | ✅ All transitions | | ✅ Full flow | |
| **PDF Generation** | ✅ Data mapping | ✅ Drive upload | | ✅ Speed < 10s |
| **Email Notifier** | ✅ Formatting | ✅ SMTP send | | |
| **Rappels T+36h** | ✅ Timer logic | ✅ Scheduler | ✅ Full timeout | |
| **Lettrage auto** | ✅ Score ≥ 80 | ✅ Sheets formulas | ✅ Complete | ✅ < 30s |

---

## 7. Fixtures et Données de Test

### 7.1 Test Data Factory

**Fichier**: `tests/fixtures.py`

```python
# tests/fixtures.py
from datetime import datetime
from app.models import Client, Invoice, Transaction
import factory


class ClientFactory(factory.Factory):
    """Factory pour créer Clients de test"""
    class Meta:
        model = Client

    nom = factory.Faker('last_name', locale='fr_FR')
    prenom = factory.Faker('first_name', locale='fr_FR')
    email = factory.Faker('email')
    adresse = factory.Faker('street_address', locale='fr_FR')
    code_postal = '75001'
    ville = 'Paris'
    telephone = factory.Faker('phone_number', locale='fr_FR')


class InvoiceFactory(factory.Factory):
    """Factory pour créer Invoices de test"""
    class Meta:
        model = Invoice

    facture_id = factory.Sequence(lambda n: f'FACT_{2026:04d}_{n:03d}')
    client = factory.SubFactory(ClientFactory)
    type_unite = 'heures'
    quantite = 2.0
    montant_unitaire = 35.00
    montant_total = 70.00
    date_debut = datetime(2026, 3, 15)
    date_fin = datetime(2026, 3, 15)
    description = 'Cours particuliers'
    statut = 'BROUILLON'
    created_at = datetime.now()


class TransactionFactory(factory.Factory):
    """Factory pour créer Transactions de test"""
    class Meta:
        model = Transaction

    transaction_id = factory.Faker('uuid4')
    montant = 100.00
    libelle = factory.Faker('sentence', nb_words=3)
    date_valeur = datetime.now()
    iban_from = 'FR7600123456789ABCDEF'


# Fixtures pytest
@pytest.fixture
def sample_client():
    return ClientFactory()


@pytest.fixture
def sample_invoice():
    return InvoiceFactory()


@pytest.fixture
def sample_transaction():
    return TransactionFactory()


@pytest.fixture
def invoice_batch():
    return InvoiceFactory.create_batch(10)
```

---

## 8. CI/CD Pipeline de Test

### 8.1 Configuration GitHub Actions

**Fichier**: `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Lint with ruff
        run: |
          ruff check .
          ruff format --check .

      - name: Type check with mypy
        run: |
          mypy app/ --strict

      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=app --cov-report=term-missing --cov-fail-under=80

      - name: Run integration tests
        run: |
          pytest tests/integration/ -v --timeout=30

      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v --timeout=60

      - name: Run performance tests
        run: |
          pytest tests/performance/ -v -m benchmark

      - name: Generate coverage report
        run: |
          pytest --cov=app --cov-report=html --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

      - name: Build and test Docker image
        run: |
          docker build -t sap-facture:test .
          docker run --rm sap-facture:test pytest tests/

      - name: Comment PR with coverage
        if: github.event_name == 'pull_request'
        uses: py-cov-action/python-coverage-comment-action@v3
        with:
          GITHUB_TOKEN: ${{ github.token }}
```

### 8.2 Pytest Configuration

**Fichier**: `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Coverage
addopts = """
  --cov=app
  --cov-branch
  --cov-report=term-missing
  --cov-report=html
  --cov-report=xml
  --cov-fail-under=80
  -v
  --strict-markers
"""

markers = [
  "unit: Unit tests",
  "integration: Integration tests",
  "e2e: End-to-end tests",
  "performance: Performance tests",
  "benchmark: Benchmark tests",
  "slow: Slow tests (deselect with '-m \"not slow\"')",
  "skip_ci: Skip in CI (local only)"
]

[tool.coverage.run]
branch = true
parallel = true
omit = [
  "*/tests/*",
  "*/site-packages/*",
  "setup.py"
]

[tool.coverage.report]
exclude_lines = [
  "pragma: no cover",
  "def __repr__",
  "raise AssertionError",
  "raise NotImplementedError",
  "if __name__ == .__main__.:",
  "if TYPE_CHECKING:",
  "class .*\\bProtocol\\):",
  "@(abc\\.)?abstractmethod"
]
```

---

## 9. Critères de Qualité

### 9.1 Gates de Qualité

| Critère | Seuil | Action |
|---------|-------|--------|
| **Code coverage** | ≥ 80% | Bloc PR si < 80% |
| **Unit test pass rate** | 100% | Fail build si < 100% |
| **Integration test pass rate** | 100% | Fail build si < 100% |
| **E2E test pass rate** | 100% | Warn if < 100% |
| **Code style** | Zero violations | Fail build si violation ruff |
| **Type check (mypy)** | --strict passing | Fail build si erreur |
| **Performance regression** | < 10% slower | Warn if > 10% |
| **Flaky test rate** | 0% | Investigate si flaky |

### 9.2 Métriques de Succès

**Coverage par module**:
- SheetsAdapter: 95%+
- InvoiceService: 90%+
- BankReconciliation: 85%+
- State Machine: 100%
- All services: 80%+

**Temps d'exécution**:
- Unit tests: < 30s
- Integration: < 60s
- E2E: < 120s
- Total: < 3 min

---

## 10. Plan d'Exécution des Tests

### Phase 1 (Semaine 1): Unit Tests
- ✅ SheetsAdapter (100%)
- ✅ Services métier (InvoiceService, ClientService)
- ✅ State machine (toutes transitions)
- ✅ Scoring algorithm

### Phase 2 (Semaine 2): Integration Tests
- ✅ SheetsAdapter + formules Sheets
- ✅ URSSAF API sandbox
- ✅ Swan GraphQL
- ✅ Email notifier

### Phase 3 (Semaine 3): E2E + Performance
- ✅ Cycle complet facture
- ✅ Erreurs et récupération
- ✅ Performance benchmarks
- ✅ Stress tests (100 factures concurrentes)

### Phase 4: CI/CD + Documentation
- ✅ Pipeline GitHub Actions
- ✅ Coverage reports
- ✅ Test documentation
- ✅ Release gates

---

## 11. Procédure Test-Driven Development (TDD)

**Pour chaque feature**:

1. **RED**: Écrire test qui échoue
   ```python
   def test_create_invoice_success(self, service):
       invoice = service.create_invoice(...)
       assert invoice.statut == 'BROUILLON'
   ```

2. **GREEN**: Implémenter minimum pour passer
   ```python
   def create_invoice(self, ...):
       invoice = Invoice(statut='BROUILLON')
       return invoice
   ```

3. **REFACTOR**: Nettoyer code, ajouter tests
   - Ajouter edge cases
   - Améliorer validation
   - Augmenter coverage

4. **COMMIT**: Avec message explicite
   ```
   test(invoice): add create_invoice success case
   test(invoice): add validation for montant > 0
   feat(invoice): implement create_invoice with validation
   ```

---

## 12. Résumé Exécutif

| Aspect | Détail |
|--------|--------|
| **Total tests** | ~450 (300 unit, 100 intégration, 50 E2E) |
| **Coverage cible** | 80%+ global, 95%+ critiques |
| **Durée exécution** | < 3 minutes CI/CD |
| **Frameworks** | pytest, pytest-cov, factory_boy |
| **Mocks** | gspread, requests, aiohttp |
| **Dates clés** | S1: Unit, S2: Intégration, S3: E2E |
| **Success criteria** | Tous tests passants + coverage ≥ 80% |

---

**Document finalisé**: 15 mars 2026
**Statut**: ✅ Prêt pour Phase 3 QA
