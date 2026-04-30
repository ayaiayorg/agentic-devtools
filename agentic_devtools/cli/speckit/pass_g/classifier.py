"""Classification orchestrator (FR-003, FR-005, FR-015, FR-016)."""

from __future__ import annotations

from .intent_detector import detect_new_symbol_intent
from .inventory import SymbolInventory
from .matcher import classify_match_confidence, exact_match, fuzzy_match
from .models import Finding, MatchStatus, Reference, ReferenceKind

# Minimum length for a reference to be eligible for matching (references
# with fewer characters are skipped).
_MIN_REFERENCE_LENGTH = 3

# Maximum candidates shown in human-readable explanation text.
_MAX_CANDIDATES_IN_EXPLANATION = 3


def classify_references(
    references: list[Reference],
    inventory: SymbolInventory,
) -> list[Finding]:
    """Classify each reference against the inventory (FR-003, FR-005, FR-015, FR-016).

    This function does NOT modify the plan or the repository.
    """
    findings: list[Finding] = []

    for ref in references:
        finding = _classify_single(ref, inventory)
        if finding is not None:
            findings.append(finding)

    return findings


def _classify_single(ref: Reference, inventory: SymbolInventory) -> Finding | None:
    """Classify a single reference."""
    # Skip unclassifiable references
    if _should_skip(ref):
        return Finding(
            reference=ref,
            status=MatchStatus.SKIPPED,
            explanation="Reference too short or unclassifiable to resolve.",
        )

    # Check new-symbol intent first (FR-006)
    if detect_new_symbol_intent(ref):
        return Finding(
            reference=ref,
            status=MatchStatus.NEW_SYMBOL,
            explanation="Reference appears to describe a new symbol to be created.",
        )

    # Attempt exact match (FR-007)
    exact_results = exact_match(ref.text, inventory)
    if exact_results:
        return Finding(
            reference=ref,
            status=MatchStatus.MATCHED,
            confidence_level="exact",
            explanation="Exact match found in repository.",
        )

    # Check for partial match: file/module exists but symbol not found within it
    partial = _check_partial_match(ref, inventory)
    if partial is not None:
        return partial

    # Attempt fuzzy match (FR-008)
    candidates = fuzzy_match(ref.text, ref.kind, inventory)

    if not candidates:
        return Finding(
            reference=ref,
            status=MatchStatus.INVALID,
            confidence_level="none",
            explanation="No match found in repository; no reliable suggestion available.",
        )

    confidence = classify_match_confidence(candidates)

    if confidence == "ambiguous":
        return Finding(
            reference=ref,
            status=MatchStatus.AMBIGUOUS,
            candidates=candidates,
            confidence_level=confidence,
            explanation=(
                f"Multiple candidates within margin: "
                f"{', '.join(c.symbol_name for c in candidates[:_MAX_CANDIDATES_IN_EXPLANATION])}"
            ),
        )

    # INVALID with suggestions
    return Finding(
        reference=ref,
        status=MatchStatus.INVALID,
        candidates=candidates,
        confidence_level=confidence,
        explanation=(
            f"Reference not found. Nearest match: "
            f"`{candidates[0].symbol_name}` (score: {candidates[0].similarity_score:.2f})"
        ),
    )


def _should_skip(ref: Reference) -> bool:
    """Determine if a reference should be skipped from matching (NFR-005)."""
    text = ref.text

    # Too short
    if len(text) < _MIN_REFERENCE_LENGTH:
        return True

    # Contains type annotations, function signatures, or assignment operators
    if any(marker in text for marker in (" -> ", " = ", ": ", "...", "| ")):
        return True

    # Looks like a shell command (contains spaces and doesn't look like a path)
    if " " in text and "/" not in text and "." not in text:
        return True

    # Single punctuation or formatting artifacts
    if text in (",", ".", ";", "|", "\\"):  # pragma: no cover – caught by length check above
        return True

    # Clearly a sentence fragment or description (too many spaces)
    if text.count(" ") >= 3:
        return True

    # Pattern references like F-01, FR-001
    if ref.kind == ReferenceKind.UNCLASSIFIED and len(text) <= 4:
        return True

    return False


def _check_partial_match(ref: Reference, inventory: SymbolInventory) -> Finding | None:
    """Check if a module/file exists but the specific symbol is missing."""
    if ref.kind == ReferenceKind.MODULE_PATH and "." in ref.text:
        # Check if the module part exists as a file
        parts = ref.text.rsplit(".", 1)
        module_path = parts[0].replace(".", "/")
        # Try as directory with __init__.py or as .py file
        candidates_paths = [
            f"{module_path}/__init__.py",
            f"{module_path}.py",
        ]
        for candidate_path in candidates_paths:
            if inventory.has_file(candidate_path):
                return Finding(
                    reference=ref,
                    status=MatchStatus.PARTIAL,
                    explanation=(
                        f"Module `{parts[0]}` exists (as `{candidate_path}`) "
                        f"but symbol `{parts[1]}` not found within it."
                    ),
                )

    if ref.kind == ReferenceKind.METHOD_NAME and "." in ref.text:
        parts = ref.text.rsplit(".", 1)
        class_name = parts[0]
        method_name = parts[1]
        # Check if class exists
        symbols = inventory.get_symbols_by_name(class_name)
        if symbols:
            return Finding(
                reference=ref,
                status=MatchStatus.PARTIAL,
                explanation=(f"Class `{class_name}` found but method `{method_name}` not found within it."),
            )

    return None
