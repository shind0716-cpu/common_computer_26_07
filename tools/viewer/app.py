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

import hashlib
import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response

from modules import access_window as aw
from modules import crossrun, paths, ledger, survival
from modules import transmission as tr
from modules.judge import SURVIVING
from modules.viewmodel import build_viewmodel, STATUS_ORDER

app = FastAPI(title="팩트 생존 뷰어")
HERE = Path(__file__).resolve().parent

# 파일럿 관측에서 세션 스크래치패드가 사라지자 데이터 뿌리를 바꿔 보는 방법도 함께
# 사라졌다. 읽기 전용 뷰어라 오염 경로가 없으므로 환경변수로 **뿌리만** 바꾸고,
# 파일명 규칙은 계속 paths.py 함수 하나를 쓴다. 상대 경로는 실행 cwd 기준으로 확정한다.
if os.environ.get("VIEWER_DATA"):
    paths.DATA = Path(os.environ["VIEWER_DATA"]).expanduser().resolve()


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


def _run_meta(issue_id: str, run_id: str) -> dict | None:
    """debate 로그 첫 이벤트의 run_meta (스키마 v0.3 §4‴). 구 로그면 None.

    조건 좌표(설정 사전 8축)를 로그에서 그대로 읽는다 — run_id 문자열이나 config 파일명에서
    추측하지 않는다. 추측이 바로 이 이벤트가 없애려던 문제다.
    """
    p = paths.debate(issue_id, run_id)
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            return None
        return ev if ev.get("event") == "run_meta" else None
    return None


def _is_unvetted(*docs: dict | None) -> bool:
    """서로 독립 저장된 source/judgment 중 하나라도 development-only면 True."""
    policies = [doc for doc in docs if isinstance(doc, dict)]
    tiers = {doc.get("promotion_tier") for doc in policies
             if doc.get("promotion_tier") is not None}
    if "pilot_unvetted" in tiers or len(tiers) > 1:
        return True
    for doc in policies:
        for key in ("aggregate_eligible", "report_eligible"):
            if key in doc and (not isinstance(doc[key], bool) or doc[key] is False):
                return True
    return False


def _available_runs(include_unvetted: bool = False) -> list[dict]:
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
        # 조건 좌표 — run_meta(스키마 v0.3 §4‴)가 있으면 로그에서 읽는다. 없으면 null:
        # run 이름에서 조건을 추측하지 않는다(그게 애초에 없애려던 문제다).
        meta = _run_meta(issue_id, run_id)
        judgment_doc = None
        if parts["judgment"] == "present":
            try:
                loaded = json.loads(paths.judgment(issue_id, run_id).read_text(encoding="utf-8"))
                judgment_doc = loaded if isinstance(loaded, dict) else None
            except Exception:
                judgment_doc = None
        unvetted = _is_unvetted(meta, judgment_doc)
        if unvetted and not include_unvetted:
            continue
        item = {
            "issue_id": issue_id, "run_id": run_id, "title": _issue_title(issue_id),
            "run_state": run_state, "parts": parts,
            "condition": (meta or {}).get("condition"),
            "settings": (meta or {}).get("settings"),
            "config_ref": (meta or {}).get("config_ref"),
            "promotion_tier": ((meta or {}).get("promotion_tier")
                               or (judgment_doc or {}).get("promotion_tier")),
            "unvetted": unvetted,
            "stage_type": None, "judge": None, "n_stages": None, "far_system": None,
        }
        if parts["judgment"] == "present":
            try:
                jd = judgment_doc or {}
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
def api_runs(include_unvetted: bool = False) -> dict:
    return {"runs": _available_runs(include_unvetted=include_unvetted)}


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
            "note": ("이 판은 장부를 끈 판이라 다시 넣은 적이 없다. 아래 목록은 "
                     "'장부를 켰다면 다시 넣었을 팩트'다."
                     if not injections else
                     "아래 문구는 실제로 입력에 넣은 원문 그대로다(로그에 남아 있다)."
                     if all(i["block_text_source"] == "injected_text" for i in injections)
                     else "아래 문구는 넣었을 내용을 되짚어 만든 것이다 — 이 로그는 옛 판본 "
                          "산출물이라 실제로 넣은 원문이 저장돼 있지 않다(원문 저장은 v0.3부터).")}


@app.get("/api/inputs/{issue_id}/{run_id}")
def api_inputs(issue_id: str, run_id: str) -> dict:
    """입력 전문 뷰 — 그 라운드에 그 참가자가 **말하기 전에 본 것 전문**.

    왜 필요한가: 로그는 출력(발화)은 전문 보존하지만 입력은 `prompt_hash` 하나였다. 해시는
    위조 검증만 되고 복원은 안 되므로, "무엇을 보고 저 말을 했나"는 사람이 확인할 길이
    없었다. 스키마 v0.3 의 `prompt_assembly`(조립 명세) + `ledger_inject.injected_text`
    (재주입 원문)가 그 구멍을 메운다 — 이 노드는 그 두 이벤트를 사람이 읽는 화면으로 옮긴다.

    재조립은 **validate.reassemble_prompt() 한 벌만** 쓴다. 뷰어에서 조립 문자열을 다시
    짜면 엔진이 바뀔 때 조용히 어긋나고, 그 어긋남을 잡는 것이 v0.3 검증 계약의 목적이라
    자기 계약을 무력화하는 짓이 된다. 재조립분의 sha256 을 `prompt_hash` 와 대조해
    `hash_match` 로 싣는다 — 화면이 "이 전문이 그때 그것과 같다"를 스스로 증명한다.

    구 로그(v0.2)에는 `prompt_assembly` 가 없다. 그 경우 조립 명세가 없다는 사실을 그대로
    싣고(status="absent") 재구성을 시도하지 않는다 — 없는 기록을 그럴듯하게 지어내면
    이 뷰가 메우려던 구멍이 더 깊어진다.

    수첩(`note_text`)이 생기면 같은 자리에 슬롯 하나로 붙는다(계약 SCHEMA_v0.3_NOTE_SLOT).
    읽기 전용·LLM 0.
    """
    dpath = paths.debate(issue_id, run_id)
    if not dpath.exists():
        raise HTTPException(status_code=404, detail=f"debate 로그 없음 ({issue_id}/{run_id})")
    events = [json.loads(ln) for ln in dpath.read_text(encoding="utf-8").splitlines()
              if ln.strip()]
    pas = [e for e in events if e.get("event") == "prompt_assembly"]
    utts = {(e.get("round"), e.get("agent_id")): e
            for e in events if e.get("event") == "utterance"}

    if not pas:
        return {
            "issue_id": issue_id, "run_id": run_id, "status": "absent",
            "rounds": sorted({r for r, _ in utts}), "items": [],
            "note": ("이 로그에는 입력 조립 기록(prompt_assembly)이 없습니다 — 스키마 v0.2 "
                     "시절 산출물입니다. 입력은 prompt_hash(지문)만 남아 있어 복원할 수 "
                     "없고, 뷰어는 없는 기록을 추측해 채우지 않습니다. v0.3 로그(엔진 "
                     "2026-07-28 이후 실행)부터 이 화면이 채워집니다."),
        }

    try:
        issue_doc = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
        facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"형제 산출물 없음: {e}")

    from modules import validate as vd
    ctx = vd.replay_context(events, issue_doc=issue_doc, facts_doc=facts_doc)
    injects = {e.get("round"): e for e in events if e.get("event") == "ledger_inject"}
    fact_by_id = ctx["fact_by_id"]

    items, n_ok, n_fail = [], 0, 0
    for pa in pas:
        rd, ag = pa.get("round"), pa.get("agent_id")
        slots = pa.get("slots") or {}
        text, err = None, None
        try:
            text = vd.reassemble_prompt(pa, ctx, where=f"round {rd} · {ag}")
        except vd.ReplayError as e:
            err = str(e)
        except Exception as e:      # 저자 저장소 부재 등 환경 사유 — 화면에 사유를 싣는다
            err = f"재조립 불가(환경): {e}"
        digest = (hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None)
        stored = pa.get("prompt_hash")
        match = (digest == stored) if digest else None
        n_ok += 1 if match else 0
        n_fail += 1 if match is False else 0

        inj = injects.get((slots.get("inject") or {}).get("round")) if slots.get("inject") else None
        u = utts.get((rd, ag)) or {}
        items.append({
            "round": rd, "agent_id": ag, "template": pa.get("template"),
            "prompt_ver": pa.get("prompt_ver"), "setting_key": pa.get("setting_key"),
            # 슬롯 = 이 입력이 무엇으로 조립됐는지의 좌표. 화면은 이 좌표를 사람 말로 옮긴다.
            "slots": {
                "assigned_facts": [{"fact_id": f, "text": fact_by_id.get(f, "")}
                                   for f in (slots.get("assigned_fact_ids") or [])],
                "others": slots.get("others") or [],
                "previous": slots.get("previous"),
                "inject": slots.get("inject"),
            },
            "inject_text": (inj or {}).get("injected_text"),
            "inject_fact_ids": (inj or {}).get("injected_fact_ids") or [],
            "prompt_hash": stored,
            "hash_match": match,          # True=그때 보낸 것과 동일 확인 / False=오염 / None=재조립 실패
            "text": text,
            "error": err,
            "response_text": u.get("response_text"),   # 이 입력으로 나온 발화(바로 옆에 놓는다)
        })

    return {
        "issue_id": issue_id, "run_id": run_id, "status": "ok",
        "rounds": sorted({i["round"] for i in items}),
        "agents": sorted({i["agent_id"] for i in items}),
        "items": items,
        "n_verified": n_ok, "n_mismatch": n_fail,
        "note": ("입력 전문은 조립 명세(prompt_assembly)대로 되살린 것이며, 되살린 전문의 "
                 "지문이 그때 저장된 지문(prompt_hash)과 같은지 함께 표시합니다 — 같다면 "
                 "이 화면의 글자가 그때 모델이 실제로 받은 글자입니다. 재주입 블록만은 "
                 "복원이 아니라 로그에 저장된 원문 그대로입니다."),
    }


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


# 근접도 임계값 — **어디를 먼저 볼지 고르는 우선순위**로만 쓴다(§계약: 문자열 대조는 지표 불가).
#
# [폐기 2026-07-30 · 요한 판단] 구간별 판정기 검출률 표(PROX_BANDS: 0.6→100% … 0→19%)를
# 화면에서 지웠다. 그 값은 2026-07-29 H2(experiments/instrument_check, 판정기 gpt-5.4-mini)
# **한 실험의 관측**인데 대조 화면이 **모든 run 옆에** "실측"으로 붙였다. 지금 뷰어에 뜨는
# run 만 해도 판정기가 갈린다(파일럿 gpt-5.4-mini vs dryrun2·fixture_v03 offline-stub —
# 부분일치 판정기는 구조적으로 검출률이 100%에 가깝다). 조건이 다른 곡선을 그 run 의
# 성질처럼 보이게 하는 표시였다. 값이 필요하면 그 실험의 산출물을 직접 읽을 것.
#
# 아래 두 임계값은 남긴다 — 표시가 아니라 **플래그 계산**에 쓰이고, 화면이 "지표가 아니라
# 시선 유도"임을 문면으로 밝힌다. 출처는 같은 H2 실험이므로 다른 조건에서는 경계가 다를 수
# 있다(그래서 이 값으로 run 간 비교를 하지 않는다).
#
# ⚠ 조건 주의 — 장부(재주입)를 켠 팔과 끈 팔의 근접도를 그냥 비교하면 안 된다.
# 장부는 팩트 원문을 그대로 다시 넣으므로 그 뒤 발화가 원문에 가까워진다(H3 실측:
# 주입 경험 팩트 0.769 vs 미주입 0.504). 닳아가던 것이 리셋되는 것이라, 팔 간 차이의
# 일부가 현상이 아니라 주입의 산물이다.
PROX_SUSPECT = 0.4   # 이 이상인데 계상 안 됐으면 눈으로 볼 값어치가 있다
PROX_GRAY = (0.3, 0.5)  # 검출이 갈리기 시작하는 구간(같은 H2 실험 관측)


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
    고르는 데만 쓴다. 어휘만 바꿔도 크게 떨어지므로(H2 실측 0.641 — 2026-07-29
    experiments/instrument_check, 그 조건의 값이다) 낮은 값이 부재의 증거가 되지 않는다.

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
    agent_ids: list[str] = []
    try:
        assignment = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
        for ag in assignment.get("agents", []):
            agent_persp[ag["agent_id"]] = ag.get("perspective") or "?"
            agent_ids.append(ag["agent_id"])
    except FileNotFoundError:
        pass

    # 접근 참가자는 access_window 계기의 산출을 stage 좌표로 옮기기만 한다. acc 키는
    # stage 값이 아니라 rounds 안의 위치 인덱스이므로 rounds[idx]로 명시적으로 사상한다.
    access_by_coord: dict[tuple, list[str]] = {}
    if assignment is not None:
        rounds, mentions = tr.mention_map(judgment)
        acc, _lit, _meta = aw.access_sets(rounds, mentions, assignment, events)
        facts_at_stage = {stage["stage"]: stage.get("facts", [])
                          for stage in judgment.get("stages", [])}
        for idx, stage in enumerate(rounds):
            for fact in facts_at_stage.get(stage, []):
                fact_id = fact["fact_id"]
                access_by_coord[(fact_id, stage)] = [
                    a for a in agent_ids if fact_id in acc[idx].get(a, set())
                ]

    # 근거 등급 — access_window 계기를 그대로 소비한다(뷰어에서 재구현하지 않는다).
    # 판정 셀 옆에 "이 셀이 무엇에 기대고 있는가"를 붙이는 것이 이 뷰의 절반이다:
    # literal=원문 대조 / judged=판정 매개 / undefined=정의 밖(수첩). 계기가 산출을
    # 거부한 run(status=suspended)이면 그 사실을 그대로 싣는다 — 숨기면 뷰어가
    # 계기의 정지를 무력화한다.
    ev_by: dict[tuple, dict] = {}
    access_meta: dict | None = None
    if assignment is not None:
        try:
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
                "access_agents": access_by_coord.get((fid, st), []),
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

    # 이 판의 소실률(FAR) — 판정물 summary 에 이미 있는 값을 그대로 싣는다(재계산 금지).
    # 왜 대조 화면에 붙이나: 격자는 셀 하나하나만 보여줘서, 화면만 보면 "이 판이 전체로
    # 얼마나 사라졌나"를 지나치게 된다(실제로 7/30 파일럿 관측에서 FAR 확인을 건너뛰었다).
    # 잣대는 격자의 ●/○ 와 같은 judge.SURVIVING 단일 소스라 두 수치가 어긋날 수 없다.
    summ = judgment.get("summary") or {}
    far = {
        "by_stage": summ.get("far_by_stage"),
        "final": summ.get("far_system"),
        "final_critical": summ.get("far_critical"),
        "note": ("격자의 ○ 와 같은 잣대(judge.SURVIVING)로 센 비율이다. 단 전체 FAR 은 "
                 "아직 등장할 차례가 안 온 팩트까지 소실로 세는 구간이 있어(survival.py) "
                 "'새로 사라진 비율'(조건부 hazard)과 같이 읽어야 한다."),
    }

    return {
        "issue_id": issue_id, "run_id": run_id, "stages": stages,
        "judge": judgment.get("judge"),
        "utterances": {str(k): v for k, v in sorted(utts_by_stage.items())},
        "facts": out_facts,
        "access": access_meta,
        "far": far,
        "n_flagged_cells": n_flagged,
        "note": ("근접도는 지표가 아니라 어디를 먼저 볼지 고르는 표시다. 같은 뜻을 다른 말로 "
                 "바꿔 쓰기만 해도 크게 떨어지므로, 낮은 값이 '안 말했다'의 증거가 되지는 "
                 "않는다. 판정은 사람이 발화 원문을 읽고 한다."),
    }


def _pair_record(issue_id: str, run_id: str) -> dict:
    """기존 재료 API 셋을 판 간 계층 입력 한 판으로 얕게 조립한다."""
    audit = api_audit(issue_id, run_id)
    ledger_view = api_ledger(issue_id, run_id)
    analysis = api_analysis(issue_id, run_id)
    cells = []
    fact_meta = []
    for fact in audit["facts"]:
        fact_meta.append({k: fact.get(k) for k in ("fact_id", "text", "critical")})
        for cell in fact["cells"]:
            cells.append({"fact_id": fact["fact_id"], **cell})
    injections = [{
        "round": inj["round"],
        "fact_ids": [f["fact_id"] for f in inj["injected"]],
        "reason": inj["reason"], "block_text": inj["block_text"],
        "block_text_source": inj["block_text_source"],
    } for inj in ledger_view["injections"]]
    events = [json.loads(line) for line in
              paths.debate(issue_id, run_id).read_text(encoding="utf-8").splitlines()
              if line.strip()]
    try:
        assignment = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
        agent_ids = [ag["agent_id"] for ag in assignment.get("agents", [])]
    except FileNotFoundError:
        agent_ids = []
    edges, edge_meta = tr.edges_map(events, agent_ids)
    seating = next((ev for ev in events if ev.get("event") == "seating"), None)
    order = list(seating.get("order") or []) if seating is not None else list(agent_ids)
    topology = {
        "structure": edge_meta["structure"],
        "order": order,
        "edges": {agent_id: sorted(neighbors) for agent_id, neighbors in edges.items()},
        "assumed_full": edge_meta["assumed_full"],
    }
    access = audit.get("access") or {}
    judgment_policy = {}
    try:
        judgment_doc = json.loads(paths.judgment(issue_id, run_id).read_text(encoding="utf-8"))
        if isinstance(judgment_doc, dict):
            judgment_policy = {key: judgment_doc[key] for key in
                               ("promotion_tier", "aggregate_eligible", "report_eligible")
                               if key in judgment_doc}
    except (FileNotFoundError, ValueError, OSError):
        # _pair_record의 순수 조립 테스트와 구 legacy 판정은 policy 필드가 없다.
        # 실제 malformed judgment는 앞선 api_audit가 이미 거부한다.
        judgment_policy = {}
    return {
        "run_id": run_id, "judge": audit["judge"], "far": audit["far"],
        "ledger_mode": ledger_view["ledger_mode"],
        "topology": topology,
        "cells": cells, "facts": fact_meta, "injections": injections,
        "evidence": {
            "evidence_mix": access.get("evidence_mix"),
            "window_source": access.get("window_source"),
            "judged_share": access.get("judged_share"),
            "resurgence_rate": access.get("resurgence_rate"),
            "status": access.get("status"),
            # 계기가 집계를 멈춘 사유(access_window status=suspended). 화면이 그 정지를
            # 침묵하지 않도록 문면을 그대로 넘긴다 — 뷰어가 사유를 새로 쓰지 않는다.
            "note": access.get("note"),
        },
        "run_meta": _run_meta(issue_id, run_id),
        "judgment_policy": judgment_policy,
        "analysis": analysis["report"],
        # 발화 전문은 audit 산출을 그대로 싣는다. crossrun은 읽거나 가공하지 않는다.
        "utterances": audit["utterances"],
    }


@app.get("/api/pair/{issue_id}/{run_a}/{run_b}")
def api_pair(issue_id: str, run_a: str, run_b: str) -> dict:
    """두 판의 기존 API 산출을 조립해 crossrun.report()에 넘긴다(새 계산 0)."""
    try:
        records = [_pair_record(issue_id, run_a), _pair_record(issue_id, run_b)]
    except HTTPException:
        raise
    try:
        out = crossrun.report(records)
    except crossrun.CrossRunError as e:
        raise HTTPException(status_code=500, detail=f"판 간 대조 실패(형태 드리프트?): {e}") from e
    out.update({"issue_id": issue_id, "data_root": str(paths.DATA), "records": records})
    return out


@app.get("/biography", response_class=HTMLResponse)
def biography_page() -> str:
    return (HERE / "biography.html").read_text(encoding="utf-8")


@app.get("/audit", response_class=HTMLResponse)
def audit_page() -> str:
    return (HERE / "audit.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def pair_page() -> str:
    return (HERE / "pair.html").read_text(encoding="utf-8")


# [폐기 2026-07-30 · 요한 판단] /terms.js 용어층 — 고치기보다 지웠다.
# 사유: run 과 무관한 정적 층 하나로 5개 화면을 덮으려다 **조건 의존 수치를 조건 비의존
# 정의처럼** 실었다(prox 0.641 · gray 0.3~0.5 · resurgence "실측 5건"). 화면은 run 마다
# 판정기·조건이 다른데 문면은 하나였다. 출처를 값과 함께 내려보내고 조건이 다르면 접는
# 기계를 새로 짓는 대안은 기각 — 틀린 표시를 관리하는 장치가 늘 뿐이고 그 장치도 틀린다.
# 화면 문면은 각 면이 자기 낱말을 직접 쓴다(중복을 감수하고 조건 혼입을 막는 쪽).
