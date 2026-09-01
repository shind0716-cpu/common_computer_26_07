"""[공용 코어 · 압박×카테고리] 카테고리별 집계 — 무엇이 줘야 남고 무엇이 그냥 남나 (콜 0).

## 무엇을 재나

가치 세트는 카테고리 셋을 「중요하다」고 이름 부르고 나머지 셋은 안 부른다.
그 **부름의 효과가 카테고리마다 얼마나 다른가**를 잰다.

  일러 준 것   그 판의 가치 세트가 이름 부른 카테고리
  안 일러 준 것 나머지 셋
  살았다       그 카테고리의 사실 둘 중 하나라도 표식 글자가 수첩에 있다

라운드마다(수첩 r0·r1·r2) 따로 세고, 압박 세 수준(C0·C1·C2)을 갈라 놓는다.

## 왜 아홉 종만 싣나

재료 30벌에 카테고리 이름이 113종 나오는데 대부분 재료 한두 벌에만 있다.
**한쪽 분모가 12칸 미만이면 싣지 않는다** — 한 칸이 8%p 를 움직이는 표는 표가 아니다.
남는 것이 아홉 종이고, 그중 「접근성」이 재료 16벌 96칸으로 가장 두껍다.

## 한계

글자 기준이라 **말을 바꿔 쓴 것을 놓친다.** 실측 예: issue_childcare 의 「적응지원」
표식은 `단계적으로` 인데 어떤 수첩은 `단계적 적응 프로그램` 이라고 적었다 — 뜻은
살았는데 기계는 죽었다고 센다. 그러므로 이 표의 값은 **아래로 치우친 값**이다.
비교와 서열로 읽고 절대값으로 읽지 않는다.

사용: PYTHONUTF8=1 python report_categories.py [--model gpt] [--min-cells 12]
산출: CATS_<모델>_<날짜>.json · CATS_<모델>_<날짜>.md
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aggregate_all11 as A  # noqa: E402

KST = timezone(timedelta(hours=9))
SCRIPTS = ("C0", "C1", "C2")
REPS = (1, 2, 3)
VSETS = ("A", "B")


def materials() -> dict:
    reg = {}
    for p in sorted((HERE / "materials").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            reg[d["issue_id"]] = d
    return reg


def hit(anchor: str, note: str) -> bool:
    """②까지 적중 — 그대로 또는 접어서 (집계 관례와 같은 자)."""
    return 0 < A.probe(anchor, note)[0] <= 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt")
    ap.add_argument("--min-cells", type=int, default=12,
                    help="한쪽(안/밖) 분모가 이 미만인 카테고리는 싣지 않는다")
    a = ap.parse_args()

    mats = materials()
    ids = [x.strip() for x in (HERE / "_live30_ids.txt").read_text(encoding="utf-8").split()
           if x.strip()]
    S = collections.Counter()
    mat_of = collections.defaultdict(set)
    runs = 0
    for iid in ids:
        m = mats[iid]
        by = collections.defaultdict(list)
        for f in m["facts"]:
            by[f["category"]].append(f["anchor"])
        for sc in SCRIPTS:
            for vs in VSETS:
                for rep in REPS:
                    p = HERE / "runs" / a.model / iid / f"run_{sc}_{vs}_rep{rep}.json"
                    if not p.exists():
                        continue
                    d = json.loads(p.read_text(encoding="utf-8"))
                    notes = d.get("notes") or []
                    if not notes:
                        continue
                    runs += 1
                    given = set(d.get("value_categories") or [])
                    for r, note in enumerate(notes):
                        for c, anchors in by.items():
                            side = "안" if c in given else "밖"
                            S[(c, sc, side, r, "n")] += 1
                            S[(c, sc, side, r, "k")] += any(hit(x, note) for x in anchors)
                    for c in by:
                        mat_of[c].add(iid)

    keep = [c for c in mat_of
            if min(S[(c, "C0", s, 2, "n")] for s in ("안", "밖")) >= a.min_cells]
    gap = lambda c: (100.0 * S[(c, "C0", "안", 2, "k")] / S[(c, "C0", "안", 2, "n")]
                     - 100.0 * S[(c, "C0", "밖", 2, "k")] / S[(c, "C0", "밖", 2, "n")])  # noqa: E731
    keep.sort(key=gap)
    today = datetime.now(KST).strftime("%Y-%m-%d")

    out = {"schema": "pressure_categories_v1", "model": a.model,
           "created_at": datetime.now(KST).isoformat(timespec="seconds"),
           "runs": runs, "materials": len(ids),
           "measure": "글자 기준 ②(그대로·접어서) · 카테고리 잣대 · 수첩 r0·r1·r2",
           "grade": "탐색 — 말 바꿔 쓴 것을 놓치므로 아래로 치우친 값",
           "category_names_total": len(mat_of), "min_cells": a.min_cells,
           "categories": {c: {"materials": len(mat_of[c]),
                              **{f"{sc}|{sd}": [[S[(c, sc, sd, r, "k")], S[(c, sc, sd, r, "n")]]
                                                for r in range(3)]
                                 for sc in SCRIPTS for sd in ("안", "밖")}} for c in keep}}

    pc = lambda x: 100.0 * x[0] / x[1] if x[1] else float("nan")  # noqa: E731
    L = [f"# 카테고리별 — 줘야 남는 것과 그냥 남는 것 ({a.model}, {today})", "",
         f"지위: **근거 자료** · 판 {runs} · 재료 {len(ids)}벌 · {out['measure']}",
         f"· **{out['grade']}**", "",
         f"카테고리 이름 {len(mat_of)}종 중 한쪽 분모가 {a.min_cells}칸 이상인 "
         f"**{len(keep)}종**만 싣는다.", "",
         "## 1. 부름의 효과 — 차이가 작은 것부터", "",
         "| 카테고리 | 재료 | 칸 | 안 일러 줌 | 일러 줌 | 차이 |",
         "|---|---:|---:|---:|---:|---:|"]
    for c in keep:
        i, o = out["categories"][c]["C0|안"][2], out["categories"][c]["C0|밖"][2]
        L.append(f"| {c} | {len(mat_of[c])} | {i[1]} | {pc(o):.1f}% {o[0]}/{o[1]} | "
                 f"{pc(i):.1f}% {i[0]}/{i[1]} | **+{pc(i)-pc(o):.1f}%p** |")

    L += ["", "## 2. 라운드별 (C0)", "",
          "| 카테고리 | 줬나 | r0 | r1 | r2 |", "|---|---|---:|---:|---:|"]
    for c in keep:
        for sd in ("안", "밖"):
            v = out["categories"][c][f"C0|{sd}"]
            L.append(f"| {c if sd=='안' else ''} | {'일러 줌' if sd=='안' else '안 줌'} | "
                     + " | ".join(f"{pc(x):.1f}% {x[0]}/{x[1]}" for x in v) + " |")

    L += ["", "## 3. 압박 세 수준 (마지막 수첩)", "",
          "| 카테고리 | 줬나 | C0 | C1 | C2 | C0→C2 |", "|---|---|---:|---:|---:|---:|"]
    for c in keep:
        for sd in ("안", "밖"):
            v = [out["categories"][c][f"{sc}|{sd}"][2] for sc in SCRIPTS]
            d = pc(v[2]) - pc(v[0])
            L.append(f"| {c if sd=='안' else ''} | {'일러 줌' if sd=='안' else '안 줌'} | "
                     + " | ".join(f"{pc(x):.1f}% {x[0]}/{x[1]}" for x in v)
                     + f" | {d:+.1f}%p |")

    L += ["", "## 4. 읽을 때", "",
          "- **분모를 보고 읽는다.** 4벌 24칸짜리는 한 칸이 4%p 를 움직인다.",
          "- **압박 열에서 순위를 읽지 않는다.** 대부분 ±7%p 안이고 분모가 얇다.",
          "- **절대값이 아니라 서열로 읽는다.** 글자 기준이라 말 바꿔 쓴 것을 놓친다 — "
          "실측 예로 `단계적으로`(표식)와 `단계적`(수첩)이 갈렸다.", ""]

    (HERE / f"CATS_{a.model}_{today}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / f"CATS_{a.model}_{today}.md").write_text("\n".join(L), encoding="utf-8")
    print(f"판 {runs} · 카테고리 이름 {len(mat_of)}종 중 {len(keep)}종 실음")
    for c in keep:
        i, o = out["categories"][c]["C0|안"][2], out["categories"][c]["C0|밖"][2]
        print(f"   {c:12s} 재료 {len(mat_of[c]):2d} · 안 {pc(i):5.1f} 밖 {pc(o):5.1f} "
              f"차 +{pc(i)-pc(o):.1f}%p")
    print(f"→ CATS_{a.model}_{today}.json · .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
