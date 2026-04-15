# Tasks: SpecKit Line Wrapper

## Phase 1: Setup

- [ ] T001 Create `agentic_devtools/markdown/__init__.py` package marker file
- [ ] T002 Create `agentic_devtools/markdown/line_wrapper.py` module stub with module docstring
- [ ] T003 [P] Create `agentic_devtools/cli/markdown/__init__.py` package marker file
- [ ] T004 [P] Create `tests/unit/markdown/__init__.py` and `tests/unit/markdown/line_wrapper/__init__.py` test package markers
- [ ] T005 [P] Create `tests/unit/cli/markdown/__init__.py` and `tests/unit/cli/markdown/commands/__init__.py` test package markers
- [ ] T006 Run `python scripts/validate_test_structure.py` to confirm scaffolding passes

## Phase 2: Foundational

- [ ] T007 Define `ProtectedBlock` and `LineContext` dataclasses in `agentic_devtools/markdown/line_wrapper.py`
- [ ] T008 Add public API re-exports (`detect_protected_blocks`, `parse_line_context`, `tokenize`, `wrap_line`, `wrap_text`, `wrap_file`, `wrap_files`) in `agentic_devtools/markdown/__init__.py`

## Phase 3: US2 — Preserve Protected Block Structure (P1)

- [ ] T009 [US2] Write tests for `detect_protected_blocks` covering code fences (FR-003), tables (FR-004), YAML front matter (FR-005),
      headings (FR-006), HTML comments (FR-017), reference-style link definitions (FR-016), and adjacent protected blocks (EC6)
      in `tests/unit/markdown/line_wrapper/test_detect_protected_blocks.py`
- [ ] T010 [US2] Implement `detect_protected_blocks(lines: list[str]) -> list[ProtectedBlock]` single-pass state-machine scanner in `agentic_devtools/markdown/line_wrapper.py` (depends: T007, T009)

## Phase 4: US1 — Wrap Long Lines in Generated Markdown (P1)

- [ ] T011 [P] [US1] Write tests for `parse_line_context` covering plain lines, list indentation preservation (FR-007),
      blockquote prefix preservation (FR-008), nested blockquotes (EC3), and mixed list+blockquote contexts (EC5)
      in `tests/unit/markdown/line_wrapper/test_parse_line_context.py`
- [ ] T012 [P] [US1] Write tests for `tokenize` covering whitespace splitting (FR-002), inline code span preservation (FR-010),
      link preservation (FR-009), image link preservation, hyphenated term integrity (EC8), and formatting span splitting (FR-018)
      in `tests/unit/markdown/line_wrapper/test_tokenize.py`
- [ ] T013 [US1] Implement `parse_line_context(line: str) -> LineContext` in `agentic_devtools/markdown/line_wrapper.py` (depends: T007, T011)
- [ ] T014 [US1] Implement `tokenize(text: str) -> list[str]` with regex-based unsplittable token detection in `agentic_devtools/markdown/line_wrapper.py` (depends: T012)
- [ ] T015 [US1] Write tests for `wrap_line` covering basic wrapping at word boundaries (FR-002), single long word passthrough (EC2),
      long URL passthrough (EC1), and inline formatting across long lines (EC9) in `tests/unit/markdown/line_wrapper/test_wrap_line.py`
- [ ] T016 [US1] Implement `wrap_line(line: str, max_length: int, prefix: str) -> list[str]` greedy word-wrap in `agentic_devtools/markdown/line_wrapper.py` (depends: T014, T015)
- [ ] T017 [US1] Write tests for `wrap_text` covering full-document wrapping (FR-001), protected block skipping, skip-unmodified files (FR-013), and idempotency (NFR-004) in `tests/unit/markdown/line_wrapper/test_wrap_text.py`
- [ ] T018 [US1] Implement `wrap_text(text: str, max_length: int = 200) -> str` integrating `detect_protected_blocks`, `parse_line_context`,
      and `wrap_line` in `agentic_devtools/markdown/line_wrapper.py` (depends: T010, T013, T016, T017)
- [ ] T019 [US1] Write tests for `wrap_file` covering in-place modification (FR-019), dry-run stdout output (FR-020),
      skip when no lines exceed limit (FR-013), and wrapped line count return (FR-012) in `tests/unit/markdown/line_wrapper/test_wrap_file.py`
- [ ] T020 [US1] Implement `wrap_file(path: Path, max_length: int = 200, dry_run: bool = False) -> int` in `agentic_devtools/markdown/line_wrapper.py` (depends: T018, T019)
- [ ] T021 [US1] Write tests for `wrap_files` covering batch operation across multiple files and per-file count dict return in `tests/unit/markdown/line_wrapper/test_wrap_files.py`
- [ ] T022 [US1] Implement `wrap_files(paths: list[Path], max_length: int = 200, dry_run: bool = False) -> dict[str, int]` in `agentic_devtools/markdown/line_wrapper.py` (depends: T020, T021)

## Phase 5: US3 — Integrate Wrapping into SpecKit Pipeline (P2)

- [ ] T023 [US3] Add `run_line_wrapping` shell function in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
      between the Markdownlint Validation and Phase Functions sections, calling `wrap_files` via `python -c`
      with PYTHONPATH set to `$REPO_ROOT` (depends: T022)
- [ ] T024 [US3] Add `[Line Wrap]` prefixed logging for file count and wrapped line count in `run_line_wrapping` (FR-012)
- [ ] T025 [US3] Insert `run_line_wrapping "$SPEC_DIR"` call between `quick_markdown_sanity_check` and `run_markdownlint_validation`
      in all 5 per-phase blocks (phases 1–5) in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (depends: T023)
- [ ] T026 [US3] Insert `run_line_wrapping "$SPEC_DIR"` call between `quick_markdown_sanity_check` and `run_markdownlint_validation`
      in the full-pipeline block (Phase 7/7) in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (depends: T023)

## Phase 6: US4 — Reduce LLM Remediation Iterations (P2)

- [ ] T027 [US4] Verify wrapping reduces MD013 violations by ≥90% by running wrapper on sample spec files from `specs/` and comparing violation counts (depends: T022)
- [ ] T028 [US4] Confirm files that previously required LLM remediation for line length now pass markdownlint after wrapping alone (depends: T025, T026)

## Phase 7: US5 — Standalone CLI for Ad-Hoc Wrapping (P3)

- [ ] T029 [US5] Write tests for `speckit_wrap_lines` CLI covering file path args (FR-015), `--line-length` flag (FR-014),
      `--dry-run` flag (FR-020), in-place modification (FR-019), per-file report output, and exit codes
      in `tests/unit/cli/markdown/commands/test_speckit_wrap_lines.py`
- [ ] T030 [US5] Implement `speckit_wrap_lines(argv: list | None = None) -> None` with argparse in `agentic_devtools/cli/markdown/commands.py` (depends: T022, T029)
- [ ] T031 [P] [US5] Register `agdt-speckit-wrap-lines = "agentic_devtools.cli.runner:run_as_script"` entry point in `pyproject.toml` `[project.scripts]` (depends: T030)
- [ ] T032 [P] [US5] Add `"agdt-speckit-wrap-lines": ("agentic_devtools.cli.markdown.commands", "speckit_wrap_lines")` to `COMMAND_MAP` in `agentic_devtools/cli/runner.py` (depends: T030)
- [ ] T033 [US5] Reinstall package (`pip install -e .`) and verify `agdt-speckit-wrap-lines --help` works (depends: T031, T032)

## Phase 8: Polish & Cross-Cutting

- [ ] T034 Finalize public API re-exports in `agentic_devtools/markdown/__init__.py` to match implemented symbols
- [ ] T035 Run full test suite (`agdt-test`) and verify 100% coverage for `agentic_devtools/markdown/line_wrapper.py`
- [ ] T036 Run `bash scripts/run-pr-checks.sh` to verify all CI checks pass (lint, format, mypy, markdownlint)
- [ ] T037 Test wrapping against real spec files in `specs/` directory to validate real-world behavior and idempotency
- [ ] T038 Update `copilot-instructions.md` to document the `agdt-speckit-wrap-lines` command and wrapping pipeline step

---
*Generated by Copilot SDK (claude-opus-4.6)*
