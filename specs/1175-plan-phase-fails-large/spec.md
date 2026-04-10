# Spec 006: Plan phase fails on large issue or context payloads

## Status

Proposed

**Source Issue**: #1175

## Summary

The planning phase must remain reliable when the source issue, related comments, linked artifacts,
or rendered prompt context are unusually large. Today, oversized inputs can cause the plan phase to fail outright
or produce unusable output. This spec defines a deterministic context-budgeting and fallback strategy so planning
succeeds whenever possible, degrades predictably when necessary, and fails with actionable guidance only after all
supported reduction stages are exhausted.

## Problem statement

The plan phase currently assumes that the full issue/context payload can be passed through as-is.
In practice, some issues contain very large descriptions, comment histories, logs, code snippets, or embedded markup.
When the prompt payload becomes too large, downstream planning fails, stalls, or returns low-quality output.
This creates a poor user experience, blocks workflows, and makes the behavior non-deterministic.

The system needs a canonical, reviewable approach for:

- detecting oversized planning context before plan generation,
- reducing content deterministically without LLM summarization,
- preserving current behavior for normal-sized inputs,
- surfacing which fallback stage was used,
- and failing with a clear, permanent error only when no supported fallback can produce valid planning input.

## Goals

- Prevent plan-phase failure caused solely by oversized context.
- Keep reductions deterministic and reproducible.
- Preserve byte-identical behavior for below-budget inputs.
- Make fallback behavior observable and debuggable.
- Ensure reduced outputs still contain substantive planning input.

## Non-goals

- Using LLM-based summarization or semantic compression in the fallback path.
- Redesigning the entire planning workflow.
- Changing plan output requirements unrelated to context size handling.
- Modifying issue retrieval semantics outside what is necessary to support context reduction.

## Clarifications

### Session 2026-04-10

1. **Threshold**: The default context budget is 32,000 characters (approximately 8K tokens), configurable via `AGDT_PLAN_CONTEXT_BUDGET`.
2. **Fallback stages**: Full → Reduced → Truncated → Summary-only → Permanent failure
3. **Reduction techniques**: Only deterministic reductions are allowed, including stripping markup, removing images,
   collapsing whitespace, and truncating content. LLM summarization is explicitly out of scope.
4. **Validation shape**: Reduced content must satisfy a minimum validation rule of non-empty, substantive text.
   Any enhanced validation preferences about preserving structure such as headings and bullet lists are deferred to a later spec.
5. **Backward compatibility**: Inputs below the configured budget must pass through untouched,
   producing byte-identical output relative to current behavior.

## Users and stakeholders

- AI agents running planning workflows
- Developers invoking plan generation locally
- CI or automation flows that depend on stable planning
- Reviewers validating plan/tasks/checklists against the canonical spec

## User stories

### US1: Plan a normal-sized issue without behavior changes

As an AI agent, I want normal-sized planning inputs to pass through unchanged so that existing workflows remain backward compatible.

**Acceptance criteria**

- Given a source payload whose rendered planning context is at or below the configured budget, when the plan phase runs, then the original content is used without reduction.
- Given a below-budget payload, when the plan phase succeeds, then the reduced-stage metadata indicates the full stage using the recorded value `passthrough`.
- Given a below-budget payload, when compared with prior behavior, then the input provided to planning is byte-identical.

### US2: Automatically reduce oversized inputs

As an AI agent, I want oversized planning inputs to be reduced automatically so that planning can still proceed without manual intervention.

**Acceptance criteria**

- Given a source payload above the configured budget, when the plan phase starts, then the system detects the oversize condition before attempting the next stage.
- Given an oversized payload, when deterministic reduction produces content within budget, then planning continues using the reduced content.
- Given reduction success, then the system records that the `reduced` stage was used.

### US3: Hard-truncate when reduction alone is insufficient

As an AI agent, I want oversized content that cannot be sufficiently reduced via formatting stripping to be hard-truncated at a word boundary so that planning can still proceed.

**Acceptance criteria**

- Given reduced content that still exceeds the budget, when hard truncation produces content within budget, then planning continues using the truncated content.
- Given truncation success, then the system records that the `truncated` stage was used.
- Given hard-truncated content, then it ends with a `[…truncated]` marker and respects a word boundary.

### US4: Fall back to summary-only content when truncation is still too large

As an AI agent, I want a smaller summary-only deterministic fallback so that extremely large issues still have a chance to produce a usable plan.

**Acceptance criteria**

- Given full content, reduced content, and truncated content that still cannot satisfy the budget,
  when summary-only extraction fits within budget and validates, then planning proceeds with summary-only content.
- Given summary-only success, then the system records that the `summary-only` stage was used.
- Given summary-only content, then it contains substantive text and retains available structural cues where feasible.

### US5: Receive a clear permanent failure when no valid fallback remains

As an AI agent, I want a final failure to be explicit and actionable so that I know whether retrying will help.

**Acceptance criteria**

- Given full, reduced, truncated, and summary-only content all fail budget or validation requirements, when the plan phase ends, then the system returns a permanent failure.
- Given permanent failure, then the error includes the attempted stages and why each failed.
- Given permanent failure, then the message tells the user what can be done next, such as reducing source issue content manually.

### US6: Understand which fallback stage was used

As a developer or reviewer, I want observable fallback metadata so that I can debug large-input behavior and verify expectations.

**Acceptance criteria**

- Given any plan-phase execution, when it completes, then the chosen stage is recorded in structured output or state.
- Given a non-full stage, then the system also records the reduction reason and final content size.
- Given a failure, then the stage attempt history is preserved for diagnostics.

### US7: Configure the context budget

As a maintainer, I want to adjust the context budget via environment variable so that the system can adapt to model or environment constraints.

**Acceptance criteria**

- Given `AGDT_PLAN_CONTEXT_BUDGET` is unset, when the plan phase runs, then the default budget is 32,000 characters.
- Given `AGDT_PLAN_CONTEXT_BUDGET` is set to a valid positive integer, when the plan phase runs, then that value is used.
- Given `AGDT_PLAN_CONTEXT_BUDGET` is invalid, then the system falls back safely to the default and emits a warning or diagnostic entry.

### US8: Keep reduction deterministic and reviewable

As a reviewer, I want the reduction algorithm to be deterministic so that behavior is reproducible across runs and suitable for validation.

**Acceptance criteria**

- Given the same input content and budget, when the reduction pipeline runs multiple times, then it produces the same output bytes.
- Given deterministic reduction is enabled, then no LLM or probabilistic summarization step is invoked.
- Given reduced output, then the transformation rules are documented and reviewable in code and spec.

## Functional requirements

### P1

- **FR-001**: The plan phase must compute the size of the rendered planning context before execution and compare it against the effective context budget.
- **FR-002**: The effective context budget must default to 32,000 characters and be overrideable via `AGDT_PLAN_CONTEXT_BUDGET`.
- **FR-003**: If the rendered context is at or below the effective budget, the system must use the original content unchanged.
- **FR-004**: If the rendered context exceeds the budget, the system must attempt a deterministic reduced-content stage before failing.
- **FR-005**: The reduced-content stage must use deterministic transformations only: strip markup where appropriate,
  remove images or non-textual payloads, collapse excessive whitespace, and truncate according to stable rules.
- **FR-006**: If reduced content still exceeds the budget, the system must attempt hard truncation at a word boundary with a `[…truncated]` marker.
- **FR-007**: If truncated content still exceeds the budget or fails validation, the system must attempt a deterministic summary-only stage.
- **FR-008**: If all supported stages fail budget or validation checks, the system must return a permanent failure with actionable diagnostics rather than looping or retrying indefinitely.
- **FR-009**: The system must record which stage was selected (`full`, `reduced`, `truncated`, `summary-only`, or `failed`) and why fallback occurred.

> **Stage vocabulary mapping (spec → implementation)**:
> The spec uses lowercase descriptive names for readability. The implementation `ReductionStage` enum uses uppercase Python-convention names.
>
> | Spec term | Enum member | `.value` string |
> |-----------|-------------|------------------|
> | `full` (passthrough) | `PASSTHROUGH` | `"passthrough"` |
> | `reduced` | `REDUCED` | `"reduced"` |
> | `truncated` | `TRUNCATED` | `"truncated"` |
> | `summary-only` | `SUMMARY_ONLY` | `"summary_only"` |
> | `failed` | _(no enum member — raised as `ContextBudgetError`)_ | N/A |
>
> FR-009 records the `.value` string. The `failed` outcome is signalled via exception, not a stage value.

### P2

- **FR-010**: Reduced or summary-only content must pass a validation step that enforces non-empty, substantive text before being used for planning.
- **FR-011**: Enhanced validation for preserving structural cues such as headings, bullets, and ordered lists is explicitly deferred
  to a later spec; this spec only requires the minimal substantive-content validation in FR-010.
- **FR-012**: The system should expose stage-attempt diagnostics sufficient for logs, troubleshooting, and review.

### P3

- **FR-013**: The system may store size statistics or transformation metadata to support future observability and tuning, provided doing so does not alter planning behavior.

## Key entities

1. **Context budget**: The maximum allowed rendered planning input size in characters.
2. **Fallback stage**: The selected attempt mode, one of `full` (`PASSTHROUGH`), `reduced` (`REDUCED`), `truncated` (`TRUNCATED`), `summary-only` (`SUMMARY_ONLY`), or `failed` (`ContextBudgetError` exception).
3. **Reduction pipeline**: The deterministic sequence of transformations applied to oversized content.
4. **Validation result**: Structured outcome indicating whether candidate content is non-empty and substantive, with optional structural-quality indicators.
5. **Attempt history**: Ordered record of stage evaluations and reasons for success or failure.
6. **`AGDT_PLAN_CONTEXT_BUDGET`**: Environment variable used to override the default context budget.

## Non-functional requirements

- **NFR-001 Backward compatibility**: For below-budget inputs, the planning input must remain byte-identical to current behavior.
- **NFR-002 Determinism**: For a fixed input and fixed budget, the selected stage and produced reduced content must be identical across repeated runs.
- **NFR-003 Performance**: Context measurement and deterministic reduction should add minimal overhead and should complete fast enough to avoid materially increasing planning latency for typical runs.
- **NFR-004 Observability**: The system must emit enough structured information to determine budget, selected stage, and stage failure reasons during debugging.
- **NFR-005 Maintainability**: Reduction rules must be implemented in straightforward, reviewable code without hidden model-side behavior or undocumented heuristics.

## Edge cases

1. The source issue is already below budget and must not be modified in any way.
2. The configured environment variable is missing, empty, non-numeric, zero, or negative.
3. The content exceeds budget mostly because of markup, embedded images, or other removable non-text payloads.
4. The content remains oversized even after markup stripping and whitespace collapse.
5. Truncation reduces content below budget but leaves it empty or non-substantive, which must fail validation.
6. The source contains mostly repeated boilerplate or log noise, and reduction must still behave deterministically.
7. Structural content such as headings or bullet lists can be partially preserved and should be retained where feasible.
8. Every fallback stage fails, requiring a final permanent failure with actionable guidance.

## Proposed behavior

### Stage 1: Full

- Measure rendered context size.
- If within budget, pass through unchanged.
- Mark stage as `full`.

### Stage 2: Reduced

- Apply deterministic reduction transforms (strip markdown, remove images, collapse whitespace).
- Re-measure the candidate content.
- Validate that the result is non-empty and substantive.
- If valid and within budget, use it and mark stage as `reduced`.

### Stage 3: Truncated

- Apply hard truncation at a word boundary with a `[…truncated]` marker.
- Re-measure the candidate content.
- Validate that the result is non-empty and substantive.
- If valid and within budget, use it and mark stage as `truncated`.

### Stage 4: Summary-only

- Extract the most essential deterministic text subset available from the issue/context (description only, comments dropped).
- Apply hard truncation if still over budget.
- Re-measure and validate.
- If valid and within budget, use it and mark stage as `summary-only`.

### Stage 5: Permanent failure

- Stop attempting further fallback stages.
- Return a non-retryable failure with stage-attempt details and next-step guidance.
- Mark final outcome as `failed`.

## Integration points

The implementation should integrate with existing planning and workflow modules responsible for:

- collecting issue and related context,
- rendering plan-phase prompt content,
- reading environment configuration,
- emitting logs or structured diagnostics,
- and surfacing plan-phase success or failure to downstream plan/tasks/checklist generation.

This spec does not require a module layout change, but the implementation must be wired into the existing SpecKit
plan-generation entry points for #1175 so reviewers can verify scope directly.

Concrete integration points:

- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - `run_plan_phase()` is the primary orchestration point for plan generation and should own deterministic fallback
    sequencing across `full`, `reduced`, `truncated`, `summary-only`, and permanent-failure stages.
  - `run_plan_phase()` should record which stage was attempted/selected, preserve attempt metadata for diagnostics,
    and surface the final success/failure result to downstream plan/tasks/checklist generation exactly once.
  - `call_llm()` is the pre-invocation enforcement point and should apply the context budget check to the rendered
    plan prompt payload before each LLM call, returning structured size/error information that `run_plan_phase()`
    can use to decide the next fallback stage.
- `.github/scripts/speckit-trigger/copilot_generate.py`
  - This is the Python generation path used by the shell trigger and should implement or expose the generation-time
    handling needed for budget-aware prompt submission, oversized-input detection, and fallback-compatible failure
    signaling back to `generate-spec-from-issue.sh`.

In practical terms, the new behavior should be added to the existing planning path at these entry points rather than
by introducing a new module tree:

- context collection and prompt rendering remain in the current spec-trigger flow,
- budget enforcement happens immediately before plan-generation invocation,
- fallback stage selection is coordinated in `run_plan_phase()`,
- generation errors/size diagnostics are surfaced through `call_llm()` and `copilot_generate.py`,
- and the final selected stage plus failure details are emitted for downstream review/debugging.

## Acceptance criteria

1. A below-budget planning input runs through the `full` stage with byte-identical content.
2. An oversized planning input that can be reduced deterministically succeeds through the `reduced` stage.
3. An oversized input that cannot pass `reduced` but can be hard-truncated succeeds through the `truncated` stage.
4. An oversized input that cannot pass `truncated` but can pass `summary-only` succeeds through the `summary-only` stage.
5. An input that cannot produce valid in-budget content at any stage fails permanently with actionable diagnostics.
6. The selected stage and relevant size/diagnostic metadata are available for debugging or review.

## Success criteria

- Planning no longer fails solely because the original issue/context payload is too large when a valid deterministic fallback exists.
- Existing behavior for normal-sized issues is preserved.
- Reviewers can verify from the spec and output which fallback stage was used.
- The fallback algorithm is deterministic and reproducible.
- Permanent failures are rare, explicit, and actionable.

## Open questions

- Whether diagnostics should be persisted only in logs or also in workflow state.
- Whether the summary-only stage should prioritize specific source sections when multiple structured sections exist.
- Whether future observability should include per-transform size deltas.
