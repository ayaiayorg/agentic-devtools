"""Tests for record_verdict function."""

import pytest

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    ModelVerdict,
    ReviewStatus,
    VerdictType,
)
from agentic_devtools.cli.azure_devops.verdict_protocol import record_verdict


def _make_file_entry(**kwargs) -> FileEntry:
    defaults = {"threadId": 100, "commentId": 200, "folder": "src", "fileName": "app.py"}
    defaults.update(kwargs)
    return FileEntry(**defaults)


class TestRecordVerdict:
    """Tests for record_verdict."""

    def test_record_agree_creates_new_entry(self):
        """Creates a new ModelVerdict when model not yet tracked."""
        fe = _make_file_entry()
        mv = record_verdict(fe, "Claude Opus 4.6", VerdictType.AGREE, ReviewStatus.APPROVED.value)
        assert mv.modelId == "Claude Opus 4.6"
        assert mv.status == ReviewStatus.APPROVED.value
        assert mv.verdictType == VerdictType.AGREE
        assert len(fe.modelVerdicts) == 1

    def test_record_verdict_updates_existing(self):
        """Updates an existing ModelVerdict entry."""
        existing = ModelVerdict(modelId="Model A", status=ReviewStatus.IN_PROGRESS.value)
        fe = _make_file_entry(modelVerdicts=[existing])
        mv = record_verdict(fe, "Model A", VerdictType.DISAGREE, ReviewStatus.NEEDS_WORK.value)
        assert mv is existing
        assert mv.status == ReviewStatus.NEEDS_WORK.value
        assert mv.verdictType == VerdictType.DISAGREE
        assert len(fe.modelVerdicts) == 1

    def test_record_supplement(self):
        """Records a supplement verdict."""
        fe = _make_file_entry()
        mv = record_verdict(fe, "Gemini Pro 3.1", VerdictType.SUPPLEMENT, ReviewStatus.APPROVED.value)
        assert mv.verdictType == VerdictType.SUPPLEMENT

    def test_invalid_verdict_type_raises(self):
        """Raises ValueError for invalid verdict type."""
        fe = _make_file_entry()
        with pytest.raises(ValueError, match="Invalid verdict_type"):
            record_verdict(fe, "Model A", "invalid", ReviewStatus.APPROVED.value)

    def test_non_terminal_status_raises(self):
        """Raises ValueError for non-terminal status."""
        fe = _make_file_entry()
        with pytest.raises(ValueError, match="terminal status"):
            record_verdict(fe, "Model A", VerdictType.AGREE, ReviewStatus.IN_PROGRESS.value)

    def test_multiple_models(self):
        """Records verdicts for multiple models on the same file."""
        fe = _make_file_entry()
        record_verdict(fe, "Model A", VerdictType.AGREE, ReviewStatus.APPROVED.value)
        record_verdict(fe, "Model B", VerdictType.DISAGREE, ReviewStatus.NEEDS_WORK.value)
        assert len(fe.modelVerdicts) == 2
        assert fe.modelVerdicts[0].modelId == "Model A"
        assert fe.modelVerdicts[1].modelId == "Model B"
