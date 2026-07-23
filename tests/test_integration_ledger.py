"""[민옥 · 수 밤 통합] debate_engine ↔ ledger v0 결합 테스트 — API 불필요(전부 가짜 주입).

검증 대상은 '결합부'다: 주입 시점(r>=2), ledger_inject 이벤트, off 모드 불변,
호출 상한·체크포인트. 판정 품질은 여기서 검증하지 않는다(그건 judge/사람라벨 몫).
저자 프롬프트 원문(DelibTrace-main)도 불필요 — authors_prompts 를 가짜로 대체한다.
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from modules import authors_prompts, debate_engine, paths
from modules.judge import judge_fact, judge_stage

INJECT_MARKER = "[장부 재고지]"

FAKE_PROMPTS = {
    "discussion_initial": "Q:<===question===>\nF:<===facts===>\nA:<===answer===>\n",
    "discussion_continue": ("Q:<===question===>\nS:<===setting===>\n"
                            "P:<===previous===>\nO:<===others===>\n"),
}

N_AGENTS = 8   # ESA 픽스처
N_FACTS = 12   # ESA 픽스처
ROUNDS = 3


def vote_all_unmentioned(fact, utts):
    return {"status": "unmentioned", "agents_mentioning": [], "reason": "fake"}


def vote_all_accepted(fact, utts):
    return {"status": "accepted", "agents_mentioning": [], "reason": "fake"}


class IntegrationBase(unittest.TestCase):
    """tmp 데이터 디렉토리 + 가짜 authors_prompts 로 격리 실행."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        repo_data = Path(__file__).resolve().parent.parent / "data"
        (self.tmp / "data").mkdir()
        for sub in ("issues", "facts", "assignments"):
            shutil.copytree(repo_data / sub, self.tmp / "data" / sub)
        for sub in ("debates", "judgments"):
            (self.tmp / "data" / sub).mkdir()

        self._saved = (paths.DATA, authors_prompts.load,
                       authors_prompts.load_settings, authors_prompts.version_tag)
        paths.DATA = self.tmp / "data"
        authors_prompts.load = lambda name: FAKE_PROMPTS[name]
        authors_prompts.load_settings = lambda: {"default": "be yourself"}
        authors_prompts.version_tag = lambda: "delibtrace@test"

        self.prompts_seen = []

    def tearDown(self):
        (paths.DATA, authors_prompts.load,
         authors_prompts.load_settings, authors_prompts.version_tag) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- 헬퍼 ---------------------------------------------------------------
    def fake_utterance(self, inputs, model=None, temperature=None):
        self.prompts_seen.append(inputs)
        return f"발화{len(self.prompts_seen)}"

    def write_config(self, **over):
        cfg = {
            "experiment": "test_integration", "issue_id": "issue_esa", "run_id": "t1",
            "seed": 42, "agents": N_AGENTS, "rounds": ROUNDS,
            "debate_model": "claude-haiku", "debate_temperature": 1.2,
            "judge_model": "claude-sonnet", "judge_temperature": 0,
            "judge_n_votes": 1, "ledger_mode": "off",
        }
        cfg.update(over)
        p = self.tmp / "cfg.yaml"
        p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
        return p

    def run_engine(self, cfg_path, vote_fn=None, run_id="t1"):
        # 진행 계기판(7/23)이 발화마다 콘솔 한 줄을 찍으므로, 테스트에서는 stdout 을
        # 흡수해 스모크 출력(quickstart 친절 요약)을 깨끗하게 유지한다.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = debate_engine.run("issue_esa", run_id, cfg_path,
                                       utterance_fn=self.fake_utterance,
                                       judge_vote_fn=vote_fn)
        self.last_stdout = buf.getvalue()
        return result

    def read_events(self, run_id="t1"):
        path = paths.debate("issue_esa", run_id)
        return [json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def prompts_of_round(self, r):
        """prompts_seen 은 호출 순서 그대로: 초기 8 → 라운드1 8 → 라운드2 8 → 라운드3 8."""
        return self.prompts_seen[N_AGENTS * r: N_AGENTS * (r + 1)]


class TestOffModeUnchanged(IntegrationBase):
    def test_off_no_ledger_events_and_no_injection(self):
        self.run_engine(self.write_config(ledger_mode="off"))
        events = self.read_events()
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds.count("utterance"), N_AGENTS * (ROUNDS + 1))
        self.assertEqual(kinds.count("ledger_inject"), 0)
        self.assertEqual(kinds.count("seating"), 1)
        for p in self.prompts_seen:
            self.assertNotIn(INJECT_MARKER, p)

    def test_unsupported_mode_rejected(self):
        with self.assertRaises(KeyError):
            self.run_engine(self.write_config(ledger_mode="v1"))


class TestV0Injection(IntegrationBase):
    def test_all_missing_injects_from_round2(self):
        self.run_engine(self.write_config(ledger_mode="v0"),
                        vote_fn=vote_all_unmentioned)
        events = self.read_events()
        injects = [e for e in events if e["event"] == "ledger_inject"]
        # 라운드 1 판정(전부 소실) → 라운드 2·3 에 주입. 라운드 1 주입은 없다(r>=2).
        self.assertEqual([e["round"] for e in injects], [2, 3])
        for e in injects:
            self.assertEqual(len(e["injected_fact_ids"]), N_FACTS)
            self.assertEqual(e["reason"], "v0_all_missing")
        # 프롬프트 실측: 라운드 0·1 은 깨끗, 라운드 2·3 은 전원 재주입 블록 포함.
        for r in (0, 1):
            for p in self.prompts_of_round(r):
                self.assertNotIn(INJECT_MARKER, p)
        for r in (2, 3):
            for p in self.prompts_of_round(r):
                self.assertIn(INJECT_MARKER, p)

    def test_inject_event_precedes_round_utterances(self):
        self.run_engine(self.write_config(ledger_mode="v0"),
                        vote_fn=vote_all_unmentioned)
        events = self.read_events()
        for r in (2, 3):
            idx_inject = next(i for i, e in enumerate(events)
                              if e["event"] == "ledger_inject" and e["round"] == r)
            idx_first_utt = next(i for i, e in enumerate(events)
                                 if e["event"] == "utterance" and e.get("round") == r)
            self.assertLess(idx_inject, idx_first_utt)

    def test_nothing_missing_no_injection(self):
        self.run_engine(self.write_config(ledger_mode="v0"),
                        vote_fn=vote_all_accepted)
        events = self.read_events()
        self.assertEqual([e for e in events if e["event"] == "ledger_inject"], [])
        for p in self.prompts_seen:
            self.assertNotIn(INJECT_MARKER, p)

    def test_debate_file_passes_validate(self):
        """스키마 4번: 모든 이벤트에 event/run_id/ts (validate.py 와 동일 기준)."""
        self.run_engine(self.write_config(ledger_mode="v0"),
                        vote_fn=vote_all_unmentioned)
        for e in self.read_events():
            for key in ("event", "run_id", "ts"):
                self.assertIn(key, e)


class TestCallCap(IntegrationBase):
    def test_cap_aborts_and_checkpoints(self):
        # 상한 = 초기 8발화 딱까지. 라운드 1 첫 호출(9번째)에서 중단돼야 한다.
        with self.assertRaises(SystemExit):
            self.run_engine(self.write_config(ledger_mode="off", max_llm_calls=N_AGENTS))
        events = self.read_events()  # 체크포인트가 남긴 파일
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds.count("utterance"), N_AGENTS)  # 초기 라운드만
        self.assertEqual(kinds.count("seating"), 1)

    def test_v0_votes_count_toward_cap(self):
        # 발화 16(초기+라운드1) + 라운드1 판정 12표 = 28 에서 상한 걸기 →
        # 라운드 1 판정 도중(29번째 호출)에 중단.
        cap = N_AGENTS * 2 + N_FACTS - 1
        with self.assertRaises(SystemExit):
            self.run_engine(self.write_config(ledger_mode="v0", max_llm_calls=cap),
                            vote_fn=vote_all_unmentioned)


class TestJudgeStageEquivalence(IntegrationBase):
    def test_judge_stage_equals_per_fact_calls(self):
        """judge_stage 는 judge_fact 반복과 결과 동일 — 잣대 단일화의 코드 증거."""
        facts = json.loads(paths.facts("issue_esa").read_text(encoding="utf-8"))["facts"]
        utts = [{"agent_id": "agent_1", "round": 1, "event": "utterance",
                 "response_text": facts[0]["text"]}]

        def det_vote(fact, stage_utts):
            return vote_all_accepted(fact, stage_utts)

        a = judge_stage(utts, facts, vote_fn=det_vote, n_votes=1)
        b = [judge_fact(utts, f, vote_fn=det_vote, n_votes=1) for f in facts]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
