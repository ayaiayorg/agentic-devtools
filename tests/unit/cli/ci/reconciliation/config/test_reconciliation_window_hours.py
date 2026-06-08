"""Tests for RECONCILIATION_WINDOW_HOURS configuration."""

import os
from unittest.mock import patch


class TestReconciliationWindowHours:
    """Tests for RECONCILIATION_WINDOW_HOURS configuration."""

    def test_default_value(self) -> None:
        """Default RECONCILIATION_WINDOW_HOURS is 24."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGDT_RECONCILIATION_WINDOW_HOURS", None)
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.RECONCILIATION_WINDOW_HOURS == 24

    def test_env_override(self) -> None:
        """AGDT_RECONCILIATION_WINDOW_HOURS env var overrides default."""
        with patch.dict(os.environ, {"AGDT_RECONCILIATION_WINDOW_HOURS": "48"}):
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.RECONCILIATION_WINDOW_HOURS == 48

    def test_invalid_env_falls_back_to_default(self) -> None:
        """Non-integer AGDT_RECONCILIATION_WINDOW_HOURS env var falls back to default."""
        with patch.dict(os.environ, {"AGDT_RECONCILIATION_WINDOW_HOURS": "many"}):
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.RECONCILIATION_WINDOW_HOURS == 24

    def test_zero_env_falls_back_to_default(self) -> None:
        """AGDT_RECONCILIATION_WINDOW_HOURS=0 falls back to default (must be >= 1)."""
        with patch.dict(os.environ, {"AGDT_RECONCILIATION_WINDOW_HOURS": "0"}):
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.RECONCILIATION_WINDOW_HOURS == 24

    def test_negative_env_falls_back_to_default(self) -> None:
        """Negative AGDT_RECONCILIATION_WINDOW_HOURS env var falls back to default."""
        with patch.dict(os.environ, {"AGDT_RECONCILIATION_WINDOW_HOURS": "-5"}):
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.RECONCILIATION_WINDOW_HOURS == 24
