"""[요한 · P3 층 1] 전달-발화 레이더 — (a,f) 사건 원장 + 집계 뷰 (G2, 순수 계산).

설계 정본: docs/P3_TRANSMISSION_DESIGN.md v1.0 (사전고정 커밋 a70470d). 이 모듈은 그 §2-0·§3의
구현이며, 문서와 코드가 어긋나면 문서가 정본이다. 판별표(§6) 판정은 이 모듈 밖(분석 보고서 몫).

지위 (2026-07-29 갱신 — 동기화 구두 확정분 반영):
  층1 자체는 **팀 확정**이다(종전 "제안·동결" 표기 해제).
  다만 같은 날 결정으로 **용도가 한정**됐다 — 이 지표들(B·TSR·획득 hazard)은 **본실험 주지표
  후보에서 내려가고, 논문 재현(협의 과제) 쪽에서 쓴다.** 사유: 이 층의 노출·언급이 전부 judge
  출력을 거치는데 7/29 계기 점검에서 그 판정이 경계면에서 불안정함이 확인됐다(요지압축 검출
  41.7%·재판정 5:0 뒤집힘). 본실험의 과정 관측은 개인 수첩 원문(판정 무경유)이 맡는다.
  근거 기록: 팀 메모리 3ac0261412b081c0a777cbfdd6706052 · WORKLOG 2026-07-29.

무엇: 정보 비대칭 토론에서 "원래 모르던(비할당) 에이전트가 팩트를 받아 말했는가"를 로그
전수로 잰다. 순수 함수만 제공 — 추가 LLM 호출 0 · 읽기 전용 · 파일 안 씀(survival.py 관례).
1급 산출물은 지표가 아니라 **사건 원장(pair_records)** — B·TSR·생명표는 전부 그 집계 뷰다.
원장 레코드는 원문을 복사하지 않고 좌표(round·agent_id)로만 가리킨다(원문 보존 원칙).

핵심 정의(v1.0):
  롤링 창(§2-0): round r 입력 = 자기·이웃(edges)의 직전 발화 + inject 블록. 누적 대화록 없음.
  노출(§3-2):  X(a,f,r) = [∃ j∈edges(a): j가 stage r−1 에 f 언급(agents_mentioning)]
               ∨ [round r 의 ledger_inject 에 f 포함].
  전달 사건:   노출 선행 첫 언급(e ≤ τ). 노출 전 언급 = prior_suspect(전달 아님, 분리 집계 —
               round 0 비보유 언급은 정의상 전부 prior_suspect).
  엄격 정본:   u = τ−e ≥ 1. u=0(노출 당회 즉답)은 창 안 반향 가능성 — u0_immediate 로 분리,
               u=0 포함 집계는 상한(upper) 민감도로 병기.
  분모:        TSR = B / |N_exp| — 노출된 비보유자만. 비노출 쌍 = never_exposed 별도 카운트.
  경로(§3-4):  첫 노출 라운드의 채널 organic / ledger / mixed.
  영점 조정:   question 상시 노출 팩트는 추적자 정본에서 제외 — question 스캔은 judge(LLM)
               사안이라 이 모듈 밖이며, question_exposed_ids 인자로 주입받는다(기본 빈 집합).

의존 계약(전부 현행 v0.2 — v1.0 §3-1):
  judgment   stages[].{stage, facts[].{fact_id, status, agents_mentioning}}  (P2 대비 +1필드)
  assignment agents[].{agent_id, assigned_fact_ids}
  debate     seating{structure, order} · ledger_inject{round, injected_fact_ids}  (soft —
             seating 없으면 full 가정으로 동작하고 그 가정을 meta 에 기록한다)
  facts      prior.score(밴드 θ_low=0.3·θ_high=0.7, v1.0 §3-5 확정값)·critical  (soft)
적용 범위: 실험 트랙(stage_type="round")만. stage 값 = round 좌표(구조 확정 §2). age·u 는
stage 정렬 위치 인덱스로 계산한다(절대값 무관 — survival/fact-clock 관례).

사용(단독):
  python -m modules.transmission --issue issue_esa --run dryrun2 [--include-u0] [--critical-only]
    → 원장 요약·팩트별 B/TSR·획득 생명표를 콘솔에 출력(파일 안 씀, 점검용).
"""
from __future__ import annotations

import argparse
import json

from . import ledger, paths
from .debate_engine import build_edges
from .survival import _judgment_sha256, _sorted_stages

PROTOCOL = "docs/P3_TRANSMISSION_DESIGN.md v1.0 (prereg commit a70470d)"

# prior 밴드 경계 — v1.0 §3-5 확정값(사전고정된 조작적 층화, 자연적 경계 아님).
PRIOR_LOW = 0.3
PRIOR_HIGH = 0.7


def prior_band(fact: dict | None) -> str:
    """facts 레코드 → 'low'|'mid'|'high'|'unknown'. score null/부재 = unknown(밴드 불합산)."""
    score = ((fact or {}).get("prior") or {}).get("score")
    if score is None:
        return "unknown"
    if score <= PRIOR_LOW:
        return "low"
    if score >= PRIOR_HIGH:
        return "high"
    return "mid"


# ---------------------------------------------------------------------------
# 입력 정규화 (전부 순수 — 파일 I/O 는 CLI 전용 로더에만)
# ---------------------------------------------------------------------------
def mention_map(judgment: dict) -> tuple[list, dict]:
    """(정렬된 round 값 목록, {round: {fact_id: set(agents_mentioning)}}).

    귀속은 agents_mentioning 만 쓴다(status 아님) — 노출·획득이 모두 이 필드 위에 정의된다
    (v1.0 §3-2). 필드 부재는 빈 집합(soft)으로 취급한다.
    """
    stages = _sorted_stages(judgment)
    rounds = [st.get("stage") for st in stages]
    mentions: dict = {}
    for st in stages:
        m: dict = {}
        for f in st.get("facts", []):
            m[f["fact_id"]] = set(f.get("agents_mentioning") or [])
        mentions[st.get("stage")] = m
    return rounds, mentions


def holders_map(assignment: dict) -> tuple[list[str], dict[str, set[str]]]:
    """(agent_id 목록(배분표 순서), {fact_id: 보유자 집합 H(f)})."""
    agents = [ag["agent_id"] for ag in assignment.get("agents", [])]
    holders: dict[str, set[str]] = {}
    for ag in assignment.get("agents", []):
        for fid in ag.get("assigned_fact_ids", []):
            holders.setdefault(fid, set()).add(ag["agent_id"])
    return agents, holders


def edges_map(events: list[dict] | None, agent_ids: list[str]) -> tuple[dict[str, set[str]], dict]:
    """debate 이벤트의 seating 으로 {agent_id: 이웃 집합} 복원.

    seating{structure, order} 가 있으면 debate_engine.build_edges 를 그대로 재사용해
    좌석 인덱스 → agent_id 로 사상한다(엔진과 동일 소스 — 이중정의 금지).
    seating 이 없으면 full 가정으로 동작하고 meta.assumed_full=True 를 기록한다(v1.0 §3-1).
    """
    seating = None
    for ev in events or []:
        if ev.get("event") == "seating":
            seating = ev
            break
    if seating is None:
        return ({a: set(agent_ids) - {a} for a in agent_ids},
                {"structure": "full", "assumed_full": True})
    order = seating.get("order", [])
    structure = seating.get("structure", "full")
    idx_edges = build_edges(structure, len(order))
    edges = {order[i]: {order[j] for j in idx_edges[i]} for i in range(len(order))}
    # 좌석표에 없는 에이전트(방어): 이웃 없음 — 노출 불가로 자동 처리된다.
    for a in agent_ids:
        edges.setdefault(a, set())
    return edges, {"structure": structure, "assumed_full": False}


def inject_map(events: list[dict] | None) -> dict:
    """{round: set(injected_fact_ids)} — ledger_inject 이벤트만 읽는다."""
    out: dict = {}
    for ev in events or []:
        if ev.get("event") == "ledger_inject":
            out.setdefault(ev.get("round"), set()).update(ev.get("injected_fact_ids", []))
    return out


# ---------------------------------------------------------------------------
# 사건 원장 (1급 산출물)
# ---------------------------------------------------------------------------
def pair_records(
    judgment: dict,
    assignment: dict,
    events: list[dict] | None = None,
    *,
    facts_by_id: dict[str, dict] | None = None,
    question_exposed_ids: frozenset | set = frozenset(),
) -> tuple[list[dict], dict]:
    """(비보유자 a, 팩트 f) 전수 사건 원장. 반환 (records, meta).

    각 레코드의 kind ∈ {acquisition, prior_suspect, censored, never_exposed}:
      acquisition   — 노출 선행 첫 언급. u=τ−e(위치차), strict=(u≥1), u0_immediate=(u==0),
                      channel(첫 노출: organic|ledger|mixed), exposure_sources(organic 이웃 —
                      증거 좌표: 그 이웃들의 첫 노출 직전 stage 발화), in_window_at_tau.
      prior_suspect — 노출 전 언급(τ<e 또는 노출 없음) = 사전지식/작화 신호. 전달 아님.
      censored      — 노출됐으나 관측 끝까지 미언급(우측 검열). censor_age = 마지막 위치 − e.
      never_exposed — 관측 내 노출 없음(음영) — 분모 밖, 카운트만(v1.0 §3-2).
    question_exposed_ids 에 든 팩트의 레코드는 excluded=True 로 표기된다(집계 뷰가 걸러냄).
    """
    rounds, mentions = mention_map(judgment)
    agents, holders = holders_map(assignment)
    edges, edge_meta = edges_map(events, agents)
    injects = inject_map(events)
    run_id = judgment.get("run_id")
    n_rounds = len(rounds)

    fact_ids: list[str] = []
    seen: set[str] = set()
    for r in rounds:
        for fid in mentions[r]:
            if fid not in seen:
                seen.add(fid)
                fact_ids.append(fid)

    records: list[dict] = []
    for fid in fact_ids:
        h = holders.get(fid, set())
        fact = (facts_by_id or {}).get(fid)
        band = prior_band(fact)
        critical = bool((fact or {}).get("critical")) if fact is not None else None
        excluded = fid in question_exposed_ids
        for a in agents:
            if a in h:
                continue
            # 노출 계열: 위치 idx 1..n-1 에서 X(a, f, rounds[idx]) 판정.
            e_idx = None
            channel = None
            sources: list[str] = []
            exposed_idx: list[int] = []
            for idx in range(1, n_rounds):
                prev_r, r = rounds[idx - 1], rounds[idx]
                organic_js = edges.get(a, set()) & mentions[prev_r].get(fid, set())
                inj = fid in injects.get(r, set())
                if organic_js or inj:
                    exposed_idx.append(idx)
                    if e_idx is None:
                        e_idx = idx
                        channel = ("mixed" if (organic_js and inj)
                                   else "organic" if organic_js else "ledger")
                        sources = sorted(organic_js)
            # 첫 언급 τ.
            tau_idx = None
            for idx in range(n_rounds):
                if a in mentions[rounds[idx]].get(fid, set()):
                    tau_idx = idx
                    break

            rec = {
                "run_id": run_id, "fact_id": fid, "agent_id": a,
                "holders": sorted(h), "prior_band": band, "critical": critical,
                "excluded": excluded,
                "e_round": None if e_idx is None else rounds[e_idx],
                "tau_round": None if tau_idx is None else rounds[tau_idx],
                "channel": channel, "exposure_sources": sources,
                "u": None, "strict": None, "u0_immediate": False,
                "in_window_at_tau": None, "censor_age": None,
            }
            if tau_idx is not None and (e_idx is None or tau_idx < e_idx):
                rec["kind"] = "prior_suspect"
            elif tau_idx is not None:
                u = tau_idx - e_idx
                rec.update({
                    "kind": "acquisition", "u": u,
                    "strict": u >= 1, "u0_immediate": u == 0,
                    "in_window_at_tau": tau_idx in exposed_idx,
                })
            elif e_idx is not None:
                rec.update({"kind": "censored", "censor_age": (n_rounds - 1) - e_idx})
            else:
                rec["kind"] = "never_exposed"
            records.append(rec)

    meta = {"protocol": PROTOCOL, "run_id": run_id, "rounds": rounds,
            "n_agents": len(agents), "n_facts": len(fact_ids),
            "edges": edge_meta,
            "question_excluded_facts": sorted(f for f in fact_ids
                                              if f in question_exposed_ids)}
    return records, meta


# ---------------------------------------------------------------------------
# 집계 뷰 (전부 원장의 함수)
# ---------------------------------------------------------------------------
def _tracked(records: list[dict], *, critical_only: bool = False,
             band: str | None = None) -> list[dict]:
    """추적자 정본 필터: question 제외 팩트 배제 + 선택적 critical/prior 밴드 한정."""
    out = [r for r in records if not r["excluded"]]
    if critical_only:
        out = [r for r in out if r["critical"]]
    if band is not None:
        out = [r for r in out if r["prior_band"] == band]
    return out


def fact_metrics(records: list[dict]) -> list[dict]:
    """팩트별 B(엄격)·B_upper(u=0 포함)·TSR = B/|N_exp| (v1.0 §3-2). excluded 팩트도
    행은 내되 excluded=True 로 표기한다(제외 목록 병기 의무)."""
    by_fact: dict[str, list[dict]] = {}
    for r in records:
        by_fact.setdefault(r["fact_id"], []).append(r)
    rows = []
    for fid, rs in by_fact.items():
        exposed = [r for r in rs if r["kind"] in ("acquisition", "censored")]
        b_strict = sum(1 for r in rs if r["kind"] == "acquisition" and r["strict"])
        b_upper = sum(1 for r in rs if r["kind"] == "acquisition")
        n_exp = len(exposed)
        rows.append({
            "fact_id": fid, "excluded": rs[0]["excluded"],
            "prior_band": rs[0]["prior_band"], "critical": rs[0]["critical"],
            "n_nonholders": len(rs), "n_exposed": n_exp,
            "n_never_exposed": sum(1 for r in rs if r["kind"] == "never_exposed"),
            "n_prior_suspect": sum(1 for r in rs if r["kind"] == "prior_suspect"),
            "B": b_strict, "B_upper": b_upper,
            "TSR": round(b_strict / n_exp, 4) if n_exp else None,
        })
    return rows


def system_summary(records: list[dict], *, critical_only: bool = False,
                   band: str | None = None) -> dict:
    """쌍 풀링 시스템 지표(추적자 정본 한정) + kind 분포. TSR_system = 엄격 획득/노출 쌍."""
    tracked = _tracked(records, critical_only=critical_only, band=band)
    exposed = [r for r in tracked if r["kind"] in ("acquisition", "censored")]
    acq_strict = [r for r in tracked if r["kind"] == "acquisition" and r["strict"]]
    acq_all = [r for r in tracked if r["kind"] == "acquisition"]
    return {
        "scope": {"critical_only": critical_only, "band": band},
        "n_pairs_tracked": len(tracked),
        "n_pairs_excluded_question": sum(1 for r in records if r["excluded"]),
        "kinds": {k: sum(1 for r in tracked if r["kind"] == k)
                  for k in ("acquisition", "censored", "prior_suspect", "never_exposed")},
        "n_exposed_pairs": len(exposed),
        "n_acq_strict": len(acq_strict),
        "n_acq_u0": sum(1 for r in acq_all if r["u0_immediate"]),
        "tsr_system": round(len(acq_strict) / len(exposed), 4) if exposed else None,
        "tsr_system_upper": round(len(acq_all) / len(exposed), 4) if exposed else None,
        "by_channel": {c: sum(1 for r in acq_all if r["channel"] == c)
                       for c in ("organic", "ledger", "mixed")},
    }


def acquisition_life_table(records: list[dict], *, include_u0: bool = False,
                           critical_only: bool = False, band: str | None = None) -> dict:
    """첫 노출 정렬 획득 생명표 — fact-clock 검열 형식화의 획득 방향·쌍 수준 이식(v1.0 §3-3).

    모집단 = 추적자 정본 중 노출된 쌍(acquisition·censored). age u = 첫 노출 후 u번째 위치.
    사건 = 엄격 획득(u≥1). include_u0=False(정본)면 u=0 획득 쌍은 age 0 검열로 처리하고
    n_u0_immediate_censored 로 분리 보고한다(이미 발화했으므로 이후 at-risk 아님).
    include_u0=True 는 상한 민감도(u=0 을 age 0 사건으로 계상). 우측 검열: censored 쌍은
    censor_age 에서 검열. h_acq(u) = acquisitions(u)/at_risk(u), at_risk(u) = #{event_age ≥ u}.
    CIF(누적 획득) = 1 − Π(1 − h).
    """
    tracked = _tracked(records, critical_only=critical_only, band=band)
    events: list[tuple[str, int]] = []   # ("acq"|"cens", age)
    n_u0 = 0
    for r in tracked:
        if r["kind"] == "acquisition":
            if r["strict"]:
                events.append(("acq", r["u"]))
            elif include_u0:
                events.append(("acq", 0))
            else:
                n_u0 += 1
                events.append(("cens", 0))
        elif r["kind"] == "censored":
            events.append(("cens", r["censor_age"]))
    max_age = max((age for _, age in events), default=0)
    life = []
    cif = []
    surv = 1.0
    for u in range(0, max_age + 1):
        at_risk = sum(1 for _, age in events if age >= u)
        acq = sum(1 for kind, age in events if kind == "acq" and age == u)
        cens = sum(1 for kind, age in events if kind == "cens" and age == u)
        h = round(acq / at_risk, 4) if at_risk else None
        if h is not None:
            surv *= (1 - h)
        life.append({"age": u, "at_risk": at_risk, "acquisitions": acq,
                     "censored": cens, "h_acq": h})
        cif.append({"age": u, "cif": round(1 - surv, 4)})
    return {"include_u0": include_u0,
            "scope": {"critical_only": critical_only, "band": band},
            "n_pairs": len(events), "n_u0_immediate_censored": n_u0,
            "life_table": life, "cif": cif}


def b_pre_series(records: list[dict]) -> dict[str, list]:
    """{fact_id: 엄격 획득의 τ round 값 오름차순 목록}(추적자 정본) — H-T1 의 시변·과거 한정
    B_pre 를 소비자(회귀·판별)가 만들 수 있는 원천."""
    out: dict[str, list] = {}
    for r in _tracked(records):
        if r["kind"] == "acquisition" and r["strict"]:
            out.setdefault(r["fact_id"], []).append(r["tau_round"])
    return {fid: sorted(ts) for fid, ts in out.items()}


def b_pre(series: dict[str, list], fact_id: str, round_value) -> int:
    """B_pre(f, r) = round_value **미만** 시점의 엄격 획득 수(과거 한정 — 미래 정보 누출 금지)."""
    return sum(1 for t in series.get(fact_id, []) if t < round_value)


def report(
    judgment: dict,
    assignment: dict,
    events: list[dict] | None,
    facts_by_id: dict[str, dict] | None = None,
    *,
    question_exposed_ids: frozenset | set = frozenset(),
    critical_only: bool = False,
) -> dict:
    """사건 원장 + 집계 뷰 일괄 구조(감사 필드 포함). 원장이 정본, 나머지는 전부 뷰."""
    records, meta = pair_records(judgment, assignment, events,
                                 facts_by_id=facts_by_id,
                                 question_exposed_ids=question_exposed_ids)
    return {
        "protocol": PROTOCOL,
        "audit": {"judgment_sha256": _judgment_sha256(judgment),
                  "issue_id": judgment.get("issue_id"), "run_id": judgment.get("run_id"),
                  "question_exposed_ids": sorted(question_exposed_ids)},
        "meta": meta,
        "records": records,
        "fact_metrics": fact_metrics(records),
        "system": system_summary(records, critical_only=critical_only),
        "system_low_prior": system_summary(records, critical_only=critical_only, band="low"),
        "life_strict": acquisition_life_table(records, include_u0=False,
                                              critical_only=critical_only),
        "life_upper": acquisition_life_table(records, include_u0=True,
                                             critical_only=critical_only),
        "b_pre_series": b_pre_series(records),
    }


# ---------------------------------------------------------------------------
# CLI (점검용 — 파일을 쓰지 않는다)
# ---------------------------------------------------------------------------
def load_debate_events(issue_id: str, run_id: str) -> list[dict]:
    """debate.jsonl → 이벤트 목록(읽기 전용)."""
    out = []
    for line in paths.debate(issue_id, run_id).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def load_assignment(issue_id: str) -> dict:
    return json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="P3 층 1 전달 레이더 — 사건 원장·B/TSR·획득 생명표 점검")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--include-u0", action="store_true", help="상한(u=0 포함) 생명표 출력")
    ap.add_argument("--critical-only", action="store_true")
    args = ap.parse_args()

    judgment = ledger.load_judgment(args.issue, args.run)
    assignment = load_assignment(args.issue)
    events = load_debate_events(args.issue, args.run)
    facts_by_id = ledger.load_facts_by_id(args.issue)
    rep = report(judgment, assignment, events, facts_by_id,
                 critical_only=args.critical_only)

    m, s = rep["meta"], rep["system"]
    print(f"[transmission] issue={args.issue} run={args.run}")
    print(f"[transmission] {PROTOCOL}")
    print(f"[transmission] rounds={m['rounds']} agents={m['n_agents']} facts={m['n_facts']} "
          f"edges={m['edges']}")
    print(f"[transmission] 쌍 {s['n_pairs_tracked']} · kinds={s['kinds']} · "
          f"u0_immediate={s['n_acq_u0']}")
    print(f"[transmission] TSR_system(엄격)={s['tsr_system']} · 상한={s['tsr_system_upper']} · "
          f"채널={s['by_channel']}")
    print("[transmission] 팩트별 (B/B_upper/TSR · 노출/음영/prior_suspect):")
    for row in rep["fact_metrics"]:
        flag = " [제외:question]" if row["excluded"] else ""
        print(f"  {row['fact_id']}: B={row['B']}/{row['B_upper']} TSR={row['TSR']} · "
              f"exp={row['n_exposed']} shadow={row['n_never_exposed']} "
              f"prior?={row['n_prior_suspect']}{flag}")
    key = "life_upper" if args.include_u0 else "life_strict"
    lt = rep[key]
    print(f"[transmission] 획득 생명표({'상한 u>=0' if args.include_u0 else '엄격 u>=1'}, "
          f"u0 검열 {lt['n_u0_immediate_censored']}건):")
    for row in lt["life_table"]:
        print(f"  age {row['age']}: at_risk={row['at_risk']} acq={row['acquisitions']} "
              f"cens={row['censored']} h_acq={row['h_acq']}")


if __name__ == "__main__":
    main()
