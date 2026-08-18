# 후속 실험 실행 가이드 (v1) — 자 세우기 · 셔플 · 스윕

> 지위: 제안 (민옥 트랙). 「실험 재현 가이드」가 완료된 실험을 다시 돌리는 법이라면,
> 이 문서는 **아직 안 한 실험 세 개**를 돌리는 법이다. 왜 하는지는 「질문 지도」 참조.
> 실행 순서: (A) 자 세우기 → (C) 셔플 → (B) 스윕 — (B)의 결론 곡선이 (A)에 의존.

## 0. 공통 절차 — 여섯 단계, 순서 고정

1. **사전등록 커밋**: PREREG_v2(해당 실험 절)와 PROMPTS_v2_draft의 지위를 "사전고정"으로 올려 로컬 커밋. 이게 없으면 러너가 실호출을 거부한다(--allow-v2 관문).
2. **드라이런**: 해당 명령에 `--dry`를 붙여 0콜 리허설. `runs/_dry/`에서 프롬프트 문면이 PROMPTS_v2와 일치하는지 눈으로 확인.
3. **실행**: `--allow-v2`를 붙여 실호출. 체크포인트가 있으니 끊겨도 재실행하면 이어간다.
4. **채점**: `PYTHONUTF8=1 python experiments/memory_structure/judge_solo.py --models <모델>` — 새 런만 채점된다.
5. **분석**: `analyze_solo.py` 실행. (주의: v2 접미사 런과 final_poll 정오 집계는 분석기 확장이 필요하다 — 아래 §4.)
6. **기록**: WORKLOG 한 줄 + 색인 한 줄.

## 1. (A) 자 세우기 — 입장 해제 + 최종 판단 (18런 추정)

질문: 소실이 결론을 실제로 바꾸는가 (앵커 논문의 비어 있는 고리 2).

```
PYTHONUTF8=1 python experiments/memory_structure/run_solo.py \
  --model gpt --arms A --no-stance --final-poll --allow-v2
PYTHONUTF8=1 python experiments/memory_structure/run_solo.py \
  --model gemini-flash --arms A --no-stance --final-poll --allow-v2
```

- 규모: 2모델 × 기억 3단 × 진행 1종(반복) × 반복 3 = 18런. 진행 1종 선택 근거는 PREREG_v2에서 확정할 것(해리가 진행 방식에 0.7↔8.7로 민감하므로 이 선택이 결과를 좌우한다 — 기본 제안은 지시문 효과가 가장 약한 A 반복).
- 콜: full/prev 런 5콜, note 런 8콜 + final_poll 1콜 → 런당 6~9콜, 총 ~130콜.
- 산출: `run_*_ns_rep*.json`의 `final_poll` 필드(원문). 정오는 문자열 대조(정답 무레온), 판정 불능은 사람 판독.

## 2. (C) 셔플 — 사실 순서 역순

질문: 불리해서 죽였나, 앞이라서 죽였나 (발견 ③의 교락 분리).

```
PYTHONUTF8=1 python experiments/memory_structure/run_solo.py \
  --model gpt --facts-reverse --allow-v2
```

- 규모 제안: 본실험과 동일 격자(2모델 × 진행 3 × 기억 3 × 반복 3 = 54런)가 정공법이나, 비용을 줄이려면 비대칭이 관측된 조건만(수첩·직전) 우선 — PREREG_v2에서 확정.
- 판독: favors별 생존 분해(analyze_solo의 B.2 로직)를 역순 런에 적용해 원순서와 대조. 방향 유지 → 입장 효과, 반전 → 위치 효과.

## 3. (B) 스윕 — 수첩 크기 {500, 250, 125, 60}

질문: 어디까지 줄여도 결정이 버티는가.

```
for B in 250 125 60; do
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py \
    --model gpt --arms A --memories note --note-budget $B --no-stance --final-poll --allow-v2
done
```

- 500자 점은 (A)의 note 런이 겸한다(같은 조건). 결론 곡선을 그리려면 스윕도 --no-stance --final-poll로 돌려야 한다 — 입장 고정 스윕은 사실 곡선만 나온다.
- 규모: 2모델 × 예산 3(+기존 500) × 반복 3 = 18런(+겸용 6런).
- 주의: 250자부터 원문 총량(409자)이 물리적으로 안 들어간다. 의역 보존을 세려면 앵커 스캔만으로는 부족하다 — 수첩 원문 사람 판독을 판정 계획에 넣을 것.

## 4. 아직 코드가 없는 것 (정직 목록)

- analyze_solo.py는 v2 접미사 런(b250/rev/ns)을 걸러 별도 집계하는 분기가 없다 — 확장 필요.
- final_poll 정오 자동 대조 스크립트 없음(현재는 원문 저장까지만).
- PREREG_v2 문서 자체가 초안 전(이 가이드의 규모·조건은 전부 "제안").

## 5. 검증된 것 (2026-08-18)

- 기본값 실행은 v1과 **바이트 동일**(드라이런 27런×2파일 대조 통과) — 기존 54런 재현성 무손상.
- b250 문면(250자 이내), 역순 나열(12→1), 무입장(입장 문장 0회 출현), final_poll 문면 — 드라이런 검증 통과.
- 사전등록 전 실호출 차단 관문 동작 확인.

---
*작성 2026-08-18 민옥 트랙 · 코드 변경: run_solo.py v2 손잡이(소유자 트랙 내 변경, 스키마 무변경 — solo_run_v1 유지 + 필드 추가)*
