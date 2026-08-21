# Handoff — Same-parent A/B/C post-hoc runner

Date: 2026-08-20
Status: implemented and independently reviewed
Working tree: shared; no stage/commit/push/reset/checkout/stash performed
Experiment participant/model API calls: 0

## Provenance

- Initial implementation: delegated GPT Sol runner-engineer D, delegation `deleg_70dc711b`.
- Parent integration, contract hardening, tests, and verification: Hermes/GPT Sol.
- Independent read-only audit: Claude Code. Claude did not edit files or run tests.

## Artifacts

- `modules/abc_same_parent_runner.py`
- `tests/test_abc_same_parent_runner.py`
- `data/judge_protocols/common_semantic_judge_v1.md`

## Implemented contract

1. A/B/C receive the same exact parent `r0` bytes, raw SHA-256, and byte length.
2. All arms receive the same canonical issue/facts material as a post-hoc judging baseline.
3. A receives common protocol only beyond the common baseline; B adds DetectionSpec; C adds DetectionSpec plus independent calibration.
4. Bundles are explicitly `role=posthoc_judge`; no participant/generation prompt is assembled.
5. Text artifacts use LF-canonical SHA-256 for cross-platform registry/manifest parity, while parent `r0` deliberately remains exact raw-byte SHA-256.
6. Spec material hash and calibration→spec version cross-links fail closed before output/evaluator calls.
7. Pending total and per-arm calls are computed before the first evaluator call; `max_calls` violation aborts before calls.
8. `--dry` executes all coordinates with zero evaluator calls.
9. JSONL records are append-only and use append + flush + fsync.
10. Completed coordinates are skipped on resume; incomplete parse/evaluator errors are retried without pretending completion.
11. Parse failures preserve raw response; evaluator errors preserve error text; both record `completed=false`.
12. `unknown` is retained rather than coerced to false.
13. Parent mutation is checked before and after every arm, including after the final-arm evaluator.
14. Inspectable deterministic A/B/C bundle files and coordinate manifest are emitted.

## Strict RED → GREEN evidence

Delegated initial slice:
- RED: `ModuleNotFoundError: modules.abc_same_parent_runner`.
- Minimal GREEN: `Ran 1 test ... OK`.

Parent hardening:
- RED: missing spec-material/calibration-spec cross-link checks and final-arm post-evaluator parent mutation were reproduced by focused tests (exit 1).
- GREEN: cross-links and post-evaluator mutation checks implemented; runner suite passed.
- RED: post-hoc bundles lacked canonical material, so a judge could not evaluate a parent against source facts (focused test exit 1).
- GREEN: identical canonical issue/facts baseline added to all three arms.
- RED: actual polar package dry integration failed before a canonical common protocol artifact existed.
- GREEN: `common_semantic_judge_v1.md` added and actual polar A/B/C dry assembly completed with zero calls.
- Claude P1 RED: coordinate manifest recorded calibration `spec_version` (`0.2`) as calibration version instead of its own `cal-0.2`.
- GREEN: dedicated calibration version extraction added; actual polar integration asserts `cal-0.2`.

## Verification

- `python -m unittest tests.test_abc_same_parent_runner -v`
  - `Ran 12 tests ... OK`.
- Focused combined runner/exile/promotion suite:
  - `Ran 83 tests ... OK`.
- Full canonical unittest run before the final P1 fix:
  - `Ran 592 tests ... OK`.
- Full canonical unittest rerun after the P1 fix exited 0; output capture formatting failed after the suite, but the suite process return code was preserved as 0.
- `py_compile` passed for runner and test.
- `git diff --check` passed; only existing CRLF→LF warnings were printed.

## Claude Code read-only audit

Initial verdict: PASS with no P0 and one P1 provenance-labeling defect.

P1:
- `calibration.version` used the generic accessor that preferred `spec_version`.
- Fixed with a dedicated `calibration_doc["version"]` requirement and manifest value.
- Regression test now asserts actual polar `cal-0.2`.

All other reviewed contracts passed, including exact parent bytes, post-hoc-only role, budget preflight, fsync, resume/dedup, error/raw preservation, unknown preservation, cross-link fail-closed behavior, and final-arm mutation detection.

## Remaining gates

- No real A/B/C judge calls may run yet.
- award_v2, polar_v2, and exile_v2 remain `candidate` with prior `pending`.
- exile_v2 E-8 was subsequently amended: `study_owner_user` may perform development coding now; an independent adjudicator is required only before confirmatory ethics use.
