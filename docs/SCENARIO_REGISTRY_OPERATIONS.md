# 콘솔 시나리오 승격 registry 운영

지위: **확정 — gate-engineer A의 fail-closed 운영 계약 (2026-08-20)**  
적용 범위: `tools/console`의 토론 시나리오 목록과 `/api/run`; 신규 실호출을 승인하지 않는다.

## 1. 단일 입구

- 승인 원장: `data/scenario_registry.json`
- JSON Schema: `data/scenario_registry.schema.json`
- 기계 게이트: `modules/scenario_gate.py`
- 콘솔 목록: `/api/meta.issues`, `/api/meta.issue_rows`
- 감사 표시: `/api/meta.scenario_gate_rows`

`data/issues/*.json` 파일 존재는 승인 근거가 아니다. registry에 없는 issue, `candidate`, 잘못된
registry, 현재 파일과 해시가 다른 항목은 모두 차단된다. `/api/run`은 목록 조회 결과를 신뢰하지
않고 같은 게이트를 다시 실행한다.

## 2. 현재 레거시 정책

`legacy_policy`의 유일한 허용값은 `deny_unless_explicit_legacy_approved`다. 기존 콘솔 시나리오는
자동 승인하지 않는다. 현재 원장의 기존/신규 시나리오는 모두 candidate이며, 따라서 콘솔 실행
목록은 비어 있는 것이 정상이다. 운영자가 과거 재료를 꼭 실행해야 한다면 다음을 모두 명시한다.

1. state를 `legacy_approved`로 둔다.
2. `approved_by`와 `approved_at`을 실제 승인자로 채운다.
3. 미적용 spec/calibration/prior마다 `required:false`와 구체적인 `reason`을 기록한다.
4. UI의 `semantic spec 미적용` 경고를 없애거나 숨기지 않는다.

테스트 픽스처의 `legacy_approved`는 실데이터 승인이 아니며 임시 data root 안에서만 유효하다.

## 3. 정상 승격 절차

1. issue/facts/assignment 세 파일을 고정하고 세 문서의 `issue_id`를 확인한다.
2. facts의 모든 fact ID가 유일하고 assignment의 ID 집합과 정확히 맞는지 확인한다. 미지 ID와
   고아 fact ID가 하나라도 있으면 승격하지 않는다.
3. DetectionSpec을 만들고 `spec.material_sha256`을 현재 facts 파일 SHA-256으로 둔다.
4. 독립 calibration을 만들고 spec/calibration version을 서로 일치시킨다.
5. required prior를 완료한다. registry의 `completed`만으로 충분하지 않으며 facts의 모든
   `prior.score`도 실제 값이어야 한다. 면제는 `required:false,status:exempt,reason` 세 칸이 필요하다.
6. `outcome_policy`를 선택한다.
   - `normative_decision`: 사전 고정된 정오/선택 판정 가능
   - `descriptive_stance_only`: accuracy 요청 금지
7. 현재 바이트의 SHA-256을 registry에 기록한다.
8. 사람 승인 후에만 state를 `console_approved`로 바꾸고 `approved_by`, `approved_at`을 채운다.
9. schema, 기계 게이트, 콘솔 메타를 순서대로 재검증한다.

`pilot_only`와 `confirmatory_frozen`도 실행 가능 state지만 앞 단계 승인과 동결 절차를 건너뛰는
별칭이 아니다. state 문자열만 바꿔도 해시·spec·calibration·prior 게이트는 그대로 적용된다.

## 4. 검증 명령

리포 루트에서 실행한다.

```bash
python -c "import json,jsonschema; from modules import paths; jsonschema.validate(json.loads(paths.scenario_registry().read_text(encoding='utf-8')), json.loads(paths.scenario_registry_schema().read_text(encoding='utf-8'))); print('PASS')"
python -c "from modules import scenario_gate; import json; print(json.dumps([r.to_dict() for r in scenario_gate.registry_results()], ensure_ascii=False, indent=2))"
python -m unittest tests.test_console_scenario_promotion -v
python -m unittest tests.test_console tests.test_console_gates -v
```

현재 registry의 기대 결과는 `approved_count=0`이다. 이는 장애가 아니라 신규 실호출 동결과
명시 승인 정책의 결과다.

## 5. 변조·사고 대응

- material/spec/calibration 파일을 수정했다면 state를 먼저 candidate로 내리고 새 해시와 독립
  검토를 완료한다. 기존 해시를 새 값으로 조용히 덮어 승인 상태를 유지하지 않는다.
- `/api/run`이 `scenario promotion gate blocked` 400을 반환하면 이유를 고친 뒤 다시 검증한다.
  게이트를 우회하는 직접 subprocess 실행을 대안으로 쓰지 않는다.
- `descriptive_stance_only`에 `outcome_metric=accuracy`를 보내지 않는다.
- registry 없는 변종(`/api/variant`가 만든 파일 포함)은 자동 노출되지 않는다. 별도 항목과 승인
  절차가 필요하다.

## 6. 승인 실무 — owner 가 시나리오 하나를 올릴 때 (2026-08-21 추가, 요한)

지위: **확정 — §3 를 owner 시점에서 다시 쓴 것.** 위 절을 바꾸지 않는다. 2026-08-21 v2 네 벌
(throne·award·polar·exile) 을 올리면서 실제로 밟은 순서이고, 다음 시나리오도 이 순서로 간다.

### 6-1. 승인하기 전에 기계가 먼저 말하게 한다

```bash
PYTHONUTF8=1 python -c "from modules import scenario_gate; [print(r.issue_id, r.allowed, r.blocking_reasons) for r in scenario_gate.registry_results()]"
```

`blocking_reasons` 가 `['promotion state not executable: candidate']` **하나만** 남아 있어야 승인 차례다.
다른 게 같이 있으면 그건 사람 승인으로 풀 문제가 아니다 — 아래 표대로 먼저 고친다.

| 남아 있는 이유 | 뜻 | 할 일 |
|---|---|---|
| `registry entry missing` | 원장에 없다 | 항목 추가(§3-1~7). outcome_policy 를 이때 정한다 |
| `facts hash mismatch` / `spec material hash mismatch` | 재료가 바뀐 뒤 해시를 안 따라갔다 | 6-3 사슬 재계산 |
| `spec missing` / `calibration missing` | 의미 계약이 없다 | v2 처럼 DetectionSpec+calibration 한 벌 만들기 (spec-engineer 일) |
| `prior not completed: 'pending'` | 사전지식 프로브 안 돌렸다 | 6-2 — **돈이 나간다**, 승인 안건 |
| `prior completed claim conflicts with material` | 원장은 completed 인데 facts 에 점수가 비었다 | 거짓 표기 — 원장을 pending 으로 되돌리고 프로브 |

### 6-2. prior 프로브 (시나리오당 팩트 수 = 콜 수, 보통 12)

```bash
PYTHONUTF8=1 python 시나리오/probe_prior_new.py
```

`ISSUES` 튜플에 이슈를 더하고 돌린다. `prior_<issue>.json` 이 이미 있는 이슈는 스킵되므로 새 것만 돈다.
상한은 안 돈 이슈의 팩트 수 + 3 으로 자동. 첫 줄에 찍히는 "이번에 돌 이슈 · 호출 상한" 을 보고 예상과
다르면 Ctrl-C. **known 이 하나라도 나오면 그 팩트는 교체 대상**이고 승인으로 못 넘어간다.
돌자마자 원자료(`prior_*.json`, `.partial.jsonl`, facts)부터 커밋한다(규약 8) — 뒤처리는 다음 커밋.

### 6-3. 해시 사슬 재계산 (재료 바이트가 바뀔 때마다 — prior 기입도 포함)

순서가 있다. 앞이 바뀌면 뒤가 전부 바뀐다.

1. `시나리오/facts_*.json` ↔ `data/facts/facts_*.json` 바이트 동일하게(한쪽을 복사).
2. spec 빌더가 재료 해시를 상수로 동결해 둔 시나리오(polar_v2·exile_v2 의 `MATERIAL_SHA256`)는 상수를
   새 해시로 바꾼다 — 빌더가 일부러 거부하게 만든 자리다. 같은 상수를 쓰는 테스트(`tests/test_*_detection_spec.py`)도.
3. spec 빌더 4종 재실행 → spec 의 `material_sha256`·`material_artifacts.facts_sha256` 두 칸만 바뀌어야 한다.
   다른 칸이 바뀌면 빌더나 재료가 의도 밖으로 움직인 것. calibration 은 안 바뀐다.
4. registry: `material.facts_sha256`, `spec.sha256`, (바뀌었으면) `calibration.sha256`, `prior.status`.
5. 검증: `jsonschema` PASS → 6-1 게이트 → 전체 unittest. 프로브 전 상태를 고정한 테스트가 깨지면
   그건 갱신 대상이다(`prior null`·`pending`·구 해시 핀).
6. 체크아웃이 CRLF 여도 해시는 정규화(`modules/content_hash.py`) 라 git blob(LF) 과 같다 — 의심되면
   `git show HEAD:<path>` 바이트로 다시 찍어 본다.

### 6-4. 승인 = 보드 한 줄 + registry 세 칸

보드 결정 로그에 먼저 적는다(정본). 그 다음 registry 항목에:

```
"state": "console_approved",
"approved_by": "<이름> (owner, <날짜> — 보드 결정 로그 <링크/식별>)",
"approved_at": "<ISO 8601, +09:00>"
```

`pilot_only` / `confirmatory_frozen` 은 별칭이 아니다 — 해시·spec·calibration·prior 게이트는 그대로 걸린다.
`legacy_approved` 는 v1 같은 과거 재료를 spec 없이 돌릴 때만, §2 의 네 조건을 다 채우고.

### 6-5. 승인 뒤 확인 두 가지

- 6-1 을 다시 돌려 `allowed=True`, `warnings=[]`.
- `descriptive_stance_only` 시나리오는 `requested_metric="accuracy"` 로 다시 평가해서 **여전히 막히는지** 본다.
  승인이 accuracy 금지를 풀어 주면 안 된다.

### 6-6. 승인을 되돌려야 할 때

재료·spec·calibration 파일을 한 바이트라도 고치면 state 를 먼저 `candidate` 로 내린다(§5). 해시만 새로 찍어
승인 상태를 유지하는 건 금지. 되돌린 사실도 보드에 한 줄.
