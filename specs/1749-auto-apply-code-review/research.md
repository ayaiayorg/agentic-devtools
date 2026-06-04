# Research Notes: Auto-apply Code Review Suggestions

## Decision 1: Pipeline placement

- Place `ApplySuggestionsAction` after `PublishAction` and before `DispatchRepairAction`.
- Rationale: it runs only after guards/publish decisions are settled and can reduce downstream repair scope.

## Decision 2: Context propagation across snapshot refresh

- Store exclusion data in runner-scoped context, not `DerivedState`.
- Rationale: `DerivedState` is rebuilt when `invalidates_snapshot=True` triggers a refresh.
- Note: `spec.md` still contains earlier wording that mentions `DerivedState`; this plan-phase artifact uses the runner-scoped context decision above as the implementation reference.
- **Action required before Phase 4**: Update `spec.md` (and any related checklist references that mention
  `DerivedState`) to reflect runner-scoped context propagation, so Phase 4 tasks are generated and
  implemented against a single consistent source.

## Decision 3: Provider-driven GraphQL operations

- Route GraphQL operations through `CIPlatformProvider`/GitHub provider methods.
- Rationale: keeps action logic testable and consistent with existing provider abstraction.

## Decision 4: Retry policy

- Use the existing `retry_with_backoff` defaults (`max_retries=5`, `initial_delay=1s`).
- Rationale: avoids introducing a divergent retry policy without a strong feature-specific reason.
- Note: `spec.md` FR-010 still mentions an earlier 2-retry value; this plan-phase artifact uses shared retry defaults as the implementation reference.
- **Action required before Phase 4**: Update `spec.md` FR-010 to replace the "2 retries" wording with
  `retry_with_backoff` defaults (`max_retries=5`, `initial_delay=1s`), so Phase 4 tasks are generated
  and implemented against a single consistent retry policy.
