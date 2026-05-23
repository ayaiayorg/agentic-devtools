# Data Model: Shared review thread reuse (#1517)

## Entity: ThreadMatch

| Field | Type | Description |
|------|------|-------------|
| `thread_id` | int | Azure DevOps thread identifier |
| `comment_id` | int | Root scaffold comment identifier |
| `original_author_id` | string \| null | ID of original thread author from first comment |
| `is_resolved` | bool | Whether the matched thread is resolved |

## Entity: ThreadDiscoveryResult

| Field | Type | Description |
|------|------|-------------|
| `activity_log` | `ThreadMatch` \| `None` | Reusable activity-log thread match |
| `overall_summary` | `ThreadMatch` \| `None` | Reusable overall summary thread match |
| `file_summaries` | `dict[str, ThreadMatch]` | Reusable file-summary matches by normalized file path |

## Review State Extensions

| Field | Type | Owner |
|------|------|-------|
| `activityLogOriginalAuthorId` | string \| null | `ReviewState` |
| `originalAuthorId` | string \| null | `OverallSummary` |
| `originalAuthorId` | string \| null | `FileEntry` |

All fields are optional and serialized only when populated to preserve
backward compatibility with existing state files.

---
*Generated for SpecKit Phase 3 (plan)*
