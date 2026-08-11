# -*- coding: utf-8 -*-
"""[접합 계층 · 요한] 비교 실험 우리 판 전용 러너 — PREREG_COMPARE 정본 실행 경로.

지위: **비교 실험(0543·0248·0262) 우리 판의 유일한 실행기.** 재검수(MUTUAL_REVIEW
2026-08-11 C-1~C-4·R-1) 교훈으로 rehearse_splice 편집 대신 신설했다 — 리허설 러너의
유산(임시 사본·자동 삭제·리허설용 assert)을 물려받지 않기 위해 목적을 하나로 좁힌다.
재재검수(C-5~C-8) 반영: 상한은 "주장"이 아니라 "강제"가 되도록 —
단일 실행 잠금 아래 직렬 트랜치 + 지속 원장 + 전송 시도 퓨즈 + 입력 지문 manifest.

하는 일 (이슈별 · PREREG §1-2 우리 판 그대로 · 트랜치가 1~3건을 직렬 실행):
  ① 발화   — debate_engine.run(config 좌표 그대로, manifest 지문 관문 아래 재사용)
  ⑤ 저자 축 — 발화×팩트목록, gpt-5·temp0·n=1 (axis_probe 조립·파싱 계승)
  ⑤′ stance — 저자 evaluate_stance 계승 (관찰 지위 — 결과 변수 아님)
그 외는 없다. ②우리 축 판정·③ledger·④창은 이 실험의 비교 축이 아니다(역리뷰 B-1).

설계 원칙 (재검수 10건이 각각 규칙이 됐다):
  - 기본 모드 = 계획(0콜·무기록): 출력 경로·기존 체크포인트·계획 콜 수만 보여준다.
    임시 디렉터리·사본이 아예 없으므로 산출물 자동 삭제류(C-2)가 구조적으로 불가능.
  - 모든 쓰기는 부모 디렉터리를 먼저 만든다(C-1). 깨끗한 데이터 루트에서 완주 보장.
  - 극단값(FAR 0.0/1.0)은 유효한 결과다 — 실행을 죽이지 않고 G5(원문 확인 의무)
    표시와 함께 보고한다(C-3). 구조 이상은 modules.validate 가 잡는다.
  - 체크포인트 행은 자기 실행 좌표 전부(issue·run·prompt/facts/config/debate 지문)를
    지니고, 재사용은 전 좌표 일치 시에만 — 이슈 간 오재사용 불가(C-4).
  - **승인 경계 = 논리 콜**(질문 수 — PREREG G1 산술 단위, 요한 확정 8/11). 이슈별
    상한 116 은 원장 누적 기준의 **지속 상한**이다 — 프로세스 재시작으로 초기화되지
    않는다(C-6). 블록 346 은 같은 원장으로 트랜치 전체에 강제된다(M-2).
  - **전송 시도(HTTP attempt)는 별도 퓨즈**: llm 내부 재시도(최대 5회)까지 세는 별도
    원장 + 상한(논리의 2배 — 이슈 232·블록 692). 정상 시 논리 1=전송 1 이라 안 보이고,
    재시도 폭주 시에만 걸린다(C-5). SystemExit 라 재시도 루프가 삼키지 못한다.
  - **live 는 단일 실행만**: OS 파일 잠금(프로세스 사망 시 자동 해제)으로 두 번째
    live 실행은 시작 전에 거부 — 유일 기록자 전제가 성립해 원장 경쟁이 없다(C-7).
    이슈 3건은 한 프로세스가 직렬로 돈다(트랜치).
  - debate 재사용은 config 만이 아니라 **입력 전부의 지문**(issue·facts·assignment ·
    debate_model·temp·prompt_ver)을 manifest 로 최초 생성 직전에 고정하고, 한 바이트라도
    다르면 거부한다(C-8). 산출 행은 debate 파일 지문에도 묶인다.

사용 (전체 명령은 PREREG §8 append 가 정본):
  계획(0콜):  PYTHONUTF8=1 python experiments/paper_repro/compare_ours.py \
                --issues issue_ethics_0543,issue_ethics_0248,issue_ethics_0262 \
                --run-prefix compare2 --config experiments/paper_repro/configs/compare_v2.yaml
  실행:       위 명령 + --live --max-calls 116  (요한 실호출 승인 후에만)
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
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

# --- 고정 좌표 (PREREG §1·§8) -------------------------------------------------
AXIS_MODEL = "gpt-5"        # 저자 evaluation.py 상수 — config 로 바꿀 수 없다
AXIS_TEMP = 0.0
AXIS_N = 1
ISSUE_CAP = 116             # 논리 콜 · 이슈별 지속 상한 = ceil(96×1.2) — PREREG §6
BLOCK_CAP = 346             # 논리 콜 · 블록(승인 경계 산술) = ceil(288×1.2) — PREREG §4
ATTEMPT_ISSUE_CAP = 232     # 전송 시도 퓨즈 = 논리×2 (C-5 · 요한 동의 8/11)
ATTEMPT_BLOCK_CAP = 692
BLOCK_LEDGER_NAME = "compare_ours_call_ledger.jsonl"      # 논리 콜 원장(append 전용)
ATTEMPT_LEDGER_NAME = "compare_ours_attempt_ledger.jsonl"  # 전송 시도 계기판(append 전용)
LOCK_NAME = "compare_ours.lock"


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


class SingleInstanceLock:
    """live 단일 실행 강제(C-7) — OS 파일 잠금. 프로세스가 죽으면 OS 가 자동 해제하므로
    크래시 후 잔류 잠금이 없다. 두 번째 live 는 시작 전에(호출·기록 0) 거부된다."""

    def __init__(self, path: Path):
        self.path = path
        self._fh = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "a+b")
        fh.seek(0, 2)
        if fh.tell() == 0:
            fh.write(b"L")
            fh.flush()
        fh.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            raise SystemExit(
                f"다른 compare_ours live 실행이 잠금을 쥐고 있다: {self.path}\n"
                "  동시 실행 금지(C-7 — 원장 경쟁 방지). 기존 실행 종료 후 재시도하라.")
        self._fh = fh

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self._fh.close()
            self._fh = None


def _read_ledger(path: Path, issue_id: str) -> tuple[int, int]:
    """(블록 누적, 이 이슈 누적). 원장 행 파손은 즉사 — 셀 수 없는 원장으로 상한을
    주장하지 않는다."""
    block = issue = 0
    if not path.exists():
        return 0, 0
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            raise SystemExit(f"원장 손상({path.name}:{i + 1}) — 상한을 셀 수 없다. "
                             "파일을 요한과 확인하라(삭제 금지).")
        block += 1
        if rec.get("issue_id") == issue_id:
            issue += 1
    return block, issue


class CallGate:
    """append 전용 원장 이중 상한. 단일 실행 잠금(C-7) 아래 유일 기록자라는 전제로
    시작 시 1회 원장을 읽고(C-6: 재시작 누적 포함) 이후 메모리로 센다.
    예약이 호출보다 먼저 — 초과분은 API 에 닿기 전에 죽는다(크래시 시 원장이 실지출보다
    1행 많을 수 있는 보수 방향)."""

    def __init__(self, ledger_path: Path, issue_id: str, run_id: str, *,
                 max_calls: int | None, issue_cap: int, block_cap: int, label: str):
        self.path = ledger_path
        self.issue_id, self.run_id = issue_id, run_id
        self.max_calls = max_calls
        self.issue_cap, self.block_cap, self.label = issue_cap, block_cap, label
        self.n = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.block_spent, self.issue_spent = _read_ledger(ledger_path, issue_id)

    def preflight(self, planned: int) -> None:
        if self.issue_spent + planned > self.issue_cap:
            raise SystemExit(
                f"{self.label} 이슈 지속 상한 사전 검사 실패: 원장 누적 {self.issue_spent} "
                f"+ 계획 {planned} > {self.issue_cap} ({self.issue_id}) — 호출 전 중단(C-6). "
                "원장·체크포인트를 요한과 확인하라.")
        if self.block_spent + planned > self.block_cap:
            raise SystemExit(
                f"{self.label} 블록 상한 사전 검사 실패: 원장 {self.block_spent} + 계획 "
                f"{planned} > {self.block_cap} (PREREG §4) — 호출 전 중단.")

    def reserve(self, stage: str) -> None:
        if self.max_calls is not None and self.n >= self.max_calls:
            raise SystemExit(
                f"이 프로세스 상한 --max-calls {self.max_calls} 도달 — 중단"
                "(체크포인트 보존, 재실행하면 이어서 재개)")
        if self.issue_spent >= self.issue_cap:
            raise SystemExit(
                f"{self.label} 이슈 지속 상한 {self.issue_cap} 도달"
                f"({self.issue_id} 원장 누적) — 호출 전 중단(C-6).")
        if self.block_spent >= self.block_cap:
            raise SystemExit(
                f"{self.label} 블록 상한 {self.block_cap} 도달(원장 {self.path.name}) — "
                "호출 전 중단. 원장을 요한과 확인하라.")
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), "issue_id": self.issue_id,
                                 "run_id": self.run_id, "stage": stage,
                                 "seq_in_process": self.n + 1},
                                ensure_ascii=False) + "\n")
            fh.flush()
        self.n += 1
        self.issue_spent += 1
        self.block_spent += 1


def _wrap_dispatch(fn, attempt_gate: CallGate, stage_ref: list):
    """llm._DISPATCH 공급자 함수를 전송 시도 퓨즈로 감싼다(C-5) — llm.py 무수정(동범
    소관), 러너에서만. SystemExit 는 BaseException 이라 obtain_response 의
    `except Exception` 재시도 루프가 삼키지 못하고 그대로 중단된다."""
    def wrapped(model_id, inputs, temperature, reasoning="default"):
        attempt_gate.reserve(stage_ref[0])
        return fn(model_id, inputs, temperature, reasoning)
    return wrapped


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
    일치해야 한다 — 불일치·run_meta 부재는 즉사(부재≠일치). 입력(issue/facts/
    assignment) 지문은 manifest 관문(C-8)이 따로 본다."""
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


def _manifest_check(mp: Path, current: dict, d_status: str) -> list[str]:
    """C-8 — debate 입력 지문 manifest 대조. 반환 = 문제 목록(빈 목록이면 통과).
    manifest 는 debate 최초 생성 직전에 고정되고(live), 이후 어떤 재사용 경로도
    입력 전부의 지문 일치 없이는 열리지 않는다."""
    problems = []
    if mp.exists():
        saved = json.loads(mp.read_text(encoding="utf-8"))
        for k, v in current.items():
            if saved.get(k) != v:
                problems.append(f"manifest 불일치: {k} {str(saved.get(k))[:20]}…≠"
                                f"{str(v)[:20]}… — debate 생성 시점의 입력과 현재 파일이 "
                                "다르다(C-8). 조건 변경 = 새 run_id.")
    elif d_status != "absent":
        problems.append(f"debate 는 있는데 manifest 부재({mp.name}) — 입력 지문을 증명할 "
                        "수 없어 재사용 거부(부재≠일치, C-8).")
    return problems


def run(issue_id: str, run_id: str, config_path: Path, source_data: Path, *,
        live: bool = False, max_calls: int = 0,
        utterance_fn=None, responder=None) -> dict:
    """이슈 1건 실행(계획 기본·0콜·무기록). CLI 는 run_tranche 를 통해서만 live 에
    들어온다(단일 실행 잠금). utterance_fn·responder 는 테스트 주입용 — 둘 다 주거나
    둘 다 생략(하나만 주면 나머지가 실호출로 새는 혼합 모드라 거부)."""
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
    old_dispatch = None
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
        mp = paths.raw_calls(f"compare_manifest_{issue_id}_{run_id}.json")
        manifest = {"issue_id": issue_id, "run_id": run_id,
                    "config_name": config_path.name, "config_sha256": config_sha,
                    "issue_sha256": _sha256_file(paths.issue(issue_id)),
                    "facts_sha256": facts_sha,
                    "assignment_sha256": _sha256_file(paths.assignment(issue_id)),
                    "debate_model": cfg["debate_model"],
                    "debate_temperature": float(cfg["debate_temperature"]),
                    "prompt_ver": prompt_ver}
        manifest_problems = _manifest_check(mp, manifest, d_status)

        ck_axis = paths.raw_calls(f"compare_axis_{issue_id}_{run_id}.jsonl")
        ck_stance = paths.raw_calls(f"compare_stance_{issue_id}_{run_id}.jsonl")
        axis_done = _load_rows(ck_axis)
        stance_done = _load_rows(ck_stance)
        ledger_path = paths.raw_calls(BLOCK_LEDGER_NAME)
        attempt_path = paths.raw_calls(ATTEMPT_LEDGER_NAME)
        block_spent, issue_spent = _read_ledger(ledger_path, issue_id)
        att_block, att_issue = _read_ledger(attempt_path, issue_id)

        plan_utt = 0 if d_status == "complete" else expected_utts
        plan_axis = expected_utts - len(axis_done)
        plan_stance = expected_utts - len(stance_done)
        planned = plan_utt + plan_axis + plan_stance
        report = {"issue_id": issue_id, "run_id": run_id, "config": config_path.name,
                  "config_sha256": config_sha, "facts_sha256": facts_sha,
                  "debate_status": d_status, "n_facts": len(facts),
                  "manifest_problems": manifest_problems,
                  "planned_calls": {"utterance": plan_utt, "axis_author": plan_axis,
                                    "stance": plan_stance, "total": planned},
                  "issue_cap": ISSUE_CAP, "block_cap": BLOCK_CAP,
                  "block_spent": block_spent, "issue_spent": issue_spent,
                  "attempt_spent": {"block": att_block, "issue": att_issue},
                  "outputs": {
                      "debate": str(dp),
                      "judgment_author": str(paths.judgment(issue_id, f"{run_id}_author")),
                      "stance_summary": str(data_root /
                                            f"stance_summary_{issue_id}_{run_id}.json"),
                      "axis_checkpoint": str(ck_axis),
                      "stance_checkpoint": str(ck_stance),
                      "manifest": str(mp),
                      "block_ledger": str(ledger_path),
                      "attempt_ledger": str(attempt_path)}}

        if not live:
            print(f"[계획] {issue_id} · {run_id} · config {config_path.name}"
                  f"({config_sha[:12]}…) · facts {len(facts)}개({facts_sha[:12]}…)")
            print(f"  debate: {d_status}"
                  + (f" ({n_utt}/{expected_utts}발화)" if d_status != "absent" else "")
                  + f" · manifest {'통과' if not manifest_problems else '문제'}"
                  + f" · 축 체크포인트 {len(axis_done)}행 · stance {len(stance_done)}행")
            for pb in manifest_problems:
                print(f"  ⚠ {pb}")
            if d_status == "partial":
                print(f"  ⚠ 부분 debate — live 는 거부된다. {dp} 를 "
                      ".incomplete-<ts> 로 밀어낸 뒤 재실행하라.")
            print(f"  계획 콜: 발화 {plan_utt} + 저자 축 {plan_axis} + stance {plan_stance}"
                  f" = {planned} (이슈 지속 상한 {ISSUE_CAP} · 원장 누적 {issue_spent})")
            print(f"  논리 원장: 블록 {block_spent}/{BLOCK_CAP} → 실행 후 "
                  f"{block_spent + planned}/{BLOCK_CAP} · 전송 계기판: "
                  f"{att_block}/{ATTEMPT_BLOCK_CAP}")
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
        if manifest_problems:
            raise SystemExit("입력 지문 관문 실패(C-8) — 호출 전 중단:\n  "
                             + "\n  ".join(manifest_problems))
        if d_status == "partial":
            raise SystemExit(
                f"debate 파일이 부분 상태({n_utt}/{expected_utts}발화): {dp}\n"
                "  .incomplete-<ts> 로 밀어낸 뒤 재실행하라 — temp>0 발화에 이어 뽑으면 "
                "다른 토론이 된다(8/10 사고).")

        gate = CallGate(ledger_path, issue_id, run_id, max_calls=max_calls,
                        issue_cap=ISSUE_CAP, block_cap=BLOCK_CAP, label="논리")
        gate.preflight(planned)
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
            # C-5: 공급자 전송 함수를 시도 퓨즈로 감싼다 — 논리 1콜의 내부 재시도까지 센다
            attempt_gate = CallGate(attempt_path, issue_id, run_id, max_calls=None,
                                    issue_cap=ATTEMPT_ISSUE_CAP,
                                    block_cap=ATTEMPT_BLOCK_CAP, label="전송")
            old_dispatch = dict(llm._DISPATCH)
            for prov, fn in old_dispatch.items():
                llm._DISPATCH[prov] = _wrap_dispatch(fn, attempt_gate, stage_ref)
        else:
            attempt_gate = None  # 스텁은 전송이 없다 — 계기판은 실호출 경로 전용

        # ① 발화
        if d_status == "complete":
            print(f"① 기존 debate 재사용({n_utt}발화) — config·manifest 지문 일치, 콜 0")
        else:
            if not mp.exists():
                # C-8: debate 최초 생성 직전에 입력 지문을 고정한다
                mp.parent.mkdir(parents=True, exist_ok=True)
                mp.write_text(json.dumps({**manifest, "created_at": _now()},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
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
        debate_sha = _sha256_file(dp)  # 산출 행을 이 debate 바이트에 묶는다(C-8)
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
                          "facts_sha256": facts_sha, "config_sha256": config_sha,
                          "debate_sha256": debate_sha}
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
                          "facts_sha256": facts_sha, "config_sha256": config_sha,
                          "debate_sha256": debate_sha}
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
        report["block_spent_after"] = gate.block_spent
        report["attempts_used"] = attempt_gate.n if attempt_gate else 0
        report["far_by_stage"] = fars
        att = (f" · 전송 {attempt_gate.n}(퓨즈 {ATTEMPT_ISSUE_CAP}/건)"
               if attempt_gate else "")
        print(f"[compare_ours] 완주 · 논리 호출 {gate.n}/{max_calls}{att} · "
              f"블록 원장 {report['block_spent_after']}/{BLOCK_CAP} · 루트 {data_root} (보존)")
        return report
    finally:
        paths.DATA = old_data
        llm.MAX_TOKENS = old_max_tokens
        llm.obtain_response = real_obtain
        if old_dispatch is not None:
            llm._DISPATCH.clear()
            llm._DISPATCH.update(old_dispatch)


def run_tranche(issues: list[str], run_prefix: str, config_path: Path,
                source_data: Path, *, live: bool = False, max_calls: int = 0,
                utterance_fn=None, responder=None) -> list[dict]:
    """이슈 1~3건 직렬 실행(C-7 두 번째 안 — 한 프로세스가 유일 기록자).
    live 는 단일 실행 잠금 아래에서만 돈다. run_id = {prefix}_{이슈 끝자리}."""
    if not 1 <= len(issues) <= 3:
        raise SystemExit(f"트랜치는 1~3건: {issues}")
    run_ids = [f"{run_prefix}_{i.rsplit('_', 1)[-1]}" for i in issues]
    lock = None
    if live:
        lock = SingleInstanceLock(Path(source_data).resolve() / "raw_calls" / LOCK_NAME)
        lock.acquire()
    try:
        reports = []
        for issue_id, run_id in zip(issues, run_ids):
            print(f"=== {issue_id} · {run_id} ===")
            reports.append(run(issue_id, run_id, config_path, source_data,
                              live=live, max_calls=max_calls,
                              utterance_fn=utterance_fn, responder=responder))
        if not live:
            total = sum(r["planned_calls"]["total"] for r in reports)
            spent = reports[-1]["block_spent"]
            print(f"[트랜치 계획] {len(reports)}건 · 계획 합계 {total} · "
                  f"블록 원장 {spent}/{BLOCK_CAP} → 실행 후 {spent + total}/{BLOCK_CAP}")
        return reports
    finally:
        if lock is not None:
            lock.release()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--issues", required=True,
                    help="쉼표 구분 1~3건 (예: issue_ethics_0543,issue_ethics_0248)")
    ap.add_argument("--run-prefix", required=True,
                    help="run_id 접두사 — {prefix}_{이슈 끝자리} 로 유도 (예: compare2)")
    ap.add_argument("--config", type=Path, required=True,
                    help="configs/compare_v2.yaml (조건 변경 = 새 yaml)")
    ap.add_argument("--source-data", type=Path, default=HERE / "data",
                    help="데이터 루트 — 직접 산출(사본·임시 폴더 없음, 규약 8)")
    ap.add_argument("--live", action="store_true",
                    help="실호출. --max-calls 필수, 요한 승인 후에만. 단일 실행 잠금")
    ap.add_argument("--max-calls", type=int, default=0,
                    help=f"이슈별 프로세스 호출 상한 (이슈 상한 {ISSUE_CAP} 초과 거부)")
    args = ap.parse_args()
    issues = [s.strip() for s in args.issues.split(",") if s.strip()]
    run_tranche(issues, args.run_prefix, args.config, args.source_data,
                live=args.live, max_calls=args.max_calls)


if __name__ == "__main__":
    main()
