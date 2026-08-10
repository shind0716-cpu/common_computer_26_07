# -*- coding: utf-8 -*-
"""논문 재현 트랙 — 접합 0콜 통합 리허설 (접합 계층 · 요한, 2026-08-10 플랜 승인분).

지위: **리허설 러너.** 논문 트랙 산출물 형태(픽스처 3종)가 우리 스택 전 사슬
(debate_engine → judge → ledger → access_window)을 실제로 통과하는지, 그리고
저자 축 판정물이 bridge 변환을 거쳐 ledger 에 오판 없이 물리는지를 **LLM 호출 0** 으로 실증한다.

픽스처 원본은 불변 — 임시 디렉터리로 복사한 뒤 paths.DATA 를 재지정한다
(structure_axis 러너의 재지정 + extractor dry 의 임시 경로 패턴 결합).

단계:
  ① debate_engine.run(utterance_fn=스텁, judge_vote_fn=스텁) — seating·run_meta 자동 방출
  ② judge_debate(offline=True) → judgment 저장 (우리 축 · 3표 offline)
  ③ ledger.missing_facts — fact_id 경로 실증 (전 팩트 소실 오판이 없어야 함)
  ④ access_window.report — status=ok, seating 존재(assumed_full 아님) 확인
  ⑤ 저자 축: offline_matched 스텁 행 → bridge.author_rows_to_judgment → validate 통과
     → ledger.missing_facts 정상 동작 (차단급 해소 실증)
  ⑥ 전 산출물 validate + 요약 수치 출력. 스텁 산출 수치는 배관 확인용 — 인용 금지.

사용:
  PYTHONUTF8=1 python experiments/paper_repro/rehearse_splice.py
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from modules import access_window, debate_engine, ledger, paths  # noqa: E402
from modules import judge as judge_mod  # noqa: E402
from modules import validate as validate_mod  # noqa: E402
from experiments.judge_axis.axis_probe import offline_matched  # noqa: E402 — import만(폴더 무수정)
import bridge  # noqa: E402

ISSUE_ID = "issue_repro_fx"
RUN_ID = "fxsmoke"
CFG = HERE / "configs" / "fx_smoke.yaml"


def _stub_utterance_factory(facts: list[dict]):
    """결정론 발화 스텁 — 프롬프트에 실린 배정 팩트 원문을 일부 되뇌게 만든다.
    (offline judge·offline_matched 가 어절 겹침으로 동작하므로, 원문 포함 여부가
    mentioned/unmentioned 를 가른다 — 전부 소실/전부 생존의 퇴화를 피한다.)"""
    texts = [f["text"] for f in facts]
    counter = {"n": 0}

    def stub(inputs: str, model: str = "", temperature: float = 0.0) -> str:
        counter["n"] += 1
        # 프롬프트에 등장한 팩트 원문 중 앞의 2개만 되뇐다 — 나머지는 침묵(소실 후보).
        present = [t for t in texts if t in inputs]
        kept = present[:2]
        return ("I considered the assigned facts. " + " ".join(kept)) if kept else \
            "I have nothing specific to add."

    stub._counter = counter
    return stub


def _stub_vote(fact: dict, stage_utterances: list[dict]) -> dict:
    """ledger v0 루프-내 판정용 스텁 — 이번 리허설은 ledger off 라 호출되지 않아야 정상."""
    return {"status": "mentioned", "agents_mentioning": [], "reason": "stub"}


def _validate(path: Path) -> None:
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        try:
            validate_mod.validate(path)
        except SystemExit:
            print(buf.getvalue(), file=sys.stderr, end="")
            raise


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="paper_repro_splice_") as td:
        data_root = Path(td) / "data"
        shutil.copytree(HERE / "fixtures" / "data", data_root)
        old_data = paths.DATA
        paths.DATA = data_root
        try:
            facts_doc = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))
            facts = facts_doc["facts"]
            facts_by_id = {f["fact_id"]: f for f in facts}

            # ① 토론 — 실호출 0 (utterance_fn/judge_vote_fn 주입)
            stub = _stub_utterance_factory(facts)
            debate_path = debate_engine.run(ISSUE_ID, RUN_ID, CFG,
                                            utterance_fn=stub, judge_vote_fn=_stub_vote)
            events = [json.loads(l) for l in
                      debate_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            n_utt = sum(1 for e in events if e.get("event") == "utterance")
            n_seating = sum(1 for e in events if e.get("event") == "seating")
            _validate(debate_path)
            print(f"① debate 완주: 발화 {n_utt} · seating {n_seating} · "
                  f"스텁 호출 {stub._counter['n']} · validate OK")

            # ② 우리 축 judgment (offline 3표)
            cfg = judge_mod._load_config(CFG)
            jd_ours = judge_mod.judge_debate(ISSUE_ID, RUN_ID, cfg, offline=True)
            jp = paths.judgment(ISSUE_ID, RUN_ID)
            jp.parent.mkdir(parents=True, exist_ok=True)
            jp.write_text(json.dumps(jd_ours, ensure_ascii=False, indent=2), encoding="utf-8")
            _validate(jp)
            print(f"② 우리 축 judgment: stages {len(jd_ours['stages'])} · "
                  f"far_by_stage {[s['far_system'] for s in jd_ours['summary']['far_by_stage']]} · validate OK")

            # ③ ledger — fact_id 경로
            last_stage = jd_ours["stages"][-1]["stage"]
            missing_ours = ledger.missing_facts(jd_ours, last_stage)
            n = len(facts)
            assert 0 <= len(missing_ours) < n, \
                f"ledger 퇴화: 소실 {len(missing_ours)}/{n} (전부/음수는 접합 실패)"
            print(f"③ ledger(우리 축): 마지막 stage 소실 {len(missing_ours)}/{n} — 오판 없음")

            # ④ access_window
            assignment = json.loads(paths.assignment(ISSUE_ID).read_text(encoding="utf-8"))
            rep = access_window.report(jd_ours, assignment, events, facts_by_id)
            assert rep["status"] == "ok", f"access_window status={rep['status']}"
            assert not rep["meta"]["window"]["edges"].get("assumed_full"), \
                "seating 미인식 — 접합 실패"
            print(f"④ access_window: status=ok · records {len(rep['records'])} · "
                  f"rounds {rep['meta']['rounds']}")

            # ⑤ 저자 축 → bridge 변환 → ledger
            utts = [e for e in events if e.get("event") == "utterance"]
            rows = []
            for u in utts:
                idx = offline_matched(facts, u.get("response_text", ""))
                rows.append({"round": u["round"], "agent_id": u["agent_id"],
                             "matched_fact_ids": idx, "parse": "offline_stub"})
            # parse_fail 경로도 함께 리허설 — 마지막 행 하나를 실패로 바꾼 사본 검사
            rows_with_fail = rows[:-1] + [dict(rows[-1], matched_fact_ids=None, parse="parse_fail")]
            jd_author = bridge.author_rows_to_judgment(
                rows_with_fail, facts_doc, issue_id=ISSUE_ID,
                run_id=f"{RUN_ID}_author", prompt_ver="offline_stub")
            jpa = paths.judgment(ISSUE_ID, f"{RUN_ID}_author")
            jpa.write_text(json.dumps(jd_author, ensure_ascii=False, indent=2), encoding="utf-8")
            _validate(jpa)
            missing_author = ledger.missing_facts(jd_author, jd_author["stages"][-1]["stage"])
            assert 0 <= len(missing_author) < n, \
                f"저자 축 ledger 퇴화: 소실 {len(missing_author)}/{n} — 변환 실패"
            health = jd_author["summary"]["judge_health"]
            print(f"⑤ 저자 축 변환: rows {health['n_rows']} (parse_fail {health['n_parse_fail']}) · "
                  f"validate OK · ledger 소실 {len(missing_author)}/{n} — 차단 해소")

            # ⑥ 요약
            print("⑥ 전 산출물 validate 통과. 스텁 수치는 배관 확인용 — 인용 금지.")
            print(f"[rehearse_splice] 완주 · LLM 호출 0 · 임시 루트 {data_root} (자동 삭제)")
        finally:
            paths.DATA = old_data


if __name__ == "__main__":
    main()
