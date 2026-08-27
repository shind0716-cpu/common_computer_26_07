"""[공용 코어 · 압박×카테고리] 1차 1단계 — 사후 기술통계.

**이 파일은 결과를 보고 나서 썼다.** `analyze_stage1.py` 가 사전고정 판정선을 그대로 집행하는
파일이고, 이 파일은 그 결과를 보고 "그래서 왜 그런가"를 묻는 자리다. 여기 나오는 수는
**판정에 안 쓴다** — 기술과 다음 물음거리다. 둘을 파일로 갈라 두는 것이 그 표시다.

담는 것:
  1. H2′ (부산물) — 안/밖 격차가 r0 에서 얼마나 벌어지나
  2. H6 짝 넷 — 같은 무대를 두 갈래로 지은 넷에서 방향이 같은가 (§15-3 의 조건)
  3. H3′ 조건부 — r0 에 오른 것 중 「부분」 비율 (원 판정선은 전체 대비라 밖의 통째 탈락과 섞인다)
  4. 부호검정 p
  5. 관문 통과·탈락별 d (§18-6-7-1 이 나눠 보고하라고 한 것)

    python analyze_stage1_extra.py
"""
import collections
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze_stage1 as S  # noqa: E402

ROOT = S.ROOT
PAIR4 = [("캣맘", "issue_community_cat_feeding", "issue_cat_feeding_party"),
         ("흡연", "issue_smoking_area", "issue_smoking_area_party"),
         ("재활용", "issue_recycling_room", "issue_recycling_room_party"),
         ("육아", "issue_childcare_room", "issue_childcare_party")]


def signtest(pos, neg):
    n = pos + neg
    if n == 0:
        return float("nan")
    p = sum(math.comb(n, k) for k in range(max(pos, neg), n + 1)) / 2 ** n
    return min(1.0, 2 * p)


def main():
    key, mats, runs = S.load_all()
    iids = sorted(key)
    out = []
    W = out.append
    gate = {i: runs[(i, "A")]["final_poll"] != runs[(i, "B")]["final_poll"] for i in iids}

    for cname, prefix in (("코더 A", "READ60_coderA"), ("헤르메스", "READ60_hermes")):
        coding = S.load_coding(prefix)
        rows = {i: S.pair_d(mats, coding, key, i) for i in iids}
        W("=" * 78)
        W(f"사후 기술 — {cname}")
        W("=" * 78)

        # 1. H2′ — 격차가 r0 에서 얼마나 벌어지나
        n = collections.defaultdict(collections.Counter)
        for iid in iids:
            M = mats[iid]
            slot_of = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
            for s in ("A", "B"):
                for tag in ("r0", "last"):
                    j = coding[(iid, slot_of[s])][tag]
                    for i, fid in enumerate(M["order"]):
                        side = "안" if M["facts"][fid]["category"] in M["sets"][s] else "밖"
                        n[(tag, side)]["살" if j[i] in S.ALIVE else "죽"] += 1
        g = {}
        for tag in ("r0", "last"):
            a, b = n[(tag, "안")], n[(tag, "밖")]
            pa = a["살"] / (a["살"] + a["죽"])
            pb = b["살"] / (b["살"] + b["죽"])
            g[tag] = pa - pb
            W(f"  1. H2′  {tag:5s} 안 {pa:.1%} · 밖 {pb:.1%} → 격차 {pa - pb:+.1%}p")
        W(f"          마지막 격차의 {g['r0'] / g['last']:.0%} 가 r0 에서 이미 벌어져 있다"
          f"  (예상선 7할 → {'넘음' if g['r0'] / g['last'] >= 0.7 else '못 넘음'})")

        # 2. H6 짝 넷
        W("\n  2. H6  같은 무대 짝 넷 — 갈래 하나 대 갈래 둘 (r0 층)")
        same = 0
        for nm, one, two in PAIR4:
            d1, d2 = rows[one][0], rows[two][0]
            arrow = "둘<하나" if d2 < d1 else ("둘>하나" if d2 > d1 else "같음")
            same += (d2 < d1)
            W(f"     {nm:5s} 하나 {d1:+.3f}  둘 {d2:+.3f}   {arrow}")
        W(f"     예상(둘<하나) 방향인 짝 {same}/4 — §15-3 은 '짝 넷에서 같은 방향'을 요구한다")
        W("     ※ 짝 없는 갈래 둘 셋: " + " · ".join(
            f"{i.replace('issue_', '')} {rows[i][0]:+.3f}"
            for i in ("issue_community_room", "issue_floor_noise", "issue_garden_plot")))

        # 3. H3′ 조건부
        c = collections.defaultdict(collections.Counter)
        for iid in iids:
            M = mats[iid]
            slot_of = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
            for s in ("A", "B"):
                j = coding[(iid, slot_of[s])]["r0"]
                for i, fid in enumerate(M["order"]):
                    side = "안" if M["facts"][fid]["category"] in M["sets"][s] else "밖"
                    c[side][j[i]] += 1
        W("\n  3. H3′ 조건부 — r0 에 오른 것 중 「부분」 (원 판정선은 전체 대비라 통째 탈락과 섞인다)")
        for side in ("안", "밖"):
            liv = sum(c[side][x] for x in S.ALIVE)
            W(f"     {side}  r0 진입 {liv:3d} 중 부분 {c[side]['부']:3d} = {c[side]['부'] / liv:.1%}")
        ra = c["안"]["부"] / sum(c["안"][x] for x in S.ALIVE)
        rb = c["밖"]["부"] / sum(c["밖"][x] for x in S.ALIVE)
        W(f"     밖:안 = {rb / ra:.2f}:1   (원 판정선의 전체 대비 비는 {c['밖']['부'] / c['안']['부']:.2f}:1)")

        # 4. 부호검정
        W("\n  4. 부호검정 (동점 제외)")
        for idx, nm in ((0, "r0 진입"), (1, "생존  ")):
            v = [rows[i][idx] for i in iids if rows[i][idx] is not None]
            p, q = sum(1 for x in v if x > 0), sum(1 for x in v if x < 0)
            W(f"     {nm}  +{p} / −{q}  (동점 {len(v) - p - q})  양측 p = {signtest(p, q):.2g}")

        # 5. 관문 통과·탈락별
        W("\n  5. 관문 통과·탈락별 d 중앙 (§18-6-7-1 — 판정은 전체로 하되 나눠 보고)")
        for lab, want in (("통과", True), ("탈락", False)):
            for idx, nm in ((0, "r0 진입"), (1, "생존  ")):
                v = sorted(rows[i][idx] for i in iids if gate[i] is want and rows[i][idx] is not None)
                m = v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2
                W(f"     {lab} n={len(v):2d}  {nm} 중앙 d {m:+.3f} (d>0 {sum(1 for x in v if x > 0)})")
        W("")

    txt = "\n".join(out)
    (ROOT / "STAGE1_EXTRA_2026-08-27.txt").write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
