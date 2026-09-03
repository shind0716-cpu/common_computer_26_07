"""[민옥 트랙] 라벨 한 문장 실험 gpt·gemini 확장 — 정독 채점용 블라인드 팩 (2026-09-03).
coderpacks_label_llm_20260902(하이쿠)와 같은 형식. 모델당 C0 66판 + 관문 통과 시나리오의 반대 압박(pxc/pxp) 판.
출력: coderpacks_label_models_20260903/{gpackNN|mpackNN}.json, KEY.json, MATERIALS11.json, PROTOCOL.md
사용: python build_packs_label_models.py"""
import json, random, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = HERE / "coderpacks_label_models_20260903"; OUT.mkdir(exist_ok=True)
SRC = HERE / "coderpacks_haiku_llm_20260902"
mats = json.load(open(SRC / "MATERIALS11.json", encoding="utf-8"))
for fn in ("MATERIALS11.json", "PROTOCOL.md"):
    if not (OUT / fn).exists(): shutil.copy(SRC / fn, OUT / fn)
STUB = {}
for mp in (HERE / "materials").glob("*.json"):
    try: md = json.loads(mp.read_text(encoding="utf-8")); STUB[md.get("issue_id")] = md.get("stub") or ""
    except Exception: pass
key = []
for model, tag in (("gpt", "g"), ("gemini-flash", "m")):
    items = []
    for iid in sorted(mats):
        for p in sorted((HERE / "runs" / model / iid).glob("run_*_l[cp]*_rep?.json")):
            if not (p.name.startswith("run_C0_") or p.name.startswith("run_px")): continue
            d = json.loads(p.read_text(encoding="utf-8")); items.append((iid, d, p))
    random.Random(20260903 + len(tag) * 7).shuffle(items)
    packs = [items[i:i + 6] for i in range(0, len(items), 6)]
    for n, pk in enumerate(packs, 1):
        name = f"{tag}pack{n:02d}"; out = []
        for j, (iid, d, p) in enumerate(pk, 1):
            m = mats[iid]; it = f"{name}-{j}"
            out.append({"item": it, "options": m["options"], "stub": STUB.get(iid, ""),
                        "facts": [{"id": f["id"], "text": f["text"]} for f in m["facts"]],
                        "essays": d["essays"], "notes": d["notes"], "final_answer": d.get("final_poll") or ""})
            key.append({"item": it, "model": model, "issue_id": iid, "run_id": d["run_id"], "value_set": d["value_set"],
                        "script": d["script"], "script_line": d.get("script_line") or "", "path": str(p.relative_to(HERE.parent.parent))})
        (OUT / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(model, "items", len(items), "packs", len(packs))
(OUT / "KEY.json").write_text(json.dumps(key, ensure_ascii=False, indent=0), encoding="utf-8")
