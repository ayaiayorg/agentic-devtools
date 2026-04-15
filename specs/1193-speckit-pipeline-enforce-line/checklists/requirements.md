# Requirements Checklist

## Coverage and scope

- [ ] Verify the implementation covers all 5 user stories described by the spec.
- [ ] Verify the implementation satisfies all 17 functional requirements described by the spec.
- [ ] Verify the implementation addresses all 7 documented edge cases.
- [ ] Verify the implementation meets all 4 success metrics defined by the spec.
- [ ] Verify the implementation respects all 5 assumptions and does not contradict any
  clarified behavior.

## Wrapping rules and protected blocks

- [ ] Verify lines exceeding 200 characters are wrapped at word boundaries.
- [ ] Verify fenced code blocks (`` ``` `` and `~~~`) are never modified by the wrapper.
- [ ] Verify table rows (pipe-delimited `| ... |` lines) are never wrapped.
- [ ] Verify YAML front matter (between `---` delimiters at file start) is never wrapped.
- [ ] Verify heading lines (starting with `#`) are never wrapped.
- [ ] Verify inline links and reference-style link labels are not split across lines.
- [ ] Verify inline code spans are not split across lines.

## Markdown-specific continuation rules

- [ ] Verify wrapped continuation lines in list items preserve the original list indentation.
- [ ] Verify wrapped continuation lines in blockquotes preserve the blockquote prefix (`` > ``).
- [ ] Verify nested blockquote prefixes (`` > > ``) are preserved on continuation lines.
- [ ] Verify mixed blockquote + list scenarios preserve both prefix and indentation.

## Pipeline integration

- [ ] Verify the wrap step runs after LLM generation and before the first markdownlint pass.
- [ ] Verify the wrap step logs file paths and wrapped line counts.
- [ ] Verify files with no long lines are not modified.
- [ ] Verify the wrapping step is idempotent (running twice produces identical output).

## Edge cases

- [ ] Verify long URLs (exceeding 200 characters) are left as-is without splitting.
- [ ] Verify single long words (no spaces) exceeding 200 characters are left as-is.
- [ ] Verify reference-style link definitions are not wrapped.
- [ ] Verify lines inside HTML comments are not wrapped.
- [ ] Verify lines immediately after code fence closers are eligible for wrapping.

## Non-functional requirements

- [ ] Verify the wrapping step completes within 5 seconds for typical spec directories.
- [ ] Verify no external dependencies beyond the Python standard library are introduced.
- [ ] Verify no markdown files outside `$SPEC_DIR` are modified.
- [ ] Verify 100% unit test coverage for the wrapping module.
