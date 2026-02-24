# Commit Convention

This project uses [Conventional Commits v1.0.0](https://www.conventionalcommits.org) with
project-specific rules that make every commit traceable to a GitHub issue.

## Format

```text
type(scope): summary

body (optional)

footer
```

## Rules

### 1. Scope is mandatory — it must be a GitHub issue link

The scope is **never** optional. It must be a markdown link to the relevant GitHub issue(s).

```text
feat([#123](https://github.com/ayaiayorg/agentic-devtools/issues/123)): add webhook support
```

### 2. Footer must repeat the issue link(s)

The last line of the commit message must be the same issue link(s) from the scope.

```text
feat([#123](https://github.com/ayaiayorg/agentic-devtools/issues/123)): add webhook support

- Implemented webhook handler
- Added tests

[#123](https://github.com/ayaiayorg/agentic-devtools/issues/123)
```

### 3. Breaking changes use both `!` after scope and `BREAKING CHANGE:` footer

Use `!` immediately after the closing `)` of the scope, and start the footer with `BREAKING CHANGE:` followed by the issue link(s).

```text
feat([#123](https://github.com/ayaiayorg/agentic-devtools/issues/123))!: summary of issue

- detail part 1
- detail part 2

BREAKING CHANGE: [#123](https://github.com/ayaiayorg/agentic-devtools/issues/123)
```

### 4. Parent/child issue ordering

When a parent issue exists, it comes **first**, separated by `/`:

- In the scope: `parent/child` (no spaces around `/`)
- In the footer: `parent / child` (spaces around `/`)

```text
feat([#123](https://github.com/ayaiayorg/agentic-devtools/issues/123)/[#234](https://github.com/ayaiayorg/agentic-devtools/issues/234)): implement sub-feature

- Detail part 1
- Detail part 2

[#123](https://github.com/ayaiayorg/agentic-devtools/issues/123) / [#234](https://github.com/ayaiayorg/agentic-devtools/issues/234)
```

### 5. Multiple issues (no parent-child relationship)

Comma-separated, sorted in **ascending** order by issue number:

```text
feat([#123](https://github.com/ayaiayorg/agentic-devtools/issues/123), [#234](https://github.com/ayaiayorg/agentic-devtools/issues/234)): implement related features

- Detail part 1
- Detail part 2

[#123](https://github.com/ayaiayorg/agentic-devtools/issues/123), [#234](https://github.com/ayaiayorg/agentic-devtools/issues/234)
```

### 6. Ordering rules summary

- Parent issues always come **before** child issues
- Within the same level, lowest issue number comes **first** (ascending order)
- These rules apply to both the scope and the footer

### 7. Supported types

| Type | Purpose |
|------|---------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Changes that do not affect the meaning of the code |
| `refactor` | A code change that neither fixes a bug nor adds a feature |
| `perf` | A code change that improves performance |
| `test` | Adding missing tests or correcting existing tests |
| `build` | Changes that affect the build system or external dependencies |
| `ci` | Changes to CI configuration files and scripts |
| `chore` | Other changes that don't modify src or test files |
| `revert` | Reverts a previous commit |

## Examples

### Single issue

```text
fix([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): handle null values in PR thread API

- Added null guard in thread parser
- Updated unit tests

[#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)
```

### Parent + child issue

```text
feat([#10](https://github.com/ayaiayorg/agentic-devtools/issues/10)/[#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): implement webhook handler

- Added endpoint
- Wired up Jira notification

[#10](https://github.com/ayaiayorg/agentic-devtools/issues/10) / [#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)
```

### Multiple unrelated issues

```text
docs([#5](https://github.com/ayaiayorg/agentic-devtools/issues/5), [#12](https://github.com/ayaiayorg/agentic-devtools/issues/12)): update CONTRIBUTING and README

[#5](https://github.com/ayaiayorg/agentic-devtools/issues/5), [#12](https://github.com/ayaiayorg/agentic-devtools/issues/12)
```
