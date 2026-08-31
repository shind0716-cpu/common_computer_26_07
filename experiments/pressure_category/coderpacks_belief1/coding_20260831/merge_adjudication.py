#!/usr/bin/env python
"""Merge independent PACK_A codings with resolution-only adjudication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


A_FIELDS = ("q1_orientation", "q2_politics", "q3_beliefs")


def merge_pack_a(left: dict[str, Any], right: dict[str, Any], adjudication: dict[str, Any]) -> list[dict[str, Any]]:
    left_items = {item["id"]: item for item in left["items"]}
    right_items = {item["id"]: item for item in right["items"]}
    resolutions = {item["id"]: item["fields"] for item in adjudication["resolutions"]}
    if left_items.keys() != right_items.keys():
        raise ValueError("coder item ID set mismatch")

    merged: list[dict[str, Any]] = []
    for item_id in sorted(left_items):
        first = left_items[item_id]
        second = right_items[item_id]
        resolved = resolutions.get(item_id, {})
        row: dict[str, Any] = {
            "id": item_id,
            "evidence": {"q1": "", "q2": "", "q3": {}},
            "confidence": {"q1": 0.0, "q2": 0.0, "q3": 0.0},
            "ambiguity_note": None,
        }
        adjudicated_fields: list[str] = []
        for field in A_FIELDS:
            evidence_key = {"q1_orientation": "q1", "q2_politics": "q2", "q3_beliefs": "q3"}[field]
            if first[field] == second[field]:
                row[field] = first[field]
                row["evidence"][evidence_key] = first["evidence"][evidence_key]
                row["confidence"][evidence_key] = first["confidence"][evidence_key]
                continue
            if field not in resolved:
                raise ValueError(f"missing adjudication for {item_id} {field}")
            decision = resolved[field]
            row[field] = decision["value"]
            row["confidence"][evidence_key] = decision["confidence"]
            adjudicated_fields.append(field)
            if field != "q3_beliefs":
                row["evidence"][evidence_key] = decision["evidence"]
            elif decision["value"] == first[field]:
                row["evidence"]["q3"] = first["evidence"]["q3"]
            elif decision["value"] == second[field]:
                row["evidence"]["q3"] = second["evidence"]["q3"]
            else:
                row["evidence"]["q3"] = {str(number): decision["evidence"] for number in decision["value"]}
        if adjudicated_fields:
            row["ambiguity_note"] = "익명 불일치 조정 완료: " + ", ".join(adjudicated_fields)
        merged.append(row)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("coder_1", type=Path)
    parser.add_argument("coder_2", type=Path)
    parser.add_argument("adjudication", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    left = json.loads(args.coder_1.read_text(encoding="utf-8"))
    right = json.loads(args.coder_2.read_text(encoding="utf-8"))
    decisions = json.loads(args.adjudication.read_text(encoding="utf-8"))
    output = {
        "pack": "PACK_A",
        "coder_id": "A_CONSENSUS_01",
        "coder_family": "Adjudicator",
        "instruction_version": "20260831-v1",
        "independent": False,
        "key_access": False,
        "source_path": "experiments/pressure_category/coderpacks_belief1/PACK_A_final.md",
        "source_sha256": left["source_sha256"],
        "notes": "Exact coder agreements retained; every disagreement resolved by blinded adjudication.",
        "items": merge_pack_a(left, right, decisions),
    }
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"WROTE: {args.output} ({len(output['items'])} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
