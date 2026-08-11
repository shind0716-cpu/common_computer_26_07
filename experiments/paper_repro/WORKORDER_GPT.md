# 작업 지시서 — 저자 충실 계층 (extractor + perspective 배분기)

지위: **작업 지시서** (요한 → 로컬 GPT 워커, 2026-08-10). 이 문서는 자기완결이다 —
대화 맥락 없이 이 문서와 여기 링크된 문서만으로 작업한다. 결정의 정본은 노션 보드이며,
이 지시서의 결정 사항은 이미 확정된 것의 전달이다. **재협상 대상이 아니다.**

## 0. 읽기 순서 (착수 전 필수)

1. `CLAUDE.md` — 리포 절대 규칙 (append-only · 경로는 paths.py · validate 통과 전 미완 · LLM 원문 보존)
2. `experiments/paper_repro/README.md` — 트랙 현황 · 투트랙 경계 · **브리지 계약 4항**
3. `docs/proposals/PAPER_REPRO_HANDOFF.md` — 기술 사양. **§12(맨 끝)까지 읽을 것** — 결정 반영이 아래에 append 돼 있다
4. `SCHEMA.md` — 파일 계약. **끝까지** (제목은 v0.2, 본문 뒤에 v0.3·§1′ 확정분)
5. `experiments/paper_repro/probe_extract.py` — **네가 계승할 패턴의 실물** (검증 완료 코드)

## 1. 네 몫 (이것만)

`experiments/paper_repro/` 안에 러너 2개를 짓는다. `modules/` 승격은 네 소관이 아니다.

| 러너 | 저자 원본 | 입력 | 산출 |
|---|---|---|---|
| `extract_facts.py` | `facts.py` 3단계 **그대로** | `data/issues/issue_ethics_NNNN.json` (200건, 완비) | `data/facts/facts_issue_ethics_NNNN.json` + 호출 원문 jsonl |
| `assign_perspective.py` | `perspective.py` **그대로** | 위 facts | `data/assignments/assignment_issue_ethics_NNNN.json` + 호출 원문 jsonl |

저자 코드 위치: `D:\ms\DelibTrace-main` (환경변수 `DELIBTRACE_DIR`로 재지정 가능).
프롬프트는 `modules.authors_prompts.load(이름)` 으로 **원본 직독** — 리포에 복사 금지.

## 2. 고정 조건 (변경 금지 — 이미 확정)

- 모델 **gpt-5 · temperature 0 · n=1** (HANDOFF §12-4. `llm.obtain_response` 사용)
- `facts_select` 의 `<===question===>` = **issue 문서의 `question` 필드** (loader가 이미
  항목별 영어 제목을 명시 주입했다. 다른 문자열을 만들지 마라)
- 출력 상한: 러너 안에서만 `llm.MAX_TOKENS = 8192` (편차 P-1. **`llm.py` 파일은 무수정** —
  probe_extract.py 46~55행이 정확한 실물)
- JSON 파싱은 저자 `obtain_json` 계승 (probe_extract.py 85~90행), 실패 시 원문 보존
- 추출 후 **refined 5개 미만 항목은 제외 표시** (삭제 아님 — 파일은 만들되 manifest에 제외 기록)

## 3. 브리지 계약 (하류가 이것에 의존한다 — 어기면 접합 계층 전체가 무효)

정본은 README 「브리지 계약」. 요약:

1. `facts[]` **배열 순서 = 저자 위치 인덱스**, 각 팩트에 `origin_index`(0-based) 병기
2. `fact_id` = `fact_ethics_NNNN_MM` (MM = origin_index+1, 2자리) — 예: `issue_ethics_0036`
   의 3번째 refined 팩트 → `fact_ethics_0036_03`
3. `critical` ← 저자 `facts_select` 산출(important 여부). `tags` = `[]` (§7 임시 처리)
4. 관점은 **정확히 4개**, 같은 관점의 pro/con 쌍은 `assigned_fact_ids` **완전 동일**,
   저자 산출(인덱스 배열)은 `perspective_sets.sets` 에 원형 보존, `seed` = 20260810

**형태의 정답지가 이미 있다**: `fixtures/data/facts/facts_issue_repro_fx.json` ·
`fixtures/data/assignments/assignment_issue_repro_fx.json`. 네 산출물은 이 픽스처와
같은 구조여야 한다. 필드를 빼거나 더하지 마라.

## 4. 안전장치 (필수 — probe_extract.py 패턴 그대로)

- **전역 호출 상한** 인자(`--max-calls`), 초과 시 즉시 예외 (조용히 넘기기 금지)
- **호출 단위 체크포인트** — tag 키 jsonl, 재실행 시 이어받기 (probe 의 `call()` 실물)
- **`--dry`(0콜) 완주 리허설을 실호출보다 먼저** 돌리고, 지시자(요한)에게 dry 결과를
  보고한 뒤 실호출 승인을 받는다. **승인 없이 실호출 금지.** 추출은 3콜/건 × 200 = 600콜,
  배분 1콜/건 × 200 = 200콜이 예산이다
- LLM 응답 **원문 전량 보존** (규약 5 — 요약 저장이 이 프로젝트가 연구하는 실패다)
- 산출 전건 `python -m modules.validate <파일>` 통과 (규약 3 — 러너가 직접 돌릴 것)
- 콘솔 인코딩: 실행은 `PYTHONUTF8=1` 접두 필수 (cp949 트레이스백 사망 방지)

## 5. 금지 (걸리면 작업 무효)

- `modules/llm.py` · `judge.py` · `debate_engine.py` (동범 담당) /
  `assignment_gen.py` · `tools/console/` (민옥 담당) — **읽기만, 수정 금지**
- `experiments/paper_repro/` **밖**의 모든 파일 수정 (WORKLOG 제외, 아래 §6)
- 기존 `experiments/*` 다른 폴더 수정 (코드가 아니라 기록이다)
- 저자 프롬프트 복사 · 3단계를 2단계로 축소 · 관점 수 4 변경 · 결과 보고 지표 변경
- SCHEMA·계약 문서 수정 (문제 발견 시 고치지 말고 보고만)
- 발화·판정·news 트랙 착수 (이번 범위 밖)

## 6. 완료 기준 (HANDOFF §10 그대로)

1. 표본 200건의 `facts/`·`assignments/` 생성, **전건 validate 통과**
2. 관점 배분이 저자 `check_available` 규칙 통과, 위반·건너뜀 건수 보고
3. **관점 쌍 전부에서 pro/con 의 `assigned_fact_ids` 동일**함을 수치로 확인·보고
4. 호출 원문 jsonl 전량 + refined<5 제외 목록 manifest 기록
5. `WORKLOG.md` **맨 끝에 한 줄 append** (기존 줄 무수정): `날짜 | 요한(GPT-sol) | 한 일 | 다음`
6. 요한에게 보고: 완료 수치(§10 각 항) + 실측하며 알게 된 것 (예상과 달랐던 것 우선)

## 7. 막히면

스스로 우회하지 말고 **멈추고 보고한다.** 특히: validate 실패를 스키마 탓으로 판단한 경우
(스키마를 고치지 말 것), 저자 코드와 사양이 어긋나 보이는 경우, 호출 상한 도달.

---

# §8. 수정 지시 + 역리뷰 (2026-08-10 요한 리뷰 반영 — append)

리뷰 결과: 테스트 7종·dry 2종 재현 통과, 지시서 준수 확인. 아래 3건 수정 후 dry 재보고.

## 수정 3건

**F-1 (차단급): `extract_facts.build_facts_doc` 의 bool 강제.** 실측 확증 — 프로브
`probe/probe_result.json` 의 gpt-5 `facts_select` 산출은 **int 0/1 배열**이다
(`[1,1,…,0]`). 현재 코드는 `isinstance(x, bool)` 강제라 실호출 첫 건에서 ValueError.
수정: 원소가 bool 또는 0/1 int 면 허용하고 `bool(x)` 로 변환해 저장(계약의
critical(bool) 유지). 그 외 타입은 지금처럼 거부. **회귀 테스트 추가**: 프로브 실물
배열(`[1,…,0]`)을 넣어 통과하는 테스트.

**F-2 (중간): refined<5 제외가 배분기로 전파 안 됨.** 사양 §12-4 — 추출 후 refined
5개 미만 항목은 표본 제외다. `assign_perspective` 가 `sample_manifest` 만 읽는다.
수정: `facts_manifest.json` 의 `excluded_refined_lt5` 를 읽어 해당 issue 를 건너뛰고
`skipped` 에 `reason: "refined_lt5"` 로 기록. facts_manifest 부재 시 즉시 에러
(순서 위반을 조용히 넘기지 말 것).

**F-3 (경미): dry 의 validate 실패 사유 소실.** `redirect_stdout` 이 `[FAIL]` 출력을
삼킨다. 수정: StringIO 내용을 잡아 실패 시 stderr 로 재출력하거나, 예외 메시지에 포함.

## 역리뷰 1건 (상호 보완 — 내 산출물을 네가 검증)

접합 계층 산출물을 **실데이터 기준으로** 리뷰하라: `load_issues.py` · `fixtures/data/` 3종 ·
`README.md` 브리지 계약. 특히 ① `to_issue_doc` 매핑이 원본 필드를 하나라도 버리는지
(규약 8) ② 픽스처가 네 라이브 산출과 어긋날 형태 요소가 있는지 ③ 순번 issue_id 규칙의
구멍. 발견은 **고치지 말고 목록으로 보고**(접합 계층은 내 담당 — §5 소유권 원칙의 역방향 적용).

## 완료 보고

수정 3건 diff 요약 + 테스트(기존 7 + F-1 회귀) 결과 + dry 2종 재실행 수치 + 역리뷰 목록.
실호출은 여전히 승인 대기.

---

# §9. 트랜치 실행 절차 (2026-08-10 요한 — 예산 절약 조정, append)

§8 완료 확인됨(수정 3건 검증 통과·역리뷰 접수, 요한 8/10). **§4의 800콜 예산은 폐기**하고
아래 트랜치로 대체한다. 코드 수정은 없다 — manifest 가 20건으로 재생성됐고(같은 시드의
층화 접두 성질로 200건의 부분집합, issue_id 불변), 러너는 manifest 를 따라가면 된다.

## 실행 전 확인

- 요한이 **이 실험 전용 OpenAI project 키**로 `.env` 의 `OPENAI_API_KEY` 를 교체했는지
  확인받고 시작하라 (비용 격리 — 대시보드에서 트랜치별 실측). 키 값 자체를 다루지 마라.
- 예산: **1차 트랜치 총 80콜** (추출 20건×3=60 + 배분 20). `--max-calls` 는
  추출 70·배분 25 로 걸어라(여유분 포함, 초과는 예외로 죽는 게 정상).

## 1차 트랜치 (승인됨)

```
PYTHONUTF8=1 python experiments/paper_repro/extract_facts.py --live --max-calls 70
PYTHONUTF8=1 python experiments/paper_repro/assign_perspective.py --live --max-calls 25
```

완료 보고(§6 형식)에 추가로: **항목별 refined 팩트 수·critical 비율 분포**(D1 —
비율이 1.0 근처에 몰리면 관점 동질화 신호라 표본 규칙 재검토 대상이다), 대시보드
실측 비용(콜당·건당).

## 이후 트랜치 (별도 승인 전 실행 금지)

- 요한이 loader 를 더 큰 --n 으로 재실행해 manifest 를 확장하면, 같은 명령을 다시
  돌리면 된다 — 체크포인트가 완료분을 캐시로 건너뛴다(추가 지출 없음).
- 확장 n 은 파일럿(발화·판정)의 FAR 표준편차 실측 후 결정된다(사양 §6-3).

---

# §10. 완성도 리뷰 반영 — 수정 1건 + 공유 2건 (2026-08-10 밤, 요한 리뷰 · append)

1차 트랜치(79콜)와 1건 계기 교정(208콜)의 실측 리뷰 결과다. 실호출 없음 — 코드 수정만.

## 수정 E-1 (extract_facts.py — 네 파일)

**파싱 실패 1건이 전체 실행을 중단시킨다.** `_require_list` 가 raise 하면 나머지 항목이
전부 막힌다(라이브 20건에선 실측 0건 — 예방 수정이다). 수정:
- 파싱 실패 항목은 **건너뛰고 계속** 진행. `facts_manifest.json` 에
  `failed_parse: [{issue_id, stage, tag}]` 로 기록(조용히 누락 금지).
- 실패 항목의 raw 는 이미 체크포인트에 보존되므로 재실행 시 캐시에서 재파싱 시도됨 —
  이 동작 유지.
- **회귀 테스트**: 파싱 불가 raw 를 캐시에 심어 두 항목 중 하나만 실패시키고,
  나머지 항목이 정상 산출되는지 + manifest 기록을 확인.
- 배분기(assign_perspective.py)는 수정 불필요 — check_available/invalid_index skip 이
  이미 같은 역할을 한다.

## 공유 (수정 금지 — 정보만)

- **A-1 (좌석 셔플 고정)**: 한 yaml 로 여러 이슈를 돌리면 엔진 seed 가 고정이라 전 이슈가
  같은 좌석 순열이 된다(저자는 이슈별 상이). 확장 시 러너(접합 계층)가 이슈별 seed 를
  유도해 풀 예정 — 엔진·config 는 건드리지 않는다. 네 파일과 무관하나 알아둘 것.
- **S3 강독/약독**: 요한 확정 대기. 오딧 코드(critical_missing)는 그대로 둘 것.

## 완료 보고

E-1 diff 요약 + 회귀 테스트 결과 + 기존 테스트 전건 통과 확인. 실호출 금지 유지.

# §11. recall probe 이원 설계·구현 — 전체 회고 + 500자 요약 저장소 (2026-08-10 요한 지시, append)

목적: 비교 실험(0543·0248·0262)에서 ① 소실 vs 침묵 구분 ② 타 에이전트 경유 진입의
자기 보고 관측 ③ **예산 압축이 무엇을 버리는지의 직접 관측**(같은 입력의 두 압축 수준).
저자 코드에 없는 추가 요소다 — 편차 P-9로 등재 예정. **토론 종료 후 실행되며 어떤
출력도 토론에 되돌아가지 않는다(관측·비개입 격리 — 비교 성립 조건).**

## 사양

- **팔 1 `probe_full` (B형 전체 회고)**: 무예산. 출력 = 팩트별
  `{statement(자기 말), source: "assigned"|"heard"|"inferred", heard_from: agent_id|null}`
  JSON 배열. 문안은 수첩 지시 철학 계승 — "요약해라"가 아니라 "네가 아는 것을 적어라".
- **팔 2 `probe_note` (예산 요약 저장소)**: 기존 수첩 문안·`note_slot.apply_budget`(500자)
  1회분 재사용. 출처 귀속 요구 없음(예산을 귀속 표기가 먹으면 안 된다).
- 입력 = 그 에이전트의 마지막 라운드 시점 창(rolling 재조립). 두 팔은 **같은 입력으로
  독립 호출** — 팔 간 참조 금지.
- 기록: 원문 전량 raw_calls 체크포인트(**CallCheckpoint 계승 — 좌표 지문 필수**),
  매핑 후 `judgment.recall_probe[]` 등재(팔 구분 키 포함 — 계약 선택 필드라 스키마 변경 0,
  구분 키 설계는 제안으로 올릴 것).
- 자기 보고(source 귀속)의 지위 = **관찰**. 결과 변수 아님. 저자 축 판정과 교차 대조
  가능한 좌표로 저장할 것.

## 산출 기대물

프롬프트 문안(팔별 2안 이상) · probe 러너(단독 실행형, `--dry` 0콜 완주) · 파서 ·
테스트. 엔진(`debate_engine.py`) 무수정 — 러너 층에서만(⑤′ stance 전례).

## 관문 (MUTUAL_REVIEW 정본 G1~G5 — 의무)

G1 신규 콜 표: probe 8발화자×3건×2팔=48콜(상한 ×1.2=58) — 매핑 판정은 별도 승인.
G2 재사용 주장마다 강제 코드 줄 번호. G3 temp>0 산출물 재생성 자천 차단.
G4 프레임 경계 매핑은 양끝 정의 원문 병기. G5 첫 수치는 원문 몇 건 소독 후에만 보고.

상호 리뷰: Claude 검수 → 요한 승인 후 실행. 실호출은 별도 승인 관문.
