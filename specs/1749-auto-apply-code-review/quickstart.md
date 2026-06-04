# Quickstart: Validate plan assumptions for issue #1749

## 1) Run targeted tests for planned touchpoints

```bash
agdt-test-pattern tests/unit/cli/ci/pipeline/actions/dispatch_repair/ -v
agdt-test-pattern tests/unit/cli/ci/pipeline/ -v
agdt-test-pattern tests/unit/cli/ci/github_provider/ -v
```

## 2) Run repo targeted checks

```bash
bash scripts/targeted-checks.sh
```

## 3) Manual verification checklist

- Action order is `guards -> publish -> apply_suggestions -> dispatch_repair`.
- Exclusion context survives snapshot invalidation and refresh.
- Applied suggestion IDs are filtered from repair dispatch input.
- Retry behavior for suggestion application matches shared retry defaults.
