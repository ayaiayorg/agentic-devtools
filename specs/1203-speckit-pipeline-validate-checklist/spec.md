# Spec: SpecKit pipeline: Validate checklist files contain actual checkbox items

## Problem Statement

The SpecKit pipeline generates checklist markdown files (e.g., `specs/<issue>/checklists/requirements.md`) as part of AI-assisted specification workflows. Currently, no validation ensures these files
contain actual markdown checkbox items (`- [ ]`, `- [x]`). This means the pipeline can produce and merge checklist artifacts that contain only descriptive prose — or too few actionable items to be
useful — without any warning or failure signal. This gap undermines the reliability of generated artifacts and forces manual inspection to catch deficient outputs. The solution adds a deterministic
checkbox-counting validator that integrates into both CI pipeline and standalone CLI usage, with an optional bounded LLM retry for auto-remediation.

## Overview

Add validation to the SpecKit pipeline so checklist-oriented markdown files are required to contain real markdown
checkbox items rather than only descriptive prose. The validator must distinguish between files with no checklist
items and files with too few checklist items, ignore checkbox-like syntax inside fenced code blocks, report
actionable results, and support both pipeline enforcement and standalone CLI usage. An optional remediation mode
may re-prompt the LLM to regenerate deficient files using a bounded retry strategy.

## Clarifications

### Session 2026-05-04

- Q: Should tilde-delimited fenced code blocks (`~~~`) be treated equivalently to triple-backtick fenced code blocks for exclusion purposes? → A: Yes. Both `~~~` and `` ``` `` fenced code block
  delimiters shall be recognized per the CommonMark specification. Checkbox-like syntax inside either delimiter type is excluded from counting.
- Q: Should indented or nested checkbox items (e.g., `- [ ] sub-item` under a parent list item) count toward the checkbox threshold? → A: Yes. Any line matching the checkbox pattern outside a fenced
  code block counts regardless of leading whitespace or nesting depth.
- Q: Should the minimum checkbox threshold (currently 3) be configurable via CLI flag or environment variable, or remain hardcoded? → A: The threshold shall be configurable via an optional
  `--min-items` CLI flag (default: 3). Pipeline mode uses the default unless explicitly overridden.
- Q: What is the CLI command name and how does it integrate with the existing SpecKit entry points? → A: The validator is exposed as `agdt-speckit-validate-checklists` (a standalone entry point
  following the established `agdt-speckit-*` pattern). In pipeline mode it is invoked automatically as a pipeline stage; in standalone mode users call
  `agdt-speckit-validate-checklists <paths/globs>` directly.
- Q: When LLM re-prompting is enabled and the regenerated file passes on retry, should the validator output indicate that remediation occurred and how many attempts were needed? → A: Yes. The
  validation result for a remediated file shall include a `remediated: true` flag and a `retries_used` count so the pipeline log clearly shows auto-recovery occurred.

## User stories

1. **P1 — Detection:** As a maintainer, I want the pipeline to detect checklist files that contain prose but
   no actual checkbox items so that incomplete generated artifacts are caught automatically.
2. **P1 — Analysis reporting:** As a developer, I want validation output to show which files failed, how many
   checkbox items were found, and why they were classified as deficient so that I can fix them quickly.
3. **P2 — Pipeline blocking:** As a CI owner, I want checklist files with fewer than the configured minimum checkbox items (default 3) to fail
   the pipeline so that obviously unusable checklist outputs do not get merged.
4. **P3 — LLM re-prompting:** As an AI-assisted workflow user, I want the system to optionally re-prompt the
   LLM when a generated checklist is invalid so that recoverable generation failures can be fixed automatically.
5. **P3 — Standalone CLI:** As a local contributor, I want to run the same checklist validation outside CI so that I can verify files before pushing changes.

## User Scenarios & Testing

### Scenario 1: Pipeline catches prose-only checklist during CI

**Actor:** CI pipeline  
**Precondition:** A SpecKit pipeline run has generated `specs/1234/checklists/requirements.md` containing only prose headings and paragraphs with zero checkbox items.  
**Steps:** (1) Pipeline invokes `agdt-speckit-validate-checklists` as a stage. (2) Validator scans `specs/1234/checklists/*.md`. (3) `requirements.md` is classified as prose-only (MEDIUM severity).  
**Expected:** Pipeline fails with a non-zero exit code. Output shows the file path, `checkbox_count: 0`, classification `prose-only`, severity `MEDIUM`, and a remediation hint.

### Scenario 2: Developer validates locally before push

**Actor:** Developer  
**Precondition:** Developer has edited `specs/1234/checklists/requirements.md` locally.  
**Steps:** (1) Developer runs `agdt-speckit-validate-checklists specs/1234/checklists/requirements.md`. (2) File contains 5 real checkbox items.  
**Expected:** CLI exits with code 0. Output shows the file as `valid` with `checkbox_count: 5`.

### Scenario 3: Fenced code block exclusion

**Actor:** CI pipeline  
**Precondition:** Checklist file contains 4 checkbox lines inside a triple-backtick code block and 0 outside it.  
**Steps:** (1) Validator parses file, tracking fenced-block regions using outermost-boundary detection (a line starting with at least three consecutive backticks or tildes opens a
fenced region; only a closing fence of the same character and at least the same length ends it — nested fences are ignored). (2) All 4 checkbox lines are inside the fenced region.  
**Expected:** File is classified as prose-only (`checkbox_count: 0`). Pipeline fails.

### Scenario 4: LLM remediation succeeds on retry

**Actor:** AI-assisted workflow with re-prompting enabled  
**Precondition:** Generated checklist has 0 checkbox items. Re-prompting is enabled (`--retry`).  
**Steps:** (1) Validator detects prose-only file. (2) System re-prompts LLM (attempt 1). (3) Regenerated file now has 5 checkbox items.  
**Expected:** File passes validation. Output includes `remediated: true`, `retries_used: 1`.

### Scenario 5: Multiple files with mixed results

**Actor:** CI pipeline  
**Precondition:** `specs/1234/checklists/` contains `requirements.md` (valid, 6 items), `security.md` (deficient, 2 items), `performance.md` (prose-only, 0 items).  
**Steps:** (1) Validator processes all three files. (2) Aggregate result computed.  
**Expected:** Pipeline fails. Per-file results show `requirements.md` as valid, `security.md` as deficient (LOW), `performance.md` as prose-only (MEDIUM). Aggregate status: `FAIL`.

## Requirements

### Functional Requirements

**FR-001:** In pipeline mode, the system shall validate `specs/<issue>/checklists/requirements.md` by default as the baseline checklist file produced by the SpecKit pipeline.

**FR-002:** In pipeline mode, when additional checklist markdown files exist under `specs/<issue>/checklists/`, the system shall also validate each matching `*.md` file in that directory in the same
run.

**FR-003:** In standalone CLI mode, the validator shall accept one or more explicit file paths and/or glob patterns that resolve to markdown files to validate.

**FR-004:** The validator shall count markdown checkbox items using standard unchecked or checked task-list syntax, including lines beginning with `- [ ]`, `- [x]`, `- [X]`,
`* [ ]`, `* [x]`, or `* [X]`, regardless of leading whitespace or nesting depth.

**FR-005:** The validator shall ignore checkbox-like syntax that appears inside fenced code blocks delimited by at least three consecutive backticks or at least three consecutive
tildes, with the closing fence using the same character and a length greater than or equal to the opening fence, per CommonMark specification.

**FR-006:** The validator shall classify a file with **0** counted checkbox items as **prose-only**.

**FR-007:** The validator shall classify a file with fewer than the configured minimum (default 3) but more than 0 counted checkbox items as **deficient**.

**FR-008:** The validator shall classify a file with checkbox items at or above the configured minimum (default 3) as **valid**.

**FR-009:** The validator shall assign **MEDIUM** severity to prose-only files.

**FR-010:** The validator shall assign **LOW** severity to deficient files.

**FR-011:** The pipeline shall fail when at least one validated file has fewer than the configured minimum counted checkbox items (prose-only or deficient).

**FR-012:** The pipeline shall distinguish prose-only failures (MEDIUM severity) from deficient failures (LOW severity) in its output.

**FR-013:** The validation result shall include, for each file: file path, checkbox count, classification, severity, a human-readable explanation, and (when applicable) `remediated` flag and
`retries_used` count.

**FR-014:** The validator shall support processing multiple files in a single run and shall report aggregate pass/fail status across all processed files.

**FR-015:** The standalone CLI mode shall return a non-zero exit code when blocking validation failures are present and shall treat each resolved file path as an independent validation target.

**FR-016:** The optional LLM re-prompting mode shall be disabled by default and enabled only through explicit configuration or CLI flag (`--retry`).

**FR-017:** When LLM re-prompting is enabled, the system shall retry regeneration at most **2** times per invalid file and shall follow the staged remediation pattern used by sibling spec `#1191`.

**FR-018:** The minimum checkbox threshold shall be configurable via an optional `--min-items` CLI flag (default: 3). Pipeline mode uses the default unless explicitly overridden.

**FR-019:** The validator is exposed as `agdt-speckit-validate-checklists`, a standalone CLI entry point following the established `agdt-speckit-*` naming convention.

**FR-020:** When glob patterns resolve to zero files, the validator shall produce a warning message and exit with code 0 (non-blocking), since no files were validated.

### Non-Functional Requirements

**NFR-001:** Validation shall be deterministic — identical file contents and configuration shall always produce identical results.

**NFR-002:** Validation output shall be concise enough for CI logs (one summary line per file plus an aggregate line) while still providing per-file remediation guidance.

**NFR-003:** The implementation shall minimize false positives by excluding fenced code blocks (delimited by at least three consecutive backticks or at least three
consecutive tildes, per FR-005) from checkbox counting.

**NFR-004:** The validator shall complete processing of up to 20 checklist files in under 2 seconds on standard CI runners (excluding LLM re-prompting time).

**NFR-005:** The standalone CLI and pipeline mode shall use identical counting, classification, and severity rules with no behavioral divergence.

**NFR-006:** The feature shall preserve backward compatibility — valid checklist files that already contain the configured minimum or more real checkbox items shall continue to pass without changes.

## Edge cases

1. A file containing checkbox examples only inside fenced code blocks (`` ``` `` or `~~~`) shall be treated as having 0 checkbox items.
2. A file containing both prose and exactly 1 or 2 real checkbox items outside code fences shall be treated as deficient, not prose-only.
3. A file containing 3 or more real checkbox items outside code fences plus additional checkbox examples inside code fences shall still be treated as valid.
4. Checked items such as `- [x]` or `- [X]` shall count toward the threshold the same as unchecked items.
5. An empty checklist file or whitespace-only file shall be treated as prose-only.
6. When re-prompting is enabled and retries are exhausted, the final reported result shall remain the last validation outcome rather than being silently ignored.
7. A file with nested fenced code blocks (e.g., `` ``` `` inside `~~~` or vice versa) shall treat the outermost delimiter pair as the fenced region boundary; checkbox-like syntax within any fenced
   region is excluded.
8. A file containing only a fenced code block with no other content shall be treated as prose-only (0 checkbox items).
9. Glob patterns that resolve to zero files shall produce a warning but not a blocking failure (exit code 0), since no files were validated.

## Success Criteria

1. 100% of prose-only checklist files in the validation scope are reported as blocking failures with MEDIUM severity.
2. 100% of files with checkbox counts above 0 but below the configured minimum are reported as blocking failures with LOW severity.
3. 100% of checkbox-like lines inside fenced code blocks (both `` ``` `` and `~~~` delimiters) are excluded from the checkbox count.
4. 100% of files with checkbox items at or above the configured minimum outside fenced code blocks pass validation.
5. When enabled, automatic re-prompting performs no more than 2 retries per invalid file and reports remediation metadata on success.
6. Validation output always includes enough information for a user to identify the failing file, understand the classification, and determine the remediation needed.
7. The `--min-items` flag correctly overrides the default threshold in both pipeline and standalone CLI modes.

## Acceptance criteria

1. Given a checklist file with only prose and no checkbox items, when validation runs, then the file is reported as MEDIUM severity and the pipeline fails.
2. Given a checklist file with exactly 1 or 2 real checkbox items, when validation runs, then the file is reported as LOW severity and the pipeline fails.
3. Given a checklist file with 3 or more real checkbox items, when validation runs, then the file passes validation.
4. Given checkbox syntax inside a fenced code block (`` ``` `` or `~~~`), when validation runs, then those lines are excluded from the checkbox count.
5. Given multiple checklist files in one run, when validation completes, then the output includes per-file results and an aggregate outcome.
6. Given re-prompting is disabled, when invalid files are detected, then no automatic regeneration attempts are made.
7. Given re-prompting is enabled, when a file is invalid, then the system attempts remediation using the staged pattern from spec `#1191` and stops after at most 2 retries.
8. Given blocking failures are present, when the standalone CLI exits, then it returns a non-zero exit code.
9. Given `--min-items 5` is passed, when a file contains 4 checkbox items, then the file is classified as deficient and the pipeline fails.
10. Given a remediated file that passes after 1 retry, when validation output is produced, then it includes `remediated: true` and `retries_used: 1`.
11. Given the validator is invoked via the CLI, then it is accessible as `agdt-speckit-validate-checklists` following the established `agdt-speckit-*` entry point pattern.
12. Given pipeline mode runs with no explicit file paths, when the validator executes, then it defaults to validating `specs/<issue>/checklists/requirements.md` plus any other `*.md` files in that directory.
13. Given glob patterns that resolve to zero files, when the validator runs, then it produces a warning and exits with code 0 without reporting a blocking failure.

---

*Generated by Copilot SDK (claude-opus-4.6)*
