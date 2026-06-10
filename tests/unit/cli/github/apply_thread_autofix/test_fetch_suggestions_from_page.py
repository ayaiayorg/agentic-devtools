"""Tests for _fetch_suggestions_from_page."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.apply_thread_autofix import _fetch_suggestions_from_page

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


def _make_react_partial(
    comment_id: int,
    suggestion_state: str = "present",
    diff_entries: list | None = None,
    *,
    has_suggestion: bool = True,
    has_automated: bool = True,
    severity: str = "medium",
) -> str:
    """Build a react-partial script tag with embedded suggestion JSON."""
    if diff_entries is None:
        diff_entries = [{"path": "src/file.py", "diffLines": [{"type": "HUNK", "text": "@@ -1,1 +1,2 @@"}]}]

    suggestion_data: dict = {}
    if has_suggestion:
        suggestion_data = {"diffEntries": diff_entries}

    automated: dict = {}
    if has_automated:
        automated = {
            "suggestionState": suggestion_state,
            "severity": severity,
        }
        if has_suggestion:
            automated["suggestion"] = suggestion_data

    comment: dict = {
        "databaseId": comment_id,
        "id": f"node_{comment_id}",
    }
    if has_automated:
        comment["automatedComment"] = automated

    data = {"props": {"comment": comment}}
    json_str = json.dumps(data)
    return f'<script type="application/json" data-target="react-partial.embeddedData">{json_str}</script>'


class TestFetchSuggestionsFromPage:
    """Tests for _fetch_suggestions_from_page."""

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_returns_empty_when_no_html(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = ""
        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert result == []

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_returns_empty_when_no_react_partials(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = "<html><body>no scripts here</body></html>"
        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert result == []

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_parses_valid_suggestion(self, mock_fetch: MagicMock) -> None:
        diff_entries = [{"path": "src/main.py", "diffLines": [{"type": "HUNK", "text": "@@ -1,1 +1,2 @@"}]}]
        html = _make_react_partial(100, "present", diff_entries)
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert len(result) == 1
        assert result[0]["comment_id"] == 100
        assert result[0]["diff_entries"] == diff_entries
        assert result[0]["severity"] == "medium"

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_skips_non_present_state(self, mock_fetch: MagicMock) -> None:
        html = _make_react_partial(200, "applied")
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert result == []

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_skips_partial_without_comment(self, mock_fetch: MagicMock) -> None:
        # A react-partial without props.comment
        data = {"props": {"somethingElse": True}}
        json_str = json.dumps(data)
        html = f'<script type="application/json" data-target="react-partial.embeddedData">{json_str}</script>'
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert result == []

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_skips_when_no_automated_comment(self, mock_fetch: MagicMock) -> None:
        html = _make_react_partial(300, has_automated=False)
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert result == []

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_skips_when_no_suggestion_key(self, mock_fetch: MagicMock) -> None:
        # Has automatedComment with suggestionState=present but no suggestion key
        html = _make_react_partial(400, "present", has_suggestion=False)
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert result == []

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_skips_when_diff_entries_empty(self, mock_fetch: MagicMock) -> None:
        html = _make_react_partial(500, "present", diff_entries=[])
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert result == []

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_multiple_suggestions_parsed(self, mock_fetch: MagicMock) -> None:
        html = _make_react_partial(10, "present") + _make_react_partial(20, "present")
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert len(result) == 2
        assert result[0]["comment_id"] == 10
        assert result[1]["comment_id"] == 20

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_invalid_json_skipped(self, mock_fetch: MagicMock) -> None:
        html = '<script type="application/json" data-target="react-partial.embeddedData">{invalid json</script>'
        html += _make_react_partial(50, "present")
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert len(result) == 1
        assert result[0]["comment_id"] == 50

    @patch(f"{_MODULE}._fetch_all_page_html")
    def test_all_automated_but_none_present_logs_info(self, mock_fetch: MagicMock) -> None:
        """When all automated comments have non-present state, the function returns empty."""
        html = _make_react_partial(60, "applied") + _make_react_partial(70, "dismissed")
        mock_fetch.return_value = html

        result = _fetch_suggestions_from_page("owner/repo", 1, "token")
        assert result == []
