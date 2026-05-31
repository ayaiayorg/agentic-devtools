# Quickstart: Parallel-safe State Isolation

## Prerequisites

- Python 3.10+
- Project dependencies installed from the repository baseline

## 1) Implement core segment primitives

- Add `agentic_devtools/segments/` package with:
  - `models.py` (`StateSegment`, `SegmentStatus`)
  - `manager.py` (create/read/write/complete/fail/list)
  - `reconciler.py` (deterministic merge + audit record)
  - `cleanup.py` (TTL expiry + orphan detection)
  - `errors.py` (domain exceptions)

## 2) Integrate parallel worker path

- Update `submit_reviews` worker flow to:
  1. Create one segment per worker
  2. Write worker-local results to that segment
  3. Mark segment `completed` or `failed`
  4. Reconcile completed segments into `reviews/review-state.json`

## 3) Keep serial behavior unchanged

- Do not apply segment wrapping to `SubmissionManager` serial FIFO path.

## 4) Add targeted tests

- Segment model/manager lifecycle tests
- Reconciliation determinism and precedence tests
- Cleanup/orphan recovery tests
- Parallel `submit_reviews` integration coverage

## 5) Validate performance guardrail

- Add pytest timing checks using `time.perf_counter()` and assert serial-mode
  p95 regression remains within 5% versus baseline.

---
*Generated for issue #1525 plan artifacts.*
