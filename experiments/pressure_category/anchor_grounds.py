"""[공용 코어 · 압박×카테고리] 표식을 조각 단위로 세운다 — 기계 구체 보존율 (콜 0).

## 왜

지금 표식은 **사실 하나에 어절 하나**라 이진이다(있다/없다). 그런데 구체는 사실마다
두세 조각이라, **표식이 어느 조각에 박혀 있었느냐**에 따라 같은 「부분」이 살았다도 되고
죽었다도 된다. `ambulance_02` 가 그 예 — 수첩이 「최근 비슷한 신고」는 살렸는데 표식
「과잉」이 하필 빠진 조각에 박혀 있어 기계는 탈락으로 셌다.

→ `CONCRETE_LIST_2026-08-27.json` 의 **구체 조각 584개를 통째로 표식으로 쓴다.**
그러면 기계도 §18-3 의 눈금을 낼 수 있다.

    기계 구체 보존율  r = 수첩에서 잡힌 조각 수 ÷ 그 사실의 전체 조각 수

## 매칭 셋 — 느슨하게 가는 사다리

문자열 검색이라 「의식 저하를」 대 「의식저하가」 같은 자리에서 깨진다(§28 실물 ③).
세 단계로 재고 **각 단계가 무엇을 사는지** 같이 본다.

  ① 그대로   조각 원문이 수첩에 그대로 있나
  ② 공백 뺌   양쪽에서 공백을 지우고
  ③ 꼬리 깎음  ② 에 더해 조각 끝 1~3자를 깎아 가며 (조사·어미 흡수, 최소 3자 유지)

**뜻으로 같은 것(`넉 주`→`4주`·`응급실`→`ER`)은 어느 단계에서도 못 잡는다.**
그건 문자열 검색의 한계이고 판독이 하는 일이다(§20-1 ⚠). 이 파일은 그 한계를 **재는** 것이지
없애는 것이 아니다.

    python anchor_grounds.py
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze_stage1 as S  # noqa: E402

ROOT = S.ROOT
MIN_KEEP = 3          # 꼬리를 깎아도 이만큼은 남긴다 — 짧은 조각이 아무 데나 걸리는 것을 막는다
MAX_TRIM = 3          # 깎는 최대 글자 수


def norm(s):
    return s.replace(" ", "")


def hit(ground, note, level):
    """조각이 수첩에 있나. level 1=그대로 · 2=공백 뺌 · 3=꼬리 깎음."""
    if level == 1:
        return ground in note
    g, n = norm(ground), norm(note)
    if level == 2:
        return g in n
    for k in range(0, MAX_TRIM + 1):
        g2 = g[: len(g) - k] if k else g
        if len(g2) < MIN_KEEP:
            break
        if g2 in n:
            return True
    return False


def load_grounds():
    conc = json.loads((ROOT / "CONCRETE_LIST_2026-08-27.json").read_text(encoding="utf-8"))["materials"]
    stem = {}
    for p in (ROOT / "materials").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("issue_id") and p.stem in conc:
            stem[d["issue_id"]] = p.stem
    return conc, stem


def main():
    key, mats, runs = S.load_all()
    cod = {n: S.load_coding(p) for n, p in (("A", "READ60_coderA"), ("H", "READ60_hermes"))}
    conc, stem = load_grounds()
    out, W = [], None
    lines = []
    W = lines.append

    rows = []          # (iid, s, fid, 사람판정, r1, r2, r3, n조각, 옛표식 잡힘)
    for iid in sorted(key):
        M = mats[iid]
        slot = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
        cc = conc[stem[iid]]
        for s in ("A", "B"):
            note = runs[(iid, s)]["notes"][0]
            j = cod["A"][(iid, slot[s])]["r0"]
            jh = cod["H"][(iid, slot[s])]["r0"]
            for i, fid in enumerate(M["order"]):
                g = cc[fid]["grounds"]
                r = [sum(hit(x, note, lv) for x in g) / len(g) for lv in (1, 2, 3)]
                anc = M["facts"][fid].get("anchor", "")
                rows.append((iid, s, fid, j[i], jh[i], r[0], r[1], r[2], len(g),
                             bool(anc) and anc in note))

    W("=" * 78)
    W("① 매칭 사다리 — 조각 584 × 두 판 = 1,168 조각관측 중 몇을 잡나")
    W("=" * 78)
    tot = sum(x[8] for x in rows)
    for k, nm in ((5, "① 그대로"), (6, "② 공백 뺌"), (7, "③ 꼬리 깎음")):
        got = sum(x[k] * x[8] for x in rows)
        W(f"  {nm:12s} 조각 {got:6.0f}/{tot} = {got / tot:.1%}")
    W(f"  (옛 표식 — 사실당 어절 하나)  사실 {sum(1 for x in rows if x[9])}/{len(rows)} "
      f"= {sum(1 for x in rows if x[9]) / len(rows):.1%} 가 잡힌다")

    W("")
    W("=" * 78)
    W("② 기계 r 과 사람 판정 — 사다리 ③ 기준")
    W("=" * 78)
    W(f"  {'사람 판정':10s} {'칸':>5s} {'기계 r 평균':>11s} {'r=0':>6s} {'0<r<1':>7s} {'r=1':>6s}")
    for lab in ("보", "부", "변", "-"):
        sub = [x for x in rows if x[3] == lab]
        if not sub:
            continue
        z = sum(1 for x in sub if x[7] == 0)
        m = sum(1 for x in sub if 0 < x[7] < 1)
        o = sum(1 for x in sub if x[7] == 1)
        W(f"  {S.__dict__.get('_', None) or lab:10s} {len(sub):>5d} "
          f"{sum(x[7] for x in sub) / len(sub):>11.2f} {z:>6d} {m:>7d} {o:>6d}")

    W("")
    W("=" * 78)
    W("③ 옛 표식이 못 하던 것을 하나 — 「부분」을 부분으로 잡나")
    W("=" * 78)
    bu = [x for x in rows if x[3] == "부"]
    old_alive = sum(1 for x in bu if x[9])
    mid = sum(1 for x in bu if 0 < x[7] < 1)
    W(f"  사람이 「부분」이라 한 {len(bu)}칸 —")
    W(f"    옛 표식: 살았다 {old_alive} · 죽었다 {len(bu) - old_alive}  (중간이 없다)")
    W(f"    조각 표식: 0<r<1 로 잡은 것 **{mid}칸 ({mid / len(bu):.0%})** · r=1 {sum(1 for x in bu if x[7] == 1)} · r=0 {sum(1 for x in bu if x[7] == 0)}")

    W("")
    W("=" * 78)
    W("④ 이진으로 접어 대조 — 기계 r>0 을 「살았다」로 볼 때")
    W("=" * 78)
    tab = collections.Counter((("살" if x[3] in S.ALIVE else "죽"),
                               ("살" if x[7] > 0 else "죽")) for x in rows)
    n = sum(tab.values())
    W(f"  {'':14s}{'기계 살':>8s}{'기계 죽':>8s}")
    for h in ("살", "죽"):
        W(f"  사람 {h:10s}{tab[(h, '살')]:>8d}{tab[(h, '죽')]:>8d}")
    miss = tab[("살", "죽")]
    fp = tab[("죽", "살")]
    W(f"  → 놓침 {miss}/{tab[('살', '살')] + miss} = {miss / (tab[('살', '살')] + miss):.0%}"
      f" · 오탐 {fp}/{fp + tab[('죽', '죽')]} = {fp / (fp + tab[('죽', '죽')]):.0%}"
      f" · 일치 {(tab[('살', '살')] + tab[('죽', '죽')]) / n:.0%}")
    W(f"  (옛 표식 — §23-7: 놓침 25% · 오탐 1%)")

    txt = "\n".join(lines)
    (ROOT / "ANCHOR_GROUNDS_2026-08-27.txt").write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
