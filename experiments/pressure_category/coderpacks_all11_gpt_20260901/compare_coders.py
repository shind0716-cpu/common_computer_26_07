#!/usr/bin/env python
"""Extract complete, deterministically anonymized field disagreements."""

from __future__ import annotations

import hashlib
from typing import Any

A_FIELDS = ("q1_orientation", "q2_politics", "q3_beliefs", "evidence", "confidence")
C_FIELDS = tuple([f"round_options.r{i}" for i in range(4)] + ["conclusion_relation", "first_flip", "trajectory_type"] + [f"evidence.r{i}" for i in range(4)] + ["confidence"])
B_FACT_FIELDS = ("retained", "evidence", "rationale", "confidence")


def _labels(pack: str, item_id: str) -> tuple[str, str]:
    swapped = int(hashlib.sha256(f"20260901|{pack}|{item_id}|coder-labels".encode()).hexdigest(), 16) & 1
    return ("CODER_2", "CODER_1") if swapped else ("CODER_1", "CODER_2")


def _field(item: dict[str, Any], name: str) -> Any:
    value: Any = item
    for part in name.split("."):
        value = value[part]
    return value


def compare_outputs(left: dict[str, Any], right: dict[str, Any], source_items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if left.get("pack") != right.get("pack"):
        raise ValueError("pack mismatch")
    if left.get("source_sha256") != right.get("source_sha256"):
        raise ValueError("source hash mismatch")
    pack = left["pack"]
    left_items = {item["id"]: item for item in left["items"]}
    right_items = {item["id"]: item for item in right["items"]}
    if left_items.keys() != right_items.keys() or left_items.keys() != source_items.keys():
        raise ValueError("item ID set mismatch")
    if len(left_items) != len(left["items"]) or len(right_items) != len(right["items"]):
        raise ValueError("duplicate item ID")

    disagreements: list[dict[str, Any]] = []
    for item_id in sorted(left_items):
        first_label, second_label = _labels(pack, item_id)
        fields: dict[str, Any] = {}
        first = left_items[item_id]
        second = right_items[item_id]
        if pack == "PACK_B":
            first_facts = {fact["fact_no"]: fact for fact in first["facts"]}
            second_facts = {fact["fact_no"]: fact for fact in second["facts"]}
            if first_facts.keys() != second_facts.keys():
                raise ValueError(f"fact number set mismatch for {item_id}")
            for fact_no in sorted(first_facts):
                for field in B_FACT_FIELDS:
                    left_value = first_facts[fact_no][field]
                    right_value = second_facts[fact_no][field]
                    if left_value != right_value:
                        fields[f"fact_{fact_no}.{field}"] = {first_label: left_value, second_label: right_value}
        else:
            for field in (A_FIELDS if pack == "PACK_A" else C_FIELDS):
                left_value, right_value = _field(first, field), _field(second, field)
                if left_value != right_value:
                    fields[field] = {first_label: left_value, second_label: right_value}
        if fields:
            disagreements.append({"id": item_id, "source_item": source_items[item_id], "fields": fields})
    return disagreements
