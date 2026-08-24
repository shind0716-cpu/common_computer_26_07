# -*- coding: utf-8 -*-
"""후보 3명 재료 — 설계 공간 전수 탐색 (LLM 호출 0).

칸 구조는 강제된다: 요건 4 × 후보 3 = 12칸, 팩트 12개가 1:1로 채운다.
미공유가 후보당 3개면 공유는 후보당 1개일 수밖에 없다.

자유도는 후보마다 ① 어느 요건이 공유인가(4) ② 네 칸의 O/X(16) = 64.
세 후보라 64^3 = 262,144 가지를 전부 돌린다.

거르는 조건
  - 최종 정답이 A 단독 (A > B, A > C)
  - 공유만 보면 B 단독 최다  (= 함정이 선다)
평가
  - 무승부 비율 (낮을수록 좋다)
  - C 단독 승리 비율 (부분 취합이 C 로 떨어지는 몫 — 클수록 좋다)
"""
from itertools import product, combinations

REQS = (1, 2, 3, 4)
CANDS = ("A", "B", "C")


def score(known):
    return {c: sum(1 for r in REQS if known.get((r, c)) == "O") for c in CANDS}


def winners(sc):
    top = max(sc.values())
    return [c for c in CANDS if sc[c] == top]


def profile(shared, unshared):
    """미공유 노출 2^9 전수 → (무승부 비율, C단독 비율, A단독 비율, B단독 비율)"""
    keys = sorted(unshared)
    n = len(keys)
    cnt = {"A": 0, "B": 0, "C": 0, "tie": 0}
    for mask in product((0, 1), repeat=n):
        known = dict(shared)
        for bit, k in zip(mask, keys):
            if bit:
                known[k] = unshared[k]
        w = winners(score(known))
        cnt["tie" if len(w) > 1 else w[0]] += 1
    t = 2 ** n
    return {k: v / t for k, v in cnt.items()}


# 후보 하나의 배치: (공유 요건, 네 칸의 값)
PER_CAND = [(sr, vals) for sr in REQS for vals in product("OX", repeat=4)]

results = []
for pa, pb, pc in product(PER_CAND, repeat=3):
    shared, unshared, final = {}, {}, {}
    for cand, (sr, vals) in zip(CANDS, (pa, pb, pc)):
        for r, v in zip(REQS, vals):
            (shared if r == sr else unshared)[(r, cand)] = v
        final[cand] = sum(1 for v in vals if v == "O")

    # 정답은 A 단독
    if not (final["A"] > final["B"] and final["A"] > final["C"]):
        continue
    # 함정: 공유만 보면 B 단독
    if winners(score(shared)) != ["B"]:
        continue

    p = profile(shared, unshared)
    results.append((p["tie"], -p["C"], final, shared, unshared, p))

print(f"조건을 만족하는 배치: {len(results):,} 가지")
if not results:
    raise SystemExit("없음")

results.sort(key=lambda x: (x[0], x[1]))
print("\n무승부가 가장 낮은 배치 5개")
print(f"{'최종(A/B/C)':>14} {'무승부':>8} {'A단독':>8} {'B단독':>8} {'C단독':>8}")
seen = set()
best = []
for tie, negc, final, sh, un, p in results:
    sig = (final["A"], final["B"], final["C"], round(tie, 4), round(p["C"], 4))
    if sig in seen:
        continue
    seen.add(sig)
    best.append((tie, negc, final, sh, un, p))
    print(f"{final['A']}/{final['B']}/{final['C']:<10} {p['tie']*100:7.1f}% "
          f"{p['A']*100:7.1f}% {p['B']*100:7.1f}% {p['C']*100:7.1f}%")
    if len(best) == 5:
        break

# C 단독이 가장 큰 배치 (부분 취합이 C 로 떨어지는 몫)
results.sort(key=lambda x: (x[1], x[0]))
print("\nC 단독 승리가 가장 큰 배치 3개")
seen = set()
shown = 0
for tie, negc, final, sh, un, p in results:
    sig = (final["A"], final["B"], final["C"], round(tie, 4), round(p["C"], 4))
    if sig in seen:
        continue
    seen.add(sig)
    print(f"{final['A']}/{final['B']}/{final['C']:<10} {p['tie']*100:7.1f}% "
          f"{p['A']*100:7.1f}% {p['B']*100:7.1f}% {p['C']*100:7.1f}%")
    shown += 1
    if shown == 3:
        break

# 가장 좋은 것 하나를 펼쳐 본다
tie, negc, final, sh, un, p = best[0]
print("\n" + "=" * 60)
print("무승부 최저 배치의 진리표")
print("        " + "".join(f"{c:>10}" for c in CANDS))
for r in REQS:
    row = f"  요건{r} "
    for c in CANDS:
        if (r, c) in sh:
            row += f"{sh[(r,c)]+'(공)':>10}"
        else:
            row += f"{un[(r,c)]+'(미)':>10}"
    print(row)
print("  최종충족 " + "".join(f"{final[c]:>10}" for c in CANDS))
print(f"\n  공유만 보면: {score(sh)} → B")
print(f"  무승부 {p['tie']*100:.1f}% · A {p['A']*100:.1f}% · "
      f"B {p['B']*100:.1f}% · C {p['C']*100:.1f}%")
