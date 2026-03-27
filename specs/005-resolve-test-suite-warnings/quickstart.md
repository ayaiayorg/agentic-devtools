# Quick Start — Spec 005: Resolve Test Suite Warnings

## Verify Current State

```bash
# Run tests and observe warnings (before applying this spec)
agdt-test-pattern tests/ -W error --no-header -q
```

## After Implementation

```bash
# Full suite should pass with zero warnings
agdt-test
agdt-task-wait
```
