# 시나리오 실험 적격성 실측 — 2026-08-21

지위: **근거 자료** (기계 게이트 두 문을 현재 바이트로 돌린 결과. 승인 아님, 실호출 0)
실행: `modules.scenario_gate.registry_results()`(확증 문) + `pilot_results()`(파일럿 문), HEAD f4ac57a 직후.
`시나리오2/` 3건은 `data/` 밖이라 임시 data root 에 올려 파일럿 문만 통과시켜 봤다.

## 1. 결과표

| issue | 확증 문 | 막는 것 (확증) | 파일럿 문 | 비고 |
|---|---|---|---|---|
| issue_throne_v2 | 차단 | state=candidate · prior pending | **허용** | spec 0.1·cal-0.1 해시 일치 |
| issue_award_v2 | 차단 | state=candidate · prior pending | **허용** | spec 0.1·cal-0.1 해시 일치 |
| issue_polar_v2 | 차단 | state=candidate · prior pending | **허용** | spec 0.2·cal-0.2 해시 일치, descriptive |
| issue_exile_v2 | 차단 | state=candidate · prior pending | **허용** | spec 0.2·cal-0.2 해시 일치, descriptive |
| issue_polar (v1) | 차단 | candidate · spec/calibration 파일 없음 | 허용 | v2 가 대체. 파일럿도 v2 로 돌릴 것 |
| issue_exile (v1) | 차단 | candidate · spec/calibration 파일 없음 | 허용 | 같음 |
| issue_throne (v1) | 차단 | candidate · 면제 3종(historical) | **금지** | "no new execution approval" 명시 |
| issue_award (v1) | 차단 | candidate · 면제 3종(historical) | **금지** | "v2 package required" 명시 |
| issue_camp · esa · hire · hire_a6 | 차단 | registry 항목 없음 | 허용 | 12팩트 베이스라인 재료. 등재된 적 없음 |
| issue_layoff (시나리오2) | 차단 | registry 항목 없음 | 허용(기계 검사만) | 정답 있음 → normative_decision 후보 |
| issue_outreach (시나리오2) | 차단 | registry 항목 없음 | 허용(기계 검사만) | 정답 없음 → descriptive_stance_only 후보 |
| issue_triage (시나리오2) | 차단 | registry 항목 없음 | 허용(기계 검사만) | 정답 없음 → descriptive_stance_only 후보 |

확증 문 통과: **0/8** (registry 등재분 전부 candidate — 운영 계약 §4 가 말하는 정상 상태).
파일럿 문 통과: data/issues 12 중 10, 시나리오2 3 중 3.

## 2. 읽는 법

**v2 네 벌은 확증까지 한 칸 남았다.** 재료 해시·DetectionSpec·calibration 전부 registry 와 맞는다. 남은 건
prior 프로브(`prior.status: pending` → facts 의 `prior.score` 실값) 와 사람 승인(`state` 전환 + `approved_by/at`).
prior 프로브는 시나리오당 12콜 — 네 벌이면 48콜. 과금 결정 사항.

**시나리오2 는 파일럿 문의 기계 검사(issue_id·schema_ver·팩트 ID 정합)는 통과하지만 재료로서는 검수 전이다.**
`modules.validate` 3종 OK, 팩트 12·에이전트 8·에이전트당 3팩트·ID 유일. 그런데
- issue 파일에 `outcome_policy` 가 없다(게이트는 None 을 막지 않는다 — registry 등재 때 정해야 함).
- prior 0/12 (전부 null). README 가 남긴 일 2번.
- `created_by: manual(session-claude-draft, 팀 검수 전 후보 지위)` — 사람 검수 미완. 민감 주제(triage·outreach) 문면 검토, 태그 분포 통일 여부(layoff 4/6/1/1 · outreach 3/6/1/2 vs 표준 2/7/1/2)가 요한 확인 대기로 README 에 적혀 있다.
- `data/` 반입 안 됨 — 루트 `시나리오2/` 에만 있다.

**v1 throne·award 는 파일럿도 막힌다.** registry 면제 사유 문자열이 새 실행 금지를 명시해서다. 의도된 것.

## 3. 등급별로 지금 돌릴 수 있는 것

- **파일럿(pilot_unvetted, 30콜 상한, 집계·보고 제외)**: v2 네 벌, camp·esa·hire·hire_a6, 시나리오2 세 벌(반입 후).
- **확증(confirmatory)**: 없음. 가장 가까운 것은 v2 네 벌 → prior 48콜 + 승인.

## 3-1. 추기 (같은 날 오후) — v2 prior 프로브 48콜 집행

요한 승인으로 `시나리오/probe_prior_new.py` 에 v2 네 벌을 더해 돌렸다. gpt-mini · 온도 0 · 문면 camp-prior-v0.2 ·
상한 51(48+재시도 3) · 실호출 48 · 파싱 실패 0. **네 벌 모두 known 0/12** — 교체할 팩트 없음. 원문은
`시나리오/prior_issue_*_v2.json` + `.partial.jsonl`, 원자료 커밋 7320519.

프로브가 facts 에 점수를 써 넣으면서 재료 해시가 바뀌었고 사슬을 따라 재계산했다: polar_v2·exile_v2 spec 빌더의
동결 상수 → spec 4개(`material_sha256`·`material_artifacts.facts_sha256` 두 칸만) → manifest 3개 → registry
(`facts_sha256`·`spec.sha256`·`prior.status: completed`). calibration 은 한 바이트도 안 바뀌었다. facts `_note` 의
"프로브 미실행" 문장은 지우지 않고 뒤에 정정 문장을 붙였다.

확증 문 재실측: v2 네 벌 모두 막는 이유가 **`promotion state not executable: candidate` 하나**. 남은 건 사람 승인
(state 전환 + `approved_by/at`)이고, 그건 코드가 아니라 보드 결정이다.

## 3-2. 추기 (같은 날 16:46) — v2 네 벌 승인

요한이 네 벌 전부 승인. registry `state: console_approved`, `approved_by`·`approved_at` 기입. 게이트 재실측:
네 벌 `allowed=True`, 경고 0. polar_v2·exile_v2 에 `accuracy` 요청은 여전히 차단(descriptive 정책은 승인과 무관).
콘솔 `/api/meta.scenario_gate_rows` 에서 allowed 가 v2 네 벌. 운영 계약 §4 "approved_count=0 이 정상" 은
이 시점부터 사실이 아니다 — 이제 **4**. 승인 절차는 `docs/SCENARIO_REGISTRY_OPERATIONS.md` §6 에 적었다.

**확증 등급으로 돌릴 수 있는 시나리오: 0 → 4.**

## 4. 이 표가 말하지 않는 것

게이트는 파일 정합성만 본다. 재료가 실험 질문에 맞는지(시나리오2 의 "12팩트 눈금" 이 분모만 맞추는지 태그 분포까지
맞추는지), 민감 주제 문면이 괜찮은지는 사람이 본다. 또 camp·esa·hire 가 registry 에 없는 건 빠뜨린 게 아니라
승격 원장이 8/20 에 생길 때 v1/v2 시나리오만 올렸기 때문이다 — 베이스라인 재료를 확증 등급으로 쓰려면 등재부터.
