"""콘솔 시나리오 승격 관문 — fail-closed 계약 테스트.

실호출은 하지 않는다. 임시 data root의 registry와 재료를 변조해 목록과 실행 입구가
같은 기계 게이트를 다시 검사하는지 확인한다.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from modules import paths


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


class TestConsoleIntegration(PromotionBase):
    def setUp(self):
        super().setUp()
        from tools.console import app as console_app
        self.mod = console_app
        self.client = TestClient(console_app.app)

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


if __name__ == "__main__":
    unittest.main()
