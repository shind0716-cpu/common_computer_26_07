# -*- coding: utf-8 -*-
"""팩 「뜻2」·「길2」를 짓는다. 조건은 가리고 열쇠는 따로 낸다. 호출 0."""
import json, glob, os, random, hashlib
R   = os.environ.get("PC_ROOT", "/mnt/user-data/uploads/ms/common_computer_26_07/experiments/pressure_category")
OUT = os.environ.get("PACK_OUT", "/home/claude/pack2")
SEED = 20260902

IIDS = ["issue_childcare","issue_euthanasia","issue_examaccom","issue_remotewatch",
        "issue_workmind","issue_recycling_room","issue_smoking_area_party",
        "issue_cat_feeding_days_list","issue_eol","issue_shelter","issue_parentalreturn"]

mats = {}
for p in glob.glob(f"{R}/materials/*.json"):
    d = json.load(open(p, encoding="utf-8"))
    if d.get("issue_id") in IIDS: mats[d["issue_id"]] = d
assert len(mats) == 11, f"재료 {len(mats)}벌 — 11 이어야 한다"

runs = []
for iid in IIDS:
    for p in sorted(glob.glob(f"{R}/runs/gpt/{iid}/run_*.json")):
        if ".partial" in p: continue
        d = json.load(open(p, encoding="utf-8"))
        rid = d["run_id"]
        arm = ("value" if rid.split("_")[0] in ("C0","C2") and rid.split("_")[1] in ("A","B")
               else "belief" if (rid.startswith("C0_wonchik") or rid.startswith("pbw_")) else None)
        if arm: runs.append((iid, os.path.basename(p), d, arm))
assert len(runs) == 198, f"판 {len(runs)} — 198 이어야 한다"

order = list(range(len(runs))); random.Random(SEED).shuffle(order)
key, M, P = {}, [], []
for n, i in enumerate(order, 1):
    iid, fn, d, arm = runs[i]
    pid = f"P-{n:03d}"; m = mats[iid]
    key[pid] = {"issue_id": iid, "file": fn, "run_id": d["run_id"], "arm": arm,
                "script": d["script"], "value_set": d["value_set"], "rep": d["rep"],
                "aligned": d.get("aligned"), "final_poll": d.get("final_poll"),
                "value_categories": d.get("value_categories"),
                "options": m["options"], "materials_hash": d.get("materials_hash")}
    opt = " · ".join(f"{j+1}) {o}" for j, o in enumerate(m["options"]))
    facts = "\n".join(f"- **{f['id']}** ({f['category']}) {f['text']}" for f in m["facts"])
    rows12 = "\n".join(f"| {f['id']} |  |  |" for f in m["facts"])
    notes = d["notes"]
    M.append(f"""## {pid}

**선택지**: {opt}

**처음에 준 사실 열둘**

{facts}

### 첫 수첩

> {notes[0].strip()}

### 마지막 수첩

> {notes[-1].strip()}

**판정표 {pid}**

| 사실 | 첫수첩 | 마지막수첩 |
|---|---|---|
{rows12}
""")
    essays = "\n\n".join(f"### 글 {j+1}\n\n> {e.strip()}" for j, e in enumerate(d["essays"]))
    P.append(f"""## {pid}

**선택지**: {opt}

{essays}

**판정표 {pid}**

| 글 | 지지 |
|---|---|
| 글1 |  |
| 글2 |  |
| 글3 |  |
| 글4 |  |
""")

def emit(cards, head_path, subdir, prefix, per):
    head = open(head_path, encoding="utf-8").read()
    os.makedirs(f"{OUT}/{subdir}", exist_ok=True)
    n = 0
    for b in range(0, len(cards), per):
        n += 1
        body = head.replace("{{NO}}", f"{n:02d}").replace("{{N}}", str(len(cards[b:b+per])))
        open(f"{OUT}/{subdir}/{prefix}_{n:02d}.md", "w", encoding="utf-8").write(
            body + "\n---\n\n" + "\n---\n\n".join(cards[b:b+per]))
    return n

nm = emit(M, f"{OUT}/tools/head_meaning2.md", "meaning2", "PACK_M", 3)
np_ = emit(P, f"{OUT}/tools/head_path2.md",   "path2",    "PACK_P", 6)
json.dump(key, open(f"{OUT}/_KEY_2026-09-02.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)

lines = []
for sub, pre in (("meaning2","PACK_M"), ("path2","PACK_P")):
    for p in sorted(glob.glob(f"{OUT}/{sub}/{pre}_*.md")):
        lines.append(f"{hashlib.sha256(open(p,'rb').read()).hexdigest()[:12]}  {sub}/{os.path.basename(p)}")
open(f"{OUT}/PACK_HASHES.txt","w",encoding="utf-8").write("\n".join(lines)+"\n")

print(f"판 {len(runs)}  (가치 {sum(1 for r in runs if r[3]=='value')} · 신념 {sum(1 for r in runs if r[3]=='belief')})")
print(f"뜻2  팩 {nm}개 × 3판 · 판정 칸 {len(runs)*12*2}")
print(f"길2  팩 {np_}개 × 6판 · 판정 칸 {len(runs)*4}")
