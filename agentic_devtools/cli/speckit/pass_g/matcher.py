"""Matching engine — exact and fuzzy matching (FR-007, FR-008, FR-009, FR-010)."""

from __future__ import annotations

import difflib

from .constants import (
    DISAMBIGUATION_MARGIN,
    HIGH_CONFIDENCE_THRESHOLD,
    MAX_CANDIDATES_PER_REFERENCE,
    SUGGESTION_THRESHOLD,
)
from .extractors.base import SymbolEntry
from .inventory import SymbolInventory
from .models import Candidate, ReferenceKind

# Minimum basename similarity to proceed with full path comparison (pre-filter).
_BASENAME_PREFILTER_THRESHOLD = 0.5


def exact_match(text: str, inventory: SymbolInventory) -> list[SymbolEntry]:
    """Check for an exact match in file paths or symbol names (FR-007)."""
    # Check file paths
    normalized = text.lstrip("/")
    if inventory.has_file(normalized):
        return [
            SymbolEntry(
                name=normalized,
                qualified_name=normalized,
                kind=ReferenceKind.FILE_PATH,
                file_path=normalized,
            )
        ]

    # Check symbol names (exact)
    symbols = inventory.get_symbols_by_name(text)
    if symbols:
        return symbols

    return []


def fuzzy_match(
    text: str,
    kind: ReferenceKind,
    inventory: SymbolInventory,
) -> list[Candidate]:
    """Find fuzzy matches using difflib.SequenceMatcher (FR-008, NFR-001, NFR-003).

    Returns candidates with similarity ≥ SUGGESTION_THRESHOLD, sorted
    deterministically by (score desc, symbol_name, file_path, kind) and
    capped at MAX_CANDIDATES_PER_REFERENCE.
    """
    candidates: list[Candidate] = []
    text_len = len(text)

    # Match against file paths for file-like references
    if kind in (ReferenceKind.FILE_PATH, ReferenceKind.MODULE_PATH, ReferenceKind.UNCLASSIFIED):
        text_base = text.rsplit("/", 1)[-1] if "/" in text else text
        text_base_len = len(text_base)

        for fp in inventory.get_all_file_paths():
            # Length pre-filter: skip if lengths are too different
            fp_len = len(fp)
            if _length_ratio_below_threshold(text_len, fp_len):
                continue

            # Quick basename comparison
            fp_base = fp.rsplit("/", 1)[-1] if "/" in fp else fp
            if _length_ratio_below_threshold(text_base_len, len(fp_base)):
                continue
            if difflib.SequenceMatcher(None, text_base, fp_base).ratio() < _BASENAME_PREFILTER_THRESHOLD:
                continue

            score = difflib.SequenceMatcher(None, text, fp).ratio()
            if score >= SUGGESTION_THRESHOLD:
                candidates.append(
                    Candidate(
                        symbol_name=fp,
                        file_path=fp,
                        similarity_score=score,
                        kind=ReferenceKind.FILE_PATH,
                    )
                )

    # Match against symbols — only compare same-kind or related symbols
    target_kinds = _related_kinds(kind)
    for sym in inventory.get_all_symbols():
        if sym.kind not in target_kinds:
            continue

        # Length pre-filter on name
        name_len = len(sym.name)
        if _length_ratio_below_threshold(text_len, name_len):
            # Also check qualified_name
            qual_len = len(sym.qualified_name)
            if _length_ratio_below_threshold(text_len, qual_len):
                continue

        score_name = difflib.SequenceMatcher(None, text, sym.name).ratio()
        best_score = score_name
        best_label = sym.name
        if sym.qualified_name != sym.name:
            score_qual = difflib.SequenceMatcher(None, text, sym.qualified_name).ratio()
            if score_qual > score_name:
                best_score = score_qual
                best_label = sym.qualified_name

        if best_score >= SUGGESTION_THRESHOLD:
            candidates.append(
                Candidate(
                    symbol_name=best_label,
                    file_path=sym.file_path,
                    similarity_score=best_score,
                    kind=sym.kind,
                )
            )

    # Deterministic sort: score desc, then symbol_name, file_path, kind
    candidates.sort(key=lambda c: (-c.similarity_score, c.symbol_name, c.file_path, c.kind.value))

    # Cap results
    return candidates[:MAX_CANDIDATES_PER_REFERENCE]


def _length_ratio_below_threshold(len_a: int, len_b: int) -> bool:
    """Return True if the lengths are too different to achieve SUGGESTION_THRESHOLD.

    SequenceMatcher.ratio() <= 2*min(a,b)/(a+b). If this upper bound is below
    our threshold, skip the comparison entirely.
    """
    if len_a == 0 or len_b == 0:
        return True
    max_possible = 2 * min(len_a, len_b) / (len_a + len_b)
    return max_possible < SUGGESTION_THRESHOLD


def _related_kinds(kind: ReferenceKind) -> set[ReferenceKind]:
    """Return the set of symbol kinds to compare against."""
    if kind == ReferenceKind.CLASS_NAME:
        return {ReferenceKind.CLASS_NAME}
    if kind == ReferenceKind.FUNCTION_NAME:
        return {ReferenceKind.FUNCTION_NAME, ReferenceKind.METHOD_NAME}
    if kind == ReferenceKind.METHOD_NAME:
        return {ReferenceKind.METHOD_NAME, ReferenceKind.FUNCTION_NAME}
    if kind == ReferenceKind.CLI_COMMAND:
        return {ReferenceKind.CLI_COMMAND}
    if kind == ReferenceKind.MODULE_PATH:
        return {ReferenceKind.CLASS_NAME, ReferenceKind.FUNCTION_NAME, ReferenceKind.METHOD_NAME}
    if kind == ReferenceKind.FILE_PATH:
        return set()  # FILE_PATH references only use file-path matching above
    # UNCLASSIFIED — check all symbol kinds
    return set(ReferenceKind)


def classify_match_confidence(candidates: list[Candidate]) -> str:
    """Classify match confidence based on candidate scores (FR-009, FR-010).

    Returns:
        "high" - single top candidate ≥ 0.90 with no competitor within margin
        "ambiguous" - multiple candidates within margin of each other
        "low" - candidates exist but below high-confidence threshold
    """
    if not candidates:
        return "none"

    top_score = candidates[0].similarity_score

    if top_score >= HIGH_CONFIDENCE_THRESHOLD:
        # Check for competitors within disambiguation margin
        competitors = [c for c in candidates[1:] if c.similarity_score >= top_score - DISAMBIGUATION_MARGIN]
        if not competitors:
            return "high"
        return "ambiguous"

    # Check if multiple candidates are within margin of each other
    if len(candidates) > 1:
        second_score = candidates[1].similarity_score
        if top_score - second_score <= DISAMBIGUATION_MARGIN:
            return "ambiguous"

    return "low"
