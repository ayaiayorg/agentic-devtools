# Research: Shared review threads across identities (#1517)

## Problem Context

The review scaffold currently creates identity-scoped activity, overall summary,
and file summary threads, which duplicates threads when different identities
review the same PR.

## Findings

1. Marker metadata is sufficient to identify reusable AGDT scaffold threads.
2. Reuse matching should be marker- and path-based (for file summaries), not
   author-filtered.
3. Reuse replies need idempotency markers to prevent duplicate replies on retry.
4. Finalization author filtering should remain scoped to edit-permission checks.

## Decision

Implement a dedicated `thread_reuse.py` discovery module and integrate it into
`review_scaffold.py` so scaffold flows reuse matching threads when present and
create new threads only when no deterministic match exists.

## Consequences

- Avoids duplicate scaffold threads across reviewer identities.
- Preserves deterministic selection and backward compatibility in review state.
- Improves traceability through explicit reuse/create logging.

---
*Generated for SpecKit Phase 3 (plan)*
