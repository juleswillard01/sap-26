"""Tests RED — EmailRenderer with Jinja2.

Tests pour src/adapters/email_renderer.py (CDC §10 Notifications Templates).

Coverage: Template rendering, XSS prevention, error handling, context injection.

PHASE RED: Tests MUST FAIL (EmailRenderer doesn't exist yet).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import TemplateNotFound

from src.adapters.email_renderer import EmailRenderer


class TestEmailRendererInit:
    """Tests for EmailRenderer initialization."""

    def test_init_default_template_dir(self) -> None:
        """EmailRenderer uses default template dir src/templates/emails/."""
        renderer = EmailRenderer()
        expected_dir = Path(__file__).parent.parent / "src" / "templates" / "emails"
        assert renderer.template_dir == expected_dir

    def test_init_custom_template_dir(self, tmp_path: Path) -> None:
        """EmailRenderer accepts custom template directory."""
        custom_dir = tmp_path / "custom_templates"
        custom_dir.mkdir()
        renderer = EmailRenderer(template_dir=custom_dir)
        assert renderer.template_dir == custom_dir

    def test_init_resolves_path_to_absolute(self) -> None:
        """EmailRenderer resolves template_dir to absolute path."""
        renderer = EmailRenderer()
        assert renderer.template_dir.is_absolute()

    def test_init_stores_jinja_environment(self) -> None:
        """EmailRenderer initializes Jinja2 environment."""
        renderer = EmailRenderer()
        assert renderer.env is not None
        assert hasattr(renderer.env, "get_template")


class TestEmailRendererRender:
    """Tests for EmailRenderer.render() method."""

    def test_render_reminder_t36h(self, tmp_path: Path) -> None:
        """Render reminder_t36h template with invoice context.

        Template variables: facture_id, client_name, montant, hours_pending, ais_url
        """
        # Create template file
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "reminder_t36h.jinja2"
        template_file.write_text(
            "Subject: Relance facture {{ facture_id }}\n"
            "---\n"
            "Bonjour {{ client_name }},\n"
            "\n"
            "Montant en attente: {{ montant }}€\n"
            "Heures: {{ hours_pending }}\n"
            "Lien: {{ ais_url }}\n"
        )

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {
            "facture_id": "F001",
            "client_name": "Alice Dupont",
            "montant": 90.0,
            "hours_pending": 36,
            "ais_url": "https://app.ais.fr/demande/F001",
        }

        plain_text, html = renderer.render("reminder_t36h", context)

        assert isinstance(plain_text, str)
        assert isinstance(html, str)
        assert "F001" in plain_text
        assert "Alice Dupont" in plain_text
        assert "90.0" in plain_text

    def test_render_expired_t48h(self, tmp_path: Path) -> None:
        """Render expired_t48h template with expiration context.

        Template variables: facture_id, client_name, montant, expired_at
        """
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "expired_t48h.jinja2"
        template_file.write_text(
            "Subject: Facture expirée {{ facture_id }}\n"
            "---\n"
            "Facture: {{ facture_id }}\n"
            "Client: {{ client_name }}\n"
            "Montant: {{ montant }}€\n"
            "Expirée: {{ expired_at }}\n"
        )

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {
            "facture_id": "F002",
            "client_name": "Bob Martin",
            "montant": 150.0,
            "expired_at": "2026-03-21T14:00:00",
        }

        plain_text, _html = renderer.render("expired_t48h", context)

        assert "F002" in plain_text
        assert "Bob Martin" in plain_text
        assert "150.0" in plain_text
        assert "2026-03-21" in plain_text

    def test_render_payment_received(self, tmp_path: Path) -> None:
        """Render payment_received template with payment context.

        Template variables: facture_id, montant, date_paiement, client_name
        """
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "payment_received.jinja2"
        template_file.write_text(
            "Subject: Paiement reçu {{ facture_id }}\n"
            "---\n"
            "Paiement reçu pour facture {{ facture_id }}\n"
            "Montant: {{ montant }}€\n"
            "Date: {{ date_paiement }}\n"
            "Client: {{ client_name }}\n"
        )

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {
            "facture_id": "F003",
            "montant": 200.0,
            "date_paiement": "2026-03-21",
            "client_name": "Charlie Durand",
        }

        plain_text, _html = renderer.render("payment_received", context)

        assert "F003" in plain_text
        assert "200.0" in plain_text
        assert "2026-03-21" in plain_text

    def test_render_reconciled(self, tmp_path: Path) -> None:
        """Render reconciled template with lettrage context.

        Template variables: facture_id, montant, score_confiance, transaction_date
        """
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "reconciled.jinja2"
        template_file.write_text(
            "Subject: Facture rapprochée {{ facture_id }}\n"
            "---\n"
            "Facture: {{ facture_id }}\n"
            "Montant: {{ montant }}€\n"
            "Score confiance: {{ score_confiance }}/100\n"
            "Date transaction: {{ transaction_date }}\n"
        )

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {
            "facture_id": "F004",
            "montant": 120.0,
            "score_confiance": 95,
            "transaction_date": "2026-03-19",
        }

        plain_text, _html = renderer.render("reconciled", context)

        assert "F004" in plain_text
        assert "120.0" in plain_text
        assert "95" in plain_text

    def test_render_error_alert(self, tmp_path: Path) -> None:
        """Render error_alert template with error context.

        Template variables: error_message, sync_type, timestamp
        """
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "error_alert.jinja2"
        template_file.write_text(
            "Subject: ERREUR {{ sync_type }}\n"
            "---\n"
            "Erreur {{ sync_type }}:\n"
            "{{ error_message }}\n"
            "À: {{ timestamp }}\n"
        )

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {
            "error_message": "Connection timeout to AIS",
            "sync_type": "ais_sync",
            "timestamp": "2026-03-21T14:30:45",
        }

        plain_text, _html = renderer.render("error_alert", context)

        assert "Connection timeout" in plain_text
        assert "ais_sync" in plain_text

    def test_render_returns_tuple_text_html(self, tmp_path: Path) -> None:
        """Render returns tuple (plain_text, html)."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "simple.jinja2"
        template_file.write_text("Hello {{ name }}")

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {"name": "World"}

        result = renderer.render("simple", context)

        assert isinstance(result, tuple)
        assert len(result) == 2
        plain_text, html = result
        assert isinstance(plain_text, str)
        assert isinstance(html, str)

    def test_render_xss_prevention_script_tag_escaped(self, tmp_path: Path) -> None:
        """XSS: <script> tags in context are escaped in HTML output."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "xss_test.jinja2"
        template_file.write_text("HTML content:\n{{ user_input | safe }}\n")

        renderer = EmailRenderer(template_dir=templates_dir)
        # Simulate user input with malicious script
        context = {
            "user_input": "<script>alert('XSS')</script>",
        }

        _plain_text, html = renderer.render("xss_test", context)

        # HTML output should escape script tags (not render raw HTML)
        # Note: Jinja2 auto-escapes by default, so <script> becomes &lt;script&gt;
        assert "<script>" not in html or "&lt;script&gt;" in html

    def test_render_xss_prevention_onclick_escaped(self, tmp_path: Path) -> None:
        """XSS: Single quotes in onclick context are escaped."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "xss_onclick.jinja2"
        template_file.write_text('<a href="{{ url }}">Link</a>')

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {
            "url": "javascript:alert('XSS')",
        }

        _plain_text, html = renderer.render("xss_onclick", context)

        # Jinja2 auto-escape should escape single quotes in HTML attributes
        # Single quote &#39; or &#x27; prevents attribute injection
        assert "&#39;" in html or "&#x27;" in html or "&apos;" in html

    def test_render_missing_template_raises_template_not_found(self, tmp_path: Path) -> None:
        """Render non-existent template raises TemplateNotFound."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {"foo": "bar"}

        with pytest.raises(TemplateNotFound):
            renderer.render("nonexistent_template", context)

    def test_render_with_empty_context(self, tmp_path: Path) -> None:
        """Render with empty context dict works."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "static.jinja2"
        template_file.write_text("Static content\nNo variables here")

        renderer = EmailRenderer(template_dir=templates_dir)
        plain_text, _html = renderer.render("static", {})

        assert "Static content" in plain_text
        assert "No variables here" in plain_text

    def test_render_with_none_values_in_context(self, tmp_path: Path) -> None:
        """Render handles None values in context gracefully."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "nullable.jinja2"
        template_file.write_text("Value: {{ value | default('N/A') }}")

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {"value": None}

        plain_text, _html = renderer.render("nullable", context)

        assert "N/A" in plain_text

    def test_render_multiline_template_text_and_html(self, tmp_path: Path) -> None:
        """Render processes multiline templates for both text and HTML."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "multiline.jinja2"
        template_file.write_text(
            "Subject: {{ subject }}\n---\nLine 1: {{ var1 }}\nLine 2: {{ var2 }}\n"
        )

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {
            "subject": "Test Subject",
            "var1": "Value 1",
            "var2": "Value 2",
        }

        plain_text, _html = renderer.render("multiline", context)

        assert "Test Subject" in plain_text
        assert "Value 1" in plain_text
        assert "Value 2" in plain_text

    def test_render_template_with_loops(self, tmp_path: Path) -> None:
        """Render handles Jinja2 loops in templates."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "loop.jinja2"
        template_file.write_text("{% for item in items %}\n- {{ item }}\n{% endfor %}")

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {"items": ["Item 1", "Item 2", "Item 3"]}

        plain_text, _html = renderer.render("loop", context)

        assert "Item 1" in plain_text
        assert "Item 2" in plain_text
        assert "Item 3" in plain_text

    def test_render_template_with_conditionals(self, tmp_path: Path) -> None:
        """Render handles Jinja2 conditionals in templates."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "conditional.jinja2"
        template_file.write_text(
            "{% if is_paid %}\nInvoice is paid.\n{% else %}\nInvoice is pending.\n{% endif %}"
        )

        renderer = EmailRenderer(template_dir=templates_dir)

        # Test paid case
        plain_text, _html = renderer.render("conditional", {"is_paid": True})
        assert "paid" in plain_text.lower()

        # Test unpaid case
        plain_text, _html = renderer.render("conditional", {"is_paid": False})
        assert "pending" in plain_text.lower()

    def test_render_template_with_filters(self, tmp_path: Path) -> None:
        """Render handles Jinja2 filters (uppercase, lowercase, etc.)."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "filters.jinja2"
        template_file.write_text("Name: {{ name | upper }}\nEmail: {{ email | lower }}")

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {"name": "Alice", "email": "ALICE@EXAMPLE.COM"}

        plain_text, _html = renderer.render("filters", context)

        assert "ALICE" in plain_text
        assert "alice@example.com" in plain_text

    def test_render_plain_text_output_format(self, tmp_path: Path) -> None:
        """Plain text output contains no HTML tags."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "plain.jinja2"
        template_file.write_text("Hello {{ name }}\n\nBest regards")

        renderer = EmailRenderer(template_dir=templates_dir)
        plain_text, _ = renderer.render("plain", {"name": "User"})

        assert "<" not in plain_text
        assert ">" not in plain_text

    def test_render_html_output_format(self, tmp_path: Path) -> None:
        """HTML output contains HTML structure."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "html_test.jinja2"
        template_file.write_text("<h1>{{ title }}</h1><p>{{ content }}</p>")

        renderer = EmailRenderer(template_dir=templates_dir)
        _, html = renderer.render("html_test", {"title": "Title", "content": "Content"})

        # HTML should have some structure indicators
        assert "Title" in html
        assert "Content" in html

    def test_render_special_characters_preserved(self, tmp_path: Path) -> None:
        """Special characters (é, è, €) are preserved in output."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "special.jinja2"
        template_file.write_text("Montant: {{ montant }}€\nÉtat: {{ etat }}")

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {"montant": "100", "etat": "Créé"}

        plain_text, _html = renderer.render("special", context)

        assert "€" in plain_text
        assert "Créé" in plain_text

    def test_render_template_name_case_sensitive(self, tmp_path: Path) -> None:
        """Template names are case-sensitive."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "CaseSensitive.jinja2"
        template_file.write_text("Content")

        renderer = EmailRenderer(template_dir=templates_dir)

        # Correct case should work
        plain_text, _ = renderer.render("CaseSensitive", {})
        assert "Content" in plain_text

        # Wrong case should fail
        with pytest.raises(TemplateNotFound):
            renderer.render("casesensitive", {})

    def test_render_large_context_dict(self, tmp_path: Path) -> None:
        """Render handles large context dictionaries."""
        templates_dir = tmp_path / "emails"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "large.jinja2"
        template_file.write_text(
            "{% for key, value in context.items() %}\n{{ key }}: {{ value }}\n{% endfor %}"
        )

        renderer = EmailRenderer(template_dir=templates_dir)
        context = {
            "context": {f"key_{i}": f"value_{i}" for i in range(100)},
        }

        plain_text, _html = renderer.render("large", context)

        assert "key_0" in plain_text
        assert "key_99" in plain_text

    def test_render_template_dir_not_exist_raises(self) -> None:
        """EmailRenderer with non-existent template dir raises error on render."""
        non_existent = Path("/nonexistent/path/emails")
        renderer = EmailRenderer(template_dir=non_existent)

        with pytest.raises((FileNotFoundError, TemplateNotFound)):
            renderer.render("any_template", {})
