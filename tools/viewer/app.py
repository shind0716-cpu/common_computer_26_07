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
import re
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
    나머지 3할(노출 사건 — 이웃 발화로 언제 봤는가)은 prompt_assembly 를 실은 로그에서
    완성된다. 스키마는 확정·구현됐고(v0.3, 2026-07-28) 남은 것은 데이터다 — 현재 리포의
    로그는 전부 그 이전 산출이라 아직 재구성 경로를 쓴다(modules/access_window 참조).
    잣대는 judge.SURVIVING 단일 소스.
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
            "note": ("노출 사건(누가 언제 봤는가)은 prompt_assembly 를 실은 로그에서 완성된다 — "
                     "스키마는 v0.3(7/28)로 확정·구현됐고, 이 로그는 그 이전 산출이라 "
                     "배정·언급·주입·판정 사슬까지만이다.")}


@app.get("/api/ledger/{issue_id}/{run_id}")
def api_ledger(issue_id: str, run_id: str) -> dict:
    """장부(ledger) 노드 — 라운드별 소실 장부 + 재주입·생환 성과 (프로토타입, 읽기 전용).

    소실 잣대 = ledger.missing_facts(= judge.SURVIVING 단일 소스). off run 에서는
    주입이 없으므로 '소실 장부'만 — v0 였다면 재주입됐을 목록이 그대로 보인다.

    재주입 블록 문구는 `ledger_inject.injected_text`(스키마 v0.3, 2026-07-28 확정·구현)가
    있으면 **실삽입 원문**을 그대로 쓰고, 없으면 build_injection_block 재조립본으로 물러난다.
    어느 쪽인지 `block_text_source` 에 적는다 — v0.2 로그는 원문이 아예 없으므로 재조립본이
    유일한 선택지이며, 그 사실을 화면에서 숨기지 않는다.
    """
    jpath = paths.judgment(issue_id, run_id)
    if not jpath.exists():
        raise HTTPException(status_code=404, detail=f"judgment 없음 ({issue_id}/{run_id})")
    try:
        judgment = json.loads(jpath.read_text(encoding="utf-8"))
        facts_by_id = ledger.load_facts_by_id(issue_id)
        events = [json.loads(ln) for ln
                  in paths.debate(issue_id, run_id).read_text(encoding="utf-8").splitlines()
                  if ln.strip()]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"산출물 없음: {e}")

    stages = sorted(s["stage"] for s in judgment.get("stages", []))
    status_by_stage = {s["stage"]: {f["fact_id"]: f["status"] for f in s["facts"]}
                       for s in judgment.get("stages", [])}

    def brief(fid):
        f = facts_by_id.get(fid, {})
        return {"fact_id": fid, "text": (f.get("text") or "")[:60],
                "critical": bool(f.get("critical"))}

    ledger_by_stage = []
    for st in stages:
        ids = ledger.missing_facts(judgment, st)
        ledger_by_stage.append({
            "stage": st, "missing": [brief(i) for i in ids],
            "n_missing": len(ids),
            "would_inject_chars": len(ledger.build_injection_block(ids, facts_by_id)),
        })

    injections = []
    for e in events:
        if e.get("event") != "ledger_inject":
            continue
        r, ids = e.get("round"), e.get("injected_fact_ids", [])
        cur = status_by_stage.get(r, {})
        revived = [i for i in ids if cur.get(i) in SURVIVING]
        literal_text = e.get("injected_text")   # v0.3 — 실삽입 원문(있으면 이게 정본)
        injections.append({
            "round": r, "reason": e.get("reason"),
            "injected": [brief(i) for i in ids],
            "block_text": literal_text or ledger.build_injection_block(ids, facts_by_id),
            "block_text_source": "injected_text" if literal_text else "rebuilt",
            "outcome": {"revived": revived,
                        "still_missing": [i for i in ids if i not in revived]},
        })

    ledger_mode = next((e.get("ledger_mode") for e in events
                        if e.get("event") == "utterance"), None)
    return {"issue_id": issue_id, "run_id": run_id, "ledger_mode": ledger_mode,
            "stages": stages, "ledger_by_stage": ledger_by_stage,
            "injections": injections,
            "note": ("off run — 주입 없음: 소실 장부는 'v0였다면 재주입됐을 목록'이다."
                     if not injections else
                     "블록 문구 = 실삽입 원문(injected_text)."
                     if all(i["block_text_source"] == "injected_text" for i in injections)
                     else "블록 문구 = 재조립본 — 이 로그는 v0.2 산출이라 실삽입 원문이 "
                          "없다(injected_text 는 v0.3 확정·구현, 이후 로그부터 실린다).")}


@app.get("/api/transmission/{issue_id}/{run_id}")
def api_transmission(issue_id: str, run_id: str) -> dict:
    """전달 레이더 노드 — transmission.report() 현장 유도 (survival /api/analysis 전례).

    ⚠ 지위: G2 층1 구현은 팀 제안(동결) 상태 — 이 페이지는 브랜치 프로토타입.
    영점 조정(question 문면 팩트 제외)은 LLM 스캔 산출물이 필요해 뷰어(LLM 0)가
    직접 못 만든다 — data/scans/question_scan_{issue}.json 이 있으면 적용, 없으면
    '영점 미적용'을 명시해 강등 표기한다(침묵 실패 방지).
    """
    from modules import transmission as tr
    jpath = paths.judgment(issue_id, run_id)
    if not jpath.exists():
        raise HTTPException(status_code=404, detail=f"judgment 없음 ({issue_id}/{run_id})")
    try:
        judgment = json.loads(jpath.read_text(encoding="utf-8"))
        facts_by_id = ledger.load_facts_by_id(issue_id)
        assignment = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
        events = [json.loads(ln) for ln
                  in paths.debate(issue_id, run_id).read_text(encoding="utf-8").splitlines()
                  if ln.strip()]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"산출물 없음: {e}")

    scan_path = paths.DATA / "scans" / f"question_scan_{issue_id}.json"
    exposed_ids: frozenset = frozenset()
    if scan_path.exists():
        try:
            exposed_ids = frozenset(
                json.loads(scan_path.read_text(encoding="utf-8"))
                .get("question_exposed_ids", []))
        except Exception:
            pass
    try:
        rep = tr.report(judgment, assignment, events, facts_by_id,
                        question_exposed_ids=exposed_ids)
    except Exception as e:  # 계산 실패 = 스키마 드리프트 신호
        raise HTTPException(status_code=500, detail=f"레이더 계산 실패(스키마 드리프트?): {e}")
    rep["zero_point"] = {
        "applied": bool(exposed_ids) or scan_path.exists(),
        "question_exposed_ids": sorted(exposed_ids),
        "note": (None if scan_path.exists() else
                 "영점 미적용 — question 스캔 산출물 없음. TSR·획득에 question 유래 "
                 "거짓양성이 섞였을 수 있음(탐색적으로만 읽을 것)."),
    }
    rep["status_note"] = "G2 층1 = 팀 제안(동결) — 브랜치 프로토타입 지위, 수치는 탐색적."
    return rep


def _ngrams(text: str, n: int = 3) -> set:
    """문자 n-gram 집합 (한글·영숫자만 남기고 공백·문장부호 제거).

    ⚠ 같은 식이 experiments/ 안 러너 3종에 이미 있다(run_experiment·run_checks·run_judge_probe).
    이 뷰어가 네 번째 사본이며 WORKING_RULES R4(세 번째에 추출)의 추출 시점을 넘겼다 —
    다만 뷰어는 읽기 전용 어댑터라 experiments/ 를 import 하지 않는 것이 경계 원칙이므로,
    공용 계기로 뺄 때(modules 편입) 함께 정리한다. 식은 H2 실측과 동일해야 수치가 비교 가능하다.
    """
    t = re.sub(r"[^0-9A-Za-z가-힣]", "", text or "")
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def _containment(fact_text: str, utt_text: str) -> float:
    """팩트 원문의 3-gram 중 발화에 나타난 비율 (축자 인용=1.0). 결정론적 — LLM 0."""
    fg = _ngrams(fact_text)
    if not fg:
        return 0.0
    return round(len(fg & _ngrams(utt_text)) / len(fg), 3)


# H2 실측(2026-07-29, experiments/instrument_check) — 근접도 구간별 판정기 검출률.
# 지표가 아니라 **어디를 먼저 볼지 고르는 우선순위**로만 쓴다(§계약: 문자열 대조는 지표 불가).
PROX_BANDS = [(0.6, "100%"), (0.4, "82%"), (0.2, "40%"), (0.0, "19%")]
PROX_SUSPECT = 0.4   # 이 이상인데 계상 안 됐으면 눈으로 볼 값어치가 있다
PROX_GRAY = (0.3, 0.5)  # H2 전이 구간 — 검출이 갈리기 시작하는 곳


@app.get("/api/audit/{issue_id}/{run_id}")
def api_audit(issue_id: str, run_id: str) -> dict:
    """판정 ↔ 원문 대조 노드 — 판정 셀 옆에 **그 라운드 전원 발화 전문**을 놓는다.

    왜 별도 뷰인가: 생존 매트릭스는 status 만, 전기(biography)는 **판정기가 센 화자만**
    보여준다. 그런데 7/29 대조에서 나온 것은 정확히 그 반대편이다 — 말했는데 안 세어진
    화자(esa_03 stage2: 5명이 발화했는데 unmentioned). 세어진 쪽만 보면 영원히 안 보인다.
    그래서 이 뷰는 counted/uncounted 를 가르지 않고 그 라운드 발화를 **전문 그대로** 싣고,
    판정 결과를 그 옆에 붙인다.

    근접도(문자 3-gram containment)는 **판정이 아니라 시선 유도**다. 계약(SCHEMA_v0.3_NOTE_SLOT
    §4)이 문자열 대조를 지표로 쓰는 것을 기각했으므로 여기서도 지표가 아니며, "먼저 볼 셀"을
    고르는 데만 쓴다. 어휘만 바꿔도 0.641로 떨어지므로 낮은 값이 부재의 증거가 되지 않는다.

    읽기 전용·LLM 0 (뷰어 경계 원칙). 산출물은 아무것도 쓰지 않는다.
    """
    jpath = paths.judgment(issue_id, run_id)
    if not jpath.exists():
        raise HTTPException(status_code=404, detail=f"judgment 없음 — 대조는 판정 이후 ({issue_id}/{run_id})")
    try:
        judgment = json.loads(jpath.read_text(encoding="utf-8"))
        facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
        events = [json.loads(ln) for ln
                  in paths.debate(issue_id, run_id).read_text(encoding="utf-8").splitlines()
                  if ln.strip()]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"산출물 없음: {e}")

    agent_persp: dict[str, str] = {}
    assignment: dict | None = None
    try:
        assignment = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
        for ag in assignment.get("agents", []):
            agent_persp[ag["agent_id"]] = ag.get("perspective") or "?"
    except FileNotFoundError:
        pass

    # 근거 등급 — access_window 계기를 그대로 소비한다(뷰어에서 재구현하지 않는다).
    # 판정 셀 옆에 "이 셀이 무엇에 기대고 있는가"를 붙이는 것이 이 뷰의 절반이다:
    # literal=원문 대조 / judged=판정 매개 / undefined=정의 밖(수첩). 계기가 산출을
    # 거부한 run(status=suspended)이면 그 사실을 그대로 싣는다 — 숨기면 뷰어가
    # 계기의 정지를 무력화한다.
    ev_by: dict[tuple, dict] = {}
    access_meta: dict | None = None
    if assignment is not None:
        try:
            from modules import access_window as aw
            arep = aw.report(judgment, assignment, events)
            for rec in arep["records"]:
                for t in rec["timeline"]:
                    ev_by[(rec["fact_id"], t["round"])] = t
            s = arep.get("summary") or {}
            access_meta = {
                "status": arep["status"],
                "window_source": arep["meta"]["window"]["window_source"],
                "evidence_mix": s.get("evidence_mix"),
                "judged_share": (s.get("self_diagnostic") or {}).get("judged_share"),
                "resurgence_rate": (s.get("self_diagnostic") or {}).get("resurgence_rate"),
                "note": arep["meta"]["evidence"]["note"],
            }
        except Exception as e:   # 계기 실패는 조용히 넘기지 않고 화면에 싣는다
            access_meta = {"status": "unavailable", "note": f"접근 창 계산 실패: {e}"}

    # 라운드별 발화 전문 — 한 번만 싣고 팩트별로는 좌표만 참조한다(중복 전송 방지).
    utts_by_stage: dict[int, list[dict]] = {}
    for e in events:
        if e.get("event") != "utterance":
            continue
        utts_by_stage.setdefault(e.get("round"), []).append({
            "agent_id": e.get("agent_id"),
            "perspective": e.get("perspective") or agent_persp.get(e.get("agent_id")),
            "text": e.get("response_text") or "",
        })

    stage_recs = {s["stage"]: {f["fact_id"]: f for f in s.get("facts", [])}
                  for s in judgment.get("stages", [])}
    stages = sorted(stage_recs)

    out_facts, n_flagged = [], 0
    for f in facts_doc.get("facts", []):
        fid, ftext = f["fact_id"], f.get("text", "")
        cells = []
        for st in stages:
            rec = stage_recs[st].get(fid)
            if rec is None:
                continue
            counted = list(rec.get("agents_mentioning") or [])
            surv = rec.get("status") in SURVIVING
            prox = {u["agent_id"]: _containment(ftext, u["text"])
                    for u in utts_by_stage.get(st, [])}
            top = max(prox.items(), key=lambda kv: kv[1], default=(None, 0.0))
            votes = [v for v in (rec.get("votes") or []) if isinstance(v, dict)]
            vstat = [v.get("status") for v in votes]

            flags = []
            # ① 계상 안 됐는데 원문이 상당히 남은 발화가 있다 = 7/29 esa_03 유형
            if not surv and top[1] >= PROX_SUSPECT:
                flags.append("uncounted_high")
            # ② 살아는 있는데, 근접도가 높은 화자가 센 명단에서 빠졌다 = 화자 간 누락
            missed = [a for a, p in prox.items() if p >= PROX_SUSPECT and a not in counted]
            if surv and missed:
                flags.append("partial_count")
            # ③ 표가 갈렸다 (다수결이 가린 분열)
            if vstat and len(set(vstat)) > 1:
                flags.append("split")
            # ④ H2 전이 구간 — 검출이 갈리기 시작하는 근접도
            if PROX_GRAY[0] <= top[1] < PROX_GRAY[1]:
                flags.append("gray")
            n_flagged += 1 if flags else 0

            aw_row = ev_by.get((fid, st))
            cells.append({
                "stage": st, "status": rec.get("status"), "surviving": surv,
                "evidence": (aw_row or {}).get("evidence"),
                "access_state": (aw_row or {}).get("state"),
                "n_access_literal": (aw_row or {}).get("n_access_literal"),
                "counted": counted, "missed_high": missed,
                "prox": prox, "max_prox": top[1], "max_prox_agent": top[0],
                "votes": {
                    "n": len(vstat),
                    "split": None if not vstat else f"{max(vstat.count(s) for s in set(vstat))}/{len(vstat)}",
                    "unanimous": None if not vstat else len(set(vstat)) == 1,
                    "parse_fail": sum(1 for v in votes
                                      if str(v.get("reason", "")).startswith("parse_fail:")),
                },
                "flags": flags,
            })
        out_facts.append({"fact_id": fid, "text": ftext,
                          "critical": bool(f.get("critical")), "cells": cells})

    return {
        "issue_id": issue_id, "run_id": run_id, "stages": stages,
        "judge": judgment.get("judge"),
        "utterances": {str(k): v for k, v in sorted(utts_by_stage.items())},
        "facts": out_facts,
        "access": access_meta,
        "n_flagged_cells": n_flagged,
        "bands": [{"min": lo, "detect": d} for lo, d in PROX_BANDS],
        "note": ("근접도는 지표가 아니라 시선 유도다 — 어휘만 바꿔도 0.641로 떨어지므로 "
                 "낮은 값이 '안 말했다'의 증거가 되지 않는다(H2 실측). 표시는 어디를 먼저 "
                 "읽을지 고르는 용도이며, 판정은 사람이 원문을 읽고 한다."),
    }


@app.get("/biography", response_class=HTMLResponse)
def biography_page() -> str:
    return (HERE / "biography.html").read_text(encoding="utf-8")


@app.get("/ledger", response_class=HTMLResponse)
def ledger_page() -> str:
    return (HERE / "ledger.html").read_text(encoding="utf-8")


@app.get("/transmission", response_class=HTMLResponse)
def transmission_page() -> str:
    return (HERE / "transmission.html").read_text(encoding="utf-8")


@app.get("/audit", response_class=HTMLResponse)
def audit_page() -> str:
    return (HERE / "audit.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (HERE / "index.html").read_text(encoding="utf-8")
