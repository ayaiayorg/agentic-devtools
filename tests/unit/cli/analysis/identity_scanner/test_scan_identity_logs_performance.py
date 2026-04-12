"""Performance tests for scan_identity_logs() — NFR-002."""

from __future__ import annotations

import time

from agentic_devtools.cli.analysis.identity_scanner import (
    list_identity_directories,
    scan_identity_logs,
)


class TestScanIdentityLogsPerformance:
    """NFR-002: Latency < 2s for ≤ 20 identity directories."""

    def test_scan_completes_within_2s_for_20_identities(self, tmp_path):
        """20 identity dirs with logs → completes in < 2 seconds."""
        wf = tmp_path / ".agdt" / "workflows"
        for i in range(20):
            logs = wf / f"identity-{i:02d}" / "PROJ-1" / "background-tasks" / "logs"
            logs.mkdir(parents=True)
            (logs / "task.log").write_text(f"log from identity-{i:02d}", encoding="utf-8")

        start = time.monotonic()
        result = scan_identity_logs(tmp_path, "PROJ-1")
        elapsed = time.monotonic() - start

        assert len(result) == 20
        assert elapsed < 2.0, f"scan_identity_logs took {elapsed:.2f}s (> 2s)"

    def test_list_completes_within_2s_for_20_identities(self, tmp_path):
        """20 identity dirs → list_identity_directories completes in < 2 seconds."""
        wf = tmp_path / ".agdt" / "workflows"
        for i in range(20):
            d = wf / f"identity-{i:02d}"
            d.mkdir(parents=True)
            (d / ".identity-owner").write_text(f"user{i}@example.com", encoding="utf-8")

        start = time.monotonic()
        result = list_identity_directories(tmp_path)
        elapsed = time.monotonic() - start

        assert len(result) == 20
        assert elapsed < 2.0, f"list_identity_directories took {elapsed:.2f}s (> 2s)"
