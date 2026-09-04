#!/usr/bin/env python
"""Stateless Hermes-Sol inference with no agent loop and no tool definitions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _get(value: Any, key: str, default: Any = None) -> Any:
    result = getattr(value, key, None)
    if result is None and isinstance(value, dict):
        result = value.get(key, default)
    return default if result is None else result


def _run_stateless_codex_response(client: Any, resolved: str, user_input: str) -> tuple[str, str, str]:
    """Call the provider Responses endpoint without the identity-dropping chat shim."""
    real_client = getattr(client, "_real_client", None)
    if real_client is None or not hasattr(real_client, "responses"):
        raise RuntimeError("openai-codex client did not expose the provider Responses endpoint")
    stream = real_client.responses.create(
        model=resolved,
        instructions="You are a stateless blind coder. No tools are defined. Return only the requested answer.",
        input=[{"role": "user", "content": user_input}],
        store=False,
        stream=True,
    )
    try:
        if hasattr(stream, "output"):
            final = stream
        else:
            from agent.codex_runtime import _consume_codex_event_stream
            final = _consume_codex_event_stream(stream, model=resolved)
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()
    text_parts: list[str] = []
    for item in (_get(final, "output", []) or []):
        if _get(item, "type") != "message":
            continue
        for part in (_get(item, "content", []) or []):
            if _get(part, "type") in {"output_text", "text"}:
                text_parts.append(str(_get(part, "text", "")))
    content = "".join(text_parts).strip()
    if not content:
        content = str(_get(final, "output_text", "") or "").strip()
    request_id = str(_get(final, "id", "") or "")
    response_model = str(_get(final, "model", "") or resolved)
    if not content:
        raise RuntimeError("empty provider response")
    if not request_id:
        raise RuntimeError("provider response did not include a request id")
    return content, response_model, request_id


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
    content, response_model, request_id = _run_stateless_codex_response(client, resolved, user_input)
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
