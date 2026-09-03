# -*- coding: utf-8 -*-
"""수첩 글 구성 분석 — 겹침을 풀고 수첩이 무엇으로 차 있는지 센다. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/compose.py

사전고정 「정정 1」 그대로다. 축을 둘로 갈라 센다 —

  역할 = 코더 갈래 (사실 · 결론 · 되풀이 · 단서 · 지시 · 그밖)
  출처 = 기계 표식 포함 (aggregate_all11.probe 기준 ②) — 이 트랙이 쓰는 자

「사실 몫」은 출처 축으로 읽는다. 출처 축은 말 바꿔 쓴 것을 놓치므로 **하한**이다.
산출: COMPOSE_S.md
"""
import json, glob, os, re, sys, pathlib, statistics as st, collections

H = pathlib.Path(__file__).resolve().parent.parent
R = os.environ.get("PC_ROOT", str(H.parent))
sys.path.insert(0, R)
try:
    import aggregate_all11 as A
    def has_anchor(anchor, text):
        return 0 < A.probe(anchor, text)[0] <= 2
    MACHINE = "기준 ②(그대로+접어서) · aggregate_all11.probe"
except Exception as e:
    sys.exit(f"aggregate_all11 을 못 불러왔다({e}). 트랙과 다른 자를 조용히 쓰지 않는다.")

KEY = json.loads((H / "_KEY_S.json").read_text(encoding="utf-8"))
G = json.loads((H / "_COLLECTED_S.json").read_text(encoding="utf-8"))
mats = {}
for p in glob.glob(f"{R}/materials/*.json"):
    d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    if d.get("issue_id"): mats[d["issue_id"]] = d

# ── 팩에서 문장 원문을 되찾는다 (판독물이 아니라 팩이 정본) ──────────
sent = {}
for p in sorted(glob.glob(str(H / "packs" / "PACK_S_*.md"))):
    t = pathlib.Path(p).read_text(encoding="utf-8")
    for m in re.finditer(r"^##\s+(N-\d{2})\s*$", t, re.M):
        nid = m.group(1); blk = t[m.end():]
        nx = re.search(r"^##\s+N-\d{2}\s*$", blk, re.M)
        if nx: blk = blk[:nx.start()]
        for sm in re.finditer(r"^\s*\|?\s*(s\d\d)\s*[|:.]\s*(.+?)\s*$", blk, re.M):
            sent[(nid, sm.group(1))] = sm.group(2).strip().strip("|").strip()

GAL = ["사실", "결론", "되풀이", "단서", "지시", "그밖"]
W = []
def w(s=""): print(s); W.append(s)
pct = lambda k, n: f"{k/n*100:.0f}%" if n else "—"

rows = []
for nid, k in KEY.items():
    facts = mats[k["issue_id"]]["facts"]
    for sid, (gal, new) in G[nid].items():
        s = sent.get((nid, sid), "")
        hit = any(has_anchor((f.get("anchor") or "").strip(), s)
                  for f in facts if (f.get("anchor") or "").strip())
        rows.append(dict(nid=nid, sid=sid, cond=k["cond"], stage=k["stage"],
                         gal=gal, new=new, anchor=hit, text=s, chars=len(s)))

w("# 수첩 글 구성 — 겹침을 풀고 다시 (2026-09-03)")
w("")
w("> 기계 산출물. 사전고정 「정정 1」 그대로. 축 둘로 갈라 센다.")
w(f"> 출처 축 자 = {MACHINE}. **말 바꿔 쓴 것을 놓치므로 하한이다.**")
w("")
w(f"수첩 {len(KEY)}장 · 문장 {len(rows)}개 · 전부 gpt")

# ── 1. 겹침이 얼마나 되나 ──────────────────────────────────────────
w("\n## 1. 갈래(역할) × 표식(출처) — 겹침의 크기\n")
ct = collections.Counter((r["gal"], r["anchor"]) for r in rows)
w(f"{'갈래':<8}{'문장':>5}{'표식 있음':>10}{'몫':>7}")
for g in GAL:
    n = sum(ct[(g, x)] for x in (True, False))
    if not n: continue
    w(f"{g:<8}{n:>5}{ct[(g, True)]:>10}{pct(ct[(g, True)], n):>7}")
tot = len(rows); anc = sum(1 for r in rows if r["anchor"])
w(f"{'합':<8}{tot:>5}{anc:>10}{pct(anc, tot):>7}")
w("")
danseo = [r for r in rows if r["gal"] == "단서"]
w(f"**「단서」로 매긴 {len(danseo)}문장 중 {sum(1 for r in danseo if r['anchor'])}개"
  f"({pct(sum(1 for r in danseo if r['anchor']), len(danseo))})에 재료 표식이 들어 있다.**")
w("역할로는 꼬리인데 출처로는 사실이다 — 이것이 대조 35칸이 어긋난 자리다.")

# ── 2. 사실 몫을 두 자로 ───────────────────────────────────────────
w("\n## 2. 사실 몫 — 자를 바꾸면\n")
gal_fact = sum(1 for r in rows if r["gal"] == "사실")
either = sum(1 for r in rows if r["gal"] == "사실" or r["anchor"])
w("| 세는 법 | 문장 | 몫 |")
w("|---|---:|---:|")
w(f"| 코더 갈래가 「사실」 (사전고정 판정용) | {gal_fact} | **{pct(gal_fact, tot)}** |")
w(f"| 기계 표식이 들어 있음 (출처 축·하한) | {anc} | **{pct(anc, tot)}** |")
w(f"| 둘 중 하나라도 (합집합) | {either} | **{pct(either, tot)}** |")
w("")
w("**S1 의 정본 판정은 첫 줄로 한다**(사전고정대로). 아래 둘은 참고다 — "
  "정정 1 에 적은 대로 보정판은 사후다.")

# ── 3. 조건별·라운드별 ────────────────────────────────────────────
for axis, name in (("cond", "조건"), ("stage", "라운드")):
    w(f"\n## 3-{1 if axis=='cond' else 2}. {name}별\n")
    keys = (["가치·압박없음", "가치·반대편", "원칙·압박없음", "원칙·반대편"]
            if axis == "cond" else sorted({r["stage"] for r in rows}))
    w(f"{name:<14}{'문장':>5}" + "".join(f"{g:>7}" for g in GAL)
      + f"{'표식':>7}{'새 내용':>8}")
    for kk in keys:
        sub = [r for r in rows if r[axis] == kk]
        if not sub: continue
        n = len(sub)
        lab = kk if axis == "cond" else f"수첩{kk+1}"
        w(f"{lab:<14}{n:>5}"
          + "".join(f"{pct(sum(1 for r in sub if r['gal']==g), n):>7}" for g in GAL)
          + f"{pct(sum(1 for r in sub if r['anchor']), n):>7}"
          + f"{pct(sum(1 for r in sub if r['new']=='예'), n):>8}")

# ── 4. 예산 — 사실이 실제로 차지하는 자리 ─────────────────────────
w("\n## 4. 예산 — 사실이 500자 중 몇 자를 쓰나\n")
per = collections.defaultdict(lambda: [0, 0, 0])   # 문장, 글자, 사실글자
for r in rows:
    p = per[r["nid"]]
    p[0] += 1; p[1] += r["chars"]
    if r["gal"] == "사실" or r["anchor"]: p[2] += r["chars"]
L = [v[1] for v in per.values()]
F = [v[2] for v in per.values()]
S = [v[0] for v in per.values()]
w(f"  수첩 한 장  문장 {st.mean(S):.1f}개 · 글자 {st.mean(L):.0f}자"
  f" (중앙 {st.median(L):.0f} · 최대 {max(L)})")
w(f"  그중 사실을 담은 문장  {st.mean(F):.0f}자 = {st.mean(F)/st.mean(L)*100:.0f}%")
w("")
w(f"  **500자 예산 가운데 실제로 쓴 것 {st.mean(L)/500*100:.0f}%,"
  f" 사실이 차지한 것 {st.mean(F)/500*100:.0f}%.**")
w("  예산이 남는데 밖이 안 적힌다면 이유는 자리가 아니다.")

# ── 5. 새 내용 ────────────────────────────────────────────────────
w("\n## 5. 새 내용 — 준 적 없는 것이 수첩에 생기나\n")
nw = [r for r in rows if r["new"] == "예"]
w(f"  {len(nw)}/{tot} = {pct(len(nw), tot)}")
c2 = collections.Counter(r["gal"] for r in nw)
w("  갈래별: " + " · ".join(f"{g} {c2[g]}" for g in GAL if c2[g]))
w("\n  새 내용으로 판정된 문장 몇 개 (원문 그대로):\n")
for r in [x for x in nw if x["gal"] in ("사실", "결론")][:5]:
    w(f"  - [{r['gal']}] {r['text'][:100]}")

(H / "COMPOSE_S.md").write_text("\n".join(W) + "\n", encoding="utf-8")
json.dump(rows, open(H / "_SENT_ROWS.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n→ COMPOSE_S.md · _SENT_ROWS.json 썼다.")
