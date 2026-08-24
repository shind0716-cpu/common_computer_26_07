# 압박 실험 — 처음 돌리는 사람용 (5분 안내)

> 이 실험이 뭔지: AI 하나에게 "너에게는 이 세 가지가 중요하다"를 주고, 상대(고정 각본)가
> 라운드마다 압박한다. AI 는 라운드마다 수첩(500자)만 들고 가고, 마지막에 최종 선택을 한다.
> 우리가 보는 것: **어떤 가치 카테고리의 주장이 먼저 사라지는가 + 선택이 뒤집히는가.**
> 배경·판정 기준은 PREREG_v0.md — 실행 전에 한 번 읽으세요.

## 콘솔로 돌리기 (권장)

1. 리포 루트에서 `run_console.bat` 더블클릭 → 브라우저에서 「압박 실행」 탭.
2. 조건 고르기 (시나리오 · 각본 C0/C1/C2 · 가치 세트 A/B · 반복) → 화면의 견적(콜 수) 확인.
3. **드라이런(0콜)** 먼저 — 프롬프트 문면이 runs/_dry/ 에 남습니다. 열어서 눈으로 확인.
4. 실호출은 PREREG_v0.md 가 로컬 커밋된 뒤, 확인 체크를 켜야 실행됩니다.
   (콜 예산 관행: 실행 전 콜 수를 적고 승인받기 — 워크오더 방식은 PREREG §4)
5. 결과는 「압박 결과」 탭 — 라운드별 글·수첩 원문과 최종 선택.

## 명령줄로 돌리기

```bash
# 0콜 리허설 (아무 때나 안전)
PYTHONUTF8=1 python experiments/pressure_category/run_pressure.py --dry

# 재료 검사만 (0콜)
PYTHONUTF8=1 python experiments/pressure_category/check_materials.py

# 실호출 (PREREG_v0.md 커밋 후 · .env 에 키 필요)
PYTHONUTF8=1 python experiments/pressure_category/run_pressure.py --model gpt --reps 1 --allow-live

# 클로드 모델로 (.env 에 ANTHROPIC_API_KEY 가 들어온 뒤 — 키 없으면 시작 전에 멈춘다)
PYTHONUTF8=1 python experiments/pressure_category/run_pressure.py --model claude-haiku --reps 1 --allow-live

# 채점 (0콜 — 표식 스캔 + 뒤집힘 집계)
PYTHONUTF8=1 python experiments/pressure_category/scan_pressure.py
```

## 내 시나리오로 돌리기

기본 재료(수련원)를 그대로 쓸 필요 없다. 원하는 주제로 시나리오를 만들어 돌릴 수 있다:

1. `materials/MATERIALS_TEMPLATE.json` 을 복사해 `materials/<이름>.json` 으로 저장.
2. 빈칸 채우기 — 선택지 2개, 카테고리(짝수 개), 카테고리마다 사실 2개 + 고유 표식,
   가치 세트 A·B(카테고리 반분, 정렬 답은 서로 반대). 자세한 규칙은 템플릿 맨 위 `_안내`.
3. 검사: `PYTHONUTF8=1 python experiments/pressure_category/check_materials.py materials/<이름>.json`
4. 통과하면 콘솔 시나리오 목록과 러너 `--materials` 에 자동으로 뜬다.
   산출물은 `runs/<모델>/<issue_id>/` 로 갈려서 남의 결과와 섞이지 않는다.
5. **실호출 전에 문면 사람 검수**(민감한 표현·집단 일반화 여부)는 네 몫이다.
   각본(C0/C1/C2) 문면은 웬만하면 그대로 — 시나리오끼리 비교하려면 압박 문면이 같아야 한다.

## 내 압박 문면으로 돌리기 (각본 등록)

압박을 **어떤 말로, 언제** 주는지도 실험 대상이다. 콘솔 「압박 실행」 탭의
「새 각본 등록」에서 직접 지을 수 있다:

- 라운드 1~3에 각각 다른 대사(점증 압박) 가능 — 비우면 직전 대사가 반복된다.
- 시작(라운드 0) 대사를 적으면 사실을 읽는 시점부터 압박이 들어간다 (기본은 r0 압박 없음).
- 대사에 `{TARGET}`(미는 쪽)·`{OTHER}`(반대쪽)를 쓰면 가치 세트에 맞춰 자동으로 채워진다.
- **등록은 새 이름으로 추가만** — 기존 각본은 못 고친다(과거 런과의 대응 보존).
  파일로는 `scripts/<id>.json` 에 저장되고, 러너 `--scripts <id>` 로도 쓸 수 있다.
- 주의 둘: ① 대사에 재료의 표식(사실 문면)을 넣으면 러너가 거부한다 — 상대가 사실을
  다시 알려주는 셈이라 측정이 무효가 되기 때문. ② 각본이 다르면 **같은 각본끼리만**
  비교할 수 있다 — C0(대조)는 웬만하면 항상 같이 돌려라.

## 규칙 4줄 (이 폴더의 규율 — 정찰 폴더 계승)

1. 실호출 전에 콜 수를 적고 사람 승인. 드라이런은 언제나 자유.
2. 기존 런·표는 수정하지 않고 덧붙인다. 정정도 새 글로.
3. 원자료(프롬프트·응답 전문)는 전량 보존 — 요약 저장은 이 프로젝트가 연구하는 바로 그 실패다.
4. 스캔 수치는 1차 집계다 — 뒤집힘·판독불가 판은 반드시 원문을 눈으로 확인.

## 파일 지도

| 파일 | 역할 |
|---|---|
| PREREG_v0.md | 사전등록 (질문·조건·판정 기준·예측) — 정본 |
| MATERIALS_v0.json | 기본 재료 (수련원 — 사실 12·가치 세트·각본) |
| materials/ | 팀원 시나리오 자리 (*.json 자동 등록) + 작성 템플릿 |
| check_materials.py | 재료 검사 3종 (0콜) |
| run_pressure.py | 러너 (판당 8콜, 체크포인트·상한·드라이런) |
| scan_pressure.py | 채점 스캐너 (0콜) → scan_table.md |
| runs/ | 산출물 (원문 전량. _dry/ 는 리허설) |
