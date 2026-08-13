# -*- coding: utf-8 -*-
"""[접합 계층 · 요한] 비교 파일럿 실행 후 일회성 완전성 검사 — 0콜·읽기 전용.

지위: **탐색적 파일럿 운영 규칙의 '실행 후' 검사기** (요한 결정 8/11 — PREREG §9).
사전 코드 방어를 늘리는 대신, live 완주 뒤 이 스크립트 한 번으로 이슈별 상태를
판정한다. 이상한 이슈는 폐기(discard) 표시만 하고 고치지 않는다 — 후속 파일럿 몫.

검사 항목 (요한 지정 6항, 이슈별 판정):
  1. debate 발화가 정확히 기대 수(예: 32)인가
  2. (round, agent_id) 가 기대 수만큼의 고유 좌표인가 (중복·누락·예상 밖 검출)
  3. axis·stance 체크포인트가 각각 기대 행 수·고유 좌표인가
  4. parse failure 계수와 raw response 전량 보존 확인
  5. 논리 호출·전송 시도 원장 계수 (+콜당 $0.01 실측 기준 비용 추정)
  6. 산출물 sha256 기록
  7. axis·stance 각 행의 debate_sha256 == 현재 debate 파일 sha256 (8/13 추가 —
     판정 행이 지금 이 debate 원문 위에서 난 것인지의 결합 검사. 종전에는 판정 후
     debate 가 바뀌어도 OK 가 나왔다: C-8 출력 불변성의 실행 후 검사판)

사용 (live 완주 직후):
  PYTHONUTF8=1 python experiments/paper_repro/compare_postcheck.py \
    --issues issue_ethics_0543,issue_ethics_0248,issue_ethics_0262 \
    --run-prefix compare2 --config experiments/paper_repro/configs/compare_v2.yaml \
    --source-data experiments/paper_repro/data
결과는 사람용 표 출력 + data/compare_postcheck_{prefix}.json 저장(생성 즉시 커밋 — 규약 8).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from modules import paths  # noqa: E402

COST_PER_CALL = 0.01  # 실측 8/11 (콜당 ~$0.01) — 추정 표시용


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rows(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def _key_report(keys: list, expected: set) -> dict:
    return {"physical": len(keys), "unique": len(set(keys)),
            "expected": len(expected),
            "duplicates": sorted({str(k) for k in keys if keys.count(k) > 1}),
            "missing": sorted(str(k) for k in expected - set(keys)),
            "unexpected": sorted(str(k) for k in set(keys) - expected)}


def check_issue(issue_id: str, run_id: str, rounds: int) -> dict:
    out: dict = {"issue_id": issue_id, "run_id": run_id, "problems": []}
    prob = out["problems"].append

    assignment = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    expected = {(r, ag["agent_id"]) for r in range(rounds + 1)
                for ag in assignment["agents"]}

    # 1·2. debate 발화 수·좌표 집합
    dp = paths.debate(issue_id, run_id)
    if not dp.exists():
        prob(f"debate 부재: {dp.name}")
        out["verdict"] = "discard"
        return out
    utts = [e for e in _rows(dp) if e.get("event") == "utterance"]
    kr = _key_report([(u["round"], u["agent_id"]) for u in utts], expected)
    out["debate_keys"] = kr
    if not (kr["physical"] == kr["unique"] == kr["expected"]) or kr["missing"] \
            or kr["unexpected"]:
        prob(f"debate 좌표 집합 불일치: {kr}")

    # 3·4·7. axis·stance 체크포인트 행·좌표·parse·raw 보존 + debate 결합(sha)
    debate_sha = _sha(dp)  # 행의 debate_sha256 은 compare_ours 가 판정 시점에 박은 값
    for name, arm in (("axis", f"compare_axis_{issue_id}_{run_id}.jsonl"),
                      ("stance", f"compare_stance_{issue_id}_{run_id}.jsonl")):
        rows = _rows(paths.raw_calls(arm))
        kr = _key_report([(r["round"], r["agent_id"]) for r in rows], expected)
        n_noraw = sum(1 for r in rows if not r.get("raw_response"))
        n_pf = (sum(1 for r in rows if r.get("parse") == "parse_fail") if name == "axis"
                else sum(1 for r in rows if r.get("parsed") not in ("yes", "no")))
        n_badsha = sum(1 for r in rows if r.get("debate_sha256") != debate_sha)
        out[f"{name}_keys"] = kr
        out[f"{name}_parse_fail"] = n_pf
        out[f"{name}_rows_without_raw"] = n_noraw
        out[f"{name}_debate_sha_mismatch"] = n_badsha
        if not (kr["physical"] == kr["unique"] == kr["expected"]) or kr["missing"] \
                or kr["unexpected"]:
            prob(f"{name} 좌표 집합 불일치: {kr}")
        if n_noraw:
            prob(f"{name} raw_response 미보존 {n_noraw}행 (규약 5 위반)")
        if n_badsha:
            prob(f"{name} debate_sha256 불일치 {n_badsha}행 — 판정이 현재 debate "
                 f"원문과 다른 판 위에서 났다(부재 행 포함, C-8 결합 검사)")

    # 6. 산출물 sha 기록 (부재는 문제로)
    outputs = {"debate": dp,
               "judgment_author": paths.judgment(issue_id, f"{run_id}_author"),
               "stance_summary": paths.DATA /
               f"stance_summary_{issue_id}_{run_id}.json",
               "manifest": paths.raw_calls(
                   f"compare_manifest_{issue_id}_{run_id}.json")}
    out["sha256"] = {}
    for k, p in outputs.items():
        if p.exists():
            out["sha256"][k] = _sha(p)
        else:
            prob(f"산출물 부재: {k} ({p.name})")

    out["verdict"] = "ok" if not out["problems"] else "discard"
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--issues", required=True)
    ap.add_argument("--run-prefix", required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--source-data", type=Path, default=HERE / "data")
    args = ap.parse_args()
    issues = [s.strip() for s in args.issues.split(",") if s.strip()]
    rounds = int(yaml.safe_load(args.config.read_text(encoding="utf-8"))["rounds"])

    old_data = paths.DATA
    paths.DATA = Path(args.source_data).resolve()
    try:
        results = []
        for issue_id in issues:
            run_id = f"{args.run_prefix}_{issue_id.rsplit('_', 1)[-1]}"
            r = check_issue(issue_id, run_id, rounds)
            results.append(r)
            mark = "OK " if r["verdict"] == "ok" else "폐기"
            print(f"[{mark}] {issue_id} · {run_id}")
            for p in r["problems"]:
                print(f"      ⚠ {p}")
            if "axis_parse_fail" in r:
                print(f"      parse_fail: axis {r['axis_parse_fail']} · "
                      f"stance {r['stance_parse_fail']} (모름 — 소실 아님)")

        # 5. 원장 계수 (블록 공용 — 이슈 밖 합계)
        ledger = _rows(paths.raw_calls("compare_ours_call_ledger.jsonl"))
        attempts = _rows(paths.raw_calls("compare_ours_attempt_ledger.jsonl"))
        summary = {"logical_calls": len(ledger),
                   "transport_attempts": len(attempts),
                   "est_cost_usd": round(len(ledger) * COST_PER_CALL, 2),
                   "checked_at": datetime.now(timezone.utc).isoformat(),
                   "issues": results}
        print(f"[원장] 논리 {len(ledger)} · 전송 {len(attempts)} · "
              f"추정 ~${summary['est_cost_usd']} (콜당 $0.01 실측 기준)")

        rp = paths.DATA / f"compare_postcheck_{args.run_prefix}.json"
        rp.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        print(f"[기록] {rp} — 생성 즉시 커밋할 것(규약 8)")
        if any(r["verdict"] != "ok" for r in results):
            sys.exit(1)   # 폐기 이슈 존재 — 대조표에서 제외하고 사실과 함께 보고(§3-6)
    finally:
        paths.DATA = old_data


if __name__ == "__main__":
    main()
