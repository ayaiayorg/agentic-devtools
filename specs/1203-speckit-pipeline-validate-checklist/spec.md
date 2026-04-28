# Spec: SpecKit pipeline: Validate checklist files contain actual checkbox items

## Overview

Add validation to the SpecKit pipeline so checklist-oriented markdown files are required to contain real markdown
checkbox items rather than only descriptive prose. The validator must distinguish between files with no checklist
items and files with too few checklist items, ignore checkbox-like syntax inside fenced code blocks, report
actionable results, and support both pipeline enforcement and standalone CLI usage. An optional remediation mode
may re-prompt the LLM to regenerate deficient files using a bounded retry strategy.

## User stories

1. **P1 — Detection:** As a maintainer, I want the pipeline to detect checklist files that contain prose but
   no actual checkbox items so that incomplete generated artifacts are caught automatically.
2. **P1 — Analysis reporting:** As a developer, I want validation output to show which files failed, how many
   checkbox items were found, and why they were classified as deficient so that I can fix them quickly.
3. **P2 — Pipeline blocking:** As a CI owner, I want checklist files with fewer than 3 checkbox items to fail
   the pipeline so that obviously unusable checklist outputs do not get merged.
4. **P3 — LLM re-prompting:** As an AI-assisted workflow user, I want the system to optionally re-prompt the
   LLM when a generated checklist is invalid so that recoverable generation failures can be fixed automatically.
5. **P3 — Standalone CLI:** As a local contributor, I want to run the same checklist validation outside CI so that I can verify files before pushing changes.

## Functional requirements

1. In pipeline mode, the system shall validate `specs/<issue>/checklists/requirements.md` by default as the baseline checklist file produced by the SpecKit pipeline.
2. In pipeline mode, when additional checklist markdown files exist under `specs/<issue>/checklists/`, the system shall also validate each matching `*.md` file in that directory in the same run.
3. In standalone CLI mode, the validator shall accept one or more explicit file paths and/or glob patterns that resolve to markdown files to validate.
4. The validator shall count markdown checkbox items using standard unchecked or checked task-list syntax, including lines beginning with `- [ ]`, `- [x]`, `- [X]`, `* [ ]`, `* [x]`, or `* [X]`.
5. The validator shall ignore checkbox-like syntax that appears inside fenced code blocks delimited by triple backticks.
6. The validator shall classify a file with **0** counted checkbox items as **prose-only**.
7. The validator shall classify a file with **1 or 2** counted checkbox items as **deficient**.
8. The validator shall classify a file with **3 or more** counted checkbox items as **valid**.
9. The validator shall assign **MEDIUM** severity to prose-only files.
10. The validator shall assign **LOW** severity to deficient files containing 1 or 2 checkbox items.
11. The pipeline shall fail when at least one validated file has fewer than 3 counted checkbox items (prose-only or deficient).
12. The pipeline shall distinguish prose-only failures (MEDIUM severity) from deficient failures (LOW severity) in its output.
13. The validation result shall include, for each file, the file path, checkbox count, classification, severity, and a human-readable explanation.
14. The validator shall support processing multiple files in a single run and shall report aggregate pass/fail
    status across all processed files resolved by the pipeline defaults or by explicit CLI inputs.
15. The standalone CLI mode shall return a non-zero exit code when blocking validation failures are present and
    shall treat each resolved file path from the provided paths or patterns as an independent validation target.
16. The optional LLM re-prompting mode shall be disabled by default and enabled only through explicit configuration or invocation.
17. When LLM re-prompting is enabled, the system shall retry regeneration at most **2** times per invalid file and shall follow the staged remediation pattern used by sibling spec `#1191`.

## Non-functional requirements

1. Validation shall be deterministic for the same file contents and configuration.
2. Validation output shall be concise enough for CI logs while still providing per-file remediation guidance.
3. The implementation shall minimize false positives by excluding fenced code blocks from checkbox counting.
4. The validator shall complete within normal CI time budgets for typical SpecKit artifact sets.
5. The standalone CLI and pipeline mode shall use the same counting and classification rules.
6. The feature shall preserve backward compatibility for valid checklist files that already contain 3 or more real checkbox items.

## Edge cases

1. A file containing checkbox examples only inside fenced code blocks shall be treated as having 0 checkbox items.
2. A file containing both prose and exactly 1 or 2 real checkbox items outside code fences shall be treated as deficient, not prose-only.
3. A file containing 3 or more real checkbox items outside code fences plus additional checkbox examples inside code fences shall still be treated as valid.
4. Checked items such as `- [x]` or `- [X]` shall count toward the threshold the same as unchecked items.
5. An empty checklist file or whitespace-only file shall be treated as prose-only.
6. When re-prompting is enabled and retries are exhausted, the final reported result shall remain the last validation outcome rather than being silently ignored.

## Success criteria

1. 100% of prose-only checklist files in the validation scope are reported as blocking failures.
2. 100% of files with exactly 1 or 2 real checkbox items are reported as blocking failures with LOW severity.
3. 100% of checkbox-like lines inside fenced code blocks are excluded from the checkbox count.
4. 100% of files with 3 or more real checkbox items outside fenced code blocks pass validation.
5. When enabled, automatic re-prompting performs no more than 2 retries per invalid file.
6. Validation output always includes enough information for a user to identify the failing file and understand the remediation needed.

## Acceptance criteria

1. Given a checklist file with only prose and no checkbox items, when validation runs, then the file is reported as MEDIUM severity and the pipeline fails.
2. Given a checklist file with exactly 1 or 2 real checkbox items, when validation runs, then the file is reported as LOW severity and the pipeline fails.
3. Given a checklist file with 3 or more real checkbox items, when validation runs, then the file passes validation.
4. Given checkbox syntax inside a fenced code block, when validation runs, then those lines are excluded from the checkbox count.
5. Given multiple checklist files in one run, when validation completes, then the output includes per-file results and an aggregate outcome.
6. Given re-prompting is disabled, when invalid files are detected, then no automatic regeneration attempts are made.
7. Given re-prompting is enabled, when a file is invalid, then the system attempts remediation using the staged pattern from spec `#1191` and stops after at most 2 retries.
8. Given blocking failures are present, when the standalone CLI exits, then it returns a non-zero exit code.

---

*Generated by Copilot SDK (claude-opus-4.6)*
