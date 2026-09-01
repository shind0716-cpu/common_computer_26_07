from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def merge_pack(kind: str) -> Path:
    sol_path = HERE / f"PACK_{kind}_SOL_01.json"
    claude_path = HERE / f"PACK_{kind}_CLAUDE_01.json"
    disagreement_path = HERE / f"PACK_{kind}_DISAGREEMENTS.json"
    adjudication_path = HERE / f"PACK_{kind}_ADJUDICATION.json"
    sol = json.loads(sol_path.read_text(encoding="utf-8"))
    claude = json.loads(claude_path.read_text(encoding="utf-8"))
    disagreements = json.loads(disagreement_path.read_text(encoding="utf-8"))
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    if adjudication["source_disagreements_sha256"] != sha(disagreement_path):
        raise ValueError(f"PACK_{kind}: adjudication is not bound to current disagreements")
    if adjudication.get("key_access") is not False or adjudication.get("blind_labels") is not True:
        raise ValueError(f"PACK_{kind}: invalid adjudicator blinding declaration")

    sol_items = {row["id"]: row for row in sol["items"]}
    claude_items = {row["id"]: row for row in claude["items"]}
    provenance = []

    if kind in {"W", "F"}:
        conflict_ids = [row["id"] for row in disagreements["disagreements"]]
        resolutions = {row["id"]: row for row in adjudication["resolutions"]}
        if set(resolutions) != set(conflict_ids) or len(resolutions) != len(conflict_ids):
            raise ValueError(f"PACK_{kind}: resolution ID set mismatch")
        items = []
        for item_id in sorted(sol_items):
            if item_id in resolutions:
                resolved = resolutions[item_id]["resolved_item"]
                if resolved["id"] != item_id:
                    raise ValueError(f"PACK_{kind}: resolved item ID mismatch {item_id}")
                items.append(resolved)
                provenance.append({
                    "id": item_id,
                    "status": "adjudicated",
                    "adjudicator_id": adjudication["adjudicator_id"],
                })
            else:
                items.append(sol_items[item_id])
                provenance.append({"id": item_id, "status": "agreement"})
    else:
        conflict_coords = [(row["id"], row["fact_no"]) for row in disagreements["disagreements"]]
        resolutions = {(row["id"], row["fact_no"]): row for row in adjudication["resolutions"]}
        if set(resolutions) != set(conflict_coords) or len(resolutions) != len(conflict_coords):
            raise ValueError("PACK_R: resolution coordinate set mismatch")
        items = []
        for item_id in sorted(sol_items):
            item = json.loads(json.dumps(sol_items[item_id], ensure_ascii=False))
            for fact in item["facts"]:
                coord = (item_id, fact["fact_no"])
                if coord in resolutions:
                    resolved = resolutions[coord]
                    for field in ("retained", "quote", "rationale", "confidence"):
                        fact[field] = resolved[field]
                    provenance.append({
                        "id": item_id,
                        "fact_no": fact["fact_no"],
                        "status": "adjudicated",
                        "adjudicator_id": adjudication["adjudicator_id"],
                    })
                else:
                    provenance.append({"id": item_id, "fact_no": fact["fact_no"], "status": "agreement"})
            items.append(item)

    consensus = {
        "pack": f"PACK_{kind}",
        "consensus_id": f"PACK_{kind}_CONSENSUS_01",
        "instruction_version": "20260901-ab-v1",
        "key_access": False,
        "source_path": sol["source_path"],
        "source_sha256": sol["source_sha256"],
        "inputs": {
            "coder_1_sha256": sha(sol_path),
            "coder_2_sha256": sha(claude_path),
            "disagreements_sha256": sha(disagreement_path),
            "adjudication_sha256": sha(adjudication_path),
        },
        "items": items,
        "provenance": provenance,
    }
    consensus_path = HERE / f"PACK_{kind}_CONSENSUS_01.json"
    atomic_json(consensus_path, consensus)
    freeze = {
        "pack": f"PACK_{kind}",
        "freeze_id": f"PACK_{kind}_FREEZE_01",
        "key_opened": False,
        "files": {
            sol_path.name: sha(sol_path),
            claude_path.name: sha(claude_path),
            disagreement_path.name: sha(disagreement_path),
            adjudication_path.name: sha(adjudication_path),
            consensus_path.name: sha(consensus_path),
            Path(sol["source_path"]).name: sol["source_sha256"],
        },
        "counts": {
            "items": len(items),
            "disagreements": disagreements["n_disagreements"],
            "adjudications": len(adjudication["resolutions"]),
        },
    }
    atomic_json(HERE / f"PACK_{kind}_FREEZE.json", freeze)
    return consensus_path


def main() -> int:
    for kind in "WRF":
        path = merge_pack(kind)
        print(f"MERGED {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
