"""Validation entry point for stage-specific experiment artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from compare_coders import A_FIELDS, B_FACT_FIELDS, C_FIELDS


def _expected_ids(pack: str) -> set[str]:
    return {f"{pack[-1]}-{number:02d}" for number in range(1, 34)}


def _expected_fields(pack: str) -> set[str]:
    if pack == "PACK_A":
        return set(A_FIELDS)
    if pack == "PACK_C":
        return set(C_FIELDS)
    return {f"fact_{number}.{field}" for number in range(1, 13) for field in B_FACT_FIELDS}


def _validate_consensus_matrix(data: dict[str, Any]) -> None:
    pack = data["pack"]
    rows = data["items"]
    ids = [row["id"] for row in rows]
    if len(ids) != 33 or len(set(ids)) != 33 or set(ids) != _expected_ids(pack):
        raise ValueError(f"exact consensus matrix requires 33 unique {pack} IDs")
    expected = _expected_fields(pack)
    coder_artifacts = data["coder_artifacts"]
    if len(coder_artifacts) != 2 or len({row["coder_id"] for row in coder_artifacts}) != 2 or len({row["sha256"] for row in coder_artifacts}) != 2:
        raise ValueError("exact consensus matrix requires two distinct coder artifacts")
    coder_refs = {
        "coder_1": (coder_artifacts[0]["coder_id"], coder_artifacts[0]["sha256"]),
        "coder_2": (coder_artifacts[1]["coder_id"], coder_artifacts[1]["sha256"]),
    }
    for row in rows:
        if set(row["fields"]) != expected:
            raise ValueError(f"exact consensus matrix field mismatch: {row['id']}")
        for field, record in row["fields"].items():
            provenance = record["provenance"]
            for label, (coder_id, digest) in coder_refs.items():
                ref = provenance[label]
                if ref["coder_id"] != coder_id or ref["artifact_sha256"] != digest:
                    raise ValueError(f"consensus provenance mismatch: {row['id']}/{field}/{label}")
            if record["coding_status"] == "unresolved" and record["value"] is not None:
                raise ValueError(f"unresolved consensus value must be null: {row['id']}/{field}")


def validate_artifact(kind: str, data: dict[str, Any]) -> None:
    import jsonschema

    path = Path(__file__).with_name("schemas") / f"{kind}.schema.json"
    if not path.exists():
        raise ValueError(f"unknown artifact kind: {kind}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        error = errors[0]
        where = "/".join(map(str, error.absolute_path)) or "<root>"
        raise ValueError(f"{kind} schema validation failed at {where}: {error.message}")
    if kind == "freeze":
        if len(set(data["launch_receipt_sha256"])) != 6:
            raise ValueError("freeze launch receipts must be six unique hashes")
    if kind == "consensus":
        _validate_consensus_matrix(data)
