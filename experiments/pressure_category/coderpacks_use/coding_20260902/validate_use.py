from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent / "PACK_U_use_2026-09-02.md"
EXPECTED_IDS = [f"U-{i:02d}" for i in range(1, 35)]
ENUM = {"세울 수 있다", "부분만", "못 세운다"}
REQUIRED_TOP = {"pack", "coder_id", "instruction_version", "independent", "key_access", "source_path", "source_sha256", "items"}
REQUIRED_ITEM = {"id", "purpose", "purpose_evidence", "missing_capability", "missing_evidence", "rebuildability", "rebuildability_evidence", "rationale", "confidence"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_sections(source: str) -> dict[str, str]:
    marks = list(re.finditer(r"^## (U-\d{2})\s*$", source, re.MULTILINE))
    return {m.group(1): source[m.start(): marks[i + 1].start() if i + 1 < len(marks) else len(source)] for i, m in enumerate(marks)}


def notebook_text(section: str) -> str:
    if "**수첩**" not in section or "**그 판의 최종 선택**" not in section:
        raise ValueError("source item missing notebook boundaries")
    return section.split("**수첩**", 1)[1].split("**그 판의 최종 선택**", 1)[0]


def validate(obj: dict, pack_path: Path = PACK, *, expected_coder: str | None = None) -> None:
    if set(obj) != REQUIRED_TOP:
        raise ValueError("top-level fields mismatch")
    if obj["pack"] != "PACK_U" or obj["instruction_version"] != "20260902-use-v1":
        raise ValueError("pack/instruction mismatch")
    if obj["independent"] is not True or obj["key_access"] is not False:
        raise ValueError("independence/key declaration invalid")
    if obj["source_path"] != pack_path.name or obj["source_sha256"] != digest(pack_path):
        raise ValueError("source binding mismatch")
    if expected_coder is not None and obj["coder_id"] != expected_coder:
        raise ValueError("coder identity mismatch")
    source = pack_path.read_text(encoding="utf-8")
    sections = source_sections(source)
    if list(sections) != EXPECTED_IDS:
        raise ValueError("source ID closure mismatch")
    items = obj["items"]
    if [x.get("id") for x in items] != EXPECTED_IDS:
        raise ValueError("output IDs/order mismatch")
    for item in items:
        if set(item) != REQUIRED_ITEM:
            raise ValueError(f"{item.get('id')}: field set mismatch")
        local = notebook_text(sections[item["id"]])
        for field in ("purpose", "missing_capability", "rationale"):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f"{item['id']}: empty {field}")
        for field in ("purpose_evidence", "rebuildability_evidence"):
            quote = item[field]
            if not isinstance(quote, str) or not quote or len(quote) > 300 or quote not in local:
                raise ValueError(f"{item['id']}: non-local {field}")
        quote = item["missing_evidence"]
        if quote is not None and (not isinstance(quote, str) or not quote or len(quote) > 300 or quote not in local):
            raise ValueError(f"{item['id']}: non-local missing_evidence")
        if item["rebuildability"] not in ENUM:
            raise ValueError(f"{item['id']}: invalid rebuildability")
        if not isinstance(item["confidence"], (int, float)) or isinstance(item["confidence"], bool) or not 0 <= item["confidence"] <= 1:
            raise ValueError(f"{item['id']}: invalid confidence")


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("usage: python validate_use.py OUTPUT.json [EXPECTED_CODER]", file=sys.stderr); return 2
    path = Path(sys.argv[1]); obj = json.loads(path.read_text(encoding="utf-8"))
    validate(obj, expected_coder=sys.argv[2] if len(sys.argv) == 3 else None)
    print(f"PACK_U_VALID coder={obj['coder_id']} items={len(obj['items'])} sha256={digest(path)}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
