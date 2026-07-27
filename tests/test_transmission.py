"""전달 레이더(transmission.py) 단위 테스트 — API 불필요, 결정론적.

실행: python -m unittest tests.test_transmission  (리포 루트에서)

입력 두 종류(test_survival 과 동일 스타일):
  1) 손으로 만든 최소 가짜 judgment/assignment/events — 엣지케이스 전수
  2) dryrun2 정본 픽스처 스모크(수치 고정이 아니라 정합성 단언 — 픽스처는 결정론적이나
     테스트는 구조 불변식만 잰다)

핵심 계약(v1.0): 전달 사건 = 노출 선행 첫 언급(round 0 비보유 언급 = prior_suspect),
엄격 정본 u≥1(u=0 은 u0_immediate 분리), TSR 분모 = 노출 쌍만, 채널 = 첫 노출 채널.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from modules import transmission as tr

ROOT = Path(__file__).resolve().parent.parent


def _stage(stage: int, mentions: dict[str, list[str]]) -> dict:
    """{fact_id: [agents]} → stage 레코드(전 팩트 완전 스냅샷은 호출측이 보장)."""
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


# 공통 픽스처: A 가 f1 보유. B·C 는 비보유. full 토폴로지(seating 없음 → full 가정).
ASSIGN = _assignment({"A": ["f1"], "B": [], "C": []})


class TestExposureAndEvents(unittest.TestCase):
    def test_strict_acquisition_u1_out_of_window(self):
        # A 가 stage0 언급 → B 노출 e=1. B 첫 언급 stage2 → u=1 엄격. stage1 에 아무도
        # f1 언급 안 함 → τ 시점 창 밖(X(B,f1,2)=0).
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": []}),
            _stage(2, {"f1": ["B"]}),
        ])
        recs, meta = tr.pair_records(j, ASSIGN)
        b = next(r for r in recs if r["agent_id"] == "B")
        self.assertEqual(b["kind"], "acquisition")
        self.assertEqual(b["e_round"], 1)
        self.assertEqual(b["tau_round"], 2)
        self.assertEqual(b["u"], 1)
        self.assertTrue(b["strict"])
        self.assertFalse(b["u0_immediate"])
        self.assertFalse(b["in_window_at_tau"])
        self.assertEqual(b["channel"], "organic")
        self.assertEqual(b["exposure_sources"], ["A"])
        self.assertTrue(meta["edges"]["assumed_full"])

    def test_u0_immediate_not_strict(self):
        # A stage0 언급 → B stage1 언급 = 노출 당회 즉답(u=0) — 획득이되 엄격 아님.
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": ["B"]}),
        ])
        recs, _ = tr.pair_records(j, ASSIGN)
        b = next(r for r in recs if r["agent_id"] == "B")
        self.assertEqual(b["kind"], "acquisition")
        self.assertEqual(b["u"], 0)
        self.assertFalse(b["strict"])
        self.assertTrue(b["u0_immediate"])
        self.assertTrue(b["in_window_at_tau"])

    def test_round0_nonholder_mention_is_prior_suspect(self):
        # round 0 입력에는 자기 할당 팩트뿐 — 비보유 C 의 stage0 언급은 정의상 prior_suspect.
        j = _judgment([
            _stage(0, {"f1": ["A", "C"]}),
            _stage(1, {"f1": []}),
        ])
        recs, _ = tr.pair_records(j, ASSIGN)
        c = next(r for r in recs if r["agent_id"] == "C")
        self.assertEqual(c["kind"], "prior_suspect")

    def test_censored_and_never_exposed(self):
        # A 가 stage1 에만 언급 → B·C 노출 e=2, 이후 미언급 = censored(censor_age=0).
        j = _judgment([
            _stage(0, {"f1": [], "f2": []}),
            _stage(1, {"f1": ["A"], "f2": []}),
            _stage(2, {"f1": [], "f2": []}),
        ])
        recs, _ = tr.pair_records(j, ASSIGN)
        b_f1 = next(r for r in recs if r["agent_id"] == "B" and r["fact_id"] == "f1")
        self.assertEqual(b_f1["kind"], "censored")
        self.assertEqual(b_f1["censor_age"], 0)
        # f2 는 아무도 언급 안 함 → 전 비보유 쌍 never_exposed.
        f2 = [r for r in recs if r["fact_id"] == "f2"]
        self.assertTrue(all(r["kind"] == "never_exposed" for r in f2))

    def test_ledger_channel_and_mixed(self):
        # f1: stage2 에 inject 만 → B 의 e=2 채널 ledger, stage3 언급 u=1 엄격.
        # f3: stage1 에 A 언급 + stage2 inject → e=2 는 organic(1에서 이미 노출)… 이 아니라
        #     A 의 stage1 언급이 만드는 노출은 idx2(stage2)다 — inject 도 stage2 → mixed.
        events = [{"event": "ledger_inject", "round": 2,
                   "injected_fact_ids": ["f1", "f3"]}]
        assign = _assignment({"A": ["f1", "f3"], "B": []})
        j = _judgment([
            _stage(0, {"f1": [], "f3": []}),
            _stage(1, {"f1": [], "f3": ["A"]}),
            _stage(2, {"f1": [], "f3": []}),
            _stage(3, {"f1": ["B"], "f3": []}),
        ])
        recs, _ = tr.pair_records(j, assign, events)
        b_f1 = next(r for r in recs if r["fact_id"] == "f1" and r["agent_id"] == "B")
        self.assertEqual(b_f1["kind"], "acquisition")
        self.assertEqual(b_f1["channel"], "ledger")
        self.assertEqual(b_f1["e_round"], 2)
        self.assertEqual(b_f1["u"], 1)
        b_f3 = next(r for r in recs if r["fact_id"] == "f3" and r["agent_id"] == "B")
        self.assertEqual(b_f3["channel"], "mixed")

    def test_line_topology_shadow(self):
        # line 좌석 [A,B,C]: C 의 이웃은 B 뿐. A 만 f1 언급 → C 는 비노출(never_exposed).
        events = [{"event": "seating", "structure": "line", "order": ["A", "B", "C"]}]
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": []}),
            _stage(2, {"f1": []}),
        ])
        recs, meta = tr.pair_records(j, ASSIGN, events)
        c = next(r for r in recs if r["agent_id"] == "C")
        self.assertEqual(c["kind"], "never_exposed")
        b = next(r for r in recs if r["agent_id"] == "B")
        self.assertIn(b["kind"], ("censored",))  # B 는 이웃 A 로 노출됨
        self.assertFalse(meta["edges"]["assumed_full"])


class TestAggregates(unittest.TestCase):
    def _mixed_records(self):
        # B: u=1 엄격 획득 / C: u=0 즉답.
        j = _judgment([
            _stage(0, {"f1": ["A"]}),
            _stage(1, {"f1": ["C"]}),
            _stage(2, {"f1": ["B"]}),
        ])
        return tr.pair_records(j, ASSIGN)

    def test_fact_metrics_strict_vs_upper(self):
        recs, _ = self._mixed_records()
        row = tr.fact_metrics(recs)[0]
        self.assertEqual(row["B"], 1)        # 엄격 = B 만
        self.assertEqual(row["B_upper"], 2)  # 상한 = B + C(u0)
        self.assertEqual(row["n_exposed"], 2)
        self.assertEqual(row["TSR"], 0.5)

    def test_question_exposed_excluded_from_system(self):
        recs, meta = tr.pair_records(
            _judgment([_stage(0, {"f1": ["A"]}), _stage(1, {"f1": ["B"]})]),
            ASSIGN, question_exposed_ids={"f1"})
        s = tr.system_summary(recs)
        self.assertEqual(s["n_pairs_tracked"], 0)
        self.assertEqual(s["n_pairs_excluded_question"], 2)
        self.assertEqual(meta["question_excluded_facts"], ["f1"])
        # 제외 팩트도 fact_metrics 행은 나온다(제외 표기 병기 의무).
        row = tr.fact_metrics(recs)[0]
        self.assertTrue(row["excluded"])

    def test_life_table_strict_censors_u0(self):
        recs, _ = self._mixed_records()
        lt = tr.acquisition_life_table(recs, include_u0=False)
        self.assertEqual(lt["n_u0_immediate_censored"], 1)
        # age0: at_risk 2(둘 다 관측), 사건 0(u0 은 검열). age1: B 획득.
        self.assertEqual(lt["life_table"][0]["acquisitions"], 0)
        self.assertEqual(lt["life_table"][1]["acquisitions"], 1)
        up = tr.acquisition_life_table(recs, include_u0=True)
        self.assertEqual(up["life_table"][0]["acquisitions"], 1)  # 상한은 u0 을 사건으로

    def test_b_pre_is_strictly_past(self):
        recs, _ = self._mixed_records()
        series = tr.b_pre_series(recs)
        self.assertEqual(series["f1"], [2])          # 엄격 획득 τ=2 만
        self.assertEqual(tr.b_pre(series, "f1", 2), 0)   # τ < 2 없음 — 미래 누출 금지
        self.assertEqual(tr.b_pre(series, "f1", 3), 1)


class TestDryrun2Smoke(unittest.TestCase):
    """dryrun2 정본 픽스처 — 구조 불변식 스모크(회사 데이터 불사용, ESA 전용)."""

    @classmethod
    def setUpClass(cls):
        jp = ROOT / "data" / "judgments" / "judgment_issue_esa_dryrun2.json"
        if not jp.exists():
            raise unittest.SkipTest("dryrun2 픽스처 없음")
        cls.j = json.loads(jp.read_text(encoding="utf-8"))
        cls.a = json.loads((ROOT / "data" / "assignments" /
                            "assignment_issue_esa.json").read_text(encoding="utf-8"))
        ev = []
        for line in (ROOT / "data" / "debates" /
                     "debate_issue_esa_dryrun2.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                ev.append(json.loads(line))
        cls.events = ev

    def test_invariants(self):
        recs, meta = tr.pair_records(self.j, self.a, self.events)
        agents, holders = tr.holders_map(self.a)
        # 쌍 수 = Σ_f (에이전트 수 − |H(f)|).
        expected = sum(len(agents) - len(holders.get(fid, set()))
                       for fid in {r["fact_id"] for r in recs})
        self.assertEqual(len(recs), expected)
        # 모든 레코드는 정확히 하나의 kind.
        for r in recs:
            self.assertIn(r["kind"],
                          ("acquisition", "prior_suspect", "censored", "never_exposed"))
        # 획득이면 e ≤ τ (노출 선행 조건).
        for r in recs:
            if r["kind"] == "acquisition":
                self.assertIsNotNone(r["e_round"])
                self.assertLessEqual(r["e_round"], r["tau_round"])
        # seating 이 있으므로 full 가정 아님.
        self.assertFalse(meta["edges"]["assumed_full"])

    def test_report_runs(self):
        rep = tr.report(self.j, self.a, self.events)
        self.assertIn("records", rep)
        self.assertIn("life_strict", rep)
        s = rep["system"]
        self.assertEqual(s["n_pairs_tracked"],
                         s["kinds"]["acquisition"] + s["kinds"]["censored"]
                         + s["kinds"]["prior_suspect"] + s["kinds"]["never_exposed"])


if __name__ == "__main__":
    unittest.main()
