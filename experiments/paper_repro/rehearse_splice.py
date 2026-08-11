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

import argparse
import contextlib
import hashlib
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

from modules import access_window, authors_prompts, debate_engine, ledger, llm, paths  # noqa: E402
from modules import judge as judge_mod  # noqa: E402
from modules import validate as validate_mod  # noqa: E402
from experiments.judge_axis.axis_probe import (  # noqa: E402 — import만(폴더 무수정)
    build_author_prompt, offline_matched, parse_matched)
import bridge  # noqa: E402

CFG = HERE / "configs" / "fx_smoke.yaml"
# 기본은 픽스처 리허설. --source-data / --issue 로 라이브 산출에도 같은 사슬을 물릴 수
# 있다(2026-08-10 추가 — 1차 트랜치 20건이 파이프라인 전 구간을 통과하는지 실증용).
# 어느 경우든 원본 디렉터리는 불변 — 사본 위에서만 돈다.


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


# --- 재사용 관문 (PR#34 리뷰: 발화 수·파일 존재만으로 다른 조건의 산출물을 조용히
#     소비하는 결함 차단 — 좌표 대조 후 불일치 즉사) ---------------------------------

def check_debate_provenance(debate_path: Path, cfg_path: Path) -> None:
    """기존 debate 재사용 전 run_meta.config_ref.sha256 을 현재 config 와 대조한다.
    run_meta 부재(구 로그)는 '모름'이므로 재사용을 거부한다 — 재사용은 좌표가
    증명될 때만 허용(부재≠일치)."""
    first = None
    for line in debate_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            first = json.loads(line)
            break
    if not first or first.get("event") != "run_meta":
        raise SystemExit(
            f"debate 재사용 거부: run_meta 부재 — 조건 좌표를 검증할 수 없다: {debate_path}\n"
            "  다른 run_id 를 쓰거나 파일을 .incomplete-<ts> 로 밀어낸 뒤 재실행하라.")
    cfg_sha = hashlib.sha256(Path(cfg_path).read_bytes()).hexdigest()
    ref = first.get("config_ref") or {}
    if ref.get("sha256") != cfg_sha:
        raise SystemExit(
            f"debate 재사용 거부: config 지문 불일치 — 기존 판={ref.get('name')}"
            f"({str(ref.get('sha256'))[:12]}…) 현재={Path(cfg_path).name}({cfg_sha[:12]}…)\n"
            "  같은 run_id 로 다른 조건을 돌리려 한 것 — 조건 변경 = 새 run_id/새 yaml.")


def check_judgment_provenance(jd: dict, issue_id: str, run_id: str,
                              expected_stages: int, fact_ids: set[str]) -> None:
    """기존 judgment 재사용 전 좌표(issue·run·stage 수·팩트 집합)를 대조한다."""
    problems = []
    if jd.get("issue_id") != issue_id:
        problems.append(f"issue_id {jd.get('issue_id')}≠{issue_id}")
    if jd.get("run_id") != run_id:
        problems.append(f"run_id {jd.get('run_id')}≠{run_id}")
    stages = jd.get("stages") or []
    if len(stages) != expected_stages:
        problems.append(f"stage 수 {len(stages)}≠{expected_stages}")
    if stages:
        got = {f["fact_id"] for f in stages[0].get("facts", [])}
        if got != fact_ids:
            problems.append(f"팩트 집합 상이(기존 {len(got)}개/현재 {len(fact_ids)}개)")
    if problems:
        raise SystemExit(
            "judgment 재사용 거부: " + " · ".join(problems) +
            " — 다른 조건의 판정을 조용히 소비하지 않는다. 파일을 밀어내고 재실행하라.")


def check_row_identity(rec: dict, model: str, temperature: float, axis: str,
                       path: Path) -> None:
    """축/입장 체크포인트 행 재사용 전 좌표 대조. 기존 원장(pilot1)부터 세 필드가
    전부 있으므로 부재도 불일치로 처리한다(재사용은 좌표가 증명될 때만)."""
    mismatch = []
    if rec.get("model") != model:
        mismatch.append(f"model {rec.get('model')}≠{model}")
    if rec.get("temperature") != temperature:
        mismatch.append(f"temperature {rec.get('temperature')}≠{temperature}")
    if rec.get("axis") != axis:
        mismatch.append(f"axis {rec.get('axis')}≠{axis}")
    if mismatch:
        raise SystemExit(
            f"체크포인트 행 좌표 불일치({rec.get('round')},{rec.get('agent_id')}): "
            + " · ".join(mismatch) + f" — 파일 확인: {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-data", type=Path, default=HERE / "fixtures" / "data",
                    help="사슬을 물릴 데이터 루트(불변 — 사본 위에서 돈다)")
    ap.add_argument("--issue", default="issue_repro_fx")
    ap.add_argument("--run-id", default="fxsmoke")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="지정 시 임시 디렉터리 대신 여기 사본을 만들고 보존(뷰어 확인용)")
    ap.add_argument("--config", type=Path, default=CFG,
                    help="config yaml (조건 변경 = 새 yaml)")
    ap.add_argument("--live", action="store_true",
                    help="스텁 대신 실호출(발화·판정 양축). --max-calls 필수, 승인 후에만")
    ap.add_argument("--in-place", action="store_true",
                    help="사본 없이 --source-data 에 직접 산출(실호출 정식 실행용, 규약 8)")
    ap.add_argument("--max-calls", type=int, default=0)
    args = ap.parse_args()
    issue_id, run_id = args.issue, args.run_id
    cfg_path = args.config

    if args.live:
        if args.max_calls <= 0:
            raise SystemExit("--live 는 --max-calls(전역 상한) 명시 필수 — 승인된 예산만큼만")
        # 편차 P-1: 저자는 상한 미전송 — 러너에서만 완화(llm.py 무수정)
        llm.MAX_TOKENS = 8192
        real_call = llm.obtain_response
        counter = {"n": 0}

        def counted(*a, **kw):
            if counter["n"] >= args.max_calls:
                raise RuntimeError(f"전역 호출 상한 {args.max_calls} 도달 — 중단(체크포인트 보존)")
            counter["n"] += 1
            return real_call(*a, **kw)

        llm.obtain_response = counted  # 발화(엔진)·판정(judge)·저자 축 전부 이 한 카운터를 지난다

    if args.in_place:
        ctx = contextlib.nullcontext(None)  # 사본 없음 — 산출이 source-data 에 직접 남는다
    elif args.out_dir is not None:
        ctx = contextlib.nullcontext(str(args.out_dir))
    else:
        ctx = tempfile.TemporaryDirectory(prefix="paper_repro_splice_")
    with ctx as td:
        if args.in_place:
            data_root = Path(args.source_data).resolve()
        else:
            data_root = Path(td) / "data"
            if data_root.exists():
                shutil.rmtree(data_root)
            shutil.copytree(args.source_data, data_root)
        old_data = paths.DATA
        paths.DATA = data_root
        try:
            facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
            facts = facts_doc["facts"]
            facts_by_id = {f["fact_id"]: f for f in facts}
            assignment = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))

            # ① 토론 — 기본은 스텁(실호출 0), --live 면 엔진이 실호출(자체 체크포인트)
            if args.live:
                # 재생성 방지 가드 (2026-08-10 실사고: 완주 판을 --live 재실행하자 엔진이
                # 발화 32콜을 새로 뽑아 기존 판정들과 짝이 안 맞는 다른 토론이 됐다.
                # temp>0 발화는 재생성 = 다른 데이터다 — 완주 판은 절대 다시 만들지 않는다.)
                import yaml as _yaml
                _rounds = int(_yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
                              .get("rounds", 3))
                _expected = len(assignment["agents"]) * (_rounds + 1)
                _dp = paths.debate(issue_id, run_id)
                if _dp.exists():
                    _n = sum(1 for l in _dp.read_text(encoding="utf-8").splitlines()
                             if l.strip() and json.loads(l).get("event") == "utterance")
                    if _n == _expected:
                        check_debate_provenance(_dp, cfg_path)  # 좌표 불일치면 즉사
                        debate_path = _dp
                        print(f"① 기존 debate 재사용({_n}발화) — 재생성 방지 가드+config 지문 일치, 콜 0")
                    else:
                        raise SystemExit(
                            f"debate 파일이 부분 상태({_n}/{_expected}발화): {_dp}\n"
                            "  mini_h2 관례대로 .incomplete-<ts> 로 밀어낸 뒤 재실행하라 — "
                            "부분 판 위에 이어 뽑으면 원장 정합이 깨진다.")
                else:
                    debate_path = debate_engine.run(issue_id, run_id, cfg_path)
            else:
                stub = _stub_utterance_factory(facts)
                debate_path = debate_engine.run(issue_id, run_id, cfg_path,
                                                utterance_fn=stub, judge_vote_fn=_stub_vote)
            events = [json.loads(l) for l in
                      debate_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            n_utt = sum(1 for e in events if e.get("event") == "utterance")
            n_seating = sum(1 for e in events if e.get("event") == "seating")
            _validate(debate_path)
            mode = "실호출" if args.live else f"스텁 호출 {stub._counter['n']}"
            print(f"① debate 완주: 발화 {n_utt} · seating {n_seating} · {mode} · validate OK")

            # ② 우리 축 judgment (3표 — live 면 실판정, 아니면 offline)
            jp = paths.judgment(issue_id, run_id)
            if args.live and jp.exists():
                # 재판정 방지 가드 — judge 단계엔 자체 체크포인트가 없다(같은 실사고).
                # PR#34 리뷰: 존재만으로 재사용하지 않고 좌표를 대조한다.
                jd_ours = json.loads(jp.read_text(encoding="utf-8"))
                check_judgment_provenance(
                    jd_ours, issue_id, run_id,
                    expected_stages=n_utt // len(assignment["agents"]),
                    fact_ids=set(facts_by_id))
                print("② 기존 judgment 재사용 — 재판정 방지 가드+좌표 일치, 콜 0")
            else:
                cfg = judge_mod._load_config(cfg_path)
                jd_ours = judge_mod.judge_debate(issue_id, run_id, cfg, offline=not args.live)
                jp.parent.mkdir(parents=True, exist_ok=True)
                jp.write_text(json.dumps(jd_ours, ensure_ascii=False, indent=2),
                              encoding="utf-8")
            _validate(jp)
            print(f"② 우리 축 judgment: stages {len(jd_ours['stages'])} · "
                  f"far_by_stage {[s['far_system'] for s in jd_ours['summary']['far_by_stage']]} · validate OK")

            # ③ ledger — fact_id 경로
            last_stage = jd_ours["stages"][-1]["stage"]
            missing_ours = ledger.missing_facts(jd_ours, last_stage)
            n = len(facts)
            if not args.live:
                # 스텁 전건 검증용 — 스텁은 팩트 2개를 되뇌므로 전부 소실이면 접합 실패다.
                # live 에서는 검사하지 않는다: FAR=1.0 은 유효한 극단값이며(재검수 C-3)
                # 결과에 따라 실행을 죽이는 것은 선택 편향이다. G5 로 원문 확인만 의무.
                assert 0 <= len(missing_ours) < n, \
                    f"ledger 퇴화: 소실 {len(missing_ours)}/{n} (전부/음수는 접합 실패)"
            print(f"③ ledger(우리 축): 마지막 stage 소실 {len(missing_ours)}/{n} — 오판 없음")

            # ④ access_window
            rep = access_window.report(jd_ours, assignment, events, facts_by_id)
            assert rep["status"] == "ok", f"access_window status={rep['status']}"
            assert not rep["meta"]["window"]["edges"].get("assumed_full"), \
                "seating 미인식 — 접합 실패"
            print(f"④ access_window: status=ok · records {len(rep['records'])} · "
                  f"rounds {rep['meta']['rounds']}")

            # ⑤ 저자 축 → bridge 변환 → ledger
            utts = [e for e in events if e.get("event") == "utterance"]
            if args.live:
                # 실판정: axis_probe 의 프롬프트 조립·파싱을 계승, 발화 단위 체크포인트
                ck = data_root / "raw_calls" / f"axis_author_{run_id}.jsonl"
                ck.parent.mkdir(parents=True, exist_ok=True)
                done = {}
                if ck.exists():
                    for line in ck.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            r = json.loads(line)
                            done[(r["round"], r["agent_id"])] = r
                rows = []
                with ck.open("a", encoding="utf-8") as fh:
                    for u in utts:
                        key = (u["round"], u["agent_id"])
                        if key in done:
                            check_row_identity(done[key], "gpt-5", 0.0,
                                               "author_evaluate_fact", ck)
                            rows.append(done[key])
                            continue
                        raw = llm.obtain_response(
                            build_author_prompt(facts, u.get("response_text", "")),
                            model="gpt-5", temperature=0.0)
                        idx, status = parse_matched(raw, len(facts))
                        rec = {"round": u["round"], "agent_id": u["agent_id"],
                               "model": "gpt-5", "temperature": 0.0, "n": 1,
                               "axis": "author_evaluate_fact",
                               "matched_fact_ids": idx, "parse": status,
                               "raw_response": raw}  # 규약 5 — 원문 그대로
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        fh.flush()
                        rows.append(rec)
                rows_for_bridge = rows
                author_prompt_ver = "delibtrace@afce3595"
            else:
                rows = []
                for u in utts:
                    idx = offline_matched(facts, u.get("response_text", ""))
                    rows.append({"round": u["round"], "agent_id": u["agent_id"],
                                 "matched_fact_ids": idx, "parse": "offline_stub"})
                # parse_fail 경로도 함께 리허설 — 마지막 행 하나를 실패로 바꾼 사본 검사
                rows_for_bridge = rows[:-1] + [dict(rows[-1], matched_fact_ids=None,
                                                    parse="parse_fail")]
                author_prompt_ver = "offline_stub"
            jd_author = bridge.author_rows_to_judgment(
                rows_for_bridge, facts_doc, issue_id=issue_id,
                run_id=f"{run_id}_author", prompt_ver=author_prompt_ver)
            jpa = paths.judgment(issue_id, f"{run_id}_author")
            jpa.parent.mkdir(parents=True, exist_ok=True)  # 재검수 C-1 계열: 쓰기 전 부모 보장
            jpa.write_text(json.dumps(jd_author, ensure_ascii=False, indent=2), encoding="utf-8")
            _validate(jpa)
            missing_author = ledger.missing_facts(jd_author, jd_author["stages"][-1]["stage"])
            if not args.live:
                # 스텁 전용 검증 — live 의 FAR=1.0 은 유효 극단값(재검수 C-3, 위 ③ 주석 참조).
                assert 0 <= len(missing_author) < n, \
                    f"저자 축 ledger 퇴화: 소실 {len(missing_author)}/{n} — 변환 실패"
            health = jd_author["summary"]["judge_health"]
            print(f"⑤ 저자 축 변환: rows {health['n_rows']} (parse_fail {health['n_parse_fail']}) · "
                  f"validate OK · ledger 소실 {len(missing_author)}/{n} — 차단 해소")

            # ⑤′ 입장 판정 (저자 evaluate_stance 계승) — 관찰 계기, §1 결과 변수 아님
            issue_doc = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
            question = issue_doc.get("question") or issue_doc["title"]
            # 극성 주의: 저자 evaluate_stance 의 YES = 행동 지지, 토론 pro 의 yes = 행동 비난.
            # 기대값은 bridge.stance_rows_to_summary 의 교정 매핑(pro→no)과 같아야 한다.
            expected_of = {ag["agent_id"]: ("no" if ag["stance"] == "pro" else "yes")
                           for ag in assignment["agents"]}
            if args.live:
                sck = data_root / "raw_calls" / f"stance_{run_id}.jsonl"
                sck.parent.mkdir(parents=True, exist_ok=True)
                sdone = {}
                if sck.exists():
                    for line in sck.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            r = json.loads(line)
                            sdone[(r["round"], r["agent_id"])] = r
                srows = []
                with sck.open("a", encoding="utf-8") as fh:
                    for u in utts:
                        key = (u["round"], u["agent_id"])
                        if key in sdone:
                            check_row_identity(sdone[key], "gpt-5", 0.0,
                                               "author_evaluate_stance", sck)
                            srows.append(sdone[key])
                            continue
                        prompt = (authors_prompts.load("evaluate_stance")
                                  .replace("<===question===>", question)
                                  .replace("<===text===>", u.get("response_text", "")))
                        raw = llm.obtain_response(prompt, model="gpt-5", temperature=0.0)
                        rec = {"round": u["round"], "agent_id": u["agent_id"],
                               "model": "gpt-5", "temperature": 0.0, "n": 1,
                               "axis": "author_evaluate_stance",
                               "parsed": bridge.parse_stance(raw),
                               "raw_response": raw}  # 규약 5 — 원문 그대로
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        fh.flush()
                        srows.append(rec)
            else:
                # 0콜 스텁 = 기대값 그대로 — 배관 검증용이라 match 1.0 이 정상
                srows = [{"round": u["round"], "agent_id": u["agent_id"],
                          "parsed": expected_of[u["agent_id"]],
                          "raw_response": expected_of[u["agent_id"]].upper()}
                         for u in utts]
            stance_doc = bridge.stance_rows_to_summary(
                srows, assignment, issue_id=issue_id, run_id=run_id)
            (data_root / f"stance_summary_{issue_id}_{run_id}.json").write_text(
                json.dumps(stance_doc, ensure_ascii=False, indent=2), encoding="utf-8")
            ss = stance_doc["summary"]
            tag = "" if args.live else " (스텁=기대값 — match 1.0 이 정상)"
            print(f"⑤′ 입장 판정: rows {ss['n_rows']} (parse_fail {ss['n_parse_fail']}) · "
                  f"라운드별 유지율 {ss['match_rate_by_round']}{tag}")

            # ⑥ 요약
            print("⑥ 전 산출물 validate 통과. 스텁 수치는 배관 확인용 — 인용 금지.")
            calls = counter["n"] if args.live else 0
            keep = "보존" if (args.in_place or args.out_dir) else "자동 삭제"
            print(f"[rehearse_splice] 완주 · LLM 호출 {calls} · 루트 {data_root} ({keep})")
        finally:
            paths.DATA = old_data


if __name__ == "__main__":
    main()
