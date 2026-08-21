"""동일 parent r0를 A/B/C 사후 judge bundle로 분기하는 generic runner.

이 모듈은 생성 프롬프트를 만들거나 생성 에이전트를 호출하지 않는다. 이미 동결된
parent r0 bytes를 사후 판정기에 전달하며, 조건 차이는 judge/coder bundle에만 둔다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from modules import content_hash


class BundleAssemblyError(RuntimeError):
    """사후 판정 bundle의 identity/version/내용 조립 실패."""


class CallBudgetExceeded(RuntimeError):
    """예상 호출 수가 명시적 상한을 넘어서 실행 전에 차단됨."""


@dataclass(frozen=True)
class RunInputs:
    issue_id: str
    parent_r0: Path
    issue: Path
    facts: Path
    assignment: Path
    detection_spec: Path
    calibration: Path
    common_protocol: Path
    common_protocol_version: str
    output_dir: Path
    model_config: dict[str, Any]


@dataclass(frozen=True)
class RunResult:
    manifest_path: Path
    records_path: Path


def _sha256(data: bytes) -> str:
    """Parent r0와 canonical JSON coordinate의 exact-byte 지문."""
    return hashlib.sha256(data).hexdigest()


def _artifact_sha256(data: bytes) -> str:
    """저장소 text artifact의 LF-canonical 지문."""
    return content_hash.sha256_bytes(data)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value, raw


def _version(doc: dict[str, Any]) -> Any:
    for key in ("spec_version", "version", "schema_ver"):
        if key in doc:
            return doc[key]
    return None


def _append_record(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as fp:
        fp.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        fp.flush()
        os.fsync(fp.fileno())


def run(
    inputs: RunInputs,
    *,
    dry: bool,
    evaluator: Callable[..., Any] | None = None,
    max_calls: int = 0,
) -> RunResult:
    """A/B/C coordinate를 조립하고 실행한다."""
    parent = inputs.parent_r0.read_bytes()
    parent_hash = _sha256(parent)
    material_docs: dict[str, dict[str, Any]] = {}
    material_raw: dict[str, bytes] = {}
    for name, path in (("issue", inputs.issue), ("facts", inputs.facts), ("assignment", inputs.assignment)):
        material_docs[name], material_raw[name] = _read_json(path)
    spec_doc, spec_raw = _read_json(inputs.detection_spec)
    calibration_doc, calibration_raw = _read_json(inputs.calibration)
    protocol_raw = inputs.common_protocol.read_bytes()
    protocol_canonical = content_hash.normalize(protocol_raw)
    identity_docs = {**material_docs, "detection_spec": spec_doc, "calibration": calibration_doc}
    for label, doc in identity_docs.items():
        if doc.get("issue_id") != inputs.issue_id:
            raise BundleAssemblyError(
                f"{label} issue_id mismatch: {doc.get('issue_id')!r} != {inputs.issue_id!r}")
    if _version(spec_doc) in (None, ""):
        raise BundleAssemblyError("detection_spec version is required")
    calibration_version = calibration_doc.get("version")
    if calibration_version in (None, ""):
        raise BundleAssemblyError("calibration version is required")
    facts_hash = _artifact_sha256(material_raw["facts"])
    if not spec_doc.get("material_sha256"):
        raise BundleAssemblyError("detection_spec material_sha256 is required")
    if spec_doc["material_sha256"] != facts_hash:
        raise BundleAssemblyError(
            "detection_spec material_sha256 mismatch: "
            f"{spec_doc['material_sha256']} != {facts_hash}")
    spec_version = _version(spec_doc)
    calibration_spec_version = calibration_doc.get("spec_version")
    if not calibration_spec_version:
        raise BundleAssemblyError("calibration spec_version is required")
    if calibration_spec_version != spec_version:
        raise BundleAssemblyError(
            "calibration spec_version mismatch: "
            f"{calibration_spec_version!r} != {spec_version!r}")
    if not inputs.common_protocol_version or not protocol_canonical:
        raise BundleAssemblyError("common protocol bytes and version are required")

    canonical_material = {
        "issue": material_docs["issue"],
        "facts": material_docs["facts"],
    }
    bundles = {
        "A": {"role": "posthoc_judge", "canonical_material": canonical_material,
              "common_protocol": protocol_canonical.decode("utf-8")},
        "B": {
            "role": "posthoc_judge",
            "canonical_material": canonical_material,
            "common_protocol": protocol_canonical.decode("utf-8"),
            "detection_spec": spec_doc,
        },
        "C": {
            "role": "posthoc_judge",
            "canonical_material": canonical_material,
            "common_protocol": protocol_canonical.decode("utf-8"),
            "detection_spec": spec_doc,
            "independent_calibration": calibration_doc,
        },
    }
    bundle_hashes = {arm: _sha256(_json_bytes(bundle)) for arm, bundle in bundles.items()}
    components = {
        "A": ["canonical_material", "common_protocol"],
        "B": ["canonical_material", "common_protocol", "detection_spec"],
        "C": ["canonical_material", "common_protocol", "detection_spec",
              "independent_calibration"],
    }
    manifest = {
        "schema": "abc_same_parent_coordinate_manifest_v1",
        "issue_id": inputs.issue_id,
        "parent_r0_sha256": parent_hash,
        "parent_r0_byte_length": len(parent),
        "parent_hash_policy": "sha256(raw_bytes)",
        "artifact_hash_policy": "sha256(normalize_crlf_cr_to_lf)",
        "material": {
            name: {"sha256": _artifact_sha256(material_raw[name]),
                   "version": _version(material_docs[name])}
            for name in ("issue", "facts", "assignment")
        },
        "detection_spec": {"sha256": _artifact_sha256(spec_raw),
                           "version": _version(spec_doc)},
        "calibration": {"sha256": _artifact_sha256(calibration_raw),
                        "version": calibration_version},
        "common_protocol": {"sha256": _artifact_sha256(protocol_raw),
                            "version": inputs.common_protocol_version},
        "conditions": {
            arm: {"components": components[arm], "bundle_file": f"bundle_{arm}.json"}
            for arm in ("A", "B", "C")
        },
        "condition_bundle_hashes": bundle_hashes,
        "model_config": inputs.model_config,
        "expected_calls": {
            "per_arm": {"A": 0 if dry else 1, "B": 0 if dry else 1, "C": 0 if dry else 1},
            "total": 0 if dry else 3,
        },
    }

    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    for arm, bundle in bundles.items():
        bundle_path = inputs.output_dir / manifest["conditions"][arm]["bundle_file"]
        bundle_bytes = _json_bytes(bundle) + b"\n"
        if bundle_path.exists() and bundle_path.read_bytes() != bundle_bytes:
            raise RuntimeError(f"existing bundle differs for arm {arm}; refuse to mix runs")
        if not bundle_path.exists():
            bundle_path.write_bytes(bundle_bytes)
    manifest_path = inputs.output_dir / "coordinate_manifest.json"
    records_path = inputs.output_dir / "records.jsonl"
    manifest_bytes = _json_bytes(manifest) + b"\n"
    if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
        raise RuntimeError("existing coordinate manifest differs; refuse to mix runs")
    if not manifest_path.exists():
        manifest_path.write_bytes(manifest_bytes)
    if not dry and evaluator is None:
        raise ValueError("non-dry run requires an injected posthoc evaluator")

    completed: set[str] = set()
    if records_path.exists():
        for line_number, line in enumerate(records_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                prior = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid checkpoint JSONL line {line_number}: {exc}") from exc
            if prior.get("completed") is True:
                completed.add(prior["coordinate_id"])

    coordinate_ids = {
        arm: _sha256(_json_bytes({"issue_id": inputs.issue_id, "arm": arm,
                                  "parent": parent_hash, "bundle": bundle_hashes[arm]}))
        for arm in ("A", "B", "C")
    }
    pending_calls = 0 if dry else sum(cid not in completed for cid in coordinate_ids.values())
    if pending_calls > max_calls:
        raise CallBudgetExceeded(f"expected {pending_calls} pending calls exceeds max_calls={max_calls}")

    for arm in ("A", "B", "C"):
        coordinate_id = coordinate_ids[arm]
        if coordinate_id in completed:
            continue
        current_parent = inputs.parent_r0.read_bytes()
        if _sha256(current_parent) != parent_hash or len(current_parent) != len(parent):
            raise RuntimeError(f"parent r0 changed before arm {arm}; fail closed")
        record = {
            "schema": "abc_same_parent_record_v1",
            "issue_id": inputs.issue_id,
            "arm": arm,
            "role": "posthoc_judge",
            "coordinate_id": coordinate_id,
            "parent_r0_sha256": parent_hash,
            "parent_r0_byte_length": len(parent),
            "condition_bundle_sha256": bundle_hashes[arm],
        }
        if dry:
            record.update({
                "status": "dry_completed", "completed": True,
                "raw_response": None, "parsed_result": None,
            })
        else:
            coordinate = {
                "issue_id": inputs.issue_id,
                "arm": arm,
                "coordinate_id": coordinate_id,
                "parent_r0_sha256": parent_hash,
                "condition_bundle_sha256": bundle_hashes[arm],
                "model_config": inputs.model_config,
            }
            try:
                raw_response = evaluator(current_parent, bundles[arm], coordinate)
            except Exception as exc:  # evaluator boundary: preserve and continue other coordinates
                after_evaluator = inputs.parent_r0.read_bytes()
                if (_sha256(after_evaluator) != parent_hash
                        or len(after_evaluator) != len(parent)):
                    raise RuntimeError(
                        f"parent r0 changed during arm {arm}; fail closed") from exc
                record.update({
                    "status": "evaluator_error", "completed": False,
                    "raw_response": None, "parsed_result": None,
                    "error": f"{type(exc).__name__}: {exc}",
                })
            else:
                after_evaluator = inputs.parent_r0.read_bytes()
                if (_sha256(after_evaluator) != parent_hash
                        or len(after_evaluator) != len(parent)):
                    raise RuntimeError(f"parent r0 changed during arm {arm}; fail closed")
                if not isinstance(raw_response, str):
                    exc = TypeError("evaluator must return the raw response as str")
                    record.update({
                        "status": "evaluator_error", "completed": False,
                        "raw_response": None, "parsed_result": None,
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                else:
                    try:
                        parsed = json.loads(raw_response)
                        if not isinstance(parsed, dict):
                            raise ValueError("evaluator JSON response must be an object")
                    except (json.JSONDecodeError, ValueError) as exc:
                        record.update({
                            "status": "parse_error", "completed": False,
                            "raw_response": raw_response, "parsed_result": None,
                            "error": f"{type(exc).__name__}: {exc}",
                        })
                    else:
                        record.update({
                            "status": "completed", "completed": True,
                            "raw_response": raw_response, "parsed_result": parsed,
                        })
        _append_record(records_path, record)
    return RunResult(manifest_path=manifest_path, records_path=records_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="same-parent A/B/C posthoc evaluator runner")
    parser.add_argument("--dry", action="store_true", help="assemble and complete with zero evaluator calls")
    parser.add_argument("--issue-id", required=True)
    parser.add_argument("--parent-r0", type=Path, required=True)
    parser.add_argument("--issue", type=Path, required=True)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--assignment", type=Path, required=True)
    parser.add_argument("--detection-spec", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--common-protocol", type=Path, required=True)
    parser.add_argument("--common-protocol-version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-config-json", default='{"model":"MODEL_PLACEHOLDER"}')
    parser.add_argument("--max-calls", type=int, default=0)
    args = parser.parse_args(argv)
    if not args.dry:
        parser.error("CLI execution is dry-only; inject an evaluator through run() for non-dry use")
    model_config = json.loads(args.model_config_json)
    if not isinstance(model_config, dict):
        parser.error("--model-config-json must decode to an object")
    result = run(
        RunInputs(
            issue_id=args.issue_id, parent_r0=args.parent_r0,
            issue=args.issue, facts=args.facts, assignment=args.assignment,
            detection_spec=args.detection_spec, calibration=args.calibration,
            common_protocol=args.common_protocol,
            common_protocol_version=args.common_protocol_version,
            output_dir=args.output_dir, model_config=model_config,
        ),
        dry=True,
        max_calls=args.max_calls,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    print(json.dumps({"manifest": str(result.manifest_path),
                      "records": str(result.records_path),
                      "expected_calls": manifest["expected_calls"]},
                     ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
