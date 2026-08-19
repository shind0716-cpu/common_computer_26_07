# -*- coding: utf-8 -*-
"""요건을 3개로 줄이면 무승부가 잡히는가 (LLM 호출 0).

요건 3 × 후보 3 = 9칸, 팩트 12개 → 칸당 1.33개로 여유가 생긴다.
구조: 공유 3개가 세 칸에 **잠정** 판정을 주고(전원이 봄),
      미공유 9개가 9칸 전부에 **확정** 판정을 준다.
      즉 세 칸은 공유의 잠정값이 미공유로 뒤집힐 수 있다 — throne 의 실제 기제.

전수: 미공유 9개 노출 2^9 = 512.
설계 공간: 후보마다 ① 공유가 걸린 요건(3) ② 공유 잠정값(2) ③ 확정 3칸의 값(8)
          = 48, 세 후보라 48^3 = 110,592.
"""
from itertools import product

REQS = (1, 2, 3)
CANDS = ("A", "B", "C")


def winners(sc):
    top = max(sc.values())
    return [c for c in CANDS if sc[c] == top]


def sc_of(known):
    return {c: sum(1 for r in REQS if known.get((r, c)) == "O") for c in CANDS}


def profile(shared, unshared):
    keys = sorted(unshared)
    cnt = {"A": 0, "B": 0, "C": 0, "tie": 0}
    for mask in product((0, 1), repeat=len(keys)):
        known = dict(shared)                 # 공유는 늘 보임(잠정)
        for bit, k in zip(mask, keys):
            if bit:
                known[k] = unshared[k]       # 미공유가 덮는다(확정)
        w = winners(sc_of(known))
        cnt["tie" if len(w) > 1 else w[0]] += 1
    t = 2 ** len(keys)
    return {k: v / t for k, v in cnt.items()}


PER_CAND = [(sr, sv, vals)
            for sr in REQS for sv in "OX" for vals in product("OX", repeat=3)]

res = []
for pa, pb, pc in product(PER_CAND, repeat=3):
    shared, unshared, final = {}, {}, {}
    for cand, (sr, sv, vals) in zip(CANDS, (pa, pb, pc)):
        shared[(sr, cand)] = sv
        for r, v in zip(REQS, vals):
            unshared[(r, cand)] = v
        final[cand] = sum(1 for v in vals if v == "O")

    if not (final["A"] > final["B"] and final["A"] > final["C"]):
        continue
    if winners(sc_of(shared)) != ["B"]:
        continue
    p = profile(shared, unshared)
    res.append((p["tie"], -p["C"], final, shared, unshared, p))

print(f"조건을 만족하는 배치: {len(res):,} 가지")
res.sort(key=lambda x: (x[0], x[1]))

print("\n무승부가 낮은 배치 (최종점수 조합별 대표)")
print(f"{'최종(A/B/C)':>14} {'무승부':>8} {'A단독':>8} {'B단독':>8} {'C단독':>8}")
seen, best = set(), []
for tie, negc, final, sh, un, p in res:
    sig = (final["A"], final["B"], final["C"])
    if sig in seen:
        continue
    seen.add(sig)
    best.append((tie, negc, final, sh, un, p))
    print(f"{final['A']}/{final['B']}/{final['C']:<10} {p['tie']*100:7.1f}% "
          f"{p['A']*100:7.1f}% {p['B']*100:7.1f}% {p['C']*100:7.1f}%")

res.sort(key=lambda x: (x[1], x[0]))
print("\nC 단독이 가장 큰 배치")
tie, negc, final, sh, un, p = res[0]
print(f"{final['A']}/{final['B']}/{final['C']:<10} {p['tie']*100:7.1f}% "
      f"{p['A']*100:7.1f}% {p['B']*100:7.1f}% {p['C']*100:7.1f}%")
print("\n  진리표 (공=공유 잠정 · 미=미공유 확정)")
print("        " + "".join(f"{c:>14}" for c in CANDS))
for r in REQS:
    row = f"  요건{r} "
    for c in CANDS:
        s = sh.get((r, c))
        cell = (s + "(공)→" if s else "") + un[(r, c)] + "(미)"
        row += f"{cell:>14}"
    print(row)
print("  최종충족 " + "".join(f"{final[c]:>14}" for c in CANDS))
print(f"\n  공유만 보면: {sc_of(sh)} → B")
