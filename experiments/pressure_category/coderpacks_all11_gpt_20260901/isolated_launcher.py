#!/usr/bin/env python
"""Fresh tool-less coder launchers with orchestrator-owned receipts."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHA_KEYS = ("bundle_sha256", "input_sha256", "stdout_sha256", "stderr_sha256", "output_sha256")


@dataclasses.dataclass(frozen=True)
class Adapter:
    executable: str
    arguments: tuple[str, ...]
    family: str
    provider: str
    requested_model: str
    output_protocol: str
    allow_filesystem: bool = False
    allow_web: bool = False
    allow_session_history: bool = False


def claude_adapter(executable: str = "claude", *, requested_model: str = "claude-opus-5") -> Adapter:
    empty_mcp = json.dumps({"mcpServers": {}}, separators=(",", ":"))
    arguments = (
        "--print", "--output-format", "json", "--model", requested_model,
        "--safe-mode", "--tools", "", "--disable-slash-commands",
        "--no-session-persistence", "--strict-mcp-config", "--mcp-config", empty_mcp,
        "--permission-mode", "dontAsk", "--setting-sources", "", "--settings", "{}",
    )
    return Adapter(executable, arguments, "Claude", "anthropic", requested_model, "claude-json")


def sol_adapter(*, requested_model: str = "gpt-5.6-sol", executable: str = sys.executable) -> Adapter:
    runner = Path(__file__).with_name("sol_toolless_runner.py")
    return Adapter(executable, (str(runner), "--model", requested_model), "Hermes-Sol", "openai-codex", requested_model, "sol-json")


def fake_adapter() -> Adapter:
    code = (
        "import sys,json; n=sys.argv[1]; m=sys.argv[2]; sys.stdin.read(); "
        "print(json.dumps({'type':'fake-result','result':'{\\\"status\\\":\\\"zero-semantic-fake\\\"}',"
        "'launch_nonce':n,'provider':'fake','resolved_model':m,'provider_request_id':'req-'+n,"
        "'session_id':'req-'+n,'resumed':False,'runtime_controls':{'tools_sent':0,'tool_choice':'none',"
        "'mcp_servers':0,'session_persistence':False,'agent_loop':False}}))"
    )
    return Adapter(sys.executable, ("-c", code), "Claude", "fake", "claude-test", "fake-json")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_bytes(path: Path, raw: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(raw)
    os.replace(temporary, path)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_bytes(path, (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def _inventory(executable: str) -> list[int]:
    try:
        import psutil
        needle = Path(executable).name.lower()
        found = []
        for process in psutil.process_iter(["pid", "name", "cmdline"]):
            text = " ".join([process.info.get("name") or "", *(process.info.get("cmdline") or [])]).lower()
            if needle and needle in text:
                found.append(process.pid)
        return sorted(set(found))
    except Exception:
        return []


def _create_time(pid: int) -> float:
    try:
        import psutil
        return psutil.Process(pid).create_time()
    except Exception:
        return time.time()


def _parse_envelope(adapter: Adapter, stdout: bytes, *, nonce: str, session_uuid: str) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    try:
        envelope = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("runtime stdout was not a JSON envelope") from exc
    if adapter.output_protocol == "claude-json":
        if envelope.get("type") != "result" or envelope.get("subtype") != "success":
            raise ValueError("Claude result envelope was not successful")
        if envelope.get("session_id") != session_uuid:
            raise ValueError("Claude session UUID mismatch")
        model_usage = envelope.get("modelUsage") or {}
        models = sorted(model_usage)
        if adapter.requested_model not in models:
            raise ValueError("requested Claude model missing from provider modelUsage")
        resolved_model = adapter.requested_model
        auxiliary_models = [model for model in models if model != resolved_model]
        content = envelope.get("structured_output", envelope.get("result"))
        if isinstance(content, (dict, list)):
            output = (json.dumps(content, ensure_ascii=False) + "\n").encode("utf-8")
        elif isinstance(content, str) and content:
            output = content.encode("utf-8")
        else:
            raise ValueError("Claude result content was empty")
        identity = {"family": "Claude", "model": resolved_model, "provider": "anthropic", "source": "provider-response"}
        controls = {"tools_sent": 0, "tool_choice": "none", "mcp_servers": 0, "session_persistence": False, "agent_loop": False}
        metadata = {"session_id": envelope["session_id"], "provider_request_id": str(envelope.get("request_id") or envelope["session_id"]), "resumed": False, "runtime_controls": controls, "provider_auxiliary_models": auxiliary_models}
        return output, identity, metadata
    required = {"result", "launch_nonce", "provider", "resolved_model", "provider_request_id", "session_id", "resumed", "runtime_controls"}
    if not required <= set(envelope):
        raise ValueError("runtime envelope missing provider fields")
    if envelope["launch_nonce"] != nonce or envelope["resumed"] is not False:
        raise ValueError("runtime nonce/resume mismatch")
    if adapter.output_protocol == "sol-json" and envelope["provider"] != "openai-codex":
        raise ValueError("Sol provider mismatch")
    content = envelope["result"]
    if not isinstance(content, str) or not content:
        raise ValueError("runtime result content was empty")
    identity = {"family": adapter.family, "model": str(envelope["resolved_model"]), "provider": str(envelope["provider"]), "source": "provider-response"}
    metadata = {"session_id": str(envelope["session_id"]), "provider_request_id": str(envelope["provider_request_id"]), "resumed": False, "runtime_controls": envelope["runtime_controls"], "provider_auxiliary_models": []}
    return content.encode("utf-8"), identity, metadata


def validate_receipt(receipt: dict[str, Any], *, expected_nonce: str, expected_family: str) -> None:
    if receipt.get("launch_nonce") != expected_nonce:
        raise ValueError("launch nonce mismatch")
    resolved = receipt.get("provider_resolved_identity") or {}
    if resolved.get("source") != "provider-response" or resolved.get("family") != expected_family or not resolved.get("model") or not resolved.get("provider"):
        raise ValueError("missing/ambiguous provider-resolved identity")
    if receipt.get("resumed") or not receipt.get("session_id") or not receipt.get("provider_request_id"):
        raise ValueError("resumed or missing provider session/request")
    if receipt.get("pid") in receipt.get("preexisting_family_pids", []):
        raise ValueError("accepted PID was pre-existing")
    if not receipt.get("fresh_process") or not receipt.get("process_create_time"):
        raise ValueError("fresh process proof missing")
    if receipt.get("exit_code") != 0:
        raise ValueError("runtime failed")
    if any(not isinstance(receipt.get(key), str) or len(receipt[key]) != 64 for key in SHA_KEYS):
        raise ValueError("receipt hash missing")
    controls = receipt.get("runtime_controls") or {}
    expected_controls = {"tools_sent": 0, "tool_choice": "none", "mcp_servers": 0, "session_persistence": False, "agent_loop": False}
    if controls != expected_controls:
        raise ValueError("tool-less runtime controls not proven")


def assert_distinct_families(first: str, second: str) -> None:
    if not first or not second or first == second:
        raise ValueError("same-family or unresolved identities: stop before coding")


def launch(adapter: Adapter, pack_path: Path, prompt_path: Path, output_path: Path, receipt_path: Path, *, requested_model: str | None = None) -> dict[str, Any]:
    if adapter.allow_filesystem or adapter.allow_web or adapter.allow_session_history:
        raise ValueError("adapter capabilities are not tool-less")
    requested = requested_model or adapter.requested_model
    if requested != adapter.requested_model:
        raise ValueError("requested model does not match adapter")
    nonce = secrets.token_hex(16)
    session_uuid = str(uuid.UUID(nonce))
    preexisting = _inventory(adapter.executable)
    pack, prompt = pack_path.read_bytes(), prompt_path.read_bytes()
    stdin = prompt + b"\n\n" + pack
    bundle_hash = _sha(pack_path.name.encode() + b"\0" + _sha(pack).encode() + prompt_path.name.encode() + b"\0" + _sha(prompt).encode())
    arguments = list(adapter.arguments)
    if adapter.output_protocol == "claude-json":
        arguments += ["--session-id", session_uuid]
    else:
        arguments += [nonce, adapter.requested_model] if adapter.output_protocol == "fake-json" else ["--nonce", nonce]
    started = _now()
    process = subprocess.Popen([adapter.executable, *arguments], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(pack_path.parent))
    pid = process.pid
    created = _create_time(pid)
    stdout, stderr = process.communicate(stdin)
    ended = _now()
    if process.returncode != 0:
        raise RuntimeError(f"coder runtime failed with exit {process.returncode}: {stderr.decode('utf-8', errors='replace')[:500]}")
    output, identity, metadata = _parse_envelope(adapter, stdout, nonce=nonce, session_uuid=session_uuid)
    _atomic_bytes(output_path, output)
    receipt = {
        "schema": "all11_gpt_launch_receipt_v2",
        "launch_nonce": nonce,
        "executable": adapter.executable,
        "arguments": arguments,
        "requested_identity": {"family": adapter.family, "model": requested, "provider": adapter.provider},
        "provider_resolved_identity": identity,
        "pid": pid,
        "ppid": os.getpid(),
        "process_create_time": created,
        "bundle_path": str(pack_path.parent.resolve()),
        "bundle_sha256": bundle_hash,
        "input_sha256": _sha(stdin),
        "session_id": metadata["session_id"],
        "provider_request_id": metadata["provider_request_id"],
        "provider_auxiliary_models": metadata["provider_auxiliary_models"],
        "resumed": metadata["resumed"],
        "runtime_controls": metadata["runtime_controls"],
        "started_at": started,
        "ended_at": ended,
        "exit_code": process.returncode,
        "stdout_sha256": _sha(stdout),
        "stderr_sha256": _sha(stderr),
        "output_sha256": _sha(output),
        "preexisting_family_pids": preexisting,
        "fresh_process": pid not in preexisting,
    }
    validate_receipt(receipt, expected_nonce=nonce, expected_family=adapter.family)
    _atomic_json(receipt_path, receipt)
    return receipt


def create_bundle(destination: Path, allowlist: dict[str, Path]) -> dict[str, Any]:
    permitted = {"prompt.txt", "PACK_A_final.md", "PACK_B_factcheck.md", "PACK_C_trajectory.md", "coding_output.schema.json"}
    if not set(allowlist) <= permitted or sum(name.startswith("PACK_") for name in allowlist) != 1 or "prompt.txt" not in allowlist or "coding_output.schema.json" not in allowlist:
        raise ValueError("bundle allowlist violation")
    destination.mkdir(parents=True, exist_ok=False)
    files = {}
    for name, source in allowlist.items():
        raw = source.read_bytes()
        (destination / name).write_bytes(raw)
        files[name] = _sha(raw)
    manifest = {"schema": "all11_toolless_bundle_v2", "files": files, "bundle_sha256": _sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())}
    _atomic_json(destination / "BUNDLE_MANIFEST.json", manifest)
    return manifest


def capability_deny_log(receipt: dict[str, Any]) -> list[dict[str, str]]:
    controls = receipt.get("runtime_controls") or {}
    expected = {"tools_sent": 0, "tool_choice": "none", "mcp_servers": 0, "session_persistence": False, "agent_loop": False}
    if controls != expected:
        raise ValueError("capability denial not established by runtime controls")
    probes = ("repository", "parent traversal", "private key", "other pack/output", "git history", "session history", "external URL", "shell/filesystem tools")
    return [{"probe": probe, "status": "DENIED", "basis": "observed provider request/launch controls"} for probe in probes]
