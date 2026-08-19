# -*- coding: utf-8 -*-
"""히든 프로필 관측 노드 계기 테스트 (계약: docs/proposals/HIDDEN_PROFILE_NODE.md §3·§5·§6).

전부 합성 이벤트 — LLM 호출 0 · 파일 쓰기 0.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules import hidden_profile as hp  # noqa: E402


def _poll(agent, text, rnd=4):
    return {"event": "final_poll", "agent_id": agent, "round": rnd, "response_text": text}


class OutcomeTests(unittest.TestCase):
    def test_counts_not_ratios_and_parse_fail_is_third_state(self):
        events = [
            _poll("agent_1", '{"recommend":"유지완"}'),        # 정답
            _poll("agent_2", '{"recommend":"한도영"}'),        # 오답
            _poll("agent_3", "판단하기 어렵습니다"),            # parse_ok=False
        ]
        out = hp.outcome(events, answer="유지완")
        self.assertEqual(out["n_agents"], 3)
        self.assertEqual(out["n_correct"], 1)
        by = {p["agent_id"]: p for p in out["picks"]}
        self.assertTrue(by["agent_1"]["correct"])
        self.assertFalse(by["agent_2"]["correct"])
        # §6: parse_ok=False 는 정답·오답 어느 쪽 개수에도 들어가지 않는다(제3의 값)
        self.assertIsNone(by["agent_3"]["correct"])
        self.assertFalse(by["agent_3"]["parse_ok"])
        # §5-1: 계기는 비율을 내지 않는다 — 개수 키만
        self.assertFalse(any("rate" in k or "ratio" in k for k in out))

    def test_answer_is_caller_supplied_and_required(self):
        with self.assertRaises(TypeError):
            hp.outcome([])  # answer 없이 호출 불가(§5-6)
        with self.assertRaises(ValueError):
            hp.outcome([], answer="  ")

    def test_non_dict_json_is_parse_fail(self):
        out = hp.outcome([_poll("a", '["유지완"]'), _poll("b", '{"recommend": 3}')],
                         answer="유지완")
        self.assertEqual(out["n_correct"], 0)
        self.assertTrue(all(p["correct"] is None for p in out["picks"]))

    def test_wrapped_json_is_read_but_prose_is_not(self):
        """v2 규칙 R2 — JSON 을 감싼 껍데기는 벗기되 자연어는 읽지 않는다(§5-6)."""
        events = [
            _poll("agent_1", '```json\n{"recommend":"유지완"}\n```'),   # 코드펜스
            _poll("agent_2", '결론입니다 {"recommend":"한도영"} 이상'),  # 앞뒤 산문
            _poll("agent_3", "저는 유지완을 추천합니다"),                # JSON 아님
        ]
        out = hp.outcome(events, answer="유지완")
        by = {p["agent_id"]: p for p in out["picks"]}
        self.assertTrue(by["agent_1"]["correct"])
        self.assertFalse(by["agent_2"]["correct"])
        self.assertEqual(by["agent_2"]["recommend"], "한도영")
        # 이름이 문면에 있어도 JSON 이 아니면 제3상태다 — 의미를 읽지 않는다
        self.assertFalse(by["agent_3"]["parse_ok"])
        self.assertIsNone(by["agent_3"]["correct"])
        self.assertEqual(out["parse_ver"], hp.OUTCOME_PARSE_VER)


def _fixture_docs():
    facts_doc = {"facts": [
        {"fact_id": "f_s1", "share": "shared", "favors": "한도영",
         "requirement": 1, "apparent": True},
        {"fact_id": "f_u1", "share": "unshared", "favors": "유지완",
         "requirement": 1, "apparent": False},
        {"fact_id": "f_u2", "share": "unshared", "favors": "한도영",
         "requirement": 3, "apparent": False},
    ]}
    assignment = {"agents": [
        {"agent_id": "agent_1", "assigned_fact_ids": ["f_s1", "f_u1"]},
        {"agent_id": "agent_2", "assigned_fact_ids": ["f_s1", "f_u2"]},
    ]}
    seating = {"event": "seating", "order": ["agent_2", "agent_1"]}
    return facts_doc, assignment, seating


class FactTraceTests(unittest.TestCase):
    def test_unshared_only_design_values_passthrough_and_holders(self):
        facts_doc, assignment, seating = _fixture_docs()
        rows = hp.fact_trace([seating], assignment, facts_doc)
        self.assertEqual([r["fact_id"] for r in rows], ["f_u1", "f_u2"])  # 공유 팩트 제외
        self.assertEqual(rows[0]["holders"], ["agent_1"])
        self.assertEqual(rows[0]["favors"], "유지완")       # 설계값 그대로 통과
        self.assertEqual(rows[1]["requirement"], 3)

    def test_coords_absent_is_none_labeled_empty_is_zero(self):
        # 부재(None)=모름 vs 빈 배열=라벨됐고 등장 0회 — 둘을 섞지 않는다(§4⁗ 원칙)
        facts_doc, assignment, seating = _fixture_docs()
        rows = hp.fact_trace([seating], assignment, facts_doc)
        self.assertIsNone(rows[0]["utterance_coords"])
        rows2 = hp.fact_trace([seating], assignment, facts_doc,
                              coords_by_fact={"f_u1": [{"round": 0, "agent_id": "agent_1"}],
                                              "f_u2": []})
        self.assertEqual(rows2[0]["utterance_coords"], [{"round": 0, "agent_id": "agent_1"}])
        self.assertEqual(rows2[1]["utterance_coords"], [])

    def test_holder_not_in_seating_dies(self):
        facts_doc, assignment, _ = _fixture_docs()
        wrong_seating = {"event": "seating", "order": ["agent_9"]}
        with self.assertRaises(ValueError):
            hp.fact_trace([wrong_seating], assignment, facts_doc)


class NoteTraceTests(unittest.TestCase):
    def test_full_text_preserved_and_length_only(self):
        note = "한도영 처우 확인 필요. 유지완 HANBIT 경험 있음."
        events = [{"event": "note_update", "agent_id": "agent_1", "round": 1,
                   "source": "utterance", "note_text": note}]
        rows = hp.note_trace(events)
        self.assertEqual(rows[0]["note_text"], note)     # 원문 전량 — 요약·발췌 금지
        self.assertEqual(rows[0]["n_chars"], len(note))
        # §5-3: "손실" 계열 키를 만들지 않는다 — n_chars 와 원문만
        self.assertEqual(sorted(rows[0]),
                         ["agent_id", "n_chars", "note_text", "round", "source"])




class LineageTests(unittest.TestCase):
    """§3-5 — 복사 충실성 검증: 결론이 아니라 완전성을 검사한다."""

    def _events(self):
        return [
            {"event": "seating", "order": ["agent_1", "agent_2"]},
            {"event": "prompt_assembly", "round": 0, "agent_id": "agent_1",
             "prompt_hash": "h1", "slots": {"assigned_fact_ids": ["f_u1"]}},
            {"event": "utterance", "round": 0, "agent_id": "agent_1",
             "response_text": "원문 발화 A — 한 글자도 바뀌면 안 된다"},
            {"event": "utterance", "round": 0, "agent_id": "agent_2",
             "response_text": "비보유자 발화 — 실리면 안 된다"},
            {"event": "note_update", "round": 0, "agent_id": "agent_1",
             "source": "dedicated", "note_text": "수첩 판본 원문"},
            {"event": "utterance", "round": 1, "agent_id": "agent_1",
             "response_text": "원문 발화 B"},
        ]

    def _docs(self):
        facts_doc = {"facts": [{"fact_id": "f_u1", "text": "원형 팩트",
                                "share": "unshared", "favors": "유지완",
                                "requirement": 2, "apparent": False}]}
        assignment = {"agents": [
            {"agent_id": "agent_1", "assigned_fact_ids": ["f_u1"]},
            {"agent_id": "agent_2", "assigned_fact_ids": []},
        ]}
        return facts_doc, assignment

    def test_copies_holder_records_verbatim_in_time_order(self):
        facts_doc, assignment = self._docs()
        out = hp.lineage(self._events(), assignment, facts_doc, "f_u1")
        self.assertEqual(out["fact"]["text"], "원형 팩트")        # 설계값 그대로
        self.assertEqual(out["holders"], ["agent_1"])
        self.assertEqual([u["response_text"] for u in out["utterances"]],
                         ["원문 발화 A — 한 글자도 바뀌면 안 된다", "원문 발화 B"])
        self.assertEqual(out["notes"][0]["note_text"], "수첩 판본 원문")
        self.assertEqual(out["inputs_ref"][0]["prompt_hash"], "h1")

    def test_non_holder_utterances_excluded(self):
        facts_doc, assignment = self._docs()
        out = hp.lineage(self._events(), assignment, facts_doc, "f_u1")
        joined = " ".join(u["response_text"] for u in out["utterances"])
        self.assertNotIn("비보유자", joined)

    def test_no_judgment_keys_in_output(self):
        # 계기는 변형 여부를 말하지 않는다 — 판정성 키가 없어야 한다
        facts_doc, assignment = self._docs()
        out = hp.lineage(self._events(), assignment, facts_doc, "f_u1")
        self.assertEqual(sorted(out), ["fact", "holders", "inputs_ref", "notes", "utterances"])

    def test_unknown_fact_dies(self):
        facts_doc, assignment = self._docs()
        with self.assertRaises(ValueError):
            hp.lineage(self._events(), assignment, facts_doc, "f_ghost")


if __name__ == "__main__":
    unittest.main()
