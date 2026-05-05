"""Tests for pass_e2.constants — TEST_TYPE_KEYWORDS."""

from agentic_devtools.cli.speckit.pass_e2.constants import TEST_TYPE_KEYWORDS


class TestTestTypeKeywords:
    """Verify TEST_TYPE_KEYWORDS contains FR-006 type tables."""

    def test_is_non_empty(self) -> None:
        assert len(TEST_TYPE_KEYWORDS) > 0

    def test_contains_all_required_types(self) -> None:
        required = {
            "happy-path",
            "edge-case",
            "negative",
            "integration",
            "e2e",
            "unit",
            "infrastructure",
        }
        assert required == set(TEST_TYPE_KEYWORDS.keys())

    def test_each_type_has_non_empty_keywords(self) -> None:
        for test_type, keywords in TEST_TYPE_KEYWORDS.items():
            assert len(keywords) > 0, f"{test_type} has no keywords"

    def test_happy_path_keywords(self) -> None:
        keywords = TEST_TYPE_KEYWORDS["happy-path"]
        assert "happy path" in keywords
        assert "happy-path" in keywords
        assert "success" in keywords
        assert "nominal" in keywords

    def test_no_duplicates_within_type(self) -> None:
        for test_type, keywords in TEST_TYPE_KEYWORDS.items():
            assert len(keywords) == len(set(keywords)), f"{test_type} has duplicate keywords"
