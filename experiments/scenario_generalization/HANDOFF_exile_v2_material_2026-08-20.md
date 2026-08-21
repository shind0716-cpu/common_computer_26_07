# HANDOFF — issue_exile_v2 정본 재료 구현 (2026-08-20)

상태: **재료 3종 GREEN · 팀 검수/registry/spec 전 blocked**
지위: 실행 인계문 (근거 자료 아님 · 계약 아님)
작성 역할: material builder (STRICT TDD)
범위: exile v2 **재료(builder/source/runtime) + 집중 테스트만**. DetectionSpec·calibration·
registry·promotion·prior probe·실호출은 이 작업 밖이다. polar spec engineer 와 경합하지 않도록
이 파일은 console-promotion HANDOFF 와 분리해 새로 판다.

## 무엇을 근거로 했나

- `DECISION_PACKET_POLAR_EXILE_V2_2026-08-20.md` §2(E-0A~E-9A), §5·§6·§7 owner 서명.
  요한이 Hermes 대화에서 **E-0A~E-9A 전부 직접 승인**(§7). E-8A 는 sidecar 분리는 승인,
  **사람 coder·독립 adjudicator 이름 지정은 별도 운영 assignment 로 남는다** — 지정 전까지
  윤리 판정·확증 차단.
- 골격 템플릿: `시나리오/build_issue_polar_v2.py` (같은 결정 패킷의 자매 재료).
- v1 원본: `시나리오/build_issue_exile.py`, `data/…/issue_exile`.

## STRICT TDD 기록

### RED (구현 전)

- 파일: `tests/test_exile_v2_material.py` 먼저 작성.
- 실행: `PYTHONUTF8=1 python -m unittest tests.test_exile_v2_material -v`
- 결과: **31 errors** — `ModuleNotFoundError: 시나리오.build_issue_exile_v2`,
  `FileNotFoundError: 시나리오/facts_issue_exile_v2.json` 등. v2 package 부재로 예상대로 RED.
  (v1 보존 테스트만 통과 — old bytes 는 이미 그 자리에 있으므로.)

### GREEN (구현 후)

1. `시나리오/build_issue_exile_v2.py` 작성 → `PYTHONUTF8=1 python 시나리오/build_issue_exile_v2.py`
   → 자가 check() **전부 통과** (앵커·identity·결정 문면 E-1A~E-7A·윤리 sidecar E-8A·구조·배분·evaluator).
2. `PYTHONUTF8=1 python -m unittest tests.test_exile_v2_material -v` → **Ran 30 tests, OK**.
3. `PYTHONUTF8=1 python -m modules.validate data/issues/issue_exile_v2.json
   data/facts/facts_issue_exile_v2.json data/assignments/assignment_issue_exile_v2.json`
   → **모든 검사 통과**.
4. `python -m py_compile 시나리오/build_issue_exile_v2.py tests/test_exile_v2_material.py` → OK.
5. byte parity(시나리오 ↔ data) 3종 **일치** (한 builder 가 같은 직렬화 문자열을 6곳에 씀).
6. 전체 스위트 `python -m unittest discover -s tests -q` → **Ran 559 tests, OK** (회귀 없음).

## 반영한 owner 결정 (문면 변경은 fact 01·02·08 셋뿐)

| 결정 | 반영 |
|---|---|
| E-0A | `outcome_policy=descriptive_stance_only`. winner/accuracy 없음. `reject_accuracy_request` fail-closed. |
| E-1A | fact01 = "시 경비대가 … 수사 명단에 올린 사람 … 이천 명 가운데 서른한 명 … 유죄 판결 … 확정되지 않았다". `FACT01_SEMANTIC{source=시 경비대,count=31/2000,guilt=unknown}`, `GUILT_UNKNOWN_FACTS`. |
| E-2A | fact02 = "적발 건수는 … 아홉 배지만, 증가 원인은 조사에서 확정되지 않았다". `CAUSAL_ATTRIBUTION_UNCONFIRMED`. |
| E-3A | fact06 문면 유지(거부당한 주체=경비대만). 행위자 unknown. `REFUSAL_ACTOR_UNKNOWN_FACTS` + `reject_refusal_actor_fill()` 가 조직원·위원회·정착민 전체 충전을 fail-closed. |
| E-4A | fact08 = "… 예순둘 가운데 열아홉이 이후 문을 닫았으나, 각 폐업의 직접 원인은 따로 확인되지 않았다". `CLOSURE_CAUSE_UNCONFIRMED`. |
| E-5A | fact10 문면 유지(11석·단순 과반). `VOTE_THRESHOLD_BLOCKED` — 6표 계산 blocked. |
| E-6A | fact11 문면 유지(미갱신→넉 달 내부 인과 보존). `INTERNAL_CAUSE_NO_UNIVERSALIZATION` — 보편화 금지. |
| E-7A | fact12 문면 유지(조항 존재·미사용만). `OPTION_FEASIBILITY_UNKNOWN` — 실행성·효과 unknown. |
| E-8A | `ethics_sidecar` 를 issue·facts 양쪽에 `status=blocked_pending_human_assignment`, `separated_from_fact_preservation=true`, `human_coder=null`, `independent_adjudicator=null`. **윤리 코딩 안 함.** `require_human_ethics_assignment()` 사람 미지정 시 RuntimeError. evaluator 는 상태만 싣고 점수 없음. |
| E-9A | 새 package `issue_exile_v2` + `fact_exile_v2_01`~`12` 전량 v2 namespace. v1 fact_id 와 disjoint. |

- 본문·질문·요약문·입장문·최종 폴링은 **v1 과 글자 동일**(테스트가 v1 issue 와 대조).
- 불리 대칭 추방 4:잔류 4·중립 2·양쪽 2·교대 배치, 배분 4에이전트·전 팩트 고립(밀도 1.0)·
  자기불리 1+상대불리 1 — v1 설계 유지. **아무도 12팩트 전량을 혼자 갖지 않는다.**
- prior 전량 `null`. v1 prior/output 미이전. 실호출 전 독립 probe 별도 승인 필요.
- unknown fact_id·accuracy/winner 요청·거부 행위자 충전·사람 미지정 윤리 코딩 = 전부 fail-closed.

## 바뀐/추가된 파일 (전부 신규 — 기존 바이트 무수정)

```
시나리오/build_issue_exile_v2.py          (신규 builder, LLM 호출 0)
시나리오/issue_exile_v2.json              (source)
시나리오/facts_issue_exile_v2.json        (source)
시나리오/assignment_issue_exile_v2.json   (source)
data/issues/issue_exile_v2.json          (runtime, source 와 byte-identical)
data/facts/facts_issue_exile_v2.json     (runtime, byte-identical)
data/assignments/assignment_issue_exile_v2.json (runtime, byte-identical)
tests/test_exile_v2_material.py          (신규 집중 테스트 30개)
```

건드리지 않은 것: `data/scenario_registry.json`(사전 M 상태 그대로 보존),
console-promotion HANDOFF, v1 exile 재료·prior 원자료(해시 재확인 아래), 그 외 공유 트리의
사전 변경분. observed pilot/model output 은 열지 않았다.

## v1 불변 재확인 (한 바이트도 안 바뀜)

| 파일 | SHA-256 |
|---|---|
| data/issues/issue_exile.json | `7138c2d7…70f9` |
| data/facts/facts_issue_exile.json | `df753281…8bb7` |
| data/assignments/assignment_issue_exile.json | `1f598d76…8497` |
| 시나리오/prior_issue_exile.json | `4c02bf13…22a7` |
| 시나리오/prior_issue_exile.partial.jsonl | `6f713bf0…4a14` |

(테스트 `ExileV1PreservationTests` 가 시나리오/data 양쪽 3종 + prior 2종을 핀으로 검사.)

## 다음 담당에게 — 여전히 BLOCKED

1. **E-8A 사람 지정** — 윤리 sidecar 의 human coder·독립 adjudicator 실명. owner(요한)만
   정할 수 있다. 지정 전까지 exile 윤리 판정·확증 실행 금지(`require_human_ethics_assignment`
   가 강제). 재료는 이 자리를 `null` + `blocked_pending_human_assignment` 로 비워 뒀다.
2. **독립 material review + owner 최종 material hash 승인** (§4 순서 6). 지금은 후보 지위.
3. **DetectionSpec·calibration** — material hash 확정 뒤 별도 spec-engineer 몫(§4 순서 7).
   이 작업에서 만들지 않았다.
4. **registry 항목·promotion** — 이 작업 밖. `issue_exile_v2` 는 registry 에 없다(의도).
   승인·감사 뒤 별도 작업에서 candidate + prior pending + spec/calibration pending 으로 등록.
5. **prior probe** — v2 문면 확정 뒤 독립 probe 별도 승인·실행. 지금은 실호출 금지라 미실행.

이 인계문은 구현 승인서가 아니다. 3번 이후는 owner·독립 감사 전까지 blocked.

---

## Hermes/GPT Sol 독립 material review — 2026-08-20

Claude material 구현 종료 후 Hermes/GPT Sol이 실제 파일을 다시 읽고 독립 재검증했다.

- `python -m unittest tests.test_exile_v2_material -v` → **30/30 PASS**
- `python -m modules.validate` issue/facts/assignment → **3종 PASS**
- builder/test `py_compile` → **PASS**
- builder 재실행 전/후 v2 6개 산출물 SHA-256 동일 → **deterministic rebuild PASS**
- source/runtime issue·facts·assignment → **3쌍 byte-identical**
- v1 source/runtime 6종과 prior 원자료 2종 → 결정 패킷 동결 SHA-256과 일치
- v2 hash:
  - issue `99e74ccbc8294fde943cb1cb23fceaf9c56e2622c4daa91abbc6de1917718216`
  - facts `87fb04e79bc935d30e0e525a6f58694d541fc35f754e973ab68089ddc113142e`
  - assignment `52233f4a2e0dd04950410120c966b574008e6d32e62441552a300631c279a471`
- E-8 ethics sidecar는 fact preservation과 분리돼 있으며 coder/adjudicator `null`,
  `blocked_pending_human_assignment`를 유지한다.
- 신규 prior/experiment LLM/API 호출: **0**.

판정: **material identity/hash와 E-0A~E-9A 경계는 독립 재검증 완료.** 이 판정은
윤리 sidecar 코딩 승인이 아니다. 실제 human coder·independent adjudicator 지정 전까지 윤리 축은
계속 blocked이며, DetectionSpec/calibration은 이 frozen material hash에 연결하는 다음 단계다.

### Parent registry candidate 연결 — 2026-08-20

독립 material review 뒤 parent Hermes가 strict RED→GREEN으로 `issue_exile_v2` candidate entry를
추가했다.

- RED: repository registry test → entry 부재로 FAIL
- GREEN: candidate entry + frozen issue/facts/assignment hashes + spec/calibration pending zero +
  prior pending + approval null을 연결; focused **31 tests PASS**
- registry JSON Schema → PASS
- 현재 gate는 candidate, descriptive accuracy 금지, spec missing, calibration missing, prior pending으로
  fail-closed. console approval이나 실행 권한을 부여하지 않았다.

---

## issue_exile_v2 DetectionSpec / synthetic calibration — 2026-08-20

- **RED**: `PYTHONUTF8=1 python -m unittest tests.test_exile_v2_detection_spec -v`
  → exit 1, **Ran 2 tests, errors=5**. `시나리오.build_detection_spec_exile_v2`와
  `data/detection_specs/{issue,calibration,manifest}_issue_exile_v2.json` 부재로 예상대로 실패.
- **GREEN**: deterministic builder 실행 뒤 같은 focused 명령 → **Ran 23 tests, OK**.
- 파일(전부 신규):
  - `시나리오/build_detection_spec_exile_v2.py`
  - `tests/test_exile_v2_detection_spec.py`
  - `data/detection_specs/issue_exile_v2.json`
  - `data/detection_specs/calibration_issue_exile_v2.json`
  - `data/detection_specs/manifest_issue_exile_v2.json`
- 버전: spec `0.1`, calibration `cal-0.1`.
- frozen material hashes: issue `99e74ccbc8294fde943cb1cb23fceaf9c56e2622c4daa91abbc6de1917718216`;
  facts `87fb04e79bc935d30e0e525a6f58694d541fc35f754e973ab68089ddc113142e`;
  assignment `52233f4a2e0dd04950410120c966b574008e6d32e62441552a300631c279a471`.
- 신규 파일 SHA-256: builder `33bb8b7c5595f0230591ed6207832c730fada890a53e6ea67fe269e86e682bd2`;
  test `2f030f73f7e08e2e96ba9157febd7f754e15ff2910c625853f9f0d32720d2019`;
  spec `8aa4df79e06bd4fbac5cb48999f48f43579701f4b75302e68c7568b4757e840c`;
  calibration `2f337bc7ea461532f3826cec0c275e162185fbe0dc16531747e72e2879adbce7`;
  manifest `a00e7eabbfa0f4c96e2d218e9bf8dc08e52a72f3e1f559c59cd03368da559fad`.
- 검증: common/focused 묶음 **148 tests OK**; 전체 unittest **587 tests OK**;
  material validator **3종 PASS**; builder/test `py_compile` PASS; 재빌드 전후 3개 detection
  artifact SHA-256 동일 및 manifest 내부 5개 지문 재대조 PASS.
- 계약: `descriptive_stance_only`; winner/accuracy/correctness·participant prompt·answer key 없음;
  missing/partial/empty는 `unknown`; `_unfavorable_to`는 prereg metadata only. synthetic calibration은
  frozen material+owner decisions만 사용했고 observed pilot/raw/model output 및 신규 LLM/API 호출은 0.
- **blocker 유지**: E-8 ethics sidecar는 fact preservation과 분리,
  `blocked_pending_human_assignment`, human coder/independent adjudicator `null`. calibration은 차단
  경계와 분리만 확인하며 윤리 score/verdict/label을 만들지 않았다. 실제 사람 지정 전 윤리 판정·확증은 blocked.
- registry·v1/v2 material·prior/pilot/raw·polar·runner·console-promotion handoff는 수정하지 않음.

---

## Parent reconciliation and E-8 operating amendment — 2026-08-20

### Dual-hash reconciliation

The delegated verifier reported the LF-canonical hashes as incompatible with the original frozen raw-byte
hashes. Parent verification showed that both sets describe the same unchanged files:

- raw bytes: issue `99e74ccb…`, facts `87fb04e7…`, assignment `52233f4a…`
- LF-canonical text identity: issue `833fcc22…`, facts `efc64f0a…`, assignment `38ad3a6c…`

`modules/content_hash.py` intentionally normalizes CRLF/CR to LF for repository text-artifact manifests,
while raw-byte freeze checks still confirm the original three hashes. No exile material bytes were modified.
A fresh deterministic builder run plus 55 focused checks returned exit 0 with
`EXILE_DUAL_HASH_CONTRACT_OK`.

### Owner-approved lower-friction E-8 policy

The owner selected: one-person development coding now, independent adjudicator deferred until immediately
before confirmatory ethics use.

- development human coder role ID: `study_owner_user`
- independent adjudicator: `null` / deferred
- development status: `development_coding_allowed_adjudicator_deferred`
- confirmatory status: `confirmatory_blocked_pending_independent_adjudicator`
- material issue/facts bytes remain frozen with their pre-assignment null sidecar; the versioned spec marks
  it `frozen_preassignment_snapshot`
- ethics remains separate from fact preservation and still has no score, verdict, winner, or accuracy

Strict TDD evidence:

- RED: previous `blocked_pending_human_assignment` status failed the new development-allowed contract.
- RED: registry integration reported spec/calibration hash and version mismatches after the version bump.
- GREEN: spec `0.2`, calibration `cal-0.2`, manifest, and registry coordinates synchronized.
- focused runner/exile/registry suite: 67 tests, OK.
- full unittest discovery after amendment: exit 0.
- new experiment/model participant calls: 0.
