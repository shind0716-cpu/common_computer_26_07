# Claude 독립 감사 — 콘솔 승격 A+B 통합

작성일: 2026-08-20  
감사 실행기: Claude Code, session `676f0a96-5eb0-4530-bb0b-34a543818028`  
역할: independent-auditor E, read-only  
상태: **최초 P0 blocker 발견 → Hermes가 RED/GREEN 수정 → Claude 재감사 PASS**

## 최초 판정

Claude는 A의 `/api/run` 게이트와 B의 award_v2 의미 패키지 자체는 견고하다고 판정했지만,
같은 콘솔의 `/api/solo/run`이 `scenario_gate`를 전혀 거치지 않아 candidate 시나리오로
실호출할 수 있는 P0 우회 경로를 발견했다.

### B1 — `/api/solo/run` 승격 게이트 우회

- 위치: `tools/console/app.py:1086` 부근 `api_solo_run`
- 관련 어휘: `tools/console/app.py:915` 부근 `SOLO_ISSUES`
- 하류 실호출: `experiments/memory_structure/run_solo.py`의 `llm.obtain_response` 경로
- 영향:
  - `issue_polar`, `issue_exile`가 registry에서 candidate여도 solo 실호출 가능
  - registry가 없는 `issue_camp`도 solo 경로에서 선택 가능
  - “콘솔 입구가 fail-closed”라는 통합 주장을 무효화

## Claude가 실제로 실행했다고 보고한 검증

- award_v2 5개 산출물 SHA-256과 registry/manifest 대조: 일치
- 관련 테스트: 44 tests PASS
- 당시 전체 테스트: 478 tests PASS
- 실제 registry: 6/6 blocked, approved 0
- registry JSON Schema: PASS
- `git diff --check`: 오류 없음
- `run_solo.py`에서 scenario registry 참조: 없음

## Improvement findings

1. polar/exile v1 prior를 registry에서 `completed`로 둔 상태는 owner가 확인해야 한다.
   v2로 승격할 경우 old prior를 상속해서는 안 된다.
2. award build-time `evaluate_chain(known_fact_ids)`와 운영 `modules/chain_eval.py` 경로가 이원화돼
   있으며 calibration chain case가 build evaluator의 출력으로 생성돼 순환 검증 성격이 있다.
3. award calibration은 preservation 축 중심이며 mention_mode/blocked 기대값이 없다.
4. descriptive accuracy 차단은 `requested_metric="accuracy"`를 전달하는 호출자 협조에 의존한다.
5. `scenario_gate._sha`의 exists/read 사이 race는 500을 낼 수 있으나 승인 방향으로 새지는 않는다.

## Hermes 수정 — strict TDD

### RED 1: solo 실행 우회

명령:

```text
python -m unittest tests.test_console_solo.TestRunGate.test_candidate_issue_is_blocked_before_preflight_or_subprocess -v
```

수정 전 실제 결과:

```text
FAIL — expected 400, got 200
subprocess command contained run_solo.py --issue issue_exile
```

수정:

- `api_solo_run`에서 `_solo_validate` 직후 `scenario_gate.require(req.issue)` 재검사
- blocked이면 prereg·preflight·Popen 전에 HTTP 400
- dry run도 실제 승인 package만 대상으로 하도록 같은 gate 적용

수정 후:

```text
PASS
```

실제 candidate `issue_exile` 0콜 요청:

```text
400
scenario gate blocked issue_exile: promotion state not executable: candidate;
spec missing; calibration missing
```

### RED 2: solo 목록 노출

명령:

```text
python -m unittest tests.test_console_solo.TestSoloMetaGate.test_meta_exposes_only_gate_approved_solo_issues -v
```

수정 전 실제 결과:

```text
FAIL — issue_camp, issue_throne, issue_polar, issue_exile 전부 노출
```

수정:

- `/api/solo/meta`가 각 `SOLO_ISSUES`에 `scenario_gate.evaluate()` 적용
- `allowed=True`인 issue만 `issues` 선택지에 노출
- 차단 결과는 `scenario_gate_rows`로 보존
- 기본 issue가 승인되지 않았으면 `default_issue=null`

수정 후:

```text
TestSoloMetaGate + TestRunGate 11 tests PASS
실 registry solo issues={} / 네 issue 모두 blocked
```

## Claude 재감사 판정

Claude Code가 같은 감사 session에서 수정된 현재 working tree를 다시 읽고 B1을 **PASS**로
판정했다.

- `/api/solo/meta`: 승인된 issue만 노출하고 default도 승인되지 않으면 null
- `/api/solo/run`: dry 여부와 무관하게 `scenario_gate.require(req.issue)` 적용
- ordering: gate가 `llm.preflight`와 `subprocess.Popen`보다 먼저 실행
- 남은 실행 bypass: 없음
- 당시 caveat였던 blocked candidate의 `dry=True` 명시 테스트도 이후 추가해 통과시켰다.

## 남은 판정

- improvement I1~I5는 별도 issue 또는 후속 작업으로 분리한다.
- prior·owner approval·promotion state는 이번 수정으로 승인하지 않는다.
