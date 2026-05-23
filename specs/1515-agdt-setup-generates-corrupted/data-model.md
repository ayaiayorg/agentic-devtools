# Data Model: PEM Normalization (#1515)

## Entity: PEM Block (logical)

| Field | Type | Description |
|------|------|-------------|
| `begin_marker` | string | Canonical `-----BEGIN CERTIFICATE-----` line |
| `content_lines` | list[string] | Non-empty base64 payload lines, trimmed |
| `end_marker` | string | Canonical `-----END CERTIFICATE-----` line |

## Canonical Representation Rules

1. Markers are emitted exactly as canonical marker text.
2. Content lines are trimmed and empty/whitespace-only lines are removed.
3. Internal line separator is always `\n`.
4. Trailing newline is controlled by bundle assembly, not required in the
   normalized block return value.

## Derived Bundle Model

| Field | Type | Description |
|------|------|-------------|
| `normalized_system_certs` | set[string] | Canonicalized certifi certificates |
| `normalized_host_certs` | list[string] | Canonicalized host certificates |
| `unified_content` | string | Joined PEM blocks with Unix newlines |

---
*Generated for SpecKit Phase 3 (plan)*
