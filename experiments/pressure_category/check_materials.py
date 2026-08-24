"""[민옥 트랙 · 압박×카테고리] 재료 제작 검사 — LLM 0콜, 파일만 읽는다.

검사 3종 (PREREG_v0 §1-3):
  ① 표식 고유성 — 각 표식은 자기 사실 문면에 정확히 1회, 다른 사실·사안문·가치문·
     각본·최종질문·옵션 어디에도 없다 (교차 검색 0).
  ② 구조 — 카테고리마다 사실 정확히 2개(옵션별 1개씩) = favors 대칭,
     가치 세트 A·B 가 카테고리 전체를 정확히 반분하고 aligned 가 서로 다르다.
  ③ 누출 — 사안문(stub)에 사실 표식·문면 노출 0.

어느 재료든 같은 잣대다 — 팀원이 만든 시나리오 파일도 이걸 통과해야 러너가 받는다.

통과하면 종료코드 0, 하나라도 걸리면 1 (사유 전부 출력).
사용: PYTHONUTF8=1 python experiments/pressure_category/check_materials.py [재료파일경로]
      (인자 생략 시 materials/*.json 전량 검사 — 템플릿 제외)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATERIALS_DIR = HERE / "materials"


def main() -> int:
    if len(sys.argv) > 1:
        targets = [Path(sys.argv[1])]
    else:   # 인자 없으면 materials/ 전량 검사 (템플릿 제외)
        targets = [p for p in sorted(MATERIALS_DIR.glob("*.json"))
                   if p.name != "MATERIALS_TEMPLATE.json"]
        if not targets:
            print("[check_materials] materials/ 에 재료가 없다")
            return 1
    rc = 0
    for t in targets:
        rc = max(rc, check_one(t))
    return rc


def check_one(target: Path) -> int:
    if not target.exists():
        print(f"[check_materials] 파일 없음: {target}")
        return 1
    doc = json.loads(target.read_text(encoding="utf-8"))
    print(f"[check_materials] 대상: {target.name} (issue_id={doc.get('issue_id')})")

    # ⓪ 필수 칸 — 러너가 읽는 키가 다 있는가 (팀원 재료의 흔한 실수를 먼저 잡는다)
    missing = [k for k in ("issue_id", "stub", "options", "categories", "facts",
                           "value_sets", "scripts", "prompts") if k not in doc]
    for vs_key in ("A", "B"):
        if vs_key not in doc.get("value_sets", {}):
            missing.append(f"value_sets.{vs_key}")
    for sc_key in ("C0", "C1", "C2"):
        if sc_key not in doc.get("scripts", {}):
            missing.append(f"scripts.{sc_key}")
    for pr_key in ("r0_task", "round_task", "final_poll"):
        if pr_key not in doc.get("prompts", {}):
            missing.append(f"prompts.{pr_key}")
    if missing:
        print(f"[check_materials] 실패 — 필수 칸 없음: {', '.join(missing)} "
              "(materials/MATERIALS_TEMPLATE.json 을 보라)")
        return 1
    for sc_key in ("C1", "C2"):
        if "{TARGET}" not in doc["scripts"][sc_key].get("line", ""):
            print(f"[check_materials] 실패 — scripts.{sc_key}.line 에 {{TARGET}} 자리가 없다 "
                  "(압박 방향을 채울 수 없음)")
            return 1
    facts = doc["facts"]
    cats = doc["categories"]
    opts = doc["options"]
    errors: list[str] = []

    # ② 구조 — 카테고리 수는 재료가 정하되(짝수), 카테고리당 2사실·옵션별 1사실은 불변
    if len(opts) != 2:
        errors.append(f"옵션 수 {len(opts)} ≠ 2")
    if len(cats) % 2 != 0:
        errors.append(f"카테고리 수 {len(cats)} 가 홀수 — 가치 세트를 반분할 수 없다")
    if len(facts) != 2 * len(cats):
        errors.append(f"사실 수 {len(facts)} ≠ 카테고리 {len(cats)} × 2")
    for cat in cats:
        cf = [f for f in facts if f["category"] == cat]
        if len(cf) != 2:
            errors.append(f"카테고리 '{cat}' 사실 수 {len(cf)} ≠ 2")
        elif len({f["favors"] for f in cf}) != 1:
            # 한 카테고리는 한쪽이 명확히 우세해야 한다(두 사실이 같은 쪽을 가리킴).
            # 갈리면 가치 정렬 답이 자명하지 않게 되어 뒤집힘 판정이 흐려진다.
            errors.append(f"카테고리 '{cat}' 의 두 사실이 서로 다른 쪽을 편듦 — 우세가 불명")
    for opt in opts:
        n = sum(1 for f in facts if f["favors"] == opt)
        if n != len(cats):
            errors.append(f"favors '{opt}' 수 {n} ≠ {len(cats)} (대칭 깨짐)")
    vs = doc["value_sets"]
    a, b = set(vs["A"]["categories"]), set(vs["B"]["categories"])
    if a | b != set(cats) or a & b:
        errors.append(f"가치 세트가 카테고리를 반분하지 않음: A={sorted(a)} B={sorted(b)}")
    if vs["A"]["aligned"] == vs["B"]["aligned"]:
        errors.append("두 가치 세트의 aligned 가 같음 — 거울이 아님")

    # ① 표식 고유성
    non_fact_texts = {
        "stub": doc["stub"],
        "value_A": vs["A"]["statement"],
        "value_B": vs["B"]["statement"],
        "script_C0": doc["scripts"]["C0"]["line"],
        "script_C1": doc["scripts"]["C1"]["line"],
        "script_C2": doc["scripts"]["C2"]["line"],
        "final_poll": doc["prompts"]["final_poll"],
        "r0_task": doc["prompts"]["r0_task"],
        "round_task": doc["prompts"]["round_task"],
    }
    anchors = [f["anchor"] for f in facts]
    if len(set(anchors)) != len(anchors):
        errors.append("표식 중복 존재")
    for f in facts:
        if f["text"].count(f["anchor"]) != 1:
            errors.append(f"{f['id']}: 표식 '{f['anchor']}' 이 자기 문면에 "
                          f"{f['text'].count(f['anchor'])}회 (1회여야 함)")
        for g in facts:
            if g["id"] != f["id"] and f["anchor"] in g["text"]:
                errors.append(f"{f['id']} 표식 '{f['anchor']}' 이 {g['id']} 문면에도 등장")
        for name, txt in non_fact_texts.items():
            if f["anchor"] in txt:
                errors.append(f"{f['id']} 표식 '{f['anchor']}' 이 {name} 에 누출")

    # ③ 사안문 누출 (문면 통째)
    for f in facts:
        if f["text"] in doc["stub"]:
            errors.append(f"{f['id']} 문면이 사안문에 통째로 노출")

    # 가치 정렬 자명성 — 각 세트의 카테고리에서 aligned 옵션이 전부 우세인지
    for key, v in vs.items():
        for cat in v["categories"]:
            favors = {f["favors"] for f in facts if f["category"] == cat}
            if favors != {v["aligned"]}:
                errors.append(f"세트 {key} 카테고리 '{cat}' 의 favors {sorted(favors)} 가 "
                              f"aligned '{v['aligned']}' 와 불일치")

    if errors:
        print(f"[check_materials] 실패 {len(errors)}건:")
        for e in errors:
            print("  ✗ " + e)
        return 1
    print(f"[check_materials] 통과 — 표식 {len(facts)}개 고유·구조 대칭·누출 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
