"""조건부 소실률(survival.py) 단위 테스트 — API 불필요, 결정론적.

실행: python -m unittest tests.test_survival  (리포 루트에서)
또는: python -m pytest tests/test_survival.py

입력 두 종류(test_ledger 와 동일 스타일):
  1) 동범 오프라인 드라이런 산출물(data/judgments/judgment_issue_esa_dryrun.json)
  2) 손으로 만든 가짜 judgment — 엣지케이스(전부 생존/도입 후 소실/미등장 배제/재등장/단일 stage/빈 facts)

핵심 계약: 소실 = status ∉ SURVIVING. survival 은 judge·ledger 와 같은 잣대를 쓴다.
'아직 등장 전(unmentioned)'은 전이 모수에서 배제 → FAR 순환 함정 보정.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from modules import survival
from modules.judge import SURVIVING, far

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


def _facts_by_id(ids_critical: dict[str, bool]) -> dict[str, dict]:
    return {fid: {"fact_id": fid, "critical": c} for fid, c in ids_critical.items()}


class TestConditionalAttrition(unittest.TestCase):
    def test_survivor_set_is_shared_with_judge(self):
        # survival 의 계약은 'judge 와 같은 잣대 공유'(아래 assertIs)이지 잣대의 '내용'이 아니다.
        # 리터럴을 박으면 기업 회신으로 정의가 교체될 때 이 테스트가 엉뚱하게 깨진다 —
        # 교체 대상은 SCHEMA.md 와 judge 뿐이어야 한다.
        self.assertIs(survival.SURVIVING, SURVIVING)

    def test_all_survive_zero_attrition(self):
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "f1", "status": "mentioned"},
                                   {"fact_id": "f2", "status": "accepted"}]},
            {"stage": 1, "facts": [{"fact_id": "f1", "status": "accepted"},
                                   {"fact_id": "f2", "status": "mentioned"}]},
        ])
        rows = survival.conditional_attrition(j)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["surviving_denom"], 2)
        self.assertEqual(rows[0]["lost"], 0)
        self.assertEqual(rows[0]["cond_attrition"], 0.0)

    def test_introduced_then_lost(self):
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "f1", "status": "mentioned"},
                                   {"fact_id": "f2", "status": "accepted"}]},
            {"stage": 1, "facts": [{"fact_id": "f1", "status": "unmentioned"},
                                   {"fact_id": "f2", "status": "refuted"}]},
        ])
        row = survival.conditional_attrition(j)[0]
        self.assertEqual(row["surviving_denom"], 2)
        self.assertEqual(row["lost"], 2)
        self.assertEqual(row["cond_attrition"], 1.0)
        self.assertEqual(set(row["lost_fact_ids"]), {"f1", "f2"})

    def test_excludes_not_yet_appeared(self):
        # 핵심: stage0·1 모두 unmentioned 인 팩트는 전이 모수에서 빠져 조건부에 안 잡힌다.
        # (FAR 은 이걸 소실로 세지만 — 순환 함정. 조건부는 배제.)
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "seen", "status": "mentioned"},
                                   {"fact_id": "ghost", "status": "unmentioned"}]},
            {"stage": 1, "facts": [{"fact_id": "seen", "status": "mentioned"},
                                   {"fact_id": "ghost", "status": "unmentioned"}]},
        ])
        row = survival.conditional_attrition(j)[0]
        self.assertEqual(row["surviving_denom"], 1)  # 'seen' 만 모수
        self.assertEqual(row["lost"], 0)
        self.assertNotIn("ghost", row["lost_fact_ids"])
        # 대비: 같은 stage1 에서 FAR 은 'ghost' 를 소실로 센다(모수 2 중 1 소실).
        fbi = _facts_by_id({"seen": True, "ghost": True})
        self.assertEqual(far(j["stages"][1]["facts"], fbi), 0.5)

    def test_missing_record_counts_as_lost(self):
        # stage1 facts[] 에 f1 레코드 자체가 없음 → 소실, 내역은 'absent'(결정 2 + 감사 필드).
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "f1", "status": "mentioned"}]},
            {"stage": 1, "facts": []},
        ])
        row = survival.conditional_attrition(j)[0]
        self.assertEqual(row["lost"], 1)
        self.assertEqual(row["cond_attrition"], 1.0)
        self.assertIn("f1", row["lost_fact_ids"])
        self.assertEqual(row["lost_by_status"]["absent"], 1)

    def test_lost_by_status_breakdown(self):
        # 소실 원인이 unmentioned/refuted/absent 로 정확히 분해되는지.
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "a", "status": "mentioned"},
                                   {"fact_id": "b", "status": "mentioned"},
                                   {"fact_id": "c", "status": "mentioned"},
                                   {"fact_id": "d", "status": "mentioned"}]},
            {"stage": 1, "facts": [{"fact_id": "a", "status": "unmentioned"},
                                   {"fact_id": "b", "status": "refuted"},
                                   {"fact_id": "c", "status": "accepted"}]},  # d 레코드 부재
        ])
        row = survival.conditional_attrition(j)[0]
        self.assertEqual(row["lost"], 3)  # a,b,d 소실 · c 생존
        self.assertEqual(row["lost_by_status"],
                         {"unmentioned": 1, "refuted": 1, "ignored": 0, "absent": 1})

    def test_reappearance_hazard_vs_cumulative(self):
        # 두 지표 대비: mentioned→unmentioned→mentioned.
        # 전이 hazard 는 stage0→1 에서 소실(lost=1)로 잡지만,
        # 누적(post_intro_final_loss)은 마지막 stage 에서 재등장하므로 lost=0.
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "f1", "status": "mentioned"}]},
            {"stage": 1, "facts": [{"fact_id": "f1", "status": "unmentioned"}]},
            {"stage": 2, "facts": [{"fact_id": "f1", "status": "mentioned"}]},
        ])
        rows = survival.conditional_attrition(j)
        self.assertEqual(rows[0]["lost"], 1)   # 0→1: 사라짐
        self.assertEqual(rows[1]["lost"], 0)   # 1→2: (1의 모수 0이므로) 소실 없음
        cum = survival.post_intro_final_loss(j)
        self.assertEqual(cum["denom"], 1)
        self.assertEqual(cum["lost"], 0)       # 끝에서 다시 살아있음 → 누적 소실 0
        self.assertEqual(cum["rate"], 0.0)

    def test_single_stage_no_transitions(self):
        j = _judgment([{"stage": 0, "facts": [{"fact_id": "f1", "status": "mentioned"}]}])
        self.assertEqual(survival.conditional_attrition(j), [])
        cum = survival.post_intro_final_loss(j)
        self.assertEqual(cum, {"denom": 0, "lost": 0, "rate": None})

    def test_empty_facts_and_denom_zero_rate_none(self):
        # stage0 에 SURVIVING 이 하나도 없음 → 전이 모수 0 → rate None.
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "f1", "status": "unmentioned"}]},
            {"stage": 1, "facts": [{"fact_id": "f1", "status": "mentioned"}]},
        ])
        row = survival.conditional_attrition(j)[0]
        self.assertEqual(row["surviving_denom"], 0)
        self.assertEqual(row["lost"], 0)
        self.assertIsNone(row["cond_attrition"])

    def test_critical_only_filters(self):
        # critical=false 팩트는 모수에서 제외.
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "crit", "status": "mentioned"},
                                   {"fact_id": "noncrit", "status": "mentioned"}]},
            {"stage": 1, "facts": [{"fact_id": "crit", "status": "unmentioned"},
                                   {"fact_id": "noncrit", "status": "unmentioned"}]},
        ])
        fbi = _facts_by_id({"crit": True, "noncrit": False})
        row = survival.conditional_attrition(j, fbi, critical_only=True)[0]
        self.assertEqual(row["surviving_denom"], 1)  # crit 만
        self.assertEqual(row["lost_fact_ids"], ["crit"])

    def test_far_by_stage_matches_judge_far(self):
        # 병기 FAR 값이 judge.far 직접 호출과 일치(재구현 아님, 위임).
        j = _judgment([
            {"stage": 0, "facts": [{"fact_id": "f1", "status": "mentioned"},
                                   {"fact_id": "f2", "status": "unmentioned"}]},
            {"stage": 1, "facts": [{"fact_id": "f1", "status": "refuted"},
                                   {"fact_id": "f2", "status": "unmentioned"}]},
        ])
        fbi = _facts_by_id({"f1": True, "f2": True})
        got = survival.far_by_stage(j, fbi)
        self.assertEqual(got[0]["far"], far(j["stages"][0]["facts"], fbi))
        self.assertEqual(got[1]["far"], far(j["stages"][1]["facts"], fbi))
        self.assertEqual(got[1]["far"], 1.0)  # stage1 둘 다 소실

    def test_depends_only_on_fact_id_and_status(self):
        # votes 등 세부 구조를 지워도 결과 동일(구조 의존 최소화 계약).
        rich = _judgment([
            {"stage": 0, "facts": [{"fact_id": "f1", "status": "mentioned",
                                    "votes": [1, 2, 3], "agents_mentioning": ["a"]}]},
            {"stage": 1, "facts": [{"fact_id": "f1", "status": "unmentioned",
                                    "votes": [0], "agents_mentioning": []}]},
        ])
        stripped = _judgment([
            {"stage": st["stage"],
             "facts": [{"fact_id": f["fact_id"], "status": f["status"]} for f in st["facts"]]}
            for st in rich["stages"]
        ])
        self.assertEqual(survival.conditional_attrition(rich),
                         survival.conditional_attrition(stripped))


class TestAgainstDongbeomDryrun(unittest.TestCase):
    """동범 오프라인 드라이런 실입력 — 순환 함정 보정을 실측으로 입증."""

    @classmethod
    def setUpClass(cls):
        p = ROOT / "data" / "judgments" / "judgment_issue_esa_dryrun.json"
        if not p.exists():
            raise unittest.SkipTest(f"드라이런 판정 파일 없음: {p}")
        cls.judgment = json.loads(p.read_text(encoding="utf-8"))
        cls.facts_by_id = survival.ledger.load_facts_by_id("issue_esa")

    def test_transitions_all_zero_conditional(self):
        # 드라이런: status 가 전 stage 불변(fact_01·02 만 mentioned) → 한번 등장한 건 안 사라짐.
        rows = survival.conditional_attrition(self.judgment)
        self.assertEqual(len(rows), 3)  # stage 0..3 → 전이 3개
        for r in rows:
            self.assertEqual(r["surviving_denom"], 2)
            self.assertEqual(r["lost"], 0)
            self.assertEqual(r["cond_attrition"], 0.0)

    def test_cumulative_final_loss_zero(self):
        cum = survival.post_intro_final_loss(self.judgment)
        self.assertEqual(cum["denom"], 2)  # fact_01·02 도입
        self.assertEqual(cum["lost"], 0)
        self.assertEqual(cum["rate"], 0.0)

    def test_far_contrast(self):
        # 대비의 핵심: 전체 FAR 은 0.8333 로 높지만 조건부는 0.0. 이 지표의 존재 이유.
        fbs = survival.far_by_stage(self.judgment, self.facts_by_id)
        for f in fbs:
            self.assertEqual(f["far"], 0.8333)

    def test_critical_only_contrast(self):
        rows = survival.conditional_attrition(self.judgment, self.facts_by_id, critical_only=True)
        for r in rows:
            self.assertEqual(r["surviving_denom"], 2)  # fact_01·02 둘 다 critical
            self.assertEqual(r["cond_attrition"], 0.0)
        fbs = survival.far_by_stage(self.judgment, self.facts_by_id, critical_only=True)
        for f in fbs:
            self.assertEqual(f["far"], 0.7778)


if __name__ == "__main__":
    unittest.main(verbosity=2)
