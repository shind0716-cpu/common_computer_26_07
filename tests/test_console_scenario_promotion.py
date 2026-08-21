"""콘솔 시나리오 승격 관문 — fail-closed 계약 테스트.

실호출은 하지 않는다. 임시 data root의 registry와 재료를 변조해 목록과 실행 입구가
같은 기계 게이트를 다시 검사하는지 확인한다.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from modules import content_hash, paths


def _sha(path: Path) -> str:
    return content_hash.sha256_file(path)


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


class PromotionBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.original_data = paths.DATA
        paths.DATA = self.tmp / "data"
        self.issue_id = "issue_gate_fixture"
        self._write_complete_package()

    def tearDown(self):
        paths.DATA = self.original_data
        shutil.rmtree(self.tmp, ignore_errors=True)

    @property
    def registry_path(self) -> Path:
        return paths.DATA / "scenario_registry.json"

    def _write_complete_package(self, *, state: str = "console_approved",
                                outcome_policy: str = "normative_decision") -> None:
        iid = self.issue_id
        issue = {"schema_ver": "0.2", "created_by": "test", "created_at": "now",
                 "issue_id": iid, "source": "synthetic", "source_meta": {},
                 "title": "gate fixture", "body": "fixture body"}
        facts = {"schema_ver": "0.2", "created_by": "test", "created_at": "now",
                 "issue_id": iid, "extractor": {"name": "test"}, "facts": [
                     {"fact_id": "fact_gate_01", "text": "one", "tags": [],
                      "critical": True, "prior": {"score": 0.0, "probe_model": "stub",
                                                     "probe_prompt_ver": "p1", "probed_at": "now"}},
                     {"fact_id": "fact_gate_02", "text": "two", "tags": [],
                      "critical": True, "prior": {"score": 0.0, "probe_model": "stub",
                                                     "probe_prompt_ver": "p1", "probed_at": "now"}},
                 ]}
        assignment = {"schema_ver": "0.2", "created_by": "test", "created_at": "now",
                      "issue_id": iid, "seed": 42, "agents": [
                          {"agent_id": "agent_1", "perspective": "a", "stance": "none",
                           "assigned_fact_ids": ["fact_gate_01"]},
                          {"agent_id": "agent_2", "perspective": "b", "stance": "none",
                           "assigned_fact_ids": ["fact_gate_02"]},
                      ]}
        _write(paths.issue(iid), issue)
        _write(paths.facts(iid), facts)
        _write(paths.assignment(iid), assignment)

        spec_path = paths.DATA / "detection_specs" / f"{iid}.json"
        calibration_path = paths.DATA / "detection_specs" / f"calibration_{iid}.json"
        spec = {"issue_id": iid, "spec_id": "fixture-spec", "spec_version": "s1",
                "material_sha256": _sha(paths.facts(iid)), "calibration_version": "c1",
                "facts": {"fact_gate_01": {}, "fact_gate_02": {}}}
        calibration = {"issue_id": iid, "version": "c1", "spec_version": "s1", "cases": []}
        _write(spec_path, spec)
        _write(calibration_path, calibration)

        entry = {
            "issue_id": iid, "state": state, "outcome_policy": outcome_policy,
            "material": {"issue_sha256": _sha(paths.issue(iid)),
                         "facts_sha256": _sha(paths.facts(iid)),
                         "assignment_sha256": _sha(paths.assignment(iid))},
            "spec": {"required": True, "version": "s1", "sha256": _sha(spec_path)},
            "calibration": {"required": True, "version": "c1",
                            "sha256": _sha(calibration_path)},
            "prior": {"required": True, "status": "completed"},
            "approved_by": "test-owner", "approved_at": "2026-08-20T00:00:00Z",
        }
        self._write_registry([entry])

    def _write_registry(self, entries: list[dict]) -> None:
        _write(self.registry_path, {"schema_version": "1.0",
                                    "legacy_policy": "deny_unless_explicit_legacy_approved",
                                    "entries": entries})

    def entry(self) -> dict:
        return json.loads(self.registry_path.read_text(encoding="utf-8"))["entries"][0]

    def save_entry(self, entry: dict) -> None:
        self._write_registry([entry])

    def evaluate(self, *, requested_metric: str | None = None):
        from modules import scenario_gate
        return scenario_gate.evaluate(self.issue_id, requested_metric=requested_metric)


class TestMachineGate(PromotionBase):
    def test_registry_without_explicit_legacy_policy_is_blocked(self):
        doc = json.loads(self.registry_path.read_text(encoding="utf-8"))
        doc.pop("legacy_policy")
        _write(self.registry_path, doc)
        result = self.evaluate()
        self.assertFalse(result.allowed)
        self.assertTrue(any("legacy_policy" in reason for reason in result.blocking_reasons))

    def test_registry_missing_is_blocked(self):
        self.registry_path.unlink()
        result = self.evaluate()
        self.assertFalse(result.allowed)
        self.assertTrue(any("registry" in reason for reason in result.blocking_reasons))

    def test_candidate_is_blocked_even_when_all_files_exist(self):
        entry = self.entry()
        entry["state"] = "candidate"
        entry["approved_by"] = entry["approved_at"] = None
        self.save_entry(entry)
        result = self.evaluate()
        self.assertFalse(result.allowed)
        self.assertTrue(any("candidate" in reason for reason in result.blocking_reasons))

    def test_approved_state_requires_all_three_material_files(self):
        paths.assignment(self.issue_id).unlink()
        result = self.evaluate()
        self.assertFalse(result.allowed)
        self.assertTrue(any("assignment" in reason for reason in result.blocking_reasons))

    def test_filename_and_content_issue_id_mismatch_is_blocked(self):
        doc = json.loads(paths.issue(self.issue_id).read_text(encoding="utf-8"))
        doc["issue_id"] = "issue_other"
        _write(paths.issue(self.issue_id), doc)
        result = self.evaluate()
        self.assertFalse(result.allowed)
        self.assertTrue(any("issue_id" in reason for reason in result.blocking_reasons))

    def test_assignment_unknown_and_orphan_fact_ids_are_blocked(self):
        doc = json.loads(paths.assignment(self.issue_id).read_text(encoding="utf-8"))
        doc["agents"][0]["assigned_fact_ids"] = ["fact_unknown"]
        _write(paths.assignment(self.issue_id), doc)
        result = self.evaluate()
        self.assertFalse(result.allowed)
        joined = " ".join(result.blocking_reasons)
        self.assertIn("unknown", joined)
        self.assertIn("orphan", joined)

    def test_spec_material_hash_mismatch_is_blocked(self):
        spec_path = paths.DATA / "detection_specs" / f"{self.issue_id}.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec["material_sha256"] = "0" * 64
        _write(spec_path, spec)
        entry = self.entry()
        entry["spec"]["sha256"] = _sha(spec_path)
        self.save_entry(entry)
        result = self.evaluate()
        self.assertFalse(result.allowed)
        self.assertTrue(any("material" in reason and "hash" in reason for reason in result.blocking_reasons))

    def test_required_calibration_missing_or_version_mismatch_is_blocked(self):
        cal_path = paths.DATA / "detection_specs" / f"calibration_{self.issue_id}.json"
        cal_path.unlink()
        self.assertFalse(self.evaluate().allowed)
        self._write_complete_package()
        cal = json.loads(cal_path.read_text(encoding="utf-8"))
        cal["version"] = "c2"
        _write(cal_path, cal)
        entry = self.entry()
        entry["calibration"]["sha256"] = _sha(cal_path)
        self.save_entry(entry)
        result = self.evaluate()
        self.assertFalse(result.allowed)
        self.assertTrue(any("calibration" in reason and "version" in reason
                            for reason in result.blocking_reasons))

    def test_prior_pending_blocks_execution(self):
        entry = self.entry()
        entry["prior"]["status"] = "pending"
        self.save_entry(entry)
        result = self.evaluate()
        self.assertFalse(result.allowed)
        self.assertTrue(any("prior" in reason for reason in result.blocking_reasons))

    def test_descriptive_scenario_rejects_accuracy_request(self):
        entry = self.entry()
        entry["outcome_policy"] = "descriptive_stance_only"
        self.save_entry(entry)
        result = self.evaluate(requested_metric="accuracy")
        self.assertFalse(result.allowed)
        self.assertTrue(any("accuracy" in reason for reason in result.blocking_reasons))

    def test_explicit_legacy_policy_is_allowed_with_warning_not_implicit(self):
        entry = self.entry()
        entry["state"] = "legacy_approved"
        entry["spec"] = {"required": False, "reason": "pre-semantic legacy material"}
        entry["calibration"] = {"required": False, "reason": "pre-semantic legacy material"}
        entry["prior"] = {"required": False, "status": "exempt",
                          "reason": "historic console fixture only"}
        self.save_entry(entry)
        result = self.evaluate()
        self.assertTrue(result.allowed, result.blocking_reasons)
        self.assertTrue(any("legacy" in warning for warning in result.warnings))

    def test_candidate_can_pass_machine_only_pilot_gate_without_prior_or_signature(self):
        entry = self.entry()
        entry["state"] = "candidate"
        entry["prior"] = {"required": True, "status": "pending"}
        entry["approved_by"] = entry["approved_at"] = None
        self.save_entry(entry)

        from modules import scenario_gate
        result = scenario_gate.evaluate_pilot(
            self.issue_id, expected_calls=12, max_calls=30)

        self.assertTrue(result.allowed, result.blocking_reasons)
        self.assertEqual(result.tier, "pilot_unvetted")
        self.assertEqual(result.call_limit, 30)
        self.assertEqual(set(result.material_hashes), {"issue", "facts", "assignment"})
        self.assertIn("default aggregate excluded", " ".join(result.warnings))

    def test_pilot_gate_requires_explicit_cap_and_blocks_over_30_or_accuracy(self):
        from modules import scenario_gate

        for expected, cap, metric in ((12, None, None), (31, 31, None), (12, 30, "accuracy")):
            with self.subTest(expected=expected, cap=cap, metric=metric):
                result = scenario_gate.evaluate_pilot(
                    self.issue_id, expected_calls=expected, max_calls=cap,
                    requested_metric=metric)
                self.assertFalse(result.allowed)

    def test_unregistered_complete_material_is_discovered_but_invalid_material_cannot_execute(self):
        self._write_registry([])
        from modules import scenario_gate

        discovered = {r.issue_id: r for r in scenario_gate.pilot_results()}
        self.assertIn(self.issue_id, discovered)
        self.assertTrue(discovered[self.issue_id].allowed, discovered[self.issue_id].blocking_reasons)

        paths.assignment(self.issue_id).unlink()
        blocked = scenario_gate.evaluate_pilot(self.issue_id, expected_calls=12, max_calls=30)
        self.assertFalse(blocked.allowed)
        self.assertTrue(any("assignment" in reason for reason in blocked.blocking_reasons))

    def test_historical_v1_no_execution_exemption_remains_pilot_blocked(self):
        entry = self.entry()
        entry["state"] = "candidate"
        entry["spec"] = {"required": False,
                         "reason": "historical v1 development material; no new execution approval"}
        entry["calibration"] = {"required": False,
                                "reason": "historical v1 development material; v2 package required"}
        entry["prior"] = {"required": False, "status": "exempt", "reason": "historical"}
        entry["approved_by"] = entry["approved_at"] = None
        self.save_entry(entry)

        from modules import scenario_gate
        result = scenario_gate.evaluate_pilot(self.issue_id, expected_calls=12, max_calls=30)
        self.assertFalse(result.allowed)
        self.assertTrue(any("historical v1" in reason for reason in result.blocking_reasons))


class TestConsoleIntegration(PromotionBase):
    def setUp(self):
        super().setUp()
        from tools.console import app as console_app
        self.mod = console_app
        self.client = TestClient(console_app.app)
        # config 도 임시 폴더로 — 종전엔 CONFIG_DIR(리포의 configs/console)에 그대로 써서
        # 픽스처 config(pilot_fixture.yaml 등)가 실제 리포에 잔재로 남았다(2026-08-20 실측).
        self.original_config_dir = console_app.CONFIG_DIR
        console_app.CONFIG_DIR = self.tmp / "configs"
        self.addCleanup(setattr, console_app, "CONFIG_DIR", self.original_config_dir)

    def _write_pilot_source(self, run_id: str, *, with_notes: bool = False) -> None:
        rows = [{
            "event": "run_meta", "run_id": run_id, "ts": "now",
            "issue_id": self.issue_id, "condition": "pilot/fixture",
            "promotion_tier": "pilot_unvetted",
            "aggregate_eligible": False, "report_eligible": False,
            "config_ref": {"name": "fixture.yaml", "sha256": "x"},
            "settings": {"window": "rolling", "memory": "note" if with_notes else "none",
                         "rounds": 1, "structure": "full", "stance": "none",
                         "overlap_k": 1, "ledger_mode": "off", "seed": 42},
        }]
        for i, aid in enumerate(("agent_1", "agent_2"), 1):
            rows.append({"event": "utterance", "run_id": run_id, "ts": "now",
                         "round": 1, "agent_id": aid, "response_text": f"response {i}"})
            if with_notes:
                rows.append({"event": "note_update", "run_id": run_id, "ts": "now",
                             "round": 1, "agent_id": aid, "note_text": f"note {i}",
                             "origin": "model", "source": "utterance"})
        path = paths.debate(self.issue_id, run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                        encoding="utf-8")

    def test_meta_lists_only_gate_approved_issue_and_reports_blocked_registry_rows(self):
        candidate = dict(self.entry())
        candidate["issue_id"] = "issue_candidate"
        candidate["state"] = "candidate"
        candidate["approved_by"] = candidate["approved_at"] = None
        self._write_registry([self.entry(), candidate])

        meta = self.client.get("/api/meta").json()
        self.assertEqual(meta["issues"], [self.issue_id])
        self.assertEqual([row["issue_id"] for row in meta["issue_rows"]], [self.issue_id])
        self.assertEqual(meta["issue_rows"][0]["promotion_state"], "console_approved")
        blocked = next(row for row in meta["scenario_gate_rows"]
                       if row["issue_id"] == "issue_candidate")
        self.assertFalse(blocked["allowed"])
        self.assertTrue(blocked["blocking_reasons"])

    def test_run_rechecks_hash_before_subprocess_or_llm_call(self):
        issue = json.loads(paths.issue(self.issue_id).read_text(encoding="utf-8"))
        issue["body"] += " tampered"
        _write(paths.issue(self.issue_id), issue)

        with mock.patch.object(self.mod.subprocess, "Popen") as popen:
            response = self.client.post("/api/run", json={
                "issue_id": self.issue_id, "run_id": "must_not_run"})
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("gate", response.json()["detail"])
        popen.assert_not_called()
        self.assertFalse(paths.debate(self.issue_id, "must_not_run").exists())

    def test_descriptive_accuracy_request_is_rejected_by_run_route(self):
        entry = self.entry()
        entry["outcome_policy"] = "descriptive_stance_only"
        self.save_entry(entry)
        with mock.patch.object(self.mod.subprocess, "Popen") as popen:
            response = self.client.post("/api/run", json={
                "issue_id": self.issue_id, "run_id": "no_accuracy",
                "outcome_metric": "accuracy"})
        self.assertEqual(response.status_code, 400, response.text)
        popen.assert_not_called()

    def test_pilot_run_uses_existing_modules_pipeline_with_budget_and_durable_labels(self):
        entry = self.entry()
        entry["state"] = "candidate"
        entry["prior"] = {"required": True, "status": "pending"}
        entry["approved_by"] = entry["approved_at"] = None
        self.save_entry(entry)

        with mock.patch.object(self.mod.subprocess, "Popen") as popen, \
                mock.patch.object(self.mod.threading, "Thread"):
            response = self.client.post("/api/run", json={
                "issue_id": self.issue_id,
                "run_id": "pilot_fixture",
                "condition": "coop",
                "promotion_tier": "pilot_unvetted",
                "max_llm_calls": 30,
                "rounds": 3,
            })
        self.assertEqual(response.status_code, 200, response.text)
        cmd = popen.call_args.args[0]
        self.assertIn("modules.debate_engine", cmd)
        cfg_path = paths.ROOT / response.json()["config"]
        cfg = cfg_path.read_text(encoding="utf-8")
        self.assertIn("promotion_tier: pilot_unvetted", cfg)
        self.assertIn("condition: pilot/coop", cfg)
        self.assertIn("aggregate_eligible: false", cfg)
        self.assertIn("report_eligible: false", cfg)

    def test_pilot_run_without_cap_or_over_30_never_starts_pipeline(self):
        entry = self.entry()
        entry["state"] = "candidate"
        entry["prior"] = {"required": True, "status": "pending"}
        entry["approved_by"] = entry["approved_at"] = None
        self.save_entry(entry)

        requests = [
            {"issue_id": self.issue_id, "run_id": "pilot_no_cap",
             "promotion_tier": "pilot_unvetted"},
            {"issue_id": self.issue_id, "run_id": "pilot_over",
             "promotion_tier": "pilot_unvetted", "max_llm_calls": 30,
             "rounds": 4, "ledger_mode": "v0"},
        ]
        for payload in requests:
            with self.subTest(run_id=payload["run_id"]), \
                    mock.patch.object(self.mod.subprocess, "Popen") as popen:
                response = self.client.post("/api/run", json=payload)
                self.assertEqual(response.status_code, 400, response.text)
                popen.assert_not_called()

    def test_pilot_judge_import_pipeline_requires_cap_and_persists_tier_config(self):
        self._write_pilot_source("pilot_judge")
        entry = self.entry()
        entry["state"] = "candidate"
        entry["prior"] = {"required": True, "status": "pending"}
        entry["approved_by"] = entry["approved_at"] = None
        self.save_entry(entry)

        with mock.patch.object(self.mod.llm, "preflight") as preflight, \
                mock.patch.object(self.mod.subprocess, "Popen") as popen:
            blocked = self.client.post("/api/judge/run", json={
                "issue_id": self.issue_id, "run_id": "pilot_judge"})
        self.assertEqual(blocked.status_code, 400, blocked.text)
        preflight.assert_not_called()
        popen.assert_not_called()

        with mock.patch.object(self.mod.llm, "preflight"), \
                mock.patch.object(self.mod.subprocess, "Popen") as popen, \
                mock.patch.object(self.mod.threading, "Thread"):
            allowed = self.client.post("/api/judge/run", json={
                "issue_id": self.issue_id, "run_id": "pilot_judge",
                "max_llm_calls": 30})
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertIn("modules.judge", popen.call_args.args[0])
        cfg = (paths.ROOT / allowed.json()["config"]).read_text(encoding="utf-8")
        self.assertIn("promotion_tier: pilot_unvetted", cfg)
        self.assertIn("aggregate_eligible: false", cfg)

    def test_pilot_intervention_requires_cap_before_preflight_and_inherits_labels(self):
        self._write_pilot_source("pilot_intervene", with_notes=True)
        entry = self.entry()
        entry["state"] = "candidate"
        entry["prior"] = {"required": True, "status": "pending"}
        entry["approved_by"] = entry["approved_at"] = None
        self.save_entry(entry)
        payload = {"issue_id": self.issue_id, "run_id": "pilot_intervene",
                   "new_run_id": "pilot_intervene_child", "notes": {}}

        with mock.patch.object(self.mod.llm, "preflight") as preflight, \
                mock.patch.object(self.mod.llm, "obtain_response") as obtain:
            blocked = self.client.post("/api/intervene", json=payload)
        self.assertEqual(blocked.status_code, 400, blocked.text)
        preflight.assert_not_called()
        obtain.assert_not_called()

        payload["max_llm_calls"] = 30
        with mock.patch.object(self.mod.llm, "preflight"), \
                mock.patch.object(self.mod.llm, "obtain_response", return_value="ok"):
            allowed = self.client.post("/api/intervene", json=payload)
        self.assertEqual(allowed.status_code, 200, allowed.text)
        rows = [json.loads(line) for line in
                paths.debate(self.issue_id, "pilot_intervene_child").read_text(
                    encoding="utf-8").splitlines() if line]
        self.assertEqual(rows[0]["promotion_tier"], "pilot_unvetted")
        self.assertFalse(rows[0]["aggregate_eligible"])
        self.assertFalse(rows[0]["report_eligible"])


class TestRepositoryRegistryIntegration(unittest.TestCase):
    """실제 v2 package는 의미 패키지·prior까지 동기화됐지만 사람 승인(state) 전에는 막힌다."""

    def test_award_v2_registry_matches_package_but_remains_non_executable(self):
        from modules import scenario_gate

        result = scenario_gate.evaluate("issue_award_v2")
        self.assertFalse(result.allowed)
        self.assertEqual(result.state, "candidate")
        joined = " | ".join(result.blocking_reasons)
        self.assertIn("promotion state not executable: candidate", joined)
        # 2026-08-21 prior 프로브 완료(known 0/12, 48콜) — 이제 prior 는 막지 않는다.
        self.assertNotIn("prior not completed", joined)
        self.assertNotIn("facts hash mismatch", joined)
        for stale_error in (
            "spec hash mismatch", "spec version mismatch",
            "calibration hash mismatch", "calibration version mismatch",
            "spec/calibration version mismatch", "spec material hash mismatch",
        ):
            self.assertNotIn(stale_error, joined)

    def test_polar_v2_registry_matches_package_but_remains_non_executable(self):
        from modules import scenario_gate

        result = scenario_gate.evaluate("issue_polar_v2", requested_metric="accuracy")
        self.assertFalse(result.allowed)
        self.assertEqual(result.state, "candidate")
        joined = " | ".join(result.blocking_reasons)
        self.assertIn("promotion state not executable: candidate", joined)
        # 2026-08-21 prior 프로브 완료(known 0/12, 48콜) — 이제 prior 는 막지 않는다.
        self.assertNotIn("prior not completed", joined)
        self.assertNotIn("facts hash mismatch", joined)
        self.assertIn("accuracy forbidden for descriptive_stance_only scenario", joined)
        for stale_error in (
            "spec hash mismatch", "spec version mismatch",
            "calibration hash mismatch", "calibration version mismatch",
            "spec/calibration version mismatch", "spec material hash mismatch",
        ):
            self.assertNotIn(stale_error, joined)

    def test_exile_v2_registry_matches_package_but_remains_non_executable(self):
        from modules import scenario_gate

        result = scenario_gate.evaluate("issue_exile_v2", requested_metric="accuracy")
        self.assertFalse(result.allowed)
        self.assertEqual(result.state, "candidate")
        joined = " | ".join(result.blocking_reasons)
        self.assertIn("promotion state not executable: candidate", joined)
        # 2026-08-21 prior 프로브 완료(known 0/12, 48콜) — 이제 prior 는 막지 않는다.
        self.assertNotIn("prior not completed", joined)
        self.assertNotIn("facts hash mismatch", joined)
        self.assertIn("accuracy forbidden for descriptive_stance_only scenario", joined)
        for stale_error in (
            "spec hash mismatch", "spec version mismatch",
            "calibration hash mismatch", "calibration version mismatch",
            "spec/calibration version mismatch", "spec material hash mismatch",
        ):
            self.assertNotIn(stale_error, joined)


if __name__ == "__main__":
    unittest.main()
