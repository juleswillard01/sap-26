"""Email template rendering with Jinja2.

Provides EmailRenderer for rendering email templates in plain text and HTML formats.
Implements CDC §10 — Notifications & Templates.

Key features:
- Jinja2 template rendering with FileSystemLoader
- Autoescape enabled for XSS prevention
- UTF-8 support for special characters (€, accents)
- Returns tuple[str, str] of (plain_text, html)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Undefined


class EmailRenderer:
    """Render email templates using Jinja2.

    Loads templates from a directory and renders them with a given context.
    Both plain text and HTML outputs come from the same template file.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize EmailRenderer with template directory.

        Args:
            template_dir: Path to directory containing .jinja2 template files.
                         Defaults to src/templates/emails/ if not provided.
                         Automatically resolved to absolute path.
        """
        if template_dir is None:
            # Default: src/templates/emails/ relative to project root
            template_dir = Path(__file__).parent.parent / "templates" / "emails"

        self.template_dir = template_dir.resolve()

        # Initialize Jinja2 environment with FileSystemLoader
        # autoescape="html": Enable HTML escaping for XSS prevention
        # Jinja2's autoescape handles all XSS prevention correctly without side effects
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape="html",  # type: ignore[arg-type]
            enable_async=False,
        )

        # Override the 'safe' filter to prevent templates from bypassing escaping
        def safe_filter(value: Any) -> Any:
            """Override safe filter: prevents bypass of autoescape."""
            # Return value but allow Jinja2's autoescape to handle it
            return value

        self.env.filters["safe"] = safe_filter

    def render(self, template_name: str, context: dict[str, Any]) -> tuple[str, str]:
        """Render template with given context.

        Loads a .jinja2 template file and renders it with the provided context.
        Returns both plain text and HTML versions from the same template.

        Args:
            template_name: Name of template file (without .jinja2 extension).
                          Example: "reminder_t36h" loads "reminder_t36h.jinja2"
            context: Dictionary of variables to inject into template.

        Returns:
            Tuple of (plain_text, html) both as strings.
            Both outputs are rendered from the same template file.

        Raises:
            TemplateNotFound: If template file does not exist.
            FileNotFoundError: If template_dir does not exist.
        """
        # Load template with .jinja2 extension
        template = self.env.get_template(f"{template_name}.jinja2")

        # Process context: replace None with undefined so Jinja2's default filter works
        # This allows {{ value | default('N/A') }} to work correctly with None

        processed_context = {}
        for key, value in context.items():
            # Convert None to Undefined so default filter recognizes it
            if value is None:
                processed_context[key] = Undefined()
            else:
                processed_context[key] = value

        # Render template with autoescape enabled
        # Jinja2's autoescape="html" will handle escaping by default
        rendered = template.render(**processed_context)

        # Both plain text and HTML come from the same rendered template
        # The template itself determines the format
        plain_text = rendered
        html = rendered

        return plain_text, html
