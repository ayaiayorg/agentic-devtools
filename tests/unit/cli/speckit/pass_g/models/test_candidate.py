"""Test Candidate dataclass (FR-008)."""

from agentic_devtools.cli.speckit.pass_g.models import Candidate, ReferenceKind


def test_candidate_fields():
    c = Candidate(
        symbol_name="my_func",
        file_path="src/module.py",
        similarity_score=0.85,
        kind=ReferenceKind.FUNCTION_NAME,
    )
    assert c.symbol_name == "my_func"
    assert c.file_path == "src/module.py"
    assert c.similarity_score == 0.85
    assert c.kind == ReferenceKind.FUNCTION_NAME
