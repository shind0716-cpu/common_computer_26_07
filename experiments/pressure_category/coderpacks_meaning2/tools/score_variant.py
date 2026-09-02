# -*- coding: utf-8 -*-
"""「변형」 점검 채점 — 사전고정 「정정 3」 그대로. 호출 0.

    python tools/score_variant.py

**판독 결과를 보기 전에 썼다.** 판정선도 정정 3 에 미리 적힌 것을 그대로 옮겼다.
산출: variant/SCORE_VARIANT.md
"""
import json, glob, math, pathlib, re, collections

HERE = pathlib.Path(__file__).resolve().parent.parent
V = HERE / "variant"
S = json.loads((V / "_SAMPLE.json").read_text(encoding="utf-8"))
cells = {c["vid"]: c for c in S["cells"]}

OK = {"그대로", "달라짐", "없음"}
got, bad = {}, []
for p in sorted(V.glob("OUT_V_*.md")):
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(V-\d{3})\s*\|\s*([^|]+?)\s*\|", line)
        if not m: continue
        vid, verdict = m.group(1), m.group(2).strip()
        if vid not in cells or verdict not in OK:
            bad.append((p.name, line.strip())); continue
        got[vid] = verdict

W = []
def w(s=""): print(s); W.append(s)

w("# 「변형」 점검 결과 — 팩2 「있음」 칸이 원문과 같은 뜻인가")
w("")
w("> 기계 산출물. 사전고정 「정정 3」의 표본·물음·판정선 그대로.")
w("")
w(f"모집단 3,267칸(팩2가 「있음」이라 한 칸 전부) 중 층별 무작위 {S['n']}칸 · 씨앗 {S['seed']}")
w(f"거둔 판정 {len(got)}/{S['n']} · 형식 어긋남 {len(bad)}")
for b in bad[:5]: w(f"  어긋남 {b[0]}: {b[1]}")
if len(got) != S["n"]:
    w("\n**칸이 다 안 들어왔다. 빠진 것을 다시 돌린 뒤 채점한다.**")
    missing = sorted(set(cells) - set(got))
    w(f"빠진 칸 {len(missing)}: {', '.join(missing[:15])}")
    (V / "SCORE_VARIANT.md").write_text("\n".join(W) + "\n", encoding="utf-8")
    raise SystemExit(1)

def wilson(k, n, z=1.96):
    if not n: return (0.0, 0.0)
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0.0, c-h)*100, min(1.0, c+h)*100)

tot = collections.Counter(got.values())
n = len(got)
w("\n## 전체\n")
w("| 판정 | 칸 | 비율 |")
w("|---|---:|---:|")
for k in ("그대로", "달라짐", "없음"):
    w(f"| {k} | {tot[k]} | {tot[k]/n*100:.1f}% |")
lo, hi = wilson(tot["달라짐"], n)
w(f"\n**달라짐 {tot['달라짐']}/{n} = {tot['달라짐']/n*100:.1f}%** (95% 구간 {lo:.1f}\\~{hi:.1f}%)")
lo2, hi2 = wilson(tot["없음"], n)
w(f"**없음 {tot['없음']}/{n} = {tot['없음']/n*100:.1f}%** (95% 구간 {lo2:.1f}\\~{hi2:.1f}%)"
  " — 있음이 아니었어야 할 칸이다")

r = tot["달라짐"] / n * 100
verdict = ("**10% 이상 — 팩2의 「있음」 수치를 그대로 못 쓴다. 보정하거나 물린다.**" if r >= 10
           else "**5\\~10% — 단서를 달고 쓴다.**" if r >= 5
           else "**5% 미만 — 앞선 두 벌의 7.4%는 그 두 벌의 성질로 본다.**")
w(f"\n판정선(정정 3): {verdict}")

w("\n## 층별 — 변형이 한쪽에 몰리나\n")
w("| 갈래 | 쪽 | 수첩 | 칸 | 그대로 | 달라짐 | 없음 | 달라짐 비율 |")
w("|---|---|---|---:|---:|---:|---:|---:|")
by = collections.defaultdict(collections.Counter)
for vid, v in got.items():
    c = cells[vid]
    by[(c["arm"], c["side"], c["stage"])][v] += 1
for k in sorted(by):
    b = by[k]; m = sum(b.values())
    w(f"| {k[0]} | {k[1]} | {k[2]} | {m} | {b['그대로']} | {b['달라짐']} | {b['없음']} |"
      f" {b['달라짐']/m*100:.0f}% |")

w("\n## 달라짐으로 판정된 칸 — 전건\n")
for vid in sorted(v for v in got if got[v] == "달라짐"):
    c = cells[vid]
    w(f"**{vid}** · {c['issue']} · {c['arm']} {c['side']} · {c['stage']} 수첩 · `{c['fact_id']}`")
    w(f"> 사실 — {c['fact']}")
    w("")

w("\n## 읽을 때\n")
w("- 이 팩은 **팩2가 「있음」이라 한 칸만** 본다. 「이름만」·「없음」 칸은 표본에 없다.")
w("- 그러므로 여기 비율은 **「있음」의 정밀도**이지 판독 전체의 정확도가 아니다.")
w("- 코더가 사람이 아니다. 그리고 이 점검도 코더 하나가 읽었다.")

(V / "SCORE_VARIANT.md").write_text("\n".join(W) + "\n", encoding="utf-8")
print("\n→ variant/SCORE_VARIANT.md 썼다.")
