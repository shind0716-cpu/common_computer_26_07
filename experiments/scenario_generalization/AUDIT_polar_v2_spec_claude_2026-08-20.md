# AUDIT — polar_v2 DetectionSpec / calibration / registry — Claude Code — 2026-08-20

상태: **PASS — P0 없음, P1 없음**
역할: independent read-only auditor E
Claude Code session UUID: `9e3796c0-de36-4706-9846-cda75afeb533`는 exile material 구현 세션이며, 이 감사는 별도 process `proc_df357ffaccd4`에서 수행됐다. 감사자는 polar material/spec 구현을 대신했다고 주장하지 않는다.

## 감사 provenance

- material/spec/calibration/manifest/registry/loader/gate/tests와 결정 문서만 읽었다.
- observed pilot/raw/debate/judgment/model output과 prior probe 파일은 열지 않았다.
- 파일 수정·stage·commit·push 없음.
- hash 검사, deterministic in-memory rebuild, gate 평가, 누출/provenance scan, focused/full unittest만 실행.
- 실제 LLM/API 실험 호출 0건. Claude Code 감사 호출 자체는 독립 감사 수행을 위한 호출이며 프로젝트 experiment call이 아니다.

## 실제 실행 결과

- polar_v2 issue/facts/assignment/spec/calibration/manifest 6종 SHA-256 → registry·manifest·spec 좌표와 일치.
- focused:
  `unittest tests.test_polar_v2_material tests.test_polar_v2_detection_spec tests.test_console_scenario_promotion tests.test_detection_spec -v`
  → **92 tests PASS**.
- in-memory spec/calibration rebuild vs on-disk → 둘 다 deterministic match.
- gate:
  `scenario_gate.evaluate("issue_polar_v2", requested_metric="accuracy")`
  → `allowed=False`, `state=candidate`, reasons:
  1. `promotion state not executable: candidate`
  2. `accuracy forbidden for descriptive_stance_only scenario`
  3. `prior not completed: 'pending'`
- calibration → 54 semantic cases + 4 descriptive final-choice cases; 독립 provenance, 5 mention modes,
  blocked와 금지추론 경계 포함; observed-output/answer-key 필드 없음.
- 전체 `unittest discover -s tests -q` → **564 tests PASS**.

## 필수 감사 항목

모두 PASS:

- material/hash/identity exact linkage
- `descriptive_stance_only`; winner/accuracy 금지
- fact03 route alternate + one-way six hours 경계
- fact05 historical-case-only 경계
- fact11 accessibility unknown; fact11/12 orientation blocked
- `_unfavorable_to`는 prereg metadata이며 fact truth 아님
- missing/partial/empty는 unknown; unknown ID/status/outcome request fail-closed
- calibration은 synthetic independent fixtures이며 요구 축을 포괄
- 공통 `FactSpec.extensions`는 구조 보존용 generic field이고 기존 scenario 회귀 없음
- manifest/registry hashes·versions exact
- candidate/prior pending/approval null 유지
- participant prompt/answer key 누출 없음
- project runner 실제 LLM/API 호출 없음

## Findings

- **P0:** 없음
- **P1:** 없음
- **P2 informational:**
  1. registry는 material/spec/calibration hashes를 직접 고정하지만 manifest 파일 자체 hash는 고정하지 않는다.
     현재 교차 좌표가 byte-exact라 무결성 blocker는 아니다.
  2. material-layer known-set evaluator와 spec-layer preservation evaluator 두 개가 존재한다.
     둘 다 answer-free지만 향후 소비자는 의미 상태가 더 엄격한 spec-layer evaluator를 우선해야 한다.

## 최종 판정

**PASS.** polar_v2 material/spec/calibration/manifest/registry integration은 정확하고 fail-closed다.
승격은 candidate + prior pending 때문에 의도대로 차단돼 있다.
