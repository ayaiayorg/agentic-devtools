# Data Model: Edit-Relevance Metadata

## Entity: `EventPayload`

New boolean fields:

- `title_changed`
- `body_changed`
- `base_changed`
- `edit_changes_known`

## Notes

- All fields default to `False` for backward compatibility.
- Providers populate these fields from platform-specific payloads.
- Guard logic consumes these fields to decide skip/proceed behavior for edited events.
