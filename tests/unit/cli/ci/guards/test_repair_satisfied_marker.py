"""Tests for repair-satisfied marker constants and regex extraction."""

from agentic_devtools.cli.ci.guards import (
    REPAIR_SATISFIED_MARKER,
    REVIEW_ID_MARKER_RE,
    THREAD_EVALUATED_MARKER,
)


class TestRepairSatisfiedMarkerConstants:
    """Tests for marker constants."""

    def test_repair_satisfied_marker_value(self) -> None:
        assert REPAIR_SATISFIED_MARKER == "<!-- ai-pr-loop:repair-satisfied -->"

    def test_thread_evaluated_marker_value(self) -> None:
        assert THREAD_EVALUATED_MARKER == "<!-- ai-pr-loop:thread-evaluated -->"

    def test_review_id_marker_regex_extracts_id(self) -> None:
        body = "<!-- review-id:12345 -->\nSome content"
        match = REVIEW_ID_MARKER_RE.search(body)
        assert match is not None
        assert match.group(1) == "12345"

    def test_review_id_marker_regex_tolerates_whitespace(self) -> None:
        body = "<!--  review-id : 12345-->"
        match = REVIEW_ID_MARKER_RE.search(body)
        assert match is not None
        assert match.group(1) == "12345"

    def test_review_id_marker_regex_no_match(self) -> None:
        body = "No marker here"
        match = REVIEW_ID_MARKER_RE.search(body)
        assert match is None

    def test_review_id_marker_regex_requires_digits(self) -> None:
        body = "<!-- review-id:abc -->"
        match = REVIEW_ID_MARKER_RE.search(body)
        assert match is None

    def test_markers_are_html_comments(self) -> None:
        """Markers should be valid HTML comments."""
        assert REPAIR_SATISFIED_MARKER.startswith("<!--")
        assert REPAIR_SATISFIED_MARKER.endswith("-->")
        assert THREAD_EVALUATED_MARKER.startswith("<!--")
        assert THREAD_EVALUATED_MARKER.endswith("-->")
