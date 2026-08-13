# -*- coding: utf-8 -*-
"""compare_ours 러너의 계약·안전장치 테스트 (LLM 호출 0).

재검수(MUTUAL_REVIEW 2026-08-11 §13 재검수) 6건이 각각 회귀 테스트다:
C-1 깨끗한 루트 완주 · C-2류 무삭제(계획 모드 무기록) · C-3 FAR=1.0 유효 ·
C-4 체크포인트 전 좌표 관문 · R-1 rehearse 기본 경로 완주 · M-2 블록 원장 346.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import compare_ours  # noqa: E402

FX = HERE / "fixtures" / "data"
CONFIG = HERE / "configs" / "compare_v2.yaml"
ISSUE = "issue_repro_fx"


def _make_root(td: Path) -> Path:
    """C-1 시나리오 그대로 — 필수 입력 3종만 있는 깨끗한 데이터 루트."""
    root = Path(td) / "data"
    for sub, name in (("issues", f"{ISSUE}.json"),
                      ("facts", f"facts_{ISSUE}.json"),
                      ("assignments", f"assignment_{ISSUE}.json")):
        (root / sub).mkdir(parents=True)
        shutil.copy(FX / sub / name, root / sub / name)
    return root


def _utt(inputs, model="", temperature=0.0):
    return "stub utterance mentioning nothing"


def _resp_factory(axis_raw='{"matched_fact_ids": [0]}', counter=None):
    def resp(prompt, model="", temperature=0.0):
        if counter is not None:
            counter["n"] += 1
        if "fact alignment evaluator" in prompt:
            return axis_raw
        return "YES"
    return resp


def _gate(ledger, *, max_calls, issue_cap=None, block_cap=None, label="논리"):
    return compare_ours.CallGate(
        Path(ledger), "i", "r", max_calls=max_calls,
        issue_cap=issue_cap if issue_cap is not None else compare_ours.ISSUE_CAP,
        block_cap=block_cap if block_cap is not None else compare_ours.BLOCK_CAP,
        label=label)


class CleanRootCompletionTests(unittest.TestCase):
    """C-1 — 깨끗한 루트에서 산출물 작성·validate 까지 완주해야 한다."""

    def test_full_chain_on_clean_root_writes_and_validates(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            report = compare_ours.run(
                ISSUE, "t1", CONFIG, root, live=True, max_calls=116,
                utterance_fn=_utt, responder=_resp_factory())
            self.assertEqual(report["calls_used"], 96)  # 발화32+축32+stance32
            out = report["outputs"]
            for key in ("debate", "judgment_author", "stance_summary",
                        "axis_checkpoint", "stance_checkpoint", "manifest",
                        "block_ledger"):
                self.assertTrue(Path(out[key]).exists(), key)
            # 전송 계기판은 실호출 경로 전용 — 스텁 실행에선 생기지 않는다
            self.assertFalse(Path(out["attempt_ledger"]).exists())
            ledger_lines = Path(out["block_ledger"]).read_text(
                encoding="utf-8").splitlines()
            self.assertEqual(len([l for l in ledger_lines if l.strip()]), 96)

    def test_resume_after_completion_uses_zero_calls(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            first = compare_ours.run(
                ISSUE, "t1", CONFIG, root, live=True, max_calls=116,
                utterance_fn=_utt, responder=_resp_factory())
            counter = {"n": 0}
            again = compare_ours.run(
                ISSUE, "t1", CONFIG, root, live=True, max_calls=116,
                utterance_fn=_utt, responder=_resp_factory(counter=counter))
            self.assertEqual(again["calls_used"], 0)
            self.assertEqual(counter["n"], 0)
            self.assertEqual(again["block_spent_after"], first["block_spent_after"])


class FarExtremeTests(unittest.TestCase):
    """C-3 — 전 팩트 unmentioned(FAR=1.0)는 유효한 극단값. 실행이 죽으면 선택 편향."""

    def test_far_one_completes_and_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            report = compare_ours.run(
                ISSUE, "t1", CONFIG, root, live=True, max_calls=116,
                utterance_fn=_utt,
                responder=_resp_factory(axis_raw='{"matched_fact_ids": []}'))
            self.assertTrue(all(f == 1.0 for f in report["far_by_stage"]))
            self.assertTrue(Path(report["outputs"]["judgment_author"]).exists())


class PlanModeTests(unittest.TestCase):
    """계획 모드(기본) — 0콜·무기록. C-2류(사본·자동 삭제)가 구조적으로 없다."""

    def test_plan_counts_96_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            report = compare_ours.run(ISSUE, "t1", CONFIG, root, live=False)
            self.assertEqual(report["planned_calls"],
                             {"utterance": 32, "axis_author": 32,
                              "stance": 32, "total": 96})
            self.assertFalse((root / "debates").exists())
            self.assertFalse((root / "raw_calls").exists())
            self.assertFalse((root / "judgments").exists())


class CapTests(unittest.TestCase):
    """이슈 상한 116(PREREG §6) + 블록 원장 346(PREREG §4·M-2)."""

    def test_max_calls_above_issue_cap_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            with self.assertRaises(SystemExit):
                compare_ours.run(ISSUE, "t1", CONFIG, root, live=True,
                                 max_calls=117, utterance_fn=_utt,
                                 responder=_resp_factory())

    def test_live_without_max_calls_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            with self.assertRaises(SystemExit):
                compare_ours.run(ISSUE, "t1", CONFIG, root, live=True,
                                 utterance_fn=_utt, responder=_resp_factory())

    def test_block_preflight_stops_before_any_call(self):
        # 원장 300 + 계획 96 > 346 — 첫 호출 전에 죽어야 한다(스텁 호출 0 확인)
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            ledger = root / "raw_calls" / compare_ours.BLOCK_LEDGER_NAME
            ledger.parent.mkdir(parents=True)
            ledger.write_text("{}\n" * 300, encoding="utf-8")
            counter = {"n": 0}
            with self.assertRaises(SystemExit):
                compare_ours.run(ISSUE, "t1", CONFIG, root, live=True,
                                 max_calls=116, utterance_fn=_utt,
                                 responder=_resp_factory(counter=counter))
            self.assertEqual(counter["n"], 0)

    def test_gate_reserve_refuses_at_block_cap(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.jsonl"
            ledger.write_text("{}\n" * compare_ours.BLOCK_CAP, encoding="utf-8")
            gate = _gate(ledger, max_calls=10)
            with self.assertRaises(SystemExit):
                gate.reserve("axis_author")

    def test_gate_reserve_refuses_at_process_cap(self):
        with tempfile.TemporaryDirectory() as td:
            gate = _gate(Path(td) / "l.jsonl", max_calls=2)
            gate.reserve("utterance")
            gate.reserve("utterance")
            with self.assertRaises(SystemExit):
                gate.reserve("utterance")

    def test_gate_reserve_refuses_at_persistent_issue_cap(self):
        # C-6 — 이슈 상한은 원장 누적 기준: 재시작(새 gate)해도 초기화되지 않는다
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "l.jsonl"
            ledger.write_text(
                (json.dumps({"issue_id": "i"}) + "\n") * compare_ours.ISSUE_CAP,
                encoding="utf-8")
            gate = _gate(ledger, max_calls=200)
            with self.assertRaises(SystemExit):
                gate.reserve("utterance")

    def test_issue_history_plus_plan_over_cap_dies_before_first_call(self):
        # C-6 재현 그대로: 같은 이슈 기존 예약 21행 + 계획 96 = 117 > 116 → 0콜 거부
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            ledger = root / "raw_calls" / compare_ours.BLOCK_LEDGER_NAME
            ledger.parent.mkdir(parents=True)
            ledger.write_text(
                (json.dumps({"issue_id": ISSUE}) + "\n") * 21, encoding="utf-8")
            counter = {"n": 0}
            with self.assertRaises(SystemExit):
                compare_ours.run(ISSUE, "t1", CONFIG, root, live=True,
                                 max_calls=116, utterance_fn=_utt,
                                 responder=_resp_factory(counter=counter))
            self.assertEqual(counter["n"], 0)

    def test_corrupt_ledger_dies_instead_of_miscounting(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "l.jsonl"
            ledger.write_text("not json\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                compare_ours._read_ledger(ledger, "i")


class CheckpointIdentityTests(unittest.TestCase):
    """C-4 — 체크포인트 행은 전 좌표(issue·run·prompt/facts/config 지문) 일치 시에만 재사용."""

    def test_tampered_issue_id_dies_on_resume(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            report = compare_ours.run(
                ISSUE, "t1", CONFIG, root, live=True, max_calls=116,
                utterance_fn=_utt, responder=_resp_factory())
            ck = Path(report["outputs"]["axis_checkpoint"])
            rows = [json.loads(l) for l in
                    ck.read_text(encoding="utf-8").splitlines() if l.strip()]
            for r in rows:
                r["issue_id"] = "issue_other"  # 다른 이슈의 행을 가장
            ck.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                  for r in rows), encoding="utf-8")
            with self.assertRaises(SystemExit):
                compare_ours.run(ISSUE, "t1", CONFIG, root, live=True,
                                 max_calls=116, utterance_fn=_utt,
                                 responder=_resp_factory())

    def test_identity_gate_treats_missing_field_as_mismatch(self):
        rec = {"round": 0, "agent_id": "a", "issue_id": "i"}  # 지문 필드 부재
        with self.assertRaises(SystemExit):
            compare_ours.check_full_identity(
                rec, {"issue_id": "i", "prompt_sha256": "abc"}, Path("x"))


class StubInjectionContractTests(unittest.TestCase):
    def test_mixed_injection_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            with self.assertRaises(ValueError):
                compare_ours.run(ISSUE, "t1", CONFIG, root, live=True,
                                 max_calls=116, responder=_resp_factory())


class AttemptFuseTests(unittest.TestCase):
    """C-5 — 전송 시도 퓨즈: llm 내부 재시도까지 세고, 상한 도달 시 SystemExit 라
    obtain_response 의 `except Exception` 재시도 루프가 삼키지 못한다."""

    def setUp(self):
        from modules import llm
        self.llm = llm
        self._old = dict(llm._DISPATCH)

    def tearDown(self):
        self.llm._DISPATCH.clear()
        self.llm._DISPATCH.update(self._old)

    def test_retries_are_counted_per_transport_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            gate = _gate(Path(td) / "att.jsonl", max_calls=None,
                         issue_cap=compare_ours.ATTEMPT_ISSUE_CAP,
                         block_cap=compare_ours.ATTEMPT_BLOCK_CAP, label="전송")
            state = {"n": 0}

            def flaky(model_id, inputs, temperature, reasoning="default"):
                state["n"] += 1
                if state["n"] < 3:
                    raise RuntimeError("timeout")  # 상태 미상 = 재시도 대상
                return "OK"

            self.llm._DISPATCH["openai"] = compare_ours._wrap_dispatch(
                flaky, gate, ["axis_author"])
            with mock.patch.object(self.llm.time, "sleep"):
                out = self.llm.obtain_response("p", model="gpt-5", temperature=0.0)
            self.assertEqual(out, "OK")
            self.assertEqual(gate.n, 3)      # 논리 1콜 = 전송 3시도 — 전부 계기판에
            rows = (Path(td) / "att.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len([l for l in rows if l.strip()]), 3)

    def test_fuse_breach_is_not_swallowed_by_retry_loop(self):
        with tempfile.TemporaryDirectory() as td:
            gate = _gate(Path(td) / "att.jsonl", max_calls=None,
                         issue_cap=2, block_cap=100, label="전송")

            def always_timeout(model_id, inputs, temperature, reasoning="default"):
                raise RuntimeError("timeout")

            self.llm._DISPATCH["openai"] = compare_ours._wrap_dispatch(
                always_timeout, gate, ["axis_author"])
            with mock.patch.object(self.llm.time, "sleep"):
                with self.assertRaises(SystemExit):   # 폴백 공백이 아니라 즉사
                    self.llm.obtain_response("p", model="gpt-5", temperature=0.0)
            self.assertEqual(gate.n, 2)


class SingleInstanceLockTests(unittest.TestCase):
    """C-7 — live 는 단일 실행만: 두 번째 잠금 획득은 즉시 거부(호출·기록 0)."""

    def test_second_acquire_rejected_while_first_holds(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.lock"
            first = compare_ours.SingleInstanceLock(path)
            first.acquire()
            try:
                second = compare_ours.SingleInstanceLock(path)
                with self.assertRaises(SystemExit):
                    second.acquire()
            finally:
                first.release()
            third = compare_ours.SingleInstanceLock(path)   # 해제 후엔 획득 가능
            third.acquire()
            third.release()

    def test_tranche_live_rejected_while_lock_held(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            holder = compare_ours.SingleInstanceLock(
                root / "raw_calls" / compare_ours.LOCK_NAME)
            holder.acquire()
            counter = {"n": 0}
            try:
                with self.assertRaises(SystemExit):
                    compare_ours.run_tranche(
                        [ISSUE], "t", CONFIG, root, live=True, max_calls=116,
                        utterance_fn=_utt, responder=_resp_factory(counter=counter))
            finally:
                holder.release()
            self.assertEqual(counter["n"], 0)
            self.assertFalse((root / "debates").exists())


class ManifestGateTests(unittest.TestCase):
    """C-8 — debate 재사용은 입력 전부(issue·facts·assignment·config·모델 좌표)의
    지문 일치 시에만. 한 바이트 변경도 0콜로 거부."""

    def _complete_run(self, root):
        return compare_ours.run(ISSUE, "t1", CONFIG, root, live=True, max_calls=116,
                                utterance_fn=_utt, responder=_resp_factory())

    def test_facts_byte_flip_refused_with_zero_calls(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            report = self._complete_run(root)
            Path(report["outputs"]["axis_checkpoint"]).unlink()
            Path(report["outputs"]["stance_checkpoint"]).unlink()
            fp = root / "facts" / f"facts_{ISSUE}.json"
            fp.write_text(fp.read_text(encoding="utf-8") + " ", encoding="utf-8")
            counter = {"n": 0}
            with self.assertRaises(SystemExit):
                compare_ours.run(ISSUE, "t1", CONFIG, root, live=True,
                                 max_calls=116, utterance_fn=_utt,
                                 responder=_resp_factory(counter=counter))
            self.assertEqual(counter["n"], 0)

    def test_debate_without_manifest_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            report = self._complete_run(root)
            Path(report["outputs"]["manifest"]).unlink()   # 지문 증명 소실
            with self.assertRaises(SystemExit):
                compare_ours.run(ISSUE, "t1", CONFIG, root, live=True,
                                 max_calls=116, utterance_fn=_utt,
                                 responder=_resp_factory())


class TrancheTests(unittest.TestCase):
    def test_plan_tranche_derives_run_ids_and_sums(self):
        with tempfile.TemporaryDirectory() as td:
            root = _make_root(Path(td))
            reports = compare_ours.run_tranche([ISSUE], "t", CONFIG, root, live=False)
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0]["run_id"], "t_fx")
            self.assertEqual(reports[0]["planned_calls"]["total"], 96)

    def test_tranche_rejects_more_than_three_issues(self):
        with self.assertRaises(SystemExit):
            compare_ours.run_tranche(["a", "b", "c", "d"], "t", CONFIG, Path("."),
                                     live=False)


class RehearseDefaultPathTests(unittest.TestCase):
    """R-1 회귀 — rehearse_splice 기본(픽스처 스텁) 경로가 CLI 로 완주해야 한다.
    suite 통과가 CLI 실행을 대변하지 못했던 재검수 교훈으로 main() 자체를 돈다."""

    def test_default_fixture_rehearsal_completes(self):
        import rehearse_splice
        with mock.patch.object(sys, "argv", ["rehearse_splice.py"]):
            rehearse_splice.main()  # 예외 없이 완주(0콜·임시 사본)


if __name__ == "__main__":
    unittest.main()
