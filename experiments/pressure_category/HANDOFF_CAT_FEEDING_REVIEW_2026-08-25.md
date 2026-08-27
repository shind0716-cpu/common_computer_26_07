# 캣맘 압박 재료 리뷰 반영 — 다음 주자 handoff

## 한 줄 목표

이 작업은 공동체 12개 원본 중 `community_cat_feeding`을 압박 콘솔용 파생 재료로 만드는 트랙이며, 일반 공용 주차 2/12나 트랙 체커 개편과 섞지 않는다.

## 현재 원격 상태

- PR: https://github.com/shind0716-cpu/common_computer_26_07/pull/38
- 브랜치: `fix/community-cat-feeding-review`
- 커밋: `1d038d7fd149ae6eca415271ac88dec72dfc4bd8`
- base: `master`
- 상태(마지막 확인): `OPEN`, `MERGEABLE`, `CLEAN`, checks 없음
- 자동 머지하지 않음

PR 변경 파일은 정확히 두 개다.

1. `experiments/pressure_category/materials/community_cat_feeding.json`
2. `experiments/scenario_generalization/scenarios/community_living/SCENARIOS_12_V03_DEVELOPMENT.yaml`

## 리뷰 반영 완료

- 옵션을 `현 위치 유지` / `창고 옆으로 이전`으로 단순화
- 팩트 12개를 고유명사 앵커로 교체
- 각 카테고리에 `about_option`을 추가
- 각 카테고리는 현 위치 사실 1개 + 창고 옆 사실 1개
- 창고 옆 관련 사실을 확대
- `CF_F06` 대안 장소 결함 복원
- `CF_F04`는 한 팩트에서만 사용
- f02를 선택 구분 사실로 교체하고 객관 서술 기준으로 통일
- 원본 12개 YAML 전체를 커밋해 `source_ref`를 살아 있는 참조로 만듦

## 검증 증거

### 재료 계약

- `check_materials.py`: PASS
- 팩트 12개
- 카테고리 6개 × 각 2팩트
- 각 카테고리 `about_option`: 두 옵션 정확히 1개씩
- 카테고리 내부 `favors`: 동일 방향 유지
- 고유명사 앵커 12개 고유
- 앵커는 자기 팩트에만 정확히 1회
- `CF_F06` 참조 존재
- `CF_F04` 사용 1회
- 모든 `CF_* source_ref`가 커밋된 YAML의 `fact_id`에 존재

성공 표식:

```text
AD_HOC_CAT_REVIEW_PASS facts=12 paired_options=6x2 unique_named_anchors=12 live_source_refs=yes CF_F06=yes CF_F04_count=1
```

### 실행 배관

- C0/C1/C2 × A/B, rep6 총 6판 드라이런 PASS
- 판당 8콜 조립
- 실호출 0
- 실제 r0 프롬프트와 C1/C2 옵션 치환 직접 검토

### 원본

```text
V03_12_SCENARIO_VERIFICATION=PASS
ERRORS=none
COUNTS scenarios=12 unique_topics=12 facts=120 unique_facts=120 variants=36 profiles=3
```

## 다음 주자의 우선 작업

1. PR #38의 실제 diff를 다시 읽는다.
2. 특히 f04를 의미 검수한다.
   - 창고 옆 자체 결함이 아니라, 창고 옆을 못 쓸 때 남는 이전 후보의 빗물 고임을 말한다.
   - `about_option=창고 옆으로 이전`로 묶는 것이 과도한지 판단한다.
3. 고유명사 앵커가 지나치게 인공적이거나 가치 방향을 암시하지 않는지 검수한다.
4. 문제가 없으면 사용자에게 머지 여부를 물어본다. 사용자 승인 없이 자동 머지하지 않는다.
5. 머지 후 `master`의 두 파일 blob과 PR merge 상태를 다시 읽어 검증한다.

## 별건 — 이 PR에서 수정하지 말 것

리뷰에서 발견된 다음 두 구멍은 트랙 수준 별건이다.

- `check_materials.py`가 `about_option`의 옵션별 1팩트를 강제하지 않음
- `status`가 실호출 관문에 연결되지 않음

별도 작업으로 다룰 경우 기존 재료 전체 회귀검사가 필요하다. PR #38에 몰래 섞지 않는다.

## 로컬 작업 트리 주의

현재 기본 작업 트리는 다른 실험 변경과 미추적 파일이 많다. 현재 브랜치를 그대로 push하지 말 것. 원격 작업은 `origin/master` 기반 별도 worktree/브랜치에서 수행한다.

로컬에는 다음이 미추적 상태로도 존재한다.

- 수정된 `community_cat_feeding.json`
- 아직 원격에 올리지 않은 `general_shared_parking.json`
- 원본 12개 YAML
- 드라이런 산출물

## Identity ledger

| 주체 | 역할 | 주장 가능한 범위 |
|---|---|---|
| Hermes/호메로스 | 구현·검증·PR 작성 | 위 도구 출력으로 확인한 파일·검사·드라이런·원격 상태 |
| 감사 리뷰어 | 독립 리뷰 | 사용자가 전달한 리뷰 문면과 요구사항 |
| 다음 주자 | 후속 의미 검수·머지 판단 | 새로 직접 읽고 실행해 확인한 증거만 |

## Append-only status

- 2026-08-25 Hermes: 리뷰 반영, 집중 검증, 6조건 드라이런, 원본 YAML 검증, fix PR #38 생성 완료. 실호출 0. 자동 머지 안 함.
- 다음 주자: 이 아래에 diff 재검수 결과, f04 판단, 사용자 머지 결정, 원격 검증을 append할 것.
