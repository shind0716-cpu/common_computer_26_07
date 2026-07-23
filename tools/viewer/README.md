# 팩트 생존 뷰어 — FastAPI 어댑터

민옥의 `modules/viewmodel.py`(계약)를 소비하는 **읽기 전용 서버 어댑터**.
`scripts/make_viewer.py`(정적 HTML 생성)와 형제 — 같은 `build_viewmodel()`을 먹는다.
설계 §2 경계 원칙: LLM 호출 0, 산출물 쓰기 0.

화면은 **파이프라인 지도(내비게이션)** — 7모듈 다이어그램의 노드를 클릭하면
그 단계 산출물이 선택된 run 기준으로 열린다. 아키텍처(지도)와 데이터(생존 매트릭스·분석)를 한 화면에.

## 정적 생성 대비 실익
- **run 목록/브라우징** — `data/judgments/` 를 스캔해 4파일(issue·facts·judgment·debate) 완비된 run 을 자동 노출.
- **라이브 직독** — 새 run 이 빌드 없이 드롭다운에 등장.
- **파이프라인 내비** — 노드 클릭으로 단계별 산출물 탐색.

## 실행 (리포 루트에서)
```
pip install -r tools/viewer/requirements.txt
uvicorn tools.viewer.app:app --port 8011
```
→ 브라우저에서 http://localhost:8011

## API (읽기 전용)
| 경로 | 노드 | 내용 |
|---|---|---|
| `GET /` | — | 파이프라인 지도 화면 |
| `GET /api/runs` | — | 가용 run 목록(issue·run·judge·far 요약) |
| `GET /api/viewmodel/{issue}/{run}` | 토론엔진·채점기·장부 | 전체 뷰모델(발화·매트릭스·재주입) |
| `GET /api/issue/{issue}` | 데이터 로더 | issue.json(title·body·source_meta) |
| `GET /api/facts/{issue}` | 팩트 추출기 | facts.json(text·tags·critical·prior) |
| `GET /api/assignment/{issue}` | 배분기 | assignment.json(seed·agents) |
| `GET /api/analysis/{issue}/{run}` | 분석·리포트 | survival 지표(조건부 hazard·FAR·fact-clock) — 순수 계산 |

## 노드 ↔ 데이터
- 데이터 로더 → issue 본문 / 팩트 추출기 → 팩트+prior / 배분기 → 8에이전트 배분
- 토론 엔진 → 라운드별 발화 / 채점기 → 생존 매트릭스 / 분석 → FAR·hazard·fact-clock
- 장부·게이트 → 재주입/게이트 이벤트. **ledger off(대조군) run은 이벤트 0건 → 빈 상태로 on/off를 실증.**

## 경계 (설계 §2)
- 완전 읽기 전용. 산출물에 쓰지 않는다. 민옥 파일(viewmodel.py, make_viewer.py, viewer_template.html) 무수정.
- 파싱/계산 실패 = 스키마 드리프트 신호 → HTTP 500 에 명시.
- `build_viewmodel`·`/api/analysis` 는 debate·judgment·facts 를 **같은 run_id 로** 읽는다(run_id 정렬 필요).
- `/api/analysis` 는 `survival`(순수 함수) 재계산 — 산출물 파일 안 씀, paths.py 에 analysis 경로 관례 불필요.
