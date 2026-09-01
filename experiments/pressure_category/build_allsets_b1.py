"""[공용 코어 · 압박×카테고리] ALL 세트 생성기 — 현행 A+B 가치문 병합 (콜 0).

## 왜 필요한가

`values/all_*.json`(2026-08-27)과 `values/allb1_*.json`(2026-09-01)은 둘 다
「A+B 병합, 전부 주기」인데 **병합한 가치문의 판이 다르다.** 재료가 개정되면서
카테고리 축이 이해관계자(아동·기관·보호자·또래환경)에서 사안 속성(비용·접근성·…)
으로 바뀌었는데, 구판 세트 아홉은 개정 전 가치문을 병합한 것이라 현행 재료
카테고리와 **겹침이 0** 이다. 그 세트로 돈 판은 안/밖을 가를 수 없다.

이 생성기는 병합 규칙을 코드로 고정해, 세 모델 균형에 필요한 세트를 같은 규칙으로
짓는다. 규칙이 맞다는 증거는 **기존 allb1_* 아홉을 재생성해 글자까지 대조**하는 것이다
(--verify). 대조가 깨지면 짓지 않는다.

## 병합 규칙 (exact_clause_union)

  categories  A.categories + B.categories (순서 유지, 여섯)
  statement   "너에게는 다음 여섯 가지가 중요하다: " + A절들 + ", " + B절들 + "."
              — 새 낱말을 만들지 않는다. 개수말만 세→여섯으로 바꾼다.

새 낱말이 없다는 것이 이 규칙의 요점이다. ALL 세트가 A·B 와 다른 문면을 쓰면
보존율 차이가 가치 때문인지 문면 때문인지 갈리지 않는다.

사용:
  PYTHONUTF8=1 python build_allsets_b1.py --verify              # 기존 9개 재생성 대조만
  PYTHONUTF8=1 python build_allsets_b1.py --write issue_ambulance issue_elderdrive ...
산출: values/allb1_<slug>.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from modules import content_hash  # noqa: E402

HERE = Path(__file__).resolve().parent
MATERIALS = HERE / "materials"
VALUES = HERE / "values"
PREFIX = "너에게는 다음 여섯 가지가 중요하다: "
HEAD = "너에게는 다음 세 가지가 중요하다: "


def index() -> dict:
    """issue_id → 재료 파일 경로. 파일 이름이 issue_id 와 다른 재료가 있다(러너와 같은 방식)."""
    reg = {}
    for p in sorted(MATERIALS.glob("*.json")):
        if p.name == "MATERIALS_TEMPLATE.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            if d["issue_id"] in reg:
                raise SystemExit(f"issue_id 충돌: {d['issue_id']}")
            reg[d["issue_id"]] = p
    return reg


REG = index()


def clauses(stmt: str) -> str:
    """가치문에서 절 목록만 떼어 낸다 — 머리말과 끝점을 벗긴다."""
    s = stmt.strip()
    if not s.startswith(HEAD):
        raise ValueError(f"머리말이 다르다: {s[:40]}")
    return s[len(HEAD):].rstrip().rstrip(".")


def merge(mat: dict) -> dict:
    A, B = mat["value_sets"]["A"], mat["value_sets"]["B"]
    return {
        "categories": list(A["categories"]) + list(B["categories"]),
        "statement": PREFIX + clauses(A["statement"]) + ", " + clauses(B["statement"]) + ".",
    }


def build(iid: str, slug: str) -> dict:
    p = REG[iid]
    mat = json.loads(p.read_text(encoding="utf-8"))
    m = merge(mat)
    if set(m["categories"]) != set(mat["categories"]):
        raise ValueError(f"{iid}: 병합 카테고리가 재료 카테고리와 다르다")
    return {
        "vset_id": f"allb1_{slug}",
        "materials": iid,
        "materials_hash": content_hash.sha256_file(p)[:12],
        "derived_from": {"value_sets": ["A", "B"], "rule": "exact_clause_union"},
        "statement": m["statement"],
        "categories": m["categories"],
        "note": "belief1 ALL 3모델 균형판(2026-09-01). 현행 A+B 가치문의 구절을 그대로 "
                "병합 — build_allsets_b1.py 가 짓고 기존 9개 재생성 대조를 통과했다.",
    }


def verify() -> tuple[list[str], list[str]]:
    """기존 allb1_* 를 규칙으로 재생성해 글자까지 대조한다.

    되돌림: (불일치, 규칙밖). **규칙 밖**은 A/B 가치문의 머리말이 표준형
    (「너에게는 다음 세 가지가 중요하다: 」)이 아니라 이 규칙으로 재생성할 수 없는
    재료다 — 실패가 아니라 이 생성기의 적용 범위 밖이라는 뜻이므로, 그런 재료의
    세트는 이 생성기로 짓지 않는다.
    """
    bad, out = [], []
    for p in sorted(VALUES.glob("allb1_*.json")):
        cur = json.loads(p.read_text(encoding="utf-8"))
        try:
            got = build(cur["materials"], cur["vset_id"][len("allb1_"):])
        except ValueError as e:
            out.append(f"{p.name} ({cur['materials']}) — {e}")
            continue
        except Exception as e:
            bad.append(f"{p.name}: 재생성 실패 {e}")
            continue
        for k in ("statement", "categories"):
            if got[k] != cur[k]:
                bad.append(f"{p.name}: {k} 불일치 | 기존 {cur[k]} | 재생성 {got[k]}")
        if cur.get("materials_hash") and cur["materials_hash"] != got["materials_hash"]:
            bad.append(f"{p.name}: materials_hash 불일치 {cur['materials_hash']} → {got['materials_hash']}")
    return bad, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="기존 세트 재생성 대조만 (쓰지 않음)")
    ap.add_argument("--write", nargs="*", default=[], metavar="ISSUE_ID")
    a = ap.parse_args()

    bad, out = verify()
    n = len(list(VALUES.glob("allb1_*.json")))
    print(f"기존 allb1_* {n}개 — 재생성 대조 {n - len(out) - len(bad)}개 통과 · "
          f"규칙 밖 {len(out)}개 · 불일치 {len(bad)}개")
    for o in out:
        print("   [규칙 밖] " + o)
    for b in bad:
        print("   [불일치] " + b)
    if bad:
        return 1
    if a.verify or not a.write:
        return 0

    for iid in a.write:
        slug = iid[len("issue_"):] if iid.startswith("issue_") else iid
        d = build(iid, slug)
        out = VALUES / f"{d['vset_id']}.json"
        if out.exists():
            print(f"[skip] 이미 있다: {out.name}")
            continue
        out.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[새로] {out.name}  지문 {d['materials_hash']}  카테고리 {len(d['categories'])}")
        print(f"        {d['statement']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
