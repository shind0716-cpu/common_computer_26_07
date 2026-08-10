# -*- coding: utf-8 -*-
"""논문 재현 트랙 — 브리지: 인덱스↔ID 번역 + 저자 축 판정물의 judgment 변환 (접합 계층 · 요한).

지위: 접합 계층 모듈 2/2 (1은 load_issues). LLM 호출 0 — 전부 순수 함수.

왜 필요한가 (플랜 2026-08-10, 실측 근거):
  1. 저자 파이프라인은 전부 **위치 인덱스**로 말하고(perspective·evaluate_fact),
     우리 스택은 전부 **fact_id**로 말한다(judge·ledger·access_window·뷰어).
     이 번역이 흩어지면 재추출 한 번에 대응이 조용히 끊긴다 — 번역을 이 파일에 가둔다.
     정본은 배열 순서가 아니라 **origin_index**다(fact_ids_in_order 가 양쪽 일치를 강제).
  2. 저자 축 판정물({round, agent_id, matched_fact_ids(인덱스)})에는 status 가 없어
     ledger.missing_facts 가 전 팩트를 소실로 오판한다(fact_id·status 두 필드 계약).
     author_rows_to_judgment 가 스키마 5(judgment)로 변환해 이 차단을 푼다.

소실 잣대는 modules.judge 의 far()·SURVIVING 을 재사용한다(단일 소스 —
judge 와 ledger 가 다른 잣대를 쓰면 측정이 무너진다, ledger.py 독스트링 계약).

사용(대표):
  facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
  jd = author_rows_to_judgment(rows, facts_doc, issue_id=..., run_id=..., prompt_ver=...)
  paths.judgment(issue_id, run_id).write_text(json.dumps(jd, ...), encoding="utf-8")
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from modules import judge as judge_mod  # noqa: E402 — far()·SURVIVING 재사용(잣대 단일 소스)

SCHEMA_VER = "0.3"
CREATED_BY = "paper_repro_bridge"


# ---------------------------------------------------------------------------
# 인덱스 ↔ fact_id 번역 (정본: origin_index)

def fact_ids_in_order(facts_doc: dict) -> list[str]:
    """origin_index 순 fact_id 목록. 배열 순서와 origin_index 가 어긋나면 즉시 에러.

    이 검사가 브리지의 토대다: 저자 위치 인덱스와 fact_id 의 대응은
    '배열 순서 == origin_index' 위에서만 성립한다(verify_bridge H1 과 같은 잣대).
    어긋난 파일을 조용히 번역하면 이후 모든 판정·장부가 틀린 팩트를 가리킨다."""
    issue_id = facts_doc.get("issue_id", "?")
    ids = []
    for i, f in enumerate(facts_doc["facts"]):
        oi = f.get("origin_index")
        if oi != i:
            raise ValueError(
                f"{issue_id}: facts[{i}].origin_index={oi} — 배열 순서와 불일치. "
                "브리지 번역 불가(H1). 산출 파일을 재생성하라.")
        ids.append(f["fact_id"])
    return ids


def to_fact_ids(facts_doc: dict, indices: list[int]) -> list[str]:
    """저자 위치 인덱스 목록 → fact_id 목록. 범위 밖 인덱스는 즉사(조용한 절단 금지)."""
    ids = fact_ids_in_order(facts_doc)
    out = []
    for i in indices:
        if not isinstance(i, int) or isinstance(i, bool) or i < 0 or i >= len(ids):
            raise ValueError(f"{facts_doc.get('issue_id', '?')}: 무효 인덱스 {i!r} (팩트 {len(ids)}개)")
        out.append(ids[i])
    return out


def to_positions(facts_doc: dict, fact_ids: list[str]) -> list[int]:
    """fact_id 목록 → 저자 위치 인덱스 목록. 미지 id 는 즉사."""
    ids = fact_ids_in_order(facts_doc)
    pos = {fid: i for i, fid in enumerate(ids)}
    out = []
    for fid in fact_ids:
        if fid not in pos:
            raise ValueError(f"{facts_doc.get('issue_id', '?')}: 미지 fact_id {fid!r}")
        out.append(pos[fid])
    return out


def author_fact_lines(facts_doc: dict) -> str:
    """저자 perspective.py 의 fact_text 조립을 위치 형식으로 재구성.

    저자 원문(perspective.py:20-22): `f"{index} {i_fact}: {r_fact}\\n"`,
    i_fact = '(Important)' | '(Not Important)'. critical 이 그 important 의 보존값이다."""
    fact_ids_in_order(facts_doc)  # H1 강제 — 어긋난 파일로 프롬프트를 만들지 않는다
    lines = ""
    for i, f in enumerate(facts_doc["facts"]):
        mark = "(Important)" if f.get("critical") else "(Not Important)"
        lines += f"{i} {mark}: {f['text']}\n"
    return lines


# ---------------------------------------------------------------------------
# 저자 evaluate_stance 산출 → 입장 이탈 요약 (계약 밖 보조 산출물 — manifests 전례)

def parse_stance(raw) -> str | None:
    """저자 evaluate_stance 응답("Answer (YES/NO only)") 파싱.

    저자는 원문 그대로 저장하고 파싱하지 않으므로 파싱 규칙은 우리 정의다:
    공백 제거·대문자화 후 YES/NO 접두 판정. 그 외는 None = parse_fail
    (axis_probe 의 3상태 원칙 — 조용한 0 금지). 원문 보존은 호출자 책임(규약 5)."""
    if not isinstance(raw, str):
        return None
    s = raw.strip().upper()
    if s.startswith("YES"):
        return "yes"
    if s.startswith("NO"):
        return "no"
    return None


def stance_rows_to_summary(rows: list[dict], assignment: dict, *,
                           issue_id: str, run_id: str) -> dict:
    """stance 체크포인트 행들 → 입장 이탈 요약.

    기대값은 배분 stance 의 엔진 매핑 그대로: pro→yes, con→no (debate_engine.py:486).
    지위: **관찰 계기** — §1 결과 변수(FAR)가 아니다. 결론 언어로 쓰려면 별도 사전 고정 필요.
    중복 (round, agent_id)는 나중 것이 이긴다(체크포인트 재개 의미론)."""
    expected_by_agent = {}
    for ag in assignment["agents"]:
        if ag["stance"] not in ("pro", "con"):
            raise ValueError(f"{issue_id}: 미지 stance {ag['stance']!r} ({ag['agent_id']})")
        expected_by_agent[ag["agent_id"]] = "yes" if ag["stance"] == "pro" else "no"

    dedup: dict[tuple, dict] = {}
    for r in rows:
        dedup[(r["round"], r["agent_id"])] = r

    per_utterance = []
    by_round: dict[int, list[bool]] = {}
    n_parse_fail = 0
    for (rnd, agent_id), r in sorted(dedup.items(), key=lambda kv: kv[0]):
        if agent_id not in expected_by_agent:
            raise ValueError(f"{issue_id}: 배분표에 없는 발화자 {agent_id!r}")
        judged = r.get("parsed", parse_stance(r.get("raw_response")))
        if judged is None:
            n_parse_fail += 1
        expected = expected_by_agent[agent_id]
        match = (judged == expected) if judged is not None else None
        per_utterance.append({"round": rnd, "agent_id": agent_id,
                              "expected": expected, "judged": judged, "match": match})
        if match is not None:
            by_round.setdefault(rnd, []).append(match)

    return {
        "schema_ver": SCHEMA_VER,
        "created_by": CREATED_BY,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "issue_id": issue_id,
        "run_id": run_id,
        "_note": ("입장 이탈 관찰 계기 — 지시된 입장(pro→yes/con→no) vs 발화가 실제 취한 "
                  "입장(저자 evaluate_stance). §1 결과 변수가 아니며 계약 파일 5종 밖의 "
                  "보조 산출물이다(manifests 전례)."),
        "per_utterance": per_utterance,
        "summary": {
            "match_rate_by_round": {
                str(rnd): round(sum(v) / len(v), 4) for rnd, v in sorted(by_round.items()) if v},
            "n_rows": len(dedup),
            "n_parse_fail": n_parse_fail,
        },
    }


# ---------------------------------------------------------------------------
# 저자 축 판정물 → judgment 스키마 5

def author_rows_to_judgment(rows: list[dict], facts_doc: dict, *,
                            issue_id: str, run_id: str, prompt_ver: str,
                            model: str = "gpt-5") -> dict:
    """axis_probe 형식 행들({round, agent_id, matched_fact_ids(인덱스)|None, parse, …})을
    judgment 스키마 5 로 변환한다.

    규칙 (judge_axis/axis_compare.py 의 저자 축 FAR 재구성 계승):
      status            = 그 round 의 어느 발화든 매치되면 mentioned, 아니면 unmentioned
      agents_mentioning = 해당 팩트를 매치한 발화의 agent_id (발화 순서 유지)
      parse_fail 행     = 매치 0 으로 세지 않고 judge_health.n_parse_fail 로 드러낸다
                          (조용한 0 금지 — axis_probe 의 3상태 구분과 같은 원칙)
    같은 (round, agent_id) 중복 행은 나중 것이 이긴다(체크포인트 재개 의미론).
    summary 는 modules.judge 산출과 같은 모양이며 far 계산은 judge.far() 재사용."""
    ids = fact_ids_in_order(facts_doc)
    facts_by_id = {f["fact_id"]: f for f in facts_doc["facts"]}

    dedup: dict[tuple, dict] = {}
    for r in rows:
        dedup[(r["round"], r["agent_id"])] = r
    n_parse_fail = 0
    by_stage: dict[int, list[dict]] = {}
    for (rnd, _), r in sorted(dedup.items(), key=lambda kv: kv[0]):
        by_stage.setdefault(rnd, []).append(r)
        if r.get("matched_fact_ids") is None:
            n_parse_fail += 1

    stages_out, far_by_stage = [], []
    for stage in sorted(by_stage):
        mentioned_by: dict[int, list[str]] = {}
        for r in by_stage[stage]:
            matched = r.get("matched_fact_ids")
            if matched is None:
                continue  # parse_fail — judge_health 로만 보고
            for i in matched:
                if not isinstance(i, int) or isinstance(i, bool) or i < 0 or i >= len(ids):
                    raise ValueError(
                        f"{issue_id}: r{stage} {r['agent_id']} 무효 매치 인덱스 {i!r}")
                mentioned_by.setdefault(i, []).append(r["agent_id"])
        recs = []
        for i, fid in enumerate(ids):
            agents = mentioned_by.get(i, [])
            status = "mentioned" if agents else "unmentioned"
            recs.append({
                "fact_id": fid,
                "status": status,
                # n=1 단일 판정 — 다수결이 아님을 votes 구조로도 드러낸다
                "votes": [{"status": status, "agents_mentioning": agents,
                           "reason": "author_axis evaluate_fact n=1"}],
                "agents_mentioning": agents,
            })
        stages_out.append({"stage": stage, "facts": recs})
        far_by_stage.append({
            "stage": stage,
            "far_system": judge_mod.far(recs, facts_by_id),
            "far_critical": judge_mod.far(recs, facts_by_id, critical_only=True),
        })

    last = far_by_stage[-1] if far_by_stage else {"far_system": None, "far_critical": None}
    return {
        "schema_ver": SCHEMA_VER,
        "created_by": CREATED_BY,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "issue_id": issue_id,
        "run_id": run_id,
        # 정본 judge(3표 다수결)와 산출물 수준에서 혼동 불가능하게 각인한다.
        # judge 사양 고정(CLAUDE.md)의 변경이 아니라 별도 축의 산출물이다(8/10 요한 "둘 다").
        "judge": {
            "model": model,
            "temperature": 0,
            "n_votes": 1,
            "aggregation": "author_axis_n1",
            "prompt_ver": prompt_ver,
        },
        "stage_type": "round",
        "stages": stages_out,
        "recall_probe": [],
        "summary": {
            "far_by_stage": far_by_stage,
            "far_system": last["far_system"],
            "far_agent_mean": None,
            "far_critical": last["far_critical"],
            "judge_health": {
                "n_rows": len(dedup),
                "n_parse_fail": n_parse_fail,
                "n_calls": len(dedup),  # 저자 축은 발화당 1콜
            },
        },
    }
