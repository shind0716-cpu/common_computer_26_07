# -*- coding: utf-8 -*-
"""「약해짐」을 넣은 2판 점검 채점 — 사전고정 「정정 4」 그대로. 호출 0."""
import json, math, re, pathlib, collections

V = pathlib.Path(__file__).resolve().parent.parent / "variant"
cells = {c["wid"]: c for c in json.loads((V / "_SAMPLE2.json").read_text(encoding="utf-8"))}
OK = {"그대로", "약해짐", "달라짐", "없음"}
got, bad = {}, []
for p in sorted(V.glob("OUT_W_*.md")):
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(W-\d{3})\s*\|\s*([^|]+?)\s*\|", line)
        if not m: continue
        if m.group(1) not in cells or m.group(2).strip() not in OK:
            bad.append((p.name, line.strip())); continue
        got[m.group(1)] = m.group(2).strip()

W = []
def w(s=""): print(s); W.append(s)
def wilson(k, n, z=1.96):
    if not n: return (0.0, 0.0)
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return max(0.0, c-h)*100, min(1.0, c+h)*100

w("# 「달라짐」 점검 2판 — 눈금에 「약해짐」을 넣고 다시")
w("")
w("> 기계 산출물. 사전고정 「정정 4」의 표본·눈금·판정선 그대로.")
w(f"> 표본 80칸은 1판과 **같은 칸**이다(눈금만 바꾼 대조). 양성 대조 5칸을 섞어 넣었다.")
w("")
w(f"거둔 판정 {len(got)}/{len(cells)} · 형식 어긋남 {len(bad)}")

ctrl = {k: v for k, v in got.items() if cells[k]["kind"] == "대조"}
samp = {k: v for k, v in got.items() if cells[k]["kind"] == "표본"}

w("\n## 먼저 — 이 검사를 믿어도 되나 (양성 대조 5칸)\n")
w("READ60 이 「변형」이라 판정한 칸이다. 1판 눈금에서는 **5칸 전부 「그대로」**가 나왔다.")
w("")
w("| 칸 | 우리 판정 |")
w("|---|---|")
for k in sorted(ctrl): w(f"| {k} | **{ctrl[k]}** |")
hit = sum(1 for v in ctrl.values() if v in ("약해짐", "달라짐"))
w(f"\n**잡은 것 {hit}/5** → 판정선 3칸: "
  + ("**통과 — 이 검사는 작동한다.**" if hit >= 3
     else "**빗나감 — 이번 검사도 못 믿는다. 아래 표본 결과를 쓰지 마라.**"))

w("\n## 표본 80칸\n")
n = len(samp); c = collections.Counter(samp.values())
w("| 판정 | 칸 | 비율 |")
w("|---|---:|---:|")
for k in ("그대로", "약해짐", "달라짐", "없음"):
    w(f"| {k} | {c[k]} | {c[k]/n*100:.1f}% |")
bad_n = c["약해짐"] + c["달라짐"]
lo, hi = wilson(bad_n, n)
w(f"\n**약해짐 + 달라짐 = {bad_n}/{n} = {bad_n/n*100:.1f}%** (95% 구간 {lo:.1f}\~{hi:.1f}%)")
w(f"\n1판(약해짐 칸이 없던 눈금)에서는 같은 80칸이 달라짐 0.0% 였다."
  f" 눈금에 한 칸을 더하니 **{bad_n/n*100:.1f}%** 가 됐다.")
if hit >= 3:
    r = bad_n/n*100
    w(f"\n판정선(정정 4): " + ("**10% 이상 — 팩2 「있음」 수치를 그대로 못 쓴다.**" if r >= 10
                              else "**10% 미만 — 단서를 달고 쓴다.**"))

w("\n## 층별\n")
w("| 갈래 | 쪽 | 수첩 | 칸 | 그대로 | 약해짐 | 달라짐 | 없음 |")
w("|---|---|---|---:|---:|---:|---:|---:|")
by = collections.defaultdict(collections.Counter)
for k, v in samp.items():
    x = cells[k]; by[(x["arm"], x["side"], x["stage"])][v] += 1
for k in sorted(by):
    b = by[k]; m = sum(b.values())
    w(f"| {k[0]} | {k[1]} | {k[2]} | {m} | {b['그대로']} | {b['약해짐']} | {b['달라짐']} | {b['없음']} |")

w("\n## 약해짐·달라짐으로 판정된 칸 — 전건\n")
for k in sorted(x for x in samp if samp[x] in ("약해짐", "달라짐")):
    x = cells[k]
    w(f"**{k}** ({samp[k]}) · {x['issue']} · {x['arm']} {x['side']} · {x['stage']} 수첩")
    w(f"> 사실 — {x['fact']}")
    w("")

w("\n## 읽을 때\n")
w("- 팩2 가 **「있음」이라 한 칸만** 본다. 「있음」의 정밀도이지 판독 전체의 정확도가 아니다.")
w("- 코더가 사람이 아니고, 이 점검도 코더 하나가 읽었다.")
w("- 1판 산출물(`OUT_V_*.md` · `SCORE_VARIANT.md`)은 지우지 않았다.")

(V / "SCORE_VARIANT2.md").write_text("\n".join(W) + "\n", encoding="utf-8")
print("\n→ variant/SCORE_VARIANT2.md 썼다.")
