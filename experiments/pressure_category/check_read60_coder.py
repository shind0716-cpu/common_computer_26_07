"""[공용 코어 · 압박×카테고리] 독립 코더 판독 검사 + 코더 간 일치도(κ).

`READ60_PROMPT_coder.md` 형식으로 받은 판독을 검사하고, 코더 A(요한 측)와 대조해
Cohen's κ 를 낸다. 사전고정 `SELECTION_live30_2026-08-27.md` §21-6 이 요구한 자다.

형식 — 한 줄에 수첩 하나. `재료 판번호 판정12개 라벨`

    ambulance ① 보 부 보 - 보 부 - 부 부 - 보 보 N

판정은 `보`/`부`/`변`/`-` 넷, 라벨은 `Y`/`N`.
20줄 뒤에 `## 갈린 자리` 절이 있어도 되고, 검사기는 그 아래를 무시한다.

    python check_read60_coder.py READ60_coderA_b1_r0.txt READ60_hermes_b1_r0.txt

한쪽만 주면 형식 검사만 한다. §21-6 판정선: κ ≥ 0.60 이면 계속, 미만이면 멈추고 보고.
"""
import collections
import json
import pathlib
import sys

LAB = {"보", "부", "변", "-", "–"}
NORM = {"–": "-"}


def _nfacts():
    """재료마다 사실 개수가 다르다 — issue_euthanasia 만 8개다.

    판독 줄의 재료 이름은 `issue_id` 에서 `issue_` 를 뗀 것이다
    (팩의 `## issue_xxx` 제목과 짝이 맞는다).
    """
    root = pathlib.Path(__file__).resolve().parent
    conc = json.loads((root / "CONCRETE_LIST_2026-08-27.json").read_text(encoding="utf-8"))["materials"]
    out = {}
    for p in (root / "materials").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        iid = isinstance(d, dict) and d.get("issue_id")
        if not iid or p.stem not in conc:
            continue
        k = len(conc[p.stem])
        out[iid] = k
        out[iid[6:] if iid.startswith("issue_") else iid] = k
    return out


def parse(path):
    rows, bad = {}, []
    NF = _nfacts()
    for n, line in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            break                              # 「갈린 자리」 아래는 안 본다
        t = s.split()
        mat = t[0]
        k = NF.get(mat)
        if k is None:
            bad.append(f"{n}줄 모르는 재료: {mat}")
            continue
        if len(t) != k + 3:
            bad.append(f"{n}줄 토큰 {len(t)}개 — {mat} 는 사실 {k}개라 {k+3}개 필요")
            continue
        slot, judg, label = t[1], t[2:2 + k], t[2 + k]
        if slot not in ("①", "②"):
            bad.append(f"{n}줄 판번호가 ①② 가 아님: {slot}")
            continue
        judg = [NORM.get(x, x) for x in judg]
        off = [x for x in judg if x not in {"보", "부", "변", "-"}]
        if off:
            bad.append(f"{n}줄 판정 밖 기호: {off}")
            continue
        if label not in ("Y", "N"):
            bad.append(f"{n}줄 라벨이 Y/N 가 아님: {label}")
            continue
        rows[(mat, slot)] = (judg, label)
    return rows, bad


def kappa(a, b):
    cats = sorted({*a, *b})
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    A, badA = parse(argv[1])
    print(f"[{pathlib.Path(argv[1]).name}] 수첩 {len(A)}줄 · 형식 오류 {len(badA)}")
    for x in badA:
        print("   ✗", x)
    tot = collections.Counter(j for v, _ in A.values() for j in v)
    print("   판정 분포:", dict(tot), f"· 합 {sum(tot.values())}")
    if len(argv) < 3:
        return 1 if badA else 0

    B, badB = parse(argv[2])
    print(f"[{pathlib.Path(argv[2]).name}] 수첩 {len(B)}줄 · 형식 오류 {len(badB)}")
    for x in badB:
        print("   ✗", x)
    totB = collections.Counter(j for v, _ in B.values() for j in v)
    print("   판정 분포:", dict(totB), f"· 합 {sum(totB.values())}")

    miss = sorted(set(A) ^ set(B))
    if miss:
        print(f"\n⚠ 한쪽에만 있는 수첩 {len(miss)}: {miss[:6]}")
    keys = sorted(set(A) & set(B))
    fa = [j for k in keys for j in A[k][0]]
    fb = [j for k in keys for j in B[k][0]]
    k, po = kappa(fa, fb)
    print(f"\n== 코더 간 일치도 ==\n  칸 {len(fa)} · 단순 일치 {po:.1%} · Cohen κ = {k:.3f}")
    print(f"  §21-6 판정선 κ ≥ 0.60 → {'통과' if k >= 0.60 else '미달 — 판독을 멈추고 보고한다'}")

    print("\n== 갈린 칸 ==")
    cm = collections.Counter((x, y) for x, y in zip(fa, fb) if x != y)
    for (x, y), c in cm.most_common():
        print(f"  A={x} · B={y} : {c}칸")
    print("\n== 갈린 자리 (앞 25) ==")
    shown = 0
    for kk in keys:
        for i, (x, y) in enumerate(zip(A[kk][0], B[kk][0]), 1):
            if x != y and shown < 25:
                print(f"  {kk[0]} {kk[1]} f{i:02d}  A={x}  B={y}")
                shown += 1
    la = [A[k][1] for k in keys]
    lb = [B[k][1] for k in keys]
    print(f"\n== 수첩 라벨 「원본에 없는 것이 생겼나」 ==")
    print(f"  A: Y {la.count('Y')} / N {la.count('N')}   B: Y {lb.count('Y')} / N {lb.count('N')}"
          f"   불일치 {sum(1 for x, y in zip(la, lb) if x != y)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
