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
