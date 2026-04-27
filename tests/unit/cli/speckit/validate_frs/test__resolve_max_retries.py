"""Tests for _resolve_max_retries()."""

from __future__ import annotations

import os
from unittest.mock import patch

from agentic_devtools.cli.speckit.validate_frs import _resolve_max_retries


class TestResolveMaxRetries:
    """Tests for max-retries resolution precedence."""

    def test_cli_value_takes_precedence(self):
        """CLI value overrides env var and default."""
        with patch.dict(os.environ, {"SPECKIT_VALIDATE_MAX_RETRIES": "10"}):
            assert _resolve_max_retries(3) == 3

    def test_env_var_used_when_no_cli(self):
        """Env var used when CLI value is None."""
        with patch.dict(os.environ, {"SPECKIT_VALIDATE_MAX_RETRIES": "7"}):
            assert _resolve_max_retries(None) == 7

    def test_default_when_no_cli_no_env(self):
        """Default of 2 when neither CLI nor env var set."""
        env = {k: v for k, v in os.environ.items() if k != "SPECKIT_VALIDATE_MAX_RETRIES"}
        with patch.dict(os.environ, env, clear=True):
            assert _resolve_max_retries(None) == 2

    def test_invalid_env_var_falls_back_to_default(self):
        """Non-integer env var → falls back to default 2."""
        with patch.dict(os.environ, {"SPECKIT_VALIDATE_MAX_RETRIES": "not_a_number"}):
            assert _resolve_max_retries(None) == 2
