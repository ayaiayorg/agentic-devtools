"""Tests for build_work_on_issue_graph factory function."""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from agentic_devtools.orchestration.graph_builder import build_work_on_issue_graph


class TestBuildWorkOnIssueGraph:
    """Tests for build_work_on_issue_graph()."""

    def test_returns_compiled_state_graph(self):
        compiled = build_work_on_issue_graph()
        assert isinstance(compiled, CompiledStateGraph)

    def test_graph_contains_all_expected_nodes(self):
        compiled = build_work_on_issue_graph()
        node_names = set(compiled.get_graph().nodes.keys())
        expected = {
            "__start__",
            "__end__",
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
        }
        assert expected == node_names

    def test_compiles_without_checkpointer(self):
        compiled = build_work_on_issue_graph(checkpointer=None)
        assert compiled is not None

    def test_compiles_with_checkpointer(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        try:
            compiled = build_work_on_issue_graph(checkpointer=saver)
            assert isinstance(compiled, CompiledStateGraph)
        finally:
            conn.close()

    def test_happy_path_execution_reaches_completion(self):
        compiled = build_work_on_issue_graph()
        result = compiled.invoke(
            {
                "issue_key": "TEST-1",
                "step": "",
                "status": "",
                "plan": "",
                "error": None,
                "retry_count": 0,
                "events": [],
                "human_approved": True,
            }
        )
        assert result["step"] == "completion"
        assert result["status"] == "completed"

    def test_happy_path_accumulates_events(self):
        compiled = build_work_on_issue_graph()
        result = compiled.invoke(
            {
                "issue_key": "TEST-1",
                "step": "",
                "status": "",
                "plan": "",
                "error": None,
                "retry_count": 0,
                "events": [],
                "human_approved": True,
            }
        )
        event_names = [e["event"] for e in result["events"]]
        assert "initiate_completed" in event_names
        assert "planning_completed" in event_names
        assert "completion_completed" in event_names

    def test_error_path_routes_through_setup(self):
        compiled = build_work_on_issue_graph()
        result = compiled.invoke(
            {
                "issue_key": "TEST-1",
                "step": "",
                "status": "",
                "plan": "",
                "error": "pre-flight failed",
                "retry_count": 0,
                "events": [],
                "human_approved": True,
            }
        )
        event_names = [e["event"] for e in result["events"]]
        assert "setup_completed" in event_names
        assert result["step"] == "completion"

    def test_interrupt_resume_flow(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        try:
            compiled = build_work_on_issue_graph(checkpointer=saver)
            config = {"configurable": {"thread_id": "interrupt-test"}}

            result = compiled.invoke(
                {
                    "issue_key": "TEST-1",
                    "step": "",
                    "status": "",
                    "plan": "",
                    "error": None,
                    "retry_count": 0,
                    "events": [],
                    "human_approved": False,
                },
                config,
            )
            assert result["step"] == "planning"
            assert result["human_approved"] is False

            result2 = compiled.invoke(Command(resume=True), config)
            assert result2["step"] == "completion"
            assert result2["human_approved"] is True
        finally:
            conn.close()

    def test_crash_recovery_from_checkpoint(self, tmp_path):
        db_path = str(tmp_path / "crash.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        try:
            compiled1 = build_work_on_issue_graph(checkpointer=saver)
            config = {"configurable": {"thread_id": "crash-test"}}

            result1 = compiled1.invoke(
                {
                    "issue_key": "CRASH-1",
                    "step": "",
                    "status": "",
                    "plan": "",
                    "error": None,
                    "retry_count": 0,
                    "events": [],
                    "human_approved": False,
                },
                config,
            )
            assert result1["step"] == "planning"

            compiled2 = build_work_on_issue_graph(checkpointer=saver)
            result2 = compiled2.invoke(Command(resume=True), config)
            assert result2["step"] == "completion"
            assert result2["status"] == "completed"
        finally:
            conn.close()

    def test_entry_point_is_initiate(self):
        compiled = build_work_on_issue_graph()
        graph = compiled.get_graph()
        start_edges = [e for e in graph.edges if e.source == "__start__"]
        assert len(start_edges) == 1
        assert start_edges[0].target == "initiate"

    def test_completion_connects_to_end(self):
        compiled = build_work_on_issue_graph()
        graph = compiled.get_graph()
        completion_edges = [e for e in graph.edges if e.source == "completion"]
        targets = {e.target for e in completion_edges}
        assert "__end__" in targets
