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
from modules.viewmodel import build_viewmodel

app = FastAPI(title="팩트 생존 뷰어")
HERE = Path(__file__).resolve().parent


def _issue_title(issue_id: str) -> str:
    try:
        return json.loads(paths.issue(issue_id).read_text(encoding="utf-8")).get("title", issue_id)
    except Exception:
        return issue_id


def _available_runs() -> list[dict]:
    """data/judgments 스캔 → build_viewmodel 4파일 세트가 완비된 run 만."""
    out: list[dict] = []
    jdir = paths.DATA / "judgments"
    if not jdir.exists():
        return out
    for jf in sorted(jdir.glob("judgment_*.json")):
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        issue_id, run_id = d.get("issue_id"), d.get("run_id")
        if not issue_id or not run_id:
            continue
        if not (paths.issue(issue_id).exists()
                and paths.facts(issue_id).exists()
                and paths.debate(issue_id, run_id).exists()):
            continue
        out.append({
            "issue_id": issue_id,
            "run_id": run_id,
            "title": _issue_title(issue_id),
            "stage_type": d.get("stage_type"),
            "judge": (d.get("judge") or {}).get("model"),
            "n_stages": len(d.get("stages", [])),
            "far_system": (d.get("summary") or {}).get("far_system"),
        })
    return out


@app.get("/api/runs")
def api_runs() -> dict:
    return {"runs": _available_runs()}


@app.get("/api/viewmodel/{issue_id}/{run_id}")
def api_viewmodel(issue_id: str, run_id: str) -> dict:
    try:
        return build_viewmodel(issue_id, run_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"산출물 없음: {e}")
    except Exception as e:  # 파싱 실패 = 스키마 드리프트 신호(설계 §3) → 화면에 노출
        raise HTTPException(status_code=500, detail=f"뷰모델 생성 실패(스키마 드리프트?): {e}")


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
