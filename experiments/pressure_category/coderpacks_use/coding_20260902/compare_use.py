from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import validate_use as V

HERE = Path(__file__).resolve().parent
PACK = HERE.parent / "PACK_U_use_2026-09-02.md"
A = HERE / "A_CLAUDE_USE_01_RAW.json"
B = HERE / "B_SOL_USE_01_CORRECTED.json"
OUT = HERE / "PACK_U_DISAGREEMENTS.json"


def atomic(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    if OUT.exists(): raise RuntimeError("refusing to overwrite disagreements")
    a = json.loads(A.read_text(encoding="utf-8")); b = json.loads(B.read_text(encoding="utf-8"))
    V.validate(a, expected_coder="A_CLAUDE_USE_01"); V.validate(b, expected_coder="B_SOL_USE_01")
    ah, bh = V.digest(A), V.digest(B)
    # Hash-derived global swap keeps the adjudication file model-anonymous.
    swap = int(hashlib.sha256((ah + bh).encode()).hexdigest(), 16) & 1
    first, second = (b, a) if swap else (a, b)
    sections = V.source_sections(PACK.read_text(encoding="utf-8"))
    rows = []
    for x, y in zip(first["items"], second["items"]):
        if x["rebuildability"] == y["rebuildability"]: continue
        rows.append({"id": x["id"], "source": sections[x["id"]],
                     "CODER_1": {k: x[k] for k in ("rebuildability", "rebuildability_evidence", "rationale")},
                     "CODER_2": {k: y[k] for k in ("rebuildability", "rebuildability_evidence", "rationale")}})
    obj = {"schema": "pack_u_disagreements_v1", "source_path": PACK.name, "source_sha256": V.digest(PACK),
           "coder_artifact_sha256": sorted([ah, bh]), "n_disagreements": len(rows), "items": rows}
    atomic(OUT, obj)
    # Mapping is operational provenance, not supplied to adjudicator.
    atomic(HERE / "ANONYMIZATION_MAP.json", {"swap": bool(swap), "CODER_1_sha256": V.digest(B if swap else A),
                                               "CODER_2_sha256": V.digest(A if swap else B)})
    print(f"PACK_U_DISAGREEMENTS n={len(rows)} sha256={V.digest(OUT)}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
