# -*- coding: utf-8 -*-
"""브리지(접합 계층) 테스트 — 번역 왕복·H1 방어·저자 축 변환 (LLM 호출 0).

GPT 담당 test_runners.py 와 분리된 파일이다(투트랙 소유권 경계)."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import bridge  # noqa: E402
from modules import validate as validate_mod  # noqa: E402

FIXTURE_FACTS = json.loads((HERE / "fixtures" / "data" / "facts" /
                            "facts_issue_repro_fx.json").read_text(encoding="utf-8"))


class TranslationTests(unittest.TestCase):
    def test_roundtrip_identity_on_fixture(self):
        ids = bridge.fact_ids_in_order(FIXTURE_FACTS)
        self.assertEqual(len(ids), 8)
        indices = [0, 3, 7]
        fids = bridge.to_fact_ids(FIXTURE_FACTS, indices)
        self.assertEqual(bridge.to_positions(FIXTURE_FACTS, fids), indices)

    def test_h1_origin_index_mismatch_fails_loudly(self):
        broken = json.loads(json.dumps(FIXTURE_FACTS))
        broken["facts"][2]["origin_index"] = 7
        for fn in (bridge.fact_ids_in_order, bridge.author_fact_lines):
            with self.assertRaises(ValueError):
                fn(broken)

    def test_invalid_index_and_unknown_id_fail_loudly(self):
        with self.assertRaises(ValueError):
            bridge.to_fact_ids(FIXTURE_FACTS, [99])
        with self.assertRaises(ValueError):
            bridge.to_fact_ids(FIXTURE_FACTS, [True])  # bool 은 int 가 아니다
        with self.assertRaises(ValueError):
            bridge.to_positions(FIXTURE_FACTS, ["fact_ghost_01"])

    def test_author_fact_lines_inherits_author_format(self):
        lines = bridge.author_fact_lines(FIXTURE_FACTS).splitlines()
        self.assertEqual(len(lines), 8)
        # 저자 perspective.py: f"{index} {'(Important)'|'(Not Important)'}: {text}"
        self.assertTrue(lines[0].startswith("0 (Important): "))
        self.assertTrue(lines[3].startswith("3 (Not Important): "))


class AuthorJudgmentTests(unittest.TestCase):
    def _rows(self):
        return [
            {"round": 0, "agent_id": "agent_1", "matched_fact_ids": [0, 1], "parse": "json"},
            {"round": 0, "agent_id": "agent_2", "matched_fact_ids": [1], "parse": "json"},
            {"round": 1, "agent_id": "agent_1", "matched_fact_ids": [], "parse": "json"},
            {"round": 1, "agent_id": "agent_2", "matched_fact_ids": None, "parse": "parse_fail"},
        ]

    def test_status_agents_and_far(self):
        jd = bridge.author_rows_to_judgment(
            self._rows(), FIXTURE_FACTS,
            issue_id="issue_repro_fx", run_id="t", prompt_ver="test")
        s0 = {f["fact_id"]: f for f in jd["stages"][0]["facts"]}
        self.assertEqual(s0["fact_repro_fx_01"]["status"], "mentioned")
        self.assertEqual(s0["fact_repro_fx_01"]["agents_mentioning"], ["agent_1"])
        self.assertEqual(s0["fact_repro_fx_02"]["agents_mentioning"],
                         ["agent_1", "agent_2"])
        self.assertEqual(s0["fact_repro_fx_03"]["status"], "unmentioned")
        # stage0: 8팩트 중 2 생존 → FAR 6/8
        self.assertEqual(jd["summary"]["far_by_stage"][0]["far_system"], 0.75)
        # stage1: 매치 0 (parse_fail 은 0으로 세지 않되 생존도 아님) → FAR 1.0
        self.assertEqual(jd["summary"]["far_by_stage"][1]["far_system"], 1.0)
        self.assertEqual(jd["summary"]["judge_health"]["n_parse_fail"], 1)
        self.assertEqual(jd["summary"]["judge_health"]["n_rows"], 4)
        # 정본 judge 와 혼동 불가능한 각인
        self.assertEqual(jd["judge"]["aggregation"], "author_axis_n1")
        self.assertEqual(jd["judge"]["n_votes"], 1)
        self.assertEqual(jd["created_by"], "paper_repro_bridge")

    def test_duplicate_rows_last_wins(self):
        rows = self._rows() + [
            {"round": 1, "agent_id": "agent_1", "matched_fact_ids": [5], "parse": "regex"}]
        jd = bridge.author_rows_to_judgment(
            rows, FIXTURE_FACTS, issue_id="issue_repro_fx", run_id="t", prompt_ver="test")
        s1 = {f["fact_id"]: f for f in jd["stages"][1]["facts"]}
        self.assertEqual(s1["fact_repro_fx_06"]["agents_mentioning"], ["agent_1"])
        self.assertEqual(jd["summary"]["judge_health"]["n_rows"], 4)  # 중복은 1행

    def test_out_of_range_match_fails_loudly(self):
        rows = [{"round": 0, "agent_id": "a", "matched_fact_ids": [8], "parse": "json"}]
        with self.assertRaises(ValueError):
            bridge.author_rows_to_judgment(
                rows, FIXTURE_FACTS, issue_id="x", run_id="t", prompt_ver="test")

    def test_output_passes_contract_validate(self):
        jd = bridge.author_rows_to_judgment(
            self._rows(), FIXTURE_FACTS,
            issue_id="issue_repro_fx", run_id="t", prompt_ver="test")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "judgment_issue_repro_fx_t.json"
            p.write_text(json.dumps(jd, ensure_ascii=False), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                validate_mod.validate(p)  # 실패 시 SystemExit → 테스트 실패


FIXTURE_ASSIGN = json.loads((HERE / "fixtures" / "data" / "assignments" /
                             "assignment_issue_repro_fx.json").read_text(encoding="utf-8"))


class StanceTests(unittest.TestCase):
    def test_parse_stance_variants(self):
        self.assertEqual(bridge.parse_stance("YES"), "yes")
        self.assertEqual(bridge.parse_stance("  yes."), "yes")
        self.assertEqual(bridge.parse_stance("No, the author is not."), "no")
        self.assertIsNone(bridge.parse_stance("Maybe."))
        self.assertIsNone(bridge.parse_stance(""))
        self.assertIsNone(bridge.parse_stance(None))

    def test_summary_expected_mapping_and_match(self):
        rows = [
            {"round": 0, "agent_id": "agent_1", "parsed": "no", "raw_response": "NO"},     # pro(행동 반대) 일치
            {"round": 0, "agent_id": "agent_2", "parsed": "no", "raw_response": "NO"},     # con(행동 지지) 이탈
            {"round": 1, "agent_id": "agent_1", "parsed": None, "raw_response": "?"},      # parse_fail
        ]
        doc = bridge.stance_rows_to_summary(rows, FIXTURE_ASSIGN,
                                            issue_id="issue_repro_fx", run_id="t")
        by = {(u["round"], u["agent_id"]): u for u in doc["per_utterance"]}
        self.assertEqual(by[(0, "agent_1")], {"round": 0, "agent_id": "agent_1",
                                              "expected": "no", "judged": "no", "match": True})
        self.assertEqual(by[(0, "agent_2")]["expected"], "yes")
        self.assertFalse(by[(0, "agent_2")]["match"])
        self.assertIsNone(by[(1, "agent_1")]["match"])          # parse_fail 은 판정 제외
        self.assertEqual(doc["summary"]["match_rate_by_round"], {"0": 0.5})
        self.assertEqual(doc["summary"]["n_parse_fail"], 1)

    def test_summary_duplicate_last_wins(self):
        rows = [{"round": 0, "agent_id": "agent_1", "parsed": "yes", "raw_response": "YES"},
                {"round": 0, "agent_id": "agent_1", "parsed": "no", "raw_response": "NO"}]
        doc = bridge.stance_rows_to_summary(rows, FIXTURE_ASSIGN,
                                            issue_id="issue_repro_fx", run_id="t")
        self.assertEqual(doc["summary"]["n_rows"], 1)
        self.assertTrue(doc["per_utterance"][0]["match"])

    def test_summary_all_eight_agents_mapped_from_fixture(self):
        rows = [{"round": 0, "agent_id": ag["agent_id"],
                 "parsed": "yes", "raw_response": "YES"}
                for ag in FIXTURE_ASSIGN["agents"]]
        doc = bridge.stance_rows_to_summary(rows, FIXTURE_ASSIGN,
                                            issue_id="issue_repro_fx", run_id="t")
        expected = [u["expected"] for u in doc["per_utterance"]]
        self.assertEqual(expected, ["no", "yes"] * 4)            # pro→NO(행동 반대)/con→YES 쌍 4개
        with self.assertRaises(ValueError):
            bridge.stance_rows_to_summary(
                [{"round": 0, "agent_id": "ghost", "parsed": "yes", "raw_response": "YES"}],
                FIXTURE_ASSIGN, issue_id="x", run_id="t")


if __name__ == "__main__":
    unittest.main()
