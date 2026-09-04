"""[민옥 트랙] gpt·gemini 정독 채점용 블라인드 팩 생성 — 하이쿠 coderpacks_haiku_llm_20260902 와 같은 형식.
같은 11재료 × 가치 A/B × C0·C2 × 3반복 = 모델당 132판. 출력: coderpacks_gptgem_llm_20260902/{packNN.json, KEY.json, MATERIALS11.json}
사용: python build_packs_gptgem.py [gpt|gemini-flash]  (모델별로 따로 실행 — VM 시간 제한)"""
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = HERE / "coderpacks_gptgem_llm_20260902"; OUT.mkdir(exist_ok=True)
SRC = HERE / "coderpacks_haiku_llm_20260902"
mats = json.load(open(SRC / "MATERIALS11.json", encoding="utf-8"))
if not (OUT / "MATERIALS11.json").exists():
    (OUT / "MATERIALS11.json").write_text(json.dumps(mats, ensure_ascii=False, indent=1), encoding="utf-8")
STUB = {}
for mp in (HERE / "materials").glob("*.json"):
    try: md = json.loads(mp.read_text(encoding="utf-8")); STUB[md.get("issue_id")] = md.get("stub") or ""
    except Exception: pass
model = sys.argv[1]
tag = {"gpt": "g", "gemini-flash": "m"}[model]
items = []
for iid in sorted(mats):
    for p in sorted((HERE / "runs" / model / iid).glob("run_C[02]_[AB]_rep*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        items.append((iid, d, p))
random.Random(20260902 + len(tag)).shuffle(items)
key = []; packs = [items[i:i + 6] for i in range(0, len(items), 6)]
for n, pk in enumerate(packs, 1):
    name = f"{tag}pack{n:02d}"; out = []
    for j, (iid, d, p) in enumerate(pk, 1):
        m = mats[iid]; it = f"{name}-{j}"
        out.append({"item": it, "options": m["options"], "stub": STUB.get(iid, ""), 
                    "facts": [{"id": f["id"], "text": f["text"]} for f in m["facts"]],
                    "essays": d["essays"], "notes": d["notes"], "final_answer": d.get("final_poll") or ""})
        key.append({"item": it, "model": model, "issue_id": iid, "run_id": d["run_id"], "value_set": d["value_set"], "script": d["script"],
                    "aligned": d.get("aligned"), "script_line": d.get("script_line") or "", "path": str(p.relative_to(HERE.parent.parent))})
    (OUT / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
kp = OUT / "KEY.json"
old = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else []
old = [k for k in old if k["model"] != model]
kp.write_text(json.dumps(old + key, ensure_ascii=False, indent=0), encoding="utf-8")
print(model, "items", len(items), "packs", len(packs))
