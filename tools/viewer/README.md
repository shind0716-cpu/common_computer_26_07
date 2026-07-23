# 🌸 팩트 생존 뷰어 — FastAPI 어댑터 (카와이 판)

민옥의 `modules/viewmodel.py`(계약)를 소비하는 **읽기 전용 서버 어댑터**.
`scripts/make_viewer.py`(정적 HTML 생성)와 형제 — 같은 `build_viewmodel()`을 먹는다.
설계 §2 경계 원칙: LLM 호출 0, 산출물 쓰기 0.

## 정적 생성 대비 실익
- **run 목록/브라우징** — `data/judgments/` 를 스캔해 4파일(issue·facts·judgment·debate) 완비된 run 을 자동 노출. 파일 N개 재생성 불필요.
- **라이브 직독** — 새 run 이 빌드 없이 드롭다운에 등장.

## 실행 (리포 루트에서)
```
pip install -r tools/viewer/requirements.txt
uvicorn tools.viewer.app:app --port 8011
```
→ 브라우저에서 http://localhost:8011

## API (읽기 전용)
| 경로 | 내용 |
|---|---|
| `GET /` | 카와이 뷰어 화면 |
| `GET /api/runs` | 가용 run 목록(issue·run·judge·far 요약) |
| `GET /api/viewmodel/{issue}/{run}` | 해당 run 의 전체 뷰모델(JSON) |

## 경계 (설계 §2)
- 완전 읽기 전용. 파이프라인 산출물에 쓰지 않는다.
- 뷰모델 파싱 실패 = 스키마 드리프트 신호 → 화면/HTTP 500 에 명시.
- `build_viewmodel` 은 debate·judgment·facts 를 **같은 run_id 로** 읽는다(run_id 정렬 필요).
