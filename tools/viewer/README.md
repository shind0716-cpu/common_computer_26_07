# 팩트 생존 뷰어 — FastAPI 어댑터

파이프라인 계약 파일과 층1 계기를 읽는 읽기 전용 서버다. LLM 호출과 산출물 쓰기는 없다.
라이브 서버와 `scripts/make_pair_page.py`의 자기완결 HTML은 같은 `pair.html` 자산을 쓴다.

## 화면 구조: 3면

- `/` 두 판: 같은 이슈의 두 판을 나란히 놓고 FAR, 확산 지도, 갈린 칸, 발화 전문,
  근거 구성을 읽는다. 접이식 판 목록에서 각 실행의 조건·건강·베이스라인 자격도 확인한다.
- `/audit` 대조: 한 판의 판정 셀과 모든 발화 전문. 각 발화 옆 펼치기에 입력 전문을 흡수했다.
- `/biography` 전기: 팩트 하나의 사건 사슬.

옛 지도·장부·레이더 화면과 레이더 HTTP 창은 폐기했다. 다만 `/api/ledger`는 두 판 화면
재료 API로 유지하고, `modules/transmission.py`와 CLI·단위테스트는
논문 재현 트랙 계기로 그대로 남긴다.

## 실행

```bash
pip install -r tools/viewer/requirements.txt
python -m uvicorn tools.viewer.app:app --port 8011
```

브라우저에서 http://localhost:8011 을 연다.

다른 데이터 뿌리를 읽으려면 파일명 규칙은 바꾸지 않고 뿌리만 지정한다.

```bash
VIEWER_DATA=experiments/mini_h2_pilot/data python -m uvicorn tools.viewer.app:app --port 8012
```

Windows에서는 `run_viewer_pilot.bat`을 더블클릭하면 파일럿 데이터와 8012 포트로 실행된다.
화면 지위 배너가 실제 데이터 뿌리를 표시한다.

## API (전부 읽기 전용)

| 경로 | 내용 |
|---|---|
| `GET /api/runs` | 가용 run과 조건 좌표·판정 요약 |
| `GET /api/viewmodel/{issue}/{run}` | 전체 뷰모델 — 화면 없음(직독용) |
| `GET /api/issue/{issue}` | issue 원문 — 화면 없음(직독용) |
| `GET /api/facts/{issue}` | 팩트 목록 — 화면 없음(직독용) |
| `GET /api/assignment/{issue}` | 배분표 — 화면 없음(직독용) |
| `GET /api/analysis/{issue}/{run}` | survival 조건부 hazard·FAR·fact-clock — 화면 없음(직독용) |
| `GET /api/provenance/{issue}/{run}` | run 신원과 건강 상태 |
| `GET /api/biography/{issue}/{run}` | 팩트별 사건 사슬 |
| `GET /api/audit/{issue}/{run}` | 판정 셀·발화 전문·근접도 시선 유도·근거 등급 |
| `GET /api/inputs/{issue}/{run}` | v0.3 입력 전문 재조립과 지문 검증. v0.2는 absent |
| `GET /api/ledger/{issue}/{run}` | 재주입 블록과 라운드별 소실 목록(두 판 재료) |
| `GET /api/pair/{issue}/{a}/{b}` | 기존 audit·ledger·analysis 산출을 `crossrun.report()`로 조립한 두 판 대조 |


## 공유용 1장

```bash
VIEWER_DATA=experiments/mini_h2_pilot/data python scripts/make_pair_page.py \
  --issue issue_esa --a h2p_off --b h2p_v0
```

`viewers/pair_issue_esa_h2p_off_vs_h2p_v0.html`이 생긴다. 서버·네트워크 없이 열리며
발화 전문까지 생성 시점 값으로 구워진다.

## 경계

- 경로·파일명은 `modules/paths.py`를 통한다. `VIEWER_DATA`는 `paths.DATA` 뿌리만 바꾼다.
- `/api/pair`는 로그를 재파싱하지 않는다. 기존 재료 API를 조립하고 층2는 좌표만 맞춘다.
- FAR은 judgment `summary` 값을 그대로 옮기며 새 비율을 만들지 않는다.
- 파싱·계산 형태 드리프트는 0으로 숨기지 않고 HTTP 500으로 드러낸다.
- 근접도는 지표가 아니라 원문을 먼저 볼 위치를 고르는 표시다. 장부 on/off 팔 간 값을 직접
  비교하지 않는다.
