"""협력(무입장) 조건 테스트 — API·저자 저장소(DelibTrace-main) 불필요.

검증 대상: ① stance 가드(미지 값·혼합 즉사 — 무음 변환 함정 제거) ② coop 분기가
우리 템플릿으로 돌고 저자 저장소를 안 건드림 ③ 산출 로그가 validate --deep
재조립 검증을 통과(등록제 A-3 집행 확인).
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
from modules.assignment_gen import generate_k_overlap


def fake_respond(inputs, model=None, temperature=None):
    return f"발언입니다 (입력 {len(inputs)}자)"


class CoopBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        repo_data = Path(__file__).resolve().parent.parent / "data"
        (self.tmp / "data").mkdir()
        for sub in ("issues", "facts", "assignments"):
            shutil.copytree(repo_data / sub, self.tmp / "data" / sub)
        for sub in ("debates", "judgments"):
            (self.tmp / "data" / sub).mkdir()
        self._saved_data = paths.DATA
        paths.DATA = self.tmp / "data"
        # 저자 저장소 접근 감시 — coop 경로는 이걸 절대 부르면 안 된다.
        self._saved_authors = (authors_prompts.load, authors_prompts.load_settings,
                               authors_prompts.version_tag)
        def _boom(*a, **k):
            raise AssertionError("coop 경로가 저자 저장소를 건드림")
        authors_prompts.load = _boom
        authors_prompts.load_settings = _boom
        authors_prompts.version_tag = _boom

    def tearDown(self):
        paths.DATA = self._saved_data
        (authors_prompts.load, authors_prompts.load_settings,
         authors_prompts.version_tag) = self._saved_authors
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_assignment(self, stances):
        facts_doc = json.loads(paths.facts("issue_esa").read_text(encoding="utf-8"))
        doc = generate_k_overlap(facts_doc, n_agents=len(stances), seed=42,
                                 overlap_k=2, stance_cycle=tuple(stances))
        p = paths.DATA / "assignments" / "assignment_issue_esa.json"
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def _cfg(self, **over):
        cfg = {"experiment": "coop_test", "issue_id": "issue_esa", "run_id": "coop1",
               "seed": 42, "agents": 4, "rounds": 2, "debate_model": "claude-haiku",
               "debate_temperature": 1.0, "judge_model": "claude-sonnet-4-6",
               "judge_temperature": 0, "judge_n_votes": 3, "ledger_mode": "off"}
        cfg.update(over)
        p = self.tmp / "cfg.yaml"
        p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
        return p

    def _run(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return debate_engine.run("issue_esa", "coop1", self._cfg(),
                                     utterance_fn=fake_respond)


class TestStanceGuard(CoopBase):
    def test_unknown_stance_dies(self):
        self._write_assignment(["pro", "con", "pro", "yes"])  # 오타 값
        with self.assertRaises(KeyError):
            self._run()

    def test_mixed_none_dies(self):
        self._write_assignment(["none", "pro", "none", "con"])
        with self.assertRaises(KeyError):
            self._run()


class TestCoopRun(CoopBase):
    def _events(self):
        self._write_assignment(["none"] * 4)
        path = self._run()
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()], path

    def test_templates_and_stance_preserved(self):
        events, _ = self._events()
        pas = [e for e in events if e["event"] == "prompt_assembly"]
        utts = [e for e in events if e["event"] == "utterance"]
        self.assertEqual({e["template"] for e in pas if e["round"] == 0}, {"coop_initial"})
        self.assertEqual({e["template"] for e in pas if e["round"] > 0}, {"coop_continue"})
        self.assertTrue(all(u["stance"] == "none" for u in utts))
        self.assertTrue(all(e["prompt_ver"].startswith("ours@") for e in pas))
        # 협력 continue는 배정 팩트 슬롯을 기록한다(정체 유지 조항)
        self.assertTrue(all(e["slots"]["assigned_fact_ids"] for e in pas if e["round"] > 0))

    def test_deep_validation_passes(self):
        _, path = self._events()
        with contextlib.redirect_stdout(io.StringIO()):
            validate.validate(path, deep=True)  # fail 시 SystemExit

    def test_deep_rejects_tampered_log(self):
        events, path = self._events()
        for e in events:
            if e["event"] == "utterance" and e["round"] == 1:
                e["response_text"] = "오염된 발언"  # 라운드1 발화 변조 → 라운드2 재조립 불일치
        path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events),
                        encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                validate.validate(path, deep=True)


if __name__ == "__main__":
    unittest.main()
