# -*- coding: utf-8 -*-
"""[접합 계층 · 요한] 비교 실험 우리 판 전용 러너 — PREREG_COMPARE 정본 실행 경로.

지위: **비교 실험(0543·0248·0262) 우리 판의 유일한 실행기.** 재검수(MUTUAL_REVIEW
2026-08-11 C-1~C-4·R-1) 교훈으로 rehearse_splice 편집 대신 신설했다 — 리허설 러너의
유산(임시 사본·자동 삭제·리허설용 assert)을 물려받지 않기 위해 목적을 하나로 좁힌다.

하는 일 (이슈 1건 단위 · PREREG §1-2 우리 판 그대로):
  ① 발화   — debate_engine.run(config 좌표 그대로, 완주 판 재사용 가드)
  ⑤ 저자 축 — 발화×팩트목록, gpt-5·temp0·n=1 (axis_probe 조립·파싱 계승)
  ⑤′ stance — 저자 evaluate_stance 계승 (관찰 지위 — 결과 변수 아님)
그 외는 없다. ②우리 축 판정·③ledger·④창은 이 실험의 비교 축이 아니다(역리뷰 B-1).

설계 원칙 (재검수 6건이 각각 규칙이 됐다):
  - 기본 모드 = 계획(0콜·무기록): 출력 경로·기존 체크포인트·계획 콜 수만 보여준다.
    임시 디렉터리·사본이 아예 없으므로 산출물 자동 삭제류(C-2)가 구조적으로 불가능.
  - 모든 쓰기는 부모 디렉터리를 먼저 만든다(C-1). 깨끗한 데이터 루트에서 완주 보장.
  - 극단값(FAR 0.0/1.0)은 유효한 결과다 — 실행을 죽이지 않고 G5(원문 확인 의무)
    표시와 함께 보고한다(C-3). 구조 이상은 modules.validate 가 잡는다.
  - 체크포인트 행은 자기 실행 좌표 전부(issue·run·prompt/facts/config 지문)를 지니고,
    재사용은 전 좌표 일치 시에만 — 이슈 간 오재사용 불가(C-4).
  - 상한 2중: 이슈별 --max-calls ≤ 116(PREREG §6) + 블록 346(PREREG §4 우리 판,
    M-2 확정: 승인 경계 = 블록 상한)을 append 전용 콜 원장으로 프로세스 간 강제.
    예약 후 호출 — 초과는 API 호출 전에 즉사한다.

사용 (전체 명령은 PREREG §7 append 가 정본):
  계획(0콜):  PYTHONUTF8=1 python experiments/paper_repro/compare_ours.py \
                --issue issue_ethics_0543 --run-id compare2_0543 \
                --config experiments/paper_repro/configs/compare_v2.yaml
  실행:       위 명령 + --live --max-calls 116  (요한 실호출 승인 후에만)
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from modules import authors_prompts, debate_engine, llm, paths  # noqa: E402
from modules import validate as validate_mod  # noqa: E402
from experiments.judge_axis.axis_probe import (  # noqa: E402 — import만(폴더 무수정)
    build_author_prompt, parse_matched)
import bridge  # noqa: E402

# --- 고정 좌표 (PREREG §1) ----------------------------------------------------
AXIS_MODEL = "gpt-5"        # 저자 evaluation.py 상수 — config 로 바꿀 수 없다
AXIS_TEMP = 0.0
AXIS_N = 1
ISSUE_CAP = 116             # ceil(96×1.2) — PREREG §6 (이슈별)
BLOCK_CAP = 346             # ceil(288×1.2) — PREREG §4 우리 판 블록(M-2: 승인 경계)
BLOCK_LEDGER_NAME = "compare_ours_call_ledger.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _validate(path: Path) -> None:
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        try:
            validate_mod.validate(path)
        except SystemExit:
            print(buf.getvalue(), file=sys.stderr, end="")
            raise


class CallGate:
    """이슈별 상한 + 블록 원장(346) — 예약 후 호출.

    블록 원장은 append 전용 jsonl(행 1줄 = 예약 1콜). 프로세스가 갈라져도(이슈 3건을
    각각 실행) 같은 파일을 세므로 '이슈별 116 × 3 = 348 > 346' 우회가 안 된다(M-2).
    예약이 호출보다 먼저라 초과분은 API 에 닿기 전에 죽는다 — 크래시 시 원장이
    실지출보다 1콜 많게 남을 수 있는데, 비용 안전장치이므로 보수적인 쪽을 택한다."""

    def __init__(self, ledger_path: Path, issue_id: str, run_id: str, max_calls: int):
        self.path = ledger_path
        self.issue_id, self.run_id = issue_id, run_id
        self.max_calls = max_calls
        self.n = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def block_spent(self) -> int:
        if not self.path.exists():
            return 0
        return sum(1 for l in self.path.read_text(encoding="utf-8").splitlines()
                   if l.strip())

    def reserve(self, stage: str) -> None:
        if self.n >= self.max_calls:
            raise SystemExit(
                f"이슈 상한 --max-calls {self.max_calls} 도달 — 중단(체크포인트 보존, "
                "재실행하면 이어서 재개)")
        spent = self.block_spent()
        if spent >= BLOCK_CAP:
            raise SystemExit(
                f"블록 상한 {BLOCK_CAP} 도달(원장 {self.path.name}: {spent}행) — "
                "PREREG §4 우리 판 블록 초과. 실행 금지: 원장을 요한과 함께 확인하라.")
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), "issue_id": self.issue_id,
                                 "run_id": self.run_id, "stage": stage,
                                 "seq_in_process": self.n + 1},
                                ensure_ascii=False) + "\n")
            fh.flush()
        self.n += 1


def check_full_identity(rec: dict, expect: dict, path: Path) -> None:
    """체크포인트 행 재사용 관문 — 전 좌표 일치 시에만(C-4). 이 러너의 행은 태어날 때부터
    전 좌표를 지니므로 부재(None)도 불일치다 — 레거시 허용 없음."""
    mismatch = [f"{k} {rec.get(k)!r}≠{v!r}" for k, v in expect.items()
                if rec.get(k) != v]
    if mismatch:
        raise SystemExit(
            f"체크포인트 행 좌표 불일치({rec.get('round')},{rec.get('agent_id')}): "
            + " · ".join(mismatch) + f"\n  파일 확인: {path}\n"
            "  다른 이슈/조건의 행을 조용히 재사용하지 않는다 — run_id 를 바꾸거나 "
            "파일을 .mismatch-<ts> 로 밀어낸 뒤 재실행하라.")


def _load_rows(ck: Path) -> dict:
    done = {}
    if ck.exists():
        for line in ck.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r["round"], r["agent_id"])] = r
    return done


def debate_status(dp: Path, cfg_path: Path, expected_utts: int) -> tuple[str, int]:
    """("absent"|"partial"|"complete", n_utt). complete 는 run_meta config 지문까지
    일치해야 한다 — 불일치·run_meta 부재는 즉사(부재≠일치)."""
    if not dp.exists():
        return "absent", 0
    events = [json.loads(l) for l in dp.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    n_utt = sum(1 for e in events if e.get("event") == "utterance")
    if n_utt != expected_utts:
        return "partial", n_utt
    first = events[0] if events else {}
    if first.get("event") != "run_meta":
        raise SystemExit(f"debate 재사용 거부: run_meta 부재 — 좌표를 검증할 수 없다: {dp}")
    cfg_sha = _sha256_file(cfg_path)
    ref = first.get("config_ref") or {}
    if ref.get("sha256") != cfg_sha:
        raise SystemExit(
            f"debate 재사용 거부: config 지문 불일치 — 기존 판={ref.get('name')}"
            f"({str(ref.get('sha256'))[:12]}…) 현재={cfg_path.name}({cfg_sha[:12]}…)\n"
            "  조건 변경 = 새 run_id/새 yaml.")
    return "complete", n_utt


def run(issue_id: str, run_id: str, config_path: Path, source_data: Path, *,
        live: bool = False, max_calls: int = 0,
        utterance_fn=None, responder=None) -> dict:
    """계획(기본·0콜·무기록) 또는 실행. utterance_fn·responder 는 테스트 주입용 —
    둘 다 주거나 둘 다 생략(하나만 주면 나머지가 실호출로 새는 혼합 모드라 거부)."""
    if (utterance_fn is None) != (responder is None):
        raise ValueError("utterance_fn·responder 는 둘 다 주입하거나 둘 다 생략 — "
                         "혼합하면 스텁 실행 중 실호출이 샌다")
    test_mode = utterance_fn is not None
    config_path = Path(config_path)
    data_root = Path(source_data).resolve()
    if not data_root.is_dir():
        raise SystemExit(f"데이터 루트 부재: {data_root}")

    old_data = paths.DATA
    old_max_tokens = llm.MAX_TOKENS
    real_obtain = llm.obtain_response
    paths.DATA = data_root
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        rounds = int(cfg["rounds"])
        for p in (paths.issue(issue_id), paths.facts(issue_id), paths.assignment(issue_id)):
            if not p.exists():
                raise SystemExit(f"입력 부재: {p}")
        facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
        facts = facts_doc["facts"]
        assignment = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
        issue_doc = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
        n_agents = len(assignment["agents"])
        expected_utts = n_agents * (rounds + 1)

        config_sha = _sha256_file(config_path)
        facts_sha = _sha256_file(paths.facts(issue_id))
        prompt_ver = authors_prompts.version_tag()

        dp = paths.debate(issue_id, run_id)
        d_status, n_utt = debate_status(dp, config_path, expected_utts)
        ck_axis = paths.raw_calls(f"compare_axis_{issue_id}_{run_id}.jsonl")
        ck_stance = paths.raw_calls(f"compare_stance_{issue_id}_{run_id}.jsonl")
        axis_done = _load_rows(ck_axis)
        stance_done = _load_rows(ck_stance)
        ledger_path = paths.raw_calls(BLOCK_LEDGER_NAME)
        block_spent = (sum(1 for l in ledger_path.read_text(encoding="utf-8").splitlines()
                           if l.strip()) if ledger_path.exists() else 0)

        plan_utt = 0 if d_status == "complete" else expected_utts
        plan_axis = expected_utts - len(axis_done)
        plan_stance = expected_utts - len(stance_done)
        planned = plan_utt + plan_axis + plan_stance
        report = {"issue_id": issue_id, "run_id": run_id, "config": config_path.name,
                  "config_sha256": config_sha, "facts_sha256": facts_sha,
                  "debate_status": d_status, "n_facts": len(facts),
                  "planned_calls": {"utterance": plan_utt, "axis_author": plan_axis,
                                    "stance": plan_stance, "total": planned},
                  "issue_cap": ISSUE_CAP, "block_cap": BLOCK_CAP,
                  "block_spent": block_spent,
                  "outputs": {
                      "debate": str(dp),
                      "judgment_author": str(paths.judgment(issue_id, f"{run_id}_author")),
                      "stance_summary": str(data_root /
                                            f"stance_summary_{issue_id}_{run_id}.json"),
                      "axis_checkpoint": str(ck_axis),
                      "stance_checkpoint": str(ck_stance),
                      "block_ledger": str(ledger_path)}}

        if not live:
            print(f"[계획] {issue_id} · {run_id} · config {config_path.name}"
                  f"({config_sha[:12]}…) · facts {len(facts)}개({facts_sha[:12]}…)")
            print(f"  debate: {d_status}"
                  + (f" ({n_utt}/{expected_utts}발화)" if d_status != "absent" else "")
                  + f" · 축 체크포인트 {len(axis_done)}행 · stance {len(stance_done)}행")
            if d_status == "partial":
                print(f"  ⚠ 부분 debate — live 는 거부된다. {dp} 를 "
                      ".incomplete-<ts> 로 밀어낸 뒤 재실행하라.")
            print(f"  계획 콜: 발화 {plan_utt} + 저자 축 {plan_axis} + stance {plan_stance}"
                  f" = {planned} (이슈 상한 {ISSUE_CAP})")
            print(f"  블록 원장: {block_spent}/{BLOCK_CAP} → 실행 후 "
                  f"{block_spent + planned}/{BLOCK_CAP}")
            for k, v in report["outputs"].items():
                print(f"  산출 {k}: {v}")
            print("  [계획 모드 — 호출 0 · 기록 0. 실행은 --live --max-calls 116 + 요한 승인]")
            return report

        # ---------------- live ----------------
        if max_calls <= 0:
            raise SystemExit("--live 는 --max-calls 명시 필수 — 승인된 예산만큼만")
        if max_calls > ISSUE_CAP:
            raise SystemExit(f"--max-calls {max_calls} > 이슈 상한 {ISSUE_CAP} "
                             "(계획 96/건 × 1.2 — PREREG §6)")
        if d_status == "partial":
            raise SystemExit(
                f"debate 파일이 부분 상태({n_utt}/{expected_utts}발화): {dp}\n"
                "  .incomplete-<ts> 로 밀어낸 뒤 재실행하라 — temp>0 발화에 이어 뽑으면 "
                "다른 토론이 된다(8/10 사고).")
        if block_spent + planned > BLOCK_CAP:
            raise SystemExit(
                f"블록 상한 사전 검사 실패: 원장 {block_spent} + 계획 {planned} > "
                f"{BLOCK_CAP} (PREREG §4) — 호출 전 중단. 원장을 요한과 확인하라.")

        gate = CallGate(ledger_path, issue_id, run_id, max_calls)
        llm.MAX_TOKENS = 8192  # 편차 P-1: 저자는 상한 미전송 — 러너에서만 완화
        stage_ref = ["utterance"]

        if not test_mode:
            # 실호출 전 좌표 예검(키·온도) — 발화 모델은 debate 필요 시에만
            if plan_utt:
                llm.preflight(cfg["debate_model"],
                              temperature=float(cfg["debate_temperature"]))
            llm.preflight(AXIS_MODEL, temperature=AXIS_TEMP)

            def gated(*a, **kw):
                gate.reserve(stage_ref[0])
                return real_obtain(*a, **kw)

            llm.obtain_response = gated  # 발화(엔진)·판정·stance 전부 이 관문을 지난다

        # ① 발화
        if d_status == "complete":
            print(f"① 기존 debate 재사용({n_utt}발화) — config 지문 일치, 콜 0")
        else:
            if test_mode:
                def _gated_utt(inputs, model="", temperature=0.0):
                    gate.reserve("utterance")
                    return utterance_fn(inputs, model=model, temperature=temperature)

                def _no_vote(fact, utts):
                    raise AssertionError("ledger_mode=off 에서 judge_vote 호출 — 계약 위반")

                dp = debate_engine.run(issue_id, run_id, config_path,
                                       utterance_fn=_gated_utt, judge_vote_fn=_no_vote)
            else:
                dp = debate_engine.run(issue_id, run_id, config_path)
            _, n_utt = debate_status(dp, config_path, expected_utts)
        events = [json.loads(l) for l in dp.read_text(encoding="utf-8").splitlines()
                  if l.strip()]
        utts = [e for e in events if e.get("event") == "utterance"]
        if len(utts) != expected_utts:
            raise SystemExit(f"발화 수 불일치: {len(utts)}≠{expected_utts} — {dp}")
        _validate(dp)
        print(f"① debate: 발화 {len(utts)} · validate OK")

        def call_model(prompt: str) -> str:
            if test_mode:
                gate.reserve(stage_ref[0])
                return responder(prompt, model=AXIS_MODEL, temperature=AXIS_TEMP)
            return llm.obtain_response(prompt, model=AXIS_MODEL, temperature=AXIS_TEMP)

        # ⑤ 저자 축 (발화×팩트목록 · gpt-5 · temp0 · n=1)
        stage_ref[0] = "axis_author"
        rows = []
        with ck_axis.open("a", encoding="utf-8") as fh:
            for u in utts:
                key = (u["round"], u["agent_id"])
                prompt = build_author_prompt(facts, u.get("response_text", ""))
                expect = {"issue_id": issue_id, "run_id": run_id,
                          "model": AXIS_MODEL, "temperature": AXIS_TEMP, "n": AXIS_N,
                          "axis": "author_evaluate_fact", "prompt_ver": prompt_ver,
                          "prompt_sha256": _sha256_text(prompt),
                          "facts_sha256": facts_sha, "config_sha256": config_sha}
                if key in axis_done:
                    check_full_identity(axis_done[key], expect, ck_axis)
                    rows.append(axis_done[key])
                    continue
                raw = call_model(prompt)
                idx, status = parse_matched(raw, len(facts))
                rec = {"round": u["round"], "agent_id": u["agent_id"], **expect,
                       "matched_fact_ids": idx, "parse": status,
                       "raw_response": raw}  # 규약 5 — 원문 그대로
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                rows.append(rec)
        jd_author = bridge.author_rows_to_judgment(
            rows, facts_doc, issue_id=issue_id, run_id=f"{run_id}_author",
            prompt_ver=prompt_ver)
        jpa = paths.judgment(issue_id, f"{run_id}_author")
        jpa.parent.mkdir(parents=True, exist_ok=True)  # C-1: 깨끗한 루트에서도 완주
        jpa.write_text(json.dumps(jd_author, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        _validate(jpa)
        fars = [s["far_system"] for s in jd_author["summary"]["far_by_stage"]]
        health = jd_author["summary"]["judge_health"]
        extreme = [f for f in fars if f in (0.0, 1.0)]
        g5 = (" ⚠ G5: 극단값 포함 — 원문 2건 이상 확인 전 보고 금지" if extreme else "")
        print(f"⑤ 저자 축: rows {health['n_rows']} (parse_fail {health['n_parse_fail']}) · "
              f"far_by_stage {fars} · validate OK{g5}")

        # ⑤′ stance (관찰 지위)
        stage_ref[0] = "stance"
        question = issue_doc.get("question") or issue_doc["title"]
        srows = []
        with ck_stance.open("a", encoding="utf-8") as fh:
            for u in utts:
                key = (u["round"], u["agent_id"])
                prompt = (authors_prompts.load("evaluate_stance")
                          .replace("<===question===>", question)
                          .replace("<===text===>", u.get("response_text", "")))
                expect = {"issue_id": issue_id, "run_id": run_id,
                          "model": AXIS_MODEL, "temperature": AXIS_TEMP, "n": AXIS_N,
                          "axis": "author_evaluate_stance", "prompt_ver": prompt_ver,
                          "prompt_sha256": _sha256_text(prompt),
                          "facts_sha256": facts_sha, "config_sha256": config_sha}
                if key in stance_done:
                    check_full_identity(stance_done[key], expect, ck_stance)
                    srows.append(stance_done[key])
                    continue
                raw = call_model(prompt)
                rec = {"round": u["round"], "agent_id": u["agent_id"], **expect,
                       "parsed": bridge.parse_stance(raw),
                       "raw_response": raw}  # 규약 5 — 원문 그대로
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                srows.append(rec)
        stance_doc = bridge.stance_rows_to_summary(
            srows, assignment, issue_id=issue_id, run_id=run_id)
        sp = data_root / f"stance_summary_{issue_id}_{run_id}.json"
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(stance_doc, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        ss = stance_doc["summary"]
        print(f"⑤′ stance: rows {ss['n_rows']} (parse_fail {ss['n_parse_fail']}) · "
              f"라운드별 유지율 {ss['match_rate_by_round']} (관찰 지위)")

        report["calls_used"] = gate.n
        report["block_spent_after"] = gate.block_spent()
        report["far_by_stage"] = fars
        print(f"[compare_ours] 완주 · 이 프로세스 호출 {gate.n}/{max_calls} · "
              f"블록 원장 {report['block_spent_after']}/{BLOCK_CAP} · 루트 {data_root} (보존)")
        return report
    finally:
        paths.DATA = old_data
        llm.MAX_TOKENS = old_max_tokens
        llm.obtain_response = real_obtain


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--config", type=Path, required=True,
                    help="configs/compare_v2.yaml (조건 변경 = 새 yaml)")
    ap.add_argument("--source-data", type=Path, default=HERE / "data",
                    help="데이터 루트 — 직접 산출(사본·임시 폴더 없음, 규약 8)")
    ap.add_argument("--live", action="store_true",
                    help="실호출. --max-calls 필수, 요한 승인 후에만")
    ap.add_argument("--max-calls", type=int, default=0,
                    help=f"이 프로세스의 호출 상한 (이슈 상한 {ISSUE_CAP} 초과 거부)")
    args = ap.parse_args()
    run(args.issue, args.run_id, args.config, args.source_data,
        live=args.live, max_calls=args.max_calls)


if __name__ == "__main__":
    main()
