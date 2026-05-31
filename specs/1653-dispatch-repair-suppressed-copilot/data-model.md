# Data Model: Suppressed Copilot Review Comment Recovery

## Entities

### ReviewCommentInfo (existing)

- Source: `agentic_devtools/cli/ci/models.py`
- Existing fields used by this feature:
  - `id: int`
  - `path: str`
  - `body: str`
  - `html_url: str`
  - `is_suppressed: bool = False`

## Derived Model Rules

1. REST comments keep their GitHub-provided positive database IDs.
2. Parsed suppressed comments use synthetic negative IDs (`-1`, `-2`, …) so IDs remain unique.
3. Suppressed comments set `is_suppressed=True`.
4. If a file path cannot be parsed, use `(unknown file)`.

## Invariants

- No interface changes to `ReviewCommentInfo`.
- Deduplication key is normalized `(path, body)` exact match only.
- Downstream ID-keyed flows must guard on `is_suppressed` before GitHub ID lookups.
