"""[민옥 · 관측 레이어 트랙] 뷰모델 — 파이프라인 산출물 → 화면용 데이터 변환 (순수 함수).

역할: debate.jsonl + judgment.json + facts.json 을 "화면이 필요로 하는 형태"로 바꾼다.
이 변환이 관측 레이어의 **계약**이다 — 정적 HTML 생성기(scripts/make_viewer.py)든
서버(FastAPI 등)든, 어떤 어댑터가 와도 이 뷰모델을 소비한다. loader = 소스 어댑터,
본체 = 공용 원칙의 시각화 판.

원칙(보드 7/22 설계 제안): 읽기 전용 소비자 — 스키마 불변, 어떤 파일도 수정하지 않는다.
judgment 의존은 fact_id·status 중심(votes 등 부가 필드는 있으면 싣고 없으면 생략 —
P2·ledger 와 같은 관용성). LLM 호출 0, 파일 쓰기 0.
"""
from __future__ import annotations

import json

from . import paths
from .judge import SURVIVING

# 화면 상태 어휘: 스키마 5종 + absent(레코드 부재 — survival 관례와 동일).
STATUS_ORDER = ("accepted", "mentioned", "unmentioned", "ignored", "refuted", "absent")


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_events(issue_id: str, run_id: str) -> list[dict]:
    out = []
    for line in paths.debate(issue_id, run_id).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def build_viewmodel(issue_id: str, run_id: str) -> dict:
    """이슈·런 하나의 전체 뷰모델(dict, JSON 직렬화 가능)을 만든다."""
    issue_doc = _load_json(paths.issue(issue_id))
    facts_doc = _load_json(paths.facts(issue_id))
    judgment = _load_json(paths.judgment(issue_id, run_id))
    events = _load_events(issue_id, run_id)

    facts = [{
        "fact_id": f["fact_id"],
        "text": f["text"],
        "tags": f.get("tags", []),
        "critical": bool(f.get("critical")),
    } for f in facts_doc["facts"]]
    fact_ids = [f["fact_id"] for f in facts]

    stages = sorted(judgment.get("stages", []), key=lambda s: s.get("stage"))
    stage_nos = [s.get("stage") for s in stages]

    # 매트릭스: fact_id → {stage: cell}. 레코드 부재 = absent (P2 결정 2와 동일 관례).
    matrix: dict[str, dict] = {fid: {} for fid in fact_ids}
    for st in stages:
        by_id = {f["fact_id"]: f for f in st.get("facts", [])}
        for fid in fact_ids:
            rec = by_id.get(fid)
            if rec is None:
                cell = {"status": "absent", "surviving": False}
            else:
                cell = {
                    "status": rec.get("status"),
                    "surviving": rec.get("status") in SURVIVING,
                    "agents": rec.get("agents_mentioning", []),
                }
                votes = rec.get("votes")
                if isinstance(votes, list) and votes:
                    # 구버전 votes 구조([{agent_id, votes:[bool]}])에는 status 가 없다 —
                    # 있는 것만 싣는다(P2·ledger 와 같은 관용성).
                    vs = [v.get("status") for v in votes
                          if isinstance(v, dict) and v.get("status")]
                    if vs:
                        cell["votes"] = vs
                        cell["vote_split"] = len(set(vs)) > 1  # 표 불일치 = judge 흔들림 표시
            matrix[fid][str(st.get("stage"))] = cell

    # 발화: stage 별 원문 전량 (요약 금지).
    utterances: dict[str, list] = {str(n): [] for n in stage_nos}
    for e in events:
        if e.get("event") == "utterance":
            key = str(e.get("round"))
            utterances.setdefault(key, []).append({
                "agent_id": e.get("agent_id"),
                "stance": e.get("stance"),
                "perspective": e.get("perspective"),
                "text": e.get("response_text", ""),
            })

    # 재주입 지점 (ledger_inject).
    injects = [{"round": e.get("round"), "fact_ids": e.get("injected_fact_ids", [])}
               for e in events if e.get("event") == "ledger_inject"]

    # 태그 어휘 (필터 버튼용 — 데이터에 실제 있는 것만).
    tag_vocab = sorted({t for f in facts for t in f["tags"]})

    ledger_mode = next((e.get("ledger_mode") for e in events
                        if e.get("event") == "utterance"), "off")

    return {
        "meta": {
            "issue_id": issue_id,
            "run_id": run_id,
            "title": issue_doc.get("title", issue_id),
            "stage_type": judgment.get("stage_type"),
            "ledger_mode": ledger_mode,
            "judge": judgment.get("judge", {}),
            "n_facts": len(facts),
            "n_critical": sum(1 for f in facts if f["critical"]),
            "created_at": judgment.get("created_at"),
        },
        "stages": stage_nos,
        "facts": facts,
        "matrix": matrix,
        "utterances": utterances,
        "injects": injects,
        "tag_vocab": tag_vocab,
        "far_by_stage": judgment.get("summary", {}).get("far_by_stage", []),
        "status_order": list(STATUS_ORDER),
    }
