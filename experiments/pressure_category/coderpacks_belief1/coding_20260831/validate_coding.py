#!/usr/bin/env python
"""Validate blind-coding JSON outputs before freezing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _expected_ids(pack: str, item_count: int | None = None) -> set[str]:
    limits = {"PACK_A": 66, "PACK_B": 66, "PACK_C": 33}
    prefixes = {"PACK_A": "A", "PACK_B": "B", "PACK_C": "C"}
    if pack not in limits:
        raise ValueError(f"unknown pack: {pack}")
    count = limits[pack] if item_count is None else item_count
    return {f"{prefixes[pack]}-{i:02d}" for i in range(1, count + 1)}


def validate_output(data: dict[str, Any], schema_path: Path, *, skip_schema: bool = False) -> None:
    if not skip_schema:
        import jsonschema

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            jsonschema.Draft202012Validator(schema).validate(data)
        except jsonschema.ValidationError as exc:
            location = "/".join(str(part) for part in exc.absolute_path) or "<root>"
            raise ValueError(f"schema validation failed at {location}: {exc.message}") from exc

    pack = data.get("pack")
    ids = [item.get("id") for item in data.get("items", [])]
    assigned_ids = data.get("assigned_ids")
    expected = set(assigned_ids) if assigned_ids is not None else _expected_ids(pack)
    if set(ids) != expected or len(ids) != len(expected):
        raise ValueError(f"{pack} items must have the exact ID set; got {len(ids)} rows and {len(set(ids))} unique IDs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).with_name("coding_output.schema.json"))
    args = parser.parse_args()
    data = json.loads(args.json_file.read_text(encoding="utf-8"))
    validate_output(data, args.schema)
    print(f"VALID: {args.json_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
