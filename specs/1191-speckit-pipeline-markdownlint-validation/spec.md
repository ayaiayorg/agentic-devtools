# Spec: SpecKit Pipeline Markdownlint Validation

## 1. Summary

The speckit pipeline shall validate markdown files within the current spec directory using
markdownlint, attempt deterministic auto-fixes first, and only invoke LLM-assisted remediation
when lint errors remain that cannot be resolved mechanically. The workflow must be scoped to
`$SPEC_DIR` only, must reuse the repository's existing markdownlint configuration where present,
and must fail gracefully with actionable output if violations remain after the configured number
of iterations.

## 2. Problem Statement

Authors need a reliable way to ensure generated or edited specification markdown complies with
repository markdown style rules before review. Manual cleanup is slow and error-prone, while
fully automatic rewriting can introduce unwanted semantic changes. The pipeline therefore needs
a staged remediation strategy:

1. lint the spec markdown files in the current spec directory;
2. apply safe deterministic fixes where supported;
3. use LLM remediation only for remaining violations that require semantic edits;
4. stop when files pass or when retries are exhausted;
5. log each iteration clearly for debugging and reviewer confidence.

## 3. Scope

In scope:

- markdownlint validation for markdown files under `$SPEC_DIR`
- use of existing repository markdownlint configuration
- iterative remediation loop combining auto-fix and LLM-assisted fixes
- logging of iterations, lint results, and termination reason
- graceful failure when the process cannot produce lint-clean files

Out of scope:

- editing markdown files outside `$SPEC_DIR`
- introducing a new markdown style configuration format
- broad repository-wide content rewrites unrelated to current spec generation
- replacing markdownlint with a different linter

## 4. Assumptions and Clarifications

1. `$SPEC_DIR` identifies the active spec directory and is the only permitted write scope.
2. The pipeline should reuse the root markdownlint configuration when available instead of
   inventing a spec-specific rule set.
3. The common successful path should complete within 120 seconds and worst-case bounded
   execution should complete within 600 seconds.
4. LLM remediation may use full-file context for the file being repaired, but must not pull in
   unrelated repository files unless already required by the existing workflow.
5. When retries are exhausted, the workflow must fail with diagnostics rather than silently
   succeeding or leaving an ambiguous state.

## 5. User Stories

### US1. Auto-fix straightforward markdown issues

As a spec author, I want the pipeline to automatically fix deterministic markdownlint issues
first, so that common formatting problems are resolved quickly without unnecessary LLM usage.

Priority: P1

### US2. Use LLM remediation only when needed

As a spec author, I want the pipeline to invoke an LLM only for remaining non-trivial markdown
issues, so that semantic corrections can be made while minimizing cost and risk.

Priority: P1

### US3. Fail gracefully when cleanup is not possible

As a reviewer or pipeline operator, I want the workflow to stop with clear diagnostics if lint
violations remain after bounded retries, so I can understand what still needs attention.

Priority: P2

### US4. Inspect what happened during each iteration

As a maintainer, I want per-iteration logs showing lint status and remediation steps, so I can
debug stalls, assess LLM behavior, and verify the pipeline is operating safely.

Priority: P3

## 6. Functional Requirements

FR-001. The pipeline shall run markdownlint against markdown files located within `$SPEC_DIR`.

FR-002. The pipeline shall not intentionally read from or write to markdown files outside
`$SPEC_DIR`, except for reading shared repository configuration required to execute markdownlint.

FR-003. The pipeline shall reuse the repository's existing markdownlint configuration when one is
available and applicable.

FR-004. The pipeline shall attempt deterministic markdownlint auto-fixes before invoking any LLM
remediation step.

FR-005. If deterministic auto-fixes result in zero remaining markdownlint violations, the pipeline
shall terminate successfully without calling the LLM.

FR-006. If markdownlint violations remain after deterministic fixes, the pipeline shall invoke an
LLM remediation step using the full contents of the affected file plus lint feedback needed to
repair the remaining issues.

FR-007. The pipeline shall limit LLM remediation to files in `$SPEC_DIR` that still have active
markdownlint violations.

FR-008. After each remediation iteration, the pipeline shall rerun markdownlint to verify whether
all violations have been resolved.

FR-009. The pipeline shall support a configurable maximum number of remediation iterations.

FR-010. The pipeline shall detect lack of progress across iterations, including cases where the
same violations repeat or where violation count does not improve, and shall stop rather than
loop indefinitely.

FR-011. The pipeline shall preserve required document footer content and other mandated spec
structure unless a change is necessary to satisfy markdownlint and remains semantically
equivalent.

FR-012. The pipeline shall produce per-iteration logs that record which phase ran
(lint, auto-fix, LLM remediation, verification), what files were targeted, and the resulting
lint status.

FR-013. When the pipeline reaches the maximum iteration limit or stall detection threshold without
achieving a clean result, it shall fail with a summary of remaining violations.

FR-014. On successful completion, the pipeline shall leave the spec markdown files in a
markdownlint-clean state and report success for the current `$SPEC_DIR`.

## 7. Non-Functional Requirements

NFR-001. In the common case where issues are resolved by auto-fix or one LLM pass, the validation
and remediation flow should complete within 120 seconds.

NFR-002. In the worst case, bounded by retry and timeout controls, the flow shall complete or fail
within 600 seconds.

NFR-003. The implementation shall maintain strict directory isolation such that no markdown file
outside `$SPEC_DIR` is modified by the remediation process.

NFR-004. LLM prompts shall remain reasonably bounded per file. For implementation and testing,
estimated token count shall be calculated as `ceil(character_count / 4)`, where
`character_count` is the total number of characters in the final per-file prompt payload sent to
the LLM. To satisfy the fewer-than-8,000-token target, the implementation shall enforce a maximum
prompt size of 32,000 characters per file before any LLM call.

NFR-005. The solution should reuse existing repository tooling and configuration rather than
introducing parallel markdownlint infrastructure unless required for compatibility.

NFR-006. The implementation should remain simple to operate and maintain, preferably centered in
the existing speckit pipeline flow rather than creating fragmented multi-tool behavior.

## 8. Edge Cases

EC1. Auto-fix-only success: all violations are resolved by deterministic fixes and no LLM call
is made.

EC2. Mixed success path: deterministic fixes resolve some violations, but the LLM is required
for the remaining semantic or structural issues.

EC3. LLM regression: the LLM resolves some lint errors but introduces new markdownlint
violations; the pipeline must detect this on re-lint and continue only within the configured
iteration limits.

EC4. No-progress loop: repeated iterations produce the same or equivalent lint findings; the
pipeline must detect stall conditions and stop with diagnostics.

EC5. Tool unavailability: markdownlint or `npx` is unavailable; the pipeline must fail clearly
with an actionable error instead of silently skipping validation.

EC6. Configuration lookup: no repo markdownlint config is present; the pipeline must either use
markdownlint defaults or fail explicitly according to existing project behavior, but must do so
deterministically and visibly.

EC7. Footer preservation: a file contains required generated footer text; remediation must not
accidentally delete it unless replacement is explicitly required and semantically equivalent.

EC8. Partial cleanup at limit: the final iteration reduces violations but does not eliminate
them; the pipeline must still fail and report the unresolved items.

EC9. Empty spec directory: `$SPEC_DIR` contains zero `*.md` files (the glob expands to nothing).
The pipeline must detect the empty input set and terminate with an early success result rather
than passing an empty glob to `markdownlint-cli2`, whose behavior on empty input is undefined.

## 9. Acceptance Criteria

AC1. Given markdown files in `$SPEC_DIR` with only auto-fixable lint errors, when the pipeline
runs, then it fixes the files, reruns markdownlint, reports success, and makes no LLM call.

AC2. Given markdown files in `$SPEC_DIR` with remaining non-trivial lint errors after
deterministic fixing, when the pipeline runs, then it invokes LLM remediation only for affected
files and reruns markdownlint after each remediation pass.

AC3. Given all markdownlint violations are resolved within the configured retry budget, when the
pipeline completes, then the final reported result is success and the files are lint-clean.

AC4. Given violations remain unchanged across iterations or the iteration limit is reached, when
the pipeline stops, then it reports failure with the remaining violations and termination reason.

AC5. Given files exist outside `$SPEC_DIR`, when the pipeline runs, then those files are not
modified by markdown remediation.

AC6. Given the repository already defines markdownlint configuration, when the pipeline runs,
then that configuration is reused rather than replaced by a divergent spec-specific config.

AC7. Given the common successful path, when the workflow completes, then execution time is at
or below 120 seconds in normal conditions.

AC8. Given worst-case retry exhaustion, when the workflow completes or fails, then total bounded
runtime is at or below 600 seconds.

AC9. Given any remediation iteration occurs, when logs are reviewed, then each iteration shows
the phase performed, target file(s), and resulting lint status.

AC10. Given a clean initial lint result, when the pipeline runs, then it reports success without
unnecessary file rewrites or LLM usage.

## 10. Success Metrics

1. At least 90% of spec markdown validation runs should pass on the first push after generation
   or remediation.
2. The markdownlint validation/remediation overhead should be no more than 120 seconds in the
   common successful path.
3. The pipeline should avoid unnecessary LLM calls whenever deterministic fixes fully resolve
   violations.
4. Iteration logging should be sufficient for a maintainer to reconstruct what happened during
   the run.
5. No markdown file outside `$SPEC_DIR` should be modified by the process.

## 11. Risks and Mitigations

- Risk: LLM remediation changes wording in a way that alters meaning.
  Mitigation: Use auto-fix first, scope LLM input to affected files, and verify with re-lint.

- Risk: Infinite or wasteful retry loops.
  Mitigation: Enforce maximum iterations and explicit stall detection.

- Risk: Config drift between lint execution paths.
  Mitigation: Reuse the repository's existing markdownlint configuration.

- Risk: File leakage beyond intended scope.
  Mitigation: Restrict remediation targets to `$SPEC_DIR` and report touched files per
  iteration.

## 12. Definition of Done

This specification is complete when:

1. the speckit pipeline behavior for markdownlint validation and remediation is fully described
   in this file;
2. reviewers can validate user stories, FRs, NFRs, edge cases, and acceptance criteria without
   following an external link;
3. the documented behavior is sufficient to guide implementation and review.
