"""Tests for ``_coerce_max_retries()``."""

from __future__ import annotations

from agentic_devtools.cli.speckit.validate_frs import _coerce_max_retries


class TestCoerceMaxRetries:
    """Tests for non-negative coercion of retry counts."""

    def test_negative_value_returns_default(self) -> None:
        """Negative input falls back to the default value."""
        assert _coerce_max_retries(-1) == 2

    def test_negative_value_with_custom_default(self) -> None:
        """Negative input falls back to the explicit default."""
        assert _coerce_max_retries(-5, default=10) == 10

    def test_zero_is_valid(self) -> None:
        """Zero is a valid retry count (no retries)."""
        assert _coerce_max_retries(0) == 0

    def test_positive_value_passed_through(self) -> None:
        """Positive values are returned unchanged."""
        assert _coerce_max_retries(3) == 3
