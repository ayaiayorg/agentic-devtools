# Quickstart: Validate shared review-thread reuse plan (#1517)

## 1. Review scope

- `agentic_devtools/cli/azure_devops/review_scaffold.py`
- `agentic_devtools/cli/azure_devops/review_state.py`
- `agentic_devtools/cli/azure_devops/thread_reuse.py` (new)
- `agentic_devtools/cli/azure_devops/finalization/classification.py`

## 2. Implement in TDD order

1. Add failing tests for thread discovery/matching selection behavior.
2. Implement `thread_reuse.py` discovery helpers and dataclasses.
3. Add failing tests for reuse-reply idempotency behavior.
4. Integrate discovery into scaffold flows and update state population.
5. Add cross-identity reuse + finalization compatibility tests.

## 3. Validate

```bash
agdt-test-pattern tests/unit/cli/azure_devops/thread_reuse/ -v
agdt-test-pattern tests/unit/cli/azure_devops/review_scaffold/ -v
agdt-test-pattern tests/unit/cli/azure_devops/review_state/ -v
agdt-test
agdt-task-wait
bash scripts/run-pr-checks.sh
```

## 4. Expected outcome

- Existing matching scaffold threads are reused across identities.
- Reuse replies are idempotent for the same session/type marker.
- Finalization behavior remains limited to edit-permission author filtering.

---
*Generated for SpecKit Phase 3 (plan)*
