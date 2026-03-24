"""Tests for agentic_devtools.cli.setup.workflow_templates.TemplateInfo."""

import dataclasses

from agentic_devtools.cli.setup.workflow_templates import TemplateInfo


class TestTemplateInfoFields:
    """TemplateInfo field access."""

    def test_fields_are_accessible(self):
        """TemplateInfo fields can be read after construction."""
        info = TemplateInfo(name="Test", filename="test.py", description="A test template.")
        assert info.name == "Test"
        assert info.filename == "test.py"
        assert info.description == "A test template."


class TestTemplateInfoFrozen:
    """TemplateInfo is frozen (immutable)."""

    def test_is_frozen(self):
        """Assigning to a field raises FrozenInstanceError."""
        info = TemplateInfo(name="Test", filename="test.py", description="desc")
        try:
            info.name = "Changed"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")  # pragma: no cover
        except dataclasses.FrozenInstanceError:
            pass
