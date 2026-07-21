"""Fact Ledger v0 단위 테스트 — API 불필요, 결정론적.

실행: python -m unittest tests.test_ledger  (리포 루트에서)
또는: python -m pytest tests/test_ledger.py

입력 두 종류:
  1) 동범 오프라인 드라이런 산출물(data/judgments/judgment_issue_esa_dryrun.json) — 실제 계약 검증
  2) 손으로 만든 가짜 judgment — 엣지케이스(전부 생존/전부 소실/혼합/refuted·ignored)

핵심 계약(SCHEMA 「FAR 정의」절):
  소실 = status ∉ SURVIVING(={mentioned, accepted}). ledger 는 judge 와 같은 잣대를 쓴다.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from modules import ledger, paths
from modules.judge import SURVIVING

ROOT = Path(__file__).resolve().parent.parent


def _judgment(stages: list[dict]) -> dict:
    """최소 judgment 골격 — stages 만 채운 가짜 판정."""
    return {
        "schema_ver": "0.2",
        "issue_id": "issue_esa",
        "run_id": "fake",
        "judge": {"model": "x", "temperature": 0, "n_votes": 3,
                  "aggregation": "majority", "prompt_ver": "test"},
        "stage_type": "round",
        "stages": stages,
        "summary": {},
    }


def _facts_by_id(ids_texts: dict[str, str]) -> dict[str, dict]:
    return {fid: {"fact_id": fid, "text": t} for fid, t in ids_texts.items()}


class TestMissingFacts(unittest.TestCase):
    def test_survivor_set_is_shared_with_judge(self):
        # ledger 가 judge 와 다른 잣대를 쓰면 측정이 무너진다 — 같은 객체여야 한다.
        self.assertEqual(SURVIVING, {"mentioned", "accepted"})

    def test_all_survive_none_missing(self):
        j = _judgment([{"stage": 0, "facts": [
            {"fact_id": "f1", "status": "mentioned"},
            {"fact_id": "f2", "status": "accepted"},
        ]}])
        self.assertEqual(ledger.missing_facts(j, 0), [])

    def test_all_missing(self):
        j = _judgment([{"stage": 0, "facts": [
            {"fact_id": "f1", "status": "unmentioned"},
            {"fact_id": "f2", "status": "refuted"},
            {"fact_id": "f3", "status": "ignored"},
        ]}])
        # refuted·ignored 도 SURVIVING 밖이므로 소실로 잡혀야 한다(2종 체계를 넘는 방어).
        self.assertEqual(ledger.missing_facts(j, 0), ["f1", "f2", "f3"])

    def test_mixed_preserves_order(self):
        j = _judgment([{"stage": 0, "facts": [
            {"fact_id": "f1", "status": "mentioned"},   # 생존
            {"fact_id": "f2", "status": "unmentioned"}, # 소실
            {"fact_id": "f3", "status": "accepted"},    # 생존
            {"fact_id": "f4", "status": "ignored"},     # 소실
        ]}])
        self.assertEqual(ledger.missing_facts(j, 0), ["f2", "f4"])

    def test_stage_selection(self):
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "f1", "status": "unmentioned"}]},
            {"stage": 1, "facts": [{"fact_id": "f1", "status": "mentioned"}]},
        ])
        self.assertEqual(ledger.missing_facts(j, 0), ["f1"])
        self.assertEqual(ledger.missing_facts(j, 1), [])

    def test_unknown_stage_raises(self):
        j = _judgment([{"stage": 0, "facts": []}])
        with self.assertRaises(KeyError):
            ledger.missing_facts(j, 9)


class TestInjectionBlock(unittest.TestCase):
    def test_empty_when_no_missing(self):
        self.assertEqual(ledger.build_injection_block([], {}), "")

    def test_uses_verbatim_text_no_summary(self):
        fbi = _facts_by_id({"f1": "보증금 500달러가 몰수된다", "f2": "월 40달러 추가 비용"})
        block = ledger.build_injection_block(["f1", "f2"], fbi)
        # 원문이 그대로 들어가야 한다(요약 금지 = 이 프로젝트가 연구하는 실패의 회피).
        self.assertIn("보증금 500달러가 몰수된다", block)
        self.assertIn("월 40달러 추가 비용", block)
        self.assertEqual(block.count("\n") + 1, 3)  # 헤더 1 + 팩트 2

    def test_missing_text_falls_back_gracefully(self):
        block = ledger.build_injection_block(["ghost"], {})
        self.assertIn("ghost", block)  # 원문 없어도 죽지 않고 표시


class TestInjectEvent(unittest.TestCase):
    def test_schema4_shape(self):
        ev = ledger.make_inject_event("run001", 2, ["f1", "f2"])
        for k in ("event", "run_id", "ts", "round", "injected_fact_ids", "reason"):
            self.assertIn(k, ev)
        self.assertEqual(ev["event"], "ledger_inject")
        self.assertEqual(ev["round"], 2)
        self.assertEqual(ev["injected_fact_ids"], ["f1", "f2"])
        self.assertEqual(ev["reason"], "v0_all_missing")

    def test_reason_codes_are_schema_allowed(self):
        # 스키마 4번: reason ∈ {v0_all_missing, v1_ignored_only}
        ev = ledger.make_inject_event("r", 1, [], reason="v1_ignored_only")
        self.assertIn(ev["reason"], {"v0_all_missing", "v1_ignored_only"})


class TestGateCheck(unittest.TestCase):
    def setUp(self):
        self.fbi = _facts_by_id({"f1": "보증금 500달러", "f2": "월 40달러 추가 비용"})

    def test_pass_when_all_present(self):
        draft = "보증금 500달러와 월 40달러 추가 비용을 모두 고려해 신고를 권고한다."
        ev = ledger.gate_check(draft, ["f1", "f2"], self.fbi, "run001")
        self.assertEqual(ev["verdict"], "pass")
        self.assertEqual(ev["missing_fact_ids"], [])

    def test_rollback_when_missing_and_first_time(self):
        draft = "그냥 원만히 합의하자."
        ev = ledger.gate_check(draft, ["f1", "f2"], self.fbi, "run001", rollback_count=0)
        self.assertEqual(ev["verdict"], "rollback")
        self.assertEqual(ev["missing_fact_ids"], ["f1", "f2"])
        self.assertEqual(ev["rollback_count"], 1)

    def test_rollback_capped_at_one(self):
        # 이미 1회 롤백했으면 또 누락이어도 pass(무한 루프 방지, 스키마 rollback 최대 1).
        draft = "그냥 원만히 합의하자."
        ev = ledger.gate_check(draft, ["f1", "f2"], self.fbi, "run001", rollback_count=1)
        self.assertEqual(ev["verdict"], "pass")
        self.assertLessEqual(ev["rollback_count"], 1)


class TestAgainstDongbeomDryrun(unittest.TestCase):
    """동범 오프라인 드라이런 산출물에 대한 실제 계약 검증(리포에 있는 실파일)."""

    @classmethod
    def setUpClass(cls):
        p = ROOT / "data" / "judgments" / "judgment_issue_esa_dryrun.json"
        if not p.exists():
            raise unittest.SkipTest(f"드라이런 판정 파일 없음: {p}")
        cls.judgment = json.loads(p.read_text(encoding="utf-8"))
        cls.facts_by_id = ledger.load_facts_by_id("issue_esa")

    def test_dryrun_missing_is_ten_facts(self):
        # 드라이런: 매 stage 12개 중 fact_01·02(mentioned)만 생존 → 10종 소실.
        for stage in range(4):
            ids = ledger.missing_facts(self.judgment, stage)
            self.assertEqual(len(ids), 10, f"stage {stage}")
            self.assertNotIn("fact_esa_01", ids)
            self.assertNotIn("fact_esa_02", ids)

    def test_dryrun_injection_block_has_verbatim_facts(self):
        ids = ledger.missing_facts(self.judgment, 3)
        block = ledger.build_injection_block(ids, self.facts_by_id)
        # 실제 팩트 원문이 블록에 실려야 한다.
        self.assertIn("Jenna는 진단된 불안이 있다", block)
        self.assertIn("임대차 계약 갱신이 3주 뒤다", block)

    def test_depends_only_on_fact_id_and_status(self):
        # votes 세부 구조를 지워도 missing_facts 는 동일해야 한다(구조 의존 최소화 계약).
        stripped = {"stages": [
            {"stage": st["stage"],
             "facts": [{"fact_id": f["fact_id"], "status": f["status"]} for f in st["facts"]]}
            for st in self.judgment["stages"]
        ]}
        for stage in range(4):
            self.assertEqual(
                ledger.missing_facts(stripped, stage),
                ledger.missing_facts(self.judgment, stage),
                f"stage {stage}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
