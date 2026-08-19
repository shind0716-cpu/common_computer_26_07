# -*- coding: utf-8 -*-
"""세 번째 답을 후보가 아니라 판단으로 두는 안 — "둘 다 미달 → 재공고" (호출 0).

후보는 둘로 두고 답을 셋으로 한다. camp 골격(요건 4 · 후보 2 · 칸 8 · 팩트 12)이
한 칸도 안 바뀐다. 앞선 검산에서 3후보가 자를 무디게 만든 원인(오답이 확률을
나눠 가짐)이 여기서는 안 생긴다 — 세 번째 답이 후보가 아니기 때문이다.

칸당 팩트를 여러 개 허용한다(camp 가 실제로 그렇다: 팩트 12 > 칸 8).
같은 칸에 여러 팩트가 걸리면 **우선순위가 높은 쪽**이 이긴다.
  우선 0 = 공유(잠정)  ·  우선 1 = 미공유 확인/뒤집기  ·  우선 2 = 결정타(예외 조항)

판정 규칙: 요건 3개 이상 충족한 후보가 정답. 없으면 '재공고'. 둘 다면 많은 쪽.
"""
from itertools import product

REQS = (1, 2, 3, 4)
CANDS = ("A", "B")
THRESHOLD = 3


def resolve(facts_known):
    """같은 칸의 팩트 중 우선순위 최고를 채택."""
    cell = {}
    for (r, c), val, pri in facts_known:
        if (r, c) not in cell or pri >= cell[(r, c)][1]:
            cell[(r, c)] = (val, pri)
    return {k: v[0] for k, v in cell.items()}


def verdict(grid):
    sc = {c: sum(1 for r in REQS if grid.get((r, c)) == "O") for c in CANDS}
    passing = [c for c in CANDS if sc[c] >= THRESHOLD]
    if not passing:
        return "재공고", sc
    top = max(sc[c] for c in passing)
    win = [c for c in passing if sc[c] == top]
    return (win[0] if len(win) == 1 else "무승부"), sc


def analyse(name, shared, unshared):
    print("=" * 70)
    print(f"[{name}]")
    full = resolve(shared + unshared)
    v, sc = verdict(full)
    print(f"\n  최종 진리표: {sc}  →  정답 = {v}")
    v0, sc0 = verdict(resolve(shared))
    print(f"  공유만 보면: {sc0}  →  {v0}   (함정)")

    n = len(unshared)
    tally = {}
    for mask in product((0, 1), repeat=n):
        known = shared + [f for bit, f in zip(mask, unshared) if bit]
        vv, _ = verdict(resolve(known))
        tally[vv] = tally.get(vv, 0) + 1
    t = 2 ** n
    print(f"\n  미공유 노출 전수 {t}가지")
    for k, c in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"    {k:<8} {c:4}  {c/t*100:5.1f}%")

    print("\n  p 별 답 분포 (무승부는 반씩 갈라 정답에 얹음)")
    print(f"    {'p':>5} " + "".join(f"{k:>10}" for k in ("재공고", "A", "B", "무승부")))
    curve = {}
    for p in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0):
        acc = {}
        for mask in product((0, 1), repeat=n):
            w = 1.0
            known = list(shared)
            for bit, f in zip(mask, unshared):
                w *= p if bit else (1 - p)
                if bit:
                    known.append(f)
            vv, _ = verdict(resolve(known))
            acc[vv] = acc.get(vv, 0.0) + w
        curve[p] = acc
        print(f"    {p:>5} " + "".join(f"{acc.get(k,0)*100:9.1f}%"
                                       for k in ("재공고", "A", "B", "무승부")))
    lo, hi = curve[0.4].get(v, 0), curve[0.6].get(v, 0)
    print(f"\n  정답('{v}') 기울기 p 0.4→0.6 : {(hi-lo)*100:.1f}%p"
          f"   (2후보 기존 골격 = 27.2%p · 3후보 안 = 13.8~16.4%p)")
    return curve


# ── 안 A: 결정타(예외 조항) 1개 ────────────────────────────────────
sharedA = [((1, "B"), "O", 0), ((2, "B"), "O", 0),
           ((3, "B"), "O", 0), ((1, "A"), "X", 0)]
unsharedA = [
    ((1, "A"), "O", 1), ((2, "A"), "O", 1), ((3, "A"), "O", 1),   # A 를 3 까지 올림
    ((4, "A"), "X", 1),
    ((1, "B"), "X", 1), ((2, "B"), "X", 1), ((4, "B"), "X", 1),   # B 를 끌어내림
    ((3, "A"), "X", 2),                                            # 결정타: A 요건3 무효
]

# ── 안 B: 결정타 2개로 나눔 (한 사람 침묵에 안 걸리게) ──────────────
sharedB = [((1, "B"), "O", 0), ((2, "B"), "O", 0),
           ((3, "B"), "O", 0), ((1, "A"), "X", 0)]
unsharedB = [
    ((1, "A"), "O", 1), ((2, "A"), "O", 1), ((3, "A"), "O", 1), ((4, "A"), "O", 1),
    ((1, "B"), "X", 1), ((2, "B"), "X", 1),
    ((3, "A"), "X", 2), ((4, "A"), "X", 2),   # 결정타 둘 — 둘 다 나와야 A 가 2 로
]

for nm, sh, un in (("안 A — 결정타 1개", sharedA, unsharedA),
                   ("안 B — 결정타 2개", sharedB, unsharedB)):
    analyse(nm, sh, un)
