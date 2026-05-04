# Implementation Plan: `agdt-speckit-validate-checklists`

## 1. Technical Context

- **Language/Runtime**: Python 3.10+ (project uses `from __future__ import annotations`)
- **Package**: `agentic_devtools` — pip-installable CLI toolkit
- **CLI pattern**: `argparse`-based entry points dispatched through `runner.py:COMMAND_MAP` → `run_as_script()`
- **Reference implementation**: `validate_frs.py` — the closest architectural sibling (validation CLI with dataclasses, exit codes 0/1/2, `--json` output, `--max-retries` metadata)
- **Test convention**: 1:1:1 under `tests/unit/cli/speckit/validate_checklists/test_<symbol>.py`
- **All speckit commands run synchronously** (no background tasks)

## 2. Research Summary

Key decisions (from research phase — research artifacts are gitignored and not committed):

| Decision | Choice |
|----------|--------|
| Fenced code block parser | Custom state-machine (CommonMark outermost-boundary rules) — no external dependency |
| Module location | `agentic_devtools/cli/speckit/validate_checklists.py` (single new module) |
| Retry/remediation | Bounded retry loop (max 2 attempts per invalid file) following the staged remediation pattern from spec #1191 — enabled via `--retry` flag |
| Output modes | Human-readable (default) + `--json` structured output |

## 3. Design Overview

```text
┌─────────────────────────────────────────────┐
│       validate_checklists_command()          │  CLI entry point (argparse)
│  --min-items, --json, --retry, [paths/globs]│  paths optional (pipeline default)
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│       validate_checklists()                  │  Orchestrator: resolves files,
│  paths → list[FileResult] + AggregateResult │  runs per-file validation,
└──────────────┬──────────────────────────────┘  computes aggregate
               │
               ▼
┌─────────────────────────────────────────────┐
│       count_checkboxes()                     │  Pure function: parse markdown,
│  content: str → int                          │  exclude fenced blocks, count
└─────────────────────────────────────────────┘  checkbox lines

┌─────────────────────────────────────────────┐
│       classify_file()                        │  Pure function: count → classification
│  count, min_items → FileClassification       │  (valid / deficient / prose-only)
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│       remediate_file()                       │  Retry loop: re-prompts LLM up to
│  path, max_retries → RemediationResult       │  2 times per invalid file (#1191)
└─────────────────────────────────────────────┘
```

### Data flow

1. CLI parses args → resolves paths (explicit or pipeline-mode default via glob `{base_path}/<issue>-*/checklists/*.md` where `base_path` comes from `SPEC_BASE_PATH` env var or defaults to `specs`)
2. For each file: read → `count_checkboxes()` → `classify_file()` → `FileResult`
3. If `--retry` enabled and file is invalid: `remediate_file()` → re-prompts LLM up to 2 times → re-validate
4. Aggregate all `FileResult`s → `AggregateResult` (pass/fail)
5. Output human-readable or JSON → exit code 0 (pass) or 1 (fail)

## 4. Implementation Phases

### Phase 1: Core Validation Logic (TDD — pure functions)

**Deliverable**: `agentic_devtools/cli/speckit/validate_checklists.py` with pure functions and dataclasses.

#### Todo 1.1 — Data types

Define enums and dataclasses: `FileClassification` (enum: `valid`, `deficient`, `prose_only`), `Severity` (enum: `LOW`, `MEDIUM`, `NONE`), `FileResult` (including `explanation: str` per FR-013),
`AggregateResult`.

#### Todo 1.2 — `count_checkboxes(content: str) -> int`

State-machine parser that:

- Tracks fenced code block regions (backtick ```` ``` ```` and tilde `~~~`, CommonMark outermost-boundary rules with fence length matching)
- Counts lines matching `^\s*[-*] \[([ xX])\]` outside fenced regions
- Returns integer count

#### Todo 1.3 — `classify_file(checkbox_count: int, min_items: int) -> tuple[FileClassification, Severity]`

Pure classification:

- 0 → `prose_only`, `MEDIUM`
- 1..min_items-1 → `deficient`, `LOW`
- ≥min_items → `valid`, `NONE`

#### Todo 1.4 — `validate_file(path: str, min_items: int) -> FileResult`

Reads file, calls `count_checkboxes` + `classify_file`, builds `FileResult`.

#### Todo 1.5 — `validate_checklists(paths: list[str], min_items: int, *, retry: bool = False, max_retries: int = 2) -> AggregateResult`

Orchestrates multi-file validation, computes aggregate pass/fail.
The `retry` and `max_retries` parameters are threaded through to the remediation loop (Phase 3) so the orchestrator signature is complete from the start.

### Phase 2: CLI Entry Point

**Deliverable**: Working `agdt-speckit-validate-checklists` command.

#### Todo 2.1 — `validate_checklists_command(argv: list[str] | None = None) -> None`

Argparse CLI with:

- Optional positional `paths` (zero or more files/globs; when omitted, defaults to pipeline-mode:
  `{base_path}/<issue>-*/checklists/*.md` where `{base_path}` defaults to `specs` but
  is overridden by the `SPEC_BASE_PATH` environment variable (matching the existing
  SpecKit pipeline convention in `generate-spec-from-issue.sh` and workflows).
  The issue number is resolved via this priority:
  1. `--issue-number` CLI argument (explicit override — highest priority, consistent with
     `validate_frs.py` which also resolves CLI configuration before environment values)
  2. `ISSUE_NUMBER` environment variable (set by GitHub Actions via `generate-spec-from-issue.sh`) →
     globs `{base_path}/${ISSUE_NUMBER}-*/checklists/*.md` to find the existing spec directory
     (handles title renames where the original directory is reused)
  3. `issue_key` state key — **only if the value is purely numeric** (e.g., `42`, `1203`).
     Non-numeric values (e.g., Jira keys like `PROJECT-1234`) are skipped because SpecKit
     directories are named from the numeric GitHub issue number (`<issue_number>-<short_name>`),
     not from provider-specific identifiers
  Note: `jira.issue_key` and workflow context `jira_issue_key` are **not** used as fallbacks
  because they always contain Jira-formatted keys (e.g., `PROJECT-1234`) which would produce
  invalid glob paths like `{base_path}/PROJECT-1234-*/checklists/*.md`.
  This ensures the validator works in CI (where env vars are set) and locally (where agdt state is available).
  The glob-based approach mirrors `generate-spec-from-issue.sh` which reuses existing `specs/${ISSUE_NUMBER}-*`
  directories even when an issue title change produces a new `SHORT_NAME`.
  The priority order is tailored to this feature's requirement for numeric GitHub issue numbers,
  intentionally diverging from the general agdt issue-resolution convention which includes
  Jira-specific keys that are incompatible with SpecKit directory naming.)
- `--issue-number` (int, optional — explicit numeric GitHub issue number; highest priority
  for issue resolution, overriding both `ISSUE_NUMBER` env var and `issue_key` state key)
- `--min-items` (int, default 3)
- `--json` (structured output)
- `--retry` (enables bounded LLM re-prompting — max 2 retries per invalid file, following staged remediation pattern from spec #1191)
- Exit codes: 0 (pass), 1 (fail — includes validation failures AND path-resolution
  errors such as multi-directory collision or failed 3-digit safety check, matching
  the generator's exit code 1 for the same conditions), 2 (I/O error — file read
  failures, permission errors)

#### Todo 2.2 — `_resolve_paths(patterns: list[str]) -> list[str]`

Glob resolution helper:

- Expands each pattern via `glob.glob()`, deduplicates, and sorts results
- **Multi-directory collision detection**: when pipeline-mode glob `{base_path}/<issue>-*/checklists/*.md`
  matches files across multiple spec directories for the same issue number, the function
  raises a `SystemExit(1)` with a descriptive error (matching the generator's collision-abort
  behavior in `generate-spec-from-issue.sh` which also exits with code 1)
- **3-digit issue number safety check** (FR-015 parity): for issue numbers 100–999, the
  `<issue>-*` prefix overlaps the legacy `^[0-9]{3}-` numbering namespace. After glob
  resolution, `_resolve_paths()` verifies that the matched spec directory contains a
  `**Source Issue**` marker referencing `#<issue_number>` (checked in
  `checklists/requirements.md` or `spec.md`). If the marker is missing, the function
  exits with code 1 and a message indicating a possible legacy directory mismatch —
  mirroring the identical guard in `generate-spec-from-issue.sh`
- **Explicit path validation**: when a pattern does not contain glob metacharacters
  (`*`, `?`, `[`), it is treated as an explicit file path. If the file does not exist,
  `_resolve_paths()` raises `SystemExit(1)` with an error message identifying the
  missing path — preventing silent success on typos.
- **Glob zero-match warning** (FR-020): when a glob pattern resolves to zero files,
  emit a warning to stderr but continue with exit code 0 (non-blocking). This
  distinction ensures that FR-020's permissive behavior only applies to glob
  patterns, not explicit paths.

#### Todo 2.3 — Output formatting

- `_print_human_output()` — per-file summary with human-readable explanation + aggregate line
- JSON mode — `AggregateResult.to_json()` (includes per-file `explanation` field per FR-013)

Each `FileResult` must include an `explanation: str` field providing a human-readable
description of the validation outcome (e.g., "File contains 5 checkbox items (≥3 required) — valid"
or "File contains 0 checkbox items — prose-only, requires checklist formatting").
This field is mandatory in both human and JSON output modes.

### Phase 3: LLM Remediation Loop (FR-017)

**Deliverable**: Bounded retry logic that re-prompts the LLM when `--retry` is enabled.

#### Todo 3.0 — Prompt persistence prerequisite

The pipeline must persist the original generation prompt alongside the checklist output so
`remediate_file()` can access it during retries. Implementation:

- After `call_llm` produces a checklist, save the generation prompt as a sidecar file
  in the **same directory** as the checklist output:
  `.generation-prompt-{stem}.md` where `{stem}` is the checklist filename without
  extension (e.g., for `requirements.md` → `.generation-prompt-requirements.md`).
  This is a gitignored artifact — requires adding gitignore rules that cover both
  the default and overridden base paths:
  `specs/*/checklists/.generation-prompt-*.md` (default base path) and
  `**/checklists/.generation-prompt-*.md` (catches any `SPEC_BASE_PATH` override).
- `remediate_file()` discovers the sidecar prompt **relative to the checklist file's
  parent directory** (i.e., `Path(checklist_path).parent / f".generation-prompt-{stem}.md"`
  where `stem = Path(checklist_path).stem`),
  which works correctly regardless of directory renames since the validator already
  resolved the real directory via glob
- If the sidecar prompt file is missing (e.g., manually-created checklists), remediation
  uses a generic fallback prompt that includes the validation failure details and explicit
  checkbox formatting instructions

#### Todo 3.1 — `remediate_file(path: str, min_items: int, max_retries: int = 2) -> RemediationResult`

Implements the staged remediation pattern from spec #1191:

- Stage 1 (retry 1): Re-prompt with the persisted generation prompt (from Todo 3.0) plus the validation failure details
- Stage 2 (retry 2): Re-prompt with additional constraints (explicit checkbox formatting instructions)
- After each retry: re-read file → `count_checkboxes()` → `classify_file()` → stop if valid
- Returns `RemediationResult` with `remediated: bool`, `retries_used: int`, final `FileResult`

**Runtime requirements**: `remediate_file()` invokes the LLM through the SpecKit
pipeline's `call_llm` and `call_with_retry` helpers, which provide exponential-backoff
retry behavior for transient SDK failures.

**Implementation constraint**: `generate-spec-from-issue.sh` executes argument
parsing, environment validation, directory resolution, and phase execution at
top level with no source-safe guard — sourcing it would run the entire generator.
Therefore the shared helpers (`call_llm`, `call_with_retry`, `generate_with_copilot`)
must first be extracted into a dedicated sourceable library script
(e.g., `pipelines/lib/speckit-helpers.sh`) that defines functions without
executing any top-level logic. This extraction is a prerequisite for Todo 3.1.

Concretely, `remediate_file()` shells out via `subprocess.run()` to a thin bash
wrapper script that sources the extracted helper library and calls `call_llm`
with the remediation prompt. This avoids both:

- calling `copilot_generate.py` directly (which would bypass `call_with_retry`)
- sourcing `generate-spec-from-issue.sh` (which would execute the full pipeline)

This requires `COPILOT_GITHUB_TOKEN` at runtime (provided in CI via
`secrets.COPILOT_GITHUB_TOKEN`, which is the dedicated Copilot SDK token;
the app token from `actions/create-github-app-token` is reserved for GitHub API
calls such as requesting reviews, NOT for LLM invocations).
This dependency is only activated when `--retry` is passed.

#### Todo 3.2 — Integrate retry into `validate_checklists()` orchestrator

When `retry=True`:

- After initial classification, if file is invalid → call `remediate_file()`
- Update the `FileResult` with remediation metadata (`remediated`, `retries_used`)
- If remediation exhausted (still invalid after 2 retries) → report final state as the result

### Phase 4: Wiring & Registration

**Deliverable**: Command is callable via `agdt-speckit-validate-checklists`.

#### Todo 4.1 — Export from `__init__.py`

Add `speckit_validate_checklists` alias in `agentic_devtools/cli/speckit/__init__.py`.

#### Todo 4.2 — Register in `runner.py` COMMAND_MAP

Add `"agdt-speckit-validate-checklists"` → `("agentic_devtools.cli.speckit", "speckit_validate_checklists")`.

#### Todo 4.3 — Register entry point in `pyproject.toml`

Add `agdt-speckit-validate-checklists = "agentic_devtools.cli.runner:run_as_script"`.

#### Todo 4.4 — Reinstall and smoke test

`pip install -e .` and verify CLI is callable.

### Phase 5: Pipeline Integration (FR-001, FR-002, FR-011)

**Deliverable**: Validator is wired into the SpecKit pipeline (`generate-spec-from-issue.sh` or equivalent orchestration) so it runs automatically during CI.

#### Todo 5.1 — Pipeline stage invocation

Add `agdt-speckit-validate-checklists` as a pipeline stage in the SpecKit orchestration (after checklist generation, before completion).
In pipeline mode (no explicit paths), the validator uses the same glob-based discovery
defined in Todo 2.1 (`{base_path}/<issue>-*/checklists/*.md`, where `base_path` is
`SPEC_BASE_PATH` or defaults to `specs`), which correctly handles
directory reuse after issue title renames.

#### Todo 5.2 — Pipeline failure handling

The pipeline stage treats both non-zero exit codes as failures:

- **Exit code 1** (validation failure or path-resolution error): The stage fails and reports
  the structured output. When `--retry` is enabled in pipeline mode, remediation is attempted
  before reporting final failure.
- **Exit code 2** (I/O/operational error — file read failures, permission errors): The stage
  fails immediately with an operational error diagnostic. No remediation is attempted since
  the failure is not related to checklist content. This matches the sibling FR-validation
  stage in `generate-spec-from-issue.sh` which also treats exit code 2 as a hard failure.

#### Todo 5.3 — Integration test

Verify end-to-end that the pipeline invokes the validator and correctly propagates pass/fail status.

### Phase 6: Tests (1:1:1 structure)

**Deliverable**: Full test coverage under `tests/unit/cli/speckit/validate_checklists/`.

#### Todo 6.1 — `test_count_checkboxes.py`

- Basic checkbox counting (unchecked, checked, mixed)
- Indented/nested checkboxes
- Backtick fenced code block exclusion
- Tilde fenced code block exclusion
- Nested fenced blocks (outermost boundary)
- Mixed content (checkboxes inside + outside fences)
- Empty/whitespace-only content
- `*` list markers

#### Todo 6.2 — `test_classify_file.py`

- prose_only (count=0)
- deficient (count=1, count=2 with default min 3)
- valid (count=3, count=10)
- Custom min_items threshold

#### Todo 6.3 — `test_validate_file.py`

- Valid file, deficient file, prose-only file
- File not found handling
- Unicode/encoding edge cases

#### Todo 6.4 — `test_validate_checklists.py`

- Single file pass, single file fail
- Multiple files mixed results
- Empty file list (warning, pass)

#### Todo 6.5 — `test_validate_checklists_command.py`

- Basic invocation with valid files
- `--min-items` override
- `--json` output mode
- Non-zero exit on failure
- Exit code 0 on all pass
- Glob resolution to zero files (warning, exit 0)
- `--retry` triggers remediation for invalid files
- Pipeline-mode default path resolution (no explicit paths)

#### Todo 6.6 — `test__resolve_paths.py`

- Single file path (exists → included in results)
- Explicit file path that does not exist → `SystemExit(1)`
- Glob pattern expansion
- Glob zero-match warning (non-blocking, exit 0)
- Deduplication
- **Multi-directory collision abort**: glob matches files across two or more spec
  directories for the same issue number → `SystemExit(1)` with descriptive error
- **3-digit Source Issue marker guard**: issue number 100–999, matched directory
  missing `**Source Issue**` marker → `SystemExit(1)`
- **3-digit marker present**: issue number 100–999 with valid `**Source Issue**`
  marker → passes without error
- **Non-default `SPEC_BASE_PATH`**: when `SPEC_BASE_PATH` env var overrides the
  default `specs/` base directory, pipeline-mode glob resolves files under the
  custom path (e.g., `custom/path/<issue>-*/checklists/*.md`) — ensures a
  hard-coded `specs/` implementation would be caught by this test

#### Todo 6.7 — `test_remediate_file.py`

- Successful remediation on first retry
- Successful remediation on second retry
- Failed remediation (exhausted 2 retries, still invalid)
- Remediation disabled (--retry not passed)
- `remediated` and `retries_used` metadata in output

### Phase 7: PR Checks & Documentation

#### Todo 7.1 — Run `bash scripts/run-pr-checks.sh`

Verify all CI-blocking checks pass.

#### Todo 7.2 — Update copilot-instructions.md

Add the new command to the SpecKit CLI commands section.

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CommonMark fenced block edge cases (info strings, lazy continuation) | Checkbox miscounting | Low | Implement strict outermost-boundary detection; comprehensive test cases |
| Glob expansion behaves differently on Windows vs Unix | Path resolution bugs | Low | Use `pathlib.Path.glob()` or `glob.glob()` — standard library |
| LLM retry prompt engineering | Remediation may still produce invalid output | Medium | Cap at 2 retries, report final state regardless; follow staged remediation pattern from spec #1191 |
| Pipeline integration breaks existing stages | CI failures | Low | Add as a new stage after generation; validate in isolation before wiring |
| New module breaks existing imports | Import errors | Very low | Module is additive, no changes to existing code |

## 6. Dependencies

- **Internal**: `agentic_devtools.cli.runner` (COMMAND_MAP registration), `agentic_devtools.cli.speckit.__init__` (export),
  SpecKit pipeline orchestration (`generate-spec-from-issue.sh` or equivalent stage runner)
- **External (core validation)**: None — pure Python standard library only (`re`, `argparse`, `glob`, `json`, `dataclasses`, `enum`, `os`)
- **External (remediation only — activated by `--retry`)**: SpecKit pipeline's `call_llm` bash helper
  (extracted into `pipelines/lib/speckit-helpers.sh` as described in Todo 3.1 — NOT sourced from
  `generate-spec-from-issue.sh` directly, since that would execute the entire generator).
  Wraps Copilot SDK calls with `call_with_retry` backoff. Invoked via a thin bash wrapper script
  through `subprocess.run()`. Requires `COPILOT_GITHUB_TOKEN` environment variable (provided by
  the GitHub Actions workflow via `secrets.COPILOT_GITHUB_TOKEN` — the dedicated Copilot SDK token;
  the app token from `actions/create-github-app-token` is reserved for GitHub API calls).
  This dependency is subprocess-only when `--retry` is passed, so the core validator remains dependency-free.
- **Environment variables consumed**:
  - `SPEC_BASE_PATH` — overrides the default base directory (`specs`) for spec discovery (matching the existing SpecKit pipeline convention)
  - `ISSUE_NUMBER` — used for pipeline-mode path resolution via glob `{base_path}/${ISSUE_NUMBER}-*/checklists/*.md` (set by `generate-spec-from-issue.sh`)
  - `SHORT_NAME` — set by the pipeline on every phase but NOT used for path resolution (the validator uses glob-based discovery to handle title renames); available for diagnostic/logging output only
  - `COPILOT_GITHUB_TOKEN` — required only when `--retry` is enabled
- **Spec dependencies**: Spec #1191 (staged remediation pattern — referenced by FR-017 retry implementation)
- **CI**: `scripts/run-pr-checks.sh` (existing), `scripts/validate_test_structure.py` (existing)

---
*Generated by Copilot SDK (claude-opus-4.6)*
