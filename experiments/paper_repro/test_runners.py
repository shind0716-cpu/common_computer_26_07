# -*- coding: utf-8 -*-
"""논문 재현 러너의 계약·안전장치 테스트 (LLM 호출 0)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import assign_perspective as assign  # noqa: E402
import extract_facts as extract  # noqa: E402


class ExtractFactsTests(unittest.TestCase):
    def test_build_facts_doc_matches_fixture_shape_and_positional_ids(self):
        doc = extract.build_facts_doc(
            issue_id="issue_ethics_0036",
            refined=["one", "two"],
            important=[True, False],
            created_at="2026-08-10T00:00:00+00:00",
            prompt_ver="delibtrace@test",
        )
        fixture = json.loads((HERE / "fixtures" / "data" / "facts" /
                              "facts_issue_repro_fx.json").read_text(encoding="utf-8"))
        self.assertEqual(set(doc), set(fixture))
        self.assertEqual(set(doc["facts"][0]), set(fixture["facts"][0]))
        self.assertEqual([f["fact_id"] for f in doc["facts"]],
                         ["fact_ethics_0036_01", "fact_ethics_0036_02"])
        self.assertEqual([f["origin_index"] for f in doc["facts"]], [0, 1])
        self.assertEqual([f["critical"] for f in doc["facts"]], [True, False])

    def test_build_facts_doc_rejects_mismatched_select_length(self):
        with self.assertRaises(ValueError):
            extract.build_facts_doc("issue_ethics_0001", ["one"], [True, False],
                                    "2026-08-10T00:00:00+00:00", "test")

    def test_build_facts_doc_accepts_probe_integer_flags_as_contract_bools(self):
        probe = json.loads((HERE / "probe" / "probe_result.json").read_text(encoding="utf-8"))
        important = probe["results"][0]["by_model"]["gpt-5"]["important_title"]
        refined = [f"fact {i}" for i in range(len(important))]
        doc = extract.build_facts_doc(
            "issue_ethics_0001", refined, important,
            "2026-08-10T00:00:00+00:00", "delibtrace@test")
        critical = [fact["critical"] for fact in doc["facts"]]
        self.assertEqual(critical, [bool(value) for value in important])
        self.assertTrue(all(isinstance(value, bool) for value in critical))
        for invalid in (2, -1, 1.0, "1"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                extract.build_facts_doc(
                    "issue_ethics_0001", ["fact"], [invalid],
                    "2026-08-10T00:00:00+00:00", "delibtrace@test")

    def test_checkpoint_appends_raw_and_resumes_by_tag_without_second_call(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "calls.jsonl"
            seen = []
            calls = extract.CallCheckpoint(path, max_calls=1,
                                           responder=lambda prompt: seen.append(prompt) or '["ok"]')
            self.assertEqual(calls.call("prompt", "x|initial"), '["ok"]')
            resumed = extract.CallCheckpoint(path, max_calls=0,
                                             responder=lambda prompt: self.fail("must resume"))
            # 같은 프롬프트로 재개해야 한다 — 다른 프롬프트 적중은 이제 좌표 불일치로 즉사
            # (PR#34 리뷰 반영, CheckpointIdentityTests 참조).
            self.assertEqual(resumed.call("prompt", "x|initial"), '["ok"]')
            record = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(record["raw"], '["ok"]')
            self.assertEqual(seen, ["prompt"])

    def test_checkpoint_raises_at_global_call_cap(self):
        with tempfile.TemporaryDirectory() as td:
            calls = extract.CallCheckpoint(Path(td) / "calls.jsonl", max_calls=0,
                                           responder=lambda prompt: '["unexpected"]')
            with self.assertRaises(RuntimeError):
                calls.call("prompt", "x|initial")

    def test_parse_failure_skips_one_issue_and_records_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            data_root = Path(td)
            issue_ids = ["issue_ethics_0001", "issue_ethics_0002"]
            (data_root / "issues").mkdir(parents=True)
            (data_root / "raw_calls").mkdir(parents=True)
            manifest = {"sample": {"n": 2, "ids": [
                {"issue_id": issue_id} for issue_id in issue_ids
            ]}}
            (data_root / "sample_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8")
            for issue_id in issue_ids:
                issue = {"issue_id": issue_id, "body": f"body for {issue_id}",
                         "question": f"question for {issue_id}"}
                (data_root / "issues" / f"{issue_id}.json").write_text(
                    json.dumps(issue), encoding="utf-8")

            # 실제 원장 형식대로 좌표를 지닌 레코드 — 좌표 없는 행은 이제 재사용이
            # 거부되므로(PR#34 리뷰) 픽스처도 현실 형식을 따른다.
            coords = {"model": extract.MODEL, "temperature": extract.TEMPERATURE,
                      "n": extract.N,
                      "prompt_ver": extract.authors_prompts.version_tag()}
            records = [
                {"tag": "issue_ethics_0001|initial", **coords, "raw": "not json"},
                {"tag": "issue_ethics_0002|initial", **coords, "raw": '["raw fact"]'},
                {"tag": "issue_ethics_0002|refine", **coords, "raw":
                 '["one", "two", "three", "four", "five"]'},
                {"tag": "issue_ethics_0002|select", **coords, "raw": "[1, 0, 0, 0, 0]"},
            ]
            raw_path = data_root / "raw_calls" / "extract_facts_calls.jsonl"
            raw_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

            with mock.patch.object(extract.llm, "preflight"):
                result = extract.run(data_root, max_calls=0, dry=False)

            self.assertEqual(result["actual_calls"], 0)
            self.assertEqual(result["n_written_and_validated"], 1)
            self.assertEqual(result["failed_parse"], [{
                "issue_id": "issue_ethics_0001",
                "stage": "initial",
                "tag": "issue_ethics_0001|initial",
            }])
            facts_path = data_root / "facts" / "facts_issue_ethics_0002.json"
            self.assertTrue(facts_path.exists())
            saved_manifest = json.loads(
                (data_root / "facts_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_manifest["failed_parse"], result["failed_parse"])
            self.assertEqual(raw_path.read_text(encoding="utf-8").count("not json"), 1)


class AssignPerspectiveTests(unittest.TestCase):
    def test_build_assignment_matches_fixture_shape_and_pairs(self):
        facts = [
            {"fact_id": f"fact_ethics_0036_{i + 1:02d}", "origin_index": i,
             "text": f"fact {i}", "tags": [], "critical": i == 0,
             "prior": {"score": None, "probe_model": None,
                       "probe_prompt_ver": None, "probed_at": None}}
            for i in range(5)
        ]
        sets = [[0, 1], [0, 2], [0, 3], [0, 4]]
        doc = assign.build_assignment_doc(
            "issue_ethics_0036", facts, sets,
            "2026-08-10T00:00:00+00:00")
        fixture = json.loads((HERE / "fixtures" / "data" / "assignments" /
                              "assignment_issue_repro_fx.json").read_text(encoding="utf-8"))
        self.assertEqual(set(doc), set(fixture))
        self.assertEqual(set(doc["agents"][0]), set(fixture["agents"][0]))
        self.assertEqual(doc["seed"], 20260810)
        self.assertEqual(doc["perspective_sets"]["sets"], sets)
        for i in range(0, 8, 2):
            self.assertEqual(doc["agents"][i]["assigned_fact_ids"],
                             doc["agents"][i + 1]["assigned_fact_ids"])

    def test_author_rule_audit_counts_semantic_violations(self):
        facts = [{"critical": i == 0} for i in range(5)]
        ok = assign.audit_perspective_sets([[0, 1], [0, 2], [0, 3], [0, 4]], facts)
        self.assertEqual(ok, [])
        bad = assign.audit_perspective_sets([[1], [1], [1], [1]], facts)
        self.assertIn("critical_missing", bad)
        self.assertIn("fact_uncovered", bad)

    def test_author_check_available_requires_exactly_four_lists(self):
        self.assertTrue(assign.check_available("body", "question", [], [[], [], [], []]))
        self.assertFalse(assign.check_available("body", "question", [], [[], [], []]))
        self.assertFalse(assign.check_available("body", "question", [], "not-a-list"))


if __name__ == "__main__":
    unittest.main()


class CheckpointIdentityTests(unittest.TestCase):
    """PR#34 리뷰 회귀 — 캐시 행은 자기 실행 좌표를 지니고, 적중 시 불일치면 즉사."""

    def test_hit_rejects_stale_coordinates(self):
        # 리뷰 재현 시나리오 그대로: prompt_ver=old·model=old 행을 새 좌표로 적중
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "calls.jsonl"
            stale = {"tag": "x|initial", "model": "old-model", "temperature": 0.7,
                     "n": 1, "prompt_ver": "old", "raw": "STALE"}
            path.write_text(json.dumps(stale) + "\n", encoding="utf-8")
            cp = extract.CallCheckpoint(path, max_calls=0, prompt_ver="new",
                                        responder=lambda p: self.fail("호출 금지"))
            with self.assertRaises(extract.CheckpointMismatch):
                cp.call("prompt", "x|initial")

    def test_hit_rejects_changed_prompt_when_hash_present(self):
        # 변형: 좌표는 전부 같고 프롬프트만 다름 — prompt_sha256 으로 걸린다
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "calls.jsonl"
            cp = extract.CallCheckpoint(path, max_calls=1, prompt_ver="v",
                                        responder=lambda p: "FRESH")
            cp.call("prompt A", "x|initial")
            resumed = extract.CallCheckpoint(path, max_calls=0, prompt_ver="v",
                                             responder=lambda p: self.fail("호출 금지"))
            with self.assertRaises(extract.CheckpointMismatch):
                resumed.call("prompt B", "x|initial")

    def test_hit_accepts_legacy_record_without_prompt_hash(self):
        # 1차 트랜치 79콜 형식(prompt_sha256 부재) — 있는 좌표가 다 맞으면 재사용 허용
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "calls.jsonl"
            legacy = {"tag": "x|initial", "model": extract.MODEL,
                      "temperature": extract.TEMPERATURE, "n": extract.N,
                      "prompt_ver": "v", "raw": "KEPT"}
            path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
            cp = extract.CallCheckpoint(path, max_calls=0, prompt_ver="v",
                                        responder=lambda p: self.fail("호출 금지"))
            self.assertEqual(cp.call("any prompt", "x|initial"), "KEPT")


class ProbeCheckpointTests(unittest.TestCase):
    """PR#34 리뷰 회귀 — probe dry/live 격리·매 콜 flush·좌표 대조."""

    def setUp(self):
        import probe_extract
        self.probe = probe_extract
        self.probe._calls = 0
        self.probe._cap = 0
        self._old_ck = self.probe._ck_path
        self.probe._ck_path = None

    def tearDown(self):
        self.probe._ck_path = self._old_ck

    def test_dry_record_is_flushed_immediately_and_marked(self):
        with tempfile.TemporaryDirectory() as td:
            self.probe._ck_path = Path(td) / "probe_calls_dry.jsonl"
            ckpt = {}
            self.probe.call("P", "gpt-5", "id|gpt-5|initial", ckpt, dry=True)
            rec = json.loads(self.probe._ck_path.read_text(encoding="utf-8").strip())
            self.assertEqual(rec["mode"], "dry")
            self.assertEqual(rec["raw"], '["dry"]')

    def test_live_hit_on_dry_record_dies(self):
        # 리뷰 재현 시나리오: dry 잔재를 live 가 캐시 적중 — API 0회 재사용 대신 즉사
        ver = self.probe.authors_prompts.version_tag()
        ckpt = {"t": {"tag": "t", "mode": "dry", "prompt_ver": ver, "raw": '["dry"]'}}
        with self.assertRaises(SystemExit):
            self.probe.call("P", "gpt-5", "t", ckpt, dry=False)

    def test_legacy_live_record_without_mode_is_reused(self):
        # 프로브 40콜 구 기록(mode 부재=live) — prompt_ver 일치 시 재사용 허용
        ver = self.probe.authors_prompts.version_tag()
        ckpt = {"t": {"tag": "t", "prompt_ver": ver, "raw": "KEPT"}}
        self.assertEqual(self.probe.call("P", "gpt-5", "t", ckpt, dry=False), "KEPT")

    def test_hit_rejects_prompt_ver_drift(self):
        ckpt = {"t": {"tag": "t", "prompt_ver": "delibtrace@old", "raw": "STALE"}}
        with self.assertRaises(SystemExit):
            self.probe.call("P", "gpt-5", "t", ckpt, dry=False)


class ReuseGateTests(unittest.TestCase):
    """PR#34 리뷰 회귀 — rehearse_splice 재사용 관문 3종(좌표 증명 없이는 재사용 금지)."""

    @classmethod
    def setUpClass(cls):
        import rehearse_splice
        cls.rs = rehearse_splice

    def _debate(self, td: Path, cfg_sha: str | None) -> Path:
        dp = td / "debate.jsonl"
        lines = []
        if cfg_sha is not None:
            lines.append(json.dumps({"event": "run_meta",
                                     "config_ref": {"name": "c.yaml", "sha256": cfg_sha}}))
        lines.append(json.dumps({"event": "utterance"}))
        dp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return dp

    def test_debate_gate_accepts_match_rejects_mismatch_and_missing_meta(self):
        import hashlib as _hl
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg = td / "c.yaml"
            cfg.write_text("rounds: 3\n", encoding="utf-8")
            sha = _hl.sha256(cfg.read_bytes()).hexdigest()
            self.rs.check_debate_provenance(self._debate(td, sha), cfg)  # 일치 — 통과
            cfg.write_text("rounds: 4\n", encoding="utf-8")  # 조건 변경 = 다른 지문
            with self.assertRaises(SystemExit):
                self.rs.check_debate_provenance(self._debate(td, sha), cfg)
            with self.assertRaises(SystemExit):  # run_meta 부재 = 모름 → 재사용 거부
                self.rs.check_debate_provenance(self._debate(td, None), cfg)

    def test_judgment_gate_checks_all_four_coordinates(self):
        jd = {"issue_id": "i", "run_id": "r",
              "stages": [{"facts": [{"fact_id": "f1"}, {"fact_id": "f2"}]}] * 4}
        self.rs.check_judgment_provenance(jd, "i", "r", 4, {"f1", "f2"})  # 통과
        for bad in (dict(jd, issue_id="other"), dict(jd, run_id="other")):
            with self.assertRaises(SystemExit):
                self.rs.check_judgment_provenance(bad, "i", "r", 4, {"f1", "f2"})
        with self.assertRaises(SystemExit):  # rounds 상이
            self.rs.check_judgment_provenance(jd, "i", "r", 5, {"f1", "f2"})
        with self.assertRaises(SystemExit):  # 팩트 집합 상이
            self.rs.check_judgment_provenance(jd, "i", "r", 4, {"f1", "f3"})

    def test_row_identity_gate(self):
        ok = {"round": 0, "agent_id": "a", "model": "gpt-5", "temperature": 0.0,
              "axis": "author_evaluate_fact"}
        self.rs.check_row_identity(ok, "gpt-5", 0.0, "author_evaluate_fact", Path("x"))
        for bad in (dict(ok, model="gpt-4.1"), dict(ok, temperature=1.0),
                    dict(ok, axis="author_evaluate_stance"), {"round": 0, "agent_id": "a"}):
            with self.assertRaises(SystemExit):
                self.rs.check_row_identity(bad, "gpt-5", 0.0, "author_evaluate_fact", Path("x"))
