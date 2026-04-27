"""Tests for ``ValidationResult`` dataclass."""

from agentic_devtools.cli.speckit.validate_frs import ValidationResult


class TestValidationResult:
    """ValidationResult field access, passed property, and to_json()."""

    def test_passed_true_when_uncovered_empty(self) -> None:
        result = ValidationResult(covered=["FR-001"], uncovered=[], total=1)
        assert result.passed is True

    def test_passed_false_when_uncovered_nonempty(self) -> None:
        result = ValidationResult(covered=["FR-001"], uncovered=["FR-002"], total=2)
        assert result.passed is False

    def test_passed_true_when_both_empty(self) -> None:
        result = ValidationResult(covered=[], uncovered=[], total=0)
        assert result.passed is True

    def test_field_access(self) -> None:
        result = ValidationResult(
            covered=["FR-001"],
            uncovered=["FR-002"],
            total=2,
            warning="test warning",
        )
        assert result.covered == ["FR-001"]
        assert result.uncovered == ["FR-002"]
        assert result.total == 2
        assert result.warning == "test warning"

    def test_default_values(self) -> None:
        result = ValidationResult()
        assert result.covered == []
        assert result.uncovered == []
        assert result.total == 0
        assert result.warning is None

    def test_to_json_schema(self) -> None:
        result = ValidationResult(
            covered=["FR-001", "FR-003"],
            uncovered=["FR-002"],
            total=3,
        )
        j = result.to_json()
        assert j == {
            "covered": ["FR-001", "FR-003"],
            "uncovered": ["FR-002"],
            "total": 3,
        }

    def test_to_json_excludes_warning(self) -> None:
        result = ValidationResult(covered=[], uncovered=[], total=0, warning="something")
        j = result.to_json()
        assert "warning" not in j

    def test_to_json_returns_new_lists(self) -> None:
        """Ensure to_json() returns independent list copies."""
        result = ValidationResult(covered=["FR-001"], uncovered=[], total=1)
        j = result.to_json()
        j["covered"].append("FR-999")
        assert result.covered == ["FR-001"]
