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
                        "axis_checkpoint", "stance_checkpoint", "block_ledger"):
                self.assertTrue(Path(out[key]).exists(), key)
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
            gate = compare_ours.CallGate(ledger, "i", "r", max_calls=10)
            with self.assertRaises(SystemExit):
                gate.reserve("axis_author")

    def test_gate_reserve_refuses_at_issue_cap(self):
        with tempfile.TemporaryDirectory() as td:
            gate = compare_ours.CallGate(Path(td) / "l.jsonl", "i", "r", max_calls=2)
            gate.reserve("utterance")
            gate.reserve("utterance")
            with self.assertRaises(SystemExit):
                gate.reserve("utterance")


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


class RehearseDefaultPathTests(unittest.TestCase):
    """R-1 회귀 — rehearse_splice 기본(픽스처 스텁) 경로가 CLI 로 완주해야 한다.
    suite 통과가 CLI 실행을 대변하지 못했던 재검수 교훈으로 main() 자체를 돈다."""

    def test_default_fixture_rehearsal_completes(self):
        import rehearse_splice
        with mock.patch.object(sys, "argv", ["rehearse_splice.py"]):
            rehearse_splice.main()  # 예외 없이 완주(0콜·임시 사본)


if __name__ == "__main__":
    unittest.main()
