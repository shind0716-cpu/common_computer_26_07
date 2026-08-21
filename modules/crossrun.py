"""판 간 대조 계층 — 두 판의 층1 산출을 좌표로만 맞춘다.

이 모듈은 순수 함수만 제공한다(파일 쓰기 0 · LLM 0). 입력은 survival,
access_window, ledger와 뷰어의 audit 산출을 얕게 조립한 판 레코드 두 개다. 로그를
다시 파싱하거나 근접도·FAR를 다시 계산하지 않는다.

중요 경계: 이 계층은 새 비율을 정의하지 않는다. FAR은 판정물 summary에서 받은 값을
그대로 옮기고, 나머지는 개수·목록·좌표만 낸다. 새 비율은 조건 의존인데 정적 화면에
조건 비의존 값처럼 실리기 쉽다(2026-07-30 용어층 폐기에서 확인한 실패). 형태가
드리프트하면 조용히 0을 만들지 않고 CrossRunError로 멈춘다.
"""
from __future__ import annotations

from typing import Any


class CrossRunError(ValueError):
    """판 레코드가 대조 계약을 충족하지 않을 때 발생한다."""


def _records(records: list[dict]) -> tuple[dict, dict]:
    if not isinstance(records, list) or len(records) != 2:
        raise CrossRunError("판 간 대조에는 판 레코드가 정확히 2개 필요합니다")
    if not all(isinstance(r, dict) for r in records):
        raise CrossRunError("판 레코드는 객체여야 합니다")
    ids = [r.get("run_id") for r in records]
    if not all(isinstance(x, str) and x for x in ids) or ids[0] == ids[1]:
        raise CrossRunError("서로 다른 비어 있지 않은 run_id 2개가 필요합니다")
    required = ("judge", "far", "cells", "injections", "evidence", "run_meta", "topology")
    for rec in records:
        missing = [k for k in required if k not in rec]
        if missing:
            raise CrossRunError(f"{rec.get('run_id')}: 필수 키 없음: {', '.join(missing)}")
        if not isinstance(rec["judge"], dict) or not isinstance(rec["far"], dict):
            raise CrossRunError(f"{rec['run_id']}: judge/far는 객체여야 합니다")
        if not isinstance(rec["cells"], list) or not isinstance(rec["injections"], list):
            raise CrossRunError(f"{rec['run_id']}: cells/injections는 목록이어야 합니다")
        topology = rec["topology"]
        if not isinstance(topology, dict):
            raise CrossRunError(f"{rec['run_id']}: topology는 객체여야 합니다")
        topo_need = ("structure", "order", "edges", "assumed_full")
        topo_absent = [k for k in topo_need if k not in topology]
        if topo_absent:
            raise CrossRunError(
                f"{rec['run_id']}: topology 필수 키 없음: {', '.join(topo_absent)}")
        if (topology["structure"] not in {"full", "line", "tree"}
                or not isinstance(topology["order"], list)
                or not all(isinstance(x, str) for x in topology["order"])
                or not isinstance(topology["edges"], dict)
                or not all(isinstance(k, str) and isinstance(v, list)
                           and all(isinstance(x, str) for x in v)
                           for k, v in topology["edges"].items())
                or not isinstance(topology["assumed_full"], bool)):
            raise CrossRunError(f"{rec['run_id']}: topology 형태가 올바르지 않습니다")
        for i, cell in enumerate(rec["cells"]):
            need = ("fact_id", "stage", "status", "surviving", "counted", "flags",
                    "max_prox", "max_prox_agent", "votes", "access_agents")
            absent = [k for k in need if k not in cell]
            if absent:
                raise CrossRunError(
                    f"{rec['run_id']}: cells[{i}] 필수 키 없음: {', '.join(absent)}")
            if not isinstance(cell["surviving"], bool):
                raise CrossRunError(f"{rec['run_id']}: cells[{i}].surviving은 bool이어야 합니다")
            if not isinstance(cell["access_agents"], list):
                raise CrossRunError(f"{rec['run_id']}: cells[{i}].access_agents는 목록이어야 합니다")
        for i, inj in enumerate(rec["injections"]):
            need = ("round", "fact_ids", "reason", "block_text", "block_text_source")
            absent = [k for k in need if k not in inj]
            if absent:
                raise CrossRunError(
                    f"{rec['run_id']}: injections[{i}] 필수 키 없음: {', '.join(absent)}")
    return records[0], records[1]


def _cell_maps(pair: tuple[dict, dict]) -> list[dict[tuple[Any, Any], dict]]:
    maps = []
    for rec in pair:
        m: dict[tuple[Any, Any], dict] = {}
        for cell in rec["cells"]:
            coord = (cell["fact_id"], cell["stage"])
            if coord in m:
                raise CrossRunError(f"{rec['run_id']}: 중복 셀 좌표 {coord}")
            m[coord] = cell
        maps.append(m)
    if set(maps[0]) != set(maps[1]):
        only_a = sorted(set(maps[0]) - set(maps[1]), key=str)
        only_b = sorted(set(maps[1]) - set(maps[0]), key=str)
        raise CrossRunError(f"두 판의 셀 좌표가 다릅니다: 첫 판만={only_a}, 둘째 판만={only_b}")
    return maps


def _cell_view(cell: dict) -> dict:
    return {
        "status": cell["status"], "surviving": cell["surviving"],
        "counted": cell["counted"], "n_counted": len(cell["counted"]),
        "access_agents": cell["access_agents"], "n_access": len(cell["access_agents"]),
        "flags": cell["flags"], "max_prox": cell["max_prox"],
        "max_prox_agent": cell["max_prox_agent"], "votes": cell["votes"],
    }


def divergences(records: list[dict]) -> list[dict]:
    """surviving 값이 갈리는 셀을 좌표와 양쪽 판별 근거 그대로 반환한다."""
    pair = _records(records)
    maps = _cell_maps(pair)
    out = []
    for fact_id, stage in sorted(maps[0], key=lambda x: (str(x[0]), x[1])):
        a, b = maps[0][(fact_id, stage)], maps[1][(fact_id, stage)]
        if a["surviving"] == b["surviving"]:
            continue
        out.append({
            "fact_id": fact_id, "stage": stage,
            "runs": {pair[0]["run_id"]: _cell_view(a), pair[1]["run_id"]: _cell_view(b)},
        })
    return out


def _intervention_rounds(rec: dict, fact_id: str) -> list:
    return sorted({inj["round"] for inj in rec["injections"]
                   if fact_id in inj["fact_ids"]})


def fact_rows(records: list[dict]) -> list[dict]:
    """갈린 칸이 하나라도 있는 팩트를 좌표로 분해한다. 판정은 하지 않는다."""
    pair = _records(records)
    maps = _cell_maps(pair)
    stages = sorted({stage for _, stage in maps[0]})
    if not stages:
        raise CrossRunError("대조할 셀이 없습니다")
    final = stages[-1]
    ds = divergences(list(pair))
    by_fact: dict[str, list[dict]] = {}
    for d in ds:
        by_fact.setdefault(d["fact_id"], []).append(d)
    out = []
    for fact_id in sorted(by_fact, key=str):
        fact_ds = by_fact.get(fact_id, [])
        divergent_stages = sorted(d["stage"] for d in fact_ds)
        first = divergent_stages[0]
        runs = {}
        for idx, rec in enumerate(pair):
            final_cell = maps[idx][(fact_id, final)]
            first_cell = maps[idx][(fact_id, first)]
            runs[rec["run_id"]] = {
                "final": {
                    "surviving": final_cell["surviving"],
                    "status": final_cell["status"],
                    "n_counted": len(final_cell["counted"]),
                    "n_access": len(final_cell["access_agents"]),
                },
                "first_divergence": {
                    "status": first_cell["status"],
                    "surviving": first_cell["surviving"],
                    "flags": first_cell["flags"],
                    "max_prox": first_cell["max_prox"],
                    "max_prox_agent": first_cell["max_prox_agent"],
                    "n_counted": len(first_cell["counted"]),
                    "n_access": len(first_cell["access_agents"]),
                },
                "intervention_rounds": _intervention_rounds(rec, fact_id),
            }
        out.append({
            "fact_id": fact_id, "final_stage": final,
            "divergent_stages": divergent_stages,
            "first_divergence_stage": first,
            "runs": runs,
        })
    return out


def _far_at(rec: dict, stage: Any) -> Any:
    rows = rec["far"].get("by_stage")
    if not isinstance(rows, list):
        raise CrossRunError(f"{rec['run_id']}: far.by_stage는 목록이어야 합니다")
    row = next((x for x in rows if isinstance(x, dict) and x.get("stage") == stage), None)
    if row is None:
        return None
    return row.get("far_system", row.get("far"))


def timeline(records: list[dict]) -> list[dict]:
    """라운드축에 판정물 FAR 통과값·주입 사건·갈린 셀 개수를 놓는다."""
    pair = _records(records)
    ds = divergences(list(pair))
    stages = sorted({c["stage"] for rec in pair for c in rec["cells"]})
    rows = []
    for stage in stages:
        runs = {}
        for rec in pair:
            injections = [inj for inj in rec["injections"] if inj["round"] == stage]
            transition = next((x for x in (rec.get("analysis") or {}).get("transitions", [])
                               if x.get("to_stage") == stage), None)
            runs[rec["run_id"]] = {
                "far": _far_at(rec, stage),
                "hazard": None if transition is None else transition.get("cond_attrition"),
                "injections": injections,
            }
        rows.append({"stage": stage, "runs": runs,
                     "n_divergent_cells": sum(1 for d in ds if d["stage"] == stage)})
    return rows


def dependencies(records: list[dict]) -> dict:
    """화면 숫자가 기대는 근거 구성·판정기·표 갈림·resurgence를 판별 없이 모은다."""
    pair = _records(records)
    out = {}
    for rec in pair:
        ev = rec["evidence"]
        if not isinstance(ev, dict):
            raise CrossRunError(f"{rec['run_id']}: evidence는 객체여야 합니다")
        out[rec["run_id"]] = {
            "evidence_mix": ev.get("evidence_mix"),
            "judged_share": ev.get("judged_share"),
            "resurgence_rate": ev.get("resurgence_rate"),
            "status": ev.get("status"),
            "judge": rec["judge"],
            "split_cells": sum(1 for c in rec["cells"] if "split" in c["flags"]),
        }
    return {"runs": out}


def _report_eligible(rec: dict) -> bool:
    """Source run_meta와 judgment policy 중 더 제한적인 provenance를 따른다."""
    docs = [doc for doc in (rec.get("run_meta"), rec.get("judgment_policy"))
            if isinstance(doc, dict)]
    tiers = {doc.get("promotion_tier") for doc in docs
             if doc.get("promotion_tier") is not None}
    if "pilot_unvetted" in tiers or len(tiers) > 1:
        return False
    for doc in docs:
        if "report_eligible" in doc:
            value = doc["report_eligible"]
            if not isinstance(value, bool) or value is False:
                return False
    return True


def report(records: list[dict]) -> dict:
    """판 간 좌표 대조 결과를 한 페이로드로 묶는다.

    두 판의 조건 일치는 판정하지 않는다 — 값을 나란히 싣고 사람이 본다.
    """
    pair = _records(records)
    ineligible = [rec["run_id"] for rec in pair if not _report_eligible(rec)]
    if ineligible:
        raise CrossRunError(
            "report-ineligible development artifact excluded: " + ", ".join(ineligible))
    maps = _cell_maps(pair)  # 형태 드리프트를 모든 진입점에서 먼저 검출
    stages = sorted({stage for _, stage in maps[0]})
    return {
        "shape": {
            "stages": stages,
            "n_facts": len({fact_id for fact_id, _ in maps[0]}),
            "n_agents": {r["run_id"]: len(r["topology"]["edges"]) for r in pair},
            "n_rounds": len(stages),
        },
        "scope": {
            "runs": [{"run_id": r["run_id"], "judge": r["judge"],
                      "ledger_mode": r.get("ledger_mode"), "run_meta": r["run_meta"],
                      "topology": r["topology"], "far": r["far"]} for r in pair],
        },
        "divergences": divergences(list(pair)),
        "fact_rows": fact_rows(list(pair)),
        "timeline": timeline(list(pair)),
        "dependencies": dependencies(list(pair)),
    }
