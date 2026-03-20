"""Tests for get_mermaid_diagram helper function."""

from agentic_devtools.orchestration.pilot_workflow import get_mermaid_diagram


class TestGetMermaidDiagram:
    def test_returns_non_empty_string(self):
        diagram = get_mermaid_diagram()
        assert isinstance(diagram, str)
        assert len(diagram) > 0

    def test_contains_expected_node_names(self):
        diagram = get_mermaid_diagram()
        expected_nodes = [
            "initiate",
            "setup",
            "planning",
            "planning_gate",
            "checklist_creation",
            "implementation",
            "implementation_review",
            "verification",
            "commit",
            "pull_request",
            "completion",
        ]
        for node in expected_nodes:
            assert node in diagram, f"Expected node '{node}' not found in Mermaid diagram"

    def test_contains_mermaid_graph_declaration(self):
        diagram = get_mermaid_diagram()
        assert "graph TD" in diagram or "graph LR" in diagram

    def test_contains_start_and_end(self):
        diagram = get_mermaid_diagram()
        assert "__start__" in diagram
        assert "__end__" in diagram
