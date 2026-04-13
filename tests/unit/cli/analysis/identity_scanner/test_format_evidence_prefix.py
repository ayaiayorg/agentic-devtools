"""Tests for format_evidence_prefix()."""

from __future__ import annotations

from agentic_devtools.cli.analysis.identity_scanner import format_evidence_prefix


class TestFormatEvidencePrefix:
    """Tests for the evidence attribution prefix."""

    def test_standard_format(self):
        assert format_evidence_prefix("alice") == "[identity: alice]"

    def test_special_characters(self):
        assert format_evidence_prefix("user+tag") == "[identity: user+tag]"

    def test_empty_identity(self):
        assert format_evidence_prefix("") == "[identity: ]"
