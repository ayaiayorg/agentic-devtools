"""Tests for parse_json_response function."""

import sys
import pytest

from agentic_devtools.cli.azure_devops.helpers import parse_json_response


class TestParseJsonResponse:
    """Tests for parse_json_response function."""

    def test_parses_valid_json(self):
        """Should return a dict when valid JSON is provided."""
        result = parse_json_response('{"key": "value"}', context="test")

        assert result == {"key": "value"}

    def test_parses_json_array(self):
        """Should return a list when a JSON array is provided."""
        result = parse_json_response('[1, 2, 3]', context="test")

        assert result == [1, 2, 3]

    def test_exits_on_invalid_json(self):
        """Should call sys.exit when the input is not valid JSON."""
        with pytest.raises(SystemExit):
            parse_json_response("not-json", context="test")
