"""Tests for pass_e2.task_classifier — classify_test_types."""

from agentic_devtools.cli.speckit.pass_e2.task_classifier import classify_test_types


class TestClassifyTestTypes:
    """Verify FR-006 test-type classification."""

    def test_happy_path_keyword(self) -> None:
        types = classify_test_types("Write happy-path test for login")
        assert "happy-path" in types

    def test_success_keyword(self) -> None:
        types = classify_test_types("Test success scenario for payment")
        assert "happy-path" in types

    def test_edge_case_keyword(self) -> None:
        types = classify_test_types("Test edge case for boundary input")
        assert "edge-case" in types

    def test_negative_keyword(self) -> None:
        types = classify_test_types("Test invalid input rejection")
        assert "negative" in types

    def test_integration_keyword(self) -> None:
        types = classify_test_types("Write integration test for API")
        assert "integration" in types

    def test_e2e_keyword(self) -> None:
        types = classify_test_types("Run e2e test for full flow")
        assert "e2e" in types

    def test_unit_keyword(self) -> None:
        types = classify_test_types("Add unit test for helper function")
        assert "unit" in types

    def test_infrastructure_keyword(self) -> None:
        types = classify_test_types("Write infrastructure setup tests")
        assert "infrastructure" in types

    def test_multiple_types(self) -> None:
        types = classify_test_types("Write integration test for end-to-end flow")
        assert "integration" in types
        assert "e2e" in types

    def test_no_test_type_for_plain_task(self) -> None:
        types = classify_test_types("Implement user login")
        assert types == []

    def test_hyphen_space_normalization(self) -> None:
        types = classify_test_types("Write happy path test")
        assert "happy-path" in types
