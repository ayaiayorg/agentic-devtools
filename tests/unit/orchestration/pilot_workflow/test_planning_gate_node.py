"""Tests for planning_gate_node human-in-the-loop gate."""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from agentic_devtools.orchestration.graph_builder import build_work_on_issue_graph


class TestPlanningGateNode:
    def test_interrupt_pauses_execution(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        try:
            compiled = build_work_on_issue_graph(checkpointer=saver)
            config = {"configurable": {"thread_id": "gate-test"}}

            result = compiled.invoke(
                {
                    "issue_key": "GATE-1",
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
        finally:
            conn.close()

    def test_resume_sets_human_approved(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        try:
            compiled = build_work_on_issue_graph(checkpointer=saver)
            config = {"configurable": {"thread_id": "gate-resume"}}

            compiled.invoke(
                {
                    "issue_key": "GATE-2",
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

            result = compiled.invoke(Command(resume=True), config)
            assert result["human_approved"] is True
        finally:
            conn.close()

    def test_resume_appends_approval_event(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        try:
            compiled = build_work_on_issue_graph(checkpointer=saver)
            config = {"configurable": {"thread_id": "gate-event"}}

            compiled.invoke(
                {
                    "issue_key": "GATE-3",
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

            result = compiled.invoke(Command(resume=True), config)
            event_names = [e["event"] for e in result["events"]]
            assert "plan_approved" in event_names
        finally:
            conn.close()
