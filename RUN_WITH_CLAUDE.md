# 클로드 코드 세션으로 파이프라인 돌리기 (API 키·비용 없이)

이 문서는 **팀원이 자기 클로드 코드(또는 Cowork) 세션에서** 파이프라인을 돌리는 절차서입니다.
API 키가 없어도, 세션의 클로드가 토론 엔진·채점기 역할을 **대행**해 파이프라인을 한 바퀴 돌릴 수 있습니다.

## 세 가지 실행 경로 (뭘 쓸지 먼저 고르기)

| 경로 | LLM 역할을 누가 | API 키 | 비용 | 결과 성격 |
|---|---|---|---|---|
| `quickstart.bat` | (LLM 안 씀 — 테스트만) | 불필요 | 0원 | 파이프라인 작동 확인 |
| `run_debate.bat` | Anthropic **API** | **필요** | 발생 | **정식 실험 수치** |
| **이 문서 (클로드 세션)** | **세션의 클로드 본인** | 불필요 | 0원(구독) | **재현·데모용** |

> ⚠ **중요 — 이 경로의 수치는 정식이 아닙니다.**
> 세션 클로드가 판정하면 모델·temperature가 고정되지 않습니다(팀 judge 사양 = Sonnet·temp 0·n=3, `CLAUDE.md` 참조).
> 따라서 이 경로는 **"파이프라인을 각자 돌려보고 이해·시연하는 용도"** 입니다.
> 팀 공식 미니 H1/H2 숫자는 반드시 `run_debate.bat`(API) 경로로 내야 합니다.

## 쓰는 법 (팀원용)

1. 이 리포 폴더에서 클로드 코드를 켜거나, Cowork 세션에 이 폴더를 연결합니다.
   (리포 루트의 `CLAUDE.md`가 자동 로드되어 실험 규칙이 세션에 적용됩니다.)
2. 아래 **[세션 클로드에게 줄 지시]** 블록을 통째로 복사해 세션에 붙여넣습니다.
3. 클로드가 단계별로 진행하며 결과(FAR 곡선 등)를 요약해 줍니다.

---

## [세션 클로드에게 줄 지시] — 이 아래를 복사해서 붙여넣으세요

너는 이 리포(`fact-ledger-pipeline`)에서 작업 중이다. 먼저 `README.md → DESIGN.md → SCHEMA.md → WORKLOG.md`와 루트 `CLAUDE.md`를 읽어 규칙을 파악하라. 그다음 아래 절차로 **미니 토론 파이프라인을 API 호출 없이 네가 대행해서** 한 바퀴 돌려라. 이건 재현·데모용이며 정식 실험 수치가 아님을 결과에 명시하라.

**0. 무결성 고지 (반드시 결과 맨 위에 적기)**
"이 실행은 세션 클로드 대행 — 재현·데모용. 모델·temperature 미고정이므로 팀 공식 H 수치 아님(정식은 run_debate.bat/API 경로)."

**1. 입력 로드**
- `python -m modules.validate data/issues/issue_esa.json data/facts/facts_issue_esa.json data/assignments/assignment_issue_esa.json` 로 픽스처가 유효한지 먼저 확인.
- `data/facts/facts_issue_esa.json`(팩트 12종), `data/assignments/assignment_issue_esa.json`(8에이전트 비대칭 배분), `data/issues/issue_esa.json`(이슈 본문)을 읽어라.

**2. 토론 대행 (debate_engine 역할)**
- 이슈 본문과 각 에이전트의 배분 팩트·관점·입장(pro/con)을 바탕으로, 8에이전트 × 3라운드 토론을 생성하라.
- 각 에이전트는 자기에게 배분된 팩트만 알고, 이전 라운드 발화를 보고 반응한다(fully-connected).
- **각 발화 원문을 요약하지 말고 그대로** `data/debates/debate_issue_esa_claude.jsonl`에 스키마 4번 형식(event=utterance, run_id, ts, ledger_mode="off", round, agent_id, response_text …)으로 한 줄씩 기록하라.
- 규모가 크면 라운드별로 나눠 진행하되, 중간 산출을 매번 저장하라(체크포인트).

**3. 채점 대행 (judge 역할, 순수 함수 규칙 준수)**
- 각 라운드 × 각 팩트에 대해, 그 라운드 발화 원문에서 팩트가 어떻게 다뤄졌는지 5종(unmentioned/mentioned/accepted/refuted/ignored) 중 하나로 판정하라. 판단은 발화 원문에만 근거하고 추측 금지.
- 팩트마다 3표를 매기고 다수결로 status를 정하되 **3표 원본을 보존**하라(불일치율 = judge 신뢰도).
- 결과를 `data/judgments/judgment_issue_esa_claude.json`에 스키마 5번 형식으로 쓰되, `judge.model`은 반드시 `"claude-session-demo"`로, `stage_type`은 `"round"`로 기록하라(정식 수치 아님 표시).

**4. FAR 산출 (기존 코드 재사용 — 잣대 통일)**
- 손으로 계산하지 말고 `modules.judge`의 `far()` 함수를 재사용하라(소실=status∉SURVIVING, SCHEMA 「FAR 정의」절과 동일 잣대). 스테이지별 far_system·far_critical과 far_by_stage 곡선을 산출하라.

**5. 검사 + 요약**
- `python -m modules.validate data/debates/debate_issue_esa_claude.jsonl data/judgments/judgment_issue_esa_claude.json` 로 산출물이 스키마를 지키는지 확인(통과 전엔 완료 아님).
- FAR 곡선(라운드별)과 팩트별 상태 전이를 표로 요약하라. 맨 위의 무결성 고지를 잊지 말 것.

**하지 말 것**
- 발화·판정을 요약해서 저장하지 마라(이 프로젝트가 연구하는 실패 그 자체다).
- 스키마를 임의로 바꾸지 마라. 문제가 있으면 노션 협업 보드 패키지 항목에 질문을 남기라고 사용자에게 안내하라.
- config(`configs/*.yaml`) 밖에서 실험 조건을 바꾸지 마라.

---

## 관찰 트랙(회사 A2A 로그)도 이 방식으로 가능

스프린트 2일차에 회사 Mystery Case 로그(971 발화)를 이 대행 방식으로 판정해 실측 FAR을 산출한 시연이 있습니다.
관찰 트랙 loader와 결과는 팀 논의 후 리포 반영 예정입니다(현재 미반영). 방법 B(초반 발화에서 ground-truth 추출 → 후반 생존 추적)가 다음 단계입니다.
