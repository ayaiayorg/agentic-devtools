"""Tests for _count_commits_behind helper in snapshot module."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.ci.pipeline.snapshot import _count_commits_behind


class TestCountCommitsBehind:
    """Tests for _count_commits_behind helper."""

    def test_returns_zero_when_provider_has_no_method(self) -> None:
        provider = MagicMock(spec=[])  # No attributes
        result = _count_commits_behind(provider, pr_number=1, base_branch="main", head_branch="feature")
        assert result == 0

    def test_returns_count_from_provider(self) -> None:
        provider = MagicMock()
        provider.count_commits_behind.return_value = 5
        result = _count_commits_behind(provider, pr_number=1, base_branch="main", head_branch="feature")
        assert result == 5

    def test_raises_on_exception(self) -> None:
        provider = MagicMock()
        provider.count_commits_behind.side_effect = RuntimeError("API error")

        with pytest.raises(RuntimeError, match="API error"):
            _count_commits_behind(provider, pr_number=1, base_branch="main", head_branch="feature")

    def test_returns_zero_when_method_not_callable(self) -> None:
        provider = MagicMock()
        provider.count_commits_behind = "not a callable"
        result = _count_commits_behind(provider, pr_number=1, base_branch="main", head_branch="feature")
        assert result == 0
