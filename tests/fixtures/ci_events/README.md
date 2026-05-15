# CI Event Fixtures

This directory contains recorded webhook payload fixtures for testing the CI provider abstraction.

## Fixture Format

Each fixture is a JSON file representing a raw GitHub Actions event payload as received
from `$GITHUB_EVENT_PATH`. Files are named by event type and action:

- `pull_request_opened.json` — `pull_request` event with `action: "opened"`
- `pull_request_synchronize.json` — `pull_request` event with `action: "synchronize"`
- `pull_request_review_submitted.json` — `pull_request_review` event with `action: "submitted"`
- `issues_labeled.json` — `issues` event with `action: "labeled"`
- `workflow_run_completed.json` — `workflow_run` event with `action: "completed"`
- `golden_pull_request.json` — expected legacy vs Python command outputs for `pull_request`
- `golden_pull_request_review.json` — expected legacy vs Python command outputs for `pull_request_review`
- `golden_workflow_run.json` — expected legacy vs Python command outputs for `workflow_run`
- `golden_issues_labeled.json` — expected legacy vs Python command outputs for `issues/labeled`

## Usage

```python
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent

def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())
```

## Notes

- No `__init__.py` in this directory — it is a data-only fixture directory
- Consistent with existing fixture directories like `tests/e2e_smoke/fixtures/`
