# Implementation Plan: SpecKit FR Validation Gate

**Source Issue**: [#1199](https://github.com/ayaiayorg/agentic-devtools/issues/1199)

## 1. Technical Context

### Technology Stack

- **Language**: Python 3.10+ (matches `pyproject.toml` `requires-python`)
- **CLI framework**: `argparse` (consistent with other `agdt-*` commands)
- **Regex engine**: Python `re` module (stdlib — no new dependencies)
- **Test workflow**: `agdt-test` / `agdt-test-pattern` commands (repo-standard wrapper around the existing pytest + coverage checks)
- **Pipeline integration**: Bash shell scripts (`.github/scripts/speckit-trigger/`)
- **CI orchestration**: GitHub Actions (`speckit-phase-progression.yml`)

### Key Dependencies

- `agentic_devtools.cli.runner` — `COMMAND_MAP` + `run_as_script` dispatch pattern
- `agentic_devtools.cli.speckit` — existing speckit command module
- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — pipeline orchestration
- `.github/scripts/speckit-trigger/create-spec-pr.sh` — PR creation script
- `.github/workflows/speckit-phase-progression.yml` — GitHub Actions workflow

### Architecture Decisions

1. **Pure Python validation module** — The core validation logic lives in a new
   `agentic_devtools/cli/speckit/validate_frs.py` module, not in bash. This
   enables both CLI usage and reuse as a Python module by other Python code
   (the pipeline bash scripts invoke it via the CLI, not via Python import).

2. **Dual integration path** — The CLI command (`agdt-speckit-validate-frs`)
   serves local developer use, while a thin bash wrapper calls the Python
   command from `generate-spec-from-issue.sh` for pipeline integration.

3. **No new dependencies** — Uses only stdlib `re`, `json`, `argparse`, `pathlib`.

## 2. Research Summary

Key design decisions (derived from spec requirements analysis):

- **FR extraction regex**: `FR-\d+` with case-insensitive matching and first-occurrence canonical form
- **Coverage matching**: Case-insensitive word-boundary regex per FR identifier
- **Sorting algorithm**: Numeric suffix → string length → lexicographic
- **Pipeline insertion point**: At the concrete boundary between `run_tasks_phase` and
  `run_analyze_phase` in `generate-spec-from-issue.sh` (single-phase / `PHASE` path:
  between Phase 4 `tasks` and Phase 5 `analyze`; run-all path: between Phase 5/7
  `tasks` and Phase 6/7 `analyze`)
- **Retry mechanism**: Loop in `generate-spec-from-issue.sh` around
  `run_tasks_phase`, with FR coverage validation immediately before
  `run_analyze_phase`

## 3. Design Overview

### Component Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Python Package (agentic_devtools)                          │
│                                                             │
│  cli/speckit/                                               │
│  ├── validate_frs.py          ← NEW: Core validation logic     │
│  │   ├── extract_frs()        Pure function: spec → FR list    │
│  │   ├── check_coverage()     Pure function: FRs + tasks →     │
│  │   │                        coverage result                  │
│  │   ├── validate_frs()       Orchestrator: spec/tasks content │
│  │   │                        strings → result                 │
│  │   └── validate_frs_command()  CLI/file wrapper: paths →     │
│  │                               file contents → validate_frs()   │
│  ├── commands.py              Existing speckit commands      │
│  └── __init__.py              Updated: exports new command   │
│                                                             │
│  cli/runner.py                Updated: COMMAND_MAP entry     │
├─────────────────────────────────────────────────────────────┤
│  pyproject.toml               Updated: entry point           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Pipeline Scripts (.github/scripts/speckit-trigger/)        │
│                                                             │
│  generate-spec-from-issue.sh  Updated: FR validation gate   │
│  │   ├── run_tasks_phase()    Existing (no changes)         │
│  │   ├── run_fr_validation()  NEW: calls Python CLI         │
│  │   │   └── retry loop       Re-runs tasks on failure      │
│  │   └── run_analyze_phase()  Updated: receives coverage    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Agent Prompt (.github/agents/)                             │
│                                                             │
│  .github/agents/speckit.analyze.agent.md                    │
│                               Updated: inject FR coverage   │
│                               data into analysis context    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```text
spec.md ──→ extract_frs() ──→ ["FR-001", "FR-002", ...]
                                        │
tasks.md ──→ check_coverage() ←─────────┘
                    │
                    ▼
            ValidationResult
            ├── covered: ["FR-001"]
            ├── uncovered: ["FR-002"]
            └── total: 2
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   CLI output              Pipeline gate
   (human/JSON)            (exit code → retry or block)
```

## 4. Implementation Phases

### Phase 1: Core Validation Module (Python)

**Deliverables**: `agentic_devtools/cli/speckit/validate_frs.py` with full test coverage

**Tasks**:

1. **Create `extract_frs(spec_content: str) -> list[str]`**
   - Regex: `FR-\d+` with case-insensitive matching to find all FR identifiers
   - Case-insensitive dedup: first occurrence wins as canonical form
   - Returns deduplicated list preserving document order

2. **Create `check_coverage(fr_ids: list[str], tasks_content: str) -> dict[str, bool]`**
   - For each FR, compile `re.compile(r"\b" + re.escape(fr_id) + r"\b", re.IGNORECASE)`
   - Returns `{fr_id: True/False}` mapping

3. **Create `sort_fr_ids(fr_ids: list[str]) -> list[str]`**
   - Sort by: numeric suffix (ascending) → string length (shorter first) → lexicographic
   - Used for deterministic JSON output

4. **Create `validate_frs(spec_content: str, tasks_content: str) -> ValidationResult`**
   - Orchestrates extraction + coverage check
   - Returns a `ValidationResult` dataclass with fields: `covered`, `uncovered`, `total`, `warning`
   - `passed` is a derived property (not a stored field): returns `True` when `uncovered` is empty
   - Exposes a `to_json()` method returning the standard JSON output dict (used by `--json` flag and pipeline integration)
   - Handles edge cases: no FRs found (warning + pass), empty tasks (all uncovered)

5. **Create `validate_frs_command()` CLI entry point**
   - `argparse` with `--spec-file`, `--tasks-file`, `--json`, `--max-retries`
   - Support FR-008 retry-budget reporting with precedence: `--max-retries` → `SPECKIT_VALIDATE_MAX_RETRIES` → built-in default
   - Clarify that the Python validator itself is single-pass: it validates the provided files once and does not internally retry
   - Make `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` the single source of truth for end-to-end retries:
     it must resolve the retry budget exactly once using that same precedence and store the result in one shell variable
   - Document bash integration explicitly: `generate-spec-from-issue.sh` must use that one resolved value both for loop control
     and when invoking `agdt-speckit-validate-frs` (if the validator needs to echo/report the configured retry budget as metadata)
   - If the script passes `--max-retries` to the validator, that forwarded resolved value wins; otherwise the script may rely on `SPECKIT_VALIDATE_MAX_RETRIES`; otherwise the CLI default applies
   - Human-readable output: banner + coverage table + summary
   - JSON output: `{"covered": [...], "uncovered": [...], "total": N}`
   - Exit code from a single validation pass:
     - `0` = all covered, no FRs found, or missing `spec.md` (warning + pass per EC4)
     - `1` = uncovered FRs exist (including when `tasks.md` is missing/empty but FRs were extracted from `spec.md`)
     - `2` = operational/usage error (for example: invalid CLI arguments from `argparse`, or unexpected runtime exceptions)
   - Clarify in the implementation contract that only `0` and `1` represent normal validation outcomes;
     `2` must be reserved so the pipeline wrapper can distinguish validator errors from uncovered-FR results

### Phase 2: CLI Registration

**Deliverables**: Command registered and callable as `agdt-speckit-validate-frs`

**Tasks**:

1. **Update `pyproject.toml`** — Add entry point:

   ```toml
   agdt-speckit-validate-frs = "agentic_devtools.cli.runner:run_as_script"
   ```

2. **Update `agentic_devtools/cli/runner.py`** — Add `COMMAND_MAP` entry:

   ```python
   "agdt-speckit-validate-frs": (
       "agentic_devtools.cli.speckit",
       "speckit_validate_frs",
   ),
   ```

3. **Update `agentic_devtools/cli/speckit/__init__.py`** — Export new command:
   - Add the import alias for the CLI entry point
   - Update the module's explicit `__all__` list to include `speckit_validate_frs`

   ```python
   from .validate_frs import validate_frs_command as speckit_validate_frs

   __all__ = [
       # ...existing exports...
       "speckit_validate_frs",
   ]
   ```

4. **Reinstall package** — `pip install -e .`

### Phase 3: Pipeline Integration (Bash)

**Deliverables**: FR validation gate in `generate-spec-from-issue.sh` with retry loop

**Tasks**:

1. **Add `run_fr_validation()` function** in `generate-spec-from-issue.sh`:
   - Calls `agdt-speckit-validate-frs --spec-file "$SPEC_DIR/spec.md" --tasks-file "$SPEC_DIR/tasks.md" --json`
   - Captures JSON output and exit code
   - Writes `fr-coverage.json` to `$SPEC_DIR/` for downstream analysis enrichment
   - Returns: 0 = pass, 1 = uncovered FRs, 2 = error
   - Update the script's arg parsing / usage text to accept `--max-retries <n>` in addition to the existing `--phase` option so the shell loop can honor the documented precedence

2. **Add retry loop around tasks phase** at the boundary between
   `run_tasks_phase` and `run_analyze_phase` in `generate-spec-from-issue.sh`
   (single-phase / `PHASE` path: `run_single_phase` case `4`; run-all path:
   the corresponding block after `run_tasks_phase` returns):
   - Resolve a single shell variable once for the script's retry budget with explicit precedence: parsed script arg `--max-retries` > `SPECKIT_VALIDATE_MAX_RETRIES` > default `2`
   - After `run_tasks_phase()` succeeds, run `run_fr_validation()` using that resolved retry budget
   - On failure: extract uncovered FRs from JSON, build retry prompt, re-invoke `run_tasks_phase()` with augmented prompt
   - Drive both loop control and any validator invocation/arguments from that same resolved shell variable so phased behavior cannot diverge by source
   - On resolved retry budget exhausted: exit 1 with clear error listing uncovered FRs

3. **Apply the same retry loop in the monolithic path** in `generate-spec-from-issue.sh`:
   - Update the non-phased code path by finding the block that calls `run_tasks_phase()` and then proceeds toward PR creation
   - Reuse the same script-resolved retry budget shell variable there instead of recomputing it or falling back to an env-var-only path

4. **Integrate with PR creation gate** — After the Phase 3 FR validation retry loop, if validation still fails, skip to error exit (PR is never created)

### Phase 4: Analysis Report Enrichment

**Deliverables**: FR coverage data injected into analysis phase

**Tasks**:

1. **Update `run_analyze_phase()`** in `generate-spec-from-issue.sh`:
   - Read `$SPEC_DIR/fr-coverage.json` if it exists
   - Inject FR coverage summary into the LLM prompt as structured context
   - The LLM includes this data in the analysis-report.md Coverage Summary Table

2. **Update `.github/agents/speckit.analyze.agent.md`**:
   - Add instruction in Step 2 (Load Artifacts): "If `fr-coverage.json` exists in FEATURE_DIR, load it and include deterministic FR coverage data in the Coverage Gaps section"
   - Add note that FR coverage is deterministic (pre-validated) and should be reported as-is

### Phase 5: Tests

**Deliverables**: 100% coverage for `validate_frs.py` following 1:1:1 test structure

**Test structure requirement**: Create the new `tests/unit/cli/speckit/validate_frs/`
hierarchy using the repo's 1:1:1 conventions, and ensure **every directory in that
path includes an `__init__.py`** (for example: `tests/unit/__init__.py`,
`tests/unit/cli/__init__.py`, `tests/unit/cli/speckit/__init__.py`, and
`tests/unit/cli/speckit/validate_frs/__init__.py`, creating any missing ones as
needed). This is enforced by `scripts/validate_test_structure.py`, and missing
`__init__.py` files will fail CI.

**Test files** (under `tests/unit/cli/speckit/validate_frs/`):

| Test File | Symbol Under Test | Key Scenarios |
|-----------|-------------------|---------------|
| `test_extract_frs.py` | `extract_frs` | Basic extraction; case-insensitive dedup (FR-001 vs fr-001, first wins); varying digit counts (FR-1, FR-001); no FRs found; duplicates in same case |
| `test_check_coverage.py` | `check_coverage` | All covered; none covered; partial; case-insensitive match; word-boundary (FR-1 ≠ FR-10); FR in code blocks counts |
| `test_sort_fr_ids.py` | `sort_fr_ids` | Numeric ordering; tie-breaking by length then lexicographic; mixed padding (FR-1 before FR-001) |
| `test_validate_frs.py` | `validate_frs` | Full pass; partial fail; no FRs (warning); empty tasks; empty spec |
| `test_validate_frs_command.py` | `validate_frs_command` | Human output format; `--json` output schema; exit code 0 vs 1; missing/empty `spec.md` warns and passes; missing/empty `tasks.md` fails with uncovered FRs when FRs exist; `--max-retries` with FR-008 precedence resolution |
| `test_validationresult.py` | `ValidationResult` | Dataclass field access; `passed` property; `to_json()` output |

## 5. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| FR identifiers use inconsistent formatting between spec and tasks (e.g., FR-1 vs FR-001) | Validation false negatives | Medium | Spec warns authors to use consistent padding; CLI output shows exact identifiers for debugging |
| Retry prompt doesn't result in LLM covering missing FRs | Pipeline blocks permanently | Low | Max retry limit prevents infinite loops; clear error message guides manual intervention |
| `agdt-speckit-validate-frs` not available in CI runner | Pipeline fails | Low | Python package is installed in CI; if the validator cannot run, fail the pipeline hard with a clear error rather than skipping validation, so missing FR coverage still blocks PR creation (FR-005/FR-006) |
| FR identifiers in markdown headings vs inline text parsed differently | False extraction | Very Low | Regex is format-agnostic (no markdown parsing) — mitigated by design |
| Existing specs without FR identifiers break pipeline | Regression | Medium | Graceful degradation: no FRs found → warning + pass (FR-014) |

## 6. Dependencies

### External Dependencies

- None — all stdlib Python

### Internal Dependencies

| Dependency | Required By | Phase |
|------------|-------------|-------|
| `agentic_devtools.cli.runner` (COMMAND_MAP) | Phase 2 | CLI registration |
| `agentic_devtools/cli/speckit/__init__.py` | Phase 2 | Export |
| `generate-spec-from-issue.sh` | Phase 3 | Pipeline integration |
| `speckit-phase-progression.yml` | Phase 3 | CI workflow (condition update) |
| `.github/agents/speckit.analyze.agent.md` | Phase 4 | Analysis enrichment |
| `pyproject.toml` | Phase 2 | Entry point |

### Blocking Order

```text
Phase 1 (Core module) → Phase 2 (CLI registration) → Phase 3 (Pipeline) → Phase 4 (Analysis)
                    ↘ Phase 5 (Tests) — can start in parallel with Phase 1
```

Phase 5 tests should be written TDD-style alongside Phase 1 (RED → GREEN → REFACTOR).
