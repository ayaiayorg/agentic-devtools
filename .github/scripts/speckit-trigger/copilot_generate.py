#!/usr/bin/env python3
"""Copilot SDK wrapper for SpecKit spec generation.

Reads a prompt from stdin, sends it to the Copilot SDK with a configurable
model, and prints the assistant's response to stdout.

Environment Variables:
    COPILOT_GITHUB_TOKEN  - Required. Fine-grained PAT with Copilot Requests: Read permission.
    COPILOT_MODEL         - Optional. Model to use (default: claude-opus-4.6).

Exit Codes:
    0 - Success (spec content written to stdout)
    1 - Failure (error message written to stderr)
"""

import asyncio
import os
import sys

from copilot import CopilotClient, PermissionHandler, SubprocessConfig


async def main() -> int:
    prompt = sys.stdin.read()
    if not prompt.strip():
        print("Error: empty prompt on stdin", file=sys.stderr)
        return 1

    model = os.environ.get("COPILOT_MODEL", "claude-opus-4.6")
    token = os.environ.get("COPILOT_GITHUB_TOKEN", "")
    if not token:
        print("Error: COPILOT_GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    client = None
    session = None
    try:
        client = CopilotClient(SubprocessConfig(github_token=token))
        await client.start()

        session = await client.create_session(
            {
                "model": model,
                "on_permission_request": PermissionHandler.approve_all,
                "infinite_sessions": {"enabled": False},
            }
        )

        content = ""
        done = asyncio.Event()

        def on_event(event):
            nonlocal content
            if event.type.value == "assistant.message":
                content = event.data.content
            elif event.type.value == "session.idle":
                done.set()

        session.on(on_event)
        await session.send(prompt)

        try:
            await asyncio.wait_for(done.wait(), timeout=300)
        except asyncio.TimeoutError:
            print(
                "Error: Copilot SDK response timed out after 300s", file=sys.stderr
            )
            return 1

        if not content.strip():
            print("Error: empty response from Copilot SDK", file=sys.stderr)
            return 1

        sys.stdout.write(content)
        return 0

    except Exception as exc:
        print(f"Error: Copilot SDK call failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if session is not None:
            await session.disconnect()
        if client is not None:
            await client.stop()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
