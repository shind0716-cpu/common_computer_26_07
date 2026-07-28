"""[요한 · P3 부속] 접근 창 계기 — 팩트 물리 상태 원장(발화/침묵·접근/접근 불가) (순수 계산).

설계 맥락: docs/P3_TRANSMISSION_DESIGN.md §2-0 "관측된 정보 생태" — 이 엔진의 에이전트는
매 라운드 (question + 직전 발화 창 + inject)만 들고 다시 만들어지므로, 라운드를 넘는 숨은
내부 기억이 구조적으로 없다. 따라서 "발화 밖에서 팩트가 남아있는가"는 심리량이 아니라
**컨텍스트 조립에 물리적으로 존재하는가**로 전량 관측 가능하다. 이 모듈은 그 관측 창이다.
지위: **서술 계기** — 사전고정 판별표(§6) 판정 밖(가설 검정 아님·지표 정본 아님). 브랜치
시제품(§F "브랜치는 자유"), P3 팀 확정은 동기화 대기.

무엇: 라운드(stage)마다 각 팩트를 셋 중 하나로 판정한 **팩트 상태 원장**을 만든다.
  spoken        — 그 라운드에 누군가 발화했다(agents_mentioning 비어있지 않음).
  accessible    — 발화되지 않았으나 ≥1 에이전트의 입력(창)에 물리적으로 존재한다.
                  (에세이 어휘 "은퇴"의 조작화 — 침묵하되 복귀 가능)
  inaccessible  — 어떤 에이전트의 입력에도 없다. (에세이 어휘 "사망"의 조작화 —
                  ledger/사전지식 밖에는 복귀 경로 없음)
원장 레코드는 원문을 복사하지 않고 좌표(round·agent_id)로만 가리킨다(원문 보존 원칙).

접근 정의 — (에이전트 a, 팩트 f, 위치 idx):
  창 원천 1순위 = **prompt_assembly 이벤트**(스키마 v0.3): slots의 previous/others 좌표가
  가리키는 발화의 언급(agents_mentioning) + assigned_fact_ids + inject 슬롯.
  부재 시(구 로그) = **롤링 창 재구성**(§2-0 확정 구조): idx=0 은 자기 할당 팩트,
  idx≥1 은 (자기 ∪ edges 이웃)의 직전 stage 언급 ∨ 해당 round 의 ledger_inject.
  어느 원천을 썼는지 meta.window_source 에 기록한다(v0.3 경계 조항의 "구 로그 유효" 계승).

파생 사건(전이):
  resurgence  — 접근 없이 발화됨(사전지식/작화 채널; 층1 prior_suspect 의 상태 원장 대응물).
                round 0 비보유 발화도 정의상 여기 잡힌다.
  ledger_lifeline — 발화 사슬이 끊긴 뒤 inject 로만 접근이 유지·복원된 라운드.
  retirement episode — spoken 연속 구간이 끝난 직후의 침묵 구간과 그 결말
                (dead / ledger_lifeline / resurgence / censored). 롤링 창(w=1)에서는
                은퇴 유예가 정확히 1라운드임이 기계적 귀결 — 이 원장은 그것을 가정하지
                않고 **측정**한다(창 구조가 바뀌어도 정의 불변).

집계 뷰(전부 원장의 함수): 라운드별 상태 곡선(발화 생존 vs 접근 생존), 팩트별 최초
inaccessible 진입, 은퇴 결말 분포, 최종 상태 분포. question 상시 노출 팩트는
question_exposed_ids 로 주입받아 excluded=True 표기(transmission.py 영점 조정 관례).

해석 한정(문서 append 7/28 준수): 이 계기는 "시스템 안 어디에 있는가"만 잰다.
inaccessible 은 **판단 활용 실패의 증명이 아니고**, accessible 은 활용의 증명이 아니다 —
기능적 사용은 사용 관문(결정 과제) 소관.

의존 계약(전부 읽기): judgment stages[].facts[].agents_mentioning · assignment
agents[].assigned_fact_ids · debate 이벤트 seating/ledger_inject(+v0.3 prompt_assembly, soft)
· facts prior/critical(soft). 적용 범위: 실험 트랙(stage 정렬 위치 인덱스 사용).

사용(단독):
  python -m modules.access_window --issue issue_esa --run dryrun2 [--critical-only]
    → 상태 곡선·팩트별 타임라인·은퇴 결말을 콘솔에 출력(파일 안 씀, 점검용).
"""
from __future__ import annotations

import argparse
import json

from . import ledger, paths
from .transmission import (PROTOCOL, edges_map, holders_map, inject_map,
                           load_assignment, load_debate_events, mention_map,
                           prior_band)

STATES = ("spoken", "accessible", "inaccessible")


# ---------------------------------------------------------------------------
# 창 원천 — 접근 집합 {idx: {agent_id: set(fact_id)}}
# ---------------------------------------------------------------------------
def _mentioned_by(mentions_at: dict, agent: str) -> set[str]:
    """한 stage 의 {fact_id: set(agents)} 에서 agent 가 언급한 팩트 집합."""
    return {fid for fid, ags in mentions_at.items() if agent in ags}


def access_sets(
    rounds: list,
    mentions: dict,
    assignment: dict,
    events: list[dict] | None,
) -> tuple[dict, dict]:
    """{idx: {agent_id: 접근 가능 팩트 집합}} + meta(window_source·보정 기록).

    prompt_assembly 이벤트가 있으면 그 (round, agent_id) 쌍은 실제 조립 기록으로 접근을
    계산하고, 없는 쌍은 롤링 창 재구성으로 채운다(혼재 시 meta 에 양쪽 카운트).
    """
    agents, _holders = holders_map(assignment)
    assigned = {ag["agent_id"]: set(ag.get("assigned_fact_ids", []))
                for ag in assignment.get("agents", [])}
    edges, edge_meta = edges_map(events, agents)
    injects = inject_map(events)

    pa: dict[tuple, dict] = {}
    for ev in events or []:
        if ev.get("event") == "prompt_assembly":
            pa[(ev.get("round"), ev.get("agent_id"))] = ev

    acc: dict = {}
    n_from_pa = 0
    n_reconstructed = 0
    for idx, r in enumerate(rounds):
        per_agent: dict[str, set[str]] = {}
        inj_facts = injects.get(r, set())
        for a in agents:
            ev = pa.get((r, a))
            if ev is not None:
                n_from_pa += 1
                slots = ev.get("slots") or {}
                facts: set[str] = set(slots.get("assigned_fact_ids") or [])
                coords = list(slots.get("others") or [])
                prev = slots.get("previous")
                if prev:
                    coords.append(prev)
                for c in coords:
                    facts |= _mentioned_by(mentions.get(c.get("round"), {}),
                                           c.get("agent_id"))
                if slots.get("inject"):
                    facts |= inj_facts
                per_agent[a] = facts
            else:
                n_reconstructed += 1
                if idx == 0:
                    per_agent[a] = set(assigned.get(a, set())) | inj_facts
                else:
                    prev_r = rounds[idx - 1]
                    facts = set(inj_facts)
                    for j in edges.get(a, set()) | {a}:
                        facts |= _mentioned_by(mentions.get(prev_r, {}), j)
                    per_agent[a] = facts
        acc[idx] = per_agent

    source = ("prompt_assembly" if n_reconstructed == 0 and n_from_pa > 0
              else "reconstructed" if n_from_pa == 0 else "mixed")
    meta = {"window_source": source, "n_from_assembly": n_from_pa,
            "n_reconstructed": n_reconstructed, "edges": edge_meta}
    return acc, meta


# ---------------------------------------------------------------------------
# 사건 원장 (1급 산출물)
# ---------------------------------------------------------------------------
def fact_records(
    judgment: dict,
    assignment: dict,
    events: list[dict] | None = None,
    *,
    facts_by_id: dict[str, dict] | None = None,
    question_exposed_ids: frozenset | set = frozenset(),
) -> tuple[list[dict], dict]:
    """팩트별 상태 타임라인 원장. 반환 (records, meta).

    레코드: fact_id·excluded·prior_band·critical·timeline[]·최초 inaccessible 진입·
    부활(revivals)·은퇴 에피소드(retirements)·최종 상태·상태별 라운드 수.
    timeline 행: {round, state, spoken_by[], n_access_agents, inject(bool),
                  resurgent_speakers[]} — 전부 좌표, 원문 복사 없음.
    """
    rounds, mentions = mention_map(judgment)
    agents, holders = holders_map(assignment)
    injects = inject_map(events)
    acc, acc_meta = access_sets(rounds, mentions, assignment, events)
    run_id = judgment.get("run_id")
    n = len(rounds)

    fact_ids: list[str] = []
    seen: set[str] = set()
    for r in rounds:
        for fid in mentions[r]:
            if fid not in seen:
                seen.add(fid)
                fact_ids.append(fid)
    assigned_untracked = sorted(set(holders) - seen)  # 배분됐으나 judgment 스냅샷 밖(경고용)

    records: list[dict] = []
    for fid in fact_ids:
        fact = (facts_by_id or {}).get(fid)
        timeline: list[dict] = []
        states: list[str] = []
        for idx in range(n):
            r = rounds[idx]
            spoken_by = sorted(mentions[r].get(fid, set()))
            access_agents = [a for a in agents if fid in acc[idx].get(a, set())]
            if spoken_by:
                state = "spoken"
            elif access_agents:
                state = "accessible"
            else:
                state = "inaccessible"
            states.append(state)
            timeline.append({
                "round": r, "state": state, "spoken_by": spoken_by,
                "n_access_agents": len(access_agents),
                "inject": fid in injects.get(r, set()),
                "resurgent_speakers": sorted(set(spoken_by) - set(access_agents)),
            })

        # 부활: inaccessible → (spoken|accessible) 전이. 채널 = inject 면 ledger, 아니면
        # 발화 자체가 접근 없이 나온 것(resurgence).
        revivals = []
        for idx in range(1, n):
            if states[idx - 1] == "inaccessible" and states[idx] != "inaccessible":
                revivals.append({
                    "round": rounds[idx], "to_state": states[idx],
                    "channel": "ledger" if timeline[idx]["inject"] else "resurgence",
                })

        # 은퇴 에피소드: spoken 연속 구간의 끝 다음 위치 s 부터의 침묵 구간과 결말.
        retirements = []
        for idx in range(n - 1):
            if states[idx] != "spoken" or states[idx + 1] == "spoken":
                continue
            s = idx + 1
            epi = {"after_round": rounds[idx], "grace_state": states[s],
                   "outcome": None, "outcome_round": None}
            if s + 1 >= n:
                epi["outcome"] = "censored"
            else:
                nxt = states[s + 1]
                if nxt == "inaccessible":
                    epi["outcome"] = "dead"
                elif nxt == "spoken" and timeline[s + 1]["resurgent_speakers"]:
                    epi["outcome"] = "resurgence"
                elif timeline[s + 1]["inject"]:
                    epi["outcome"] = "ledger_lifeline"
                else:
                    epi["outcome"] = "carried"   # 창 구조상 조직적 접근이 살아있는 경우
                epi["outcome_round"] = rounds[s + 1]
            retirements.append(epi)

        first_dead = next((rounds[i] for i in range(n)
                           if states[i] == "inaccessible"), None)
        records.append({
            "run_id": run_id, "fact_id": fid,
            "excluded": fid in question_exposed_ids,
            "prior_band": prior_band(fact),
            "critical": bool((fact or {}).get("critical")) if fact is not None else None,
            "timeline": timeline,
            "first_inaccessible_round": first_dead,
            "revivals": revivals,
            "retirements": retirements,
            "final_state": states[-1] if states else None,
            "rounds_by_state": {st: states.count(st) for st in STATES},
            "n_resurgent_rounds": sum(1 for t in timeline if t["resurgent_speakers"]),
        })

    meta = {"protocol": PROTOCOL, "run_id": run_id, "rounds": rounds,
            "n_agents": len(agents), "n_facts": len(fact_ids),
            "window": acc_meta,
            "assigned_untracked_facts": assigned_untracked,
            "question_excluded_facts": sorted(f for f in fact_ids
                                              if f in question_exposed_ids)}
    return records, meta


# ---------------------------------------------------------------------------
# 집계 뷰 (전부 원장의 함수)
# ---------------------------------------------------------------------------
def _tracked(records: list[dict], *, critical_only: bool = False) -> list[dict]:
    out = [r for r in records if not r["excluded"]]
    if critical_only:
        out = [r for r in out if r["critical"]]
    return out


def state_curve(records: list[dict], rounds: list, *,
                critical_only: bool = False) -> list[dict]:
    """라운드별 상태 분포 — 발화 생존 곡선과 접근 생존 곡선을 한 표로.
    alive_spoken = spoken 수, alive_access = spoken+accessible 수(접근 기준 생존)."""
    tracked = _tracked(records, critical_only=critical_only)
    curve = []
    for idx, r in enumerate(rounds):
        counts = {st: 0 for st in STATES}
        for rec in tracked:
            counts[rec["timeline"][idx]["state"]] += 1
        curve.append({"round": r, **counts,
                      "alive_spoken": counts["spoken"],
                      "alive_access": counts["spoken"] + counts["accessible"]})
    return curve


def summary(records: list[dict], *, critical_only: bool = False) -> dict:
    """최종 상태·최초 사망 진입·은퇴 결말·부활 채널의 시스템 요약."""
    tracked = _tracked(records, critical_only=critical_only)
    outcomes: dict[str, int] = {}
    for rec in tracked:
        for epi in rec["retirements"]:
            outcomes[epi["outcome"]] = outcomes.get(epi["outcome"], 0) + 1
    revival_ch: dict[str, int] = {}
    for rec in tracked:
        for rv in rec["revivals"]:
            revival_ch[rv["channel"]] = revival_ch.get(rv["channel"], 0) + 1
    return {
        "scope": {"critical_only": critical_only},
        "n_facts_tracked": len(tracked),
        "n_facts_excluded_question": sum(1 for r in records if r["excluded"]),
        "final_state": {st: sum(1 for r in tracked if r["final_state"] == st)
                        for st in STATES},
        "n_ever_inaccessible": sum(1 for r in tracked
                                   if r["first_inaccessible_round"] is not None),
        "retirement_outcomes": outcomes,
        "revival_channels": revival_ch,
        "n_facts_with_resurgence": sum(1 for r in tracked
                                       if r["n_resurgent_rounds"] > 0),
    }


def report(
    judgment: dict,
    assignment: dict,
    events: list[dict] | None,
    facts_by_id: dict[str, dict] | None = None,
    *,
    question_exposed_ids: frozenset | set = frozenset(),
    critical_only: bool = False,
) -> dict:
    """사건 원장 + 집계 뷰 일괄 구조. 원장이 정본, 나머지는 전부 뷰."""
    records, meta = fact_records(judgment, assignment, events,
                                 facts_by_id=facts_by_id,
                                 question_exposed_ids=question_exposed_ids)
    return {
        "protocol": PROTOCOL,
        "instrument": "access_window (서술 계기 — 판별표 밖)",
        "meta": meta,
        "records": records,
        "curve": state_curve(records, meta["rounds"], critical_only=critical_only),
        "summary": summary(records, critical_only=critical_only),
    }


# ---------------------------------------------------------------------------
# CLI (점검용 — 파일을 쓰지 않는다)
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="P3 접근 창 계기 — 팩트 상태 원장(발화/접근/접근 불가) 점검")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--critical-only", action="store_true")
    args = ap.parse_args()

    judgment = ledger.load_judgment(args.issue, args.run)
    assignment = load_assignment(args.issue)
    events = load_debate_events(args.issue, args.run)
    facts_by_id = ledger.load_facts_by_id(args.issue)
    rep = report(judgment, assignment, events, facts_by_id,
                 critical_only=args.critical_only)

    m, s = rep["meta"], rep["summary"]
    print(f"[access_window] issue={args.issue} run={args.run}")
    print(f"[access_window] {PROTOCOL} · 창 원천={m['window']['window_source']}")
    print(f"[access_window] rounds={m['rounds']} agents={m['n_agents']} "
          f"facts={m['n_facts']} edges={m['window']['edges']}")
    print("[access_window] 상태 곡선 (spoken / accessible / inaccessible · 접근 생존):")
    for row in rep["curve"]:
        print(f"  round {row['round']}: {row['spoken']} / {row['accessible']} / "
              f"{row['inaccessible']} · alive_access={row['alive_access']}")
    print("[access_window] 팩트별 타임라인 (S=발화 A=접근 D=불가 · *=resurgence):")
    for rec in rep["records"]:
        line = "".join(("S" if t["state"] == "spoken" else
                        "A" if t["state"] == "accessible" else "D")
                       + ("*" if t["resurgent_speakers"] else "")
                       for t in rec["timeline"])
        flag = " [제외:question]" if rec["excluded"] else ""
        dead = rec["first_inaccessible_round"]
        print(f"  {rec['fact_id']}: {line} · 최초 D={dead} · 최종={rec['final_state']}"
              f"{flag}")
    print(f"[access_window] 요약: 최종={s['final_state']} · "
          f"사망 경험={s['n_ever_inaccessible']}/{s['n_facts_tracked']} · "
          f"은퇴 결말={s['retirement_outcomes']} · 부활={s['revival_channels']} · "
          f"resurgence 팩트={s['n_facts_with_resurgence']}")


if __name__ == "__main__":
    main()
