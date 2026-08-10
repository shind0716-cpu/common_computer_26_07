# -*- coding: utf-8 -*-
"""연결 모양 축 — tree / line 팔 실행기 (2026-08-10 · 요한).

지위: **실측 기록** (탐색적). 설정 사전 ④ 연결 모양 축의 실행 로그가 0건이라 그 칸을 연다.

무엇을 하는가
  `modules.debate_engine.run()` 과 `modules.judge` 를 **무수정으로** 호출한다. 이 파일이
  하는 일은 세 가지뿐 — (1) `paths.DATA` 를 이 폴더 아래로 재지정, (2) 전역 호출 상한을
  걸기 위해 `llm.obtain_response` 를 세는 껍데기로 감싸기, (3) `--dry` 리허설용 가짜 주입.
  토론 루프·판정 잣대·프롬프트 조립은 전부 정본이다(재구현 0).

full 팔은 왜 없는가
  `experiments/mini_h2_pilot` 의 `h2p_off` 가 **structure 를 뺀 모든 좌표가 같다**
  (gpt-5.4-mini · temp 1.2 · seed 42 · 8에이전트 · rounds 3 · ledger off · judge gpt-mini
  temp0 n=3). 입력 3파일(issue·facts·assignment) sha256 이 이 폴더 사본과 일치함을
  확인하고 그대로 기준선으로 쓴다 — 같은 조건을 두 번 돌리는 것은 비용이자 노이즈다.

계승한 편차 (mini_h2_pilot README 표기 계승)
  D-p1 debate_model=gpt-5.4-mini (팀 정본 claude-haiku — 예산 사유)
  D-p2 judge=gpt-5.4-mini·temp0·n=3 다수결 (확정 사양과 모델만 다름)
  D-p3 issue_esa 에 question 필드 주입본 사용 (팀 data/ 는 이 필드가 없어 제목으로
       폴백하고, 그 제목에 "(스프린트 정본 v1)" 이 섞여 프롬프트로 들어간다)

안전장치 (CLAUDE.md 비용 주의)
  전역 호출 상한(--max-calls, 초과 시 즉시 예외) · 엔진 내장 라운드 체크포인트 ·
  judge stage 진행 계기판 · --dry (API 0원 완주 리허설).

사용 (리포 루트에서)
  python experiments/structure_axis/run_structure.py --arm tree --phase debate --dry
  python experiments/structure_axis/run_structure.py --arm tree --phase all
  python experiments/structure_axis/run_structure.py --arm line --phase all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from modules import debate_engine, llm, paths  # noqa: E402
from modules import judge as judge_mod  # noqa: E402

paths.DATA = HERE / "data"

ISSUE_ID = "issue_esa"
ARMS = {"tree": ("struct_tree", HERE / "configs" / "struct_tree_gpt.yaml"),
        "line": ("struct_line", HERE / "configs" / "struct_line_gpt.yaml")}

_calls = 0
_cap = 0
_real_obtain = llm.obtain_response


def _counted(inputs, model, temperature=0.0, reasoning="default"):
    """전역 호출 상한 — 조용히 넘기지 않고 즉시 죽는다."""
    global _calls
    if _calls >= _cap:
        raise RuntimeError(
            f"[structure_axis] 전역 호출 상한 {_cap} 도달 — 중단. "
            "엔진 체크포인트가 남아 있으니 상한을 올려 다시 부르면 이어집니다.")
    _calls += 1
    return _real_obtain(inputs, model=model, temperature=temperature, reasoning=reasoning)


def _dry_utterance(inputs, model=None, temperature=None):
    """리허설용 가짜 발화 — 재조립 검증이 돌 만큼의 형태만 갖춘다. 수치 인용 금지."""
    return f"[dry] 모의 발화 (len={len(inputs)})"


def _dry_vote(fact, stage_utterances):
    """리허설용 가짜 표 — 문자열 대조. 수치 인용 금지."""
    hit = [u["agent_id"] for u in stage_utterances
           if fact["text"][:8] in (u.get("response_text") or "")]
    return {"status": "mentioned" if hit else "unmentioned",
            "agents_mentioning": hit, "reason": "dry-run 문자열 대조"}


def main() -> None:
    global _cap
    ap = argparse.ArgumentParser(description="연결 모양 축 실행기")
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--phase", default="all", choices=["debate", "judge", "all"])
    ap.add_argument("--max-calls", type=int, default=220,
                    help="전역 실호출 상한 (발화 32 + 판정 144 = 176 예상)")
    ap.add_argument("--dry", action="store_true", help="API 0원 리허설")
    args = ap.parse_args()

    run_id, cfg_path = ARMS[args.arm]
    _cap = args.max_calls
    if not args.dry:
        llm.obtain_response = _counted
        debate_engine.llm.obtain_response = _counted

    cfg = json.loads(json.dumps({}))  # placeholder, judge 는 아래에서 yaml 로 읽는다
    print(f"[structure_axis] arm={args.arm} run={run_id} data={paths.DATA} "
          f"dry={args.dry} 상한={_cap}")

    if args.phase in ("debate", "all"):
        out = debate_engine.run(
            ISSUE_ID, run_id, cfg_path,
            utterance_fn=_dry_utterance if args.dry else None,
            judge_vote_fn=_dry_vote if args.dry else None)
        print(f"[structure_axis] debate 작성: {out} · 누적 호출 {_calls}")

    if args.phase in ("judge", "all"):
        cfg = judge_mod._load_config(cfg_path)
        result = judge_mod.judge_debate(ISSUE_ID, run_id, cfg, offline=args.dry)
        jp = paths.judgment(ISSUE_ID, run_id)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        s, h = result["summary"], result["summary"]["judge_health"]
        print(f"[structure_axis] judgment 작성: {jp}")
        print(f"[structure_axis] far_system={s['far_system']} far_critical={s['far_critical']} "
              f"· 표 {h['n_calls']}회 · 파싱실패 {h['n_parse_fail']} · 공백발화 "
              f"{h.get('n_blank_utterances', 0)} · 누적 호출 {_calls}")


if __name__ == "__main__":
    main()
