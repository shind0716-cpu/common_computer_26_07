# 판정 축 대조 — 저자 축 vs 우리 축 (2026-08-10, 요한)

지위: **실측 기록** (파일럿 1건 · 실호출 32회 · 코드 변경 0)
대상: `issue_esa` / `논문재현콜` (실호출 발화 32건, 빈 발화 0)
판정 모델 고정: `gpt-5.4-mini`, temperature 0 — **축만 다르게** 했다(모델 효과 배제).

## 왜

논문 재현 트랙 대조에서 두 파이프라인의 **판정 축이 다르다**는 것이 드러났다.

| | 저자 `evaluation.evaluate_facts` | 우리 `modules.judge` |
|---|---|---|
| 판정 단위 | 발화 1건 × 전체 팩트 목록 | 팩트 1개 × 라운드 전체 발화 |
| 출력 | `{"matched_fact_ids": [...]}` | `{status, agents_mentioning, reason}` |
| 표 | n=1 | n_votes=3 다수결 |
| 호출 수(이 run) | **32** | **144** (12팩트 × 4stage × 3표) |

같은 로그를 두 축으로 채점해 격자가 갈리는지 본다. 저자 프롬프트는 원본
저장소에서 그대로 읽는다(`modules.authors_prompts` 계승 원칙 — 복사 금지).

## 실행

```
python -m experiments.judge_axis.axis_probe --issue issue_esa --run 논문재현콜 \
    --max-calls 40 --out-dir experiments/judge_axis
python -m experiments.judge_axis.axis_compare --issue issue_esa --run 논문재현콜 \
    --ckpt experiments/judge_axis/author_axis_issue_esa_논문재현콜.jsonl \
    --out experiments/judge_axis/axis_compare_issue_esa_논문재현콜.json
```

`--offline` 은 실호출 0의 결정론적 스텁(하네스 배관 검증 전용, **수치 인용 금지**).
호출 상한과 발화 단위 체크포인트가 있어 중단·재개된다(CLAUDE.md 비용 주의).

## 실측 (파일럿 1건 — 가설 언어 금지)

- **셀 수준(팩트×라운드 48칸) 일치 47/48 = 0.979.** 최종 FAR 두 축 모두 0.3333.
- 유일한 갈림 `r2 · fact_esa_07`(월 40달러): 저자 축 mentioned(agent_6) vs 우리 축
  unmentioned(3표 만장일치). **원문 대조 결과 agent_6 r2 발화에 비용 언급이 없다** —
  저자 축의 오검출이며, 저자 프롬프트 자신의 규칙("부분적으로만 뒷받침되면 선택하지
  말 것")에 걸린다. 이 한 칸이 `far_critical` 을 0.1111 ↔ 0.0 으로 흔든다.
- **화자 수준은 갈린다.** 화자 집합이 다른 셀 9개 · 우리 축이 빠뜨린 화자 8명분 ·
  우리만 센 화자 2명분. 표본 검증 3건(`r2 agent_8/esa_03`·`r2 agent_8/esa_08`·
  `r1 agent_7/esa_01`) **전건 실재** — 발화 원문에 해당 팩트가 그대로 있다.
  셀 판정은 다른 화자가 대신 세어져 안 흔들리지만, **화자 단위 지표(전달 폭·
  agent×fact 격자·근접도 플래그)는 우리 축 위에서 과소 계상된다.**
- **기각된 가설**: `uncounted_high` 플래그(뷰어 `esa_01 r0`, 근접도 0.6·0.467인
  agent_2·agent_8이 센 명단에서 빠짐)가 축 때문이라고 의심했으나, **저자 축도 두 명을
  미표현으로 판정**했다(두 축 일치). 그 플래그는 근접도 휴리스틱의 오경보다.
  축에서 오는 누락은 실재하지만 그 셀은 아니었다.

## 한계

판 1개 · 이슈 1개 · 판정 모델 1종 · 발화 32건. 저자 축은 n=1 이라 그 오검출 1건이
재현되는지 확인하지 않았다(같은 축을 3번 돌리면 갈리는지가 다음 질문). 이 수치로
"어느 축이 옳다"를 말할 수 없다 — 말할 수 있는 것은 **셀 판정은 거의 같고 화자
명단은 체계적으로 다르다**는 것뿐이다.

---

## 결함 기록 — 재사용 금지 (2026-08-10 append, PR#34 리뷰 실측)

이 폴더는 **종결된 기록**이다(요한 방침 8/10: 종결 러너는 증거물 — 결함 있는 채로가
정직하다. 수정하지 않고 기록만 남긴다). 위 실측 수치의 provenance 로는 유효하나,
**러너를 재사용하지 말 것.** 리뷰에서 실측 재현된 결함:

1. `axis_probe.py --offline` 이 **라이브 체크포인트를 오염**시킨다 — 체크포인트가
   mode/model/prompt 와 무관하게 같은 파일·같은 tag 를 쓰므로, offline 후 실호출하면
   32건 전부 `offline_stub` 를 0콜 재사용한다(모델을 바꿔도 동일).
2. `axis_probe.py` 에 **preflight 부재** — 자격증명/SDK 실패가 정상 체크포인트의
   `parse_fail` 로 저장되고 재개 시 계속 건너뛴다.
3. `axis_compare.py` 가 **부분 체크포인트를 완전한 실험으로 집계**한다 — 행 수·
   화자×라운드 완전성을 검증하지 않아 32발화 중 9행만 있어도 지표를 출력하고,
   parse_fail 의 미지 매치가 사실상 absence(소실)로 계상된다.

같은 계열 결함의 **수정본은 현행 트랙에 있다**: 좌표 지문 체크포인트
(`paper_repro/extract_facts.CallCheckpoint`), dry/live 격리(`probe_extract`),
재사용 관문(`rehearse_splice.check_*`), parse_fail=모름 정책
(`paper_repro/bridge.author_rows_to_judgment`). 이 축 대조를 다시 하려면
저 부품들 위에서 새로 지어라.
