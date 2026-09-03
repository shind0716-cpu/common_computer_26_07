# -*- coding: utf-8 -*-
"""열쇠를 열고 수첩이 무엇으로 차 있는지 센다. 호출 0."""
import json, os, collections, statistics as st
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = json.load(open(f"{H}/_KEY_S.json", encoding="utf-8"))
G   = json.load(open(f"{H}/_COLLECTED_S.json", encoding="utf-8"))
GAL = ["사실", "결론", "되풀이", "단서", "지시", "그밖"]
W = []
def w(s=""): print(s); W.append(s)

# ── 0. 대조가 서나 — 이걸 먼저 본다 ────────────────────────────────
ok = tot = 0
missed = collections.Counter()
for nid, k in KEY.items():
    for sid, want in k["controls"].items():
        tot += 1
        got = G[nid][sid][0]
        if got == want: ok += 1
        else: missed[f"{want}→{got}"] += 1
w(f"## 대조 {ok}/{tot} ({ok/tot*100:.0f}%)")
for k_, v in missed.most_common(6): w(f"   어긋남 {k_}: {v}")
w("   ※ 60% 아래면 검사가 눈이 하나 없는 것이다. 아래를 읽기 전에 그것부터 본다.\n")

# ── 1. 수첩은 무엇으로 차 있나 ────────────────────────────────────
by = collections.defaultdict(lambda: collections.Counter())
new = collections.defaultdict(lambda: [0, 0])
for nid, k in KEY.items():
    c = k["cond"]
    for sid, (g, n) in G[nid].items():
        by[c][g] += 1; by["전체"][g] += 1
        for t in (c, "전체"):
            new[t][1] += 1
            if n == "예": new[t][0] += 1
w("## 문장 갈래 (%)\n")
w(f"{'조건':<14}{'문장':>5}" + "".join(f"{g:>7}" for g in GAL) + f"{'새 내용':>8}")
for c in ("가치·압박없음", "가치·반대편", "원칙·압박없음", "원칙·반대편", "전체"):
    t = sum(by[c].values())
    if not t: continue
    w(f"{c:<14}{t:>5}" + "".join(f"{by[c][g]/t*100:>6.0f}%" for g in GAL)
      + f"{new[c][0]/new[c][1]*100:>7.0f}%")

# ── 2. 라운드별 ──────────────────────────────────────────────────
w("\n## 라운드별 (전체)\n")
byr = collections.defaultdict(lambda: collections.Counter())
for nid, k in KEY.items():
    for sid, (g, n) in G[nid].items(): byr[k["stage"]][g] += 1
for r in sorted(byr):
    t = sum(byr[r].values())
    w(f"  수첩{r+1}  " + " · ".join(f"{g} {byr[r][g]/t*100:.0f}%" for g in GAL))

# ── 3. 「500자가 병목」 검산 ──────────────────────────────────────
w("\n## 사실이 수첩에서 차지하는 몫\n")
t = sum(by["전체"].values())
w(f"  전체 문장 {t} 중 사실 {by['전체']['사실']} = {by['전체']['사실']/t*100:.0f}%")
w("  나머지가 무엇인지가 이 팩의 물음이었다. 위 표가 답이다.")
open(f"{H}/SCORE_S.md", "w", encoding="utf-8").write(
    "# 채점 — 수첩 문장 갈래\n\n> 기계 생성물. 손으로 고치지 마라 — `tools/score.py` 를 고친다.\n\n```\n"
    + "\n".join(W) + "\n```\n")
print("\n→ SCORE_S.md 썼다.")
