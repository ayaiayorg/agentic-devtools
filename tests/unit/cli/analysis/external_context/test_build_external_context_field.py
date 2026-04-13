"""Tests for build_external_context_field()."""

from __future__ import annotations

from agentic_devtools.cli.analysis.external_context import (
    ExternalContext,
    ExternalLogEvidence,
    build_external_context_field,
)


class TestBuildExternalContextField:
    """Tests for serializing ExternalContext to dict."""

    def test_none_input_returns_none(self):
        """None → None (serialized as null in JSON)."""
        assert build_external_context_field(None) is None

    def test_populated_context_returns_dict(self):
        """Populated ExternalContext → dict with correct keys."""
        ctx = ExternalContext(
            worktrees_scanned=["/path/to/wt"],
            log_evidence=[
                ExternalLogEvidence(
                    worktree_path="/path/to/wt",
                    identity="alice",
                    log_file="/path/to/log.log",
                    excerpt="log content",
                    timestamp="2026-01-01T00:00:00+00:00",
                )
            ],
            identities_scanned=["alice"],
        )
        result = build_external_context_field(ctx)

        assert result is not None
        assert result["worktrees_scanned"] == ["/path/to/wt"]
        assert len(result["log_evidence"]) == 1
        assert result["log_evidence"][0]["identity"] == "alice"
        assert result["log_evidence"][0]["excerpt"] == "log content"
        assert result["identities_scanned"] == ["alice"]

    def test_empty_context_returns_dict(self):
        """ExternalContext with empty lists → dict with empty lists."""
        ctx = ExternalContext(
            worktrees_scanned=[],
            log_evidence=[],
            identities_scanned=[],
        )
        result = build_external_context_field(ctx)

        assert result is not None
        assert result["worktrees_scanned"] == []
        assert result["log_evidence"] == []
        assert result["identities_scanned"] == []
