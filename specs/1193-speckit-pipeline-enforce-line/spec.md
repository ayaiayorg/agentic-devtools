# Spec: SpecKit pipeline: Enforce line length limits in generated markdown

## 1. Summary

Add a deterministic post-processing step to the SpecKit pipeline that wraps long lines in
generated markdown files at 200 characters. The wrapping step runs after LLM generation but
before the existing markdownlint validation loop, reducing MD013 violations without relying on
LLM prompt instructions. Protected blocks (code fences, tables, YAML front matter, headings)
are preserved unchanged.

## 2. Problem Statement

Generated markdown files frequently exceed the 200-character line length limit configured in
`.markdownlint-cli2.jsonc`. PR #1178 had 7 MD013 violations across multiple files
(`checklists/requirements.md`, `spec.md`, `tasks.md`). Long lines in task descriptions are
particularly common because LLM output tends to produce single-line paragraphs.

Relying on LLM prompts to enforce line length is unreliable — models frequently ignore
formatting constraints. A deterministic post-processing step is more predictable and
eliminates the need for LLM-assisted markdownlint remediation iterations in most cases.

## Clarifications

### Session 2026-04-15

- Q: Should the standalone CLI command modify files in-place or write wrapped output to stdout?
  → A: In-place modification (matching the pipeline behavior), with an optional `--dry-run`
  flag that prints wrapped output to stdout without modifying files. This is consistent with
  the pipeline use case and existing `agdt-*` command patterns.
- Q: Where should the wrapping module be located in the package structure? → A: Core wrapping
  logic in `agentic_devtools/markdown/line_wrapper.py` (new sub-package), with the CLI entry
  point in `agentic_devtools/cli/markdown/commands.py` following existing package conventions.
- Q: Should inline formatting spans (`**bold**`, `*italic*`, `~~strikethrough~~`) be treated
  as unsplittable tokens like inline code spans and links? → A: No. Bold, italic, and
  strikethrough markers are paired delimiters that naturally allow word-boundary breaks between
  interior words. Only inline code spans and links (which have structural syntax that breaks
  if split) need unsplittable-token protection.
- Q: What constitutes a "word boundary" for line splitting purposes? → A: Whitespace characters
  (space, tab) serve as word boundaries. Hyphens, em-dashes, and other punctuation are not
  treated as split points. This keeps the algorithm simple, predictable, and avoids breaking
  hyphenated terms, URLs with hyphens, or punctuation-adjacent tokens.
- Q: What is the CLI entry point name for the standalone wrapping command? → A:
  `speckit-wrap-lines` as a `[project.scripts]` entry point in `pyproject.toml`, since this is
  a SpecKit pipeline utility rather than a general `agdt-*` devtools command.

## 3. Scope

In scope:

- Deterministic line wrapping of markdown files within `$SPEC_DIR`
- Preservation of protected blocks (code fences, tables, YAML front matter, headings)
- Integration into the SpecKit Phase 7 pipeline after generation and before markdownlint
- Markdown-aware wrapping that respects list indentation, blockquote prefixes, and links
- Standalone CLI command (`speckit-wrap-lines`) for ad-hoc wrapping outside the pipeline
- In-place file modification with `--dry-run` support for stdout-only preview

Out of scope:

- Wrapping markdown files outside `$SPEC_DIR`
- Replacing the existing markdownlint validation loop (it remains as a safety net)
- Modifying LLM generation prompts for line length control
- Reformatting table column widths or code block contents
- Treating bold, italic, or strikethrough spans as unsplittable tokens

## 4. Assumptions and Clarifications

1. The line length limit is 200 characters, matching the repository's
   `.markdownlint-cli2.jsonc` MD013 configuration.
2. The wrap step is additive to Phase 7 — it does not replace the existing markdownlint
   validation loop, which remains as a safety net for violations the wrapper cannot handle.
3. Wrapping operates on the final generated markdown files, not on intermediate LLM output.
4. The wrapper uses word-boundary splitting to avoid breaking words mid-token. When a single
   word exceeds the line length limit, the line is left as-is (see EC2).
5. Protected blocks are identified by their markdown syntax (fence markers, pipe-delimited
   rows, YAML delimiters, heading prefixes) and are never modified.
6. Word boundaries are defined as whitespace characters (space, tab). Hyphens, em-dashes, and
   other punctuation are not treated as split points.
7. Inline formatting spans (`**bold**`, `*italic*`, `~~strikethrough~~`) are not treated as
   unsplittable tokens — wrapping may split between words inside these spans, as the paired
   delimiters remain valid across line breaks.
8. The standalone CLI modifies files in-place by default. A `--dry-run` flag outputs wrapped
   content to stdout without modifying the source files.

## 5. Key Entities / Data Model

### WrappableToken

A contiguous sequence of non-whitespace characters that is treated as an atomic unit during
line splitting. Tokens are derived by splitting on whitespace boundaries (spaces and tabs).

| Field       | Type   | Description                                                  |
|-------------|--------|--------------------------------------------------------------|
| `text`      | str    | The token string content                                     |
| `length`    | int    | Character length of the token                                |

### ProtectedBlock

A range of lines that must not be modified by the wrapping algorithm.

| Field        | Type   | Description                                                 |
|--------------|--------|-------------------------------------------------------------|
| `start_line` | int    | Zero-based index of the first protected line                |
| `end_line`   | int    | Zero-based index of the last protected line (inclusive)     |
| `block_type` | str    | One of: `code_fence`, `table`, `yaml_front_matter`, `heading`, `html_comment`, `link_definition` |

### LineContext

Contextual metadata extracted from a line to guide wrapping behavior.

| Field              | Type        | Description                                       |
|--------------------|-------------|---------------------------------------------------|
| `prefix`           | str         | Leading whitespace, blockquote markers (`>`), or list markers to preserve on continuation lines |
| `is_protected`     | bool        | Whether the line falls inside a protected block   |
| `content`          | str         | The line content after the prefix                 |

## 6. User Stories

### US1. Wrap long lines in generated markdown

As a spec author, I want the pipeline to automatically wrap lines exceeding 200 characters in
generated markdown files, so that MD013 violations are eliminated without manual editing.

Priority: P1

Acceptance criteria:

- Lines exceeding 200 characters are wrapped at whitespace word boundaries (spaces and tabs).
- The wrapped output produces zero MD013 violations for the affected lines, excluding lines
  that contain unsplittable tokens (long URLs, single long words) as defined in EC1 and EC2,
  and excluding protected/unwrapped constructs (YAML front matter, headings, reference-style
  link definitions, multi-line HTML comments) as defined in FR-005, FR-006, FR-016, and FR-017.
- Wrapping does not alter the semantic content of the markdown.
- Inline formatting spans (`**bold**`, `*italic*`) may be split between interior words;
  inline code spans and links are never split.

### US2. Preserve protected block structure

As a spec author, I want the pipeline to leave code fences, tables, YAML front matter, and
headings unchanged during wrapping, so that structured content is not corrupted.

Priority: P1

Acceptance criteria:

- Lines inside fenced code blocks (`` ``` `` or `~~~`) are never wrapped.
- Table rows (lines matching `| ... |` format) are never wrapped.
- YAML front matter (between `---` delimiters at the start of a file) is never wrapped.
- Heading lines (starting with `#`) are never wrapped.

### US3. Integrate wrapping into the SpecKit pipeline

As a pipeline operator, I want the wrap step to run automatically in Phase 7 after generation
and before markdownlint validation, so that most line length violations are resolved before
the lint loop begins.

Priority: P2

Acceptance criteria:

- The wrap step executes after file generation and before the first markdownlint run.
- When wrapping resolves all MD013 violations, no LLM remediation iterations are needed.
- The wrap step logs which files were modified and how many lines were wrapped.

### US4. Reduce LLM remediation iterations

As a pipeline operator, I want fewer markdownlint violations reaching the LLM remediation
loop, so that pipeline execution is faster and less costly.

Priority: P2

Acceptance criteria:

- The number of MD013 violations entering the markdownlint loop is reduced by at least 90%
  compared to the baseline without wrapping.
- Files that previously required LLM remediation for line length now pass after wrapping alone.

### US5. Standalone CLI for ad-hoc wrapping

As a developer, I want a standalone CLI command (`speckit-wrap-lines`) to wrap markdown files
outside the pipeline, so that I can fix line length issues in existing files or test wrapping
behavior independently.

Priority: P3

Acceptance criteria:

- The `speckit-wrap-lines` command accepts one or more file paths and wraps lines exceeding
  the configured limit.
- The command supports a `--line-length` flag (default: 200).
- The command reports the number of lines wrapped per file.
- The command modifies files in-place by default.
- A `--dry-run` flag outputs wrapped content to stdout without modifying files.

## 7. Functional Requirements

FR-001. The pipeline shall wrap lines exceeding 200 characters in markdown files located within
`$SPEC_DIR`.

FR-002. Wrapping shall split lines at whitespace word boundaries (spaces and tabs), inserting a
newline before the word that would cause the line to exceed the limit. Hyphens, em-dashes, and
other punctuation are not treated as split points.

FR-003. Lines inside fenced code blocks (delimited by `` ``` `` or `~~~`) shall not be wrapped.

FR-004. Table rows (lines matching the `| ... |` pipe-delimited format) shall not be wrapped.

FR-005. YAML front matter (content between `---` delimiters at the start of a file) shall not
be wrapped.

FR-006. Heading lines (lines starting with one or more `#` characters followed by a space)
shall not be wrapped.

FR-007. Wrapped continuation lines in list items shall preserve the original list indentation
level so that the continuation aligns with the list item text.

FR-008. Wrapped continuation lines in blockquotes shall preserve the blockquote prefix (`` > ``)
on each continuation line.

FR-009. Inline links (`[text](url)`) and reference-style link labels (`[text][ref]`) shall not
be split across lines during wrapping.

FR-010. Inline code spans (`` `...` ``) shall not be split across lines during wrapping.

FR-011. The wrapping step shall run after LLM generation and before the first markdownlint
validation pass in the Phase 7 pipeline.

FR-012. The wrapping step shall log the file path and count of wrapped lines for each modified
file.

FR-013. The wrapping step shall not modify files that contain no lines exceeding the limit.

FR-014. The standalone CLI command (`speckit-wrap-lines`) shall accept a `--line-length` flag
with a default value of 200.

FR-015. The standalone CLI command shall accept one or more file paths or a glob pattern as
positional arguments.

FR-016. Reference-style link definitions (`[label]: url "title"`) shall not be wrapped, as
wrapping could break link resolution.

FR-017. Lines inside multi-line HTML comments (`<!-- ... -->`) shall not be wrapped, as
wrapping could break comment structure.

FR-018. Inline formatting spans (`**bold**`, `*italic*`, `~~strikethrough~~`) are not treated
as unsplittable tokens. Wrapping may split between interior words of these spans.

FR-019. The standalone CLI command shall modify files in-place by default.

FR-020. The standalone CLI command shall support a `--dry-run` flag that outputs wrapped
content to stdout without modifying the source files.

FR-021. The core wrapping logic shall reside in `agentic_devtools/markdown/line_wrapper.py`.

FR-022. The CLI entry point shall reside in `agentic_devtools/cli/markdown/commands.py` and be
registered as `speckit-wrap-lines` in `pyproject.toml` `[project.scripts]`.

## 8. Non-Functional Requirements

NFR-001. The wrapping step shall complete within 5 seconds for a typical spec directory
containing up to 10 markdown files totaling 50 KB.

NFR-002. The implementation shall not introduce external dependencies beyond the Python standard
library for the core wrapping logic.

NFR-003. The implementation shall maintain strict directory isolation such that no markdown file
outside `$SPEC_DIR` is modified by the pipeline wrapping step.

NFR-004. The wrapping algorithm shall produce deterministic output — running the wrapper twice
on the same input shall produce identical output (idempotency).

NFR-005. The implementation shall be testable with unit tests covering each protected block type
and wrapping rule independently.

## 9. Edge Cases

EC1. Long URLs: A line contains a markdown link whose URL alone exceeds 200 characters. The
link shall not be split; the line is left as-is (exceeding the limit is acceptable for
unsplittable tokens).

EC2. Single long words: A line contains a single word (no whitespace) exceeding 200 characters
(e.g., a base64 string). The word shall not be split; the line is left as-is.

EC3. Nested blockquotes: A line inside a nested blockquote (`` > > text ``) exceeds the limit.
Wrapping shall preserve the full blockquote prefix (`` > > ``) on continuation lines.

EC4. Reference-style links: A line contains a reference-style link definition
(`[label]: url "title"`) that exceeds the limit. The definition shall not be wrapped to avoid
breaking the link resolution.

EC5. Mixed list and blockquote: A blockquote contains a list item whose text exceeds the limit.
Wrapping shall preserve both the blockquote prefix and the list indentation on continuation
lines.

EC6. Adjacent protected blocks: A line immediately following a code fence closing marker is a
regular paragraph line and shall be eligible for wrapping.

EC7. HTML comments: Lines inside HTML comments (`<!-- ... -->`) that span multiple lines shall
not be wrapped, as wrapping could break comment structure.

EC8. Hyphenated terms: A long line contains hyphenated words (e.g., `well-established-pattern`).
The hyphen is not a split point; the entire hyphenated term is treated as a single token and
is only breakable at surrounding whitespace boundaries.

EC9. Inline formatting across long lines: A line contains `**bold text spanning many words**`
that exceeds the limit. Wrapping may split between interior words of the bold span; the `**`
delimiters remain valid across the line break.

## 10. Success Metrics

SM1. Zero MD013 violations in generated spec files after the wrapping step, excluding lines
that contain unsplittable tokens (long URLs, single long words) and lines within
protected/unwrapped constructs (YAML front matter, headings, reference-style link definitions,
multi-line HTML comments) that the wrapper intentionally leaves unchanged.

SM2. At least 90% reduction in MD013 violations reaching the markdownlint remediation loop
compared to the baseline without the wrapping step.

SM3. The wrapping step adds less than 2 seconds to the overall Phase 7 pipeline execution time.

SM4. 100% unit test coverage for the wrapping module, with dedicated tests for each protected
block type and edge case.

---

*Generated by Copilot SDK (claude-opus-4.6)*
