"""[요한 · 관측 레이어 트랙] FastAPI 뷰어 어댑터 (카와이 판).

설계 §2 경계 원칙 준수: 읽기 전용 — 어떤 산출물도 쓰지 않고, LLM 호출 0.
민옥의 modules.viewmodel.build_viewmodel() 을 **그대로 소비**한다(계약 재사용,
뷰어 전용 모델 이중정의 없음). make_viewer.py(정적 생성)와 형제 어댑터 —
같은 뷰모델을 먹고 화면 자산을 공유한다.

FastAPI 어댑터의 실익(정적 생성 대비): run 목록/브라우징 + 라이브 파일시스템 직독
(새 run 이 빌드 없이 등장). run 발견 기준 = data/debates 의 debate.jsonl 스캔
(v0.3 §G 제안 선반영) — 부분 run(채점 전)도 run_state/parts 와 함께 노출하며,
"4파일 완비" 특례는 없다.

실행(리포 루트에서):
  pip install -r tools/viewer/requirements.txt
  uvicorn tools.viewer.app:app --port 8011
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from modules import paths, ledger, survival
from modules.judge import SURVIVING
from modules.viewmodel import build_viewmodel, STATUS_ORDER

app = FastAPI(title="팩트 생존 뷰어")
HERE = Path(__file__).resolve().parent


def _issue_title(issue_id: str) -> str:
    try:
        return json.loads(paths.issue(issue_id).read_text(encoding="utf-8")).get("title", issue_id)
    except Exception:
        return issue_id


def _debate_run_id(path: Path) -> str | None:
    """debate.jsonl 내용에서 run_id 취득 — 이벤트엔 issue_id 가 없고 run_id 만 있어
    파일명 언더스코어 분해 모호성을 회피(내용 앵커, 기존 judgment 스캔과 같은 결)."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rid = json.loads(line).get("run_id")
        except Exception:
            continue
        if rid:
            return rid
    return None


def _run_parts(issue_id: str, run_id: str) -> tuple[str, dict]:
    """순수 파일 관찰(LLM 0)로 run_state/parts 산출 (스키마 v0.3 §B 필드명 — 제안 상태).
    ⚠ 레거시 호환: 기존 debate 엔 run_end 이벤트가 없어, debate 완결을 judgment 존재로
    프록시한다(run_end 도입 전까지의 절충 — §H 사람 협의 안건)."""
    dpath = paths.debate(issue_id, run_id)
    debate_exists = dpath.exists()
    judgment_exists = paths.judgment(issue_id, run_id).exists()
    has_run_end = has_inject = False
    if debate_exists:
        for line in dpath.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line).get("event")
            except Exception:
                continue
            if ev == "run_end":
                has_run_end = True
            elif ev == "ledger_inject":
                has_inject = True
    debate_state = ("absent" if not debate_exists
                    else "complete" if (has_run_end or judgment_exists)
                    else "partial")
    parts = {
        "debate": debate_state,
        "judgment": "present" if judgment_exists else "absent",
        "recalls": "present" if has_inject else "absent",  # v0.3 recalls 계약 전 프록시(재주입 유무)
    }
    if not debate_exists:
        run_state = "absent"
    elif judgment_exists and debate_state == "complete":
        run_state = "complete"
    else:
        run_state = "partial"
    return run_state, parts


def _available_runs() -> list[dict]:
    """data/debates 스캔 → run 목록(부분/완전 모두). 존재 기준 = debate.jsonl (§G).
    run_id 는 파일 내용에서, issue_id 는 파일명 접미 제거로 역추출. '4파일 완비' 특례 없음."""
    out: list[dict] = []
    ddir = paths.DATA / "debates"
    if not ddir.exists():
        return out
    for df in sorted(ddir.glob("debate_*.jsonl")):
        run_id = _debate_run_id(df)
        if not run_id:
            continue
        core = df.name[len("debate_"):-len(".jsonl")]  # = issue_id + "_" + run_id
        suffix = "_" + run_id
        if not core.endswith(suffix):
            continue
        issue_id = core[:-len(suffix)]
        if not issue_id or not paths.issue(issue_id).exists():
            continue
        run_state, parts = _run_parts(issue_id, run_id)
        item = {
            "issue_id": issue_id, "run_id": run_id, "title": _issue_title(issue_id),
            "run_state": run_state, "parts": parts,
            "stage_type": None, "judge": None, "n_stages": None, "far_system": None,
        }
        if parts["judgment"] == "present":
            try:
                jd = json.loads(paths.judgment(issue_id, run_id).read_text(encoding="utf-8"))
                item.update(
                    stage_type=jd.get("stage_type"),
                    judge=(jd.get("judge") or {}).get("model"),
                    n_stages=len(jd.get("stages", [])),
                    far_system=(jd.get("summary") or {}).get("far_system"),
                )
            except Exception:
                pass
        out.append(item)
    return out


def _partial_viewmodel(issue_id: str, run_id: str) -> dict:
    """judgment 없는 run 의 부분 뷰모델 — build_viewmodel 과 같은 shape(발화만, 매트릭스 빈값).
    ⚠ 임시 스캐폴드: viewmodel.py(공용 계약) 미변경 원칙상 여기서 조립. §B viewmodel
    부분상태가 정식 반영되면 이 함수를 build_viewmodel 로 흡수한다."""
    def _load(p, default):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default

    issue_doc = _load(paths.issue(issue_id), {})
    facts_doc = _load(paths.facts(issue_id), {"facts": []})
    events = [json.loads(line) for line
              in paths.debate(issue_id, run_id).read_text(encoding="utf-8").splitlines()
              if line.strip()]

    facts = [{"fact_id": f["fact_id"], "text": f.get("text", ""),
              "tags": f.get("tags", []), "critical": bool(f.get("critical"))}
             for f in facts_doc.get("facts", [])]
    rounds = sorted({e.get("round") for e in events
                     if e.get("event") == "utterance" and e.get("round") is not None})
    utterances: dict[str, list] = {str(n): [] for n in rounds}
    for e in events:
        if e.get("event") == "utterance":
            utterances.setdefault(str(e.get("round")), []).append({
                "agent_id": e.get("agent_id"), "stance": e.get("stance"),
                "perspective": e.get("perspective"), "text": e.get("response_text", ""),
            })
    injects = [{"round": e.get("round"), "fact_ids": e.get("injected_fact_ids", [])}
               for e in events if e.get("event") == "ledger_inject"]
    ledger_mode = next((e.get("ledger_mode") for e in events
                        if e.get("event") == "utterance"), "off")
    return {
        "meta": {
            "issue_id": issue_id, "run_id": run_id,
            "title": issue_doc.get("title", issue_id),
            "stage_type": None, "ledger_mode": ledger_mode, "judge": {},
            "n_facts": len(facts), "n_critical": sum(1 for f in facts if f["critical"]),
            "created_at": None,
        },
        "stages": rounds, "facts": facts, "matrix": {},
        "utterances": utterances, "injects": injects,
        "tag_vocab": sorted({t for f in facts for t in f["tags"]}),
        "far_by_stage": [], "status_order": list(STATUS_ORDER),
    }


@app.get("/api/runs")
def api_runs() -> dict:
    return {"runs": _available_runs()}


@app.get("/api/viewmodel/{issue_id}/{run_id}")
def api_viewmodel(issue_id: str, run_id: str) -> dict:
    run_state, parts = _run_parts(issue_id, run_id)
    if parts["debate"] == "absent":
        raise HTTPException(status_code=404, detail=f"산출물 없음: debate 없음 ({issue_id}/{run_id})")
    try:
        vm = (build_viewmodel(issue_id, run_id) if parts["judgment"] == "present"
              else _partial_viewmodel(issue_id, run_id))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"산출물 없음: {e}")
    except Exception as e:  # 파싱 실패 = 스키마 드리프트 신호(설계 §3) → 화면에 노출
        raise HTTPException(status_code=500, detail=f"뷰모델 생성 실패(스키마 드리프트?): {e}")
    vm["run_state"] = run_state   # v0.3 §B (app 층 공급 — viewmodel 승격 시 그대로 이관)
    vm["parts"] = parts
    return vm


# --- 파이프라인 노드별 단계 데이터 (읽기 전용, run 무관 3 + run별 1) ---
# 다이어그램 노드 클릭 → 그 단계 산출물. paths.py 로만 경로 유도, 파일 쓰기 0.

@app.get("/api/issue/{issue_id}")
def api_issue(issue_id: str) -> dict:
    """데이터 로더 노드 — issue.json 전량(title·body·source_meta)."""
    try:
        return json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"issue 없음: {e}")


@app.get("/api/facts/{issue_id}")
def api_facts(issue_id: str) -> dict:
    """팩트 추출기 노드 — facts.json 전량(text·tags·critical·prior)."""
    try:
        return json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"facts 없음: {e}")


@app.get("/api/assignment/{issue_id}")
def api_assignment(issue_id: str) -> dict:
    """배분기 노드 — assignment.json(seed·agents[perspective/stance/assigned_fact_ids])."""
    try:
        return json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"assignment 없음: {e}")


@app.get("/api/analysis/{issue_id}/{run_id}")
def api_analysis(issue_id: str, run_id: str) -> dict:
    """분석·리포트 노드 — survival 지표(순수 계산, 파일 안 씀).

    조건부 hazard·누적소실·FAR(report) + fact-clock(KM 생존·w_divergence).
    critical 스코프도 병기. survival 은 순수 함수라 산출물 경로 관례 불필요.
    """
    try:
        judgment = ledger.load_judgment(issue_id, run_id)
        facts_by_id = ledger.load_facts_by_id(issue_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"산출물 없음: {e}")
    try:
        return {
            "issue_id": issue_id,
            "run_id": run_id,
            "report": survival.report(judgment, facts_by_id),
            "report_critical": survival.report(judgment, facts_by_id, critical_only=True),
            "fact_clock": survival.fact_clock_report(judgment, facts_by_id=facts_by_id),
        }
    except Exception as e:  # 계산 실패 = 스키마 드리프트 신호
        raise HTTPException(status_code=500, detail=f"분석 계산 실패(스키마 드리프트?): {e}")


@app.get("/api/provenance/{issue_id}/{run_id}")
def api_provenance(issue_id: str, run_id: str) -> dict:
    """run 기록 노드 — 재현성 신원 + 건강 판정 (베이스라인 자격 판별, 순수 파일 관찰).

    신원: seed·에이전트 수(assignment), judge 사양·judge_health·created_at(judgment),
    ledger_mode·라운드 수(debate). 건강: 공백 발화(llm.py 무음 폴백 흔적)·judge
    파싱실패·judgment 유무 — 전부 깨끗해야 baseline_eligible. "죽지 않는 파이프라인은
    조용히 썩는다" — 썩은 run 이 베이스라인 증빙으로 인용되는 것을 화면에서 막는다.
    """
    dpath = paths.debate(issue_id, run_id)
    if not dpath.exists():
        raise HTTPException(status_code=404, detail=f"산출물 없음: debate 없음 ({issue_id}/{run_id})")
    n_utt = n_blank = n_inject = 0
    ledger_mode = None
    rounds: set = set()
    for line in dpath.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "utterance":
            n_utt += 1
            rounds.add(ev.get("round"))
            if ledger_mode is None:
                ledger_mode = ev.get("ledger_mode")
            if not str(ev.get("response_text") or "").strip():
                n_blank += 1
        elif ev.get("event") == "ledger_inject":
            n_inject += 1

    seed = n_agents = None
    try:
        asg = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
        seed = asg.get("seed")
        n_agents = len(asg.get("agents", []))
    except FileNotFoundError:
        pass

    judge = judge_health = created_at = stage_type = None
    judgment_exists = paths.judgment(issue_id, run_id).exists()
    if judgment_exists:
        try:
            jd = json.loads(paths.judgment(issue_id, run_id).read_text(encoding="utf-8"))
            judge = jd.get("judge")
            judge_health = (jd.get("summary") or {}).get("judge_health")
            created_at = jd.get("created_at")
            stage_type = jd.get("stage_type")
        except Exception:
            pass

    issues = []
    if n_blank:
        issues.append(f"공백 발화 {n_blank}건 — llm 무음 폴백(5회 실패 후 공백 반환) 의심")
    if not judgment_exists:
        issues.append("judgment 없음 — 채점 전 (부분 run)")
    if judge_health and judge_health.get("n_parse_fail"):
        issues.append(f"judge 파싱실패 {judge_health['n_parse_fail']}건 — 무음 unmentioned 강등 포함 가능")
    if judgment_exists and judge_health is None:
        issues.append("judge_health 미계측 — 계기판(PR #14) 이전 산출물")
    return {
        "issue_id": issue_id,
        "run_id": run_id,
        "provenance": {
            "seed": seed, "n_agents": n_agents, "n_rounds": len(rounds),
            "ledger_mode": ledger_mode, "judge": judge, "judge_health": judge_health,
            "stage_type": stage_type, "created_at": created_at,
        },
        "health": {
            "n_utterances": n_utt, "blank_utterances": n_blank, "n_injects": n_inject,
            "baseline_eligible": not issues,
            "issues": issues,
        },
    }


@app.get("/api/biography/{issue_id}/{run_id}")
def api_biography(issue_id: str, run_id: str) -> dict:
    """팩트 전기(biography) 노드 — 팩트 하나의 일대기를 사건 사슬로 (프로토타입, 읽기 전용).

    "사건 원장 1급, 지표는 뷰"의 뷰어판: 생존 매트릭스가 상태(state)를 보여준다면
    이 뷰는 사건(event)을 보여준다 — 배정 → 언급/침묵 → 소실 → 재주입 → 재생(경로:
    장부/자생) → 재소실. 판정 불확실성(표 분열·parse_fail)을 셀 속성으로 병기한다.

    지금 지을 수 있는 7할: assignment+debate(utterance·ledger_inject)+judgment(votes).
    나머지 3할(노출 사건 — 이웃 발화로 언제 봤는가)은 스키마 v0.3 prompt_assembly
    안건(7/28 보드) 채택 시 완성된다. 잣대는 judge.SURVIVING 단일 소스.
    """
    jpath = paths.judgment(issue_id, run_id)
    if not jpath.exists():
        raise HTTPException(status_code=404, detail=f"judgment 없음 — 전기는 판정 이후 ({issue_id}/{run_id})")
    try:
        judgment = json.loads(jpath.read_text(encoding="utf-8"))
        facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
        events = [json.loads(ln) for ln
                  in paths.debate(issue_id, run_id).read_text(encoding="utf-8").splitlines()
                  if ln.strip()]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"산출물 없음: {e}")

    assigned_to: dict[str, list[str]] = {}
    agent_persp: dict[str, str] = {}
    seed = None
    try:
        asg = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
        seed = asg.get("seed")
        for ag in asg.get("agents", []):
            agent_persp[ag["agent_id"]] = ag.get("perspective") or "?"
            for fid in ag.get("assigned_fact_ids", []):
                assigned_to.setdefault(fid, []).append(ag["agent_id"])
    except FileNotFoundError:
        pass

    injects_by_round: dict[int, set] = {}
    utt_text: dict[tuple, str] = {}
    for e in events:
        if e.get("event") == "ledger_inject":
            injects_by_round.setdefault(e.get("round"), set()).update(
                e.get("injected_fact_ids", []))
        elif e.get("event") == "utterance":
            utt_text[(e.get("round"), e.get("agent_id"))] = e.get("response_text") or ""

    stage_recs: dict[int, dict[str, dict]] = {
        s["stage"]: {f["fact_id"]: f for f in s.get("facts", [])}
        for s in judgment.get("stages", [])}
    stages = sorted(stage_recs)

    bios = []
    for f in facts_doc.get("facts", []):
        fid = f["fact_id"]
        chain, prev_surv, first_missing, n_rev_ledger, n_rev_organic = [], None, None, 0, 0
        for r in stages:
            rec = stage_recs[r].get(fid)
            if rec is None:
                continue
            surv = rec.get("status") in SURVIVING
            votes = rec.get("votes") or []
            statuses = [v.get("status") for v in votes if isinstance(v, dict)]
            injected = fid in injects_by_round.get(r, ())
            if surv and prev_surv is False:
                event = "revived_ledger" if injected else "revived_organic"
                if injected:
                    n_rev_ledger += 1
                else:
                    n_rev_organic += 1
            elif surv and prev_surv is None:
                event = "first_mention"
            elif not surv and prev_surv:
                event = "died"
            elif not surv:
                event = "missing"
            else:
                event = "alive"
            if not surv and first_missing is None:
                first_missing = r
            chain.append({
                "stage": r, "status": rec.get("status"), "surviving": surv,
                "event": event, "injected": injected,
                "votes": {
                    "n": len(statuses),
                    "split": None if not statuses else f"{max(statuses.count(s) for s in set(statuses))}/{len(statuses)}",
                    "unanimous": None if not statuses else len(set(statuses)) == 1,
                    "parse_fail": sum(1 for v in votes if isinstance(v, dict)
                                      and str(v.get("reason", "")).startswith("parse_fail:")),
                },
                "mentions": [
                    {"agent_id": aid, "snippet": (utt_text.get((r, aid), "")[:200] or None)}
                    for aid in rec.get("agents_mentioning", [])],
            })
            prev_surv = surv
        bios.append({
            "fact_id": fid, "text": f.get("text", ""), "critical": bool(f.get("critical")),
            "tags": f.get("tags", []), "assigned_to": assigned_to.get(fid, []),
            # 팩트의 '관점' = 이 팩트를 배정받은 에이전트들의 perspective (유도값 —
            # facts 스키마에 관점 필드가 없어 assignment 에서 역산. 등장 순서 보존)
            "perspectives": list(dict.fromkeys(
                agent_persp.get(a, "?") for a in assigned_to.get(fid, []))),
            "chain": chain,
            "summary": {
                "final_surviving": chain[-1]["surviving"] if chain else None,
                "first_missing_stage": first_missing,
                "n_revived_ledger": n_rev_ledger, "n_revived_organic": n_rev_organic,
            },
        })
    ledger_mode = next((e.get("ledger_mode") for e in events
                        if e.get("event") == "utterance"), None)
    return {"issue_id": issue_id, "run_id": run_id, "stages": stages,
            "ledger_mode": ledger_mode,
            # 실험 조건 요약 — 사이드바 조건 패널용 (전부 기존 산출물에서 읽기 전용 유도)
            "conditions": {
                "seed": seed,
                "n_agents": len(agent_persp) or None,
                "n_rounds": len({e.get("round") for e in events
                                 if e.get("event") == "utterance"}),
                "ledger_mode": ledger_mode,
                "judge": judgment.get("judge"),
                "far_system": (judgment.get("summary") or {}).get("far_system"),
                "perspectives": sorted(set(agent_persp.values())),
            },
            "facts": bios,
            "note": "노출 사건(누가 언제 봤는가)은 스키마 v0.3 prompt_assembly 채택 후 완성 — 현재는 배정·언급·주입·판정 사슬까지."}


@app.get("/biography", response_class=HTMLResponse)
def biography_page() -> str:
    return (HERE / "biography.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (HERE / "index.html").read_text(encoding="utf-8")
