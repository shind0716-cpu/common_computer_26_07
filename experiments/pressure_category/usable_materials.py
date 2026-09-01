"""[공용 코어 · 압박×카테고리] 쓸 수 있는 재료 가리기 — 보고서에 인용 가능한가 (콜 0).

## 무엇을 정하나

최종 보고서에 **표식 기반 수치를 인용할 수 있는 재료**와 **못 하는 재료**를 가른다.
판정은 하나뿐이다 — 그 재료의 카테고리마다 기계가 무언가를 볼 수 있었나.

카테고리 하나가 실호출 전 판에서 **한 번도** 안 잡히면 그 카테고리에 대해서는
"덜 남았다"도 "더 남았다"도 말할 수 없다. 사실이 없어서인지 잣대가 못 본 것인지
가르지 못하기 때문이다(cat_feeding_days_list 실측: 여섯 중 셋이 0, 그런데 수첩 원문에는
여섯 사실이 다 있었다).

## 등급

  A 쓸 수 있다      죽은 카테고리 0 — 여섯 축 전부에 대해 뭐라도 말할 수 있다
  B 조건부          죽은 카테고리 1~2 — 그 축은 빼고 나머지로만 말한다 (어느 축인지 표기)
  C 표식 수치 못 씀  죽은 카테고리 3 이상 — 최종 선택·사람 판독만 쓴다

등급은 재료의 좋고 나쁨이 아니라 **이 잣대로 잴 수 있나**의 판정이다. C 재료도
최종 선택(final_poll)과 사람 판독에는 그대로 쓸 수 있다.

## 곁들여 표시하는 것 (판정에는 안 들어간다)

  와/과   GUIDE §2-2 가 금지한 표식이 몇 개인가 (check_scenarios ③)
  세트    그 재료를 쓰는 가치 세트가 현행 재료 카테고리와 맞나

잣대는 `aggregate_all11.py` 와 같다(② 접어서 = 기존 스캐너 판정). 판은 `runs/<모델>/`
전량이고 `_dry`·`_scout` 같은 밑줄 폴더는 뺀다.

사용: PYTHONUTF8=1 python experiments/pressure_category/usable_materials.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate_all11 as A  # noqa: E402  — 잣대(probe/norm)를 그대로 쓴다

HERE = A.HERE
OUT = HERE / "USABLE_MATERIALS_2026-09-01.md"


def load_materials() -> dict:
    mats = {}
    for p in sorted((HERE / "materials").glob("*.json")):
        if p.name == "MATERIALS_TEMPLATE.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema") != "pressure_materials_v0":
            continue
        mats[d["issue_id"]] = (p, d)
    return mats


def value_set_currency(mats: dict) -> dict:
    """재료별로 그 재료를 가리키는 가치 세트 중 카테고리가 어긋난 것 목록."""
    bad = defaultdict(list)
    for p in sorted((HERE / "values").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        iid, cats = d.get("materials"), set(d.get("categories") or [])
        if not cats or iid not in mats:
            continue
        if cats != set(mats[iid][1]["categories"]):
            bad[iid].append(p.stem)
    return bad


def scan(mats: dict):
    """판마다 마지막 수첩에서 표식을 찾고, 재료·카테고리 단위로 접는다."""
    alive = defaultdict(lambda: [0, 0])          # (iid, cat) → [산 판, 전체 판]
    runs = defaultdict(int)                       # iid → 판 수
    hashes = defaultdict(set)                     # iid → 판이 가리키는 재료 지문
    for p in sorted((HERE / "runs").rglob("run_*.json")):
        if p.relative_to(HERE / "runs").parts[0].startswith("_"):
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        iid = doc.get("issue_id")
        if iid not in mats:
            continue
        notes = doc.get("notes") or []
        if not notes:
            continue
        M = mats[iid][1]
        runs[iid] += 1
        hashes[iid].add(doc.get("materials_hash"))
        last = notes[-1]
        by_cat = defaultdict(list)
        for f in M["facts"]:
            by_cat[f["category"]].append(f)
        for cat, fs in by_cat.items():
            hit = any(0 < A.probe(f["anchor"], last)[0] <= 2 for f in fs)
            alive[(iid, cat)][0] += int(hit)
            alive[(iid, cat)][1] += 1
    return alive, runs, hashes


def main() -> int:
    mats = load_materials()
    stale = value_set_currency(mats)
    alive, runs, hashes = scan(mats)

    rows = []
    for iid, (path, M) in sorted(mats.items()):
        n = runs.get(iid, 0)
        if not n:
            continue
        cats = M["categories"]
        dead = [c for c in cats if alive[(iid, c)][0] == 0]
        live_cells = sum(alive[(iid, c)][0] for c in cats)
        tot_cells = sum(alive[(iid, c)][1] for c in cats)
        josa = [f["anchor"] for f in M["facts"] if re.search(r"(와|과|및)\s", f["anchor"])]
        grade = "A" if not dead else ("B" if len(dead) <= 2 else "C")
        rows.append({
            "issue": iid, "판": n, "등급": grade,
            "카테고리생존율": round(100 * live_cells / tot_cells, 1) if tot_cells else 0.0,
            "죽은 카테고리": dead,
            "와/과 표식": josa,
            "어긋난 세트": stale.get(iid, []),
            "지문": sorted(hashes[iid]),
        })
    rows.sort(key=lambda r: ("ABC".index(r["등급"]), -r["카테고리생존율"]))

    L = ["# 쓸 수 있는 재료 — 표식 기반 수치를 인용할 수 있는가 (2026-09-01, 기계 생성물)",
         "",
         "> `usable_materials.py` 가 찍는다. 판정은 **죽은 카테고리 수** 하나로 한다 —",
         "> 실호출 전 판에서 한 번도 안 잡힌 카테고리는 사실이 없어서인지 잣대가 못 본",
         "> 것인지 못 가르므로, 그 축으로는 아무 말도 할 수 없다.",
         "> 잣대는 `aggregate_all11.py` 와 같은 ② 접어서(= 기존 스캐너 판정).",
         "> **C 등급도 최종 선택과 사람 판독에는 그대로 쓸 수 있다** — 못 쓰는 것은 표식 수치뿐이다.",
         "",
         f"실호출 판이 있는 재료 {len(rows)}벌 · "
         f"A {sum(1 for r in rows if r['등급']=='A')} · "
         f"B {sum(1 for r in rows if r['등급']=='B')} · "
         f"C {sum(1 for r in rows if r['등급']=='C')}",
         "",
         "| 등급 | 재료 | 판 | 카테고리 생존율 | 죽은 카테고리 | 와/과 표식 | 어긋난 가치 세트 |",
         "|:-:|---|---:|---:|---|---|---|"]
    for r in rows:
        L.append(f"| **{r['등급']}** | {r['issue'].replace('issue_', '')} | {r['판']} | "
                 f"{r['카테고리생존율']:.1f}% | "
                 f"{'—' if not r['죽은 카테고리'] else ' · '.join(r['죽은 카테고리'])} | "
                 f"{'—' if not r['와/과 표식'] else ' · '.join('「'+a+'」' for a in r['와/과 표식'])} | "
                 f"{'—' if not r['어긋난 세트'] else ' · '.join(r['어긋난 세트'])} |")

    L += ["", "## 지문이 여럿인 재료 (판마다 다른 재료를 가리킨다 — 섞어 세면 안 된다)", ""]
    multi = [r for r in rows if len(r["지문"]) > 1]
    if multi:
        for r in multi:
            L.append(f"- {r['issue']} — 지문 {r['지문']}")
    else:
        L.append("없다 — 실호출 판이 가리키는 재료 지문은 재료마다 하나뿐이다.")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"찍었다: {OUT.name}")
    for g in "ABC":
        rs = [r for r in rows if r["등급"] == g]
        print(f"\n[{g}] {len(rs)}벌")
        for r in rs:
            d = "" if not r["죽은 카테고리"] else "  죽은 축: " + "·".join(r["죽은 카테고리"])
            print(f"   {r['issue']:32s} {r['판']:4d}판  {r['카테고리생존율']:5.1f}%{d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
