# Audit — exile_v2 semantic package and A/B/C runner

Date: 2026-08-20
Auditor: Claude Code
Audit mode: independent, read-only
Parent integrator: Hermes/GPT Sol

## Verdict

PASS after remediation.

- P0: none.
- P1: one runner manifest provenance-label defect, reproduced and fixed by Hermes/GPT Sol.

## Claude-reviewed scope

- `modules/abc_same_parent_runner.py`
- `tests/test_abc_same_parent_runner.py`
- `data/judge_protocols/common_semantic_judge_v1.md`
- `시나리오/build_detection_spec_exile_v2.py`
- `tests/test_exile_v2_detection_spec.py`
- exile_v2 DetectionSpec, calibration, manifest
- `data/scenario_registry.json`
- `modules/content_hash.py`
- `modules/scenario_gate.py`
- supporting `modules/detection_spec.py`

## Passed contracts

Claude confirmed by static inspection:

- raw-byte parent `r0` identity is common to all A/B/C arms;
- canonical material is common to all arms;
- only post-hoc judge bundles differ by A/B/C condition;
- no participant prompt is assembled;
- call budget is checked before any evaluator call;
- append + flush + fsync is used;
- completed coordinate resume/dedup works;
- parse/evaluator errors retain raw/error evidence and remain incomplete;
- unknown is not coerced;
- identity and cross-links fail closed;
- parent mutation is detected even after the final evaluator;
- text artifacts use LF-canonical hashes while parent remains raw-byte exact;
- exile_v2 remains descriptive-only;
- calibration is synthetic and independent of observed pilot/raw/model output;
- ethics sidecar remains `blocked_pending_human_assignment` with null coder/adjudicator;
- registry is linked but remains candidate with prior pending.

## P1 and remediation

Finding:
- Runner manifest used a generic version accessor for calibration.
- Because `spec_version` was checked before `version`, the manifest mislabeled calibration `cal-0.2` as `0.2`.

Strict RED:
- Actual polar package integration asserted `manifest["calibration"]["version"] == "cal-0.2"`.
- Observed failure: `'cal-0.2' != '0.2'`.

GREEN:
- Runner now requires and records `calibration_doc["version"]` directly.
- Runner suite: 12 tests passed.

## Provenance boundary

Claude Code did not edit files, create files, run the test suite, or make experiment/model participant calls. The 592-test result was produced by Hermes/GPT Sol and was explicitly not claimed by Claude.

## Subsequent owner amendment

This audit predates the owner-approved E-8 operating amendment. The earlier null/null
`blocked_pending_human_assignment` contract is superseded for development operation by spec `0.2`:

- human coder: `study_owner_user`
- independent adjudicator: deferred/null
- development coding: allowed
- confirmatory ethics use: blocked pending independent adjudicator

The frozen material sidecar remains an unchanged pre-assignment snapshot. This amendment was implemented
and verified by Hermes/GPT Sol after the Claude read-only audit; it is not part of Claude's original PASS.
