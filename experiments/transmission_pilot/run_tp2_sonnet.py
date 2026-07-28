# -*- coding: utf-8 -*-
"""P3 전달 레이더 파일럿 tp2 — Sonnet 실호출 판(Anthropic). 탐색적/데모 지위.

지위: tp1 전례 계승(브랜치 시제품·개인 키 집행·experiments/ 분리·팀 data/ 읽기 전용).
목적: tp1(gpt-5.4-mini)과 **같은 시나리오·같은 롤링 창 생태**를 모델만 Claude Sonnet 4.6으로
바꿔 재실행 — (a) TSR·소실 패턴의 모델 교차 검증(생태 특성 vs 모델 특성), (b) 접근 창
원장(modules.access_window)의 실모델 첫 적용, (c) 선결 2건(temp 1.2 불가·Sonnet 5 temp0
거부)의 실증 근거 확보. 정식 판정(H-T1·H-T2)은 미니 H2 실호출 몫 — 본 산출물 수치는 전부
"탐색적" 지위다.

구현: run_pilot.py 를 임포트해 phase 로직·프롬프트·출력 모양(v0.2)을 그대로 쓰고,
호출층(chat)·상수(RUN_ID·모델)만 오버라이드한다. 로직 이중정의 금지.

모델 스택 (7/28 요한 확정 — "소넷 4.6에 n=1"):
  생성: claude-sonnet-4-6 · temp 0.7(민옥 N1 계승 — Sonnet 4.6은 temperature 허용) · max 1024
  판정: claude-sonnet-4-6 · temp 0 · n=1 단일 표 — **파일럿 판정기**(팀 확정 judge 아님)
  프로브: 생성 모델과 동일 · temp 0 (민옥 확정 방식 v0)
  편차 기록: Anthropic API 는 seed 파라미터가 없다 — tp1 의 seed(N3 best-effort)는 기록만
  하고 전달하지 않는다. thinking 은 미지정(Sonnet 4.6 기본 = 안 켬).

안전장치(tp1 계승): 호출 상한(--max-calls, 기본 300) · 단계별 체크포인트(완료 파일 스킵) ·
출력 절단(stop_reason=max_tokens) 즉시 에러(민옥 D1) · judge 파싱실패 카운트.

사용 (리포 루트에서, anthropic SDK 있는 파이썬으로):
  python experiments/transmission_pilot/run_tp2_sonnet.py --phase probe   --issue carkey
  python experiments/transmission_pilot/run_tp2_sonnet.py --phase scan    --issue carkey
  python experiments/transmission_pilot/run_tp2_sonnet.py --phase debate  --issue carkey
  python experiments/transmission_pilot/run_tp2_sonnet.py --phase judge   --issue carkey
  python experiments/transmission_pilot/run_tp2_sonnet.py --phase analyze --issue carkey
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import run_pilot as rp  # noqa: E402  (tp1 로직 재사용 — 이중정의 금지)

RUN_ID = "tp2"
MODEL = "claude-sonnet-4-6"   # 생성·판정·프로브 단일 모델 (temp 표현 가능한 최신 Sonnet)

_client = None


def _anthropic_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=rp.ENV["ANTHROPIC_API_KEY"])
    return _client


def chat(model: str, system: str, user: str, *, temperature: float | None,
         max_tokens: int, seed: int | None = None) -> str:
    """tp1 chat 과 동일 계약의 Anthropic 판 — 상한·절단 가드 동일.

    seed 는 Anthropic API 미지원 — 받되 전달하지 않는다(편차: 모듈 독스트링).
    절단(stop_reason=max_tokens)은 즉시 에러 — D1 교훈.
    """
    rp.N_CALLS += 1
    if rp.N_CALLS > rp.MAX_CALLS:
        raise SystemExit(f"[ABORT] 호출 상한 초과 ({rp.N_CALLS} > {rp.MAX_CALLS})")
    kwargs = dict(model=model, max_tokens=max_tokens, system=system,
                  messages=[{"role": "user", "content": user}])
    if temperature is not None:
        kwargs["temperature"] = temperature
    resp = _anthropic_client().messages.create(**kwargs)
    if resp.stop_reason == "max_tokens":
        raise RuntimeError(f"출력 절단(stop_reason=max_tokens) — model={model}. "
                           "D1 교훈: 폐기 대상")
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"안전 거부(stop_reason=refusal) — model={model}. 검토 필요")
    return "".join(b.text for b in resp.content if b.type == "text")


def phase_analyze(issue_key: str) -> None:
    """tp1 analyze 계승 + 접근 창 원장(access_window) 리포트 추가 산출."""
    from modules import access_window as aw
    rp.phase_analyze(issue_key)   # transmission_report_*_tp2.json

    m = rp.materials(issue_key)
    issue_id = m["issue_id"]
    judgment = json.loads(rp.out_path("judgment", issue_id).read_text(encoding="utf-8"))
    events = [json.loads(ln) for ln
              in rp.out_path("debate", issue_id).read_text(encoding="utf-8").splitlines()
              if ln.strip()]
    prior = json.loads(rp.out_path("prior", issue_id).read_text(encoding="utf-8"))
    scan = json.loads(rp.out_path("scan", issue_id).read_text(encoding="utf-8"))
    facts_by_id = {f["fact_id"]: dict(f) for f in m["facts"]["facts"]}
    for row in prior["facts"]:
        facts_by_id[row["fact_id"]]["prior"] = {"score": row["score"]}

    rep = aw.report(judgment, m["assignment"], events, facts_by_id,
                    question_exposed_ids=frozenset(scan["question_exposed_ids"]))
    rep["pilot_meta"] = {"status": "탐색적/데모 지위 — 서술 계기(판별표 밖)",
                         "run_id": RUN_ID, "model": MODEL}
    dst = rp.DATA / f"access_report_{issue_id}_{RUN_ID}.json"
    dst.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    s = rep["summary"]
    print(f"[access] 최종={s['final_state']} · 사망 경험={s['n_ever_inaccessible']}"
          f"/{s['n_facts_tracked']} · 은퇴 결말={s['retirement_outcomes']} · "
          f"부활={s['revival_channels']} · resurgence 팩트={s['n_facts_with_resurgence']}")
    print(f"[access] 완료 → {dst.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description="tp2 — Sonnet 4.6 실호출 파일럿")
    ap.add_argument("--phase", required=True,
                    choices=["probe", "scan", "debate", "judge", "analyze"])
    ap.add_argument("--issue", required=True, choices=["esa", "carkey"])
    ap.add_argument("--max-calls", type=int, default=300)
    args = ap.parse_args()

    # tp1 모듈의 상수·호출층 오버라이드 (phase 로직은 모듈 전역을 참조한다)
    rp.RUN_ID = RUN_ID
    rp.GEN_MODEL = MODEL
    rp.JUDGE_MODEL = MODEL
    rp.chat = chat
    rp.MAX_CALLS = args.max_calls

    if args.phase == "analyze":
        phase_analyze(args.issue)
    else:
        {"probe": rp.phase_probe, "scan": rp.phase_scan,
         "debate": rp.phase_debate, "judge": rp.phase_judge}[args.phase](args.issue)
    print(f"[calls] 이번 실행 LLM 호출 {rp.N_CALLS}회")


if __name__ == "__main__":
    main()
