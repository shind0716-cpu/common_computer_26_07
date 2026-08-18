# WORKORDER — 실험 콘솔에 「단독 실험」 탭 추가 (2026-08-18, 민옥 트랙)

> 지위: 확정 작업 지시 (민옥 승인). 이 문서는 클로드 코드 세션이 이 작업을 수행하기 위한
> 완결 명세다. 시작 전에 리포 CLAUDE.md를 읽고 그 규칙을 전부 따르라 (특히: 경로는
> modules/paths.py, encoding="utf-8", 작업 후 WORKLOG.md 한 줄, 기존 줄 수정 금지).

## 0. 배경 (이 세션이 알아야 할 최소 맥락)

- `experiments/memory_structure/`는 단독 에이전트 기억 실험 트랙이다(민옥 소유). 러너
  `run_solo.py`는 CLI로 완결 동작하며, 2026-08-18에 v2 손잡이가 추가되었다:
  `--note-budget N`(수첩 예산), `--facts-reverse`(사실 역순), `--no-stance --final-poll`
  (입장 해제+최종 판단), `--allow-v2`(사전등록 관문), `--dry`(0콜 리허설).
  v2 run_id에는 접미사(b250·rev·ns)가 붙는다. 산출물: `runs/<model>/run_<id>.json`
  (essays·notes·recall·final_poll) + `.partial.jsonl`(호출 단위 프롬프트·응답 원문).
- `tools/console/`(app.py + index.html)은 민옥 소유의 실험 콘솔이다. 현재 debate
  파이프라인만 실행한다. 서브프로세스 실행(_proc 1개, 동시 실행 방지)·로그 스트림
  (/api/log)·중지(/api/stop) 골격이 이미 있다 — 재사용하라.
- 채점 산출물: `experiments/memory_structure/judgments/<model>/judge_<id>.json`
  (records: essay_r0..r3·carrier, 사실 12개 × status mentioned/unmentioned, votes 보존).
- 배경 문서(참고): EXPERIMENT_GUIDE_후속실험-v1.md(무엇을 왜 돌리나),
  PROMPTS_v2_draft.md(v2 프롬프트 정본 초안), 왜 문서·재현 가이드(노션).

## 1. 목표

콘솔에 「단독 실험」 영역(탭 3개)을 추가한다. 팀원이 run_console.bat 더블클릭 →
브라우저에서 (a) 기존 54런을 눈으로 보고 (b) 후속 실험을 조건 폼으로 실행할 수 있게.

### 탭 1 — 실행
- 조건 폼: 모델(gpt/gemini-flash), 진행(A/P/B 다중 선택), 기억(full/note/prev 다중 선택),
  반복(기본 1,2,3), v2 손잡이: 수첩 예산(500/250/125/60 선택), 사실 역순 토글,
  입장 해제+최종 판단 토글(final_poll은 no-stance와만 켜짐 — 러너와 같은 제약).
- 실행 전 견적: 호출 수 산식 = 런 수 × (full/prev 5콜, note 8콜) + final_poll 시 런당 1콜.
  화면에 "총 N런 · 약 M콜" 표시.
- 드라이런 버튼(0콜)과 실행 버튼 분리. **v2 조건 실행 시**: "PROMPTS_v2·PREREG_v2를
  로컬 커밋했습니까?" 확인 체크박스를 켜야 실행 가능 — 체크 시에만 `--allow-v2`를
  붙인다. **UI가 이 플래그를 자동으로 켜서는 안 된다** (사전등록 관문의 무력화 금지).
- 실행은 `run_solo.py`를 서브프로세스로(`sys.executable -X utf8 <경로> <인자들>`),
  기존 _proc/_log 골격 재사용(동시 실행 1개 원칙 유지).

### 탭 2 — 결과 (런 뷰어)
- `experiments/memory_structure/runs/<model>/` 스캔 → 런 목록(최신순, v1/v2 접미사와
  meta 요약: note_budget·facts_order·stance·final_poll 표시). `_dry`는 별도 표시.
- 런 클릭 → 라운드별 화면: 발화 원문, (note 조건) 수첩 원문 + **글자 수와 여백**
  (예: "251자 · 여백 249자") — 발견 ④(자리가 남는데 버림)가 화면에서 보이게.
- final_poll이 있으면 원문 그대로 표시(자동 정오 판정은 이 작업 범위 밖).

### 탭 3 — 생존 격자
- judgments가 있는 런에 한해 사실(12행) × 시점(r0~r3·carrier) 격자를 그린다.
  셀 = status(mentioned 진하게 / unmentioned 비움). 조건 단위 집계(3런 겹침 농도)는
  여유 있으면. 스타일 참고: `experiments/memory_structure/analysis/
  본실험-2모델-생존리포트-2026-08-11.html`. LLM 호출 0, 재계산은 파일 읽기만으로.

## 2. 금지·제약 (어기면 반려)

1. 기존 debate 관련 라우트·동작·index.html 기존 화면을 바꾸지 마라. 추가만 한다.
2. `run_solo.py`·PROMPTS·PREREG·runs/·judgments/를 수정하지 마라. 콘솔은 러너를
   호출하고 산출물을 읽기만 한다. 러너 인터페이스가 부족하면 고치지 말고 보고하라.
3. `--allow-v2` 자동화 금지(위 §1). 드라이런 기본 유도(실행 버튼보다 드라이런이 앞에).
4. 경로 하드코딩 금지 — solo 산출물 경로는 상수 한 곳에 모아라(paths.py 수정은 금지,
   콘솔 로컬 상수로).
5. 테스트: 기존 스모크 전체 통과 + 신규 라우트 테스트 추가(파일 스캔·견적 산식·
   allow-v2 미체크 시 실행 거부). 콘솔 기동·탭 렌더를 브라우저로 실측하라.

## 3. 인수 기준 (전부 만족해야 완료)

- [ ] run_console.bat 더블클릭 → 단독 실험 탭 3개가 뜬다
- [ ] 기존 54런이 결과 탭·생존 격자 탭에 보인다 (v1 산출물 무변경 확인)
- [ ] 드라이런 버튼으로 0콜 실행이 되고 로그가 흐른다
- [ ] v2 조건은 확인 체크 없이 실행되지 않는다
- [ ] 기존 debate 실행 경로 회귀 없음 (스모크 통과)
- [ ] WORKLOG.md 한 줄 추가 (날짜 | 민옥(Claude Code) | 한 일 | 다음)

## 4. 범위 밖 (하지 말 것)

final_poll 자동 정오 판정 · analyze_solo v2 분기 확장 · 개입 모드의 solo 이식 ·
뷰어(tools/viewer) 수정 · 채점 실행 UI(judge는 CLI 유지). 전부 다음 작업이다.
