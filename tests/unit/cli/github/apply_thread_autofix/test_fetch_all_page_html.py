"""Tests for _fetch_all_page_html."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.apply_thread_autofix import _fetch_all_page_html

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestFetchAllPageHtml:
    """Tests for _fetch_all_page_html."""

    @patch(f"{_MODULE}.requests.get")
    def test_returns_html_on_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html>some content</html>"
        mock_get.return_value = mock_resp

        result = _fetch_all_page_html("owner/repo", 5, "token123")
        assert result == "<html>some content</html>"
        mock_get.assert_called_once()

    @patch(f"{_MODULE}.requests.get")
    def test_returns_empty_on_non_200(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = _fetch_all_page_html("owner/repo", 5, "token123")
        assert result == ""

    @patch(f"{_MODULE}.requests.get")
    def test_fetches_include_fragments(self, mock_get: MagicMock) -> None:
        main_html = '<html><include-fragment src="/owner/repo/pull/5/diffs?page=2"></include-fragment></html>'
        fragment_html = "<div>lazy loaded diff</div>"

        main_resp = MagicMock()
        main_resp.status_code = 200
        main_resp.text = main_html

        frag_resp = MagicMock()
        frag_resp.status_code = 200
        frag_resp.text = fragment_html

        mock_get.side_effect = [main_resp, frag_resp]

        result = _fetch_all_page_html("owner/repo", 5, "token123")
        assert main_html in result
        assert fragment_html in result
        assert mock_get.call_count == 2

    @patch(f"{_MODULE}.requests.get")
    def test_fragment_non_200_skipped(self, mock_get: MagicMock) -> None:
        main_html = (
            '<html><include-fragment src="https://github.com/owner/repo/pull/5/diffs?page=2"></include-fragment></html>'
        )

        main_resp = MagicMock()
        main_resp.status_code = 200
        main_resp.text = main_html

        frag_resp = MagicMock()
        frag_resp.status_code = 500
        frag_resp.text = ""

        mock_get.side_effect = [main_resp, frag_resp]

        result = _fetch_all_page_html("owner/repo", 5, "token123")
        # Main HTML is still returned, fragment not appended
        assert result == main_html

    @patch(f"{_MODULE}.requests.get")
    def test_fragment_url_with_html_entities(self, mock_get: MagicMock) -> None:
        main_html = '<html><include-fragment src="/owner/repo/pull/5/diffs?a=1&amp;b=2"></include-fragment></html>'
        fragment_html = "<div>content</div>"

        main_resp = MagicMock()
        main_resp.status_code = 200
        main_resp.text = main_html

        frag_resp = MagicMock()
        frag_resp.status_code = 200
        frag_resp.text = fragment_html

        mock_get.side_effect = [main_resp, frag_resp]

        result = _fetch_all_page_html("owner/repo", 5, "token123")
        # Verify the fragment URL was unescaped (& not &amp;)
        call_args = mock_get.call_args_list[1]
        assert "&amp;" not in call_args[0][0]
        assert fragment_html in result
