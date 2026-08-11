# 비교 실험 사전고정 — 실험 조건 정본 + 판정 규칙 (2026-08-11)

지위: **사전고정** (실행 전 커밋 — 고정 이후 변경은 append 전용). 이 문서가 비교 실험
조건의 정본이다. 실행 절차·환경은 `COMPARE_SETUP.md`, probe 상세는 `WORKORDER_GPT.md §11`,
좌표 파일은 `configs/compare_v1.yaml` — 어긋나면 이 문서가 이기고, 어긋남 발견 시 수정
대신 여기 append 로 기록한다.

## 0. 한 문단 (처음 읽는 사람용)

같은 논문 데이터·같은 팩트·같은 배분 위에서, **저자(논문) 코드**와 **우리 파이프라인**으로
각각 토론을 돌려 "팩트가 얼마나 살아남았는지"가 비슷하게 나오는지 확인한다. 비슷하면
우리 파이프라인이 논문의 측정을 재현하고 있다는 근거가 되고, 다르면 어느 단계에서
갈라지는지가 다음 질문이 된다. 결과가 어떻게 나오든 그대로 보고한다.

## 1. 실험 조건 — 두 판의 전 좌표

### 1-1. 양쪽에 공통 (고정 상수)

| 좌표 | 값 | 근거·출처 |
|---|---|---|
| 데이터 | issue_ethics_**0543 · 0248 · 0262** (팩트 15·14·11) | 요한 원문 직접 확인 후 채택 8/10 (선정 시트 전 후보 19건) |
| 팩트·배분 | **공통 주입** — 1차 트랜치 추출물 + 배분표 (`compare/author_inputs/` sha 지문 3종) | 비교 단위 (ii) 팩트 고정 — 요한 8/11. 추출 사양은 양쪽 동일(저자 프롬프트 직독·gpt-5·temp 0)이라 재추출 실익 없음 |
| 발화 모델 | gpt-4.1 | 저자 `discussion.py` 상수 |
| 발화 온도 | **1.2** | 저자 상수 — 요한 확정 8/11. ⚠ pilot1(1.0)과 직접 비교 불가(온도 상이 명시 의무) |
| 라운드 | 3 (+초기 발화) · 발화자 8 (4관점×찬반) · 구조 full | 저자 상수 |
| 판정 축 | 저자 축 (발화×팩트목록 · gpt-5 · temp 0 · n=1) | 축 확정 8/10 (논문 데이터 한정, 보드 결정 로그) |
| 키·환경 | 팀 공유 OpenAI 키 · `PYTHONUTF8=1` | COMPARE_SETUP §4 |

### 1-2. 판별 차이 (이것만 다르고, 이 차이가 곧 비교 대상이다)

| | 저자 판 | 우리 판 |
|---|---|---|
| 토론 실행 | `DelibTrace-main/discussion.py` (무수정, cwd=저자 리포) | `debate_engine` (rehearse_splice `--live --in-place --config compare_v1.yaml`) |
| 판정 실행 | `evaluation.py` (evaluate_fact + evaluate_stance) | 저자 축 계기 + stance 계기 (rehearse ⑤·⑤′) |
| 좌석 셔플 | 저자 `discussion_preprocess()` seed 20260601 | 엔진 seating seed 42 | 
| 기록 | 저자 JSON (원문 즉시 회수·커밋) | debate jsonl (run_meta·prompt_assembly 전량) |
| 추가 관측 | 없음 | recall probe 2팔 (토론 종료 후·비개입 — §11) |

좌석 순서는 양쪽 다 자기 절차의 결정론 값이며 서로 다르다 — **통제하지 않는다**(저자
절차 무수정이 우선). 이 차이는 해석 시 명시한다.

### 1-3. 편차 원장 (이 판 기준)

| # | 편차 | 방향 |
|---|---|---|
| P-1 | 우리 판 발화·판정 콜에 max_tokens 8192 (저자는 미전송) | 기존 등재 유지 |
| P-7 | 발화 온도 — **이 판에 한해 해소**(1.2 저자 정합). pilot1 등 기존 판은 1.0 그대로 | 이 판 한정 |
| P-9 | recall probe 2팔 — 저자에 없는 추가 관측. 토론 종료 후 실행·출력이 토론에 미유입 | 신규 (§11) |

## 2. 산출물 자리 (전부 생성 즉시 커밋 — 7/21 교훈)

```
compare/author_inputs/        주입 파일 3종 + mapping_manifest (완료·커밋됨)
compare/authors_run/          저자 판 산출 전량 회수분 (initial/discussion/evaluation)
data/debates|judgments/…compare1  우리 판 (run_id: compare1_{issue})
data/raw_calls/…compare1      우리 판 콜 원장 (좌표 지문 포함)
compare/RESULT.md             집계 — 이 문서의 §3 규칙대로만 작성
```

## 3. 판정 규칙 — 결과를 보기 전에 고정한다

**이 실험은 n=3 이고 발화 온도 1.2(확률적)다. 따라서 "성공/실패 판정"이 아니라
"기술(記述) 규칙"을 고정한다** — 가설 언어 금지, 수치는 아래 형식으로만 보고.

1. **주 대조표**: 이슈별 × stage별 far_system·far_critical 을 저자 판/우리 판 나란히.
   분모가 같으므로(팩트 고정) **절대값 직접 비교**가 성립한다.
2. **구분 가능성의 경계 — 1팩트 규칙**: 판정 단위가 팩트 1개이므로, stage FAR 차이가
   **1/n_facts 이하**(팩트 1개분)이면 "구분 불가"로 기술한다. 초과 차이는 "차이 관찰"로
   기술하되, **해당 stage 의 발화·판정 원문을 판독한 뒤에만**(G5) 원인 후보를 적는다.
3. **셀 수준 병행**: 팩트×stage 그리드의 판정 일치율(mentioned/unmentioned)을 이슈별로
   병기 — FAR 이 우연히 같아도 셀이 다르면 드러난다(판정 축 대조 0.979/0.479 의 교훈).
4. **stance·probe 는 관찰 지위** — 결과 변수가 아니다. stance 유지율은 라운드별 개수로
   나란히, probe 는 팔 간 원문 대조(사람 읽기·§5-2 자동 대조 금지). 여기서 무엇이
   보여도 이 실험의 결론에 넣지 않고 다음 실험의 재료로만 적는다.
5. **G5**: 극단값(0.0/1.0)·전건 일치·전건 불일치는 원문 2건 이상 확인 후에만 보고.
6. **중단 시**: 부분 완주 데이터는 그 사실과 함께 보고하고 완주분만 대조표에 넣는다
   (부재≠소실 — 미완주 이슈를 0 이나 실패로 세지 않는다).

## 4. G1 — 신규 콜 표 (상한 = 예상 ×1.2)

| 블록 | 예상 | 상한 |
|---|---|---|
| 저자 판: 발화 96 + evaluate_fact 96 + evaluate_stance 96 | 288 | 346 |
| 우리 판: 발화 96 + 저자 축 96 + stance 96 | 288 | 346 |
| probe 2팔 (8×3×2) | 48 | 58 |
| probe 매핑 판정 (별도 승인 관문) | 48 | 58 |
| **합계** | **672** | **808** |

예상 비용 ≈ **$7** (콜당 $0.01 실측 기준 8/11). 저자 코드에는 상한 장치가 없다 —
3건짜리 입력 파일이 상한을 대신하고, 단계별로 나눠 실행·감시한다(COMPARE_SETUP §3).

## 5. 실행 순서 (관문 통과 순)

① 이 문서 커밋(사전고정) → ② GPT-sol §11 회신·검수·승인(probe) → ③ **실호출 승인(요한)**
→ ④ 저자 판 실행(단계별)·산출 즉시 회수 → ⑤ 우리 판 실행(체크포인트) → ⑥ probe →
⑦ G2~G5 통과 → ⑧ RESULT.md (§3 규칙만으로) → ⑨ 검토 문서(멘토·퍼실용, 수요일 공유)

---

## 6. 정정 append — 역리뷰 반영 (2026-08-11, GPT-sol §13 차단급 2건)

**B-1 (실행 경로)**: §5 의 우리 판 실행 경로를 `rehearse_splice.py --live --author-only
--config configs/compare_v2.yaml` 로 정정한다. 종전 경로는 사전고정에 없는 ② 우리 축
판정 160콜(중간 판 — 정본 judge 사양도 저자 축도 아님)을 실행했다. author-only 는
②~④를 건너뛰고 ①발화+⑤저자 축+⑤′stance 만 실행하며, **이슈별 상한 116**(계획
96×1.2)을 러너가 강제한다(dry 실측: 3건 각 96, 실호출 0). config 는 v2(소비 키만 —
v1 은 보존·미사용).

**B-2 (G1 콜 표 정정)**: §4 의 probe 행(48/58)은 §12 시계열 확정 전 수치다. 정본 갱신:

| 블록 | 예상 | 상한 |
|---|---|---|
| 저자 판 (발화 96 + evaluate_fact 96 + evaluate_stance 96) | 288 | 346 |
| 우리 판 author-only (발화 96 + 저자 축 96 + stance 96) | 288 | 346 (116/건) |
| probe (full 8×4시점×3 + note 8×1×3) | 120 | 144 |
| **합계 (매핑 판정 제외)** | **696** | **836** |
| probe 매핑 판정 | **TBD** — §12 시계열 행 확장으로 종전 48콜 근거 소멸, 설계·승인 후 새 G1 | — |

**M-1 (저자 판 명령열)**: §5 실행 순서의 저자 판 단계를 다음으로 구체화한다 —
(ii) 주입으로 facts.py·perspective.py 는 **실행하지 않는다**(산출물 주입됨).
cwd=DelibTrace-main 에서: ① `python discussion.py --dataset scruples --model gpt
--structure full` ② `python evaluation.py --dataset scruples --model gpt --structure
initial` ③ `python evaluation.py --dataset scruples --model gpt --structure full`
(4시점 판정은 initial·full 두 번 실행이 필요 — evaluation.py:63-78). 각 단계 후 산출물
수 확인, 재개 전 manifest sha·index 0/1/2 재대조(저자 코드 재개는 길이 기반 —
좌표 지문 없음).

---

## 7. 정정 append — 재검수(C-1~C-4·R-1·M-2) 반영: 우리 판 실행기 교체 (2026-08-11)

**경로 정정**: §6 B-1 의 `rehearse_splice --author-only` 경로는 재검수에서 차단급 4건
(C-1 산출물 쓰기 실패·C-2 원자료 자동 삭제·C-3 극단값 폐기·C-4 체크포인트 이슈 미구분)
+ 회귀 1건(R-1)이 확인되어 폐기한다. 우리 판 실행기는 **`compare_ours.py` 신설**
(비교 실험 전용 — 리허설 러너 편집 중단, 요한 방향 결정 8/11). rehearse_splice 는
리허설 지위로 복원(--author-only 제거·R-1 해소)했다. 실행 계획·좌표는 변경 없음:
①발화 + ⑤저자 축 + ⑤′stance = 96콜/건, config v2, run_id 는 `compare2_{issue}`
(v2 config 의 새 run identity — 재검수 C-2 수용 기준).

**실행 명령 정본 (복사 가능 전문 — C-2 수용 기준)**: cwd = 리포 루트.

계획 확인(0콜·무기록 — 실행 전 의무):
```
PYTHONUTF8=1 python experiments/paper_repro/compare_ours.py --issue issue_ethics_0543 --run-id compare2_0543 --config experiments/paper_repro/configs/compare_v2.yaml --source-data experiments/paper_repro/data
```
실호출(요한 승인 후 · 이슈별 1회, 0543 → 0248 → 0262 순):
```
PYTHONUTF8=1 python experiments/paper_repro/compare_ours.py --issue issue_ethics_0543 --run-id compare2_0543 --config experiments/paper_repro/configs/compare_v2.yaml --source-data experiments/paper_repro/data --live --max-calls 116
```
```
PYTHONUTF8=1 python experiments/paper_repro/compare_ours.py --issue issue_ethics_0248 --run-id compare2_0248 --config experiments/paper_repro/configs/compare_v2.yaml --source-data experiments/paper_repro/data --live --max-calls 116
```
```
PYTHONUTF8=1 python experiments/paper_repro/compare_ours.py --issue issue_ethics_0262 --run-id compare2_0262 --config experiments/paper_repro/configs/compare_v2.yaml --source-data experiments/paper_repro/data --live --max-calls 116
```
러너는 임시 디렉터리·사본 없이 `--source-data` 에 직접 산출한다(자동 삭제 경로 부재).
계획 모드가 실행 전 출력 경로 6종과 기존 체크포인트 행 수를 열거한다. 재개 시 debate 는
config 지문, 체크포인트 행은 전 좌표(issue·run·model·temp·n·axis·prompt_ver·
prompt_sha256·facts_sha256·config_sha256) 일치 시에만 재사용된다(C-4).

**M-2 확정 — 승인 경계는 블록 상한 346** (`ceil(288×1.2)`, §4·§6 표의 우리 판 블록 그대로).
이슈별 116 은 보조 상한이다. 강제 장치: append 전용 콜 원장
`data/raw_calls/compare_ours_call_ledger.jsonl` (행 1줄 = 예약 1콜, 프로세스 간 공유) —
매 콜 예약이 호출보다 먼저이며 원장 346 도달 시 API 호출 전 즉사, 실행 전 사전 검사
(원장 잔액 + 계획 > 346 즉사)도 수행한다. 이로써 "116×3=348 우회"는 성립하지 않는다.

**계획 실측 (2026-08-11 · 실호출 0)**: 3건 각각 `발화 32 + 저자 축 32 + stance 32 = 96
(이슈 상한 116)` · 블록 원장 0/346 → 실행 후 96/346 예상 · 기록 0. G1 합계는 §6 정본
(696/상한 836, 매핑 TBD) 변경 없음.

---

## 8. 정정 append — 재재검수(C-5~C-8) 반영: 상한 의미론 확정·트랜치 실행 (2026-08-11)

**C-5 방침 (요한 동의 8/11)**: **승인 경계 = 논리 콜**(질문 수 — §6 정본 696/836 의 단위,
비용 산술과 동일 단위). llm 내부 HTTP 재시도(최대 5회)는 **별도 전송 시도 퓨즈**로
강제한다: 전송 원장 `data/raw_calls/compare_ours_attempt_ledger.jsonl` 에 시도마다 1행
기록(계기판 — 사후 "재시도 몇 회"를 사실로 보고), 상한 = 논리의 2배(**이슈 232 ·
블록 692**). 정상 시 논리 1=전송 1 이라 이 퓨즈는 보이지 않고, 재시도 폭주 시에만
실행을 중단한다(SystemExit — llm 재시도 루프가 삼킬 수 없음). llm.py 는 무수정(동범
소관) — 러너가 공급자 전송 함수를 감싼다.

**C-6**: 이슈별 상한 116 은 **원장 누적 기준의 지속 상한**이다 — 프로세스 재시작으로
초기화되지 않으며, `원장 누적 + 계획 > 116` 이면 첫 호출 전에 거부한다.

**C-7**: live 는 **단일 실행만** — OS 파일 잠금(`raw_calls/compare_ours.lock`, 프로세스
사망 시 자동 해제)으로 두 번째 live 를 시작 전에 거부하고, 이슈 3건은 **한 프로세스가
직렬 실행**(트랜치)한다. 유일 기록자 전제가 성립해 원장 경쟁 자체가 없다.

**C-8**: debate 재사용은 config 지문만이 아니라 **입력 전부의 지문** —
issue·facts·assignment 파일 sha256 + debate_model·temperature·prompt_ver — 을 debate
최초 생성 직전 manifest(`raw_calls/compare_manifest_{issue}_{run}.json`)로 고정하고,
한 바이트라도 다르면 0콜로 거부한다(debate 존재 + manifest 부재도 거부 — 부재≠일치).
저자 축·stance 체크포인트 행은 debate 파일 sha256 에도 묶인다(좌표 11종).

**실행 명령 정본 (§7 의 이슈별 3명령을 대체 — 트랜치 1명령)**: cwd = 리포 루트.

계획 확인(0콜·무기록 — 실행 전 의무):
```
PYTHONUTF8=1 python experiments/paper_repro/compare_ours.py --issues issue_ethics_0543,issue_ethics_0248,issue_ethics_0262 --run-prefix compare2 --config experiments/paper_repro/configs/compare_v2.yaml --source-data experiments/paper_repro/data
```
실호출(요한 승인 후 · 1명령이 3건 직렬):
```
PYTHONUTF8=1 python experiments/paper_repro/compare_ours.py --issues issue_ethics_0543,issue_ethics_0248,issue_ethics_0262 --run-prefix compare2 --config experiments/paper_repro/configs/compare_v2.yaml --source-data experiments/paper_repro/data --live --max-calls 116
```
(run_id 는 `compare2_{끝자리}` 로 유도 — §7 의 compare2_0543/0248/0262 와 동일.
`--max-calls` 는 이슈별 프로세스 상한이며 지속 상한 116·블록 346 은 원장이 별도 강제.)

**계획 실측 (2026-08-11 · 실호출 0)**: 트랜치 3건 직렬 각 96 = **합계 288** · 블록 원장
0/346 → 288/346 · 전송 계기판 0/692 · manifest 통과 · 기록 0. G1 합계는 §6 정본
(696/상한 836, 매핑 TBD) 변경 없음.

---

## 9. 지위 재분류 append — 탐색적 파일럿 확정·수정-재검수 루프 종료 (2026-08-11 요한 결정)

**결정 (요한)**: 이 실험의 목적은 *논문 파이프라인과 우리 파이프라인을 비교하면서 압축
회고 프로브·전체 기억 수첩에서 후속 검증 가치가 있는 지표·가설을 발굴하는 것*이지,
이번 1회 실행으로 확정적 재현 결론을 내는 것이 아니다. 따라서 이 판의 지위는
**탐색적 파일럿**이며, 수정-재검수 루프는 여기서 종료한다. 자연 단일 실행에서 발생
확률이 낮은 fault injection 방어를 러너에 계속 쌓는 것은 목적 대비 과잉이다.

**finding 재분류 (live 차단 해제 — 후속 정식 검증 러너의 개선 목록으로 이관)**:

| # | 내용 | 재분류 근거 |
|---|---|---|
| C-5 잔여 | OpenAI 내부 파라미터 폴백 전송 계수 | 비차단 — 비용 증가 미입증, 논리 상한은 존재 |
| C-7 잔여 | run(live) 직접 호출 우회 | 비차단 — 정본 CLI 하나만 사용(운영 규칙) |
| C-8 잔여 | 완주 debate 의 사람 변조 | 비차단 — 실행 중 산출물 편집 금지(운영 규칙) |
| N-2 | 중복·누락·extra 행 집합 | 비차단 — 사전 차단 대신 실행 후 일회성 검사 |

**운영 규칙 (코드 방어의 대체 — 위반 시 해당 실행 무효)**:
- 실행 전: ① 코드·config 동결(아래 지문) ② 입력 3종 sha 기록(아래) ③ 정본 트랜치 CLI
  만, 한 터미널에서 ④ 병렬 실행·`run()` 직접 호출·실행 중 파일 수정 금지 ⑤ 중단 시
  자동 재개 금지 — 사람이 먼저 상태 확인.
- 실행 후: `compare_postcheck.py` 1회(0콜·읽기 전용) — ① 발화 32/이슈 ② (round,agent)
  고유 좌표 32 ③ axis·stance 각 32행·고유 좌표 ④ parse_fail 계수·raw 보존 ⑤ 논리·전송
  원장 계수·비용 ⑥ 산출물 sha 기록. **이상 이슈는 폐기(그 사실과 함께 §3-6 보고)** —
  고치지 않는다.

**동결 지문 (2026-08-11, 커밋 c64bddb)**:

| 파일 | sha256(앞 16) |
|---|---|
| compare_ours.py | 147dc2d5eb656d58 |
| configs/compare_v2.yaml | 77f155a30a58679c |
| issue/facts/assignment 0543 | b8d7f9c21c87c0d4 · ccd77903c12c3c3c · 07a14ba01a0d24ff |
| issue/facts/assignment 0248 | 1e1c8ee8ca8fb31f · ec842b7921c78da4 · 0f3bbff55a89203d |
| issue/facts/assignment 0262 | 86aebbc26ce9a19b · e9605189043e47cf · ac8edd36a43ada49 |

**보고 표현 제한 (RESULT.md·검토 문서에 강제)**: "탐색적 비교" · "후속 검증 후보 지표
발굴" · "확정적 재현 증거가 아님" · "3개 이슈의 방향성 관찰" · "발견된 지표는 별도
사전고정 실험에서 검증 예정". §3 기술 규칙(가설 언어 금지·1팩트 규칙·G5)은 그대로.

§8 의 "전송 시도마다 1행" 서술은 dispatch 단위 계수로 정정한다(OpenAI 내부 폴백은
1행 — C-5 잔여, 위 재분류). 퓨즈 232/692 는 dispatch 단위로 유효하다.
