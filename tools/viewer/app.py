"""[요한 · 관측 레이어 트랙] FastAPI 뷰어 어댑터 (카와이 판).

설계 §2 경계 원칙 준수: 읽기 전용 — 어떤 산출물도 쓰지 않고, LLM 호출 0.
민옥의 modules.viewmodel.build_viewmodel() 을 **그대로 소비**한다(계약 재사용,
뷰어 전용 모델 이중정의 없음). make_viewer.py(정적 생성)와 형제 어댑터 —
같은 뷰모델을 먹고 화면 자산을 공유한다.

FastAPI 어댑터의 실익(정적 생성 대비): run 목록/브라우징 + 라이브 파일시스템 직독
(새 run 이 빌드 없이 등장). run 목록은 data/judgments 를 스캔해 build_viewmodel 이
필요로 하는 4파일(issue·facts·judgment·debate)이 모두 있는 것만 노출.

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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (HERE / "index.html").read_text(encoding="utf-8")
