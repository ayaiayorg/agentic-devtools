"""Tests for agentic_devtools.cli.setup.platform_detection.DetectionResult."""

from agentic_devtools.cli.setup.platform_detection import DetectionResult


class TestDetectionResultDefaults:
    """DetectionResult default values."""

    def test_default_values(self):
        """DetectionResult has correct defaults."""
        result = DetectionResult()

        assert result.detected_issue_platforms == ()
        assert result.detected_code_hosting is None
        assert result.github_repo is None
        assert result.azure_devops_project is None
        assert result.confidence == {}


class TestDetectionResultFrozen:
    """DetectionResult is frozen (immutable)."""

    def test_is_frozen(self):
        """DetectionResult is immutable."""
        import dataclasses

        result = DetectionResult()

        try:
            result.github_repo = "test"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")  # pragma: no cover
        except dataclasses.FrozenInstanceError:
            pass


class TestDetectionResultConfidenceImmutability:
    """DetectionResult confidence field is truly immutable."""

    def test_confidence_is_immutable(self):
        """Confidence mapping cannot be mutated after construction."""
        from types import MappingProxyType

        result = DetectionResult(confidence={"jira": "high"})

        assert isinstance(result.confidence, MappingProxyType)
        assert result.confidence["jira"] == "high"

        try:
            result.confidence["jira"] = "low"  # type: ignore[index]
            raise AssertionError("Should have raised TypeError")  # pragma: no cover
        except TypeError:
            pass

    def test_confidence_wraps_dict_to_mapping_proxy(self):
        """A plain dict passed as confidence is wrapped in MappingProxyType."""
        from types import MappingProxyType

        raw = {"github": "medium"}
        result = DetectionResult(confidence=raw)

        # Wrapped in MappingProxyType
        assert isinstance(result.confidence, MappingProxyType)
        # Original dict mutation does not affect the result
        raw["github"] = "changed"
        assert result.confidence["github"] == "medium"

    def test_confidence_wraps_non_dict_mapping(self):
        """A non-dict Mapping (e.g. UserDict) is also wrapped in MappingProxyType."""
        from collections import UserDict
        from types import MappingProxyType

        raw = UserDict({"jira": "high"})
        result = DetectionResult(confidence=raw)

        assert isinstance(result.confidence, MappingProxyType)
        assert result.confidence["jira"] == "high"

    def test_confidence_already_mapping_proxy_not_rewrapped(self):
        """A MappingProxyType passed as confidence is not double-wrapped."""
        from types import MappingProxyType

        proxy = MappingProxyType({"azure_devops": "high"})
        result = DetectionResult(confidence=proxy)

        assert result.confidence is proxy
