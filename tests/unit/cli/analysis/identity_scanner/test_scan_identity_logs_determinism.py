"""Determinism tests for scan_identity_logs() — NFR-005."""

from __future__ import annotations

import json

from agentic_devtools.cli.analysis.identity_scanner import scan_identity_logs


class TestScanIdentityLogsDeterminism:
    """NFR-005: Identical inputs → identical output."""

    def test_consecutive_calls_produce_identical_output(self, tmp_path):
        """Two consecutive calls with same filesystem → identical JSON."""
        wf = tmp_path / ".agdt" / "workflows"
        for name in ["charlie", "alice", "bob"]:
            logs = wf / name / "PROJ-1" / "background-tasks" / "logs"
            logs.mkdir(parents=True)
            (logs / "task_a.log").write_text("log a", encoding="utf-8")
            (logs / "task_b.log").write_text("log b", encoding="utf-8")

        result1 = scan_identity_logs(tmp_path, "PROJ-1")
        result2 = scan_identity_logs(tmp_path, "PROJ-1")

        # Serialize to JSON for byte-identical comparison
        json1 = json.dumps(
            [{"identity": r.identity, "path": str(r.path), "modified_time": r.modified_time} for r in result1],
            sort_keys=True,
        )
        json2 = json.dumps(
            [{"identity": r.identity, "path": str(r.path), "modified_time": r.modified_time} for r in result2],
            sort_keys=True,
        )

        assert json1 == json2
