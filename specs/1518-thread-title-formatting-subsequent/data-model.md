# Data Model — Issue #1518: Thread Title Formatting for Subsequent Review Comments

No new data models are introduced by this specification.

## Affected Function Signatures

The only data-model change is the addition of a boolean parameter to two existing
render helpers:

```python
# review_templates.py

def render_file_summary(
    ...,
    commit_hash: str | None = None,
    commit_url: str | None = None,
    is_subsequent: bool = False,   # NEW — default False preserves existing behaviour
) -> str: ...

def render_overall_summary(
    ...,
    commit_hash: str | None = None,
    commit_url: str | None = None,
    is_subsequent: bool = False,   # NEW — default False preserves existing behaviour
) -> str: ...
```

A new utility function is also added to `review_templates.py`:

```python
def rewrite_header_for_subsequent(
    content: str,
    commit_hash: str | None,
    commit_url: str | None,
) -> str: ...
```

## No Schema or State Changes

`ReviewState`, `FileEntry`, and all other state dataclasses remain unchanged.
`review-state.json` layout is unaffected.
