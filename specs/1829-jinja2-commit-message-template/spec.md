# Feature Specification: Jinja2 Commit Message Template System

**Feature Branch**: `speckit/1829/phase-2-clarify`
**Created**: 2026-06-07
**Status**: Draft
**Source Issue**: #1829 (<https://github.com/ayaiayorg/agentic-devtools/issues/1829>)

## Clarifications

### Session 2026-06-07

- Q: Where exactly in the `agdt-setup` flow should template creation and validation be inserted — before or after dependency checks, env var persistence, and workflow template generation? → A:
  Template creation and validation should occur after dependency checks and env var persistence but before (or alongside) workflow template generation, since it is a repo-level configuration artifact
  similar to workflow templates. It should be gated by the existing `skip_repo_steps` flag (version guard) and the `--skip-templates` CLI flag, consistent with how other repo-file-creating steps are
  skipped. Because this extends `--skip-templates` behavior beyond workflow templates, the `agdt-setup` CLI flag help text and setup documentation must explicitly describe that commit-template
  creation/validation are skipped too.

- Q: When both a template file exists AND rendering fails (syntax error or empty file), and the fallback to `commit_message` state key is taken, should the system also emit a warning about the
  template failure, or silently fall back? → A: The system MUST emit a diagnostic warning to stderr describing the template failure (including the Jinja2 error message for syntax errors, or "commit
  template file is empty or whitespace-only" for zero-byte/whitespace-only files) before falling back to the `commit_message` state key. This ensures the user is aware their template is broken.

- Q: For `issueLink` derivation — when `resolve_github_repo()` calls `sys.exit(1)` on resolution failure, should the template renderer catch that exit and treat `issueLink` as unresolved instead of
  letting the process terminate? → A: Yes. The template render-context builder MUST NOT call `resolve_github_repo()` directly (which exits on failure). Instead, it should use a non-exiting
  repo-resolution path with equivalent semantics (e.g., catch `SystemExit`, or otherwise separate resolution logic from process exit behavior). If repo resolution fails, `issueLink` is simply
  unresolved and follows the standard unresolved-variable warning path.

- Q: Should the `--commit-message` CLI argument to `agdt-git-save-work` override the template system entirely (i.e., skip template rendering), or should it be ignored when a template exists? → A: The
  `--commit-message` CLI argument MUST override the template system entirely. Priority order is: (1) `--commit-message` CLI arg (use verbatim, no template rendering), (2) template rendering if
  `.agdt/config/commit-template.j2` exists, (3) raw `commit_message` state key fallback. This preserves the existing CLI-arg-overrides-state pattern.

- Q: Does the `versionControl.commitMessageBodyFile` path resolution use an absolute path, or is it relative to the git repository root? → A: The path stored in `versionControl.commitMessageBodyFile`
  is resolved as follows: if the value is an OS-native absolute path, use it directly; if relative, resolve it relative to the git repository root. If the file does not exist at the resolved path,
  `commitMessageBody` is treated as unresolved.

## Problem Statement

The current `agdt-git-save-work` workflow constructs commit messages by reading a raw `commit_message` state key that must be manually composed by the AI agent or user each time a commit is created.
This means the agent must remember the full conventional-commit format — including the correct issue type prefix, the GitHub issue markdown link in the scope, the footer reference, and any
project-specific formatting — every single time it creates or amends a commit. There is no mechanism to enforce a consistent commit message structure across repositories, and no way for repository
maintainers to customize the commit format without modifying the agentic-devtools source code itself.

This inflexibility causes several practical problems. First, AI agents frequently produce commit messages that deviate slightly from the expected conventional-commit format defined in
COMMIT_CONVENTION.md — perhaps omitting the footer link, using a bare issue number instead of a full markdown link, or choosing the wrong issue type prefix. These deviations are caught only during
code review or CI validation, creating unnecessary review churn and wasted cycles. Second, different repositories within an organization may have distinct commit message conventions (such as including
a Jira key alongside a GitHub issue link, or using a custom scope format), but the current system provides no per-repo configuration mechanism. Repository maintainers must rely entirely on prompt
instructions and hope that the AI agent follows them consistently, which is fragile.

Third, when the commit message format needs to change (for example, when the project adopts a new link format or adds a required trailer), every prompt and instruction that references commit message
structure must be updated simultaneously. A template-based approach would provide a single source of truth for the commit format that both humans and AI agents can reference, and that the system
itself can validate against before the commit is created.

The proposed Jinja2 template system addresses these problems by introducing a configurable, validatable, and self-documenting template at `.agdt/config/commit-template.j2` that the system renders at
commit time. Variables are resolved from state, and any unresolved variables trigger a warning (not a failure) to provide helpful feedback to agents and humans without blocking their workflow.

## User Scenarios & Testing

### User Story 1 — Default Template Auto-Creation on Setup (Priority: P1)

As a developer running `agdt-setup` for the first time in a repository, I want the system to create a sensible default commit message template at `.agdt/config/commit-template.j2` so that I
immediately benefit from structured commit messages without any additional configuration. The template should follow the conventional-commit format already documented in the project's
COMMIT_CONVENTION.md file, including the issue type, scoped issue link, title line, body content, and footer reference.

**Why this priority**: Without the default template being created during setup, the entire feature has no entry point. Every other capability (rendering, validation, warnings) depends on a template
existing on disk. This is the foundational piece that bootstraps the system.

**Integration with `agdt-setup` flow**: Template creation occurs after dependency checks and env var persistence, alongside (or immediately before) workflow template generation. It is gated by the
existing `skip_repo_steps` flag and the `--skip-templates` CLI flag, so that version-guard-blocked or template-skipped runs do not attempt template creation or validation.

**Independent Test**: Run `agdt-setup` in a repository that has no `.agdt/config/commit-template.j2` file and verify the file is created with the expected default content. Then run `agdt-setup` again
and verify the file is not overwritten.

**Acceptance Scenarios**:

1. **Given** a repository where `.agdt/config/commit-template.j2` does not exist, **When** `agdt-setup` runs, **Then** the file is created with
   the default template content containing `{{ issueType }}`, `{{ issueKey }}`, `{{ issueLink }}`, `{{ commitMessageTitle }}`, and `{{ commitMessageBody }}` variables.

2. **Given** a repository where `.agdt/config/commit-template.j2` already exists with user-customized content, **When** `agdt-setup` runs, **Then** the existing file is left untouched and not
   overwritten.

3. **Given** a repository where the `.agdt/config/` directory does not yet exist, **When** `agdt-setup` runs and creates the template, **Then** the directory structure is created automatically and the
   template file is placed correctly within it.

4. **Given** `agdt-setup` is invoked with `--skip-templates` or the version guard returns `"force"` (setting `skip_repo_steps = True`), **When** the template creation step is reached, **Then** it is
   skipped entirely and no file is created or validated.

---

### User Story 2 — Commit Message Rendering from Template (Priority: P1)

As a developer or AI agent invoking `agdt-git-save-work`, I want the commit message to be rendered from the Jinja2 template using variables resolved from the current workflow state, so that I only
need to set individual state keys (issue type, title, body file path) rather than composing the full formatted message manually.

**Why this priority**: This is the core runtime behavior that delivers the primary value of the template system. Without rendering, the template file is inert. This story represents the integration
point between the template on disk and the git commit flow.

**Note on `commitMessageBody`**: Unlike other variables that are resolved directly from state keys, `commitMessageBody` is populated by reading the content of a file whose path is stored in the
`versionControl.commitMessageBodyFile` state key. This avoids requiring agents to set a large multiline string directly in state; instead they write the body text to a file and point the state key at
that path. The path is resolved using OS-native absolute-path semantics; if the configured path is not absolute, it is resolved relative to the git repository root.

**Priority order for commit message source**: (1) `--commit-message` CLI argument (use verbatim, no template rendering), (2) template rendering if `.agdt/config/commit-template.j2` exists (attempt
rendering; if invalid/empty, emit warning and fall back per FR-007), (3) raw `commit_message` state key fallback.

**Independent Test**: Set the state inputs required by the FR-003 render-context mapping (including `versionControl.commitMessageBodyFile` pointing to a file containing the body text), invoke
`agdt-git-save-work`, and verify the resulting commit message matches the rendered template output with all variables substituted correctly (including `commitMessageBody` populated from the file).

**Acceptance Scenarios**:

1. **Given** a valid template at `.agdt/config/commit-template.j2` and all required state keys are set, **When** the commit message is rendered, **Then** all template variables are replaced with their
   corresponding state values and the resulting message conforms to the expected format.

2. **Given** the `versionControl.commitMessageBodyFile` state key points to a file containing multiline content with special characters, **When** the template is rendered, **Then** the body content
   read from the file is preserved exactly as-is in the rendered output without any escaping or modification.

3. **Given** no template file exists at the expected path, **When** the commit message is rendered, **Then** the system falls back to using the raw `commit_message` state key directly
   (backward-compatible behavior).

4. **Given** a valid template exists but the `--commit-message` CLI argument is provided, **When** `agdt-git-save-work` executes, **Then** the CLI argument value is used verbatim as the commit message
   and template rendering is skipped entirely.

5. **Given** `versionControl.commitMessageBodyFile` contains a relative path (e.g., `docs/body.txt`), **When** the template is rendered, **Then** the path is resolved relative to the git repository
   root.

---

### User Story 3 — Warning on Unresolved Template Variables (Priority: P1)

As a developer or AI agent, I want to receive a clear warning (not a hard failure) when any template variable cannot be resolved from state, so that I am informed about missing data while still being
able to proceed with the commit if I choose to.

**Why this priority**: Hard failures on missing variables would block agents and break existing workflows that partially rely on state being set. A warning-based approach provides discoverability and
helpful feedback without introducing regressions. This is critical for the system to be adopted incrementally.

**Independent Test**: Set all state keys except one (e.g., omit `versionControl.commitMessageBodyFile`), render the template, and verify that a warning is printed to stderr listing
`commitMessageBody` as the unresolved variable, while the rendered output contains an empty string in place of the unresolved variable (consistent with FR-004).

**Acceptance Scenarios**:

1. **Given** a template with 5 variables and only 4 are resolved from state, **When** the template is rendered, **Then** a warning message is printed to stderr identifying the unresolved variable by
   name.

2. **Given** multiple unresolved variables, **When** the template is rendered, **Then** each unresolved variable is listed individually in the warning output so the user can address them
   systematically.

3. **Given** all variables are resolved, **When** the template is rendered, **Then** no warnings are emitted and the operation completes silently (aside from normal operational output).

---

### User Story 4 — Template Validation During Setup (Priority: P2)

As a repository maintainer who has customized the commit template, I want the system to validate that my template references all required variables during `agdt-setup`, so that I am alerted to
potential issues before they cause problems at commit time.

**Why this priority**: This is a quality-of-life improvement that catches configuration errors early. While not strictly required for the system to function, it significantly reduces debugging time
when templates are misconfigured. It depends on User Story 1 being in place.

**Independent Test**: Create a template that omits one of the required variables (e.g., `{{ issueKey }}`), run `agdt-setup`, and verify a validation warning is printed identifying the missing
variable.

**Acceptance Scenarios**:

1. **Given** an existing template that includes all required variables, **When** `agdt-setup` runs validation, **Then** no warnings are emitted and setup completes normally.

2. **Given** an existing template that is missing the `{{ issueLink }}` variable, **When** `agdt-setup` runs validation, **Then** a warning is printed indicating which required variable is absent, but
   setup does not fail.

3. **Given** an existing template that contains additional custom variables beyond the required set, **When** `agdt-setup` runs validation, **Then** no error is raised because extra variables are
   permitted.

---

### User Story 5 — Fallback to Raw Commit Message (Priority: P2)

As a user who has not yet adopted the template system or who is working in a repository without a template configured, I want the commit flow to fall back gracefully to the existing `commit_message`
state key behavior, so that the template system does not break any existing workflow.

**Why this priority**: Backward compatibility is essential for incremental adoption. Users who have not opted into the template system must not experience any change in behavior. This story ensures
the feature is additive rather than disruptive.

**Independent Test**: Remove or never create the template file, set `commit_message` in state, run `agdt-git-save-work`, and verify the commit uses the raw state value exactly as before.

**Acceptance Scenarios**:

1. **Given** no template file exists and `commit_message` is set in state, **When** `agdt-git-save-work` executes, **Then** the commit message is taken directly from the `commit_message` state key
   with no template processing.

2. **Given** both a template file exists and the `commit_message` state key is set, **When** the system determines which to use, **Then** the template takes precedence and `commit_message` is ignored
   (or used only as a fallback if template rendering fails).

### Edge Cases

What happens when the template file exists but is empty (zero bytes)? The system MUST treat an empty template as invalid, print a diagnostic warning to stderr (stating "commit template file is empty
or whitespace-only"), and fall back to the raw `commit_message` state key.

What happens when the template file contains syntax errors (e.g., unclosed `{{ }}`)? The system MUST catch the Jinja2 `TemplateSyntaxError`, print a diagnostic warning to stderr with the error details
(including the Jinja2 error message), and fall back to the raw `commit_message` state key rather than crashing.

What happens when none of the template variables are set in state? All variables should appear as unresolved warnings, and the rendered output should contain empty strings in place of the variable
values (using the configured Jinja2 `Undefined` behavior that renders missing variables as empty strings).

What happens when `resolve_github_repo()` would call `sys.exit(1)` during `issueLink` derivation? The template render-context builder MUST use a non-exiting resolution approach with equivalent
repo-resolution semantics (for example by catching `SystemExit` or otherwise separating resolution logic from process exit behavior). If repo resolution fails, `issueLink` is treated as unresolved and
follows the standard warning path without terminating the process.

What happens when `versionControl.commitMessageBodyFile` contains a relative path? It is resolved relative to the git repository root. If the resolved path does not exist, `commitMessageBody` is
treated as unresolved.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST create a default commit message template at `.agdt/config/commit-template.j2` during `agdt-setup` execution when the file does not already exist at that path. The default
  template MUST use exactly the following content:

  ```jinja2
  {{ issueType }}([{{ issueKey }}]({{ issueLink }})): {{ commitMessageTitle }}

  {{ commitMessageBody }}

  [{{ issueKey }}]({{ issueLink }})
  ```

  The indentation around this code block is for Markdown readability only and MUST NOT be written to the template file. Template creation MUST be gated by the existing `skip_repo_steps` flag and the
  `--skip-templates` CLI flag, consistent with other repo-file-creating steps in `agdt-setup`.

- **FR-002**: The system MUST NOT overwrite an existing `.agdt/config/commit-template.j2` file during `agdt-setup` execution, regardless of whether the existing file matches the default content or has
  been customized by the user.

- **FR-003**: The system MUST render the commit message template using Jinja2 when `.agdt/config/commit-template.j2` exists and the commit flow is invoked via `agdt-git-save-work` AND no
  `--commit-message` CLI argument was provided. The `--commit-message` CLI argument takes highest priority and bypasses template rendering entirely. The system MUST
  construct a render context that maps template variable names (`issueType`, `issueKey`, `issueLink`, `commitMessageTitle`, `commitMessageBody`) to values derived from state, without requiring or
  introducing new un-namespaced top-level state keys named after template variables. This mapping MUST support namespaced state keys and legacy fallbacks where applicable, with the following
  deterministic resolution order:

  - `issueKey`: `issue_key` → `jira.issue_key` → `issueManagement.issueKey` (optional future alias,
    checked last) → unresolved. A null/missing/empty-string value at every level yields unresolved.
    The resolved raw value MUST
    then be normalized before being placed in the render context using this decision tree:
    (a) **GitHub issue number**: if `type(raw) is int` (this excludes `bool` because in Python
    `type(True) is int` evaluates to `False`, so only pure integer literals pass) OR if `raw` is a
    string satisfying `raw.isascii() and raw.isdigit() and (len(raw) == 1 or raw[0] != '0')`
    (i.e., one or more
    ASCII digits with no leading zeros; the single-character string `'0'` is accepted and maps to
    `#0`) — prepend `#` to form `#N` (e.g., integer `42` or string `"42"` → `"#42"`; `"0"` →
    `"#0"`; `"007"` does NOT match); (b) **pre-formatted GitHub key**: if `raw` is a string
    matching the pattern `^#[0-9]+$` (exactly one `#` followed by one or more ASCII digits and nothing
    else, e.g., `"#42"`) — use it as-is; (c) **all other cases** (Jira-style keys like
    `"PROJ-123"`, free-form strings like `"#abc"`) — use the raw string value without modification
    and do NOT prepend `#`.
  - `issueLink`: `issueManagement.issueLink` → derived from resolved GitHub repo + raw numeric issue
    number → unresolved. When no explicit link state key is present, the system MUST attempt
    derivation only if `issueKey` resolved via rule (a) or (b) above (i.e., it is a GitHub issue
    number or pre-formatted `#N` key), and GitHub repository resolution succeeds using existing
    AGDT repo-resolution semantics (equivalent to `resolve_github_repo()`): prefer `github.repo`
    after leading/trailing whitespace trimming and optional trailing `.git` removal, and if that is
    missing or malformed, fall back to deriving `owner/repo` from the git `origin` remote URL.
    Construct `https://github.com/{owner_repo}/issues/{raw_number}` where `{raw_number}` is the
    integer extracted from the raw `issueKey` value — for a Python `int` raw value this is the
    value itself; for a digits-only string this is `int(raw)`; for a `#N`-pattern string this is
    `int(raw[1:])`. If repository resolution fails, or if the issue key matched rule (c),
    `issueLink` is unresolved. **IMPORTANT**: The render-context builder MUST NOT call
    `resolve_github_repo()` directly because that function calls `sys.exit(1)` on failure.
    Instead, it MUST use a non-exiting repo-resolution path with equivalent semantics (for
    example by catching `SystemExit` or otherwise separating the resolution logic from process
    exit behavior) so that a failed repo resolution simply leaves `issueLink` as unresolved.
  - `commitMessageTitle`: `versionControl.commitMessageTitle` → unresolved
  - `issueType`: `versionControl.commitMessageType` → explicit mapped value derived from `issueManagement.issueType` or `jira.issue_type` → unresolved
  - `commitMessageBody`: Read file content from the path in `versionControl.commitMessageBodyFile`. Path resolution: absolute paths are used directly; relative paths are resolved relative to the git
    repository root. If the state key is missing, empty, or the resolved file path does not exist or cannot be read, `commitMessageBody` is unresolved.

  `issueType` in the render context MUST be a Conventional Commits type (`feat`, `fix`, `docs`, etc.), and when derived from Jira issue type it MUST use this default mapping unless explicitly
  overridden
  by configuration: `Story`/`Feature` → `feat`, `Task` → `chore`, `Bug` → `fix`, `Epic` → `feat`, `Sub-task` → `chore`.

- **FR-004**: The system MUST emit a warning to stderr for each template variable that cannot be resolved from state during rendering. Each warning MUST identify the specific unresolved variable by
  name. If `versionControl.commitMessageBodyFile` is missing or points to a file that cannot be read, the system MUST treat `commitMessageBody` as unresolved, emit the same warning behavior for
  `commitMessageBody`, and continue rendering. Rendering MUST still complete (not raise an exception) with unresolved variables replaced by empty strings.

- **FR-005**: The system MUST fall back to the raw `commit_message` state key when no template file exists at the expected path, preserving full backward compatibility with the existing commit message
  flow.

- **FR-006**: The system MUST validate existing templates during `agdt-setup` by checking that all required variables (`issueType`, `issueKey`, `issueLink`, `commitMessageTitle`, `commitMessageBody`)
  are referenced in the template, unless `--skip-templates` is provided or `skip_repo_steps` is true (in which case validation is skipped). Validation failures MUST produce a warning (not an error)
  and MUST NOT prevent setup from completing.

- **FR-007**: The system MUST handle invalid template content gracefully during rendering by printing a diagnostic warning to stderr (including the Jinja2 error message for syntax errors, or "commit
  template file is empty or whitespace-only" for zero-byte/whitespace-only files) and falling back to the raw `commit_message` state key rather than
  propagating an exception. This requirement MUST cover both Jinja2 `TemplateSyntaxError` exceptions and empty template content (zero-byte or whitespace-only template files). If this fallback path
  is taken and `commit_message` is missing or empty, the system MUST exit with a clear, actionable error that explicitly instructs users/agents to either fix the template or set `commit_message`.

- **FR-008**: The system MUST create the `.agdt/config/` directory structure automatically if it does not exist when writing the default template during setup.

- **FR-009**: Documentation MUST be updated to describe the commit message template system, including: how to use the default template, how to customize the template for repository-specific formats,
  and troubleshooting guidance for common issues (unresolved variables, Jinja2 syntax errors, and empty template fallback behaviour). This MUST include updating `docs/state-keys.md` to document the
  new inputs (`versionControl.commitMessageType`, `versionControl.commitMessageTitle`, `versionControl.commitMessageBodyFile`) and optional `issueManagement.issueLink`. It MUST also include updating
  `agdt-setup --skip-templates` CLI help text and setup documentation to state that the flag skips commit-template creation/validation in addition to workflow template generation.

### Non-Functional Requirements

- **NFR-001**: Template rendering MUST complete within 100 milliseconds for templates containing up to 20 variables, ensuring no perceptible delay in the commit flow.

- **NFR-002**: Warning messages for unresolved variables MUST follow the existing AGDT CLI output conventions (prefixed with `Warning:` and written to stderr) so that AI agents can parse and act on
  them programmatically.

- **NFR-003**: The Jinja2 dependency MUST be declared in the package's dependencies (it is already available in the environment for the existing prompt template system) and MUST NOT introduce a new
  transitive dependency that is not already present.

- **NFR-004**: All new code paths MUST achieve 100% branch coverage in unit tests, consistent with the repository's existing coverage requirements enforced by CI.

### Key Entities

- **Commit Template**: A Jinja2 template file at `.agdt/config/commit-template.j2` that defines the structure of commit messages. Contains variable placeholders that are resolved from workflow state
  at render time.

- **Template Variables**: Named placeholders within the template (`issueType`, `issueKey`, `issueLink`, `commitMessageTitle`, `commitMessageBody`) that map to render-context entries at render
  time. Render-context values are derived from namespaced and legacy state keys (rather than requiring same-name top-level keys). `commitMessageBody` is a special case: it is populated by reading
  the file content referenced by the `versionControl.commitMessageBodyFile` state key (resolved as absolute or relative to git repo root) rather than being set directly as a multiline string in state.
  Each variable has a required/optional designation for validation purposes.

- **Render Context**: The dictionary of resolved variable values passed to Jinja2 for template rendering, constructed from the current workflow state at commit time.

- **Commit Message Source Priority**: The deterministic order in which the system resolves the final commit message: (1) `--commit-message` CLI argument (verbatim, no template), (2) template rendering
  from `.agdt/config/commit-template.j2`, (3) raw `commit_message` state key fallback.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After implementation, 100% of `agdt-setup` executions in repositories without an existing commit template MUST result in the default template being created at the correct path, verified
  by running setup in 10 fresh repository contexts and confirming file existence and correct content.

- **SC-002**: Template rendering with all variables resolved MUST produce output that exactly matches the expected conventional-commit format in every unit test case for the rendering module,
  with each test asserting a specific expected output string (pass/fail), and 100% of those tests passing.

- **SC-003**: When any variable is unresolved, the system MUST emit exactly one warning per unresolved variable to stderr, achieving 100% accuracy in identifying missing variables across 20 distinct
  test scenarios with varying combinations of missing keys.

- **SC-004**: The fallback path (no template file exists) MUST produce identical commit messages to the current system behavior, verified by running the existing git command test suite with the
  template file absent and observing zero test failures.

- **SC-005**: New code MUST achieve 100% branch coverage as measured by `agdt-test-file` targeting each new source module, consistent with the repository's CI enforcement policy.

- **SC-006**: Template rendering latency MUST remain below 50 milliseconds in the p99 case when measured across 1000 renders with a fully-populated 5-variable template, ensuring no perceptible impact
  on the commit workflow responsiveness.

---
*Generated by Copilot SDK (claude-opus-4.6)*
