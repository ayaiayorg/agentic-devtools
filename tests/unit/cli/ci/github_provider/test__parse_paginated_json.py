"""Tests for _parse_paginated_json helper."""

import json

import pytest

from agentic_devtools.cli.ci.github_provider import _parse_paginated_json


class TestParsePaginatedJson:
    """Tests for _parse_paginated_json."""

    def test_empty_string_returns_empty_list(self) -> None:
        assert _parse_paginated_json("") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        assert _parse_paginated_json("   \n\t  ") == []

    def test_single_array(self) -> None:
        raw = json.dumps([{"id": 1}, {"id": 2}])
        result = _parse_paginated_json(raw)
        assert result == [{"id": 1}, {"id": 2}]

    def test_single_object(self) -> None:
        raw = json.dumps({"total_count": 2, "check_runs": [{"id": 1}]})
        result = _parse_paginated_json(raw)
        assert result == {"total_count": 2, "check_runs": [{"id": 1}]}

    def test_concatenated_arrays(self) -> None:
        page1 = json.dumps([{"id": 1}])
        page2 = json.dumps([{"id": 2}])
        raw = page1 + page2
        result = _parse_paginated_json(raw)
        assert result == [{"id": 1}, {"id": 2}]

    def test_concatenated_arrays_with_whitespace(self) -> None:
        page1 = json.dumps([{"id": 1}])
        page2 = json.dumps([{"id": 2}])
        raw = page1 + "\n  " + page2
        result = _parse_paginated_json(raw)
        assert result == [{"id": 1}, {"id": 2}]

    def test_concatenated_dicts_merge_array_values(self) -> None:
        page1 = json.dumps({"total_count": 3, "items": [{"id": 1}]})
        page2 = json.dumps({"total_count": 3, "items": [{"id": 2}]})
        raw = page1 + page2
        result = _parse_paginated_json(raw)
        assert result == {"total_count": 3, "items": [{"id": 1}, {"id": 2}]}

    def test_concatenated_dicts_divergent_scalar_logs_warning(self, caplog) -> None:
        page1 = json.dumps({"total_count": 3, "items": [{"id": 1}]})
        page2 = json.dumps({"total_count": 5, "items": [{"id": 2}]})
        raw = page1 + page2
        result = _parse_paginated_json(raw)
        # First page value is preserved
        assert result["total_count"] == 3
        assert result["items"] == [{"id": 1}, {"id": 2}]
        assert "scalar key" in caplog.text

    def test_concatenated_invalid_json_raises(self) -> None:
        raw = '[{"id": 1}]  {invalid'
        with pytest.raises(json.JSONDecodeError, match="Failed to parse concatenated JSON"):
            _parse_paginated_json(raw)

    def test_no_results_after_whitespace_stripping_returns_empty(self) -> None:
        # Single valid doc that is NOT an array and NOT a dict (edge case)
        raw = "42"
        result = _parse_paginated_json(raw)
        assert result == 42

    def test_concatenated_non_container_results_returned_as_list(self) -> None:
        raw = "42\n43"
        result = _parse_paginated_json(raw)
        assert result == [42, 43]

    def test_concatenated_dicts_skip_non_dict_page(self) -> None:
        """When concatenated pages start with a dict but include a non-dict, skip it."""
        page1 = json.dumps({"items": [1]})
        page2 = json.dumps([99])  # non-dict page
        raw = page1 + page2
        result = _parse_paginated_json(raw)
        # Non-dict page is skipped; only page1 keys are preserved
        assert result == {"items": [1]}
