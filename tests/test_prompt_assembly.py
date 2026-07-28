# -*- coding: utf-8 -*-
"""[요한 · v0.3 작업 이관분] prompt_assembly 이벤트 + injected_text + validate --deep 회귀.

검증 대상: ① 발화마다 조립 명세 이벤트가 나오고 hash 가 utterance 와 결합되는가
② 재주입 원문(injected_text)이 이벤트에 전문 보존되는가 ③ --deep 재조립 검증이
정상 로그를 통과시키고 오염 로그를 잡는가 ④ v0.2 구 로그(prompt_assembly 없음)는
--deep 에서도 통과하는가(append 호환). API 불필요 — 전부 가짜 주입(통합 테스트 전례).
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from modules import authors_prompts, debate_engine, paths, validate

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


class AssemblyBase(unittest.TestCase):
    """tmp 데이터 디렉토리 + 가짜 authors_prompts 격리 (test_integration_ledger 전례)."""

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

    def fake_utterance(self, inputs, model=None, temperature=None):
        self.prompts_seen.append(inputs)
        return f"발화{len(self.prompts_seen)}"

    def write_config(self, **over):
        cfg = {
            "experiment": "test_assembly", "issue_id": "issue_esa", "run_id": "t1",
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
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            return debate_engine.run("issue_esa", run_id, cfg_path,
                                     utterance_fn=self.fake_utterance,
                                     judge_vote_fn=vote_fn)

    def read_events(self, run_id="t1"):
        path = paths.debate("issue_esa", run_id)
        return [json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def deep_validate(self, path):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            validate.validate(path, deep=True)
        return buf.getvalue()


class TestAssemblyEvents(AssemblyBase):
    def test_every_utterance_has_matching_assembly(self):
        self.run_engine(self.write_config())
        events = self.read_events()
        pas = {(e["round"], e["agent_id"]): e
               for e in events if e["event"] == "prompt_assembly"}
        utts = [e for e in events if e["event"] == "utterance"]
        self.assertEqual(len(utts), N_AGENTS * (ROUNDS + 1))
        self.assertEqual(len(pas), len(utts))
        for u in utts:
            pa = pas[(u["round"], u["agent_id"])]
            self.assertEqual(pa["prompt_hash"], u["prompt_hash"])  # 결합 키

    def test_slot_shapes(self):
        self.run_engine(self.write_config())
        events = self.read_events()
        assign = json.loads(paths.assignment("issue_esa").read_text(encoding="utf-8"))
        by_agent = {a["agent_id"]: a for a in assign["agents"]}
        for pa in (e for e in events if e["event"] == "prompt_assembly"):
            if pa["round"] == 0:
                self.assertEqual(pa["template"], "discussion_initial")
                self.assertEqual(pa["slots"]["assigned_fact_ids"],
                                 by_agent[pa["agent_id"]]["assigned_fact_ids"])
                self.assertEqual(pa["slots"]["others"], [])
                self.assertIsNone(pa["slots"]["previous"])
            else:
                self.assertEqual(pa["template"], "discussion_continue")
                self.assertEqual(len(pa["slots"]["others"]), N_AGENTS - 1)  # full 토폴로지
                self.assertEqual(pa["slots"]["previous"]["round"], pa["round"] - 1)
                self.assertEqual(pa["slots"]["previous"]["agent_id"], pa["agent_id"])

    def test_injected_text_preserved_and_slot_marked(self):
        self.run_engine(self.write_config(ledger_mode="v0"), vote_fn=vote_all_unmentioned)
        events = self.read_events()
        injects = [e for e in events if e["event"] == "ledger_inject"]
        self.assertEqual([e["round"] for e in injects], [2, 3])
        from modules import ledger
        facts_by_id = ledger.load_facts_by_id("issue_esa")
        for e in injects:
            self.assertIn("injected_text", e)                    # v0.3 원문 전문 저장
            self.assertIn(INJECT_MARKER, e["injected_text"])
            # 원문 = build_injection_block 재현과 동일 (요약·변형 없음)
            self.assertEqual(e["injected_text"],
                             ledger.build_injection_block(e["injected_fact_ids"], facts_by_id))
        for pa in (e for e in events if e["event"] == "prompt_assembly"):
            if pa["round"] in (2, 3):
                self.assertEqual(pa["slots"]["inject"], {"round": pa["round"]})
            else:
                self.assertIsNone(pa["slots"]["inject"])


class TestDeepValidate(AssemblyBase):
    def test_deep_passes_off_and_v0(self):
        p_off = self.run_engine(self.write_config(ledger_mode="off"), run_id="toff")
        out = self.deep_validate(p_off)
        self.assertIn("재조립 검증 통과", out)
        self.prompts_seen = []
        p_v0 = self.run_engine(self.write_config(ledger_mode="v0", run_id="tv0"),
                               vote_fn=vote_all_unmentioned, run_id="tv0")
        out = self.deep_validate(p_v0)
        self.assertIn("재조립 검증 통과", out)

    def test_deep_catches_tampered_response(self):
        p = self.run_engine(self.write_config(ledger_mode="v0"),
                            vote_fn=vote_all_unmentioned)
        lines = p.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            ev = json.loads(line)
            # 라운드 1 발화 원문을 오염 → 라운드 2 others 재조립이 어긋나야 한다.
            if ev.get("event") == "utterance" and ev.get("round") == 1:
                ev["response_text"] = "오염된 원문"
                lines[i] = json.dumps(ev, ensure_ascii=False)
                break
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.deep_validate(p)

    def test_deep_skips_legacy_log(self):
        p = self.run_engine(self.write_config())
        lines = [line for line in p.read_text(encoding="utf-8").splitlines()
                 if json.loads(line).get("event") != "prompt_assembly"]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out = self.deep_validate(p)
        self.assertIn("구 로그", out)

    def test_plain_validate_unchanged(self):
        p = self.run_engine(self.write_config())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            validate.validate(p)  # deep 미지정 — 종전 구조 검사만
        self.assertIn("(debate jsonl)", buf.getvalue())
        self.assertNotIn("재조립", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
