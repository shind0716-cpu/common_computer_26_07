"""[민옥 트랙 · 압박×카테고리] 재료 제작 검사 — LLM 0콜, 파일만 읽는다.

검사 3종 (PREREG_v0 §1-3 · 규칙 v1, 2026-08-26):
  ① 표식 고유성 — 각 표식은 자기 사실 문면에 정확히 1회, 다른 사실·사안문·가치문·
     각본·최종질문·옵션 어디에도 없다 (교차 검색 0).
  ② 구조 — 카테고리마다 사실 개수 동일(k개, k≥2) + 카테고리 안에서 한쪽이 다수 우세
     (동률 금지 — 만장일치가 아니면 ⚠ 경고로 표시) + favors 전체 대칭(반씩),
     가치 세트 A·B 가 카테고리 전체를 정확히 반분하고 aligned = 그 카테고리들의 다수 우세.
  ③ 누출 — 사안문(stub)에 사실 표식·문면 노출 0.

규칙 v1 변경(2026-08-26, 민옥): "카테고리당 정확히 2개 · 만장일치"를 "동수 k개 · 다수
우세"로 완화. 이유: 히든 프로필판에서 변환된 재료(카테고리당 3사실, 2:1 구조)를 사실
삭제 없이 받기 위함. 주의: k가 다른 재료끼리는 카테고리 생존율을 직접 비교하지 않는다.

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

    # ② 구조 (규칙 v1) — 카테고리 수는 재료가 정하되(짝수), 카테고리당 동수 k(k≥2) +
    #    카테고리 안 다수 우세(동률 금지). 만장일치가 아니면 경고만 남긴다 — 소수파 사실이
    #    섞인 재료(히든 프로필 변환판)를 허용하되, 눈금이 다르다는 표시는 남긴다.
    warnings: list[str] = []
    if len(opts) != 2:
        errors.append(f"옵션 수 {len(opts)} ≠ 2")
    if len(cats) % 2 != 0:
        errors.append(f"카테고리 수 {len(cats)} 가 홀수 — 가치 세트를 반분할 수 없다")
    k, rem = divmod(len(facts), len(cats)) if cats else (0, 1)
    if rem != 0 or k < 2:
        errors.append(f"사실 수 {len(facts)} 가 카테고리 {len(cats)} 의 동수 배분이 아님 "
                      "(카테고리당 같은 개수 · 최소 2개)")
    majority: dict[str, str | None] = {}
    for cat in cats:
        cf = [f for f in facts if f["category"] == cat]
        if k >= 2 and len(cf) != k:
            errors.append(f"카테고리 '{cat}' 사실 수 {len(cf)} ≠ {k} (동수 배분 위반)")
            continue
        votes: dict[str, int] = {}
        for f in cf:
            votes[f["favors"]] = votes.get(f["favors"], 0) + 1
        top = sorted(votes.items(), key=lambda kv: -kv[1])
        if len(top) > 1 and top[0][1] == top[1][1]:
            # 한 카테고리는 한쪽이 명확히 우세해야 한다. 동률이면 가치 정렬 답이
            # 자명하지 않게 되어 뒤집힘 판정이 흐려진다.
            errors.append(f"카테고리 '{cat}' 의 사실이 동률로 갈림 — 우세가 불명")
            majority[cat] = None
            continue
        majority[cat] = top[0][0]
        if len(top) > 1:
            warnings.append(f"카테고리 '{cat}' 는 만장일치가 아님({top[0][1]}:{top[1][1]}) — "
                            "소수파 사실 포함, 만장일치 재료와 생존율 직접 비교 금지")
    for opt in opts:
        n = sum(1 for f in facts if f["favors"] == opt)
        if n != len(facts) // 2:
            errors.append(f"favors '{opt}' 수 {n} ≠ {len(facts) // 2} (대칭 깨짐)")
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

    # 가치 정렬 자명성 (규칙 v1) — 각 세트의 카테고리에서 다수 우세가 aligned 와 같은지
    for key, v in vs.items():
        for cat in v["categories"]:
            maj = majority.get(cat)
            if maj is not None and maj != v["aligned"]:
                errors.append(f"세트 {key} 카테고리 '{cat}' 의 다수 우세 '{maj}' 가 "
                              f"aligned '{v['aligned']}' 와 불일치")

    if errors:
        print(f"[check_materials] 실패 {len(errors)}건:")
        for e in errors:
            print("  ✗ " + e)
        return 1
    for w in warnings:
        print("  ⚠ " + w)
    print(f"[check_materials] 통과(규칙 v1) — 표식 {len(facts)}개 고유·구조 대칭·누출 0"
          + (f" · 경고 {len(warnings)}건" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
