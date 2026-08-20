"""[gate-engineer A] 콘솔 시나리오 승격 원장과 fail-closed 기계 게이트.

`data/issues/*.json`의 존재는 승인 증거가 아니다. 콘솔 목록과 실행 라우트는 모두 이 모듈의
`evaluate()`를 호출하고, 명시 registry 항목과 현재 바이트를 매번 다시 대조한다. 이 모듈은
LLM을 호출하지 않으며 불확실한 상태를 승인으로 추론하지 않는다.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from modules import paths

APPROVED_STATES = frozenset({
    "console_approved", "pilot_only", "confirmatory_frozen", "legacy_approved",
})
KNOWN_STATES = frozenset({
    "candidate", "canonical_reviewed", "spec_ready", "calibration_ready", "prior_ready",
    *APPROVED_STATES,
})
OUTCOME_POLICIES = frozenset({"normative_decision", "descriptive_stance_only"})


@dataclass
class GateResult:
    issue_id: str
    state: str | None = None
    outcome_policy: str | None = None
    allowed: bool = False
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, label: str, reasons: list[str]) -> dict | None:
    if not path.exists():
        reasons.append(f"{label} missing: {path.name}")
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        reasons.append(f"{label} invalid JSON: {exc}")
        return None
    if not isinstance(doc, dict):
        reasons.append(f"{label} must be a JSON object")
        return None
    return doc


def _registry_doc(reasons: list[str]) -> dict | None:
    doc = _read_json(paths.scenario_registry(), "registry", reasons)
    if doc is None:
        return None
    if doc.get("schema_version") != "1.0":
        reasons.append(f"registry schema_version mismatch: {doc.get('schema_version')!r}")
    if doc.get("legacy_policy") != "deny_unless_explicit_legacy_approved":
        reasons.append("registry legacy_policy must be deny_unless_explicit_legacy_approved")
    if not isinstance(doc.get("entries"), list):
        reasons.append("registry entries must be a list")
        return None
    return doc


def _entry_for(issue_id: str, doc: dict, reasons: list[str]) -> dict | None:
    entries = [e for e in doc["entries"] if isinstance(e, dict) and e.get("issue_id") == issue_id]
    if not entries:
        reasons.append(f"registry entry missing: {issue_id}")
        return None
    if len(entries) != 1:
        reasons.append(f"registry duplicate issue_id: {issue_id}")
        return None
    return entries[0]


def _required_entry_fields(entry: dict, reasons: list[str]) -> None:
    for key in ("issue_id", "state", "outcome_policy", "material", "spec", "calibration",
                "prior", "approved_by", "approved_at"):
        if key not in entry:
            reasons.append(f"registry field missing: {key}")


def _check_material(issue_id: str, entry: dict, reasons: list[str]) -> tuple[dict | None, dict | None]:
    material = entry.get("material")
    if not isinstance(material, dict):
        reasons.append("registry material must be an object")
        material = {}

    docs: dict[str, dict | None] = {}
    artifact_paths = {
        "issue": paths.issue(issue_id),
        "facts": paths.facts(issue_id),
        "assignment": paths.assignment(issue_id),
    }
    for kind, path in artifact_paths.items():
        doc = _read_json(path, kind, reasons)
        docs[kind] = doc
        if doc is not None and doc.get("issue_id") != issue_id:
            reasons.append(
                f"{kind} filename/content issue_id mismatch: expected {issue_id}, "
                f"got {doc.get('issue_id')!r}")
        expected = material.get(f"{kind}_sha256")
        if not expected:
            reasons.append(f"registry material.{kind}_sha256 missing")
        elif path.exists() and _sha(path) != expected:
            reasons.append(f"{kind} hash mismatch")

    facts_doc, assignment_doc = docs.get("facts"), docs.get("assignment")
    if facts_doc is not None and assignment_doc is not None:
        rows = facts_doc.get("facts")
        agents = assignment_doc.get("agents")
        if not isinstance(rows, list):
            reasons.append("facts.facts must be a list")
        elif not isinstance(agents, list):
            reasons.append("assignment.agents must be a list")
        else:
            fact_ids = [f.get("fact_id") for f in rows if isinstance(f, dict)]
            valid = {fid for fid in fact_ids if isinstance(fid, str) and fid}
            if len(valid) != len(fact_ids):
                reasons.append("facts contains missing or duplicate fact_id")
            assigned = set()
            malformed = False
            for agent in agents:
                ids = agent.get("assigned_fact_ids") if isinstance(agent, dict) else None
                if not isinstance(ids, list):
                    malformed = True
                    continue
                assigned.update(ids)
            if malformed:
                reasons.append("assignment assigned_fact_ids must be lists")
            unknown = sorted(str(fid) for fid in assigned - valid)
            orphan = sorted(valid - assigned)
            if unknown:
                reasons.append(f"assignment unknown fact_id: {unknown}")
            if orphan:
                reasons.append(f"assignment orphan fact_id: {orphan}")
    return facts_doc, assignment_doc


def _check_spec_and_calibration(issue_id: str, entry: dict, facts_doc: dict | None,
                                reasons: list[str], warnings: list[str]) -> None:
    spec_cfg = entry.get("spec")
    cal_cfg = entry.get("calibration")
    if not isinstance(spec_cfg, dict):
        reasons.append("registry spec must be an object")
        spec_cfg = {}
    if not isinstance(cal_cfg, dict):
        reasons.append("registry calibration must be an object")
        cal_cfg = {}

    spec_doc = None
    if spec_cfg.get("required") is True:
        spec_path = paths.detection_spec(issue_id)
        spec_doc = _read_json(spec_path, "spec", reasons)
        expected_sha = spec_cfg.get("sha256")
        if not expected_sha:
            reasons.append("registry spec.sha256 missing")
        elif spec_path.exists() and _sha(spec_path) != expected_sha:
            reasons.append("spec hash mismatch")
        if spec_doc is not None:
            if spec_doc.get("issue_id") != issue_id:
                reasons.append("spec issue_id mismatch")
            if spec_doc.get("spec_version") != spec_cfg.get("version"):
                reasons.append("spec version mismatch")
            facts_path = paths.facts(issue_id)
            if facts_path.exists() and spec_doc.get("material_sha256") != _sha(facts_path):
                reasons.append("spec material hash mismatch")
            if facts_doc is not None and isinstance(facts_doc.get("facts"), list):
                material_ids = {f.get("fact_id") for f in facts_doc["facts"] if isinstance(f, dict)}
                spec_ids = set((spec_doc.get("facts") or {}).keys())
                if material_ids != spec_ids:
                    reasons.append("spec fact IDs mismatch material")
    elif spec_cfg.get("required") is False:
        if not str(spec_cfg.get("reason") or "").strip():
            reasons.append("spec exemption reason missing")
        else:
            warnings.append("semantic spec 미적용")
    else:
        reasons.append("registry spec.required must be boolean")

    if cal_cfg.get("required") is True:
        cal_path = paths.calibration_set(issue_id)
        cal_doc = _read_json(cal_path, "calibration", reasons)
        expected_sha = cal_cfg.get("sha256")
        if not expected_sha:
            reasons.append("registry calibration.sha256 missing")
        elif cal_path.exists() and _sha(cal_path) != expected_sha:
            reasons.append("calibration hash mismatch")
        if cal_doc is not None:
            if cal_doc.get("issue_id") != issue_id:
                reasons.append("calibration issue_id mismatch")
            if cal_doc.get("version") != cal_cfg.get("version"):
                reasons.append("calibration version mismatch")
            if spec_doc is not None:
                if cal_doc.get("spec_version") != spec_doc.get("spec_version"):
                    reasons.append("calibration spec version mismatch")
                if spec_doc.get("calibration_version") != cal_doc.get("version"):
                    reasons.append("spec/calibration version mismatch")
    elif cal_cfg.get("required") is False:
        if not str(cal_cfg.get("reason") or "").strip():
            reasons.append("calibration exemption reason missing")
        else:
            warnings.append("independent calibration 미적용")
    else:
        reasons.append("registry calibration.required must be boolean")


def _check_prior(entry: dict, facts_doc: dict | None, reasons: list[str], warnings: list[str]) -> None:
    prior = entry.get("prior")
    if not isinstance(prior, dict):
        reasons.append("registry prior must be an object")
        return
    required = prior.get("required")
    status = prior.get("status")
    if required is True:
        if status != "completed":
            reasons.append(f"prior not completed: {status!r}")
        elif facts_doc is not None and isinstance(facts_doc.get("facts"), list):
            unprobed = [f.get("fact_id") for f in facts_doc["facts"]
                        if not isinstance(f.get("prior"), dict)
                        or f["prior"].get("score") is None]
            if unprobed:
                reasons.append(f"prior completed claim conflicts with material: {unprobed}")
    elif required is False:
        if status != "exempt" or not str(prior.get("reason") or "").strip():
            reasons.append("prior exemption requires status=exempt and reason")
        else:
            warnings.append("prior 명시 면제")
    else:
        reasons.append("registry prior.required must be boolean")


def evaluate(issue_id: str, *, requested_metric: str | None = None) -> GateResult:
    """현재 파일 바이트 기준으로 issue 하나를 평가한다. 실패는 결과 객체이지 승인 추론이 아니다."""
    result = GateResult(issue_id=issue_id)
    doc = _registry_doc(result.blocking_reasons)
    if doc is None:
        return result
    entry = _entry_for(issue_id, doc, result.blocking_reasons)
    if entry is None:
        return result

    _required_entry_fields(entry, result.blocking_reasons)
    result.state = entry.get("state")
    result.outcome_policy = entry.get("outcome_policy")
    if result.state not in KNOWN_STATES:
        result.blocking_reasons.append(f"unknown promotion state: {result.state!r}")
    elif result.state not in APPROVED_STATES:
        result.blocking_reasons.append(f"promotion state not executable: {result.state}")
    if result.outcome_policy not in OUTCOME_POLICIES:
        result.blocking_reasons.append(f"unknown outcome_policy: {result.outcome_policy!r}")
    if result.state in APPROVED_STATES:
        if not str(entry.get("approved_by") or "").strip():
            result.blocking_reasons.append("approved_by missing for approved state")
        if not str(entry.get("approved_at") or "").strip():
            result.blocking_reasons.append("approved_at missing for approved state")
    if result.state == "legacy_approved":
        result.warnings.append("legacy_approved: semantic spec 미적용 가능 — 명시 정책")
    if requested_metric == "accuracy" and result.outcome_policy == "descriptive_stance_only":
        result.blocking_reasons.append("accuracy forbidden for descriptive_stance_only scenario")

    facts_doc, _ = _check_material(issue_id, entry, result.blocking_reasons)
    _check_spec_and_calibration(issue_id, entry, facts_doc,
                                result.blocking_reasons, result.warnings)
    _check_prior(entry, facts_doc, result.blocking_reasons, result.warnings)
    result.allowed = not result.blocking_reasons
    return result


def registry_results() -> list[GateResult]:
    """원장 전 항목의 상태를 UI용으로 돌려준다. 파일 glob은 승인 후보 집합으로 쓰지 않는다."""
    reasons: list[str] = []
    doc = _registry_doc(reasons)
    if doc is None:
        return [GateResult(issue_id="<registry>", blocking_reasons=reasons)]
    results = []
    seen = set()
    for raw in doc["entries"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("issue_id"), str):
            results.append(GateResult(issue_id="<invalid-entry>",
                                      blocking_reasons=["registry entry missing issue_id"]))
            continue
        iid = raw["issue_id"]
        if iid in seen:
            results.append(GateResult(issue_id=iid,
                                      blocking_reasons=[f"registry duplicate issue_id: {iid}"]))
            continue
        seen.add(iid)
        results.append(evaluate(iid))
    return results


def require(issue_id: str, *, requested_metric: str | None = None) -> GateResult:
    """실행 입구용. 호출자는 blocking_reasons를 HTTP 400 등으로 변환한다."""
    return evaluate(issue_id, requested_metric=requested_metric)
