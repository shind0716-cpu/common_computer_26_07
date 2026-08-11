# -*- coding: utf-8 -*-
"""[관측 노드 · 요한] 히든 프로필 노드 — 정답 대조 + 수첩 판본 (계약 정본: docs/proposals/HIDDEN_PROFILE_NODE.md)

순수 함수만. 파일 쓰기 0 · LLM 0 · 판정 0. 기존 계기 관례(survival·crossrun) 계승.

절대 금지 (계약 §5 — 구현 지시서 맨 앞 복사 의무):
1. 새 비율·점수를 정의하지 마라. 정답은 개수로 낸다(n_correct/n_agents 를 계기가
   나눠서 내지 않는다). 비율은 조건 의존인데 화면은 조건 비의존처럼 싣는다.
2. 수첩·발화에서 팩트를 자동 추출하지 마라. 문자열 대조는 어휘 치환만으로 붕괴한다
   (NOTE_SLOT §4, H2 실측 0.641). 근접도도 안 된다 — 시선 유도로도 쓰지 않는다.
3. 줄어든 것을 "손실"이라 부르지 마라. 계기는 n_chars 와 판본 원문만 낸다.
   "버렸다 / 필요 없어 뺐다"의 구분은 requirement·favors 를 나란히 보고 사람이 정한다.
4. 임계값을 만들지 마라. "등장 1회 이하 = 취합 실패" 같은 선을 긋지 않는다.
5. 분모를 먼저 그려라. 기본은 미공유 팩트 전량이다(등장 0회도 행을 차지한다).
6. 정답을 자연어에서 파싱하지 마라. 정답은 호출자가 인자로 준다.

부호 주의(계약 §1): 이 트랙에서 압축은 실패가 아니라 해야 하는 일이다. 생존 트랙의
문면("줄어든 것 = 손실")을 이 노드의 출력에 섞지 않는다.
"""
from __future__ import annotations

import json


def _events_of(events: list[dict], kind: str) -> list[dict]:
    return [e for e in events if e.get("event") == kind]


def outcome(events: list[dict], *, answer: str) -> dict:
    """final_poll 이벤트를 좌표로 옮긴다. 판정 없음 — response_text 의 JSON 을 그대로 읽는다.

    answer 는 호출자가 준다(§5-6 — 계기가 issue._note 자연어에서 추론하지 않는다).
    parse_ok=False 는 정답도 오답도 아닌 제3의 값이다(correct=None) — 오답으로 세면
    파싱 실패율이 정답률에 조용히 섞인다(계약 §3-1·§6)."""
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("answer 는 비어 있지 않은 문자열이어야 한다 — 호출자 책임(§5-6)")
    picks = []
    for e in _events_of(events, "final_poll"):
        raw = e.get("response_text", "")
        recommend = None
        parse_ok = False
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and isinstance(obj.get("recommend"), str):
                recommend = obj["recommend"]
                parse_ok = True
        except (json.JSONDecodeError, TypeError):
            pass
        picks.append({
            "agent_id": e.get("agent_id"),
            "round": e.get("round"),
            "recommend": recommend,
            "correct": (recommend == answer) if parse_ok else None,
            "parse_ok": parse_ok,
        })
    return {
        "answer": answer,
        "picks": picks,
        "n_agents": len({p["agent_id"] for p in picks}),
        "n_correct": sum(1 for p in picks if p["correct"] is True),
    }


def fact_trace(events: list[dict], assignment: dict, facts_doc: dict, *,
               coords_by_fact: dict | None = None) -> list[dict]:
    """미공유 팩트마다 보유자·등장 좌표를 놓는다. 설계값(share·favors·requirement·apparent)은
    그대로 통과 — 계기가 가공하지 않는다.

    등장 좌표는 계기가 만들지 않는다(§3-4 — "이 팩트가 이 발화에 나왔나"는 판정이다).
    coords_by_fact 는 호출자 책임(사람 라벨 1급, judge 출력이면 판정 매개 표기는 화면 몫):
      * None(기본)          → 각 팩트의 utterance_coords = None (좌표 미공급 = 모름)
      * {fact_id: [...]}    → 그대로 싣는다. 빈 배열은 "라벨됐고 등장 0회"라는 뜻이다 —
                              None(모름)과 다르다(부재≠0, §4⁗ 원칙).
    events 는 좌표 정합 검사에만 쓴다: 배분표의 보유자가 seating 에 없으면 즉사."""
    seating = _events_of(events, "seating")
    seated = None
    if seating:
        order = seating[0].get("order") or seating[0].get("agents")
        if isinstance(order, list):
            seated = {a if isinstance(a, str) else a.get("agent_id") for a in order}
    rows = []
    for f in facts_doc["facts"]:
        if f.get("share") != "unshared":
            continue
        fid = f["fact_id"]
        holders = [ag["agent_id"] for ag in assignment["agents"]
                   if fid in ag.get("assigned_fact_ids", [])]
        if seated is not None:
            missing = [h for h in holders if h not in seated]
            if missing:
                raise ValueError(f"{fid}: 보유자 {missing} 가 seating 에 없음 — 배분표와 "
                                 "debate 가 다른 판이다(좌표 정합 위반)")
        coords = None
        if coords_by_fact is not None:
            coords = coords_by_fact.get(fid)
        rows.append({
            "fact_id": fid,
            "share": f.get("share"),
            "favors": f.get("favors"),
            "requirement": f.get("requirement"),
            "apparent": f.get("apparent"),
            "holders": holders,
            "utterance_coords": coords,
        })
    return rows


def note_trace(events: list[dict]) -> list[dict]:
    """에이전트별 수첩 판본을 원문 그대로 좌표에 건다. n_chars 는 길이만 —
    "얼마나 줄었나"는 화면(사람) 몫이다(§5-3)."""
    rows = []
    for e in _events_of(events, "note_update"):
        text = e.get("note_text", "")
        rows.append({
            "agent_id": e.get("agent_id"),
            "round": e.get("round"),
            "source": e.get("source"),
            "note_text": text,   # 원문 전량. 요약·발췌 금지
            "n_chars": len(text),
        })
    return rows
