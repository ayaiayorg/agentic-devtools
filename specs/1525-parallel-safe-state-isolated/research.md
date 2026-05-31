# Research Notes: Parallel-safe State Isolation

## Decision Summary

1. **Segment representation**  
   Use one JSON file per worker under `segments/` to avoid lock contention on
   shared canonical files.

2. **Segment identity format**  
   Use hyphenated UUID4 strings (`str(uuid.uuid4())`) for consistency with
   existing task-state conventions.

3. **Reconciliation precedence**  
   Apply last-writer-wins by `completed_utc` timestamp; break ties using
   lexicographic `segment_id` ordering for deterministic results.

4. **Orphan handling**  
   Detect dead owners using PID liveness checks and transition orphaned `active`
   segments to `failed` before TTL cleanup.

5. **Cleanup policy**  
   Remove terminal segments after a 24-hour TTL, aligned with existing
   background task expiry defaults.

6. **Compatibility boundary**  
   Keep `SubmissionManager` serial FIFO behavior unchanged; apply segment
   isolation to parallel `submit_reviews` worker execution path.

## Why this approach

- Minimizes shared-file lock contention in parallel flows.
- Preserves deterministic output and auditability.
- Limits blast radius by retaining existing serial behavior where already safe.
- Avoids introducing new runtime dependencies for reconciliation or performance checks.

---
*Generated for issue #1525 plan artifacts.*
