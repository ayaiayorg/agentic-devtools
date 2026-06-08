"""Tests for reconciliation config module."""

import os
from unittest.mock import patch


class TestMaxRunAttempts:
    """Tests for MAX_RUN_ATTEMPTS configuration."""

    def test_default_value(self) -> None:
        """Default MAX_RUN_ATTEMPTS is 3."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGDT_MAX_RUN_ATTEMPTS", None)
            # Re-import to pick up env change
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.MAX_RUN_ATTEMPTS == 3

    def test_env_override(self) -> None:
        """AGDT_MAX_RUN_ATTEMPTS env var overrides default."""
        with patch.dict(os.environ, {"AGDT_MAX_RUN_ATTEMPTS": "5"}):
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.MAX_RUN_ATTEMPTS == 5

    def test_invalid_env_falls_back_to_default(self) -> None:
        """Non-integer AGDT_MAX_RUN_ATTEMPTS env var falls back to default."""
        with patch.dict(os.environ, {"AGDT_MAX_RUN_ATTEMPTS": "three"}):
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.MAX_RUN_ATTEMPTS == 3

    def test_zero_env_falls_back_to_default(self) -> None:
        """AGDT_MAX_RUN_ATTEMPTS=0 falls back to default (must be >= 1)."""
        with patch.dict(os.environ, {"AGDT_MAX_RUN_ATTEMPTS": "0"}):
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.MAX_RUN_ATTEMPTS == 3

    def test_negative_env_falls_back_to_default(self) -> None:
        """Negative AGDT_MAX_RUN_ATTEMPTS env var falls back to default."""
        with patch.dict(os.environ, {"AGDT_MAX_RUN_ATTEMPTS": "-1"}):
            import importlib

            import agentic_devtools.cli.ci.reconciliation.config as cfg

            importlib.reload(cfg)
            assert cfg.MAX_RUN_ATTEMPTS == 3
