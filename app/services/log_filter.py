from __future__ import annotations

import logging
import re


class PiiMaskingFilter(logging.Filter):
    """Custom logging filter that masks sensitive PII patterns.

    Masks common patterns like passwords, tokens, and secrets with ***MASKED***.
    Patterns matched: secret=, token=, password=, client_secret=
    """

    # Pattern to match sensitive field assignments
    MASK_PATTERNS = [
        re.compile(r'(secret\s*=\s*)["\']?[^"\'\s,}]+', re.IGNORECASE),
        re.compile(r'(token\s*=\s*)["\']?[^"\'\s,}]+', re.IGNORECASE),
        re.compile(r'(password\s*=\s*)["\']?[^"\'\s,}]+', re.IGNORECASE),
        re.compile(r'(client_secret\s*=\s*)["\']?[^"\'\s,}]+', re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record and mask sensitive values.

        Args:
            record: The log record to filter.

        Returns:
            True to allow the record to be logged, False otherwise.
        """
        # Apply masking to the message
        if isinstance(record.msg, str):
            record.msg = self._mask_sensitive_data(record.msg)

        # Apply masking to message arguments if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._mask_sensitive_data(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._mask_sensitive_data(str(arg)) if arg else arg for arg in record.args
                )

        return True

    @staticmethod
    def _mask_sensitive_data(text: str) -> str:
        """Mask sensitive data in text using predefined patterns.

        Args:
            text: The text to mask.

        Returns:
            Text with sensitive values replaced with ***MASKED***.
        """
        for pattern in PiiMaskingFilter.MASK_PATTERNS:
            text = pattern.sub(r"\1***MASKED***", text)
        return text
