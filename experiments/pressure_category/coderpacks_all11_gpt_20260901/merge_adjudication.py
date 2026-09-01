#!/usr/bin/env python
"""Fail-closed merge of agreements and conflict-only adjudication."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from artifact_contracts import validate_artifact
from build_packs import parse_pack_bytes
from compare_coders import A_FIELDS, B_FACT_FIELDS, C_FIELDS, compare_outputs
from validate_coding import validate_output


def _flatten(pack: str, item: dict[str, Any]) -> dict[str, Any]:
    if pack == "PACK_A":
        return {field: item[field] for field in A_FIELDS}
    if pack == "PACK_C":
        values: dict[str, Any] = {}
        for field in C_FIELDS:
            value: Any = item
            for part in field.split("."):
                value = value[part]
            values[field] = value
        return values
    values = {}
    for fact in item["facts"]:
        for field in B_FACT_FIELDS:
            values[f"fact_{fact['fact_no']}.{field}"] = fact[field]
    return values


def merge_consensus(
    left: dict[str, Any],
    right: dict[str, Any],
    disagreements: dict[str, Any],
    adjudication: dict[str, Any],
    *,
    source_items: dict[str, dict[str, Any]],
    left_sha256: str,
    right_sha256: str,
) -> dict[str, Any]:
    pack = left.get("pack")
    if pack != right.get("pack") or pack != disagreements.get("pack") or pack != adjudication.get("pack"):
        raise ValueError("pack mismatch")
    if left.get("source_sha256") != right.get("source_sha256"):
        raise ValueError("source hash mismatch")
    if left.get("coder_id") == right.get("coder_id"):
        raise ValueError("coder identities must be distinct")
    if disagreements.get("coder_artifact_sha256") != [left_sha256, right_sha256]:
        raise ValueError("coder artifact hash mismatch")

    left_items = {item["id"]: item for item in left["items"]}
    right_items = {item["id"]: item for item in right["items"]}
    if left_items.keys() != right_items.keys() or left_items.keys() != source_items.keys() or len(left_items) != len(left["items"]) or len(right_items) != len(right["items"]):
        raise ValueError("coder/source item ID set mismatch")

    expected_rows = compare_outputs(left, right, source_items)
    if disagreements.get("disagreements") != expected_rows:
        raise ValueError("disagreement content mismatch")

    expected_disputes: dict[str, set[str]] = {}
    flattened: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for item_id in left_items:
        first = _flatten(pack, left_items[item_id])
        second = _flatten(pack, right_items[item_id])
        if first.keys() != second.keys():
            raise ValueError(f"coder field-set mismatch: {item_id}")
        flattened[item_id] = (first, second)
        mismatches = {field for field in first if first[field] != second[field]}
        if mismatches:
            expected_disputes[item_id] = mismatches

    resolution_rows = adjudication.get("resolutions", [])
    resolutions = {row["id"]: row["fields"] for row in resolution_rows}
    if len(resolutions) != len(resolution_rows):
        raise ValueError("duplicate adjudication item")
    if set(resolutions) != set(expected_disputes):
        missing = set(expected_disputes) - set(resolutions)
        if missing:
            raise ValueError("missing adjudication: " + ", ".join(sorted(missing)))
        raise ValueError("extra adjudication: " + ", ".join(sorted(set(resolutions) - set(expected_disputes))))
    for item_id, expected in expected_disputes.items():
        if set(resolutions[item_id]) != expected:
            raise ValueError(f"adjudication field mismatch: {item_id}")

    merged_items: list[dict[str, Any]] = []
    for item_id in sorted(left_items):
        first, second = flattened[item_id]
        fields: dict[str, Any] = {}
        for field in first:
            provenance = {
                "coder_1": {"coder_id": left["coder_id"], "artifact_sha256": left_sha256, "value": first[field]},
                "coder_2": {"coder_id": right["coder_id"], "artifact_sha256": right_sha256, "value": second[field]},
            }
            if first[field] == second[field]:
                fields[field] = {"value": first[field], "coding_status": "audited_agreement", "provenance": provenance}
                continue
            decision = resolutions[item_id][field]
            status = decision.get("coding_status")
            if status not in ("adjudicated", "unresolved"):
                raise ValueError(f"invalid coding_status: {item_id}/{field}")
            if status == "adjudicated" and "value" not in decision:
                raise ValueError(f"adjudicated value missing: {item_id}/{field}")
            if status == "unresolved" and decision.get("value") is not None:
                raise ValueError(f"unresolved value must be null: {item_id}/{field}")
            provenance["adjudication"] = {key: value for key, value in decision.items() if key != "coding_status"}
            fields[field] = {"value": decision.get("value"), "coding_status": status, "provenance": provenance}
        merged_items.append({"id": item_id, "fields": fields})
    return {
        "schema": "all11_gpt_consensus_v2",
        "pack": pack,
        "coder_artifacts": [{"coder_id": left["coder_id"], "sha256": left_sha256}, {"coder_id": right["coder_id"], "sha256": right_sha256}],
        "items": merged_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("coder_1", type=Path)
    parser.add_argument("coder_2", type=Path)
    parser.add_argument("disagreements", type=Path)
    parser.add_argument("adjudication", type=Path)
    parser.add_argument("pack_file", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--first-pass-schema", type=Path, default=Path(__file__).with_name("coding_output.schema.json"))
    args = parser.parse_args()

    left_raw, right_raw = args.coder_1.read_bytes(), args.coder_2.read_bytes()
    left, right = json.loads(left_raw), json.loads(right_raw)
    disagreement = json.loads(args.disagreements.read_text(encoding="utf-8"))
    adjudication = json.loads(args.adjudication.read_text(encoding="utf-8"))
    validate_output(left, args.first_pass_schema, args.pack_file)
    validate_output(right, args.first_pass_schema, args.pack_file)
    validate_artifact("disagreement", disagreement)
    validate_artifact("adjudication", adjudication)
    source = parse_pack_bytes(args.pack_file.read_bytes())
    source_items = {item["id"]: item for item in source["items"]}
    result = merge_consensus(
        left,
        right,
        disagreement,
        adjudication,
        source_items=source_items,
        left_sha256=hashlib.sha256(left_raw).hexdigest(),
        right_sha256=hashlib.sha256(right_raw).hexdigest(),
    )
    validate_artifact("consensus", result)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"WROTE: {args.output} ({len(result['items'])} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
