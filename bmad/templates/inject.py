"""Template injection helper for BMAD deliverables."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def inject(template_path: str, values_path: str, output_path: str) -> None:
    """Inject JSON values into HTML template, replacing {{PLACEHOLDER}} markers.

    Args:
        template_path: Path to HTML template file.
        values_path: Path to JSON file with placeholder values.
        output_path: Path to write final HTML output.

    Raises:
        FileNotFoundError: If template or values file not found.
        json.JSONDecodeError: If values JSON is malformed.
        ValueError: If template placeholders are missing from values or coverage is invalid.
    """
    template = Path(template_path).read_text(encoding="utf-8")
    values = json.loads(Path(values_path).read_text(encoding="utf-8"))

    # Find all {{PLACEHOLDER}} markers in template
    placeholders = set(re.findall(r"\{\{(\w+)\}\}", template))
    json_keys = set(values.keys())
    missing = placeholders - json_keys
    if missing:
        msg = f"Missing values for template placeholders: {sorted(missing)}"
        raise ValueError(msg)

    # Validate numeric coverage values (0-100)
    for key, value in values.items():
        if key.endswith("_COVERAGE"):
            try:
                num_value = float(value)
                if not 0 <= num_value <= 100:
                    msg = f"{key} must be between 0 and 100, got {num_value}"
                    raise ValueError(msg)
            except (TypeError, ValueError) as e:
                msg = f"{key} must be numeric (0-100), got {value}"
                raise ValueError(msg) from e

    for key, value in values.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    Path(output_path).write_text(template, encoding="utf-8")
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python inject.py <template_path> <values_path> <output_path>")
        sys.exit(1)

    try:
        inject(sys.argv[1], sys.argv[2], sys.argv[3])
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in values file: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
