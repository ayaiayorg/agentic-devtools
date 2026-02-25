"""Tests for require_content function."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.commands import require_content


class TestRequireContent:
    """Tests for require_content function."""

    def test_returns_content_when_available(self):
        """Should return the content string when it is set in state."""
        with patch(
            "agentic_devtools.cli.azure_devops.commands.get_value",
            return_value="My comment",
        ):
            result = require_content()

        assert result == "My comment"

    def test_exits_when_content_not_set(self):
        """Should call sys.exit when content is not set in state."""
        with patch(
            "agentic_devtools.cli.azure_devops.commands.get_value",
            return_value=None,
        ):
            with pytest.raises(SystemExit):
                require_content()

    def test_exits_when_content_is_empty_string(self):
        """Should call sys.exit when content is an empty string."""
        with patch(
            "agentic_devtools.cli.azure_devops.commands.get_value",
            return_value="",
        ):
            with pytest.raises(SystemExit):
                require_content()
