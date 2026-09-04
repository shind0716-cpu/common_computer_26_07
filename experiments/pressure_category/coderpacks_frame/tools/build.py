# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 팩 「틀」 생성기 — 수첩이 스스로 세운 틀을 묻는다 (콜 0).

사전고정 `PREREG_frame_2026-09-03.md` 그대로다. 씨앗·짝짓기·가릴 것을 바꾸지 마라.

  뒤집힘 124판 전수 + 짝 124판 = 수첩 248장
  짝 = 같은 재료·같은 각본에서 최종 답이 정렬 답과 같은 판
       (세트까지 같은 것이 있으면 그쪽 먼저)

가린다: 최종 답 · 정렬 답 · 압박 방향 · 각본 · 세트
보인다: 사안 · 선택지 둘 · 준 가치문 · 사실 열둘 · 마지막 수첩

사용: PC_ROOT=<...>/experiments/pressure_category python tools/build.py
산출: packs/PACK_F_01..NN.md · _KEY_F.json · PACK_HASHES.txt
"""
import json, glob, os, random, hashlib, pathlib, sys, collections

H = pathlib.Path(__file__).resolve().parent.parent
R = os.environ.get("PC_ROOT", str(H.parent))
sys.path.insert(0, R)
import report_choice as RC  # noqa: E402  — 선택 판정 규칙을 그대로 쓴다

SEED = 20260903
PER_PACK = 8

mats = {}
for p in glob.glob(f"{R}/materials/*.json"):
    d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    if d.get("issue_id"): mats[d["issue_id"]] = d

rows = [r for r in RC.load() if r["모델"] == "gpt" and r["축"] in ("A", "B")
        and r["고름"] and r["정렬답"]]
flip = [r for r in rows if r["고름"] != r["정렬답"]]
keep = [r for r in rows if r["고름"] == r["정렬답"]]

rng = random.Random(SEED)
by3 = collections.defaultdict(list)   # 재료·각본·세트
by2 = collections.defaultdict(list)   # 재료·각본
for r in keep:
    by3[(r["재료"], r["각본"], r["세트"])].append(r)
    by2[(r["재료"], r["각본"])].append(r)
for d in (by3, by2):
    for v in d.values(): rng.shuffle(v)

used, pairs = set(), []
for f in sorted(flip, key=lambda x: (x["재료"], x["각본"], x["세트"], x["반복"])):
    cand = ([c for c in by3[(f["재료"], f["각본"], f["세트"])] if id(c) not in used]
            or [c for c in by2[(f["재료"], f["각본"])] if id(c) not in used])
    if not cand:
        print(f"  짝 못 찾음: {f['재료']} {f['각본']} {f['세트']}"); continue
    m = cand[0]; used.add(id(m))
    pairs.append((f, m))
print(f"짝지음 {len(pairs)}/{len(flip)}")

items = []
for f, m in pairs:
    items.append(dict(r=f, label="flip"))
    items.append(dict(r=m, label="keep"))
rng.shuffle(items)
for i, it in enumerate(items): it["fid"] = f"F-{i+1:03d}"

HEAD = pathlib.Path(H / "tools" / "head.md").read_text(encoding="utf-8")

def block(it):
    r = it["r"]; mat = mats[r["재료"]]
    run = json.loads(pathlib.Path(
        f"{R}/runs/gpt/{r['재료']}/{r['판']}").read_text(encoding="utf-8"))
    vs = (run.get("value_statement") or "").strip()
    facts = "\n".join(f"- **{f['id']}** ({f['category']}) {f['text']}" for f in mat["facts"])
    return (f"## {it['fid']}\n\n"
            f"**선택지** — 1) {mat['options'][0]} · 2) {mat['options'][1]}\n\n"
            f"**이 판에 준 가치문**\n\n> {vs}\n\n"
            f"**처음에 준 사실 열둘**\n\n{facts}\n\n"
            f"**마지막 수첩**\n\n> {run['notes'][-1]}\n\n---\n")

packs = [items[i:i+PER_PACK] for i in range(0, len(items), PER_PACK)]
(H / "packs").mkdir(exist_ok=True)
hashes = []
for pi, ch in enumerate(packs, 1):
    nn = f"{pi:02d}"
    body = HEAD.replace("{nn}", nn).replace("{n}", str(len(ch))) + "\n" + "".join(block(x) for x in ch)
    p = H / "packs" / f"PACK_F_{nn}.md"
    p.write_text(body, encoding="utf-8")
    hashes.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()[:12]}  packs/PACK_F_{nn}.md")

(H / "PACK_HASHES.txt").write_text("\n".join(hashes), encoding="utf-8")
key = {it["fid"]: dict(label=it["label"], issue=it["r"]["재료"], script=it["r"]["각본"],
                       vset=it["r"]["세트"], rep=it["r"]["반복"], file=it["r"]["판"],
                       aligned=it["r"]["정렬답"], final=it["r"]["고름"],
                       options=mats[it["r"]["재료"]]["options"]) for it in items}
(H / "_KEY_F.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"수첩 {len(items)}장 · 팩 {len(packs)}개 ({PER_PACK}장씩)")
print(f"  뒤집힘 {sum(1 for i in items if i['label']=='flip')} · "
      f"유지 {sum(1 for i in items if i['label']=='keep')}")
