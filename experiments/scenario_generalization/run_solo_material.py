"""[재료 확장 · 김요한] 단독 3×3 을 새 재료로 돌리는 실행기 — 원본 러너 재사용, 0줄 수정

## 무엇을 하나

`experiments/memory_structure/run_solo.py` 는 `ISSUE_ID = "issue_camp"` 상수라 다른 재료를
못 받는다. 그 파일을 고치는 대신 **import 해서 재료 상수만 바꿔 끼운다.**

프롬프트 조립·호출 상한·체크포인트·원문 보존·절단 처리는 **원본 함수를 그대로 쓴다.**
러너가 두 벌이 되지 않는다 — 두 벌이 되면 언젠가 어긋나고, 그때 어느 쪽이 정본인지 아무도
모른다.

## 왜 원본을 안 고치나

- 기존 54런의 재현성이 `run_solo.py` 의 기본값 동작에 걸려 있다. 원본을 안 건드리면
  그 보장이 **자동으로** 유지된다. 고치면 내가 보장해야 한다.
- `STUB`·`STANCE` 는 `PROMPTS_v1.md` 축자 정본의 코드 미러다. 사전등록 문서에 속한다.
- 되돌리기가 이 파일 삭제 하나로 끝난다.

## 바꿔 끼우는 것 (딱 다섯)

| 이름 | 원본 | 여기서 |
|---|---|---|
| `ISSUE_ID` | `issue_camp` | 재료 이름 (산출물 meta 기록용) |
| `STUB` | 합숙지 사안 요약 | 재료의 사안 요약문 |
| `STANCE` | 무레온 입장 고정 | 재료의 입장 문면 |
| `FINAL_POLL_INSTR` | 다림재/무레온 택일 | 재료의 두 선택지 |
| `RUNS_DIR` | `memory_structure/runs` | **우리 폴더** — 민옥 산출물과 안 섞인다 |

`facts_block` 은 원래부터 `run_one()` 의 인자다. 우리가 만들어 넘긴다.

## 무결성 관문

몽키패치의 위험은 **원본이 바뀌었는데 조용히 계속 도는 것**이다. 그래서 시작할 때
① 원본 상수 4종의 해시 ② `run_one` 시그니처의 해시를 확인하고, 하나라도 다르면 그 자리에서
죽는다. 원본이 개정되면 이 파일도 같이 봐야 한다는 신호다.

## 한계 (알고 쓴다)

- 산출물이 `experiments/scenario_generalization/runs/` 에 생긴다. 콘솔 결과 탭·생존 격자는
  `memory_structure/runs` 만 보므로 **여기 것은 콘솔에 안 뜬다.** 분석은 우리 스크립트로 한다.
- 콘솔 「단독 실행」 폼으로는 못 돌린다(폼에 이슈 칸이 없다). 명령줄 전용이다.
- 위 둘을 풀려면 원본·콘솔을 고쳐야 한다 — 실험을 한 번 돌려보고 값어치를 확인한 뒤에 한다.

## 사용례

    # 0콜 조립 리허설 (권장 — 문면부터 눈으로 본다)
    PYTHONUTF8=1 python experiments/scenario_generalization/run_solo_material.py --issue throne --dry
    # 입장 대립형은 두 입장을 각각
    PYTHONUTF8=1 python .../run_solo_material.py --issue polar --stance 후송 --reps 1
    PYTHONUTF8=1 python .../run_solo_material.py --issue polar --stance 대기 --reps 1
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "memory_structure"))

import run_solo as rs  # noqa: E402  (민옥 트랙 원본 — 읽기만 한다)

# 2026-08-19 실측. 원본이 개정되면 여기서 죽는다 — 조용히 어긋나지 않게.
EXPECT_CONST_SHA = "308e1dbc292f992a79571544db49af3c155107512a7d24509e9065aa1081a05e"
EXPECT_SIG_SHA = "e524a8e711c96d7147af8fa1052ec2d7f81318c72ad3713b0f9725fac87237c6"

BUILDERS = {"throne": "build_issue_throne",
            "polar": "build_issue_polar",
            "exile": "build_issue_exile"}


def integrity_gate() -> None:
    blob = "\x00".join([rs.ISSUE_ID, rs.STUB, rs.STANCE, rs.FINAL_POLL_INSTR])
    got_c = hashlib.sha256(blob.encode()).hexdigest()
    got_s = hashlib.sha256(str(inspect.signature(rs.run_one)).encode()).hexdigest()
    if got_c != EXPECT_CONST_SHA:
        raise SystemExit(
            "[관문] run_solo.py 의 재료 상수가 바뀌었다 — 이 래퍼가 무엇을 덮어쓰는지 다시 "
            f"확인하라.\n  기대 {EXPECT_CONST_SHA}\n  실측 {got_c}")
    if got_s != EXPECT_SIG_SHA:
        raise SystemExit(
            "[관문] run_solo.run_one 의 시그니처가 바뀌었다 — 호출부를 다시 맞춰라.\n"
            f"  기대 {EXPECT_SIG_SHA}\n  실측 {got_s}\n  현재 {inspect.signature(rs.run_one)}")
    print("[관문] 원본 상수·시그니처 해시 일치 — 원본 무변경 확인")


def facts_block(issue_id: str, reverse: bool = False) -> str:
    """원본 load_facts_block 과 **같은 형식**으로 조립한다(ID 미노출, '- ' 접두)."""
    doc = json.loads((HERE / f"facts_{issue_id}.json").read_text(encoding="utf-8"))
    facts = list(doc["facts"])
    if reverse:
        facts = list(reversed(facts))
    return "\n".join("- " + f["text"] for f in facts)


def main() -> None:
    ap = argparse.ArgumentParser(description="새 재료로 단독 3×3 (원본 러너 재사용)")
    ap.add_argument("--issue", required=True, choices=sorted(BUILDERS))
    ap.add_argument("--stance", default=None,
                    help="입장 대립형 재료에서 어느 입장으로 돌릴지 (polar: 후송|대기, exile: 추방|잔류)")
    ap.add_argument("--model", default="gpt")
    ap.add_argument("--provider", default="api", choices=["api", "hermes"])
    ap.add_argument("--arms", nargs="*", default=list(rs.ARMS), choices=list(rs.ARMS))
    ap.add_argument("--memories", nargs="*", default=list(rs.MEMS), choices=list(rs.MEMS))
    ap.add_argument("--reps", nargs="*", type=int, default=[1])
    ap.add_argument("--max-calls", type=int, default=60, help="런 1개당 상한")
    ap.add_argument("--dry", action="store_true", help="0콜 조립 리허설")
    ap.add_argument("--final-poll", action="store_true")
    args = ap.parse_args()

    integrity_gate()

    mod = importlib.import_module(BUILDERS[args.issue])
    bundle = mod.SOLO_PROMPTS
    stances = bundle["stances"]
    if args.stance is None:
        if len(stances) > 1:
            raise SystemExit(f"--stance 필요 — {args.issue} 의 입장: {', '.join(stances)}")
        stance_key = next(iter(stances))
    else:
        if args.stance not in stances:
            raise SystemExit(f"모르는 입장 '{args.stance}' — {args.issue} 의 입장: {', '.join(stances)}")
        stance_key = args.stance

    issue_id = bundle["issue_id"]
    fb = facts_block(issue_id)
    out_root = HERE / "runs" / (issue_id if stance_key == "fixed" else f"{issue_id}_{stance_key}")

    if not args.dry and args.provider == "api":
        rs.llm.preflight(args.model, temperature=rs.GEN_TEMPERATURE)

    planned = [(a, m, r) for a in args.arms for m in args.memories for r in args.reps]
    per = sum(8 if m == "note" else 5 for _, m, _ in planned) + (len(planned) if args.final_poll else 0)
    print(f"[plan] {issue_id} · 입장 {stance_key} · {args.model} ({args.provider}) — "
          f"{len(planned)}런 · 약 {per}콜 · dry={args.dry}")
    print(f"[out ] {out_root}")

    saved = (rs.ISSUE_ID, rs.STUB, rs.STANCE, rs.FINAL_POLL_INSTR, rs.RUNS_DIR)
    try:
        rs.ISSUE_ID = issue_id
        rs.STUB = bundle["stub"]
        rs.STANCE = stances[stance_key]
        rs.FINAL_POLL_INSTR = bundle["final_poll"]
        rs.RUNS_DIR = out_root
        for a, m, r in planned:
            rs.run_one(args.model, args.provider, a, m, r, fb, args.max_calls, args.dry,
                       stance=True, final_poll=args.final_poll)
    finally:
        (rs.ISSUE_ID, rs.STUB, rs.STANCE, rs.FINAL_POLL_INSTR, rs.RUNS_DIR) = saved


if __name__ == "__main__":
    main()
