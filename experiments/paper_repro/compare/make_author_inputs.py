# -*- coding: utf-8 -*-
"""비교 실험 — 우리 산출물을 저자 파이프라인 입력 3종으로 변환 (0콜 · 저자 코드 무수정).

지위: 접합 계층(COMPARE_SETUP §6 주입 계획 이행). 저자 하류가 실제로 읽는 필드만 정확히
채우고(discussion.py:95-98·evaluation.py:59,65 실측), 자기 검증(불일치 즉사)을 내장한다.

저자 형식 (facts.py·perspective.py 실측):
  datasets/scruples.json          [{description, question, ...} ...]      (위치 배열)
  data/facts_scruples.json        [[raw_facts, refined_facts, important_facts] ...]
  data/perspective_scruples.json  [[4개 인덱스 배열] ...]

인덱스 순서 = 채택 순서(0543·0248·0262)로 고정하고 mapping manifest 에 기록한다 —
저자 산출물({index}/ 디렉터리)을 우리 issue_id 로 되돌릴 유일한 열쇠다.

사용:
  PYTHONUTF8=1 python experiments/paper_repro/compare/make_author_inputs.py           # 검증+생성
  PYTHONUTF8=1 python experiments/paper_repro/compare/make_author_inputs.py --check   # 검증만(파일 미작성)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACK = HERE.parent
ROOT = TRACK.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TRACK))

import bridge  # noqa: E402
from extract_facts import obtain_json  # noqa: E402 — 저자 계승 파서(raw 단계 복원용)
from modules import paths  # noqa: E402

ISSUE_IDS = ["issue_ethics_0543", "issue_ethics_0248", "issue_ethics_0262"]  # 요한 채택 8/10
DATA = TRACK / "data"


def build_inputs(issue_ids: list[str]) -> tuple[list, list, list, list]:
    """(datasets, facts, perspective, mapping) — 자기 검증 내장(즉사).
    트랙 data 루트로 paths 를 재지정한다(러너 관례 — 종료 시 원복)."""
    old_data = paths.DATA
    paths.DATA = DATA
    try:
        return _build_inputs_inner(issue_ids)
    finally:
        paths.DATA = old_data


def _build_inputs_inner(issue_ids: list[str]) -> tuple[list, list, list, list]:
    datasets, facts_out, pers_out, mapping = [], [], [], []
    raw_ledger = {}
    ck = DATA / "raw_calls" / "extract_facts_calls.jsonl"
    for line in ck.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            raw_ledger[r["tag"]] = r["raw"]

    for idx, iid in enumerate(issue_ids):
        issue = json.loads(paths.issue(iid).read_text(encoding="utf-8"))
        facts_doc = json.loads(paths.facts(iid).read_text(encoding="utf-8"))
        assignment = json.loads(paths.assignment(iid).read_text(encoding="utf-8"))

        # 저자 하류가 읽는 두 필드 + 추적용 origin_id (저자 코드는 여분 키를 안 읽는다)
        q = issue.get("question")
        if not isinstance(q, str) or not q.strip():
            raise SystemExit(f"{iid}: question 부재 — §1′ 경계 2(이 트랙 폴백 금지)")
        datasets.append({"description": issue["body"], "question": q,
                         "origin_id": issue.get("source_meta", {}).get("origin_id")})

        # facts 3중: raw 는 우리 원장의 initial 응답을 저자 파서로 복원, refined/important 는
        # origin_index 순 (bridge H1 이 순서==인덱스를 강제)
        ordered_ids = bridge.fact_ids_in_order(facts_doc)  # 어긋나면 즉사
        refined = [f["text"] for f in facts_doc["facts"]]
        important = [bool(f["critical"]) for f in facts_doc["facts"]]
        raw_resp = raw_ledger.get(f"{iid}|initial")
        if raw_resp is None:
            raise SystemExit(f"{iid}: raw_calls 에 initial 응답 없음 — 추출 원장 확인")
        raw_facts = obtain_json(raw_resp)
        if not isinstance(raw_facts, list):
            raise SystemExit(f"{iid}: initial 응답이 배열로 파싱되지 않음 — 원장 확인")
        facts_out.append([raw_facts, refined, important])

        # perspective: 접합 계층이 원형 보존해 둔 위치 인덱스 배열 그대로
        sets = assignment["perspective_sets"]["sets"]
        # 자기 검증: sets 를 bridge 로 번역하면 assignment 의 배분과 일치해야 한다(H8)
        for k, group in enumerate(sets):
            translated = bridge.to_fact_ids(facts_doc, group)
            if translated != assignment["agents"][2 * k]["assigned_fact_ids"]:
                raise SystemExit(f"{iid}: sets[{k}] 번역 불일치 — 원형 보존 위반(H8)")
        # 자기 검증: refined 길이와 인덱스 전집합 정합
        n = len(refined)
        if any(i < 0 or i >= n for g in sets for i in g):
            raise SystemExit(f"{iid}: perspective 인덱스가 refined 범위 밖")
        _ = ordered_ids
        pers_out.append(sets)

        mapping.append({"author_index": idx, "issue_id": iid,
                        "n_facts": n, "question": q})
    return datasets, facts_out, pers_out, mapping


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="검증만 — 파일 미작성")
    ap.add_argument("--dest", type=Path, default=HERE / "author_inputs",
                    help="산출 디렉터리 (기본: compare/author_inputs — 저자 리포 복사는 실행 단계)")
    args = ap.parse_args()

    datasets, facts_out, pers_out, mapping = build_inputs(ISSUE_IDS)
    print(f"[make_author_inputs] 검증 통과 — {len(mapping)}건 "
          f"(팩트 {[m['n_facts'] for m in mapping]})")
    if args.check:
        return

    dest = args.dest
    dest.mkdir(parents=True, exist_ok=True)
    files = {
        "scruples.json": datasets,                # → DelibTrace-main/datasets/
        "facts_scruples.json": facts_out,         # → DelibTrace-main/data/
        "perspective_scruples.json": pers_out,    # → DelibTrace-main/data/
    }
    shas = {}
    for name, obj in files.items():
        p = dest / name
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        shas[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (dest / "mapping_manifest.json").write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "created_by": "compare_make_author_inputs",
        "purpose": "저자 판 입력 — index↔issue_id 매핑 (COMPARE_SETUP §6)",
        "issue_order": mapping,
        "sha256": shas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[make_author_inputs] 저장: {dest} (파일 3종 + mapping_manifest)")
    for name, sha in shas.items():
        print(f"  {name}  sha256={sha[:16]}…")


if __name__ == "__main__":
    main()
