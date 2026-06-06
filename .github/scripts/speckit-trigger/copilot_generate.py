#!/usr/bin/env python3
"""Copilot SDK wrapper for SpecKit spec generation.

Reads a prompt from stdin, sends it to the Copilot SDK with a configurable
model, and prints the assistant's response to stdout.

Environment Variables:
    COPILOT_GITHUB_TOKEN  - Required. Provided by the workflow via secrets.COPILOT_GITHUB_TOKEN.
    COPILOT_MODEL         - Optional. Model to use (default: claude-opus-4.6).
    COPILOT_TIMEOUT       - Optional. Seconds to wait for a response (default: 600).
                            Heavy phases (Plan, Tasks, Analyze) may need 900s or more.

Exit Codes:
    0 - Success (spec content written to stdout)
    1 - Failure (error message written to stderr)
"""

import asyncio
import os
import subprocess
import sys

try:
    from copilot import CopilotClient
    from copilot.session import PermissionHandler
except Exception as exc:
    pip_show = subprocess.run(
        [sys.executable, "-m", "pip", "show", "github-copilot-sdk"],
        capture_output=True,
        text=True,
        check=False,
    )
    pip_show_wrong = subprocess.run(
        [sys.executable, "-m", "pip", "show", "copilot"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Error: Copilot SDK import failed: {exc}", file=sys.stderr)
    sdk_info = (pip_show.stdout or pip_show.stderr or "").strip() or "(not installed)"
    wrong_info = (pip_show_wrong.stdout or pip_show_wrong.stderr or "").strip() or "(not installed)"
    print(f"pip show github-copilot-sdk:\n{sdk_info}", file=sys.stderr)
    print(f"pip show copilot:\n{wrong_info}", file=sys.stderr)
    if wrong_info != "(not installed)" and "Package(s) not found" not in wrong_info:
        print("⚠ Conflicting 'copilot' package detected (it may shadow github-copilot-sdk).", file=sys.stderr)
    print(
        "Ensure 'github-copilot-sdk' is installed and no conflicting 'copilot' package is present.",
        file=sys.stderr,
    )
    sys.exit(1)


async def main() -> int:
    prompt = sys.stdin.read()
    if not prompt.strip():
        print("Error: empty prompt on stdin", file=sys.stderr)
        return 1

    model = os.environ.get("COPILOT_MODEL", "claude-opus-4.6")
    token = os.environ.get("COPILOT_GITHUB_TOKEN", "")
    timeout_str = os.environ.get("COPILOT_TIMEOUT", "600")
    try:
        timeout = int(timeout_str)
        if timeout <= 0:
            raise ValueError("timeout must be positive")
    except ValueError:
        print(
            f"Error: COPILOT_TIMEOUT must be a positive integer (got {timeout_str!r})",
            file=sys.stderr,
        )
        return 1
    if not token:
        print(
            "Error: COPILOT_GITHUB_TOKEN environment variable is required"
            " (provided by workflow via secrets.COPILOT_GITHUB_TOKEN)",
            file=sys.stderr,
        )
        return 1

    client = None
    session = None
    try:
        client = CopilotClient(github_token=token)
        await client.start()

        try:
            session = await client.create_session(
                model=model,
                on_permission_request=PermissionHandler.approve_all,
                infinite_sessions={"enabled": False},
                github_token=token,
            )
        except TypeError as exc:
            if "unexpected keyword argument" not in str(exc) or "github_token" not in str(exc):
                raise
            # Fallback for SDK versions that don't accept github_token kwarg
            print(
                "Warning: create_session() does not accept github_token; "
                "falling back to session without explicit token.",
                file=sys.stderr,
            )
            session = await client.create_session(
                model=model,
                on_permission_request=PermissionHandler.approve_all,
                infinite_sessions={"enabled": False},
            )

        content_parts: list[str] = []
        received_events: list[str] = []
        error_messages: list[str] = []
        done = asyncio.Event()

        def on_event(event):
            event_type = event.type.value
            received_events.append(event_type)
            if event_type == "assistant.message":
                content_parts.append(event.data.content)
            elif event_type == "session.idle":
                done.set()
            elif event_type in ("error", "session.error", "assistant.error"):
                msg = getattr(event.data, "message", None) or str(event.data)
                error_messages.append(f"{event_type}: {msg}")
                done.set()

        session.on(on_event)
        await session.send(prompt)

        try:
            await asyncio.wait_for(done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            print(f"Error: Copilot SDK response timed out after {timeout}s", file=sys.stderr)
            print(f"Events received before timeout: {received_events}", file=sys.stderr)
            return 1

        if error_messages:
            print(
                f"Error: Copilot SDK returned error(s): {'; '.join(error_messages)}",
                file=sys.stderr,
            )
            return 1

        content = content_parts[-1] if content_parts else ""
        if not content.strip():
            print("Error: empty response from Copilot SDK", file=sys.stderr)
            print(f"Events received: {received_events}", file=sys.stderr)
            print(
                f"Model: {model}, Prompt length: {len(prompt)} chars",
                file=sys.stderr,
            )
            return 1

        sys.stdout.write(content)
        return 0

    except Exception as exc:
        print(f"Error: Copilot SDK call failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if session is not None:
            try:
                await session.disconnect()
            except Exception as exc:
                print(
                    f"Warning: failed to disconnect Copilot session: {exc}",
                    file=sys.stderr,
                )
        if client is not None:
            try:
                await client.stop()
            except Exception as exc:
                print(
                    f"Warning: failed to stop Copilot client: {exc}",
                    file=sys.stderr,
                )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
