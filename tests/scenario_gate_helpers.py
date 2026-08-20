"""콘솔 테스트 픽스처용 명시적 legacy 승인 원장 작성기."""
from __future__ import annotations

import hashlib
import json

from modules import paths


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approve_legacy_fixture(issue_id: str) -> None:
    """테스트가 파일 존재를 암묵 승인하지 않도록 legacy 정책을 명시한다."""
    doc = {
        "schema_version": "1.0",
        "legacy_policy": "deny_unless_explicit_legacy_approved",
        "entries": [{
            "issue_id": issue_id,
            "state": "legacy_approved",
            "outcome_policy": "normative_decision",
            "material": {
                "issue_sha256": _sha(paths.issue(issue_id)),
                "facts_sha256": _sha(paths.facts(issue_id)),
                "assignment_sha256": _sha(paths.assignment(issue_id)),
            },
            "spec": {"required": False, "reason": "pre-semantic unit-test fixture"},
            "calibration": {"required": False, "reason": "pre-semantic unit-test fixture"},
            "prior": {"required": False, "status": "exempt",
                      "reason": "deterministic no-LLM unit-test fixture"},
            "approved_by": "test-suite",
            "approved_at": "2026-08-20T00:00:00Z",
        }],
    }
    path = paths.scenario_registry()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
