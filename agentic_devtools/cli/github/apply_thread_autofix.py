"""Apply GitHub Copilot review suggestions to a PR.

Fetches suggestion data from embedded React partial JSON in the PR
changes page, applies diffs via the GitHub Contents API, then replies
to each applied comment with a resolution message and resolves the thread.

Handles multiple suggestions including conflict detection when applying
one suggestion makes another inapplicable (overlapping hunk ranges).

STABILITY NOTE: This module scrapes GitHub's internal page HTML to extract
suggestion data from embedded React partial JSON. The expected data
structure is:

    <script data-target="react-partial.embeddedData">
    {"props":{"comment":{"databaseId":N,"automatedComment":{
      "suggestionState":"present",
      "suggestion":{"diffEntries":[{"path":"...","diffLines":[...]}]}
    }}}}

If GitHub changes this format, the _fetch_suggestions_from_page function
will return an empty list and log diagnostic details to stderr. Look for
"[SCRAPE-FORMAT]" markers in logs to diagnose format changes.
"""

from __future__ import annotations

import base64
import json
import re
import sys
import time

import requests

from ..subprocess_utils import run_safe

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REACT_PARTIAL_RE = re.compile(
    r'<script type="application/json" data-target="react-partial\.embeddedData">'
    r"(.*?)</script>",
    re.DOTALL,
)

_HUNK_HEADER_RE = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 3

_RESOLUTION_REPLY_TEMPLATE = """\
<!-- agdt:resolution-tier:autofix-suggestion-applied -->
✅ **Thread resolved** [high]

**Tier**: autofix suggestion was applied
**Rationale**: The autofix suggestion from the copilot code review was applied — the commented code has been modified.

**HEAD**: [{commit_hash_short}](https://github.com/{repo}/commit/{commit_hash})\
"""

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------


def _log(msg: str, *, tag: str = "INFO") -> None:
    """Log a structured message to stderr for diagnostics."""
    print(f"[agdt-apply-pr-thread-autofix-suggestions:github][{tag}] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def _get_gh_token() -> str:
    result = run_safe(
        ["gh", "auth", "token"],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        _log(f"gh auth token failed: {result.stderr.strip()}", tag="ERROR")
        sys.exit(1)
    return result.stdout.strip()


def _get_pr_head_branch(repo: str, pr_number: int) -> str:
    result = run_safe(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".head.ref"],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        _log(f"Failed to get PR head branch: {result.stderr.strip()}", tag="ERROR")
        sys.exit(1)
    return result.stdout.strip()


def _get_pr_head_sha(repo: str, pr_number: int) -> str:
    result = run_safe(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".head.sha"],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        _log(f"Failed to get PR head SHA: {result.stderr.strip()}", tag="ERROR")
        sys.exit(1)
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Suggestion scraping (fragile — depends on GitHub HTML format)
# ---------------------------------------------------------------------------


_INCLUDE_FRAGMENT_RE = re.compile(
    r'<include-fragment[^>]*src="([^"]+/diffs\?[^"]+)"',
)


def _extract_nested(data: dict, keys: list[str]):
    """Safely traverse nested dict keys, returning None if any is missing."""
    current: object = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def _fetch_all_page_html(repo: str, pr_number: int, token: str) -> str:
    """Fetch the PR changes page HTML including lazy-loaded diff fragments.

    GitHub progressively loads large diffs via <include-fragment> elements.
    This function fetches the main page, finds any lazy-load URLs, fetches
    them too, and concatenates all HTML for parsing.
    """
    from html import unescape

    base_url = f"https://github.com/{repo}/pull/{pr_number}/changes"
    _log(f"Fetching PR page: {base_url}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/html",
    }

    resp = requests.get(base_url, headers=headers, timeout=60)
    if resp.status_code != 200:
        _log(
            f"PR page returned HTTP {resp.status_code} (expected 200). URL: {base_url}",
            tag="ERROR",
        )
        return ""

    all_html = resp.text
    _log(f"Main page fetched OK ({len(all_html)} bytes)")

    # Find lazy-loaded diff fragments
    fragment_matches = _INCLUDE_FRAGMENT_RE.findall(all_html)
    if fragment_matches:
        _log(f"Found {len(fragment_matches)} lazy-loaded diff fragment(s)")
        for frag_url in fragment_matches:
            # Unescape HTML entities in the URL (&amp; → &)
            frag_url_clean = unescape(frag_url)
            if not frag_url_clean.startswith("http"):
                frag_url_clean = f"https://github.com{frag_url_clean}"
            _log(f"Fetching lazy fragment: {frag_url_clean[:100]}...")
            frag_resp = requests.get(frag_url_clean, headers=headers, timeout=60)
            if frag_resp.status_code == 200:
                all_html += frag_resp.text
                _log(f"  Fragment fetched OK ({len(frag_resp.text)} bytes)")
            else:
                _log(
                    f"  Fragment returned HTTP {frag_resp.status_code}",
                    tag="WARN",
                )

    return all_html


def _fetch_suggestions_from_page(repo: str, pr_number: int, token: str) -> list[dict]:
    """Fetch and parse suggestion data from the PR changes page HTML.

    Returns list of dicts with keys: comment_id, diff_entries, severity.

    Fetches both the main page and any lazy-loaded diff fragments to
    handle PRs with large diffs that are progressively loaded.

    Logs detailed diagnostics under [SCRAPE-FORMAT] tag if the expected
    HTML structure is not found.
    """
    all_html = _fetch_all_page_html(repo, pr_number, token)
    if not all_html:
        return []

    # Find all React partial scripts
    matches = list(_REACT_PARTIAL_RE.finditer(all_html))
    if not matches:
        _log(
            "[SCRAPE-FORMAT] No react-partial.embeddedData scripts found. "
            "GitHub may have changed their frontend rendering. "
            'Expected: <script type="application/json" '
            'data-target="react-partial.embeddedData">',
            tag="ERROR",
        )
        return []

    _log(f"Found {len(matches)} react-partial scripts (across all pages)")

    suggestions = []
    partials_with_comments = 0
    partials_with_automated = 0

    for match in matches:
        raw = match.group(1)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        comment = _extract_nested(data, ["props", "comment"])
        if comment is None:
            continue
        partials_with_comments += 1

        automated = comment.get("automatedComment")
        if not automated:
            continue
        partials_with_automated += 1

        suggestion_state = automated.get("suggestionState")
        if suggestion_state != "present":
            _log(
                f"Comment {comment.get('databaseId')}: suggestionState={suggestion_state!r} (skipping, need 'present')"
            )
            continue

        suggestion = automated.get("suggestion")
        if not suggestion:
            _log(
                f"[SCRAPE-FORMAT] Comment {comment.get('databaseId')}: "
                "has suggestionState='present' but no 'suggestion' key. "
                f"Available keys in automatedComment: {list(automated.keys())}",
                tag="WARN",
            )
            continue

        diff_entries = suggestion.get("diffEntries")
        if not diff_entries:
            _log(
                f"[SCRAPE-FORMAT] Comment {comment.get('databaseId')}: "
                "suggestion exists but 'diffEntries' is empty/missing. "
                f"Available keys in suggestion: {list(suggestion.keys())}",
                tag="WARN",
            )
            continue

        severity = automated.get("severity", "medium")

        suggestions.append(
            {
                "comment_id": comment.get("databaseId"),
                "node_id": comment.get("id"),
                "diff_entries": diff_entries,
                "severity": severity,
            }
        )

    _log(
        f"Parsing summary: {len(matches)} partials, "
        f"{partials_with_comments} with comments, "
        f"{partials_with_automated} with automatedComment, "
        f"{len(suggestions)} with applicable suggestions"
    )

    if partials_with_automated > 0 and len(suggestions) == 0 and partials_with_comments == partials_with_automated:
        # All automated comments found but none have applicable suggestions.
        # This is normal if suggestions were already applied or dismissed.
        _log(
            "All automated comments found but none have "
            "suggestionState='present' — suggestions may have already been "
            "applied or dismissed."
        )

    return suggestions


# ---------------------------------------------------------------------------
# Diff application with conflict detection
# ---------------------------------------------------------------------------


def _split_into_hunks(diff_lines: list[dict]) -> list[list[dict]]:
    """Split a diff_lines array into separate hunks (each starting with a HUNK line)."""
    hunks: list[list[dict]] = []
    current: list[dict] = []
    for dl in diff_lines:
        if dl["type"] == "HUNK":
            if current:
                hunks.append(current)
            current = [dl]
        else:
            current.append(dl)
    if current:
        hunks.append(current)
    return hunks


def _get_hunk_range(diff_lines: list[dict]) -> tuple[int, int] | None:
    """Extract the full (start_line, end_line) 0-indexed range spanning all hunks."""
    start = None
    end = None
    for dl in diff_lines:
        if dl["type"] == "HUNK":
            m = _HUNK_HEADER_RE.match(dl["text"])
            if m:
                hunk_start = int(m.group(1)) - 1  # 0-indexed
                hunk_count = int(m.group(2)) if m.group(2) is not None else 1
                if start is None or hunk_start < start:
                    start = hunk_start
                hunk_end = hunk_start + hunk_count
                if end is None or hunk_end > end:
                    end = hunk_end
    if start is not None and end is not None:
        return (start, end)
    return None


def _ranges_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Check if two (start, end) ranges overlap."""
    return a[0] < b[1] and b[0] < a[1]


def _apply_single_hunk(original_lines: list[str], hunk: list[dict]) -> tuple[list[str], bool]:
    """Apply a single hunk to file content.

    Returns (new_lines, success). success=False if context lines
    don't match (indicating the file has changed and the diff is stale).
    """
    hunk_header = hunk[0]
    if hunk_header["type"] != "HUNK":
        return original_lines, False

    match = _HUNK_HEADER_RE.match(hunk_header["text"])
    if not match:
        return original_lines, False

    orig_start = int(match.group(1)) - 1  # 0-indexed

    # Verify context lines match before applying
    check_idx = orig_start
    for dl in hunk[1:]:
        if dl["type"] in ("CONTEXT", "DELETION"):
            if check_idx >= len(original_lines):
                _log(
                    f"Context verification failed: line {check_idx + 1} "
                    f"is beyond file length ({len(original_lines)} lines)",
                    tag="CONFLICT",
                )
                return original_lines, False
            expected = dl["text"]
            actual = original_lines[check_idx]
            if expected != actual:
                _log(
                    f"Context verification failed at line {check_idx + 1}: expected {expected!r}, got {actual!r}",
                    tag="CONFLICT",
                )
                return original_lines, False
            check_idx += 1
        elif dl["type"] == "ADDITION":
            pass  # additions don't consume original lines

    # Context verified — apply the hunk
    new_region_lines = []
    orig_consumed = 0

    for dl in hunk[1:]:
        if dl["type"] == "CONTEXT":
            new_region_lines.append(dl["text"])
            orig_consumed += 1
        elif dl["type"] == "ADDITION":
            new_region_lines.append(dl["text"])
        elif dl["type"] == "DELETION":
            orig_consumed += 1

    result = original_lines[:orig_start] + new_region_lines + original_lines[orig_start + orig_consumed :]
    return result, True


def _apply_diff_to_content(original_lines: list[str], diff_lines: list[dict]) -> tuple[list[str], bool]:
    """Apply a suggestion diff (possibly multi-hunk) to file content.

    Splits the diff into individual hunks and applies them in reverse
    order (bottom-up) so that earlier hunks' line numbers aren't
    invalidated by later hunks' insertions/deletions.

    Returns (new_lines, success). success=False if any hunk fails
    context verification.
    """
    hunks = _split_into_hunks(diff_lines)
    if not hunks:
        return original_lines, False

    _log(f"Applying diff with {len(hunks)} hunk(s)")

    # Sort hunks by start position descending (apply bottom-up)
    def _hunk_start_pos(hunk: list[dict]) -> int:
        m = _HUNK_HEADER_RE.match(hunk[0]["text"])
        return int(m.group(1)) if m else 0

    hunks_sorted = sorted(hunks, key=_hunk_start_pos, reverse=True)

    lines = original_lines
    for hunk in hunks_sorted:
        lines, success = _apply_single_hunk(lines, hunk)
        if not success:
            return original_lines, False

    return lines, True


# ---------------------------------------------------------------------------
# File mutation via Contents API
# ---------------------------------------------------------------------------


def _get_file_content_and_sha(repo: str, path: str, branch: str) -> tuple[str, str]:
    """Fetch file content and SHA from the Contents API."""
    result = run_safe(
        [
            "gh",
            "api",
            f"repos/{repo}/contents/{path}?ref={branch}",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        _log(f"Failed to fetch file {path}: {result.stderr.strip()}", tag="ERROR")
        raise RuntimeError(f"Failed to fetch file {path}")

    data = json.loads(result.stdout)
    file_sha = data["sha"]
    content_b64 = data["content"]
    content = base64.b64decode(content_b64).decode("utf-8")
    return content, file_sha


def _update_file_via_api(
    repo: str,
    path: str,
    content: str,
    file_sha: str,
    branch: str,
    message: str,
) -> str:
    """Update a file via the Contents API. Returns the new commit SHA.

    Uses stdin (--input) for the request body to avoid Windows command
    line length limits with large base64-encoded file content.
    """
    import tempfile

    content_b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    payload = json.dumps(
        {
            "message": message,
            "content": content_b64,
            "sha": file_sha,
            "branch": branch,
        }
    )

    # Write payload to a temp file to avoid command line length limits
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(payload)
        temp_path = f.name

    try:
        result = run_safe(
            [
                "gh",
                "api",
                "--method",
                "PUT",
                f"repos/{repo}/contents/{path}",
                "--input",
                temp_path,
            ],
            capture_output=True,
            text=True,
            shell=False,
        )
    finally:
        import os

        os.unlink(temp_path)

    if result.returncode != 0:
        _log(f"Failed to update file {path}: {result.stderr.strip()}", tag="ERROR")
        raise RuntimeError(f"Failed to update file {path}")

    data = json.loads(result.stdout)
    return data["commit"]["sha"]


# ---------------------------------------------------------------------------
# Reply and resolve
# ---------------------------------------------------------------------------


def _post_reply_to_comment(repo: str, pr_number: int, comment_id: int, body: str) -> bool:
    """Post a reply to a PR review comment. Returns success."""
    result = run_safe(
        [
            "gh",
            "api",
            f"repos/{repo}/pulls/{pr_number}/comments/{comment_id}/replies",
            "--raw-field",
            f"body={body}",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        _log(
            f"Failed to post reply to comment {comment_id}: {result.stderr.strip()}",
            tag="WARN",
        )
        return False
    return True


def _resolve_thread_for_comment(pr_number: int, repo: str, comment_id: int) -> bool:
    """Resolve the review thread containing the given comment."""
    owner, repo_name = repo.split("/")

    # Fetch threads with cursor-based pagination to handle PRs with >100 threads
    _THREADS_QUERY = """
query($owner: String!, $repoName: String!, $prNumber: Int!, $cursor: String) {
  repository(owner: $owner, name: $repoName) {
    pullRequest(number: $prNumber) {
      reviewThreads(first: 50, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first: 100) {
            nodes { databaseId }
          }
        }
      }
    }
  }
}
"""

    thread_id = None
    cursor: str | None = None

    while thread_id is None:  # pragma: no branch – always exits via break
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={_THREADS_QUERY}",
            "-f",
            f"owner={owner}",
            "-f",
            f"repoName={repo_name}",
            "-F",
            f"prNumber={pr_number}",
        ]
        if cursor is not None:
            cmd += ["-f", f"cursor={cursor}"]
        result = run_safe(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            _log(
                f"Failed to fetch threads for comment {comment_id}: {result.stderr.strip()}",
                tag="WARN",
            )
            return False

        try:
            data = json.loads(result.stdout)
            threads_page = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            threads = threads_page["nodes"]
            page_info = threads_page["pageInfo"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            _log(f"Failed to parse threads response: {exc}", tag="WARN")
            return False

        # Find the thread containing this comment on this page
        for thread in threads:
            if thread.get("isResolved"):
                continue
            comments = thread.get("comments", {}).get("nodes", [])
            for c in comments:
                if c.get("databaseId") == comment_id:
                    thread_id = thread["id"]
                    break
            if thread_id:
                break

        if thread_id:
            break

        if not page_info.get("hasNextPage"):
            break
        cursor = page_info["endCursor"]

    if not thread_id:
        _log(f"No unresolved thread found for comment {comment_id}", tag="WARN")
        return False

    # Resolve it
    _RESOLVE_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { id isResolved }
  }
}
"""
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={_RESOLVE_MUTATION}",
        "-f",
        f"threadId={thread_id}",
    ]
    result = run_safe(cmd, capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        _log(
            f"Failed to resolve thread {thread_id}: {result.stderr.strip()}",
            tag="WARN",
        )
        return False

    try:
        resp = json.loads(result.stdout)
        resolved = resp["data"]["resolveReviewThread"]["thread"]["isResolved"]
        return bool(resolved)
    except (json.JSONDecodeError, KeyError, TypeError):
        _log(f"Unexpected resolve response for thread {thread_id}", tag="WARN")
        return False


def _reply_and_resolve_comments(
    repo: str,
    pr_number: int,
    applied_suggestions: list[dict],
    commit_hash: str,
) -> dict:
    """Post resolution replies and resolve threads for applied suggestions."""
    commit_hash_short = commit_hash[:12]

    replied = 0
    resolved = 0
    failed_replies = []
    failed_resolves = []

    for suggestion in applied_suggestions:
        comment_id = suggestion["comment_id"]

        body = _RESOLUTION_REPLY_TEMPLATE.format(
            commit_hash_short=commit_hash_short,
            commit_hash=commit_hash,
            repo=repo,
        )

        _log(f"Posting resolution reply to comment {comment_id}")
        if _post_reply_to_comment(repo, pr_number, comment_id, body):
            replied += 1
        else:
            failed_replies.append(comment_id)

        # Small delay to avoid rate limiting
        time.sleep(0.5)

        _log(f"Resolving thread for comment {comment_id}")
        if _resolve_thread_for_comment(pr_number, repo, comment_id):
            resolved += 1
        else:
            failed_resolves.append(comment_id)

    return {
        "replied": replied,
        "resolved": resolved,
        "failed_replies": failed_replies,
        "failed_resolves": failed_resolves,
    }


# ---------------------------------------------------------------------------
# Core orchestrator
# ---------------------------------------------------------------------------


def apply_pr_suggestions(
    pr_number: int,
    repo: str,
    comment_ids: list[int] | None = None,
    message: str = "Apply suggestions from code review",
    resolve: bool = True,
) -> dict:
    """Apply Copilot review suggestions to the PR branch.

    Handles multiple suggestions with conflict detection. When applying
    one suggestion shifts line numbers, subsequent suggestions are
    verified via context-line matching before application.

    Returns dict with applied/skipped counts, commit SHA, changed files,
    and thread resolution results.
    """
    _log(f"Starting: PR #{pr_number}, repo={repo}")

    token = _get_gh_token()
    branch = _get_pr_head_branch(repo, pr_number)
    _log(f"PR head branch: {branch}")

    # Filter target comment IDs (if specified)
    target_comment_ids = set(comment_ids) if comment_ids else None

    # Iterative application loop: apply what we can, re-fetch for conflicts
    max_iterations = _MAX_RETRIES + 1  # 1 initial pass + _MAX_RETRIES retry passes
    new_sha = None
    files_changed: list[str] = []
    all_applied: list[dict] = []
    final_skipped: list[dict] = []
    resolved_total = 0
    replied_total = 0
    failed_replies: list[int] = []
    failed_resolves: list[int] = []

    for iteration in range(max_iterations):
        suggestions = _fetch_suggestions_from_page(repo, pr_number, token)

        if not suggestions:
            if iteration == 0:
                _log("No suggestions found on PR page")
            break

        if iteration == 0:
            _log(f"Found {len(suggestions)} suggestions on page")

        # Filter by target comment IDs
        if target_comment_ids:
            # Exclude already-applied comments from this iteration
            applied_ids = {e["comment_id"] for e in all_applied}
            suggestions = [
                s for s in suggestions if s["comment_id"] in target_comment_ids and s["comment_id"] not in applied_ids
            ]
        else:
            # Exclude already-applied
            applied_ids = {e["comment_id"] for e in all_applied}
            suggestions = [s for s in suggestions if s["comment_id"] not in applied_ids]

        if not suggestions:
            break

        if iteration > 0:
            _log(f"Retry iteration {iteration + 1}: {len(suggestions)} suggestions remaining")

        # Group suggestions by file path
        file_suggestions: dict[str, list[dict]] = {}
        for suggestion in suggestions:
            for entry in suggestion["diff_entries"]:
                path = entry["path"]
                if path not in file_suggestions:
                    file_suggestions[path] = []
                file_suggestions[path].append(
                    {
                        "comment_id": suggestion["comment_id"],
                        "diff_lines": entry["diffLines"],
                        "severity": suggestion.get("severity", "medium"),
                    }
                )

        # Apply diffs per file
        iteration_applied: list[dict] = []
        iteration_skipped: list[dict] = []

        for path, entries in file_suggestions.items():
            _log(f"Processing file: {path} ({len(entries)} suggestions)")

            try:
                content, file_sha = _get_file_content_and_sha(repo, path, branch)
            except RuntimeError:
                for entry in entries:
                    iteration_skipped.append(entry)
                continue

            lines = content.split("\n")

            # Sort by hunk start position descending
            def _hunk_start(entry: dict) -> int:
                for dl in entry["diff_lines"]:
                    if dl["type"] == "HUNK":
                        m = _HUNK_HEADER_RE.match(dl["text"])
                        if m:
                            return int(m.group(1))
                return 0

            entries_sorted = sorted(entries, key=_hunk_start, reverse=True)

            # Detect overlapping hunks
            ranges = []
            for entry in entries_sorted:
                r = _get_hunk_range(entry["diff_lines"])
                if r:
                    ranges.append((r, entry))

            for i, (range_a, entry_a) in enumerate(ranges):
                for j, (range_b, entry_b) in enumerate(ranges):
                    if i >= j:
                        continue
                    if _ranges_overlap(range_a, range_b):
                        _log(
                            f"Overlapping hunks detected in {path}: "
                            f"comment {entry_a['comment_id']} "
                            f"(lines {range_a[0] + 1}-{range_a[1]}) overlaps with "
                            f"comment {entry_b['comment_id']} "
                            f"(lines {range_b[0] + 1}-{range_b[1]}). "
                            "Will retry conflicted suggestions with fresh diffs.",
                            tag="WARN",
                        )

            # Apply each diff with context verification
            for entry in entries_sorted:
                new_lines, success = _apply_diff_to_content(lines, entry["diff_lines"])
                if success:
                    lines = new_lines
                    iteration_applied.append(entry)
                    _log(f"Applied suggestion from comment {entry['comment_id']}")
                else:
                    iteration_skipped.append(entry)
                    _log(
                        f"Skipped suggestion from comment {entry['comment_id']} "
                        "(context mismatch — will retry with fresh diff)",
                        tag="CONFLICT",
                    )

            # Commit applied suggestions for this file
            file_applied = [e for e in entries_sorted if e in iteration_applied]
            if file_applied:
                new_content = "\n".join(lines)
                try:
                    new_sha = _update_file_via_api(repo, path, new_content, file_sha, branch, message)
                    if path not in files_changed:
                        files_changed.append(path)
                    _log(f"File updated: {path} (commit: {new_sha[:12]})")

                    # Reply and resolve immediately
                    if resolve:
                        seen_ids = set()
                        deduped = []
                        for entry in file_applied:
                            if entry["comment_id"] not in seen_ids:
                                seen_ids.add(entry["comment_id"])
                                deduped.append(entry)
                        file_resolution = _reply_and_resolve_comments(repo, pr_number, deduped, new_sha)
                        resolved_total += file_resolution["resolved"]
                        replied_total += file_resolution["replied"]
                        failed_replies.extend(file_resolution["failed_replies"])
                        failed_resolves.extend(file_resolution["failed_resolves"])
                except RuntimeError:
                    for entry in file_applied:
                        iteration_applied.remove(entry)
                        iteration_skipped.append(entry)

        all_applied.extend(iteration_applied)
        # Always update final_skipped so the last iteration's conflicts are
        # captured even when the loop exhausts max_iterations with partial progress.
        final_skipped = iteration_skipped

        # If nothing was skipped due to conflicts, we're done
        if not iteration_skipped:
            break

        # If nothing was applied this iteration, stop retrying (avoid infinite loop)
        if not iteration_applied:
            _log(
                f"No suggestions applied in iteration {iteration + 1} — stopping retries",
                tag="WARN",
            )
            break

        # There were conflicts — wait before re-fetching so GitHub has time to
        # regenerate suggestion diffs against the new HEAD, then retry.
        _log(
            f"Iteration {iteration + 1} complete: "
            f"applied {len(iteration_applied)}, "
            f"skipped {len(iteration_skipped)} (waiting {_RETRY_DELAY_SECONDS}s then retrying with fresh diffs)"
        )
        time.sleep(_RETRY_DELAY_SECONDS)

    _log(f"Application complete: {len(all_applied)} applied, {len(final_skipped)} skipped")

    resolution_result = None
    if resolved_total > 0 or replied_total > 0 or failed_replies or failed_resolves:
        resolution_result = {
            "replied": replied_total,
            "resolved": resolved_total,
            "failed_replies": failed_replies,
            "failed_resolves": failed_resolves,
        }
        _log(f"Resolution: {replied_total} replied, {resolved_total} resolved")

    conflict_comment_ids = [e["comment_id"] for e in final_skipped]

    return {
        "applied": len(all_applied),
        "skipped": len(final_skipped),
        "conflict_comment_ids": conflict_comment_ids,
        "commit": new_sha,
        "files_changed": files_changed,
        "resolution": resolution_result,
    }
