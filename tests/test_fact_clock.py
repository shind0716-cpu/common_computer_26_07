"""팩트 기준 시계(fact-clock, survival.py 추가분) 단위 테스트 — API 불필요, 결정론적.

실행: python -m unittest tests.test_fact_clock  (리포 루트에서)

사전 고정 기준: docs/analysis/FACTCLOCK_PREREG.md
핵심 계약: 도입 = 첫 SURVIVING stage(위치). 미도입 제외. age t hazard 분모는 우측 검열
(관측창 >= t 이고 t-1까지 생존)로 한정. w=0/w=1 병렬. 잣대는 judge.SURVIVING 공유.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from modules import survival
from modules.judge import SURVIVING

ROOT = Path(__file__).resolve().parent.parent


def _judgment(seqs: dict[str, list[str]], run_id: str = "fake") -> dict:
    """fact_id -> stage별 status 열(위치 순) 로 최소 judgment 조립.

    예: {"f1": ["mentioned", "unmentioned"]} → stage0=mentioned, stage1=unmentioned.
    매 stage 는 전 팩트 완전 스냅샷(계약)이라 모든 열의 길이가 같아야 한다.
    """
    n = len(next(iter(seqs.values())))
    stages = [{"stage": i,
               "facts": [{"fact_id": fid, "status": seqs[fid][i]} for fid in seqs]}
              for i in range(n)]
    return {"schema_ver": "0.2", "issue_id": "issue_esa", "run_id": run_id,
            "stage_type": "round", "stages": stages, "summary": {}}


def _hazards(fc: dict) -> dict[int, float | None]:
    return {r["age"]: r["hazard"] for r in fc["life_table"]}


def _deaths(fc: dict) -> dict[int, int]:
    return {r["age"]: r["deaths"] for r in fc["life_table"]}


class TestFactEventFormalization(unittest.TestCase):
    """_fact_event 의사코드(FACTCLOCK_PREREG §2·§3)를 직접 검증."""

    def test_w0_immediate_death(self):
        # S - S : w=0 은 첫 비생존 즉시 사망(age1), 재등장 무시.
        self.assertEqual(survival._fact_event([True, False, True], 0), ("death", 1, "fatal_run"))

    def test_w1_bridges_single_silence(self):
        # S - S : w=1 은 한 stage 침묵 후 재등장 → 사망 아님, 끝까지 생존 → 검열(age2).
        self.assertEqual(survival._fact_event([True, False, True], 1),
                         ("censored", 2, "survived_to_end"))

    def test_w1_two_consecutive_is_death(self):
        # S - - S : 연속 2침묵(런 길이 2 = w+1) → w=1 도 사망, age=런 시작(1).
        self.assertEqual(survival._fact_event([True, False, False, True], 1),
                         ("death", 1, "fatal_run"))

    def test_w1_boundary_silence_is_terminal_silence(self):
        # S S - : 마지막 age 단일 침묵(미확정) → w=1 은 검열(직전 생존 age1), 사유 terminal_silence.
        # ← 이게 "관측창 부족 검열" 케이스. churn 과 구분되어야 하는 바로 그 기전.
        self.assertEqual(survival._fact_event([True, True, False], 1),
                         ("censored", 1, "terminal_silence"))
        # 대비: w=0 은 같은 열에서 사망(age2).
        self.assertEqual(survival._fact_event([True, True, False], 0), ("death", 2, "fatal_run"))

    def test_survives_all_censored_at_M(self):
        self.assertEqual(survival._fact_event([True, True, True], 0),
                         ("censored", 2, "survived_to_end"))


class TestFactClockDryrun2(unittest.TestCase):
    """dryrun2 정본: 12팩트 전부 age0 도입 → fact-clock 이 전역 시계와 일치."""

    @classmethod
    def setUpClass(cls):
        p = ROOT / "data" / "judgments" / "judgment_issue_esa_dryrun2.json"
        if not p.exists():
            raise unittest.SkipTest(f"dryrun2 정본 없음: {p}")
        cls.j = json.loads(p.read_text(encoding="utf-8"))

    def test_hazard_matches_global_decay(self):
        # 전부 age0 도입이므로 age == 전역 stage. WORKLOG hazard 0.1667→0.4→0.0.
        fc = survival.fact_clock(self.j, w=0)
        self.assertEqual(fc["population"]["n_introduced"], 12)
        self.assertEqual(fc["population"]["n_never_introduced"], 0)
        h = _hazards(fc)
        self.assertEqual(h[1], 0.1667)
        self.assertEqual(h[2], 0.4)
        self.assertEqual(h[0], 0.0)
        self.assertEqual(h[3], 0.0)
        # at-risk 감소: 12 → 12 → 10 → 6
        atrisk = {r["age"]: r["at_risk"] for r in fc["life_table"]}
        self.assertEqual([atrisk[a] for a in (0, 1, 2, 3)], [12, 12, 10, 6])

    def test_w0_w1_identical_when_no_reappearance(self):
        # dryrun2 엔 재등장(S-S)이 없으므로 두 허용폭 결과가 같아야 한다.
        rep = survival.fact_clock_report(self.j)
        self.assertEqual(_hazards(rep["by_w"][0]), _hazards(rep["by_w"][1]))


class TestCensoringBoundary(unittest.TestCase):
    def test_last_stage_intro_only_age0(self):
        # 마지막 stage 에서 도입된 팩트 = age0 만 관측 → age>=1 분모에서 제외(우측 검열).
        j = _judgment({"late": ["unmentioned", "unmentioned", "mentioned"]})
        fc = survival.fact_clock(j, w=0)
        self.assertEqual(fc["population"]["n_introduced"], 1)
        self.assertEqual(fc["max_age"], 0)
        lt = {r["age"]: r for r in fc["life_table"]}
        self.assertEqual(lt[0]["at_risk"], 1)
        self.assertEqual(lt[0]["censored"], 1)  # 사망 불가, 관측 끝 → 검열
        self.assertEqual(fc["n_deaths_total"], 0)

    def test_short_window_fact_excluded_from_later_denominator(self):
        # early(age0 도입, age1 사망) + late(age2 도입). age1 분모에 late 는 안 들어감.
        j = _judgment({
            "early": ["mentioned", "unmentioned", "unmentioned"],
            "late":  ["unmentioned", "unmentioned", "mentioned"],
        })
        fc = survival.fact_clock(j, w=0)
        lt = {r["age"]: r for r in fc["life_table"]}
        self.assertEqual(lt[1]["at_risk"], 1)   # early 만 (late 는 관측창 age0 뿐)
        self.assertEqual(lt[1]["deaths"], 1)
        self.assertEqual(lt[1]["hazard"], 1.0)


class TestReappearanceWDivergence(unittest.TestCase):
    def test_w0_vs_w1_diverge_on_reappearance(self):
        # S - S : w=0 은 age1 사망, w=1 은 생존(검열). 두 생명표가 달라야 한다.
        j = _judgment({"reap": ["mentioned", "unmentioned", "mentioned"]})
        rep = survival.fact_clock_report(j)
        d0, d1 = _deaths(rep["by_w"][0]), _deaths(rep["by_w"][1])
        self.assertEqual(d0[1], 1)                       # w=0: age1 사망
        self.assertEqual(rep["by_w"][1]["n_deaths_total"], 0)  # w=1: 사망 없음
        self.assertNotEqual(_hazards(rep["by_w"][0]), _hazards(rep["by_w"][1]))
        self.assertEqual(rep["by_w"][0]["n_deaths_total"], 1)

    def test_two_consecutive_silence_dies_under_w1(self):
        # S - - S : 연속 2침묵 → w=1 도 age1 사망, 뒤 재등장 무시.
        j = _judgment({"twosil": ["mentioned", "unmentioned", "unmentioned", "mentioned"]})
        rep = survival.fact_clock_report(j)
        self.assertEqual(_deaths(rep["by_w"][1])[1], 1)
        self.assertEqual(_deaths(rep["by_w"][0])[1], 1)


class TestNeverIntroducedExcluded(unittest.TestCase):
    def test_ghost_excluded_and_counted(self):
        j = _judgment({
            "seen":  ["mentioned", "mentioned"],
            "ghost": ["unmentioned", "unmentioned"],  # 한 번도 생존 못함 → 미도입
        })
        fc = survival.fact_clock(j, w=0)
        self.assertEqual(fc["population"]["n_introduced"], 1)     # seen 만
        self.assertEqual(fc["population"]["n_never_introduced"], 1)
        self.assertEqual(fc["population"]["never_introduced"][0]["fact_id"], "ghost")


class TestPooling(unittest.TestCase):
    def test_two_judgments_pooled_by_age(self):
        # 두 run 의 age1 사망을 합산 → deaths(1)=2.
        j1 = _judgment({"a": ["mentioned", "unmentioned"]}, run_id="r1")
        j2 = _judgment({"b": ["mentioned", "unmentioned"]}, run_id="r2")
        fc = survival.fact_clock([j1, j2], w=0)
        self.assertEqual(fc["population"]["n_introduced"], 2)
        self.assertEqual(_deaths(fc)[1], 2)
        rep = survival.fact_clock_report([j1, j2])
        self.assertEqual(rep["audit"]["n_judgments"], 2)
        self.assertEqual(len(rep["audit"]["inputs"]), 2)
        self.assertTrue(all(inp["sha256"] for inp in rep["audit"]["inputs"]))


class TestWDivergenceMechanism(unittest.TestCase):
    """w=1 사망 감소가 churn 인지 관측창 부족(terminal silence)인지 분리 — 리뷰 지적 반영."""

    def test_split_terminal_silence_vs_churn_vs_robust(self):
        # 세 팩트: 종말부침묵 / 재등장 / 강건사망 — w0 사망이 w1 에서 갈리는 세 갈래.
        j = _judgment({
            "term":   ["mentioned", "mentioned", "unmentioned"],    # SS- : w0 death, w1 종말부침묵
            "churn":  ["mentioned", "unmentioned", "mentioned"],    # S-S : w0 death, w1 재등장 생존
            "robust": ["mentioned", "unmentioned", "unmentioned"],  # S-- : w0·w1 모두 사망
        })
        wd = survival.w_divergence(j)
        self.assertEqual(wd["counts"], {
            "death_robust": 1,
            "churn_reappearance": 1,
            "artifact_terminal_silence": 1,
        })

    def test_censored_breakdown_separates_terminal_silence(self):
        # w=1 검열 사유 분해: term(종말부침묵) 1 · survivor(끝까지생존) 1.
        j = _judgment({
            "term":     ["mentioned", "mentioned", "unmentioned"],  # w1 terminal_silence
            "survivor": ["mentioned", "mentioned", "mentioned"],    # w1 survived_to_end
        })
        fc1 = survival.fact_clock(j, w=1)
        self.assertEqual(fc1["censored_breakdown"]["terminal_silence"], 1)
        self.assertEqual(fc1["censored_breakdown"]["survived_to_end"], 1)
        self.assertEqual(fc1["n_deaths_total"], 0)

    def test_report_includes_w_divergence_when_both_w(self):
        rep = survival.fact_clock_report(
            _judgment({"term": ["mentioned", "mentioned", "unmentioned"]}))
        self.assertIn("w_divergence", rep)
        self.assertEqual(rep["w_divergence"]["counts"]["artifact_terminal_silence"], 1)
        # churn 아님을 명시적으로 단언(리뷰 지적의 핵심).
        self.assertEqual(rep["w_divergence"]["counts"]["churn_reappearance"], 0)


class TestReportContract(unittest.TestCase):
    def test_shares_survivor_set_with_judge(self):
        # P2 와 동일 계약: 잣대는 judge.SURVIVING 단일 소스.
        rep = survival.fact_clock_report(_judgment({"f": ["mentioned"]}))
        self.assertEqual(rep["surviving_set"], sorted(SURVIVING))
        self.assertEqual(set(rep["by_w"].keys()), {0, 1})
        self.assertEqual(rep["protocol"], "docs/analysis/FACTCLOCK_PREREG.md")

    def test_depends_only_on_fact_id_and_status(self):
        # votes 등 세부 구조를 지워도 결과 동일(구조 의존 최소화).
        rich = {"schema_ver": "0.2", "issue_id": "i", "run_id": "r", "stage_type": "round",
                "stages": [
                    {"stage": 0, "facts": [{"fact_id": "f", "status": "mentioned",
                                            "votes": [1, 2, 3], "agents_mentioning": ["a"]}]},
                    {"stage": 1, "facts": [{"fact_id": "f", "status": "unmentioned",
                                            "votes": [0]}]}]}
        stripped = _judgment({"f": ["mentioned", "unmentioned"]}, run_id="r")
        self.assertEqual(_deaths(survival.fact_clock(rich)), _deaths(survival.fact_clock(stripped)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
