# Quickstart: Persist Commit Params and Rendered Messages to State

## 1) Execute a commit with a multi-line message

```bash
agdt-set commit_message $'feat([#1832](https://github.com/ayaiayorg/agentic-devtools/issues/1832)): persist commit metadata\n\n- add persistence\n\n[#1832](https://github.com/ayaiayorg/agentic-devtools/issues/1832)'
agdt-git-save-work
agdt-task-wait
```

## 2) Verify persisted values

```bash
agdt-get commit_message_title
agdt-get git.last_commit_title
agdt-get git.last_commit_message
agdt-get git.last_commit_body
```

Expected:

- `commit_message_title` and `git.last_commit_title` equal the first line.
- `git.last_commit_message` contains the full message.
- `git.last_commit_body` contains body/footer content (or `""` for title-only).

## 3) Verify fallback behavior

```bash
agdt-delete commit_message
agdt-git-save-work
agdt-task-wait
```

When `commit_message` is absent/empty and no `--commit-message` argument is provided,
`agdt-git-save-work` should reuse `git.last_commit_message`.
