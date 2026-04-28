# Implementation Plan: Pass G — Code Reference Cross-Referencing

**Issue**: #1204
**Branch**: `speckit/1204/phase-3-plan`
**Spec**: `specs/1204-speckit-pipeline-cross-reference/spec.md`

## 1. Technical Context

### Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.x | Matches existing `agentic_devtools` package |
| Fuzzy Matching | `difflib.SequenceMatcher` | Standard library only; `rapidfuzz` deferred per NFR-003 |
| AST Parsing | `ast` module (stdlib) | For Python symbol extraction from `.py` files |
| File Discovery | `git ls-files` + `pathlib` | Uses `git ls-files --cached --others --exclude-standard`; `PROTECTED_FILE_PATTERNS` as extra filter |
| CLI Integration | Dedicated `*_command()` entry point | Follows `validate_frs_command` precedent; standalone CLI callable independently of prompt-rendering helpers |
| Testing | pytest + 1:1:1 structure | Under `tests/unit/cli/speckit/` |

### Key Files (Existing)

| File | Purpose |
|------|---------|
| `agentic_devtools/cli/speckit/commands.py` | Entry points; `speckit_analyze()` delegates to `_run("analyze", ...)` for prompt rendering (not used by Pass G) |
| `agentic_devtools/cli/speckit/validate_frs.py` | Precedent: pure-function validation module with dataclasses, CLI entry point |
| `.github/agents/speckit.analyze.agent.md` | Local/CLI analyze agent prompt defining Passes A–F; **Pass G will be added here for `agdt-speckit-analyze` parity** |
| `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` | CI pipeline trigger script; `run_analyze_phase` contains the embedded analyze prompt that must also be updated so Pass G runs in CI |
| `agentic_devtools/cli/runner.py` | Dispatch map for CLI command routing |
| `pyproject.toml` | Entry point registration |

### Architecture Decision: Hybrid Approach

Pass G has **three integration surfaces**:

1. **CI pipeline analyze prompt** — Update `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (`run_analyze_phase`) so the pipeline-owned analyze prompt executes Pass G during CI spec generation.
2. **Local agent prompt extension** — Add matching Pass G instructions to `.github/agents/speckit.analyze.agent.md` so the local `agdt-speckit-analyze` flow stays behaviorally aligned with CI.
3. **Python library modules** — Provide deterministic Python utilities (symbol extraction, fuzzy matching, reference extraction) that can be invoked by the agent via CLI or imported directly for
   testing and future automation.

Related analyze-phase gate expectations must be reviewed and updated wherever the pipeline validates analyze output, so Pass G is required
consistently rather than being advisory only in the local CLI path.

This mirrors the `validate_frs.py` precedent: pure functions + CLI + pipeline prompt integration.

## 2. Research Summary

Key decisions from research:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Fuzzy matching engine | `difflib.SequenceMatcher` | NFR-003 mandates stdlib-only at launch |
| Symbol extraction | Python `ast` module | Reliable for classes, functions, methods; no external dependency |
| File discovery | `git ls-files` subprocess call | Correctly respects `.gitignore` (unlike `os.walk`/`pathlib`); fresh call per run avoids stale-cache per Edge Case 4 |
| Exclusion mechanism | `.gitignore` patterns + hardcoded protected list | Covers `_version.py`, `__pycache__`, `.git/` per FR-011 |
| New-symbol detection | Regex-based sentence-level marker scan | Named constant list per FR-006 clarification |
| Reference extraction from plan | Regex patterns for code fences and backtick-quoted identifiers | Conservative initial scope; bare-text patterns deferred to reduce noise |
| TOML parsing (`pyproject.toml`) | `tomllib` (3.11+) with minimal line-parser fallback | Maintains stdlib-only constraint; Python 3.10 uses regex-based `[project.scripts]` section parser |
| CLI entry point module | Dedicated `cross_ref.py` module | Follows `validate_frs.py` precedent; avoids mixing with prompt-rendering wrappers in `commands.py` |

## 3. Design Overview

### Module Architecture

```text
agentic_devtools/cli/speckit/
├── commands.py                    # Existing — prompt-rendering wrappers only (not used by Pass G)
├── validate_frs.py                # Existing — precedent pattern for dedicated CLI entry points
├── cross_ref.py                   # NEW — `cross_ref_command()` entry point for `agdt-speckit-cross-ref`
├── pass_g/                        # NEW — Pass G package
│   ├── __init__.py                # Public API exports
│   ├── constants.py               # Named constants (thresholds, markers, budget)
│   ├── models.py                  # Data models (Finding, Candidate, ReferenceKind, etc.)
│   ├── reference_extractor.py     # Extract code references from plan text
│   ├── inventory.py               # Repository symbol/file inventory builder
│   ├── extractors/                # Pluggable language extractors
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract base class for language extractors
│   │   └── python_extractor.py    # Python-specific symbol extraction
│   ├── matcher.py                 # Matching engine (exact + fuzzy)
│   ├── intent_detector.py         # New-symbol intent marker detection
│   ├── classifier.py              # Classification logic (matched/invalid/ambiguous/etc.)
│   └── reporter.py                # Structured finding output (Markdown + JSON)
```

### Data Flow

```text
plan.md text
    │
    ▼
reference_extractor ──► list[Reference]
                              │
                              ▼
inventory (repo scan) ──► SymbolInventory
                              │
                              ▼
intent_detector ──► annotate references with creation-intent flags
                              │
                              ▼
matcher ──► exact match → matched
         ├► fuzzy match (≥0.75) → suggestion/high-confidence
         └► no match → unresolved
                              │
                              ▼
classifier ──► Finding (matched | invalid | ambiguous | partial | skipped | new-symbol)
                              │
                              ▼
reporter ──► Markdown table + JSON structure for agent report
```

### Agent Integration

The agent prompt (`.github/agents/speckit.analyze.agent.md`) gains:

1. A new **Pass G: Code Reference Cross-Referencing** section in Detection Passes
2. Instructions to invoke `agdt-speckit-cross-ref` CLI (or use the Python output directly)
3. Finding IDs that continue to use the existing sequential analyze-report contract (`F-01`, `F-02`, …), including for Pass G output
4. Integration into the existing severity/report format and finding ID contract without special-casing

## 4. Implementation Phases

### Phase 1: Core Data Models and Constants

**Deliverables**: `constants.py`, `models.py`, `extractors/base.py`

#### 1a. Named Constants (`constants.py`)

Define all tunable parameters as module-level constants:

- `SUGGESTION_THRESHOLD = 0.75` — minimum similarity to surface a candidate
- `HIGH_CONFIDENCE_THRESHOLD = 0.90` — score for high-confidence classification
- `DISAMBIGUATION_MARGIN = 0.05` — competing candidate score margin
- `PERFORMANCE_WARNING_SECONDS = 30` — elapsed time before warning logged
- `NEW_SYMBOL_VERB_MARKERS` — tuple of verb phrases ("create", "add", "introduce", …)
- `NEW_SYMBOL_NOUN_MARKERS` — tuple of noun phrases ("new file", "new class", …)
- `PROTECTED_FILE_PATTERNS` — tuple of patterns (`_version.py`, `__pycache__`, `.git/`)
- `MAX_CANDIDATES_PER_REFERENCE = 5` — cap on suggestion list length

#### 1b. Data Models (`models.py`)

Dataclasses for the finding pipeline:

- `ReferenceKind` — enum: `FILE_PATH`, `MODULE_PATH`, `CLASS_NAME`, `FUNCTION_NAME`, `METHOD_NAME`, `CLI_COMMAND`, `UNCLASSIFIED`
- `Reference` — extracted plan reference: `text`, `kind`, `plan_location` (line number or section), `context_sentence`
- `MatchStatus` — enum: `MATCHED`, `INVALID`, `AMBIGUOUS`, `PARTIAL`, `SKIPPED`, `NEW_SYMBOL`
- `Candidate` — a match suggestion: `symbol_name`, `file_path`, `similarity_score`, `kind`
- `Finding` — the full result: `reference`, `status`, `candidates`, `confidence_level`, `explanation`

#### 1c. Extractor Base Class (`extractors/base.py`)

Abstract base with method signatures:

- `supported_extensions() -> set[str]`
- `extract_symbols(file_path: Path, content: str) -> list[SymbolEntry]`

Where `SymbolEntry` is a dataclass: `name`, `qualified_name`, `kind`, `file_path`, `line_number`

### Phase 2: Repository Inventory Builder

**Deliverables**: `inventory.py`, `extractors/python_extractor.py`

#### 2a. File Inventory (`inventory.py`)

- Discover tracked and untracked files via `git ls-files --cached --others --exclude-standard` to correctly respect `.gitignore` rules
- Collect all file paths relative to repo root
- Apply `PROTECTED_FILE_PATTERNS` as an extra filter on top of git's output
- Build a `SymbolInventory` class with lookup methods:
  - `has_file(path: str) -> bool`
  - `find_files(pattern: str) -> list[str]` (glob-style)
  - `get_symbols_by_name(name: str) -> list[SymbolEntry]`
  - `get_all_symbols() -> list[SymbolEntry]`
  - `get_all_file_paths() -> list[str]`

#### 2b. Python Extractor (`extractors/python_extractor.py`)

- Parse `.py` files using `ast.parse()` with error recovery (skip unparseable files)
- Extract:
  - Top-level class names (`ast.ClassDef`)
  - Top-level function names (`ast.FunctionDef`, `ast.AsyncFunctionDef`)
  - Method names within classes
  - Module dotted paths (derived from file path)
- Extract CLI entry points from `pyproject.toml` `[project.scripts]` section using a conditional
  import strategy: use `tomllib` (stdlib in Python 3.11+) when available, otherwise fall back to a
  minimal line-based parser that reads only the `[project.scripts]` section via regex (maintaining
  the stdlib-only constraint for Python 3.10 without introducing a third-party TOML dependency)
- Register as a pluggable extractor implementing the base class

### Phase 3: Plan Reference Extraction

**Deliverables**: `reference_extractor.py`

Extract code references from plan Markdown text with an intentionally narrow initial scope:

- **Backtick-quoted identifiers**: Match `` `symbol_name` ``, `` `path/to/file.py` ``, `` `module.submodule` ``
- **Code fence contents**: Extract identifiers from fenced code blocks (`````` ```)
- **Defer bare-text pattern matching initially**: Do **not** extract unquoted file path patterns, bare dotted module paths, or bare `agdt-*` command references in this phase
- Deduplicate extracted references; preserve plan location (line number) for each
- Classify each extracted reference into `ReferenceKind` based on syntactic patterns
- Capture deferred bare-text extraction as follow-up scope after the initial extractor proves low-noise

### Phase 4: Intent Detection and Matching

**Deliverables**: `intent_detector.py`, `matcher.py`

#### 4a. New-Symbol Intent Detection (`intent_detector.py`)

- For each extracted reference, examine the surrounding sentence/step
- Check for verb markers (case-insensitive) from `NEW_SYMBOL_VERB_MARKERS`
- Check for noun markers from `NEW_SYMBOL_NOUN_MARKERS`
- Return boolean flag per reference indicating creation intent

#### 4b. Matching Engine (`matcher.py`)

- **Exact matching**: Check if reference text exactly matches a file path, symbol name, or qualified name in inventory
- **Fuzzy matching** (when exact fails):
  - Use `difflib.SequenceMatcher.ratio()` against inventory entries of the same `ReferenceKind`
  - Ensure inventory file and symbol lists are sorted deterministically before matching so traversal order cannot vary by filesystem/OS
  - Filter candidates by `SUGGESTION_THRESHOLD` (≥ 0.75)
  - Sort candidates deterministically by `(score desc, symbol_name, file_path, kind)` so tied scores preserve stable ordering across repeated runs using only fields present on the `Candidate` model
  - Cap at `MAX_CANDIDATES_PER_REFERENCE`
- **High-confidence classification**: If top candidate scores ≥ 0.90 and no competitor within 0.05
- **Ambiguity detection**: Multiple candidates within 0.05 of each other → ambiguous; preserve the deterministic candidate ordering above when reporting ambiguous matches

### Phase 5: Classification and Reporting

**Deliverables**: `classifier.py`, `reporter.py`

#### 5a. Classifier (`classifier.py`)

Orchestrates the full pipeline for a single reference:

1. Check intent → if new-symbol, classify as `NEW_SYMBOL` and skip matching
2. Attempt exact match → if found, classify as `MATCHED`
3. Attempt fuzzy match → classify as `AMBIGUOUS`, `INVALID`, or high-confidence suggestion
4. Handle partial matches (file exists but symbol not found within it) → `PARTIAL`
5. Handle unclassifiable references → `SKIPPED`

Top-level function: `classify_references(references: list[Reference], inventory: SymbolInventory) -> list[Finding]`

#### 5b. Reporter (`reporter.py`)

- Generate Markdown table rows in the existing analysis report format:
  - `| F-01 | Code Reference | HIGH | plan.md:L42 | Reference to \`nonexistent_module.py\` not found | Nearest match: \`existing_module.py\` (score: 0.82) |`
- Generate structured JSON for programmatic consumption
- Severity mapping:
  - `INVALID` with no candidates → HIGH
  - `INVALID` with candidates → MEDIUM (correctable)
  - `AMBIGUOUS` → MEDIUM
  - `PARTIAL` → LOW
  - `SKIPPED` → LOW (informational)
- Emit performance warning if elapsed time exceeds `PERFORMANCE_WARNING_SECONDS`

### Phase 6: Agent Prompt Integration

**Deliverables**: Updated `.github/agents/speckit.analyze.agent.md`

- Add **Pass G: Code Reference Cross-Referencing** after Pass F in Detection Passes section
- Instructions for the agent to:
  1. Extract code references from `plan.md`
  2. Cross-reference against the repository file tree and Python symbols
  3. Detect new-symbol intent markers
  4. Apply fuzzy matching for unresolved references
  5. Report findings using the existing sequential finding ID contract (`F-01`, `F-02`, …)
- Add Pass G to severity assignment guidance
- Update the "Metrics" section to include code reference counts

### Phase 7: CLI Entry Point (Optional Standalone)

**Deliverables**: `cross_ref.py` module + CLI wiring for `agdt-speckit-cross-ref`

- Create `agentic_devtools/cli/speckit/cross_ref.py` with a dedicated `cross_ref_command()` entry point
  (follows `validate_frs.py` precedent; kept separate from `commands.py` which is reserved for prompt-rendering wrappers)
- Export from `agentic_devtools/cli/speckit/__init__.py` for `runner.py` dispatch
- Add entry point in `pyproject.toml` for standalone invocation
- Register in `runner.py` dispatch map
- Accept `--plan-file` and `--repo-root` arguments
- Output JSON or Markdown report
- This allows both agent-driven and standalone usage

### Phase 8: Testing

**Deliverables**: Full test suite under `tests/unit/cli/speckit/pass_g/`

Following TDD and 1:1:1 test structure (one test file per symbol — function,
class, enum, or named constant):

```text
tests/unit/cli/speckit/pass_g/
├── __init__.py
├── constants/
│   ├── __init__.py
│   ├── test_suggestion_threshold.py          # Constant: SUGGESTION_THRESHOLD
│   ├── test_high_confidence_threshold.py     # Constant: HIGH_CONFIDENCE_THRESHOLD
│   ├── test_disambiguation_margin.py         # Constant: DISAMBIGUATION_MARGIN
│   ├── test_performance_warning_seconds.py   # Constant: PERFORMANCE_WARNING_SECONDS
│   ├── test_new_symbol_verb_markers.py       # Constant: NEW_SYMBOL_VERB_MARKERS
│   ├── test_new_symbol_noun_markers.py       # Constant: NEW_SYMBOL_NOUN_MARKERS
│   ├── test_protected_file_patterns.py       # Constant: PROTECTED_FILE_PATTERNS
│   └── test_max_candidates_per_reference.py  # Constant: MAX_CANDIDATES_PER_REFERENCE
├── models/
│   ├── __init__.py
│   ├── test_referencekind.py                 # Enum: ReferenceKind
│   ├── test_reference.py                     # Dataclass: Reference
│   ├── test_matchstatus.py                   # Enum: MatchStatus
│   ├── test_candidate.py                     # Dataclass: Candidate
│   └── test_finding.py                       # Dataclass: Finding
├── extractors/
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   └── test_symbolextractor.py           # Class: SymbolExtractor
│   └── python_extractor/
│       ├── __init__.py
│       └── test_pythonextractor.py           # Class: PythonExtractor
├── inventory/
│   ├── __init__.py
│   ├── test_symbolinventory.py               # Class: SymbolInventory
│   └── test_build_inventory.py               # Function: build_inventory()
├── reference_extractor/
│   ├── __init__.py
│   ├── test_extract_references.py            # Function: extract_references()
│   └── test_classify_reference_kind.py       # Function: classify_reference_kind()
├── intent_detector/
│   ├── __init__.py
│   └── test_detect_new_symbol_intent.py      # Function: detect_new_symbol_intent()
├── matcher/
│   ├── __init__.py
│   ├── test_exact_match.py                   # Function: exact_match()
│   ├── test_fuzzy_match.py                   # Function: fuzzy_match()
│   └── test_classify_match_confidence.py     # Function: classify_match_confidence()
├── classifier/
│   ├── __init__.py
│   └── test_classify_references.py           # Function: classify_references()
└── reporter/
    ├── __init__.py
    ├── test_render_markdown.py               # Function: render_markdown()
    └── test_render_json.py                   # Function: render_json()
```

Key test scenarios mapped from spec User Scenarios:

| Test | US | Validates |
|------|----|-----------|
| Nonexistent file reference flagged | US1 | FR-005 |
| Multiple invalid refs reported separately | US1 | FR-013 |
| Valid-only plan produces no findings | US1 | FR-015 |
| Misspelled symbol gets ≥0.75 suggestion | US2 | FR-008 |
| No candidate above 0.75 → no suggestion | US2 | FR-008 |
| Multiple close candidates → ambiguous | US2 | FR-009, FR-010 |
| "create" marker suppresses flag | US3 | FR-006 |
| "new file" marker suppresses flag | US3 | FR-006 |
| Mixed new + existing refs in same step | US3 | FR-006 |
| Short ambiguous name → ambiguous finding | US4 | FR-010 |
| Module exists but symbol missing → partial | US4 | FR-003 |
| Unclassifiable reference → skipped | US4 | FR-015 |
| Report includes Pass G findings in sequential ID format | US5 | FR-012 |
| Empty plan → success, zero findings | Edge Case 1 | FR-015 |
| `_version.py` excluded from suggestions | Edge Case 3 | FR-011 |
| Non-Python file path still matched | Edge Case 7 | FR-007 |
| Deterministic output on repeated runs | NFR-001 | NFR-001 |

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `difflib` too slow for large repos | Medium | Medium | Early performance benchmarking; pre-filter candidates by kind before fuzzy matching |
| AST parse failures on complex Python | Low | Low | Graceful skip with warning; file still in inventory by path |
| Over-extraction of plan references (false positives) | Medium | Medium | Conservative regex patterns; only extract from backtick-quoted and code fences initially |
| Under-extraction misses references (false negatives) | Medium | Low | Iterative improvement; start conservative, expand patterns based on real plan analysis |
| Agent prompt too long after Pass G addition | Low | Medium | Keep Pass G instructions concise; reference CLI tool for heavy lifting |
| New-symbol detection too aggressive (masks real errors) | Medium | Medium | Require marker in same sentence/step; configurable marker list |

## 6. Dependencies

### Internal Dependencies

- `agentic_devtools.state._get_git_repo_root()` — for repository root detection
- `agentic_devtools.cli.speckit.validate_frs.validate_frs_command()` — precedent for dedicated `*_command()` CLI entry point in its own module
- `agentic_devtools.cli.speckit.cross_ref.cross_ref_command()` — new dedicated module (not in `commands.py` which is reserved for prompt-rendering wrappers)
- `.github/agents/speckit.analyze.agent.md` — agent prompt to extend
- `.specify/scripts/bash/check-prerequisites.sh` — used by analyze agent for context initialization

### External Dependencies

- **None added** — all implementation uses Python standard library (`ast`, `difflib`, `pathlib`, `re`, `json`, `dataclasses`, `enum`)

### Backward Compatibility

- Existing Passes A–F are not modified
- Existing report format gains an additive section (Pass G)
- No breaking changes to `speckit.analyze` invocation
- New CLI entry point (`agdt-speckit-cross-ref`) is additive

---
*Generated by Copilot SDK (claude-opus-4.6)*
