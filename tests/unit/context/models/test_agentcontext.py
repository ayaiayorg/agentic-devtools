"""Tests for agentic_devtools.context.models.AgentContext."""

from agentic_devtools.context.models import AgentContext


class TestAgentContext:
    """Tests for the AgentContext dataclass."""

    def test_instantiation_with_defaults(self):
        """All optional fields default to empty/None when only issue_key is given."""
        ctx = AgentContext(issue_key="TEST-1")
        assert ctx.issue_key == "TEST-1"
        assert ctx.issue_details is None
        assert ctx.parent_issue is None
        assert ctx.epic_issue is None
        assert ctx.remote_links == []
        assert ctx.relevant_files == []
        assert ctx.recent_changes == []
        assert ctx.test_coverage == {}
        assert ctx.documentation == []
        assert ctx.errors == []

    def test_instantiation_with_all_fields(self):
        """All fields can be populated explicitly."""
        ctx = AgentContext(
            issue_key="PROJ-42",
            issue_details={"key": "PROJ-42", "summary": "Test"},
            parent_issue={"key": "PROJ-10"},
            epic_issue={"key": "PROJ-1"},
            remote_links=[{"url": "https://example.com"}],
            relevant_files=["src/main.py"],
            recent_changes=[{"sha": "abc123"}],
            test_coverage={"src/main.py": {"percent_covered": 80.0}},
            documentation=[{"path": "README.md", "content": "# Hello"}],
            errors=["some warning"],
        )
        assert ctx.issue_key == "PROJ-42"
        assert ctx.issue_details == {"key": "PROJ-42", "summary": "Test"}
        assert ctx.parent_issue == {"key": "PROJ-10"}
        assert ctx.epic_issue == {"key": "PROJ-1"}
        assert ctx.remote_links == [{"url": "https://example.com"}]
        assert ctx.relevant_files == ["src/main.py"]
        assert ctx.recent_changes == [{"sha": "abc123"}]
        assert ctx.test_coverage == {"src/main.py": {"percent_covered": 80.0}}
        assert ctx.documentation == [{"path": "README.md", "content": "# Hello"}]
        assert ctx.errors == ["some warning"]

    def test_to_dict_returns_json_serializable(self):
        """to_dict returns a plain dict with all fields."""
        ctx = AgentContext(
            issue_key="TEST-1",
            issue_details={"key": "TEST-1"},
            remote_links=[{"url": "https://example.com"}],
        )
        d = ctx.to_dict()
        assert isinstance(d, dict)
        assert d["issue_key"] == "TEST-1"
        assert d["issue_details"] == {"key": "TEST-1"}
        assert d["remote_links"] == [{"url": "https://example.com"}]
        assert d["parent_issue"] is None
        assert d["errors"] == []

    def test_to_dict_with_none_values(self):
        """to_dict handles None values natively."""
        ctx = AgentContext(issue_key="X")
        d = ctx.to_dict()
        assert d["issue_details"] is None
        assert d["parent_issue"] is None
        assert d["epic_issue"] is None

    def test_from_dict_full_round_trip(self):
        """from_dict reconstructs an equivalent AgentContext from to_dict output."""
        original = AgentContext(
            issue_key="PROJ-5",
            issue_details={"summary": "test"},
            relevant_files=["a.py"],
            errors=["err1"],
        )
        d = original.to_dict()
        restored = AgentContext.from_dict(d)
        assert restored.issue_key == original.issue_key
        assert restored.issue_details == original.issue_details
        assert restored.relevant_files == original.relevant_files
        assert restored.errors == original.errors

    def test_from_dict_with_missing_keys(self):
        """from_dict uses defaults for missing keys."""
        ctx = AgentContext.from_dict({"issue_key": "TEST-1"})
        assert ctx.issue_key == "TEST-1"
        assert ctx.issue_details is None
        assert ctx.relevant_files == []
        assert ctx.errors == []

    def test_from_dict_ignores_extra_keys(self):
        """from_dict silently ignores keys not in the dataclass."""
        ctx = AgentContext.from_dict({"issue_key": "TEST-1", "unknown_field": "value"})
        assert ctx.issue_key == "TEST-1"
        assert not hasattr(ctx, "unknown_field")
