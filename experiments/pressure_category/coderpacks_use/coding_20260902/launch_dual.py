from __future__ import annotations

import concurrent.futures
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INFRA = ROOT / "experiments/pressure_category/coderpacks_all11_gpt_20260901"
sys.path.insert(0, str(INFRA))
from isolated_launcher import claude_adapter, launch, sol_adapter

PACK = HERE.parent / "PACK_U_use_2026-09-02.md"
RUNS = [
    ("A_CLAUDE_USE_01", claude_adapter(), HERE / "PROMPT_CLAUDE.txt"),
    ("B_SOL_USE_01", sol_adapter(), HERE / "PROMPT_SOL.txt"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(coder_id, adapter, prompt, bundle):
    pack_dst = bundle / PACK.name
    prompt_dst = bundle / "prompt.txt"
    shutil.copyfile(PACK, pack_dst); shutil.copyfile(prompt, prompt_dst)
    manifest = {"files": {pack_dst.name: sha(pack_dst), prompt_dst.name: sha(prompt_dst)}, "coder_id": coder_id}
    (bundle / "BUNDLE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return launch(adapter, pack_dst, prompt_dst, HERE / f"{coder_id}_RAW.json", HERE / f"{coder_id}_LAUNCH_RECEIPT.json")


def main():
    existing = [HERE / f"{cid}_RAW.json" for cid, _, _ in RUNS if (HERE / f"{cid}_RAW.json").exists()]
    if existing: raise RuntimeError(f"refusing to overwrite existing outputs: {existing}")
    base = Path(tempfile.mkdtemp(prefix="coder-use-20260902-"))
    bundles = []
    for cid, _, _ in RUNS:
        p = base / cid; p.mkdir(); bundles.append(p)
    state = {"status": "LAUNCHED", "planned_launches": 2, "bundle_root": str(base), "pack_sha256": sha(PACK)}
    (HERE / "RUN_STATE.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futures = [ex.submit(one, *spec, bundle) for spec, bundle in zip(RUNS, bundles)]
        for future in futures: receipts.append(future.result())
    families = [r["provider_resolved_identity"]["family"] for r in receipts]
    if len(set(families)) != 2: raise RuntimeError(f"distinct-family gate failed: {families}")
    state.update(status="RAW_COMPLETE", attempted_launches=2, families=families,
                 outputs={cid: sha(HERE / f"{cid}_RAW.json") for cid, _, _ in RUNS})
    (HERE / "RUN_STATE.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": state["status"], "families": families, "bundle_root": str(base)}, ensure_ascii=False))

if __name__ == "__main__": main()
