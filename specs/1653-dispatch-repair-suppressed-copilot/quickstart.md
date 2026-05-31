# Quickstart: Verify plan assumptions for issue #1653

## 1) Run targeted tests for planned touchpoints

```bash
agdt-test-pattern tests/unit/cli/ci/github_provider/ -v
agdt-test-pattern tests/unit/cli/ci/pipeline/snapshot/ -v
agdt-test-pattern tests/unit/cli/ci/evaluator/snapshot/ -v
```

## 2) Run full suite

```bash
agdt-test
agdt-task-wait
```

## 3) Run targeted repo checks

```bash
bash scripts/targeted-checks.sh
```

## 4) Manual verification checklist

- Mixed review (REST + suppressed) returns merged comments.
- Suppressed-only review still yields repair context.
- No-suppressed review behavior remains unchanged.
- Snapshot/evaluator ID-based flows skip suppressed synthetic IDs.
