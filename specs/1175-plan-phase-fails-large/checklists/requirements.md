# Requirements Quality Checklist: Plan Phase Fails Large

Use this checklist to review the requirements/spec quality for `006-plan-phase-fails-large`.
Mark each item as complete only when the spec is explicit, internally consistent, and reviewable without guessing.

## 1. Problem definition and scope

- [ ] The spec clearly defines the problem being solved when the plan phase input becomes too large.
- [ ] The spec states the triggering threshold explicitly, including the documented 32K-character limit.
- [ ] The spec explains whether the threshold is fixed, configurable, or both.
- [ ] The spec defines the role of `AGDT_PLAN_CONTEXT_BUDGET` clearly, including how it affects behavior.
- [ ] The spec distinguishes between normal plan generation and degraded/fallback behavior when context is too large.
- [ ] The spec identifies what is in scope for this change and what is intentionally out of scope.

## 2. User needs and success criteria

- [ ] All 8 user stories are present and written from a user or operator perspective.
- [ ] Each user story has a concrete outcome that can be validated in review or tests.
- [ ] The spec explains how users benefit from deterministic reduction instead of opaque truncation.
- [ ] The spec makes clear what "successful plan phase behavior" looks like when large input is encountered.
- [ ] Success criteria are stated in measurable terms, not vague terms like "better" or "improved."

## 3. Functional requirements

- [ ] All 13 functional requirements are listed explicitly and are individually testable.
- [ ] Each functional requirement uses clear normative language such as "must" or "must not" where appropriate.
- [ ] The 5-stage fallback chain (Full → Reduced → Truncated → Summary-only → Permanent failure) is described step by step with unambiguous ordering.
- [ ] The spec states what causes progression from one fallback stage to the next.
- [ ] The spec states what happens if a fallback stage succeeds.
- [ ] The spec states what happens if all fallback stages fail.
- [ ] Deterministic reduction techniques are named and described clearly enough to implement consistently.
- [ ] The spec states which data must be preserved during reduction and which data may be reduced or omitted.
- [ ] The spec avoids contradictory requirements about completeness versus budget enforcement.
- [ ] The spec defines any required logging, messaging, or visibility for fallback activation.

## 4. Edge cases and failure handling

- [ ] All 8 edge cases are explicitly enumerated or clearly traceable in the spec.
- [ ] The spec covers behavior when the initial prompt is already over budget before any optional context is added.
- [ ] The spec covers behavior when deterministic reduction still cannot reach the target budget.
- [ ] The spec covers behavior when configuration values such as `AGDT_PLAN_CONTEXT_BUDGET` are missing, invalid, or extreme.
- [ ] The spec covers behavior when required plan inputs are unavailable, malformed, or unexpectedly large.
- [ ] The spec defines failure behavior in a way that is consistent with existing workflow expectations.
- [ ] The spec avoids silent failure modes and defines what the user or calling workflow should observe.

## 5. Non-functional requirements

- [ ] All 5 non-functional requirements are explicitly documented.
- [ ] Performance expectations are stated clearly enough to evaluate whether the fallback logic is acceptable.
- [ ] Determinism/reproducibility expectations are explicit, especially for reduction and fallback behavior.
- [ ] The spec addresses maintainability by defining responsibilities clearly rather than embedding ad hoc behavior.
- [ ] The spec addresses observability or diagnosability for large-input failures and fallback activation.
- [ ] The spec does not introduce non-functional expectations that conflict with the existing CLI/workflow architecture.

## 6. Integration points and architecture alignment

- [ ] The spec identifies integration points with existing modules such as `prompts/loader.py`.
- [ ] The spec identifies integration points with existing workflow code such as `cli/workflows/`.
- [ ] The spec explains whether the change belongs in prompt construction, workflow orchestration, or both.
- [ ] The spec defines boundaries between new logic and existing reusable components.
- [ ] The spec avoids requiring changes that would conflict with documented package patterns or workflow behavior.
- [ ] The spec makes downstream effects on prompts, state, or workflow transitions explicit if any are expected.

## 7. Testability and verification

- [ ] Every requirement in the spec can be verified by automated tests, manual review steps, or both.
- [ ] The spec implies concrete test scenarios for threshold crossing, fallback progression, and final failure behavior.
- [ ] The spec defines observable outputs or state changes that tests can assert against.
- [ ] The spec makes deterministic behavior testable rather than subjective.
- [ ] The spec includes enough detail to derive unit-level and workflow-level test coverage without guessing.

## 8. Consistency, clarity, and ambiguity check

- [ ] Terminology is used consistently throughout the spec (for example: threshold, budget, fallback stage, reduction).
- [ ] The spec does not mix implementation details and requirements in a way that obscures reviewer intent.
- [ ] Requirements are specific enough that two implementers would produce materially similar behavior.
- [ ] There are no unresolved placeholders, TODOs, or references that require opening a different checklist file to complete review.
- [ ] The checklist itself is self-contained and usable directly from `checklists/requirements.md`.

## 9. Review outcome

- [ ] Ready for implementation
- [ ] Needs requirement clarification
- [ ] Needs missing edge cases or failure modes added
- [ ] Needs testability improvements
- [ ] Needs architecture/integration clarification

## Notes

- Reviewer:
- Review date:
- Summary:
- Follow-up actions:
