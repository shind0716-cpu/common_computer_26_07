# -*- coding: utf-8 -*-
"""팩 「틀」 채점 — 사전고정 F1~F4 를 그대로 잰다. 호출 0.

    python tools/collect.py && python tools/score.py

**판독 결과를 보기 전에 썼다.** 판정선도 사전고정에 미리 적힌 것을 옮긴 것이다.
중단선: 「있음」 판의 인용 15장을 뽑아 사람이 본다 — 준 가치문·사실을 그대로 옮긴 것이
3분의 1을 넘으면 ①의 정의가 안 먹은 것이므로 멈춘다.
산출: SCORE_F.md
"""
import json, math, re, glob, pathlib, random, collections

H = pathlib.Path(__file__).resolve().parent.parent
KEY = json.loads((H / "_KEY_F.json").read_text(encoding="utf-8"))
G = json.loads((H / "_COLLECTED_F.json").read_text(encoding="utf-8"))

W = []
def w(s=""): print(s); W.append(s)
def pct(k, n): return f"{k/n*100:.0f}%" if n else "—"
def wilson(k, n, z=1.96):
    if not n: return (0.0, 0.0)
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return max(0.0, c-h)*100, min(1.0, c+h)*100

w("# 채점 — 팩 「틀」 (2026-09-03)")
w("")
w("> 기계 산출물. 사전고정 F1\\~F4 와 정정 1 그대로. 손으로 고치지 마라.")
w(f"> 수첩 {len(G)}/{len(KEY)} · 짝지은 대조(뒤집힘 114 대 유지 114)")
w("")

# ── 중단선 먼저 — 인용이 준 것을 그대로 옮긴 것인가 ─────────────────
w("## 0. 먼저 — ①의 정의가 먹었나 (중단선)\n")
yes = [f for f in G if G[f]["frame"] == "있음"]
rng = random.Random(20260903)
samp = rng.sample(yes, min(15, len(yes)))
w(f"「있음」 {len(yes)}장 중 무작위 {len(samp)}장의 인용 — **사람이 눈으로 본다**\n")
for f in samp:
    w(f"  {f} · {KEY[f]['issue'][:24]:24s} 「{G[f]['quote'][:64]}」")
w("")
w("  → 준 가치문·사실을 그대로 옮긴 인용이 3분의 1(5장)을 넘으면 여기서 멈춘다.")

# ── F1 주 물음 ─────────────────────────────────────────────────────
w("\n## F1 — 뒤집힌 판에 틀이 더 많나 (주 물음)\n")
t = collections.Counter((KEY[f]["label"], G[f]["frame"]) for f in G)
w("| 판 | 수첩 | 틀 있음 | 몫 | 95% 구간 |")
w("|---|---:|---:|---:|---|")
rate = {}
for lab, nm in (("flip", "뒤집힘"), ("keep", "유지")):
    a, b = t[(lab, "있음")], t[(lab, "없음")]
    n = a + b; rate[lab] = a/n*100 if n else 0
    lo, hi = wilson(a, n)
    w(f"| {nm} | {n} | {a} | **{pct(a, n)}** | {lo:.0f}\\~{hi:.0f}% |")
d = rate["flip"] - rate["keep"]
w(f"\n**차 {d:+.1f}%p** → 판정선 15%p: **{'맞음' if d >= 15 else '빗나감'}**")
if d < 15:
    w("\n빗나갔다면 **틀은 답을 가르지 않는다** — 사후 정당화 쪽으로 읽는다.")

# ── F2 틀이 최종 답 쪽을 미나 ──────────────────────────────────────
w("\n## F2 — 틀이 최종 답 쪽을 미나\n")
ok = amb = wrong = 0
for f in yes:
    k = KEY[f]; push = G[f]["push"]
    if push not in ("1", "2"): amb += 1; continue
    if k["options"][int(push)-1] == k["final"]: ok += 1
    else: wrong += 1
n = ok + wrong
w(f"  틀 있음 {len(yes)}장 · 방향 판독 가능 {n} · 어느 쪽도 아님 {amb}")
w(f"  **최종 답 쪽을 민 것 {ok}/{n} = {pct(ok, n)}** → 판정선 60%: "
  f"**{'맞음' if n and ok/n >= 0.6 else '빗나감'}**")

# ── F3·F4 각본별 ───────────────────────────────────────────────────
w("\n## F3·F4 — 각본별 틀 비율\n")
w("| 각본 | 수첩 | 틀 있음 | 몫 |")
w("|---|---:|---:|---:|")
by = collections.defaultdict(collections.Counter)
for f in G: by[KEY[f]["script"]][G[f]["frame"]] += 1
rr = {}
for s in ("C0", "C1", "C2"):
    a, b = by[s]["있음"], by[s]["없음"]; n = a + b
    if not n: continue
    rr[s] = a/n*100
    w(f"| {s} | {n} | {a} | **{pct(a, n)}** |")
if "C0" in rr:
    w(f"\n**F3** C0 에서 {rr['C0']:.0f}% → 판정선 20% 이상: "
      f"**{'맞음' if rr['C0'] >= 20 else '빗나감'}**")
if len(rr) > 1:
    span = max(rr.values()) - min(rr.values())
    w(f"**F4** 각본 사이 폭 {span:.0f}%p → 판정선 15%p 안: "
      f"**{'맞음' if span <= 15 else '빗나감'}**")

# ── 곁들임 ─────────────────────────────────────────────────────────
w("\n## 곁들임 — 세트·재료\n")
for axis, nm in (("vset", "세트"), ("script", "각본")):
    w(f"\n  {nm}별 뒤집힘 판의 틀 비율")
    d2 = collections.defaultdict(collections.Counter)
    for f in G:
        if KEY[f]["label"] == "flip": d2[KEY[f][axis]][G[f]["frame"]] += 1
    for k2 in sorted(d2):
        a, b = d2[k2]["있음"], d2[k2]["없음"]
        w(f"    {k2}: {a}/{a+b} = {pct(a, a+b)}")

w("\n## 읽을 때\n")
w("- **인과가 아니다.** 마지막 수첩과 최종 답은 같은 판 안이고 순서만 다르다. F1 이 서도 **동반**까지다.")
w("- **짝지은 대조라 모집단 비율이 아니다.** 「전체 판의 몇 %에 틀이 있다」는 못 말한다.")
w("- 짝을 못 찾은 뒤집힘 10판은 팩 밖이다(그 칸이 100% 뒤집힘 — 기운 재료).")
w("- 코더가 사람이 아니고, 코더 하나가 한 팩을 읽었다. gpt 한 모델이다.")

(H / "SCORE_F.md").write_text("\n".join(W) + "\n", encoding="utf-8")
print("\n→ SCORE_F.md 썼다.")
