#!/usr/bin/env python
"""Stateless Hermes-Sol inference with no agent loop and no tool definitions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args()
    hermes_source = Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent"
    if str(hermes_source) not in sys.path:
        sys.path.insert(0, str(hermes_source))
    from agent.auxiliary_client import resolve_provider_client

    client, resolved = resolve_provider_client("openai-codex", model=args.model)
    if client is None or not resolved:
        raise RuntimeError("openai-codex provider/model could not be resolved")
    user_input = sys.stdin.buffer.read().decode("utf-8")
    response = client.chat.completions.create(
        model=resolved,
        messages=[
            {"role": "system", "content": "You are a stateless blind coder. No tools are defined. Return only the requested answer."},
            {"role": "user", "content": user_input},
        ],
        tools=[],
        tool_choice="none",
    )
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content:
        raise RuntimeError("empty provider response")
    response_model = str(getattr(response, "model", "") or resolved)
    request_id = str(getattr(response, "id", "") or "")
    if not request_id:
        raise RuntimeError("provider response did not include a request id")
    envelope = {
        "type": "hermes-sol-result",
        "result": content,
        "launch_nonce": args.nonce,
        "provider": "openai-codex",
        "resolved_model": response_model,
        "provider_request_id": request_id,
        "session_id": request_id,
        "resumed": False,
        "runtime_controls": {
            "tools_sent": 0,
            "tool_choice": "none",
            "mcp_servers": 0,
            "session_persistence": False,
            "agent_loop": False,
        },
    }
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
