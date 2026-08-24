# -*- coding: utf-8 -*-
"""후보 3명 재료 — 종이 검증 (LLM 호출 0).

판정 모형: camp 방식 그대로. 요건 4개, 후보 3명, 12칸 진리표.
에이전트는 "지금 드러난 팩트로 확인된 충족 개수"를 세어 가장 많은 후보를 고른다.
확인 안 된 칸은 셈에서 빠진다(모르는 것은 못 센다).

미공유 팩트 9개 각각이 드러났나/아닌가로 2^9 상태를 전부 돌려
어떤 답이 나오는지 센다. 무승부도 따로 센다.
"""
from itertools import product
from collections import Counter

REQS = [1, 2, 3, 4]
CANDS = ["A", "B", "C"]


def evaluate(design, name):
    shared = design["shared"]        # {(req,cand): "O"/"X"}
    unshared = design["unshared"]    # {(req,cand): "O"/"X"}
    keys = sorted(unshared)

    # --- 최종 진리표 (전부 드러난 상태) ---
    full = {}
    full.update(shared)
    full.update(unshared)
    final = {c: sum(1 for r in REQS if full.get((r, c)) == "O") for c in CANDS}

    print("=" * 68)
    print(f"[{name}]")
    print("\n  진리표 (공=공유 · 미=미공유 · 빈칸=정보 없음)")
    print("        " + "".join(f"{c:>10}" for c in CANDS))
    for r in REQS:
        row = f"  요건{r} "
        for c in CANDS:
            if (r, c) in shared:
                row += f"{shared[(r,c)]+'(공)':>10}"
            elif (r, c) in unshared:
                row += f"{unshared[(r,c)]+'(미)':>10}"
            else:
                row += f"{'—':>10}"
        print(row)
    print("  최종충족 " + "".join(f"{final[c]:>10}" for c in CANDS))

    # --- 공유만 봤을 때 ---
    sc0 = {c: sum(1 for r in REQS if shared.get((r, c)) == "O") for c in CANDS}
    top0 = max(sc0.values())
    win0 = [c for c in CANDS if sc0[c] == top0]
    print(f"\n  공유만 보면: {sc0} → {'/'.join(win0)}"
          f"{'  (단독)' if len(win0)==1 else '  ← 무승부'}")

    # --- 미공유 노출 전수 조사 ---
    tally = Counter()
    for mask in product([0, 1], repeat=len(keys)):
        known = dict(shared)
        for bit, k in zip(mask, keys):
            if bit:
                known[k] = unshared[k]
        sc = {c: sum(1 for r in REQS if known.get((r, c)) == "O") for c in CANDS}
        top = max(sc.values())
        win = [c for c in CANDS if sc[c] == top]
        tally["무승부 " + "/".join(win) if len(win) > 1 else win[0]] += 1

    total = 2 ** len(keys)
    print(f"\n  미공유 노출 전수 {total}가지 — 어떤 답이 나오나")
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"    {k:<14} {v:4}  {v/total*100:5.1f}%")
    tie = sum(v for k, v in tally.items() if k.startswith("무승부"))
    print(f"    → 무승부 합계 {tie/total*100:.1f}%")

    # --- 현실적 노출 확률로 가중 ---
    print("\n  팩트 하나가 드러날 확률 p 별 답 분포")
    print(f"    {'p':>5}  {'A':>7} {'B':>7} {'C':>7} {'무승부':>8}")
    for p in (0.3, 0.5, 0.7, 0.9):
        acc = Counter()
        for mask in product([0, 1], repeat=len(keys)):
            w = 1.0
            known = dict(shared)
            for bit, k in zip(mask, keys):
                w *= p if bit else (1 - p)
                if bit:
                    known[k] = unshared[k]
            sc = {c: sum(1 for r in REQS if known.get((r, c)) == "O") for c in CANDS}
            top = max(sc.values())
            win = [c for c in CANDS if sc[c] == top]
            acc["tie" if len(win) > 1 else win[0]] += w
        print(f"    {p:>5}  {acc['A']*100:6.1f}% {acc['B']*100:6.1f}% "
              f"{acc['C']*100:6.1f}% {acc['tie']*100:7.1f}%")
    return final


# ── 안 1: 공유 3 (B에 O 하나, A·C에 X 하나씩) ────────────────────────
V1 = {
    "shared": {(1, "B"): "O", (2, "A"): "X", (3, "C"): "X"},
    "unshared": {
        (1, "A"): "O", (3, "A"): "O", (4, "A"): "O",      # A 3충족
        (2, "B"): "X", (3, "B"): "X", (4, "B"): "X",      # B 1충족
        (1, "C"): "O", (2, "C"): "O", (4, "C"): "X",      # C 2충족
    },
}

# ── 안 2: 공유가 B를 두 칸 밀어 함정을 세게 ───────────────────────────
V2 = {
    "shared": {(1, "B"): "O", (2, "B"): "O", (3, "A"): "X"},
    "unshared": {
        (1, "A"): "O", (2, "A"): "O", (4, "A"): "O",      # A 3충족
        (3, "B"): "X", (4, "B"): "X", (1, "C"): "O",
        (2, "C"): "O", (3, "C"): "X", (4, "C"): "X",      # C 2충족
    },
}

for d, n in ((V1, "안 1 — 공유 3개가 세 후보에 하나씩"),
             (V2, "안 2 — 공유 3개 중 둘이 B를 민다")):
    evaluate(d, n)
