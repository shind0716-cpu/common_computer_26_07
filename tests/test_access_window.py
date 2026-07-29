"""접근 창 계기(access_window.py) 단위 테스트 — API 불필요, 결정론적.

실행: python -m unittest tests.test_access_window  (리포 루트에서)

입력 두 종류(test_transmission 과 동일 스타일):
  1) 손으로 만든 최소 가짜 judgment/assignment/events — 상태·전이 엣지케이스 전수
  2) dryrun2 정본 픽스처 스모크(구조 불변식만 단언)

핵심 계약: 상태 = spoken > accessible > inaccessible 우선순위. 접근 원천 =
prompt_assembly(있으면) / 롤링 창 재구성(idx0 = 자기 할당, idx≥1 = 자기∪이웃 직전 언급
∨ inject). resurgence = 접근 없는 발화. 은퇴 유예(w=1) = 1라운드는 가정이 아니라 측정 결과.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from modules import access_window as aw

ROOT = Path(__file__).resolve().parent.parent


def _stage(stage: int, mentions: dict[str, list[str]]) -> dict:
    return {"stage": stage,
            "facts": [{"fact_id": fid,
                       "status": "mentioned" if ags else "unmentioned",
                       "agents_mentioning": ags}
                      for fid, ags in mentions.items()]}


def _judgment(stages: list[dict]) -> dict:
    return {"schema_ver": "0.2", "issue_id": "issue_fake", "run_id": "fake",
            "stages": stages}


def _assignment(agents: dict[str, list[str]]) -> dict:
    return {"agents": [{"agent_id": a, "assigned_fact_ids": fids}
                       for a, fids in agents.items()]}


# 공통 픽스처: A 가 f1 보유. B·C 비보유. full 토폴로지(seating 없음 → full 가정).
ASSIGN = _assignment({"A": ["f1"], "B": [], "C": []})


def _states(rec: dict) -> list[str]:
    return [t["state"] for t in rec["timeline"]]


class TestStates(unittest.TestCase):
    def test_spoken_then_grace_then_dead(self):
        # A 가 round0 발화 → round1 침묵(창에는 남음 = accessible) → round2 접근 소멸.
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": []}),
            _stage(2, {"f1": []}),
        ])
        recs, meta = aw.fact_records(j, ASSIGN)
        rec = recs[0]
        self.assertEqual(_states(rec), ["spoken", "accessible", "inaccessible"])
        self.assertEqual(rec["first_inaccessible_round"], 2)
        self.assertEqual(rec["final_state"], "inaccessible")
        # 은퇴 에피소드: round0 발화 뒤 침묵 — 결말 dead.
        self.assertEqual(len(rec["retirements"]), 1)
        epi = rec["retirements"][0]
        self.assertEqual(epi["after_round"], 0)
        self.assertEqual(epi["grace_state"], "accessible")
        self.assertEqual(epi["outcome"], "dead")
        self.assertEqual(epi["outcome_round"], 2)
        self.assertEqual(meta["window"]["window_source"], "reconstructed")

    def test_assigned_but_never_spoken_dies_at_round1(self):
        # 보유자 A 가 f1 을 round0 에 발화하지 않음 — idx0 은 A 입력에 있어 accessible,
        # idx1 부터는 어떤 창에도 없음(할당 팩트는 재공급되지 않음 §2-0).
        j = _judgment([
            _stage(0, {"f1": []}),
            _stage(1, {"f1": []}),
        ])
        recs, _ = aw.fact_records(j, ASSIGN)
        rec = recs[0]
        self.assertEqual(_states(rec), ["accessible", "inaccessible"])
        self.assertEqual(rec["first_inaccessible_round"], 1)
        self.assertEqual(rec["retirements"], [])  # spoken 구간이 없으니 은퇴도 없음

    def test_carried_chain_stays_spoken(self):
        # A→B 재발화 사슬: 매 라운드 spoken, 사망 없음.
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": ["B"]}),
            _stage(2, {"f1": ["A", "C"]}),
        ])
        recs, _ = aw.fact_records(j, ASSIGN)
        rec = recs[0]
        self.assertEqual(_states(rec), ["spoken", "spoken", "spoken"])
        self.assertIsNone(rec["first_inaccessible_round"])
        self.assertEqual(rec["retirements"], [])
        self.assertEqual(rec["rounds_by_state"]["spoken"], 3)

    def test_resurgence_flagged(self):
        # f1 이 round2 에서 죽은 뒤 round3 에 C 가 접근 없이 발화 = resurgence 부활.
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": []}),
            _stage(2, {"f1": []}),
            _stage(3, {"f1": ["C"]}),
        ])
        recs, _ = aw.fact_records(j, ASSIGN)
        rec = recs[0]
        self.assertEqual(_states(rec),
                         ["spoken", "accessible", "inaccessible", "spoken"])
        self.assertEqual(rec["timeline"][3]["resurgent_speakers"], ["C"])
        self.assertEqual(rec["revivals"],
                         [{"round": 3, "to_state": "spoken",
                           "channel": "resurgence"}])

    def test_round0_nonholder_mention_is_resurgent(self):
        # round0 입력에는 자기 할당 팩트뿐 — 비보유 C 의 round0 발화는 접근 없는 발화.
        j = _judgment([_stage(0, {"f1": ["C"]})])
        recs, _ = aw.fact_records(j, ASSIGN)
        rec = recs[0]
        self.assertEqual(_states(rec), ["spoken"])
        self.assertEqual(rec["timeline"][0]["resurgent_speakers"], ["C"])

    def test_ledger_inject_revives_and_lifeline(self):
        # round0 발화 → round1 침묵 → round2 inject 로 접근 부활(ledger 채널).
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": []}),
            _stage(2, {"f1": []}),
            _stage(3, {"f1": []}),
        ])
        events = [{"event": "ledger_inject", "round": 3,
                   "injected_fact_ids": ["f1"]}]
        recs, _ = aw.fact_records(j, ASSIGN, events)
        rec = recs[0]
        self.assertEqual(_states(rec),
                         ["spoken", "accessible", "inaccessible", "accessible"])
        self.assertEqual(rec["revivals"],
                         [{"round": 3, "to_state": "accessible",
                           "channel": "ledger"}])
        self.assertTrue(rec["timeline"][3]["inject"])

    def test_retirement_outcome_ledger_lifeline(self):
        # round0 발화 → round1 침묵(유예) → round2 inject 존재 → 결말 ledger_lifeline.
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": []}),
            _stage(2, {"f1": []}),
        ])
        events = [{"event": "ledger_inject", "round": 2,
                   "injected_fact_ids": ["f1"]}]
        recs, _ = aw.fact_records(j, ASSIGN, events)
        epi = recs[0]["retirements"][0]
        self.assertEqual(epi["outcome"], "ledger_lifeline")

    def test_retirement_censored_at_observation_end(self):
        # 마지막 라운드 직전 발화 → 마지막 라운드 침묵 = 유예 상태로 관측 종료(censored).
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": []}),
        ])
        recs, _ = aw.fact_records(j, ASSIGN)
        epi = recs[0]["retirements"][0]
        self.assertEqual(epi["outcome"], "censored")
        self.assertIsNone(epi["outcome_round"])


class TestPromptAssemblyWindow(unittest.TestCase):
    def test_assembly_slots_override_reconstruction(self):
        # line 구조를 슬롯으로 직접 기술: B 의 round1 창에는 A 발화가 없음(others 에 C 만)
        # → 재구성(full 가정)이라면 접근이지만, 조립 기록상 B 는 f1 에 접근 불가.
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": []}),
        ])
        events = []
        for a, others in (("A", ["B"]), ("B", ["C"]), ("C", ["B"])):
            events.append({"event": "prompt_assembly", "round": 0, "agent_id": a,
                           "slots": {"assigned_fact_ids":
                                     ["f1"] if a == "A" else [],
                                     "others": [], "previous": None,
                                     "inject": None}})
            events.append({"event": "prompt_assembly", "round": 1, "agent_id": a,
                           "slots": {"assigned_fact_ids": [],
                                     "others": [{"round": 0, "agent_id": o}
                                                for o in others],
                                     "previous": {"round": 0, "agent_id": a},
                                     "inject": None}})
        recs, meta = aw.fact_records(j, _assignment({"A": ["f1"], "B": [], "C": []}),
                                     events)
        self.assertEqual(meta["window"]["window_source"], "prompt_assembly")
        # round1: A 자신(previous)만 f1 발화 좌표를 창에 보유 → accessible(1명).
        row = recs[0]["timeline"][1]
        self.assertEqual(row["state"], "accessible")
        self.assertEqual(row["n_access_agents"], 1)


class TestViewsAndExclusion(unittest.TestCase):
    def test_curve_and_summary(self):
        j = _judgment([
            _stage(0, {"f1": ["A"], "f2": []}),
            _stage(1, {"f1": [], "f2": []}),
            _stage(2, {"f1": [], "f2": []}),
        ])
        assign = _assignment({"A": ["f1"], "B": ["f2"], "C": []})
        recs, meta = aw.fact_records(j, assign)
        curve = aw.state_curve(recs, meta["rounds"])
        self.assertEqual(curve[0]["alive_access"], 2)   # f1 spoken + f2 accessible
        self.assertEqual(curve[2]["inaccessible"], 2)
        s = aw.summary(recs)
        self.assertEqual(s["n_ever_inaccessible"], 2)
        self.assertEqual(s["final_state"]["inaccessible"], 2)

    def test_question_exposed_excluded_from_views(self):
        j = _judgment([_stage(0, {"f1": ["A"], "fq": ["A"]})])
        recs, _ = aw.fact_records(j, ASSIGN,
                                  question_exposed_ids=frozenset({"fq"}))
        s = aw.summary(recs)
        self.assertEqual(s["n_facts_tracked"], 1)
        self.assertEqual(s["n_facts_excluded_question"], 1)


class TestDryrun2Smoke(unittest.TestCase):
    """dryrun2 정본 픽스처 — 구조 불변식만 단언(수치 고정 아님)."""

    @classmethod
    def setUpClass(cls):
        cls.judgment = json.loads(
            (ROOT / "data/judgments/judgment_issue_esa_dryrun2.json")
            .read_text(encoding="utf-8"))
        cls.assignment = json.loads(
            (ROOT / "data/assignments/assignment_issue_esa.json")
            .read_text(encoding="utf-8"))
        cls.events = [json.loads(line) for line in
                      (ROOT / "data/debates/debate_issue_esa_dryrun2.jsonl")
                      .read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_report_invariants(self):
        rep = aw.report(self.judgment, self.assignment, self.events)
        n_rounds = len(rep["meta"]["rounds"])
        self.assertGreater(len(rep["records"]), 0)
        for rec in rep["records"]:
            self.assertEqual(len(rec["timeline"]), n_rounds)
            states = _states(rec)
            self.assertTrue(all(st in aw.STATES for st in states))
            # 상태별 라운드 수 합 = 라운드 수.
            self.assertEqual(sum(rec["rounds_by_state"].values()), n_rounds)
            # spoken 라운드에는 발화자가, accessible 라운드에는 접근자가 있다.
            for t in rec["timeline"]:
                if t["state"] == "spoken":
                    self.assertTrue(t["spoken_by"])
                if t["state"] == "accessible":
                    self.assertFalse(t["spoken_by"])
                    self.assertGreater(t["n_access_agents"], 0)
        # 곡선의 각 행 합 = 추적 팩트 수.
        s = rep["summary"]
        for row in rep["curve"]:
            self.assertEqual(row["spoken"] + row["accessible"]
                             + row["inaccessible"], s["n_facts_tracked"])


if __name__ == "__main__":
    unittest.main()
