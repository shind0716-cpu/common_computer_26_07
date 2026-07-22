# FAR 정의 교체 계획서 (기업 회신 시 실행)

> 기업 확인(패키지 A Q: **FAR 수식 방향**)이 회신되면 현행 **잠정** FAR 정의를 교체한다.
> 이 문서는 (1) 현행 정의를 **원문 인용으로 고정 기록**하고, (2) 교체 시 손대야 할 지점을
> **파일:줄로 전수** 정리하며, (3) 회신 전에도 비교 실행이 막히지 않는 이유를 밝힌다.
> 신규 파일이며 기존 코드·문서를 수정하지 않는다.

---

## 1. 현행 잠정 FAR 정의 — 원문 인용(고정 기록)

### 1-1. `SCHEMA.md` 「FAR 정의 — 스프린트 잠정 확정 (2026-07-22, 민옥/리더)」 (SCHEMA.md:35–44)

> - **방향**: 손실↑ = FAR↑ (FAR = 소실 팩트 수 / 대상 팩트 수). 값이 클수록 사실 보존이 나쁨.
> - **소실 판정**: status ∉ SURVIVING. 스프린트 SURVIVING = {mentioned, accepted}. 즉 unmentioned·refuted·ignored = 소실.
> - **critical 한정**: far_critical = 위 식을 facts[].critical=true 팩트로만 집계.
> - Ledger v0의 '소실=재주입 대상' 정의는 이 SURVIVING과 **동일 소스**를 쓴다(modules/ledger.MISSING = status ∉ SURVIVING). judge와 ledger가 같은 잣대를 쓰도록 강제.

그리고 교체 트리거 문장(SCHEMA.md:36):

> **기업 확인(패키지 A Q: FAR 수식 방향) 회신 시 이 절과 judge.py의 SURVIVING/far()를 교체한다.**

### 1-2. `modules/judge.py` — 잣대 상수 (judge.py:35–37)

> ```
> # 잠정(TODO: FAR 수식 확정) — '살아남음'으로 볼 status. 나머지는 소실로 집계.
> # 동범.md 열린 질문 "FAR 수식 방향(선결)" 확정되면 이 한 줄과 far() 만 교체하면 됨.
> SURVIVING = {"mentioned", "accepted"}
> ```

### 1-3. `modules/judge.py` — `far()` 수식 (judge.py:193–203, 독스트링 발췌)

> ```
> def far(fact_records, facts_by_id, *, critical_only=False):
>     """소실률 = 소실 팩트 수 / 대상 팩트 수. '소실' = status not in SURVIVING.
>     TODO(FAR 수식 미확정): refuted 를 소실로 볼지, unmentioned 만 셀지 등은 노션 확정 대기.
>     현재 잠정: SURVIVING={mentioned,accepted} 외 전부 소실."""
> ```

---

## 2. 교체 지점 전수 목록 (`grep`으로 `SURVIVING` / `far(` import·호출)

**설계 의도 = 단일 소스**: SCHEMA.md:44가 강제하듯 잣대는 `judge.SURVIVING`(+ `judge.far`)
한 곳에만 정의되고, 다른 모듈은 전부 여기서 **import** 한다. 따라서 값만 바꾸는 교체라면
**편집은 정의 지점 3곳뿐**이고 나머지는 자동 전파된다. 아래는 그럼에도 회귀 검토가 필요한
지점까지 **전수** 나열한 것이다.

### A. 정의 지점 — 반드시 편집 (3곳)

| 파일:줄 | 내용 | 편집 성격 |
|---|---|---|
| `modules/judge.py:37` | `SURVIVING = {"mentioned", "accepted"}` | 잣대 집합 교체(핵심 1줄) |
| `modules/judge.py:193–203` | `far()` 수식 본문 | 방향/분모 정의 바뀌면 본문 교체 |
| `SCHEMA.md:35–44` | 「FAR 정의」 절 (문서) | 확정 내용으로 새 버전 절 추가(append) |

### B. 전파 지점 — `SURVIVING` import·사용 (편집 불필요, 검토만)

| 파일:줄 | 종류 | 비고 |
|---|---|---|
| `modules/ledger.py:27` | import `SURVIVING` | 단일 소스 자동 전파 |
| `modules/ledger.py:56` | 사용 (`missing_facts`) | 재주입 대상 정의가 함께 이동 — **의도된 결합** |
| `modules/survival.py:31` | import `SURVIVING, far` | **⚠ 수정 금지 파일** — 자동 전파로 충분 |
| `modules/survival.py:76, :78, :120, :124` | 사용 (P2 지표) | 자동 전파 |
| `modules/judge.py:202` | `far()` 내부 사용 | A와 함께 이동 |

### C. 전파 지점 — `far()` 호출 (편집 불필요, 검토만)

| 파일:줄 | 호출 | 비고 |
|---|---|---|
| `modules/judge.py:254, :255` | `far(recs, ...)` / `far(..., critical_only=True)` | 시그니처 유지 시 무변경 |
| `modules/survival.py:139` | `far(st..., critical_only=...)` | 병기 FAR — 자동 전파 |

### D. 테스트 — 하드코딩된 값이라 **교체 시 반드시 갱신** (회귀 방지)

| 파일:줄 | 내용 | 교체 영향 |
|---|---|---|
| `tests/test_ledger.py:46` | `assertEqual(SURVIVING, {"mentioned","accepted"})` | **집합값 단언 → 새 값으로 갱신 필요** |
| `tests/test_ledger.py:20, :61` | import·소실 케이스 | 새 잣대에 맞게 케이스 재확인 |
| `tests/test_survival.py:91` | `assertEqual(far(...), 0.5)` | **수식 바뀌면 기대값 갱신 필요** |
| `tests/test_survival.py:178, :179` | `far_by_stage` 값 대조 | 수식 의존 — 값 재확인 |
| `tests/test_survival.py:20, :227, :236` | import·`far_by_stage` 호출 | 검토 |
| `tests/test_survival.py:48` | `assertIs(survival.SURVIVING, judge.SURVIVING)` | **정체성 단언 → 값 바뀌어도 통과**(단일 소스 보증, 갱신 불필요) |

### 지점 개수 요약

- **정의 지점(반드시 편집): 3곳** (`judge.py:37`, `judge.py:193–203` far 본문, `SCHEMA.md` 「FAR 정의」 절)
- **전파 지점(검토만, 자동 전파): 코드 11곳** — `SURVIVING` 7곳(ledger 2·survival 5) + `far` 호출 4곳(judge 2·survival 1은 위 표대로 총 4)
- **테스트 갱신 필요: 최소 2곳**(`test_ledger.py:46`, `test_survival.py:91`) + 값 재확인 4곳
- **불변 보증 1곳**: `test_survival.py:48`(정체성 단언) — 단일 소스라 값이 바뀌어도 통과

`grep` 근거: `SURVIVING` 매치 파일 = judge/ledger/survival + test_ledger/test_survival,
`far(` 매치 = judge(정의·호출)/survival(호출)/test_survival(호출). **survival.py는 수정 금지
목록이며, 단일 소스 전파 덕분에 실제로 손댈 필요가 없다.**

---

## 3. 회신 전에도 비교 실행이 막히지 않는 이유

판정 프로토콜 v0.1과 SCHEMA.md 「FAR 정의」의 미니 H2 기준에 따른다.

1. **주지표는 조건부 소실률(P2)이지 절대 FAR이 아니다.** on/off·(a)/(b) 비교는 **동일
   judgment 내 stage 간 상대 패턴**(전이 hazard가 후반에 상승하는가 등)으로 이뤄지며,
   이는 `SURVIVING`의 **절대값이 아니라 잣대의 일관성**에만 의존한다. 세 지표가 같은
   `judge.SURVIVING`을 공유(§2)하므로 잣대가 잠정이어도 상대 비교는 유효하다.
2. **SCHEMA.md 미니 H2 판정 기준**은 "절대 수치 신뢰는 유보, on의 far_critical이 off보다
   낮은지 등 **상대·곡선 비교**로 판정"이라 명시한다(SCHEMA.md:42–43). 즉 잠정 잣대로도
   H2 비교 실행이 성립한다.
3. **교체는 방향을 뒤집지 않는지 확인하는 재실행**으로 충분하다. 회신 후 §2-A 3곳을 바꾸고
   `scripts/run_ucurve_reanalysis.py`를 동일 judgment에 재실행해, `docs/analysis/UCURVE_PREREG.md`
   의 판별 방향이 유지되는지만 대조하면 된다(주2 연계).

**결론**: 기업 회신은 **절대 수치 확정**에 필요할 뿐, 회신 전에도 조건부 지표 기반 비교
실행과 (a)/(b) 판별은 **차단되지 않는다.**
