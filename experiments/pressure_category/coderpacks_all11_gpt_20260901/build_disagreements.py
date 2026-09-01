#!/usr/bin/env python
"""Build validated JSON and Markdown conflict-only adjudication bundles."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from artifact_contracts import validate_artifact
from build_packs import parse_pack_bytes
from compare_coders import compare_outputs
from validate_coding import validate_output


def atomic_json(path: Path, data: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_bundle(coder_1: Path, coder_2: Path, pack_file: Path, output: Path, markdown: Path, *, first_pass_schema: Path | None = None) -> dict:
    schema = first_pass_schema or Path(__file__).with_name("coding_output.schema.json")
    left_raw, right_raw = coder_1.read_bytes(), coder_2.read_bytes()
    left, right = json.loads(left_raw), json.loads(right_raw)
    validate_output(left, schema, pack_file)
    validate_output(right, schema, pack_file)
    source = parse_pack_bytes(pack_file.read_bytes())
    source_items = {item["id"]: item for item in source["items"]}
    rows = compare_outputs(left, right, source_items)
    result = {
        "schema": "all11_gpt_disagreements_v2",
        "pack": left["pack"],
        "coder_labels": ["CODER_1", "CODER_2"],
        "coder_artifact_sha256": [hashlib.sha256(left_raw).hexdigest(), hashlib.sha256(right_raw).hexdigest()],
        "disagreements": rows,
    }
    validate_artifact("disagreement", result)
    atomic_json(output, result)
    lines = [f"# {left['pack']} blind adjudication items", "", "Resolve exactly the listed fields; coder-family mapping is intentionally hidden.", ""]
    for row in rows:
        lines += [f"## {row['id']}", "", "```json", json.dumps(row, ensure_ascii=False, indent=2), "```", ""]
    temporary = markdown.with_suffix(markdown.suffix + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(markdown)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("coder_1", type=Path)
    parser.add_argument("coder_2", type=Path)
    parser.add_argument("pack_file", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--first-pass-schema", type=Path, default=Path(__file__).with_name("coding_output.schema.json"))
    args = parser.parse_args()
    result = build_bundle(args.coder_1, args.coder_2, args.pack_file, args.output, args.markdown, first_pass_schema=args.first_pass_schema)
    print(f"WROTE: {args.output} ({len(result['disagreements'])} item disagreements)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
