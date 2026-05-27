"""Tests for log_group() context manager."""

import os
from unittest.mock import patch

from agentic_devtools.cli.ci.logging_config import log_group


class TestLogGroup:
    """Tests for log_group() context manager."""

    def test_emits_group_annotations_in_github_actions(self, capsys) -> None:
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with log_group("Test Group"):
                pass
        captured = capsys.readouterr()
        assert "::group::Test Group" in captured.err
        assert "::endgroup::" in captured.err

    def test_no_annotations_outside_github_actions(self, capsys) -> None:
        env = os.environ.copy()
        env.pop("GITHUB_ACTIONS", None)
        with patch.dict(os.environ, env, clear=True):
            with log_group("Test Group"):
                pass
        captured = capsys.readouterr()
        assert "::group::" not in captured.err
        assert "::endgroup::" not in captured.err

    def test_endgroup_emitted_on_exception(self, capsys) -> None:
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            try:
                with log_group("Failing Group"):
                    raise ValueError("test error")
            except ValueError:
                pass
        captured = capsys.readouterr()
        assert "::group::Failing Group" in captured.err
        assert "::endgroup::" in captured.err
