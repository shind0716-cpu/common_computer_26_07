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


def merge_pack_b(primary: dict[str, Any], audit: dict[str, Any], adjudication: dict[str, Any]) -> list[dict[str, Any]]:
    primary_items = {item["id"]: item for item in primary["items"]}
    audit_items = {item["id"]: item for item in audit["items"]}
    resolutions = {item["id"]: item["fields"] for item in adjudication["resolutions"]}
    merged: list[dict[str, Any]] = []

    for item in primary["items"]:
        item_id = item["id"]
        row = json.loads(json.dumps(item, ensure_ascii=False))
        if item_id not in audit_items:
            merged.append(row)
            continue
        audit_facts = {fact["fact_no"]: fact for fact in audit_items[item_id]["facts"]}
        for fact in row["facts"]:
            fact_no = fact["fact_no"]
            audited = audit_facts[fact_no]
            if fact["retained"] == audited["retained"]:
                continue
            field = f"fact_{fact_no}"
            if field not in resolutions.get(item_id, {}):
                raise ValueError(f"missing adjudication for {item_id} {field}")
            decision = resolutions[item_id][field]
            fact["retained"] = decision["value"]
            fact["evidence"] = decision["evidence"]
            fact["rationale"] = decision["rationale"]
            fact["confidence"] = decision["confidence"]
            note = row.get("ambiguity_note")
            addition = f"익명 감사 불일치 조정 완료: {field}"
            row["ambiguity_note"] = f"{note}; {addition}" if note else addition
        merged.append(row)
    return merged


def merge_pack_c(first_coder: dict[str, Any], second_coder: dict[str, Any], adjudication: dict[str, Any]) -> list[dict[str, Any]]:
    second_items = {item["id"]: item for item in second_coder["items"]}
    resolutions = {item["id"]: item for item in adjudication["resolutions"]}
    fields = ("conclusion_relation", "first_flip", "change_type")
    merged: list[dict[str, Any]] = []

    for item in first_coder["items"]:
        item_id = item["id"]
        row = json.loads(json.dumps(item, ensure_ascii=False))
        second = second_items[item_id]
        disputed = [field for field in fields if item[field] != second[field]]
        if not disputed:
            merged.append(row)
            continue
        if item_id not in resolutions:
            raise ValueError(f"missing adjudication for {item_id}")
        resolution = resolutions[item_id]
        if set(resolution["fields"]) != set(disputed):
            raise ValueError(f"adjudication field mismatch for {item_id}")
        row["round_options"] = resolution["round_options"]
        row["evidence"] = resolution["evidence"]
        confidences = []
        for field in disputed:
            decision = resolution["fields"][field]
            row[field] = decision["value"]
            confidences.append(decision["confidence"])
        row["confidence"] = min(confidences)
        row["ambiguity_note"] = "익명 불일치 조정 완료: " + ", ".join(disputed)
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
    pack = left["pack"]
    if pack == "PACK_A":
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
    elif pack == "PACK_B":
        output = {
            "pack": "PACK_B",
            "coder_id": "B_CONSENSUS_01",
            "coder_family": "Adjudicator",
            "instruction_version": "20260831-v1",
            "independent": False,
            "key_access": False,
            "source_path": "experiments/pressure_category/coderpacks_belief1/PACK_B_factcheck.md",
            "source_sha256": left["source_sha256"],
            "notes": "Post-hoc exploratory primary coding with prespecified 14-card audit; audited disagreements resolved blindly.",
            "items": merge_pack_b(left, right, decisions),
        }
    elif pack == "PACK_C":
        output = {
            "pack": "PACK_C",
            "coder_id": "C_CONSENSUS_01",
            "coder_family": "Adjudicator",
            "instruction_version": "20260831-v1",
            "independent": False,
            "key_access": False,
            "source_path": "experiments/pressure_category/coderpacks_belief1/PACK_C_flipround.md",
            "source_sha256": left["source_sha256"],
            "notes": "Post-hoc exploratory full double coding with blinded adjudication of every requested-field disagreement.",
            "items": merge_pack_c(left, right, decisions),
        }
    else:
        raise ValueError(f"unsupported pack for merge: {pack}")
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"WROTE: {args.output} ({len(output['items'])} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
