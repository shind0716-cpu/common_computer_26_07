# -*- coding: utf-8 -*-
"""수첩 문장 갈래 팩을 짓는다. 조건 표기는 가리고 열쇠는 따로. 호출 0."""
import json, glob, os, re, random, hashlib
R   = os.environ.get("PC_ROOT", "/mnt/user-data/uploads/ms/common_computer_26_07/experiments/pressure_category")
OUT = os.environ.get("PACK_OUT", "/home/claude/pack3")
SEED, PER_CELL, PER_PACK = 20260902, 4, 8

IIDS = ["issue_childcare","issue_euthanasia","issue_examaccom","issue_remotewatch",
        "issue_workmind","issue_recycling_room","issue_smoking_area_party",
        "issue_cat_feeding_days_list","issue_eol","issue_shelter","issue_parentalreturn"]
mats = {}
for p in glob.glob(f"{R}/materials/*.json"):
    d = json.load(open(p, encoding="utf-8"))
    if d.get("issue_id") in IIDS: mats[d["issue_id"]] = d

SPLIT = re.compile(r"(?<=[.!?])\s+|\n+|(?=[①②③④⑤⑥])|·\s")
def sents(t):
    return [s.strip(" ·-—*") for s in SPLIT.split(t) if len(s.strip(" ·-—*")) >= 4]

pool = []
for iid in IIDS:
    m = mats[iid]
    for p in sorted(glob.glob(f"{R}/runs/gpt/{iid}/run_*.json")):
        if ".partial" in p: continue
        d = json.load(open(p, encoding="utf-8")); rid = d["run_id"]; h = rid.split("_")[0]
        if h in ("C0","C2") and rid.split("_")[1] in ("A","B"):
            cond = "가치·압박없음" if h == "C0" else "가치·반대편"
        elif rid.startswith("C0_wonchik"): cond = "원칙·압박없음"
        elif rid.startswith("pbw_"):       cond = "원칙·반대편"
        else: continue
        for k, note in enumerate(d["notes"]):
            ss = sents(note)
            if len(ss) >= 3:
                pool.append(dict(iid=iid, file=os.path.basename(p), run_id=rid,
                                 cond=cond, stage=k, sents=ss,
                                 statement=d.get("value_statement", "")))

rnd = random.Random(SEED)
cells = {}
for r in pool: cells.setdefault((r["cond"], r["stage"]), []).append(r)
sample = []
for key_ in sorted(cells):
    v = cells[key_][:]; rnd.shuffle(v); sample += v[:PER_CELL]
rnd.shuffle(sample)

key, cards = {}, []
for n, r in enumerate(sample, 1):
    nid = f"N-{n:02d}"; m = mats[r["iid"]]
    anchors = [(f.get("anchor") or "").strip() for f in m["facts"] if f.get("anchor")]
    ctrl = {}
    CONCL = re.compile(r"결론|권고|판단|택한|고른|선택한|우선순위")
    for j, s in enumerate(r["sents"], 1):
        sid = f"s{j:02d}"
        if re.match(r"^(결론|판단|권고|최종)\s*[:：]", s):
            ctrl[sid] = "결론"
        elif any(a and a in s for a in anchors) and not CONCL.search(s) and len(s) < 90:
            ctrl[sid] = "사실"
    key[nid] = dict(issue_id=r["iid"], file=r["file"], run_id=r["run_id"],
                    cond=r["cond"], stage=r["stage"], n_sents=len(r["sents"]),
                    controls=ctrl)
    facts = "\n".join(f"- {f['text']}" for f in m["facts"])
    body = "\n".join(f"| {f's{j:02d}'} | {s} |  |  |" for j, s in enumerate(r["sents"], 1))
    cards.append(f"""## {nid}

**선택지**: {' · '.join(m['options'])}

**처음에 준 사실 열둘**

{facts}

**이 판에 준 문장**

> {r['statement'].strip()}

**판정표 {nid}** — 문장마다 갈래 하나와 「새 내용」 하나.

| 번호 | 문장 | 갈래 | 새 내용 |
|---|---|---|---|
{body}
""")

head = open(f"{OUT}/tools/head.md", encoding="utf-8").read()
os.makedirs(f"{OUT}/packs", exist_ok=True)
np_ = 0
for b in range(0, len(cards), PER_PACK):
    np_ += 1
    open(f"{OUT}/packs/PACK_S_{np_:02d}.md", "w", encoding="utf-8").write(
        head.replace("{{NO}}", f"{np_:02d}").replace("{{N}}", str(len(cards[b:b+PER_PACK])))
        + "\n---\n\n" + "\n---\n\n".join(cards[b:b+PER_PACK]))
json.dump(key, open(f"{OUT}/_KEY_S.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
lines = [f"{hashlib.sha256(open(p,'rb').read()).hexdigest()[:12]}  packs/{os.path.basename(p)}"
         for p in sorted(glob.glob(f"{OUT}/packs/PACK_S_*.md"))]
open(f"{OUT}/PACK_HASHES.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
ns = sum(k["n_sents"] for k in key.values())
nc = sum(len(k["controls"]) for k in key.values())
print(f"수첩 {len(sample)} · 문장 {ns} · 팩 {np_} × {PER_PACK}장")
print(f"자연 발생 대조 {nc}칸 (표식 그대로 낀 문장 · 「결론:」으로 시작하는 문장)")
import collections
print(dict(collections.Counter(f"{r['cond']}/r{r['stage']}" for r in sample)))
