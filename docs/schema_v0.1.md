*작성: 민옥 측 (7/21). 검토 의견은 본 보드 소통 스레드로. 수정은 이 문서를 고치지 않고 v0.2를 새로 만든다.*

# 공통 규칙

- 인코딩 UTF-8, 필드명 snake_case. 단일 객체는 .json, 이벤트 누적은 .jsonl(한 줄 = 이벤트 하나).
- 모든 파일 공통 필드: `schema_ver`(예: "0.1"), `created_by`(모듈명), `created_at`(ISO8601).
- id 규칙: `issue_001`, `fact_001_03`(이슈번호_팩트번호), `agent_1`.
- 재현성 3종 세트: 난수 쓰는 모든 곳에 `seed`, LLM 호출마다 `model`·`temperature`·`prompt_ver`, 프롬프트 원문은 `prompt_hash`로 검증 가능하게 (7/16 파일럿의 해시 검증 방식 계승).

# 1. 이슈 문서 — issue_{id}.json

```json
{
  "schema_ver": "0.1",
  "created_by": "loader",
  "created_at": "2026-07-21T10:00:00+09:00",
  "issue_id": "issue_001",
  "source": "company_json | paper | synthetic",
  "source_meta": {"url": "...", "fetched_at": "...", "usage_approved": false},
  "title": "...",
  "body": "전문"
}
```

- `usage_approved`: 회사 JSON 사용 허락 전까지 false. false인 이슈는 내부 개발용으로만.

# 2. 팩트 목록 — facts_{issue_id}.json

```json
{
  "schema_ver": "0.1",
  "created_by": "extractor",
  "created_at": "...",
  "issue_id": "issue_001",
  "extractor": {"model": "...", "temperature": 0, "prompt_ver": "ex-0.1"},
  "facts": [
    {
      "fact_id": "fact_001_01",
      "text": "원자 팩트 한 문장",
      "tags": ["condition", "exception", "counter_evidence", "stance_support"],
      "critical": true,
      "prior": {"score": 0.0, "probe_model": "...", "probe_prompt_ver": "pr-0.1", "probed_at": "..."}
    }
  ]
}
```

- `tags`는 복수 허용(해당하는 것만). `prior.score`: 0(모델이 전혀 모름)~1(완전히 암) — 프리필 프로브 결과. 프로브 전이면 null.
- **설계 결정**: 팩트의 라운드별 상태(언급/반박/무시)는 여기 없음 — 이 파일은 정적 원장이고, 상태는 라운드마다 변하는 동적 정보라 5번(판정 결과)에서 관리.

# 3. 배분표 — assignment_{issue_id}.json

```json
{
  "schema_ver": "0.1",
  "created_by": "assigner",
  "created_at": "...",
  "issue_id": "issue_001",
  "seed": 42,
  "agents": [
    {"agent_id": "agent_1", "perspective": "...", "stance": "pro | con", "assigned_fact_ids": ["fact_001_01", "fact_001_04"]}
  ]
}
```

- `seed` 필수 — 같은 시드면 같은 배분. 재현성의 심장.
- 논문 세팅 기본값: 8에이전트(관점 4 × 입장 2).

# 4. 토론 로그 — debate_{issue_id}_{run_id}.jsonl

한 줄 = 이벤트 하나. 발화와 장부 개입이 같은 타임라인에 쑎인다.

```json
{"event": "utterance", "run_id": "run_001", "ledger_mode": "off | v0 | v1 | v2 | a1", "round": 0, "agent_id": "agent_1", "model": "...", "temperature": 1.2, "prompt_ver": "db-0.1", "prompt_hash": "sha256:...", "response_text": "발화 원문", "ts": "..."}
{"event": "ledger_inject", "run_id": "run_001", "round": 1, "injected_fact_ids": ["fact_001_03"], "reason": "v0_all_missing | v1_ignored_only", "ts": "..."}
{"event": "gate_check", "run_id": "run_001", "draft_text": "합의문 초안", "missing_fact_ids": ["fact_001_07"], "verdict": "pass | rollback", "rollback_count": 0, "ts": "..."}
```

- `ledger_mode`가 실험 조건 스위치. off = 대조군.
- `prompt_hash`: 재생·재현 시 프롬프트 동일성 검증용 (파일럿 방식 그대로).
- 응답은 무조건 원문 저장. 요약 금지.

# 5. 판정 결과 — judgment_{issue_id}_{run_id}.json

```json
{
  "schema_ver": "0.1",
  "created_by": "judge",
  "created_at": "...",
  "issue_id": "issue_001",
  "run_id": "run_001",
  "judge": {"model": "sonnet", "temperature": 0, "n_votes": 3, "aggregation": "majority", "prompt_ver": "jd-0.1"},
  "rounds": [
    {
      "round": 0,
      "facts": [
        {"fact_id": "fact_001_01", "status": "unmentioned | mentioned | accepted | refuted | ignored", "votes": ["mentioned", "mentioned", "ignored"], "agents_mentioning": ["agent_1"]}
      ]
    }
  ],
  "recall_probe": [
    {"agent_id": "agent_1", "recalled_fact_ids": ["fact_001_01"], "extra_lines": 4}
  ],
  "summary": {"far_by_round": [0.08, 0.21, 0.33], "far_system": 0.33, "far_agent_mean": 0.51, "far_critical": 0.29}
}
```

- `judge`: Sonnet 단일 + n=3 다수결 고정 (결정 로그 확정 사항, 7/16 judge 노이즈 문제 반영). `votes`를 원본 그대로 남겨 다수결 이전 불일치율을 재젬 수 있게 함(judge 신뢰도 지표가 공짜로 나옴).
- `far_by_round`: 라운드별 분해 필드 — 7/16 파일럿의 두 국면 발견(초반 발화억제/후반 지식붕괴) 검증용. 장부 효과를 국면별로 볼 수 있어야 "재주입은 후반 약, 게이트는 초반 약" 가설 판정 가능.
- `recall_probe`: A4(사후 회상)용 선택 필드. 없으면 생략 가능.
- 상태 5종: 미언급/언급/수용/반박/무시 — v1 상태 머신과 1:1 대응.

# 모듈 ↔ 파일 매핑 (누가 쓰고 누가 읽나)

| 파일 | 쓰는 모듈 | 읽는 모듈 |
| --- | --- | --- |
| issue | 로더 | 추출기 |
| facts | 추출기(+prior 프로브) | 배분기, 채점기, 장부, 분석 |
| assignment | 배분기 | 토론 엔진, 분석 |
| debate(.jsonl) | 토론 엔진(+장부·게이트) | 채점기, 분석 |
| judgment | 채점기 | 장부(실험군 루프), 분석 |

---

# v0.2 (2026-07-21, 리더 확정)

*v0.1에서 바뀐 것만 기록. 나머지는 v0.1 그대로 유효.*

**변경 1 — `rounds` → `stages` 일반화 (판정 결과 파일).** 관찰 트랙에는 라운드·에이전트 구조가 없다는 지적(동범 측, 7/21) 수용. 판정 결과의 `rounds` 배열을 `stages`로 개명하고 `stage_type` 필드 추가:

```json
{
  "stage_type": "round | summary_layer",
  "stages": [
    {"stage": 0, "facts": [ ... ]}
  ],
  "summary": {"far_by_stage": [0.08, 0.21, 0.33], "far_system": 0.33, "far_agent_mean": null, "far_critical": 0.29}
}
```

- 실험 트랙: `stage_type: "round"`, stage = 토론 라운드
- 관찰 트랙: `stage_type: "summary_layer"`, stage = 요약 계층 깊이 (0 = 원문)
- `far_agent_mean`은 관찰 트랙에서 **null** (System/Agent 분할 불성립 — 명시적 N/A). `far_system`·`far_critical`·`far_by_stage`는 양 트랙 공통 → 두 트랙 결과를 같은 표에 나란히 배치 가능.

**변경 2 — debate.jsonl의 `round` 필드는 그대로 유지.** 토론 로그는 실험 트랙 전용 파일이므로 일반화 불필요. 관찰 트랙은 debate 파일을 생성하지 않음 (원본 JSON의 요약 계층이 그 역할).

**적용**: 3일 스프린트의 모든 산출물은 v0.2 기준. v0.1로 이미 작성 중인 코드는 판정 결과 부분만 필드명 교체.
