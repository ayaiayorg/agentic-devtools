# Implementation Plan: SpecKit Line Wrapper

## 1. Technical Context

- **Stack**: Python 3.10+, pip-installable package (`agentic-devtools`)
- **CLI routing**: All entry points go through `agentic_devtools/cli/runner.py`, entering via `run_as_script` and then dispatching through `COMMAND_MAP`
- **Pipeline**: `generate-spec-from-issue.sh` runs Phases 1–7; Phase 7 is the markdownlint validation/remediation loop (`run_markdownlint_validation`)
- **Markdownlint config**: The SpecKit pipeline runs `markdownlint-cli2`, so `.markdownlint-cli2.jsonc` is the authoritative config
  for pipeline enforcement; it sets `MD013.line_length: 200` with `code_blocks: false` and `tables: false`
- **Test policy**: 1:1:1 test structure under `tests/unit/`, 100% coverage required
- **No new deps**: Core wrapping uses only Python stdlib (per NFR-002)

## 2. Research Summary

Detailed design decisions for this plan:

- **Line wrapping algorithm** → greedy word-wrap with prefix preservation
- **Protected block detection** → regex-based state machine (single pass)
- **Unsplittable token handling** → regex capture for `[text](url)`, `[text][ref]`, and `` `code` ``
- **Pipeline integration point** → new `run_line_wrapping` shell function in `generate-spec-from-issue.sh` that calls
  `wrap_files` via `python -c`, invoked between `quick_markdown_sanity_check` and `run_markdownlint_validation`
- **CLI entry point** → `agdt-speckit-wrap-lines` registered via `pyproject.toml` (follows `agdt-*` namespace)

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────────┐
│              agentic_devtools/markdown/                  │
│  ┌──────────────────┐    ┌───────────────────────────┐  │
│  │  line_wrapper.py  │    │  __init__.py              │  │
│  │                   │    │  (re-exports public API)  │  │
│  │  - wrap_line()    │    └───────────────────────────┘  │
│  │  - wrap_text()    │                                   │
│  │  - wrap_file()    │                                   │
│  │  - wrap_files()   │                                   │
│  │  - detect_        │                                   │
│  │    protected_     │                                   │
│  │    blocks()       │                                   │
│  │  - parse_line_    │                                   │
│  │    context()      │                                   │
│  │  - tokenize()     │                                   │
│  └──────────────────┘                                    │
└─────────────────────────────────────────────────────────┘
               ▲                      ▲
               │                      │
    ┌──────────┴──────────┐    ┌──────┴─────────────────┐
    │  CLI entry point    │    │  Pipeline integration   │
    │  cli/markdown/      │    │  generate-spec-from-    │
    │  commands.py        │    │  issue.sh               │
    │  agdt-speckit-wrap- │    │  (calls Python wrapper) │
    │  lines              │    │                         │
    └─────────────────────┘    └─────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Core Wrapping Module (TDD)

**Deliverable**: `agentic_devtools/markdown/line_wrapper.py` + `__init__.py`

1. Create `agentic_devtools/markdown/__init__.py` to re-export the public wrapping API from `line_wrapper.py`
   (`detect_protected_blocks`, `parse_line_context`, `tokenize`, `wrap_line`, `wrap_text`, `wrap_file`, `wrap_files`)
2. Create `agentic_devtools/markdown/line_wrapper.py` with:
   - `detect_protected_blocks(lines: list[str]) -> list[ProtectedBlock]` — single-pass scanner for code fences, tables, YAML front matter, headings, HTML comments, link definitions
   - `parse_line_context(line: str) -> LineContext` — extract prefix (blockquote markers, list indentation) and content
   - `tokenize(text: str) -> list[str]` — split on whitespace while treating inline code spans (`` `...` ``), links (`[text](url)`, `[text][ref]`), and image links as unsplittable tokens
   - `wrap_line(line: str, max_length: int, prefix: str) -> list[str]` — greedy word-wrap producing continuation lines with correct prefix
   - `wrap_text(text: str, max_length: int = 200) -> str` — full-document wrapper (detect protected blocks, parse context, wrap eligible lines)
   - `wrap_file(path: Path, max_length: int = 200, dry_run: bool = False) -> int` — file-level wrapper returning count of wrapped lines; modifies in-place unless dry_run
   - `wrap_files(paths: list[Path], max_length: int = 200, dry_run: bool = False) -> dict[str, int]` — batch wrapper returning per-file counts

3. Before adding any new test modules under `tests/unit/markdown/line_wrapper/`, create the required package marker files so the 1:1:1 validator passes:
   - `tests/unit/markdown/__init__.py`
   - `tests/unit/markdown/line_wrapper/__init__.py`

**Tests** (TDD — write first):

| Test file | Covers |
|-----------|--------|
| `tests/unit/markdown/line_wrapper/test_detect_protected_blocks.py` | FR-003, FR-004, FR-005, FR-006, FR-016, FR-017 |
| `tests/unit/markdown/line_wrapper/test_parse_line_context.py` | FR-007, FR-008, EC3, EC5 |
| `tests/unit/markdown/line_wrapper/test_tokenize.py` | FR-009, FR-010, FR-018, EC1, EC8 |
| `tests/unit/markdown/line_wrapper/test_wrap_line.py` | FR-002, EC2, EC9 |
| `tests/unit/markdown/line_wrapper/test_wrap_text.py` | FR-001, FR-013, EC6, NFR-004 (idempotency) |
| `tests/unit/markdown/line_wrapper/test_wrap_file.py` | FR-013, FR-019, FR-020, FR-012 |
| `tests/unit/markdown/line_wrapper/test_wrap_files.py` | Batch operation, per-file counts |

### Phase 2: CLI Entry Point

**Deliverable**: `agentic_devtools/cli/markdown/commands.py` + registration

1. Create `agentic_devtools/cli/markdown/__init__.py`
2. Before adding any new test modules under `tests/unit/cli/markdown/commands/`, create the required package marker files so the 1:1:1 validator passes:
   - `tests/unit/cli/markdown/__init__.py`
   - `tests/unit/cli/markdown/commands/__init__.py`
3. Create `agentic_devtools/cli/markdown/commands.py` with:
   - `speckit_wrap_lines(argv: list | None = None) -> None` — argparse-based CLI:
     - Positional: one or more file paths or glob patterns
     - `--line-length` (default: 200)
     - `--dry-run` flag (stdout-only, no file modification)
   - Reports per-file wrapped line counts to stderr
   - Exit code 0 on success
4. Register in `pyproject.toml` `[project.scripts]`:
   - `agdt-speckit-wrap-lines = "agentic_devtools.cli.runner:run_as_script"`
5. Add to `COMMAND_MAP` in `runner.py`:
   - `"agdt-speckit-wrap-lines": ("agentic_devtools.cli.markdown.commands", "speckit_wrap_lines")`
6. Reinstall package (`pip install -e .`)

**Tests**:

| Test file | Covers |
|-----------|--------|
| `tests/unit/cli/markdown/commands/test_speckit_wrap_lines.py` | FR-014, FR-015, FR-019, FR-020, US5 |

### Phase 3: Pipeline Integration

**Deliverable**: Modified `generate-spec-from-issue.sh`

1. Add a `run_line_wrapping` shell function that calls
   `python -c "from agentic_devtools.markdown.line_wrapper import wrap_files; ..."` on all `.md` files in `$SPEC_DIR`,
   and ensure the invocation runs with `$REPO_ROOT` on Python's import path
   (preferably by running from `"$REPO_ROOT"` or by setting `PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"` inside the function)
2. Define `run_line_wrapping` within the existing `generate-spec-from-issue.sh` section extracted by
   `test_markdownlint_validation.sh` (between the "Markdownlint Validation" and "Phase Functions" markers),
   so the current harness can source and exercise it without modification
3. Insert `run_line_wrapping "$SPEC_DIR"` call between `quick_markdown_sanity_check` and `run_markdownlint_validation` in:
   - Each per-phase block (phases 1–5, single-phase mode)
   - The full-pipeline block (phase 7/7)
4. Log output: `[Line Wrap] Wrapped N lines across M files`
5. The function is best-effort (returns 0 always) — markdownlint validation remains the gate

**Tests**: Shell function tested via the existing `test_markdownlint_validation.sh` harness because it is defined
inside the harness-extracted Markdownlint Validation section, plus a new dedicated test for wrapping-specific behavior.

### Phase 4: Validation & Documentation

1. Run full test suite (`agdt-test`) — verify 100% coverage
2. Run `bash scripts/run-pr-checks.sh` — verify all CI checks pass
3. Run wrapping against existing spec files in `specs/` to validate real-world behavior
4. Update `copilot-instructions.md` to document the new `agdt-speckit-wrap-lines` command

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Wrapping breaks markdown semantics (e.g., splits inline code) | High | Low | Unsplittable token regex + comprehensive edge case tests |
| Protected block detection misses edge cases (nested fences, indented fences) | Medium | Medium | Test with real-world spec files; conservative approach (leave unrecognized patterns unwrapped) |
| Pipeline integration fails silently | Medium | Low | Best-effort pattern with logging; markdownlint remains as safety net |
| Performance regression on large spec dirs | Low | Low | NFR-001 targets <5s; pure Python string ops are fast for 50KB |
| CLI naming conflict | Low | Low | Uses `agdt-speckit-wrap-lines` following repo `agdt-*` convention |

## 6. Dependencies

### Internal

- `agentic_devtools/cli/runner.py` — COMMAND_MAP registration
- `pyproject.toml` — entry point registration
- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — Phase 7 integration
- `scripts/validate_test_structure.py` — must pass with new test directories

### External

- None (stdlib only per NFR-002)

---
*Generated by Copilot SDK (claude-opus-4.6)*
