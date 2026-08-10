# -*- coding: utf-8 -*-
"""논문 재현 트랙 — 저자 perspective.py 계승 배분기.

입력 facts[]의 위치 인덱스를 저자 프롬프트에 그대로 주고, 산출 인덱스 배열 4개를
perspective_sets.sets에 원형 보존한 뒤 fact_id로 번역한다. 같은 관점의 pro/con 쌍은
항상 동일한 assigned_fact_ids를 공유한다.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from modules import authors_prompts, llm, paths  # noqa: E402
from extract_facts import (CallCheckpoint, MAX_TOKENS, MODEL, N, SCHEMA_VER,  # noqa: E402
                           TEMPERATURE, _validate_dry_output, obtain_json)

CREATED_BY = "paper_repro_perspective"
SEED = 20260810
llm.MAX_TOKENS = MAX_TOKENS  # 편차 P-1: 러너 안에서만 완화


def check_available(text, question, facts, pers) -> bool:
    """저자 discussion.py:43-54의 check_available 규칙 그대로."""
    if not isinstance(text, str):
        return False
    if not isinstance(question, str):
        return False
    if not isinstance(facts, list):
        return False
    if not isinstance(pers, list):
        return False
    if len(pers) != 4:
        return False
    return True


def audit_perspective_sets(sets: list, facts: list[dict]) -> list[str]:
    """저자 프롬프트의 계수 가능한 규칙 위반 범주를 반환(판정 모델 추가 없음)."""
    violations = []
    n = len(facts)
    valid_indices = set(range(n))
    if not isinstance(sets, list) or len(sets) != 4 or not all(isinstance(s, list) for s in sets):
        return ["not_four_lists"]
    flat = []
    invalid = False
    for group in sets:
        for idx in group:
            if not isinstance(idx, int) or isinstance(idx, bool) or idx not in valid_indices:
                invalid = True
            else:
                flat.append(idx)
    if invalid:
        violations.append("invalid_index")
    if any(set(g) == valid_indices for g in sets if all(isinstance(i, int) for i in g)):
        violations.append("perspective_has_all_facts")
    if valid_indices - set(flat):
        violations.append("fact_uncovered")
    critical = {i for i, fact in enumerate(facts) if fact.get("critical") is True}
    if any(not critical.issubset({i for i in group if isinstance(i, int)}) for group in sets):
        violations.append("critical_missing")
    return violations


def build_assignment_doc(issue_id: str, facts: list[dict], sets: list[list[int]],
                         created_at: str) -> dict:
    """저자 인덱스 배열을 assignment 픽스처와 같은 구조로 변환."""
    if not isinstance(sets, list) or len(sets) != 4 or not all(isinstance(s, list) for s in sets):
        raise ValueError(f"{issue_id}: perspective는 정확히 4개 배열이어야 함")
    fact_ids = [f["fact_id"] for f in facts]
    translated = []
    for group in sets:
        if any(not isinstance(i, int) or isinstance(i, bool) or i < 0 or i >= len(fact_ids)
               for i in group):
            raise ValueError(f"{issue_id}: perspective에 유효하지 않은 fact index 존재")
        translated.append([fact_ids[i] for i in group])
    agents = []
    for k, assigned in enumerate(translated):
        perspective = f"관점{k + 1}"
        agents.append({"agent_id": f"agent_{2 * k + 1}", "perspective": perspective,
                       "stance": "pro", "assigned_fact_ids": list(assigned)})
        agents.append({"agent_id": f"agent_{2 * k + 2}", "perspective": perspective,
                       "stance": "con", "assigned_fact_ids": list(assigned)})
    return {
        "schema_ver": SCHEMA_VER,
        "created_by": CREATED_BY,
        "created_at": created_at,
        "issue_id": issue_id,
        "seed": SEED,
        "_note": ("저자 perspective.py의 위치 인덱스 배열을 perspective_sets.sets에 원형 보존. "
                  "같은 관점 pro/con 쌍은 assigned_fact_ids가 완전히 동일하다."),
        "perspective_sets": {
            "origin_format": "list of 4 lists of positional fact indices (author perspective.py output)",
            "sets": sets,
        },
        "agents": agents,
    }


def _issue_ids(data_root: Path) -> list[str]:
    manifest = json.loads((data_root / "sample_manifest.json").read_text(encoding="utf-8"))
    ids = [x["issue_id"] for x in manifest["sample"]["ids"]]
    if len(ids) != manifest["sample"]["n"] or len(ids) != len(set(ids)):
        raise ValueError("sample_manifest의 표본 수 또는 issue_id 유일성 불일치")
    return ids


def _issue_plan(data_root: Path, dry: bool) -> tuple[list[str], list[str], list[dict]]:
    """전체 표본, 배분 대상, refined<5 제외 기록을 한 번에 확정한다."""
    all_ids = _issue_ids(data_root)
    if dry:
        # dry는 extractor 실산출 전에도 0콜 접합 리허설이 가능해야 하므로 합성 facts를 쓴다.
        return all_ids, all_ids, []
    manifest_path = data_root / "facts_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"facts_manifest.json 없음: {manifest_path} — extractor 완료 전에 배분기 실행 금지")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    excluded = manifest.get("excluded_refined_lt5")
    if not isinstance(excluded, list) or not all(isinstance(x, str) for x in excluded):
        raise ValueError("facts_manifest.excluded_refined_lt5는 issue_id 문자열 배열이어야 함")
    # PR#34 리뷰: failed_parse 도 제외 집합이다 — extractor 가 facts 없이 기록만 남긴
    # 이슈가 eligible 에 남으면 FileNotFoundError 로 전체 중단되거나, 이전 트랜치의
    # 낡은 facts 파일이 있으면 조용히 섞인다. 두 집합을 합치고 사유를 보존한다.
    failed = manifest.get("failed_parse", [])
    if not isinstance(failed, list) or not all(
            isinstance(x, dict) and isinstance(x.get("issue_id"), str) for x in failed):
        raise ValueError("facts_manifest.failed_parse는 {issue_id,…} 객체 배열이어야 함")
    failed_ids = {x["issue_id"] for x in failed}
    unknown = (set(excluded) | failed_ids) - set(all_ids)
    if unknown:
        raise ValueError(f"facts_manifest에 표본 밖 제외 issue_id 존재: {sorted(unknown)}")
    excluded_set = set(excluded) | failed_ids
    eligible = [issue_id for issue_id in all_ids if issue_id not in excluded_set]
    skipped = []
    for issue_id in all_ids:
        if issue_id in failed_ids:
            skipped.append({"issue_id": issue_id, "reason": "extractor_failed_parse"})
        elif issue_id in set(excluded):
            skipped.append({"issue_id": issue_id, "reason": "refined_lt5"})
    return all_ids, eligible, skipped


def _synthetic_facts(issue_id: str) -> list[dict]:
    prefix = f"fact_{issue_id[len('issue_'):]}"
    return [
        {"fact_id": f"{prefix}_{i + 1:02d}", "origin_index": i,
         "text": f"DRY fact {i + 1} for {issue_id}", "tags": [], "critical": i == 0,
         "prior": {"score": None, "probe_model": None,
                   "probe_prompt_ver": None, "probed_at": None}}
        for i in range(6)
    ]


def _dry_sets(facts: list[dict]) -> list[list[int]]:
    critical = [i for i, f in enumerate(facts) if f.get("critical") is True]
    noncritical = [i for i, f in enumerate(facts) if not f.get("critical")]
    sets = [list(critical) for _ in range(4)]
    for pos, idx in enumerate(noncritical):
        sets[pos % 4].append(idx)
    return sets


def _prompt(facts: list[dict]) -> str:
    lines = "".join(
        f"{i} {'(Important)' if fact['critical'] else '(Not Important)'}: {fact['text']}\n"
        for i, fact in enumerate(facts))
    prompt = authors_prompts.load("perspective").replace("<===facts===>", lines)
    if "<===facts===>" in prompt:
        raise ValueError("perspective 프롬프트 슬롯 미치환")
    return prompt


def run(data_root: Path, max_calls: int, dry: bool) -> dict:
    data_root = Path(data_root).resolve()
    old_data = paths.DATA
    paths.DATA = data_root
    try:
        all_issue_ids, issue_ids, excluded_skips = _issue_plan(data_root, dry)
        prompt_ver = authors_prompts.version_tag()
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if dry and max_calls < len(issue_ids):
            raise RuntimeError(
                f"dry 예산 점검 실패: 예정 {len(issue_ids)}콜 > --max-calls {max_calls}")
        checkpoint = None if dry else CallCheckpoint(
            paths.DATA / "raw_calls" / "assign_perspective_calls.jsonl", max_calls,
            prompt_ver=prompt_ver)
        if not dry:
            llm.preflight(MODEL, temperature=TEMPERATURE, reasoning="default")

        target_ctx = tempfile.TemporaryDirectory(prefix="paper_repro_assign_dry_") if dry else None
        target_root = Path(target_ctx.name) if target_ctx else paths.DATA
        validated = 0
        skipped = list(excluded_skips)
        violations_by_issue = {}
        pair_equal = 0
        pair_total = 0
        try:
            for issue_id in issue_ids:
                issue = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
                if dry:
                    facts = _synthetic_facts(issue_id)
                    sets = _dry_sets(facts)
                    raw = json.dumps(sets)
                else:
                    facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
                    facts = facts_doc["facts"]
                    raw = checkpoint.call(_prompt(facts), f"{issue_id}|perspective")
                    sets = obtain_json(raw)
                # dry에서도 실제 저자 프롬프트 조립을 통과시킨다.
                _prompt(facts)
                if not check_available(issue["body"], issue["question"], facts, sets):
                    skipped.append({"issue_id": issue_id, "reason": "check_available"})
                    continue
                violations = audit_perspective_sets(sets, facts)
                if violations:
                    violations_by_issue[issue_id] = violations
                if "invalid_index" in violations or "not_four_lists" in violations:
                    skipped.append({"issue_id": issue_id, "reason": ",".join(violations)})
                    continue
                doc = build_assignment_doc(issue_id, facts, sets, created_at)
                if dry:
                    old_target = paths.DATA
                    paths.DATA = target_root
                try:
                    out = paths.assignment(issue_id)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
                    _validate_dry_output(out)
                finally:
                    if dry:
                        paths.DATA = old_target
                validated += 1
                for k in range(0, 8, 2):
                    pair_total += 1
                    if (doc["agents"][k]["assigned_fact_ids"] ==
                            doc["agents"][k + 1]["assigned_fact_ids"]):
                        pair_equal += 1
        finally:
            if target_ctx:
                target_ctx.cleanup()

        result = {
            "dry": dry, "issues": len(all_issue_ids), "planned_calls": len(issue_ids),
            "actual_calls": 0 if dry else checkpoint.calls_this_run,
            "validated": validated, "skipped": skipped,
            "violations_by_issue": violations_by_issue,
            "pair_equal": pair_equal, "pair_total": pair_total,
            "prompt_ver": prompt_ver, "seed": SEED,
        }
        if not dry:
            manifest = {
                "schema_ver": SCHEMA_VER, "created_by": CREATED_BY,
                "created_at": created_at, **{k: v for k, v in result.items() if k != "dry"},
                "raw_calls": "raw_calls/assign_perspective_calls.jsonl",
                "model": MODEL, "temperature": TEMPERATURE, "n": N,
            }
            (paths.DATA / "assignments_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    finally:
        paths.DATA = old_data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=HERE / "data")
    ap.add_argument("--max-calls", type=int, default=200)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true", help="0콜 완주 리허설; 합성 facts로 접합 검증")
    mode.add_argument("--live", action="store_true", help="지시자 승인 후에만 사용할 실호출 모드")
    args = ap.parse_args()
    result = run(args.data_dir, args.max_calls, dry=args.dry)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
