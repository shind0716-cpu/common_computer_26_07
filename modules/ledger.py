"""[민옥 · 수요일] Fact Ledger v0 + 합의 전 게이트.
v0 계약: judge 판정에서 사라진 팩트를 찾아 다음 라운드 프롬프트에 전량 재주입,
        ledger_inject 이벤트를 debate 로그에 기록.
게이트 계약: 합의문 초안 vs 장부 대조 → 누락 시 재작성 요구(rollback 최대 1회), gate_check 이벤트 기록.
사다리: v0(전량) → v1(무시된 것만, 상태 추적) → v2(pull 전환). 폴백 = a1(무지성 전량 재게시).

이 파일의 상태: v0 초안. 순수 함수(missing_facts·build_injection_block·make_inject_event·
gate_check) 구현 완료. debate_engine 루프 결합은 통합(수 밤) 몫 — 여기선 순수 함수만 제공한다.

판정 잣대의 단일 소스: '소실'=재주입 대상 정의는 judge.SURVIVING 을 그대로 쓴다
(SCHEMA.md 「FAR 정의」절 강제). judge 와 ledger 가 다른 잣대를 쓰면 측정이 무너진다.

judgment 구조 의존 최소화: stages[].facts[].{fact_id, status} 두 필드만 읽는다.
(votes 세부 구조는 judge 버전에 따라 다를 수 있음 — SCHEMA 「통합 전 확인 필요」 참조.)

사용(단독):
  python -m modules.ledger --issue issue_esa --run dryrun --stage 3
    → 해당 stage 소실 팩트와 v0 재주입 블록을 콘솔에 출력(파일 안 씀, 점검용).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from . import paths
from .judge import SURVIVING

# v0 재주입 사유 코드 (스키마 4번 ledger_inject.reason).
REASON_V0 = "v0_all_missing"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 핵심 순수 함수
# ---------------------------------------------------------------------------
def _stage_record(judgment: dict, stage: int) -> dict:
    """judgment 에서 주어진 stage 레코드를 찾는다. 없으면 KeyError."""
    for st in judgment.get("stages", []):
        if st.get("stage") == stage:
            return st
    raise KeyError(f"judgment 에 stage={stage} 없음 (있는 stage: "
                   f"{[s.get('stage') for s in judgment.get('stages', [])]})")


def missing_facts(judgment: dict, stage: int) -> list[str]:
    """해당 stage 에서 '소실'된 팩트의 fact_id 목록(등장 순서 보존).

    소실 = status ∉ SURVIVING (judge 와 동일 잣대). judge v0 2종 체계에선
    unmentioned 가 곧 소실. votes 등 세부 구조에 의존하지 않는다.
    """
    st = _stage_record(judgment, stage)
    return [f["fact_id"] for f in st.get("facts", []) if f.get("status") not in SURVIVING]


def build_injection_block(missing_ids: list[str], facts_by_id: dict[str, dict]) -> str:
    """소실 팩트들을 다음 라운드 프롬프트에 붙일 재주입 텍스트 블록으로 만든다(v0=전량).

    facts_by_id: fact_id -> fact dict({text, ...}). 원문 텍스트를 그대로 싣는다(요약 금지).
    소실 팩트가 없으면 빈 문자열(주입할 것 없음).
    """
    if not missing_ids:
        return ""
    lines = [
        "[장부 재고지] 아래 사실들은 앞선 라운드 논의에서 누락되었습니다. "
        "다음 발언에서 반드시 검토하세요:",
    ]
    for fid in missing_ids:
        text = facts_by_id.get(fid, {}).get("text", f"(원문 없음: {fid})")
        lines.append(f"- {text}")
    return "\n".join(lines)


def make_inject_event(run_id: str, next_round: int, injected_fact_ids: list[str],
                      *, reason: str = REASON_V0) -> dict:
    """스키마 4번 ledger_inject 이벤트 레코드 생성(debate 로그에 append 될 dict).

    next_round: 이 소실분이 재주입되어 반영될 라운드 번호(재주입은 '다음' 라운드 대상).
    debate_engine.emit() 과 동일한 형식(event/run_id/ts + 필드)을 따른다.
    """
    return {
        "event": "ledger_inject",
        "run_id": run_id,
        "ts": now(),
        "round": next_round,
        "injected_fact_ids": list(injected_fact_ids),
        "reason": reason,
    }


def gate_check(draft_text: str, ledger_fact_ids: list[str], facts_by_id: dict[str, dict],
               run_id: str, *, rollback_count: int = 0) -> dict:
    """합의문 초안 vs 장부 대조 → 스키마 4번 gate_check 이벤트.

    누락 = 장부의 팩트 원문이 draft 에 문자열로 나타나지 않음(v0 단순 대조).
    verdict: 누락 있고 아직 롤백 안 했으면 'rollback'(최대 1회), 아니면 'pass'.
    rollback_count 는 최대 1 로 고정(스키마 4번 제약).
    """
    missing = []
    for fid in ledger_fact_ids:
        text = (facts_by_id.get(fid, {}).get("text") or "").strip()
        if text and text not in draft_text:
            missing.append(fid)
    if missing and rollback_count < 1:
        verdict, rc = "rollback", 1
    else:
        verdict, rc = "pass", min(rollback_count, 1)
    return {
        "event": "gate_check",
        "run_id": run_id,
        "ts": now(),
        "draft_text": draft_text,
        "missing_fact_ids": missing,
        "verdict": verdict,
        "rollback_count": rc,
    }


# ---------------------------------------------------------------------------
# 로딩 헬퍼 (순수 — 파일 읽기만, 쓰기 없음)
# ---------------------------------------------------------------------------
def load_facts_by_id(issue_id: str) -> dict[str, dict]:
    doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    return {f["fact_id"]: f for f in doc["facts"]}


def load_judgment(issue_id: str, run_id: str) -> dict:
    return json.loads(paths.judgment(issue_id, run_id).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CLI (점검용 — 파일을 쓰지 않는다. 통합 루프는 debate_engine 몫)
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Fact Ledger v0 — 소실 팩트·재주입 블록 점검")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--stage", type=int, required=True, help="소실을 집계할 stage(=round)")
    args = ap.parse_args()

    judgment = load_judgment(args.issue, args.run)
    facts_by_id = load_facts_by_id(args.issue)

    ids = missing_facts(judgment, args.stage)
    block = build_injection_block(ids, facts_by_id)
    event = make_inject_event(args.run, args.stage + 1, ids)

    print(f"[ledger v0] issue={args.issue} run={args.run} stage={args.stage}")
    print(f"[ledger v0] 소실 팩트 {len(ids)}종: {ids}")
    print("[ledger v0] 재주입 블록:")
    print(block or "  (없음)")
    print("[ledger v0] ledger_inject 이벤트(다음 라운드용):")
    print("  " + json.dumps(event, ensure_ascii=False))


if __name__ == "__main__":
    main()
