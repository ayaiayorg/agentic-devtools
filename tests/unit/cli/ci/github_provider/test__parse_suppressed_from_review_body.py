"""Tests for _parse_suppressed_from_review_body() in the GitHub provider."""

from agentic_devtools.cli.ci.github_provider import _parse_suppressed_from_review_body


class TestParseSuppressedFromReviewBody:
    """Tests for _parse_suppressed_from_review_body()."""

    def test_returns_empty_list_for_empty_body(self) -> None:
        assert _parse_suppressed_from_review_body("") == []

    def test_returns_empty_list_when_no_details_block(self) -> None:
        body = "Some review text without any suppressed comments."
        assert _parse_suppressed_from_review_body(body) == []

    def test_returns_empty_list_for_empty_details_block(self) -> None:
        body = "<details>\n<summary>Comments suppressed due to low confidence (0)</summary>\n\n</details>"
        assert _parse_suppressed_from_review_body(body) == []

    def test_parses_bold_file_path_entry(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "**src/foo.py**: Fix the null check here\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1
        assert result[0].path == "src/foo.py"
        assert result[0].body == "Fix the null check here"
        assert result[0].is_suppressed is True
        assert result[0].id < 0
        assert result[0].html_url == ""

    def test_parses_code_formatted_file_path(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "`src/bar.py`: Use a helper function\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1
        assert result[0].path == "src/bar.py"
        assert result[0].body == "Use a helper function"
        assert result[0].is_suppressed is True

    def test_parses_bold_code_formatted_file_path(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "**`src/baz.py`**: Add error handling\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1
        assert result[0].path == "src/baz.py"
        assert result[0].body == "Add error handling"

    def test_parses_multiple_entries(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (3)</summary>\n"
            "\n"
            "**src/foo.py**: Fix null check\n"
            "**src/bar.py**: Add error handling\n"
            "**src/baz.py**: Use helper\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 3
        assert result[0].path == "src/foo.py"
        assert result[1].path == "src/bar.py"
        assert result[2].path == "src/baz.py"

    def test_parses_entries_separated_by_blank_lines(self) -> None:
        """Blank lines between entries (common Markdown layout) are handled correctly."""
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (2)</summary>\n"
            "\n"
            "**src/foo.py**: Fix null check\n"
            "\n"
            "**src/bar.py**: Add error handling\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 2
        assert result[0].path == "src/foo.py"
        assert result[0].body == "Fix null check"
        assert result[1].path == "src/bar.py"
        assert result[1].body == "Add error handling"

    def test_parses_multiline_body_with_blank_line_before_next_entry(self) -> None:
        """Multi-line body followed by a blank line before the next header is parsed correctly."""
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (2)</summary>\n"
            "\n"
            "**src/foo.py**: This is a longer explanation\n"
            "that spans multiple lines.\n"
            "\n"
            "**src/bar.py**: Another finding\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 2
        assert result[0].path == "src/foo.py"
        assert "longer explanation" in result[0].body
        assert "spans multiple lines" in result[0].body
        assert result[1].path == "src/bar.py"
        assert result[1].body == "Another finding"

    def test_assigns_unique_negative_sentinel_ids(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (2)</summary>\n"
            "\n"
            "**a.py**: Comment A\n"
            "**b.py**: Comment B\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 2
        assert result[0].id == -1
        assert result[1].id == -2
        assert result[0].id != result[1].id

    def test_all_entries_have_is_suppressed_true(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "**x.py**: Some comment\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert all(c.is_suppressed for c in result)

    def test_fallback_to_unknown_file_when_no_path(self) -> None:
        """Lines without a file path pattern use (unknown file) marker."""
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "Some standalone comment without a file path\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1
        assert result[0].path == "(unknown file)"
        assert "standalone comment" in result[0].body

    def test_case_insensitive_summary_match(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments Suppressed Due To Low Confidence (1)</summary>\n"
            "\n"
            "**f.py**: Comment\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1

    def test_preserves_surrounding_review_text(self) -> None:
        """Parser only extracts from the <details> block, ignoring surrounding text."""
        body = (
            "## Review Summary\n\n"
            "This PR has issues.\n\n"
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "**src/x.py**: Fix this\n"
            "\n"
            "</details>\n\n"
            "## Conclusion\n\nPlease address the above."
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1
        assert result[0].path == "src/x.py"

    def test_multiline_body_text(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "**src/foo.py**: First line\n"
            "continuation of the comment\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1
        assert "First line" in result[0].body

    def test_structured_entry_with_blank_path_uses_unknown_file(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "**   **: Body text\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1
        assert result[0].path == "(unknown file)"
        assert result[0].body == "Body text"

    def test_structured_entry_with_empty_body_falls_back_to_raw_line(self) -> None:
        body = (
            "<details>\n<summary>Comments suppressed due to low confidence (1)</summary>\n\n**foo.py**:\n\n</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 1
        assert result[0].path == "(unknown file)"
        assert result[0].body == "**foo.py**:"

    def test_fallback_ignores_blank_lines(self) -> None:
        body = (
            "<details>\n"
            "<summary>Comments suppressed due to low confidence (1)</summary>\n"
            "\n"
            "first fallback comment\n"
            "\n"
            "second fallback comment\n"
            "\n"
            "</details>"
        )
        result = _parse_suppressed_from_review_body(body)
        assert len(result) == 2
        assert result[0].path == "(unknown file)"
        assert result[0].body == "first fallback comment"
        assert result[1].path == "(unknown file)"
        assert result[1].body == "second fallback comment"
