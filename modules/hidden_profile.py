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

# ─────────────────────────────────────────────────────────────────────────────
# OUTCOME_PARSE_VER — 폴링 원문에서 선택지를 꺼내는 규칙의 버전.
# note_slot.NOTE_PARSE_VER 과 같은 자리·같은 이유다: 규칙을 한 글자라도 바꾸면 과거
# run 의 수치가 조용히 달라지므로, 바꿀 때 이 상수를 올리고 산출물에 실어 보낸다.
#
# v1 (암묵) : json.loads(원문) 이 dict 이고 recommend 가 str 이면 그 값. 그 외 파싱 실패.
# v2 (2026-08-14 고정):
#   R1. v1 규칙 그대로.
#   R2. 실패 시 원문에서 첫 '{' 부터 마지막 '}' 까지를 잘라 json.loads 재시도.
#       모델이 JSON 을 ```json 펜스나 산문으로 감싸는 흔한 실패 모드를 위한 것이며,
#       note_slot 의 R2 와 같은 규칙이다.
#   R3. 그래도 실패하면 parse_ok=False — 제3상태다. 자연어에서 후보 이름을 찾지
#       않는다(계약 §5-6: 정답도 선택지도 추론하지 않는다). R2 는 **JSON 을 찾는**
#       규칙이지 의미를 읽는 규칙이 아니다.
#
# v2 로 올린 계기(정직하게 남긴다): 단독 기준선 팔 20단위 중 6단위가 v1 에서 파싱
# 실패로 떨어졌고, 원문을 읽어보니 전부 ```json 펜스에 싸인 정상 JSON 이었다. 즉
# **결과를 본 뒤의 규칙 변경**이다. 복구된 6건의 방향은 한도영 4 · 유지완 2 로 정답
# 쪽으로 기울지 않는다(수치를 유리하게 만드는 변경이 아님을 함께 기록한다).
OUTCOME_PARSE_VER = "hp_outcome_v2"


def _events_of(events: list[dict], kind: str) -> list[dict]:
    return [e for e in events if e.get("event") == kind]


def _recommend_of(raw) -> str | None:
    """폴링 원문 → recommend 문자열. 규칙은 OUTCOME_PARSE_VER 주석이 정본."""
    if not isinstance(raw, str):
        return None
    candidates = [raw]
    i, j = raw.find("{"), raw.rfind("}")
    if i >= 0 and j > i and raw[i:j + 1] != raw:
        candidates.append(raw[i:j + 1])
    for text in candidates:
        try:
            obj = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(obj, dict) and isinstance(obj.get("recommend"), str):
            return obj["recommend"]
    return None


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
        recommend = _recommend_of(raw)
        parse_ok = recommend is not None
        picks.append({
            "agent_id": e.get("agent_id"),
            "round": e.get("round"),
            "recommend": recommend,
            "correct": (recommend == answer) if parse_ok else None,
            "parse_ok": parse_ok,
        })
    return {
        "answer": answer,
        "parse_ver": OUTCOME_PARSE_VER,   # 어느 규칙으로 읽었는지 산출물이 들고 다닌다
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


def lineage(events: list[dict], assignment: dict, facts_doc: dict, fact_id: str) -> dict:
    """팩트 1개의 원형이 통과했을 수 있는 경로 전체를 시간순 좌표에 나란히 놓는다(§3-5).

    판정 0 — 변형 여부·정도·방향을 계기가 말하지 않는다. 보유자 특정은 배분표
    설계값이라 판정이 아니다. 비보유자 발화는 싣지 않는다(§3-5 — 전달 여부는
    등장 좌표가 라벨된 뒤의 질문). inputs_ref 는 참조다 — 전문 재조립은
    화면·validate --deep 몫(조립 코드 단일 소스 원칙)."""
    fact = next((f for f in facts_doc["facts"] if f["fact_id"] == fact_id), None)
    if fact is None:
        raise ValueError(f"미지 fact_id {fact_id!r} — facts_doc 에 없음")
    holders = [ag["agent_id"] for ag in assignment["agents"]
               if fact_id in ag.get("assigned_fact_ids", [])]
    holder_set = set(holders)

    def _key(e):
        return (e.get("round", -1), e.get("agent_id", ""))

    utterances = [{"round": e.get("round"), "agent_id": e.get("agent_id"),
                   "response_text": e.get("response_text", "")}  # 원문 전량
                  for e in sorted(_events_of(events, "utterance"), key=_key)
                  if e.get("agent_id") in holder_set]
    notes = [{"round": e.get("round"), "agent_id": e.get("agent_id"),
              "source": e.get("source"), "note_text": e.get("note_text", ""),
              "n_chars": len(e.get("note_text", ""))}
             for e in sorted(_events_of(events, "note_update"), key=_key)
             if e.get("agent_id") in holder_set]
    inputs_ref = [{"round": e.get("round"), "agent_id": e.get("agent_id"),
                   "prompt_hash": e.get("prompt_hash"), "slots": e.get("slots")}
                  for e in sorted(_events_of(events, "prompt_assembly"), key=_key)
                  if e.get("agent_id") in holder_set]
    return {
        "fact": {"fact_id": fact_id, "text": fact.get("text"),
                 "share": fact.get("share"), "favors": fact.get("favors"),
                 "requirement": fact.get("requirement"), "apparent": fact.get("apparent")},
        "holders": holders,
        "utterances": utterances,
        "notes": notes,
        "inputs_ref": inputs_ref,
    }


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
