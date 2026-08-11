# experiments 교차 리뷰 — paper_repro 외 실험 폴더

> 지위: **리뷰 기록** (2026-08-11, 요한/GPT-sol, 실제 API 호출 0)
> 범위: `paper_repro`를 제외한 `experiments/` 하위 11개 폴더. 기존 실험 코드·원자료는 수정하지 않는다.
> 운영 판정: 종결 실험의 기존 수치는 원자료와 명시된 한계 안에서 보존하되, 아래 재사용 금지 폴더의 러너로 새 실호출을 시작하지 않는다.

## 범위와 폴더별 판정

| 폴더 | 문서 지위 | 이번 판정 |
|---|---|---|
| `judge_crossmodel` | 제안, 리더 승인 전 | **차단 — JX-1~JX-4 해소 전 live 금지** |
| `judge_axis` | 종결 실측 기록 | **기공지 재사용 금지 유지** |
| `structure_axis` | 탐색적 실측 기록 | **기공지 재사용 금지 유지** |
| `mini_h2_pilot` | 탐색적/데모 완료 | 기존 산출물은 유효, **러너 재사용 금지(MH-1~MH-2)** |
| `transmission_pilot` | 탐색적/데모 완료 | 원자료는 보존, 파생물 재검토 지위 유지, **러너 재사용 금지(TP-1~TP-3)** |
| `instrument_check` | 탐색적 계기 점검 완료 | 기존 0-parse-fail 결과는 보존, **러너 재사용 금지(IC-1~IC-2)** |
| `discourse_progression` | 사전고정 후 정식 검증 완료 | 결과는 보존하되 provenance 공백 DP-1 명시, **러너 재사용 금지(DP-2~DP-4)** |
| `hidden_profile` | 사전고정 없는 탐색적 눈금 | 기존 결과는 보존, **러너 재사용 금지(HP-1~HP-3)** |
| `hidden_profile_node` | 현행 0콜 파생 뷰 | 이번 리뷰에서 차단 결함 없음 |
| `cost_frontier` | 탐색적 0콜 계측 | 이번 리뷰에서 차단 결함 없음 |
| `task_structure` | 승인 전 초안, 러너 없음 | 실행 금지라는 문서 지위가 이미 명확함 |

## 신규 차단 — `judge_crossmodel`

### JX-1 — `.part`가 체크포인트가 아니라 덮어쓰는 진행 표시다 (차단)

- 근거: `experiments/judge_crossmodel/run_rejudge.py:277-311`
- 문서는 조건별 체크포인트·중단 재개를 약속하지만, `phase_run()`은 기존 `.part`를 읽지 않는다. 각 셀 뒤 지금까지의 `rows`를 덮어쓸 뿐이다.
- 영향: 조건당 33콜 중 마지막에 중단되면 같은 조건을 처음부터 재호출한다. 이미 결제된 성공 표도 반복되고, 재시작 상한은 트랜치 누적 상한이 아니다.
- 수용 기준:
  1. 표 단위 안정 tag에 condition·cell·vote·model·prompt/input hash를 묶는다.
  2. 성공 직후 raw 응답을 append+flush한다.
  3. 재진입 시 같은 지문인 완료 tag만 재사용하고 drift를 거부한다.
  4. 중간 강제 실패 후 재진입에서 신규 호출 수가 남은 표 수와 정확히 같음을 0콜 가짜 responder로 검증한다.

### JX-2 — LLM 원응답이 보존되지 않고 parse failure가 `unmentioned`로 바뀐다 (차단)

- 근거: `experiments/judge_crossmodel/run_rejudge.py:212-231,293-307`
- `_chat()`의 문자열은 파싱 직후 버려진다. 저장되는 `votes`는 파생 구조이며 공급자 원응답이 아니다.
- 파일럿 프롬프트 파싱 실패는 `status=unmentioned`로 정규화되어 다수결·flip·pattern 지표에 실제 표처럼 들어간다. `reason`에는 raw 앞 120자만 남는다.
- 이는 CLAUDE.md의 “LLM 응답 원문 그대로 저장”과 PREREG §5의 parse-fail 보류 관문을 충족하지 못한다.
- 수용 기준:
  1. 호출별 raw 전문과 parse status를 별도 원장에 보존한다.
  2. parse failure는 `None/unknown`으로 격리하고 다수결 분모에서 제외하거나 해당 셀을 미산출한다.
  3. 조건별 parse-fail 비율 10% 초과 시 자동 보류한다.
  4. malformed raw 1표가 `unmentioned` 표로 변하지 않는 회귀 테스트를 추가한다.

### JX-3 — `hash(cname)` 때문에 표 seed가 프로세스마다 달라진다 (중간)

- 근거: `experiments/judge_crossmodel/run_rejudge.py:287-288`
- Python 문자열 hash는 프로세스별 salt를 쓴다. 0콜 실측에서 `pilot_gpt`의 seed base가 네 새 프로세스에서 `66722, 97249, 89730, 9338`로 모두 달랐다.
- PREREG의 “재실행 재현성”과 반대다.
- 수용 기준: 고정 seed 표 또는 SHA-256 기반 정수 seed를 쓰고, 새 프로세스 2회에서 condition/cell/vote별 seed 전량이 동일함을 검사한다.

### JX-4 — report가 불완전 조건을 정상 집계한다 (중간)

- 근거: `experiments/judge_crossmodel/run_rejudge.py:332-375`
- 존재하는 조건 파일만 조용히 집계하며 4조건×11셀 완전성, 중복 좌표, meta 지문, parse-fail 보류를 강제하지 않는다.
- 수용 기준: 조건 집합과 셀 좌표가 사전고정과 set-equal이어야만 결과 파일을 쓰고, 하나라도 누락·중복·지문 불일치면 exit 1로 중단한다.

## 종결 러너 재사용 금지 — 신규 확인

### MH-1 — dry와 live가 같은 run_id·산출물·partial checkpoint를 공유한다 (차단)

- 근거: `experiments/mini_h2_pilot/run_h2.py:219-299,422-445`
- `--dry`도 `h2p_off|h2p_v0` 정본 경로에 debate/judgment/partial을 쓴다. 이후 live는 파일 존재·발화 수만 보고 스킵한다. 모델·mode·config·prompt/input 지문 검사가 없다.
- 수용 기준: dry 전용 임시 root/run_id를 사용하고 source root 쓰기 0을 보장한다. live 재사용은 모든 지문이 일치한 완주 산출물만 허용한다.

### MH-2 — stage checkpoint가 입력·판정 조건과 결합되지 않는다 (중간)

- 근거: `experiments/mini_h2_pilot/run_h2.py:252-272`
- partial key가 stage 숫자뿐이므로 debate/facts/model/prompt가 바뀌어도 옛 stage를 재사용한다.
- 수용 기준: stage key에 debate·facts·model·prompt·n_votes 지문을 묶고 drift를 즉시 거부한다.

### TP-1 — “phase 재실행 안전”과 달리 호출 단위 재개가 없다 (차단)

- 근거: `experiments/transmission_pilot/run_pilot.py:165-233,252-308,318-374`
- debate는 라운드가 끝나야 전체 파일을 `w`로 다시 쓰므로 라운드 중 성공 호출이 유실된다. 부분 debate를 재실행하면 처음부터 다시 쓰며, judge/probe/scan은 단계가 끝날 때만 최종 파일을 쓴다.
- 수용 기준: 모든 유료 단계에 호출 단위 append+flush 원장과 안정 tag를 두고, 재진입 시 남은 좌표만 호출한다. 완료 debate·상류 원자료 hash는 재개 전후 불변이어야 한다.

### TP-2 — judge/scan parse failure가 소실 또는 비노출로 조용히 바뀐다 (차단)

- 근거: `experiments/transmission_pilot/run_pilot.py:274-307,360-373`
- judge parse failure는 `unmentioned`로 저장되고, question scan parse failure는 단순 `pass`되어 비노출로 처리된다.
- 수용 기준: unknown을 별도 보존하고 관련 FAR/노출 분모를 미산출하며, raw 원응답과 실패 좌표를 manifest에 기록한다.

### TP-3 — 완료 파일 재사용이 source/config/prompt 지문을 검사하지 않는다 (중간)

- 근거: `experiments/transmission_pilot/run_pilot.py:165-172,252-258,318-324,352-358`
- 파일 존재 또는 `run_end` 문자열만으로 스킵한다. 같은 `tp1`에 모델·프롬프트·입력 변경이 섞여도 감지하지 않는다.
- 수용 기준: run identity에 issue/facts/assignment/config/model/prompt/input hash를 묶고 drift를 거부한다.

### IC-1 — `.part`를 쓰지만 읽지 않아 중단 재개가 아니다 (차단)

- 근거: `experiments/instrument_check/run_judge_probe.py:77-141,147-187`
- H2/H1의 `.part`는 진행 중 덮어쓰기만 하며 재시작 시 읽지 않는다. ladder는 12개 생성이 모두 끝난 뒤에만 저장한다.
- 수용 기준: 호출별 raw checkpoint를 읽어 재개하고, 강제 중단 후 남은 좌표만 호출함을 검증한다.

### IC-2 — raw 응답과 parse failure 근거가 사라진다 (중간)

- 근거: `experiments/instrument_check/run_judge_probe.py:92-101,123-140,168-186`
- raw는 파싱 후 버려지고 실패는 `None`만 저장된다. report는 `None`을 분모에서 제외하지만 실패율·좌표를 보고하지 않는다.
- 현재 커밋 산출물 실측은 H1 300표·H2 144표 모두 `None=0`이라 기존 수치 오염 증거는 없다. 재사용 안전성 문제다.
- 수용 기준: raw 전문·parse status·실패율을 보존하고, 실패가 있는 결과는 완전 결과와 구분한다.

### DP-1 — GPT 생성물 3개가 `gen_meta.json` 호출 원장에 없다 (중간, 기존 산출물 provenance 공백)

- 근거: `experiments/discourse_progression/run_experiment.py:185-213`
- 기존 파일을 스킵한 뒤 매 실행마다 새 `meta`를 만들기 때문에, 이전 호출 메타가 새 `gen_meta.json`에서 사라진다.
- 0콜 실측: GPT 텍스트 36개 중 meta calls는 33개이며 `A1_r0.txt`, `A1_r1.txt`, `A1_r2.txt`가 원장에 없다. Gemini는 36/36이다.
- 기존 텍스트를 무효화한다는 뜻은 아니지만, 세 파일의 실제 요청 파라미터를 현 meta만으로 증명할 수 없다.
- 수용 기준: 결과 인용 시 이 provenance 공백을 한계로 병기한다. 새 실행기는 기존 meta를 병합하거나 각 output 옆 immutable call record를 둔다.

### DP-2 — 파일 존재만으로 다른 model/prompt/config 출력도 재사용한다 (차단)

- 근거: `experiments/discourse_progression/run_experiment.py:185-213,232-269`
- 텍스트와 judgments/stability는 지문 없이 존재 여부만으로 재사용된다. 모델 환경변수를 바꿔도 같은 `results/gpt`의 옛 텍스트가 새 모델 meta와 섞일 수 있다.
- 수용 기준: output identity에 model·temperature·seed·prompt/input hash를 묶고 drift를 거부한다.

### DP-3 — 불완전 judge JSON이 12개 정상 표로 바뀐다 (차단)

- 근거: `experiments/discourse_progression/run_experiment.py:216-230`
- 누락 fact_id는 `.get(..., "unmentioned")`로 채워져 소실로 계상되고, raw judge 응답은 저장되지 않는다.
- 수용 기준: 12개 key set-equal·값 enum을 강제하고, 실패 raw를 보존하며 해당 셀/텍스트를 미산출한다.

### DP-4 — 실호출 상한과 OpenAI 절단 검사가 없다 (중간)

- 근거: `experiments/discourse_progression/run_experiment.py:101-176,383-401`
- 약 150콜이라는 문서 추정은 있으나 강제 cap이 없다. Gemini만 `MAX_TOKENS`를 검사하고 OpenAI `finish_reason=length`는 확인하지 않는다.
- 수용 기준: 단계·전체 상한, OpenAI 절단 즉사, 호출별 checkpoint를 추가한 새 러너에서만 재실행한다.

### HP-1 — 호출 상한·checkpoint가 없고 결과 파일을 마지막에 덮어쓴다 (차단)

- 근거: `experiments/hidden_profile/sanity_check.py:99-123`, `experiments/hidden_profile/curve.py:70-118`
- 예외를 행 결과로 삼고 계속 호출하며 durable 저장은 전체 종료 후 한 번이다. 중단 시 성공 호출이 모두 유실되고 재실행은 처음부터 결제한다.
- 수용 기준: 호출별 raw append+flush, 전역 cap, tag 재개를 추가한 새 러너를 사용한다.

### HP-2 — 원응답을 보존하지 않는다 (차단)

- 근거: `experiments/hidden_profile/sanity_check.py:62-89,114-121`, `experiments/hidden_profile/curve.py:48-68,91-117`
- sanity는 choice/reason만, curve는 choice만 저장한다. 현재 결과 파일 6종 218행에서 error·parse_fail은 0이지만 원문 감사와 재파싱은 불가능하다.
- 수용 기준: provider raw 응답 전문·usage·parse status를 호출별 원장에 보존한다.

### HP-3 — 실패가 발생하면 curve 정답률 분모에 오답처럼 포함된다 (중간)

- 근거: `experiments/hidden_profile/curve.py:84-96,103-114`
- `에러:*`와 `파싱실패`도 `picks` 길이에 포함되어 정답률을 낮춘다. 현재 커밋된 131행에는 해당 행이 0이라 기존 표 영향은 없다.
- 수용 기준: transport/parse failure를 과학 결과와 분리하고 성공 분모·실패율을 함께 보고한다.

## 기공지 재확인

- `judge_axis`: `README.md:60-79`에 offline/live checkpoint 오염, preflight 부재, 부분 checkpoint 집계·parse_fail 소실 변환이 이미 기록돼 있다. **재사용 금지 유지.**
- `structure_axis`: `run_structure.py:102-114`의 dry/live 동일 경로 쓰기와 재진입 안전성 결함은 PR#34 리뷰·WORKLOG에 이미 기록됐다. **재사용 금지 유지.**
- `transmission_pilot/data/STATUS.md:9-19`: access/transmission 파생물 재검토 대상·인용 금지와 access report 재생성 경로 부재는 이미 명시돼 있다. 이번 리뷰는 그 지위를 변경하지 않는다.

## 0콜 검증 증거

- `python -m compileall -q experiments` 통과.
- `python run_smoke.py`: 파일 계약·311 tests·ledger 점검 전부 통과.
- mini_h2/structure 산출물 8개 canonical validate 통과; debate 4개는 `--deep` 재조립까지 통과.
- 기존 결과 데이터 감사:
  - hidden_profile 6파일 218행: error 0, parse_fail 0.
  - instrument H1 300표·H2 144표: parse `None` 0.
  - discourse: GPT 36텍스트/33 call-meta, Gemini 36/36; judgment는 양 모델 모두 9 run×4 stage×12 fact 완전.
  - crossmodel seed base 새 프로세스 4회 전부 상이.
- 실제 외부 API 호출: **0**.

## 다음 상태

- `judge_crossmodel`: **JX-1~JX-4 해소 및 0콜 재진입 회귀 전 live 금지.**
- 나머지 종결 실험: 기존 원자료·결과는 문서 지위와 한계 안에서 보존하되, 새 질문은 현행 `paper_repro` 부품 또는 새 버전 러너로 수행한다. 종결 러너를 고쳐 과거 결과와 코드 대응을 바꾸지 않는다.

## append-only 응답 형식

이 아래에 후속 담당자가 기존 finding을 수정하지 말고 덧붙인다.

```text
YYYY-MM-DD | 작성자 | finding ID | 수용 | 반박 | 수정완료 | 대기
- 근거:
- 변경:
- 0콜 검증:
- 남은 관문:
```

## 2026-08-11 독립 reviewer 후속 — 추가 수용

> 위 1차 리뷰가 작성된 뒤 병렬 독립 리뷰 3건의 전문을 회수해 대조했다. 아래 항목은 1차 문서에
> 없거나 범위가 더 좁게 적혀 있던 finding이다. 기존 항목은 수정하지 않고 이 절을 append한다.

### XR-1 — 논리 호출 상한이 전송 재시도 횟수를 제한하지 않는다 (높음)

- 근거: `experiments/structure_axis/run_structure.py:58-66,87-96`,
  `experiments/mini_h2_pilot/run_h2.py:113-138,429-431`, `modules/llm.py:448-469`.
- `CallBudget`은 논리 호출마다 1만 소비하지만 `modules.llm`은 그 안에서 최대 5회 전송한다.
  따라서 structure의 `--max-calls 220`은 최악 1,100회, mini H2의 600은 최악 3,000회
  전송을 허용한다. mini H2 CLI 기본값 600은 README의 500과도 다르다.
- 0콜 fault injection: 논리 호출 1회에서 가짜 500 응답 전송 5회를 확인했다.
- 수용 기준: 모든 네트워크 전송 직전에 예산을 소비한다. 상한 1 회귀에서 전송도 정확히 1회여야
  하며 README와 CLI 기본값을 일치시킨다.

### XR-2 — mini H2 분석기가 불완전·이질 입력을 검사하지 않고 report를 덮어쓴다 (중간)

- 근거: `experiments/mini_h2_pilot/run_h2.py:311-325,348-406`.
- 두 팔의 stage 연속성·팩트 집합·run/arm·dry/live·config/prompt/input 지문을 검사하지 않고
  `h2_report.json`을 쓴다. `modules.validate` 전에 보고서가 생성될 수도 있다.
- 수용 기준: 두 팔 schema·좌표 완전성·source SHA-256을 fail-closed 검증하고 실패 시 기존
  report를 byte 불변으로 둔다.

### XR-3 — structure 기준선의 “입력 SHA 동일” 주장은 현 파일 바이트로 재현되지 않는다 (중간)

- 근거: `experiments/structure_axis/README.md:13-15`, `run_structure.py:12-16`.
- 0콜 실측: issue `47b241…` vs `6f689d…`, facts `fb6af7…` vs `b62b84…`, assignment
  `51a313…` vs `b1f88f…`; 세 쌍 모두 바이트 SHA는 다르고 JSON 객체는 동일했다.
- 의미상 입력 차이의 증거는 아니지만 “바이트 SHA 동일”의 provenance는 현재 재현할 수 없다.
- 수용 기준: byte hash를 주장하면 실제 SHA 전문이 같은 manifest를 보존한다. 의미 hash라면
  canonicalization 규칙과 canonical SHA를 명시한다.

### XR-4 — transmission judge가 불완전 debate를 정상 최종본으로 고착한다 (높음)

- 근거: `experiments/transmission_pilot/run_pilot.py:252-307`.
- `run_end`, 예상 stage, stage별 참가자 완전성을 확인하지 않는다. 독립 0콜 stub 재현에서 r0 발화
  1개만으로 stage `[0]` judgment를 만들었고, 다음 실행은 파일 존재로 영구 스킵했다.
- 수용 기준: 완전한 `run_end(status=complete)`, stage `0..ROUNDS`, 참가자 집합을 API 호출 전에
  검사한다. 불완전 입력은 0콜·최종 파일 미생성으로 실패하며 source debate 지문을 저장한다.

### XR-5 — transmission STATUS의 “API 응답 원본” 지위가 실제 파일과 어긋난다 (높음)

- 근거: `experiments/transmission_pilot/data/STATUS.md:11-12`,
  `run_pilot.py:274-307,361-373`, `experiments/instrument_check/run_judge_probe.py:92-101,123-140,168-186`.
- tp1 judgment/scan과 instrument ladder/H1/H2는 raw 모델 텍스트 없이 파싱 결과만 가진다.
  따라서 `STATUS.md`의 원본 표기는 raw API 원응답이라는 의미로는 사실이 아니다.
- 수용 기준: 기존 파일은 “파싱된 파생 판정이며 raw 응답 미보존”이라고 STATUS에 append 정정한다.
  향후 호출은 raw 원장과 파생물 좌표를 분리한다.

### XR-6 — 문자열 `"false"`가 `true`로 뒤집히는 JSON 타입 결함 (중간)

- 근거: `experiments/transmission_pilot/run_pilot.py:278-286,334-340,364-369`,
  `experiments/instrument_check/run_judge_probe.py:127-131,172-179`.
- 코드가 `bool(value)`를 사용하므로 JSON 문자열 `"false"`는 `True`다. 이 행은 parse-fail에도
  잡히지 않는다.
- 수용 기준: `mentioned`/`known`은 정확한 JSON boolean만 허용하고, agent 목록도 `list[str]`와
  허용 ID를 검증한다. 문자열 false, 0, null, 누락, 미지 agent를 모두 parse-fail로 만드는
  회귀 테스트를 둔다.

### XR-7 — cost frontier가 일부 hash mismatch run을 verified 가격에 포함한다 (중간)

- 근거: `experiments/cost_frontier/p0_census.py:152-173,191-197`.
- mismatch 입력은 문자 수에서 빠지지만 하나라도 일치해 `input_chars > 0`이면 run 전체가
  `verified`에 들어간다. 독립 0콜 probe에서 16콜 중 15 verified/1 mismatch가 검증 가격에
  포함됐다.
- 수용 기준: `hash_mismatch > 0` 또는 `hash_verified != calls`면 가격 합계에서 제외하고
  `complete_verified/partial/invalid/unreassemblable` 상태를 명시한다.

### XR-8 — 담화 결과가 사전고정 2모델을 3모델 정식 복제로 표시한다 (중간)

- 근거: `experiments/discourse_progression/PREREG_v0.2.md:23-26,45-52`,
  `담화전진가설-쉬운설명.md:71-79`, `보고서가시화 html.html:44-52,225-232`,
  `results/analysis.json:515-519`.
- 사전고정 R1은 GPT·Gemini 2/2 규칙이다. Sonnet은 앞선 데모인데 후속 설명과 HTML은
  3모델 모두를 사전고정 정식 검증처럼 묶는다. R1 자체의 2/2 성립을 반박하는 finding은 아니며
  증거 등급 표기의 과장이다.
- 수용 기준: Sonnet을 prior demo/외부 복제로 분리하고 R1은 “사전고정 2/2(GPT·Gemini)”로
  표시한다. 통합 표에는 각 모델의 preregistered/demo 지위를 표시한다.

### XR-9 — 담화 실험이 조작하지 않은 영구 사망·장부 효과까지 결론을 확장한다 (중간)

- 근거: `experiments/discourse_progression/run_experiment.py:76-89,179-183`,
  `담화전진가설-쉬운설명.md:83-89`.
- 러너는 매 라운드 12팩트 원본과 전체 이전 발화를 다시 준다. rolling summary, 500자 저장소,
  원본 비가용, ledger 조건을 조작하지 않았으므로 “요약의 요약에서 영구 사망”과 Fact Ledger
  필요성은 본 데이터의 직접 결론이 아니라 후속 가설이다.
- 수용 기준: 현재 결론을 발화 선택에서의 비언급으로 제한하고, 해당 문단은 후속 가설/설계 동기로
  낮춘다. 영구 사망·장부 효과는 원본 접근×summary/ledger 사전고정 비교 뒤에만 결과로 쓴다.

### XR-10 — 단독 calibration을 고전 hidden-profile 효과 재현으로 부른다 (중간)

- 근거: `experiments/hidden_profile/REPORT_v0.md:6-14,86-91`,
  `gen_evidence.py:138-146,161-168`.
- 데이터에는 집단 토론·미공유 정보 분산·정보 취합이 없고 단독 강제선택만 있다. 문서도 한편으로
  “눈금”이라고 정확히 제한하면서 다른 문단에서는 고전 효과 재현이라고 확장한다.
- 수용 기준: 결론을 “단독 강제선택 calibration이 ceiling/trap을 분리”로 한정한다. 고전 효과
  재현 표현은 배분 v2·다중 에이전트·사전고정 집단 결과변수 실행 전까지 사용하지 않는다.

### 독립 reviewer 통합 후 운영 판정

- 1차 판정의 live/재사용 금지는 완화되지 않는다.
- 추가로 `cost_frontier`는 실행 차단 결함은 없지만, **XR-7 해소 전 partial mismatch run을
  verified 가격으로 인용하지 않는다.**
- `discourse_progression`과 `hidden_profile`의 기존 원자료는 보존하되, XR-8~XR-10의 문구를
  정정하기 전 해당 확장 결론을 정식 검증 결과로 인용하지 않는다.
