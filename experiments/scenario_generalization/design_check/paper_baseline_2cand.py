# -*- coding: utf-8 -*-
"""기준선: 지금 쓰는 2후보 골격(camp·hire·throne)의 무승부는 몇 %인가 (호출 0).

camp 골격 = 요건 4 × 후보 2 = 8칸, 팩트 12개.
공유 4개가 네 칸에 잠정 판정을 주고, 미공유 8개가 여덟 칸 전부를 확정한다.
칸당 1.5개 — 이 여유가 3후보에서 사라진다는 것이 앞선 검산의 결론이었다.

같은 잣대로 무승부를 재서, 3후보 안의 37~44%가 나쁜 값인지 원래 그런 값인지 본다.
"""
from itertools import product

REQS = (1, 2, 3, 4)
CANDS = ("A", "B")


def winners(sc):
    top = max(sc.values())
    return [c for c in CANDS if sc[c] == top]


def sc_of(known):
    return {c: sum(1 for r in REQS if known.get((r, c)) == "O") for c in CANDS}


def profile(shared, unshared):
    keys = sorted(unshared)
    cnt = {"A": 0, "B": 0, "tie": 0}
    for mask in product((0, 1), repeat=len(keys)):
        known = dict(shared)
        for bit, k in zip(mask, keys):
            if bit:
                known[k] = unshared[k]
        w = winners(sc_of(known))
        cnt["tie" if len(w) > 1 else w[0]] += 1
    t = 2 ** len(keys)
    return {k: v / t for k, v in cnt.items()}


# 후보 하나: 공유가 걸린 요건 2개 선택 + 그 잠정값 + 확정 4칸 값
from itertools import combinations
PER_CAND = [(srs, svs, vals)
            for srs in combinations(REQS, 2)
            for svs in product("OX", repeat=2)
            for vals in product("OX", repeat=4)]

res = []
for pa, pb in product(PER_CAND, repeat=2):
    shared, unshared, final = {}, {}, {}
    for cand, (srs, svs, vals) in zip(CANDS, (pa, pb)):
        for r, v in zip(srs, svs):
            shared[(r, cand)] = v
        for r, v in zip(REQS, vals):
            unshared[(r, cand)] = v
        final[cand] = sum(1 for v in vals if v == "O")

    if final["A"] <= final["B"]:          # 정답은 A
        continue
    if winners(sc_of(shared)) != ["B"]:   # 함정: 공유만 보면 B
        continue
    p = profile(shared, unshared)
    res.append((p["tie"], final, p))

print(f"조건을 만족하는 2후보 배치: {len(res):,} 가지")
res.sort(key=lambda x: x[0])
print("\n무승부가 낮은 쪽 (최종점수 조합별 대표)")
print(f"{'최종(A/B)':>12} {'무승부':>9} {'A단독':>9} {'B단독':>9}")
seen = []
for tie, final, p in res:
    sig = (final["A"], final["B"])
    if sig in seen:
        continue
    seen.append(sig)
    print(f"{final['A']}/{final['B']:<10} {p['tie']*100:8.1f}% "
          f"{p['A']*100:8.1f}% {p['B']*100:8.1f}%")

ties = [t for t, _, _ in res]
print(f"\n2후보 무승부: 최저 {min(ties)*100:.1f}% · "
      f"중앙값 {sorted(ties)[len(ties)//2]*100:.1f}% · 최고 {max(ties)*100:.1f}%")
print("\n(비교) 3후보 검산 결과")
print("  요건4 × 후보3 : 무승부 최저 37.5% · C단독 최대 12.5%")
print("  요건3 × 후보3 : 무승부 최저 25.0% · C단독 최대 15.6%")
