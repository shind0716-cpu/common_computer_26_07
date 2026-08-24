# 승격 관문 등급 분리 결정 패킷

작성일: 2026-08-20
작성 역할: Claude Code (owner 요청으로 안건 작성)
상태: **OWNER DECISION REQUIRED / 구현 전 / 신규 실호출 금지**
범위: 콘솔 승격 관문의 통과 기준만 다룬다. 재료 의미·정본 결정·spec 내용은 건드리지 않는다.

## 0. 이 문서의 효력과 승인 방법

이 문서는 관문 계약을 바꾸지 않는다. owner가 각 결정점에서 **선택지 하나만** 체크하고 마지막
서명란을 채워야 구현을 시작할 수 있다. 체크 안 된 결정은 `blocked`다.

이 안건은 검수·반입 절차라 노션 보드 안건이 아니다. owner 결정이 곧 확정이다.

### 발의 사유

owner 진술(2026-08-20): "애초에 실호출 이전에 파일럿도 돌려보려고 `data/issues`에 넣으면서
발생한 건데 기준을 좀 낮춰야 함."

## 1. 현재 상태 — 실측 2026-08-20 16:17

```text
명단 등재 7건 · 실행 가능 0건 · 콘솔 시나리오 목록 0건
```

| issue | state | 차단 사유 |
|---|---|---|
| `issue_throne` | candidate | 도장 없음 (그 외 전부 면제 기재) |
| `issue_throne_v2` | candidate | 도장 없음 · prior pending |
| `issue_award` | candidate | 도장 없음 (그 외 전부 면제 기재) |
| `issue_award_v2` | candidate | 도장 없음 · prior pending |
| `issue_polar` | candidate | 도장 없음 · spec·calibration 파일 없음 |
| `issue_polar_v2` | candidate | 도장 없음 · spec/calibration hash·version 미연결 |
| `issue_exile` | candidate | 도장 없음 · spec·calibration 파일 없음 |

부수 사실:

- `data/issues` 파일 11개 중 명단 등재 7개. 미등재 4개(`issue_camp`, `issue_esa`, `issue_hire`,
  `issue_hire_a6`)는 콘솔 감사표에 **행조차 나오지 않는다**. UI 문구는 "차단된 재료도 이유를
  숨기지 않고 보여준다"인데 이 4개는 이유 없이 사라진다.
- `issue_camp`은 solo 탭 기본 이슈인데 미등재라 `default_issue=None`이 된다.
- `ANTHROPIC_API_KEY`가 10자 자리표시자다. 콘솔 기본 모델 `claude-haiku`로는 실호출이 안 된다.
  `OPENAI_API_KEY`·`GEMINI_API_KEY`는 사용 가능하다.

## 2. 문제 진단

관문 하나가 성격이 다른 두 질문을 같은 기준으로 심사하고 있다.

```text
"이거 한번 돌려봐도 되나"        — 싸다. 틀리면 버리면 된다. 되돌릴 수 있다.
"이 수치를 주장해도 되나"        — 채점 기준표·독립 교정·사전조사·사람 서명이 필요하다.
```

지금은 두 번째 기준을 첫 번째에도 적용한다. 그래서 `data/issues`에 재료를 넣어 파일럿을
돌려보는 일 — 이 관문이 생긴 원래 계기 — 이 통째로 막혔다.

`issue_throne`이 이 어긋남의 표본이다. spec·calibration·prior가 전부 면제 사유까지 적혀 있고
남은 차단 사유가 도장 하나뿐인데, 그 면제 사유 문면이 `no new execution approval`이다. 즉
"안 돌릴 거니까 기준표가 없어도 된다"고 적어둔 재료라서, 그걸 근거로 실행 도장을 찍으면
서명이 자기 근거를 부정한다. 낮은 등급이 없으니 어느 쪽으로도 갈 데가 없는 상태다.

## 3. 안 — 문을 둘로 나눈다

| | 파일럿 문 | 확증 문 |
|---|---|---|
| 무엇에 쓰나 | 재료가 굴러가는지 본다 | 보고서·논문에 넣을 수치를 낸다 |
| 사람 도장 | 없음 | 필요 |
| 채점 기준표(spec) | 없어도 됨 | 필요 |
| 독립 교정(calibration) | 없어도 됨 | 필요 |
| 사전조사(prior) | 없어도 됨 | 필요 또는 명시 면제 |
| 기계가 보는 것 | 스키마 통과 · fact/배분 짝 · 콜 상한 · 라벨 | 위 전부 + 지문 + 기준표 + 교정 + 사전조사 + 서명 |
| 산출물 취급 | `unvetted` 라벨, 집계 기본 제외 | 정식 집계 대상 |

파일럿 문이 보는 네 가지는 전부 사람 없이 판정된다. 이미 있는 검사를 재배치하는 것이지
새 검사를 만드는 게 아니다.

### 3-1. 돈과 기록은 도장 말고 다른 것으로 막는다

- **돈** — 도장은 금액을 모른다. 콜 상한(숫자)으로 막는 게 맞다.
- **검수 안 된 수치가 보고서로 새는 것** — 실행을 막을 게 아니라 산출물에 라벨을 박아 막는다.
  스키마 v0.3이 개입 run을 `note_update.origin`으로 거르는 것과 같은 방식이다. 습관이 아니라
  필드다.

---

# 4. 결정점

## G-0. 등급 분리를 채택하는가

- [x] **G-0A (권고)** 파일럿/확증 두 등급으로 나눈다. 파일럿은 사람 도장 없이 통과한다.
- [ ] G-0B 현행 유지 — 모든 실행에 도장을 요구한다.
- [ ] G-0C 등급은 나누되 파일럿에도 도장을 요구한다(허들은 그대로, 기준만 완화).

**G-0B를 고르면 아래 결정점은 전부 무효다.**

## G-1. 파일럿 등급을 누가 부여하는가

- [x] **G-1A (권고·owner 안전 수정)** `data/issues`에 재료 3종이 들어오면 기계가 자동으로 파일럿 후보로 등재한다.
      지문은 등재 시점에 계산한다. 사람이 명단에 손으로 적을 일이 없다.
- [ ] G-1B 사람이 명단에 항목을 추가한다(도장은 아니고 등재만).

**G-1A의 부수 효과**: §5의 줄바꿈 지문 결함이 같이 사라진다. 지문을 손으로 옮겨 적지 않게 되기
때문이다. 다만 "명시 registry가 후보 집합"이라는 현행 설계 원칙과 정면으로 어긋나므로, A(gate
engineer) 담당분의 설계 근거를 다시 쓰는 작업이 따라온다.

**owner 안전 수정**: 자동 발견은 감사표와 기계검증 대상 등재까지만 수행한다. issue/facts/assignment
3종의 schema·identity·배분 무결성·현재 지문·콜 상한이 모두 통과하기 전에는 파일 존재만으로
파일럿 실행권한을 부여하지 않는다.

## G-2. 파일럿 콜 상한

참고 수치 — 협력 조건 3인 3라운드는 12콜, 수첩을 켜면 18콜, 최종 폴링까지 21콜이다.

- [x] **G-2A (권고)** 30콜. 한 시나리오 한 판을 넉넉히 돌리고 그 이상은 확증 문으로 보낸다.
- [ ] G-2B 60콜
- [ ] G-2C 다른 값: __________

상한이 없거나 상한을 넘기는 요청은 파일럿 등급에서 400으로 막는다.

## G-3. 파일럿 산출물 라벨

- [x] **G-3A (권고)** `run_meta`에 승격 등급 필드를 한 칸 추가하고, `condition` 앞에 `pilot/`을
      붙인다. 로그만 보고도 검수 안 된 재료였음을 알 수 있어야 한다.
- [ ] G-3B `run_meta` 필드만 추가한다.
- [ ] G-3C 라벨을 붙이지 않는다.

## G-4. 파일럿 등급에서 금지할 것

복수 선택.

- [x] **G-4A (권고)** accuracy·정답률·winner 산출 금지. `outcome_policy` 검사와 무관하게 등급으로도 막는다.
- [x] **G-4B (권고)** 보고서·발표 자료에 수치 인용 금지. 인용하려면 확증 문을 통과시킨다.
- [ ] G-4C judge 채점 금지(비용이 크므로 확증 문 전용으로 둔다)

## G-5. v1 재료의 면제 사유 문면

`issue_throne`·`issue_award`의 spec/calibration 면제 사유가 각각
`historical v1 development material; no new execution approval`,
`historical v1 development material; v2 package required`다.

- [x] **G-5A (권고)** 문면 그대로 둔다. 두 재료는 파일럿 등급으로도 돌리지 않는다.
- [ ] G-5B 문면을 고쳐 파일럿 등급을 허용한다. 고칠 문면: __________

**G-5A를 권고하는 이유**: 문면이 "새 실행 승인 아님"이라고 못 박고 있다. 파일럿이라도 그
문면과 어긋난다. 새로 돌릴 재료는 v2 쪽이 맞다.

---

# 5. 승인 여부와 무관하게 고쳐야 하는 결함

## 5-1. 지문이 이 컴퓨터에서만 맞는다 (P0)

`.gitattributes`가 `*.json text eol=lf`인데, 명단에 적힌 지문은 전부 **로컬 작업본(CRLF) 기준**으로
계산돼 있다. 같은 커밋을 새로 체크아웃해 대조한 결과다.

| 파일 | 로컬 CRLF 줄 | 명단에 적힌 지문 | 새 체크아웃 지문 |
|---|---|---|---|
| `detection_specs/issue_award_v2.json` | 392 | `cc71fe70…` | `40b4d5bf…` |
| `detection_specs/calibration_issue_award_v2.json` | 649 | `7a02bdea…` | `4ec16f69…` |
| `issues/issue_award_v2.json` | 15 | `5aa0fcce…` | `a43b1984…` |
| `facts/facts_issue_award_v2.json` | 208 | `d023a085…` | `dff21dee…` |
| `assignments/assignment_issue_award_v2.json` | 61 | `33c0e222…` | `f9fb873e…` |

영향:

- 팀원이 클론하면 material·spec·calibration 지문이 전부 mismatch로 차단된다.
- 깨끗한 체크아웃에서 전체 테스트가 19건 실패한다(`test_detection_spec`,
  `test_award_v2_detection_spec`, `test_console_gates` 등 — 전부 지문 비교). 현재 트리의 PASS는
  이 컴퓨터 한정이다.
- `TEAM_PROTOCOL` §5의 감사 항목 "material hash mismatch를 변조해 차단 확인"은, 변조 없이
  체크아웃만 바꿔도 mismatch가 나므로 이미 실질 실패 상태다. 세 차례 감사 모두 이걸 못 봤다
  (`AUDIT_console_promotion_claude_2026-08-20.md`에 줄바꿈 언급 없음).

**도장을 찍기 전에 고쳐야 한다.** 안 고치면 그 도장이 이 컴퓨터에서만 유효하다.

재현:

```bash
python -c "import hashlib,pathlib,subprocess as s; p='data/detection_specs/issue_award_v2.json'; print('worktree',hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()); print('git     ',hashlib.sha256(s.run(['git','show','HEAD:'+p],capture_output=True).stdout).hexdigest())"
```

## 5-2. 화면 결함 두 건

- 감사표 안내 문구가 "차단된 재료도 이유를 숨기지 않고 보여준다"인데, 명단 미등재 4개는 행이
  아예 없다. 문구를 고치거나 4개를 등재하거나 해야 한다.
- 변종 생성 안내 문구에 단항 `+`가 섞여 화면에 `NaN`이 찍힌다
  (`tools/console/index.html:503`).

## 5-3. 관문 밖에 남은 과금 경로 두 개

`/api/run`과 `/api/solo/run`은 관문을 거치지만 아래 둘은 거치지 않는다.

- `/api/judge/run` — 팩트×라운드×표 수만큼 과금
- `/api/intervene` — 이 프로세스에서 `llm.obtain_response` 직접 호출

운영 문서 §1의 "단일 입구" 서술과 어긋난다.

---

# 6. 승인 시 작업 순서

1. §5-1 지문 기준을 먼저 정하고 수리한다(담당: gate engineer A). 등급 분리보다 앞선다.
2. `scenario_gate`에 등급 판정을 넣는다. 실행 가능 state 4종 중 코드가 구별하는 것이
   `legacy_approved` 하나뿐이므로, `pilot_only`에 실제 의미를 주는 쪽이 깔끔하다.
3. `/api/run`·`/api/solo/run`에서 파일럿 등급이면 콜 상한을 강제한다.
4. `run_meta`에 등급 필드를 추가한다(스키마 문서 갱신 동반).
5. G-1A를 채택했으면 자동 등재를 붙인다.
6. 콘솔 화면에 등급을 표시한다. 파일럿 재료를 고를 때 "검수 안 된 재료"임이 보여야 한다.
7. §5-2·§5-3 수리.
8. 독립 감사를 다시 돌린다 — 파일럿 등급으로 상한을 넘기거나 라벨을 우회할 수 있는지.

# 7. 반대 논거

기록해 둔다. 채택하더라도 이 위험은 남는다.

- 파일럿 라벨이 붙은 결과가 시간이 지나면 그냥 "결과"로 인용될 수 있다. 라벨은 집계 코드가
  실제로 그 필드를 거를 때만 작동한다. 필드만 추가하고 집계를 안 고치면 무의미하다.
- "파일럿"이라는 이름으로 콜이 조금씩 새는 경로가 생긴다. 상한을 run 단위로 걸면 run을 여러 번
  나눠 돌리는 것을 못 막는다. 일 단위 누적 상한이 별도로 필요할 수 있다.
- 자동 등재(G-1A)는 "명시 registry가 후보 집합"이라는 현행 fail-closed 설계의 핵심 전제를
  뒤집는다. A 담당분의 설계 근거 문서를 다시 써야 한다.

# 8. 용어

| 문서 용어 | 쉬운 말 |
|---|---|
| registry | 검수 명단 |
| state = candidate | 도장 안 찍힘 |
| DetectionSpec / spec | 채점 기준표 |
| calibration | 기준표가 되는지 본 시험지 |
| prior | 모델이 원래 알던 건 아닌지 미리 재본 것 |
| material hash | 파일 지문 |
| 면제 (`required: false`) | "이건 안 재고 넘어간다" + 사유 한 줄 |
| fail-closed | 애매하면 막는다 |
| 실호출 | 진짜 돈 나가는 호출 |
| 0콜 / 드라이런 | 돈 안 쓰고 흉내만 내보기 |

---

# 서명

- 결정자: owner (`study_owner_user`)
- 결정일: 2026-08-20
- 비고: 권고 묶음 승인. G-1A는 자동 발견과 실행권한을 분리하는 owner 안전 수정 문면이 우선한다.

미체크 결정점이 하나라도 남아 있으면 구현을 시작하지 않는다.
