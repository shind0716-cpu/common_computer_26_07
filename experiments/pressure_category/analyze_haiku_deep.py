"""[민옥 트랙 · 압박×카테고리] 하이쿠 A/B 813판 심화 — 9/1 기준선·라운드 집계가 안 본 축 (콜 0).

축:
  A 편향 사멸 — 죽는 사실은 "그때 입장"에 불리한 쪽인가 (favors × 라운드 입장)
  B 반복 흔들림 — 같은 칸 3반복이 최종 선택·수첩 사실 집합에서 얼마나 같은가
  C 사실 경로 — 수첩 3번에 걸친 사실별 생존 패턴(부활 포함)
  D 글 대 수첩 — 에세이가 쓰는 사실과 수첩이 남기는 사실
  E 사실 속성 — 숫자/비숫자·목록 위치·favors=정렬 이 생존을 가르나
  F 수첩 길이 — 예산 사용량과 사실 수

잣대: aggregate_all11.probe (레벨1 그대로 / 레벨≤3 접고 깎아서). 두 값 병기.
범위: runs/claude-haiku 의 A/B 720판 (C0·C1·C2). 재료 지문 불일치 판은 따로 센다.
사용: PYTHONUTF8=1 python analyze_haiku_deep.py  → DEEP_haiku_<날짜>.json / .md
"""
from __future__ import annotations
import json, sys, collections, itertools, statistics, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_pressure import discover_materials, load_materials
from aggregate_all11 import probe, norm

DATE = "2026-09-02"
reg = {iid: load_materials(p) for iid, p in discover_materials().items()}
labels = {}
lj = json.load(open(HERE / "LABELS_c2_discourse_haiku_2026-09-01.json", encoding="utf-8"))
lrows = lj if isinstance(lj, list) else (lj.get("rows") or next(v for v in lj.values() if isinstance(v, list)))
for r in lrows:
    labels[(r["issue_id"], r["run_id"])] = r

runs = []
for p in sorted((HERE / "runs" / "claude-haiku").glob("*/run_*.json")):
    if p.name.endswith(".final2.json"): continue
    d = json.loads(p.read_text(encoding="utf-8"))
    if d["meta"].get("dry"): continue
    if d.get("value_set") not in ("A", "B"): continue
    mat = reg.get(d["issue_id"])
    if not mat: continue
    d["_mat"] = mat
    d["_stale"] = (d.get("materials_hash") != mat["_hash"])
    runs.append(d)

def opts(mat): return mat["options"]
def choice_of(d):
    poll = (d.get("final_poll") or "").strip().strip("'\"*` \n")
    o = opts(d["_mat"])
    if poll in o: return poll
    pos = {x: (d.get("final_poll") or "").rfind(x) for x in o}
    hit = [x for x in o if pos[x] >= 0]
    return max(hit, key=lambda x: pos[x]) if hit else None

def alive(anchor, text, loose):
    lv = probe(anchor, text)[0]
    return lv == 1 if not loose else lv >= 1

out = {"date": DATE, "n_runs": len(runs), "n_stale": sum(d["_stale"] for d in runs)}
by_script = collections.Counter(d["script"] for d in runs)
out["by_script"] = dict(by_script)
stale_by_issue = collections.Counter(d["issue_id"] for d in runs if d["_stale"])
out["stale_issues"] = dict(stale_by_issue)
cur = [d for d in runs if not d["_stale"]]      # 본 분석 모수
out["n_current"] = len(cur)

# ---------- A. 편향 사멸 ----------
# 라운드 입장: C2 는 LABELS r0..r3 (에세이 입장), 나머지는 최종 선택 대리.
def stance_at(d, k):
    lb = labels.get((d["issue_id"], d["run_id"]))
    if lb and lb.get(f"r{k}") in opts(d["_mat"]): return lb[f"r{k}"]
    return None
A = {}
for loose in (False, True):
    key = "loose" if loose else "strict"
    tab = collections.defaultdict(lambda: [0, 0])   # (script, side, k) -> [alive, total]
    flipsurv = collections.defaultdict(lambda: [0, 0])  # 진짜뒤집힘 판: (phase, side) 
    for d in cur:
        mat = d["_mat"]; notes = d.get("notes") or []
        fin = choice_of(d)
        for k, note in enumerate(notes[:3]):
            st = stance_at(d, k) if d["script"] == "C2" else fin
            if st is None: continue
            for f in mat["facts"]:
                side = "pro" if f["favors"] == st else "con"
                a = alive(f["anchor"], note, loose)
                tab[(d["script"], side, k)][0] += a; tab[(d["script"], side, k)][1] += 1
        # 진짜뒤집힘 판: 전향 전/후 라운드에서 옛 입장(=r0) 편 사실 vs 새 입장 편 사실
        lb = labels.get((d["issue_id"], d["run_id"]))
        if lb and lb.get("label") == "진짜뒤집힘" and lb.get("shift_round") not in (None, ""):
            s = int(lb["shift_round"]); old = lb["r0"]
            for k, note in enumerate(notes[:3]):
                phase = "before" if k < s else "after"
                for f in mat["facts"]:
                    side = "old" if f["favors"] == old else "new"
                    a = alive(f["anchor"], note, loose)
                    flipsurv[(phase, side, k)][0] += a; flipsurv[(phase, side, k)][1] += 1
    A[key] = {"|".join(map(str, kk)): v for kk, v in tab.items()}
    A[key + "_flip"] = {"|".join(map(str, kk)): v for kk, v in flipsurv.items()}
out["A"] = A

# ---------- B. 반복 흔들림 ----------
cells = collections.defaultdict(list)
for d in cur: cells[(d["issue_id"], d["script"], d["value_set"])].append(d)
B = {"final_agree": collections.Counter(), "jaccard": {}, "cells": {}}
jac = collections.defaultdict(list)
for k, ds in cells.items():
    ch = [choice_of(x) for x in ds]
    c = collections.Counter(ch); top = c.most_common(1)[0][1]
    pat = f"{top}/{len(ds)}" if None not in ch else f"{top}/{len(ds)}+unread"
    B["final_agree"][(k[1], pat)] += 1
    sets = []
    for x in ds:
        ln = (x.get("notes") or [""])[-1]
        sets.append({f["id"] for f in x["_mat"]["facts"] if alive(f["anchor"], ln, True)})
    js = []
    for s1, s2 in itertools.combinations(sets, 2):
        u = s1 | s2; js.append(len(s1 & s2) / len(u) if u else 1.0)
    if js: jac[k[1]].append(statistics.mean(js))
    B["cells"]["|".join(k)] = {"final": ch, "jaccard": round(statistics.mean(js), 3) if js else None,
                               "sizes": [len(s) for s in sets]}
B["final_agree"] = {"|".join(k): v for k, v in B["final_agree"].items()}
B["jaccard"] = {s: {"mean": round(statistics.mean(v), 3), "n_cells": len(v),
                    "share_lt_0.34": round(sum(x < 0.34 for x in v) / len(v), 3)} for s, v in jac.items()}
out["B"] = B

# ---------- C. 사실 경로 ----------
C = {}
for loose in (False, True):
    key = "loose" if loose else "strict"
    pat = collections.defaultdict(collections.Counter)
    resur = []
    for d in cur:
        notes = d.get("notes") or []
        if len(notes) < 3: continue
        for f in d["_mat"]["facts"]:
            bits = "".join("1" if alive(f["anchor"], n, loose) else "0" for n in notes[:3])
            pat[d["script"]][bits] += 1
            if "01" in bits:
                stub_has = f["anchor"] in d["_mat"]["stub"]
                lines = " ".join(d.get("script_lines") or []) + (d.get("script_r0_line") or "")
                resur.append({"issue": d["issue_id"], "run": d["run_id"], "fact": f["id"], "bits": bits,
                              "in_stub": stub_has, "in_script": f["anchor"] in lines})
    C[key] = {s: dict(c) for s, c in pat.items()}
    C[key + "_resurrect"] = {"n": len(resur), "in_stub": sum(r["in_stub"] for r in resur),
                             "in_script": sum(r["in_script"] for r in resur), "neither": sum((not r["in_stub"] and not r["in_script"]) for r in resur),
                             "examples": resur[:12]}
out["C"] = C

# ---------- D. 글 대 수첩 ----------
D = {}
ess = collections.defaultdict(list); newfromnowhere = collections.defaultdict(lambda: [0, 0])
for d in cur:
    essays = d.get("essays") or []; notes = d.get("notes") or []
    for k, e in enumerate(essays[:4]):
        ids = {f["id"] for f in d["_mat"]["facts"] if alive(f["anchor"], e, True)}
        ess[(d["script"], k)].append(len(ids))
        if k >= 1 and len(notes) >= k:
            prev = {f["id"] for f in d["_mat"]["facts"] if alive(f["anchor"], notes[k - 1], True)}
            newfromnowhere[(d["script"], k)][0] += len(ids - prev); newfromnowhere[(d["script"], k)][1] += len(ids)
D["essay_anchors_mean"] = {"|".join(map(str, k)): round(statistics.mean(v), 2) for k, v in ess.items()}
D["essay_anchor_not_in_prev_note"] = {"|".join(map(str, k)): v for k, v in newfromnowhere.items()}
# 수첩 표식 수: 참고(라운드 집계와 대조용)
nt = collections.defaultdict(list)
for d in cur:
    for k, n in enumerate((d.get("notes") or [])[:3]):
        nt[(d["script"], k)].append(sum(alive(f["anchor"], n, True) for f in d["_mat"]["facts"]))
D["note_anchors_mean_loose"] = {"|".join(map(str, k)): round(statistics.mean(v), 2) for k, v in nt.items()}
out["D"] = D

# ---------- E. 사실 속성 ----------
E = collections.defaultdict(lambda: [0, 0])
for d in cur:
    ln = (d.get("notes") or [""])[-1]; mat = d["_mat"]
    incats = set(d.get("value_categories") or [])
    for i, f in enumerate(mat["facts"]):
        a = alive(f["anchor"], ln, True)
        num = bool(re.search(r"\d", f["anchor"]))
        E[("numeric", num)][0] += a; E[("numeric", num)][1] += 1
        E[("pos", i // 4)][0] += a; E[("pos", i // 4)][1] += 1      # 목록 앞/중/뒤 4개씩
        E[("favors_aligned", f["favors"] == d.get("aligned"))][0] += a; E[("favors_aligned", f["favors"] == d.get("aligned"))][1] += 1
        E[("in_valueset", f["category"] in incats)][0] += a; E[("in_valueset", f["category"] in incats)][1] += 1
        E[("about_aligned", f.get("about_option") == d.get("aligned"))][0] += a; E[("about_aligned", f.get("about_option") == d.get("aligned"))][1] += 1
        E[("anchor_len", min(len(f["anchor"]) // 3, 4))][0] += a; E[("anchor_len", min(len(f["anchor"]) // 3, 4))][1] += 1
out["E"] = {"|".join(map(str, k)): v for k, v in E.items()}

# ---------- F. 수첩 길이 ----------
F = collections.defaultdict(list); trunc = collections.Counter()
for d in cur:
    for k, n in enumerate((d.get("notes") or [])[:3]):
        F[(d["script"], k)].append(len(n))
    trunc[d["meta"].get("note_truncated")] += 1
lens = [len(n) for d in cur for n in (d.get("notes") or [])[:3]]
cnts = [sum(alive(f["anchor"], n, True) for f in d["_mat"]["facts"]) for d in cur for n in (d.get("notes") or [])[:3]]
def corr(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    sx = sum((a - mx) ** 2 for a in x) ** .5; sy = sum((b - my) ** 2 for b in y) ** .5
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)
out["F"] = {"len_mean": {"|".join(map(str, k)): round(statistics.mean(v)) for k, v in F.items()},
            "len_quartiles": statistics.quantiles(lens, n=4), "over_budget": sum(l > 500 for l in lens),
            "truncated_flag": dict(trunc), "corr_len_anchors": round(corr(lens, cnts), 3),
            "anchors_by_len_bin": None}
bins = collections.defaultdict(list)
for l, c in zip(lens, cnts): bins[min(l // 100, 5)].append(c)
out["F"]["anchors_by_len_bin"] = {f"{k*100}-": [round(statistics.mean(v), 2), len(v)] for k, v in sorted(bins.items())}

json.dump(out, open(HERE / f"DEEP_haiku_{DATE}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: out[k] for k in ("n_runs", "n_stale", "n_current", "by_script", "stale_issues")}, ensure_ascii=False))
