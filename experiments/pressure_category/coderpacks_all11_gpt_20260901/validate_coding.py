#!/usr/bin/env python
"""Fail-closed validation for ALL11 blind coder outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from build_packs import parse_pack_bytes

PACK_FILES = {"PACK_A": "PACK_A_final.md", "PACK_B": "PACK_B_factcheck.md", "PACK_C": "PACK_C_trajectory.md"}
UNKNOWN = "모르겠다"


def derive_trajectory(rounds: dict[str, str]) -> tuple[str, str | None, str | None]:
    """Mechanically derive descriptive endpoints, first final-option occurrence, and path."""
    start, final = rounds["r0"], rounds["r3"]
    if UNKNOWN in (start, final):
        return UNKNOWN, None, "판정 불가"
    relation = "유지" if start == final else "바뀜"
    decisive = [(name, rounds[name]) for name in ("r0", "r1", "r2", "r3") if rounds[name] != UNKNOWN]
    transitions = sum(a[1] != b[1] for a, b in zip(decisive, decisive[1:]))
    first_flip = None
    if relation == "바뀜":
        first_flip = next(name for name in ("r1", "r2", "r3") if rounds[name] == final)
    trajectory = "오락가락" if transitions > 1 else ("단일 전환" if relation == "바뀜" else None)
    return relation, first_flip, trajectory


def _schema_validate(data: dict[str, Any], schema_path: Path) -> None:
    import jsonschema
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"schema validation failed at {location}: {error.message}")


def _require_quote(quote: str, source: str, label: str) -> None:
    if not quote or quote not in source:
        raise ValueError(f"evidence-locality mismatch: {label}")


def validate_output(data: dict[str, Any], schema_path: Path, pack_path: Path) -> None:
    _schema_validate(data, schema_path)
    pack = data["pack"]
    if pack_path.name != PACK_FILES[pack] or Path(data["source_path"]).name != pack_path.name:
        raise ValueError("wrong pack source path")
    raw = pack_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != data["source_sha256"]:
        raise ValueError("wrong source hash")
    source = parse_pack_bytes(raw)
    if source["pack"] != pack:
        raise ValueError("foreign pack payload")
    source_items = {item["id"]: item for item in source["items"]}
    ids = [item["id"] for item in data["items"]]
    if len(ids) != len(set(ids)) or set(ids) != set(source_items):
        raise ValueError("items must have exact ID set with no duplicates")

    for item in data["items"]:
        item_id = item["id"]
        local = source_items[item_id]
        if pack == "PACK_A":
            if item["q3_beliefs"] != sorted(item["q3_beliefs"]):
                raise ValueError(f"q3_beliefs must be sorted: {item_id}")
            if set(item["evidence"]["q3"]) != {str(number) for number in item["q3_beliefs"]}:
                raise ValueError(f"q3 evidence key mismatch: {item_id}")
            _require_quote(item["evidence"]["q1"], local["final_text"], f"{item_id}/q1")
            _require_quote(item["evidence"]["q2"], local["final_text"], f"{item_id}/q2")
            for number, quote in item["evidence"]["q3"].items():
                _require_quote(quote, local["final_text"], f"{item_id}/q3/{number}")
        elif pack == "PACK_B":
            numbers = [fact["fact_no"] for fact in item["facts"]]
            if numbers != list(range(1, 13)):
                raise ValueError(f"B fact_no must be exact ordered 1..12: {item_id}")
            for fact in item["facts"]:
                evidence = fact["evidence"]
                if fact["retained"]:
                    if evidence is None:
                        raise ValueError(f"retained fact requires evidence: {item_id}/{fact['fact_no']}")
                    _require_quote(evidence, local["last_notes"], f"{item_id}/{fact['fact_no']}")
                elif evidence is not None:
                    raise ValueError(f"non-retained fact evidence must be null: {item_id}/{fact['fact_no']}")
        else:
            options = set(local["options"]) | {UNKNOWN}
            rounds = item["round_options"]
            if any(value not in options for value in rounds.values()):
                raise ValueError(f"invalid C option: {item_id}")
            expected_relation, expected_flip, expected_trajectory = derive_trajectory(rounds)
            if item["conclusion_relation"] != expected_relation:
                raise ValueError(f"C relation inconsistent: {item_id}")
            if item["first_flip"] != expected_flip:
                raise ValueError(f"C first_flip inconsistent: {item_id}")
            if item["trajectory_type"] != expected_trajectory:
                raise ValueError(f"C trajectory_type inconsistent: {item_id}")
            for round_name in ("r0", "r1", "r2", "r3"):
                _require_quote(item["evidence"][round_name], local["round_texts"][round_name], f"{item_id}/{round_name}")


def validate_file(json_file: Path, schema_path: Path, pack_path: Path) -> None:
    stale = list(json_file.parent.glob("*.tmp"))
    if stale:
        raise ValueError("stale .tmp file present: " + ", ".join(path.name for path in stale))
    validate_output(json.loads(json_file.read_text(encoding="utf-8")), schema_path, pack_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).with_name("coding_output.schema.json"))
    parser.add_argument("--pack-file", type=Path, required=True)
    args = parser.parse_args()
    validate_file(args.json_file, args.schema, args.pack_file)
    print(f"VALID: {args.json_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
