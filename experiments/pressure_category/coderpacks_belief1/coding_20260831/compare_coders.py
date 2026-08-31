#!/usr/bin/env python
"""Extract anonymized semantic disagreements between two coding files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIELDS = {
    "PACK_A": ("q1_orientation", "q2_politics", "q3_beliefs"),
    "PACK_B": ("facts",),
    "PACK_C": ("conclusion_relation", "first_flip", "change_type"),
}


def compare_outputs(left: dict[str, Any], right: dict[str, Any]) -> list[dict[str, Any]]:
    if left.get("pack") != right.get("pack"):
        raise ValueError("pack mismatch")
    pack = left["pack"]
    left_items = {item["id"]: item for item in left["items"]}
    right_items = {item["id"]: item for item in right["items"]}
    if left_items.keys() != right_items.keys():
        raise ValueError("item ID set mismatch")

    disagreements = []
    for item_id in sorted(left_items):
        fields = {}
        if pack == "PACK_B":
            first_facts = {row["fact_no"]: row["retained"] for row in left_items[item_id]["facts"]}
            second_facts = {row["fact_no"]: row["retained"] for row in right_items[item_id]["facts"]}
            if first_facts.keys() != second_facts.keys():
                raise ValueError(f"fact number set mismatch for {item_id}")
            for fact_no in sorted(first_facts):
                if first_facts[fact_no] != second_facts[fact_no]:
                    fields[f"fact_{fact_no}"] = {"CODER_1": first_facts[fact_no], "CODER_2": second_facts[fact_no]}
        else:
            for field in FIELDS[pack]:
                first = left_items[item_id].get(field)
                second = right_items[item_id].get(field)
                if first != second:
                    fields[field] = {"CODER_1": first, "CODER_2": second}
        if fields:
            disagreements.append({"id": item_id, "fields": fields})
    return disagreements


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("coder_1", type=Path)
    parser.add_argument("coder_2", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    left = json.loads(args.coder_1.read_text(encoding="utf-8"))
    right = json.loads(args.coder_2.read_text(encoding="utf-8"))
    result = {"pack": left.get("pack"), "coder_labels": ["CODER_1", "CODER_2"], "disagreements": compare_outputs(left, right)}
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"WROTE: {args.output} ({len(result['disagreements'])} item disagreements)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
