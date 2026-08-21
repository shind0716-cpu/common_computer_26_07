"""동일 parent r0에서 A/B/C 사후 평가를 분기하는 generic runner 계약."""
from __future__ import annotations

import hashlib

from modules import content_hash
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from modules.abc_same_parent_runner import (
    BundleAssemblyError,
    CallBudgetExceeded,
    RunInputs,
    run,
)


class SameParentDryRunEndToEndTests(unittest.TestCase):
    def test_dry_run_uses_identical_parent_and_only_posthoc_bundles_differ(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            parent_bytes = b"same immutable parent r0\x00bytes"
            parent = root / "parent-r0.bin"
            parent.write_bytes(parent_bytes)

            issue = root / "issue.json"
            facts = root / "facts.json"
            assignment = root / "assignment.json"
            spec = root / "spec.json"
            calibration = root / "calibration.json"
            protocol = root / "common-protocol.txt"
            issue.write_text(json.dumps({"issue_id": "issue_fixture", "schema_ver": "0.3"}), encoding="utf-8")
            facts.write_text(json.dumps({"issue_id": "issue_fixture", "schema_ver": "0.3", "facts": []}), encoding="utf-8")
            assignment.write_text(json.dumps({"issue_id": "issue_fixture", "schema_ver": "0.3", "seed": 7}), encoding="utf-8")
            facts_hash = content_hash.sha256_file(facts)
            spec.write_text(json.dumps({"issue_id": "issue_fixture", "spec_version": "spec-1", "material_sha256": facts_hash, "lexical_probes": ["judge-only-anchor"]}), encoding="utf-8")
            calibration.write_text(json.dumps({"issue_id": "issue_fixture", "version": "cal-1", "spec_version": "spec-1", "cases": []}), encoding="utf-8")
            protocol.write_text("common judge protocol v1", encoding="utf-8")

            evaluator_calls = []
            result = run(
                RunInputs(
                    issue_id="issue_fixture",
                    parent_r0=parent,
                    issue=issue,
                    facts=facts,
                    assignment=assignment,
                    detection_spec=spec,
                    calibration=calibration,
                    common_protocol=protocol,
                    common_protocol_version="common-1",
                    output_dir=root / "out",
                    model_config={"model": "MODEL_PLACEHOLDER", "temperature": None},
                ),
                dry=True,
                evaluator=lambda *_: evaluator_calls.append(True),
                max_calls=0,
            )

            self.assertEqual([], evaluator_calls)
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(hashlib.sha256(parent_bytes).hexdigest(), manifest["parent_r0_sha256"])
            self.assertEqual(len(parent_bytes), manifest["parent_r0_byte_length"])
            self.assertEqual({"A": 0, "B": 0, "C": 0}, manifest["expected_calls"]["per_arm"])
            self.assertEqual(0, manifest["expected_calls"]["total"])
            self.assertEqual(["canonical_material", "common_protocol"],
                             manifest["conditions"]["A"]["components"])
            self.assertEqual(["canonical_material", "common_protocol", "detection_spec"],
                             manifest["conditions"]["B"]["components"])
            self.assertEqual(
                ["canonical_material", "common_protocol", "detection_spec",
                 "independent_calibration"],
                manifest["conditions"]["C"]["components"],
            )
            self.assertEqual(3, len(set(manifest["condition_bundle_hashes"].values())))

            records = [json.loads(line) for line in result.records_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["A", "B", "C"], [record["arm"] for record in records])
            self.assertTrue(all(record["parent_r0_sha256"] == manifest["parent_r0_sha256"] for record in records))
            self.assertTrue(all(record["parent_r0_byte_length"] == len(parent_bytes) for record in records))
            self.assertTrue(all(record["status"] == "dry_completed" and record["completed"] for record in records))
            self.assertTrue(all(record["role"] == "posthoc_judge" for record in records))

    def test_resume_skips_completed_coordinates_without_duplicate_records(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files = self._fixture(root)
            first = run(files, dry=True, max_calls=0)
            manifest_before = first.manifest_path.read_bytes()
            second = run(files, dry=True, max_calls=0)

            records = second.records_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(3, len(records))
            self.assertEqual(manifest_before, second.manifest_path.read_bytes())

    def test_call_budget_is_checked_for_all_arms_before_first_evaluator_call(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))
            calls = []
            with self.assertRaises(CallBudgetExceeded):
                run(inputs, dry=False, evaluator=lambda *_: calls.append(True), max_calls=2)
            self.assertEqual([], calls)
            manifest = json.loads((inputs.output_dir / "coordinate_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual({"A": 1, "B": 1, "C": 1}, manifest["expected_calls"]["per_arm"])
            self.assertEqual(3, manifest["expected_calls"]["total"])

    def test_injected_evaluator_gets_same_parent_and_unknown_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))
            seen = []

            def fake(parent_bytes, bundle, coordinate):
                seen.append((parent_bytes, bundle, coordinate))
                return '{"decision":"unknown","evidence":null}'

            result = run(inputs, dry=False, evaluator=fake, max_calls=3)

            self.assertEqual(3, len(seen))
            self.assertEqual(1, len({parent for parent, _, _ in seen}))
            self.assertEqual(["A", "B", "C"], [coordinate["arm"] for _, _, coordinate in seen])
            self.assertEqual(
                [
                    {"role", "canonical_material", "common_protocol"},
                    {"role", "canonical_material", "common_protocol", "detection_spec"},
                    {"role", "canonical_material", "common_protocol", "detection_spec",
                     "independent_calibration"},
                ],
                [set(bundle) for _, bundle, _ in seen],
            )
            records = [json.loads(line) for line in result.records_path.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all(record["status"] == "completed" and record["completed"] for record in records))
            self.assertTrue(all(record["parsed_result"]["decision"] == "unknown" for record in records))
            self.assertTrue(all(record["raw_response"] == '{"decision":"unknown","evidence":null}' for record in records))

    def test_parse_and_evaluator_errors_are_preserved_and_resume_only_retries_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))

            def faulty(_parent, _bundle, coordinate):
                if coordinate["arm"] == "A":
                    return "not-json verbatim"
                if coordinate["arm"] == "B":
                    raise OSError("synthetic evaluator outage")
                return '{"decision":"unknown"}'

            first = run(inputs, dry=False, evaluator=faulty, max_calls=3)
            first_records = [json.loads(line) for line in first.records_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["parse_error", "evaluator_error", "completed"], [r["status"] for r in first_records])
            self.assertEqual("not-json verbatim", first_records[0]["raw_response"])
            self.assertIn("JSONDecodeError", first_records[0]["error"])
            self.assertIn("synthetic evaluator outage", first_records[1]["error"])
            self.assertTrue(all(not r["completed"] for r in first_records[:2]))

            retried = []

            def recovered(_parent, _bundle, coordinate):
                retried.append(coordinate["arm"])
                return '{"decision":"unknown"}'

            second = run(inputs, dry=False, evaluator=recovered, max_calls=2)
            all_records = [json.loads(line) for line in second.records_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["A", "B"], retried)
            self.assertEqual(5, len(all_records))
            self.assertEqual(1, sum(r["arm"] == "C" for r in all_records))

    def test_cli_dry_executes_all_coordinates_with_zero_calls(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))
            command = [
                sys.executable, "-m", "modules.abc_same_parent_runner", "--dry",
                "--issue-id", inputs.issue_id,
                "--parent-r0", str(inputs.parent_r0),
                "--issue", str(inputs.issue), "--facts", str(inputs.facts),
                "--assignment", str(inputs.assignment),
                "--detection-spec", str(inputs.detection_spec),
                "--calibration", str(inputs.calibration),
                "--common-protocol", str(inputs.common_protocol),
                "--common-protocol-version", inputs.common_protocol_version,
                "--output-dir", str(inputs.output_dir),
                "--model-config-json", json.dumps(inputs.model_config),
                "--max-calls", "0",
            ]
            completed = subprocess.run(command, cwd=Path(__file__).parents[1], text=True,
                                       capture_output=True, encoding="utf-8", check=False)
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertIn('"total": 0', completed.stdout)
            self.assertEqual(3, len((inputs.output_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()))

    def test_bundle_identity_mismatch_fails_closed_before_output_or_evaluator(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))
            inputs.detection_spec.write_text(
                json.dumps({"issue_id": "wrong_issue", "spec_version": "spec-1", "facts": {}}),
                encoding="utf-8",
            )
            calls = []
            with self.assertRaisesRegex(BundleAssemblyError, "detection_spec issue_id mismatch"):
                run(inputs, dry=False, evaluator=lambda *_: calls.append(True), max_calls=3)
            self.assertEqual([], calls)
            self.assertFalse(inputs.output_dir.exists())

    def test_spec_material_and_calibration_spec_cross_links_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))
            spec_doc = json.loads(inputs.detection_spec.read_text(encoding="utf-8"))
            spec_doc["material_sha256"] = "0" * 64
            inputs.detection_spec.write_text(json.dumps(spec_doc), encoding="utf-8")
            with self.assertRaisesRegex(BundleAssemblyError, "material_sha256 mismatch"):
                run(inputs, dry=True, max_calls=0)
            self.assertFalse(inputs.output_dir.exists())

        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))
            calibration_doc = json.loads(inputs.calibration.read_text(encoding="utf-8"))
            calibration_doc["spec_version"] = "wrong-spec"
            inputs.calibration.write_text(json.dumps(calibration_doc), encoding="utf-8")
            with self.assertRaisesRegex(BundleAssemblyError, "calibration spec_version mismatch"):
                run(inputs, dry=True, max_calls=0)
            self.assertFalse(inputs.output_dir.exists())

    def test_parent_mutation_inside_final_evaluator_fails_before_completion_record(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))

            def mutating_evaluator(_parent, _bundle, coordinate):
                if coordinate["arm"] == "C":
                    inputs.parent_r0.write_bytes(b"mutated after final preflight")
                return '{"decision":"unknown"}'

            with self.assertRaisesRegex(RuntimeError, "parent r0 changed during arm C"):
                run(inputs, dry=False, evaluator=mutating_evaluator, max_calls=3)
            records = [json.loads(line) for line in
                       (inputs.output_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["A", "B"], [record["arm"] for record in records])
            self.assertTrue(all(record["completed"] for record in records))

    def test_all_arms_receive_same_canonical_material_for_posthoc_judging(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))
            seen = []

            def fake(_parent, bundle, coordinate):
                seen.append((coordinate["arm"], bundle["canonical_material"]))
                return '{"decision":"unknown"}'

            run(inputs, dry=False, evaluator=fake, max_calls=3)
            self.assertEqual(["A", "B", "C"], [arm for arm, _ in seen])
            material_bytes = [json.dumps(material, sort_keys=True).encode("utf-8")
                              for _, material in seen]
            self.assertEqual(1, len(set(material_bytes)))
            self.assertEqual(inputs.issue_id, seen[0][1]["issue"]["issue_id"])
            self.assertIn("facts", seen[0][1]["facts"])

    def test_dry_writes_three_inspectable_posthoc_bundle_files(self):
        with tempfile.TemporaryDirectory() as td:
            inputs = self._fixture(Path(td))
            result = run(inputs, dry=True, max_calls=0)
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            bundle_docs = {
                arm: json.loads((inputs.output_dir / manifest["conditions"][arm]["bundle_file"]).read_text(encoding="utf-8"))
                for arm in ("A", "B", "C")
            }
            self.assertNotIn("detection_spec", bundle_docs["A"])
            self.assertIn("detection_spec", bundle_docs["B"])
            self.assertNotIn("independent_calibration", bundle_docs["B"])
            self.assertIn("independent_calibration", bundle_docs["C"])
            self.assertTrue(all(doc["role"] == "posthoc_judge" for doc in bundle_docs.values()))

    @staticmethod
    def _fixture(root: Path) -> RunInputs:
        parent = root / "parent-r0.bin"
        parent.write_bytes(b"same immutable parent")
        docs = {
            "issue": {"issue_id": "issue_fixture", "schema_ver": "0.3"},
            "facts": {"issue_id": "issue_fixture", "schema_ver": "0.3", "facts": []},
            "assignment": {"issue_id": "issue_fixture", "schema_ver": "0.3", "seed": 7},
            "spec": {"issue_id": "issue_fixture", "spec_version": "spec-1", "facts": {}},
            "calibration": {"issue_id": "issue_fixture", "version": "cal-1",
                            "spec_version": "spec-1", "cases": []},
        }
        paths = {}
        for name, doc in docs.items():
            paths[name] = root / f"{name}.json"
            paths[name].write_text(json.dumps(doc), encoding="utf-8")
        spec_doc = json.loads(paths["spec"].read_text(encoding="utf-8"))
        spec_doc["material_sha256"] = content_hash.sha256_file(paths["facts"])
        paths["spec"].write_text(json.dumps(spec_doc), encoding="utf-8")
        protocol = root / "common.txt"
        protocol.write_text("common protocol", encoding="utf-8")
        return RunInputs(
            issue_id="issue_fixture", parent_r0=parent,
            issue=paths["issue"], facts=paths["facts"], assignment=paths["assignment"],
            detection_spec=paths["spec"], calibration=paths["calibration"],
            common_protocol=protocol, common_protocol_version="common-1",
            output_dir=root / "out", model_config={"model": "MODEL_PLACEHOLDER"},
        )


class ActualV2PackagesDryIntegrationTests(unittest.TestCase):
    def _assert_package(self, issue_id: str):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            parent = tmp / "synthetic-parent-r0.txt"
            parent.write_text("synthetic zero-call parent; not observed output", encoding="utf-8")
            inputs = RunInputs(
                issue_id=issue_id,
                parent_r0=parent,
                issue=repo / f"data/issues/{issue_id}.json",
                facts=repo / f"data/facts/facts_{issue_id}.json",
                assignment=repo / f"data/assignments/assignment_{issue_id}.json",
                detection_spec=repo / f"data/detection_specs/{issue_id}.json",
                calibration=repo / f"data/detection_specs/calibration_{issue_id}.json",
                common_protocol=repo / "data/judge_protocols/common_semantic_judge_v1.md",
                common_protocol_version="common-semantic-judge-v1",
                output_dir=tmp / "out",
                model_config={"model": "MODEL_PLACEHOLDER", "config": "CONFIG_PLACEHOLDER"},
            )
            calls = []
            result = run(inputs, dry=True, evaluator=lambda *_: calls.append(True), max_calls=0)
            self.assertEqual([], calls)
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(0, manifest["expected_calls"]["total"])
            self.assertEqual(issue_id, manifest["issue_id"])
            self.assertEqual("cal-0.2", manifest["calibration"]["version"])
            self.assertEqual("sha256(raw_bytes)", manifest["parent_hash_policy"])
            self.assertEqual(3, len(result.records_path.read_text(encoding="utf-8").splitlines()))

    def test_actual_polar_package_assembles_all_three_arms_with_zero_calls(self):
        self._assert_package("issue_polar_v2")

    def test_actual_exile_package_assembles_all_three_arms_with_zero_calls(self):
        self._assert_package("issue_exile_v2")


if __name__ == "__main__":
    unittest.main()
