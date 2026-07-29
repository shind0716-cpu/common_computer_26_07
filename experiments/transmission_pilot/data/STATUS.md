# STATUS — transmission_pilot 산출물 지위

> 규칙: `docs/WORKING_RULES.md` R7. **append-only** — 지위가 바뀌면 위를 고치지 않고 아래에
> 줄을 추가한다. **파일명은 바꾸지 않는다**(참조가 깨짐).
> 이 폴더의 파일을 인용하기 전에 이 표를 먼저 볼 것.

| 날짜 | 파일 | 층 | 지위 | 근거 |
|---|---|---|---|---|
| 07-29 | `access_report_issue_{carkey,esa}_tp1.json` | 파생 | **재검토 대상 — 인용 금지** | 판정기 감사 H1(`experiments/instrument_check/`): 재판정 n=5에서 `fact_car_04` s0가 **5:0으로 뒤집힘**. 접근 창은 판정 결과에서 재구성되므로(`window_source: reconstructed`, `n_from_assembly: 0`) 판정 하나가 뒤집히면 타임라인·음영 쌍이 통째로 바뀐다 |
| 07-29 | `transmission_report_issue_{carkey,esa}_tp1.json` | 파생 | **재검토 대상** | 위와 같은 judgment에서 유도. `fact_car_04` 뒤집힘이 사실이면 노출 쌍(TSR 분모)이 달라진다 |
| 07-29 | `judgment_issue_{carkey,esa}_tp1.json` | **원자료** | 유효 — 단 파일럿 판정기 | API 응답 원본이라 보존. 다만 gpt-5.4-mini·temp0·**n=1**이며 팀 확정 judge가 아니다. 절대 수치는 탐색적, 재판정 결과와 함께 읽을 것 |
| 07-29 | `debate_issue_*_tp1.jsonl` · `prior_issue_*_tp1.json` · `question_scan_*_tp1.json` | **원자료** | 유효 | API 응답 원본. 오늘 원문 대조·재판정의 근거이며 그 자체는 흔들리지 않았다 |

## 재생성 경로 (파생물)

- `transmission_report_*`: `python experiments/transmission_pilot/run_pilot.py --phase analyze --issue {carkey|esa}`
- `access_report_*`: **저장된 명령 없음 — 인라인 실행으로 생성됐다.** `modules.access_window.report(
  judgment, assignment, events, facts_by_id, question_exposed_ids=...)`를 tp1 입력으로 호출하면
  재생성된다. *이것이 R7이 막으려는 사례다 — 파생물을 커밋하면서 재생성 경로를 남기지 않았다.*

## 지위 어휘

- **유효**: 그대로 인용 가능
- **재검토 대상**: 인용 금지. 재검토가 끝나면 이 표에 결과 줄을 추가한다
- **의도적 보존**: 더 이상 쓰지 않지만 지우지 않는다(재현성·감사 근거). 사유를 근거 열에 명시
