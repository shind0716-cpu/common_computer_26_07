# throne 파일럿 실행 계보 — 실제 호출 55행 / 저장 응답 54개

작성: 실행 에이전트(파일럿을 실제로 돌린 코딩 에이전트) · 2026-08-20
지위: **탐색적 E2E/측정자 검사 파일럿의 실행 기록** — 확증 tranche 아님
근거: HANDOFF_throne_pilot_agent_conversation_2026-08-20.md 「정정된 작업 배분 · 실행 에이전트」

## 이 문서가 답하는 것

Hermes 감사가 `모델·호출 격리 provenance: UNVERIFIED`로 둔 자리를, 실행 당사자만 아는
정보로 채운다. **저장소에서 확인되는 것과 실행 세션 기록에서만 확인되는 것을 구분해서
적는다.** 후자는 독립 검증이 안 되므로 감사 판정을 뒤집지 않는다.

| 항목 | 값 | 근거 |
|---|---|---|
| 호출별 새 컨텍스트 | **그렇다** — 호출마다 하위 에이전트를 새로 세움 | 세션 기록(agent ID 55개, 아래 표) · 저장소 **미수록** |
| 실제 모델 | `requested_label=claude-haiku-4-5` · `provider_verified=false` | 요청 측만 기록. 공급자 응답 메타 없음 |
| 온도 | **`unspecified / tool_default`** | 하위 에이전트 호출에 온도를 넘기는 경로가 없었음. 확인 불가가 아니라 확정적 미지정 |
| 재시도·재생성 | **1건** (아래 §3) | 세션 기록 · `deviations: []`에는 안 잡힘 |
| 사전등록 | **없음.** `--allow-v2`로 v2 관문을 열고 실행 | `run_solo.py`의 `is_v2` 분기(비-camp `--issue`) |

`model_id: claude-haiku-4-5`는 **내가 러너에 넘긴 라벨**이지 공급자가 돌려준 값이 아니다.
파일 왕복 러너는 그 문자열을 그대로 적는다. 검증된 값처럼 읽힐 수 있어 명시한다.

## 1. 실행 구도

셀 9개를 **별개 OS 프로세스**로 띄웠다. `run_solo.py`는 `--arms`/`--memories`로 셀 하나만
돌릴 수 있어, 프로세스마다 pending 파일을 하나씩 내놓는다. 그래서 동시에 최대 9개가 대기했고
나는 그 9개를 병렬로 하위 에이전트에 넘겼다. 표의 `배치` 열이 그 묶음이다.

- 배치 0: A_full 단독 프로세스(`--max-calls 10`)로 배관 확인 — 2호출
- 배치 1~9: 나머지 8셀을 한 번에 띄운 뒤 라운드마다 병렬 응답

셀 간 파일명이 겹치지 않아(`<모델>_<팔>_<기억>_rep1_<호출>`) 프로세스끼리 간섭하지 않는다.

**앞선 실패 실행 1건**(호출 0): 첫 launch가 `--allow-v2` 없이 나가 v2 관문에서 즉사했다
(exit 1). pending 파일이 나오기 전이라 생성물이 없다. 계보 표에 행이 없는 이유다.

## 2. 계보 표

`상태` 열: 정상 / **대체**(폐기 호출을 대신한 것) / **폐기**(생성했으나 저장 안 됨).
`기록 시각`은 partial 행의 `at`(UTC)이며 러너가 응답을 읽은 시각이다 — 하위 에이전트가
생성한 시각이 아니다.

﻿| # | 배치 | 셀 | 호출 | agent ID | 상태 | 기록 시각(UTC) | answer sha256(앞12) | 크기 | partial |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | A_full | essay_r0 | `a7cb3e903dea6fb82` | 정상 | 02:47:05 | `0c53063ce5b4…` | 1257B | 있음 |
| 2 | 0 | A_full | essay_r1 | `ae24540f287ddf6cb` | 정상 | 02:48:30 | `6465458e00c8…` | 1296B | 있음 |
| 3 | 1 | A_full | essay_r2 | `ab56dc535c6b88c8c` | 정상 | 02:52:30 | `cb80599d0ac2…` | 1503B | 있음 |
| 4 | 1 | A_note | essay_r0 | `af9654e48c8a5a60a` | 정상 | 02:52:41 | `f87d52dc466c…` | 1435B | 있음 |
| 5 | 1 | A_prev | essay_r0 | `a9e84b2056e0c76c6` | 정상 | 02:52:41 | `b35ea49334f4…` | 943B | 있음 |
| 6 | 1 | B_full | essay_r0 | `a716bde3f2f411b09` | 정상 | 02:52:51 | `4c9e14b703c2…` | 1150B | 있음 |
| 7 | 1 | B_note | essay_r0 | `ac39986414e54c89c` | 정상 | 02:52:56 | `4d56a1dfc256…` | 1293B | 있음 |
| 8 | 1 | B_prev | essay_r0 | `aaf0af607dd0d61c7` | 정상 | 02:52:56 | `9ce3f62d6ca6…` | 1060B | 있음 |
| 9 | 1 | P_full | essay_r0 | `aa326e2aff17c7bcb` | 정상 | 02:53:01 | `e68a42a2f0bd…` | 941B | 있음 |
| 10 | 1 | P_note | essay_r0 | `a1858cbfbbff4d85c` | **폐기** | — | — | — | 저장 안 됨 |
| 11 | 1 | P_prev | essay_r0 | `a4607c8235820887f` | 정상 | 02:53:11 | `0969a8efdf67…` | 973B | 있음 |
| 12 | 2 | P_note | essay_r0 | `aaf77901a31a35efd` | **대체** | 02:59:11 | `ea7fabf59e3a…` | 866B | 있음 |
| 13 | 2 | A_full | essay_r3 | `a2fa7ee2cb46aa4db` | 정상 | 02:59:05 | `a88de3e408a5…` | 1538B | 있음 |
| 14 | 2 | A_note | note_r0 | `af53e30e88c8ea949` | 정상 | 02:59:06 | `6fa549b8461c…` | 806B | 있음 |
| 15 | 2 | A_prev | essay_r1 | `a740e193b0f4f33a7` | 정상 | 02:59:11 | `a7a725890b5b…` | 1005B | 있음 |
| 16 | 2 | B_full | essay_r1 | `a79539f896aa38ba3` | 정상 | 02:59:36 | `9b6fe864b726…` | 989B | 있음 |
| 17 | 2 | B_note | note_r0 | `aaf941fc2a1fe5201` | 정상 | 02:59:41 | `75940e8b36a2…` | 414B | 있음 |
| 18 | 2 | B_prev | essay_r1 | `a4df00a382a584d6e` | 정상 | 02:59:51 | `4b125b840b3e…` | 1320B | 있음 |
| 19 | 2 | P_full | essay_r1 | `a7794053a33323de3` | 정상 | 03:01:16 | `90f24e1abea0…` | 1064B | 있음 |
| 20 | 2 | P_prev | essay_r1 | `ae201f1e1b7e372fd` | 정상 | 02:59:36 | `26fea75dfd68…` | 960B | 있음 |
| 21 | 3 | A_full | recall | `a181626151dc8f266` | 정상 | 03:02:45 | `462a6f360890…` | 1161B | 있음 |
| 22 | 3 | A_note | essay_r1 | `a5ae5d0b727c8b579` | 정상 | 03:02:51 | `3cfa19fd47ef…` | 1242B | 있음 |
| 23 | 3 | A_prev | essay_r2 | `ad8084843b7bdcee0` | 정상 | 03:02:51 | `10c602b1ea60…` | 1270B | 있음 |
| 24 | 3 | B_full | essay_r2 | `ad0c8284b619c492a` | 정상 | 03:03:26 | `ececfe6eb13f…` | 1265B | 있음 |
| 25 | 3 | B_note | essay_r1 | `abf62a24eb9fc787d` | 정상 | 03:03:26 | `7de059038618…` | 1976B | 있음 |
| 26 | 3 | B_prev | essay_r2 | `a61df32e3439107b8` | 정상 | 03:03:26 | `58995bfb2cb1…` | 1386B | 있음 |
| 27 | 3 | P_full | essay_r2 | `ade75a50aa0633c8e` | 정상 | 03:03:26 | `6dec2c939cda…` | 1354B | 있음 |
| 28 | 3 | P_note | note_r0 | `a14031a7a8757c6b9` | 정상 | 03:03:46 | `678aac8a4eb0…` | 751B | 있음 |
| 29 | 3 | P_prev | essay_r2 | `a49587af4617b7264` | 정상 | 03:03:36 | `583a78c1ed23…` | 1204B | 있음 |
| 30 | 4 | A_note | note_r1 | `a447eee7030e7ad6d` | 정상 | 03:05:56 | `cd23ee399370…` | 972B | 있음 |
| 31 | 4 | A_prev | essay_r3 | `a5bd3dfac099e316f` | 정상 | 03:05:51 | `74cc7e210e59…` | 1305B | 있음 |
| 32 | 4 | B_full | essay_r3 | `a5753e87c42c616f3` | 정상 | 03:06:16 | `667139034a27…` | 1367B | 있음 |
| 33 | 4 | B_note | note_r1 | `aa14956654bd7b524` | 정상 | 03:05:56 | `c355fd318540…` | 500B | 있음 |
| 34 | 4 | B_prev | essay_r3 | `a02c1b84deaa24b1f` | 정상 | 03:06:06 | `787f1f8b9132…` | 1121B | 있음 |
| 35 | 4 | P_full | essay_r3 | `a0cd8e695429120d0` | 정상 | 03:08:16 | `6bac6d1aa877…` | 1600B | 있음 |
| 36 | 4 | P_note | essay_r1 | `ad7b12da22e27cffc` | 정상 | 03:06:16 | `16f75f899a9a…` | 908B | 있음 |
| 37 | 4 | P_prev | essay_r3 | `aa9e52139d237341b` | 정상 | 03:06:01 | `bfb89099dc8f…` | 1394B | 있음 |
| 38 | 5 | A_note | essay_r2 | `a8f5c552680e4d56c` | 정상 | 03:09:16 | `57c5895fdff3…` | 996B | 있음 |
| 39 | 5 | A_prev | recall | `a123c6d6d936950b3` | 정상 | 03:09:31 | `c9790fe13b3a…` | 799B | 있음 |
| 40 | 5 | B_full | recall | `a0c36a7fd782a217a` | 정상 | 03:09:21 | `b0d398e07a48…` | 985B | 있음 |
| 41 | 5 | B_note | essay_r2 | `a3a5da5dab77fd5da` | 정상 | 03:09:31 | `b475136b3ef6…` | 1128B | 있음 |
| 42 | 5 | B_prev | recall | `a21978c5844ccd691` | 정상 | 03:09:31 | `581f8ec9c6fe…` | 679B | 있음 |
| 43 | 5 | P_full | recall | `a4615aae855bc989d` | 정상 | 03:09:36 | `750a520efafb…` | 1075B | 있음 |
| 44 | 5 | P_note | note_r1 | `acbee022bd78d6932` | 정상 | 03:09:36 | `f20c8eea2f8f…` | 710B | 있음 |
| 45 | 5 | P_prev | recall | `aa21ffeb783b7f7a8` | 정상 | 03:09:41 | `d4a15af034bf…` | 689B | 있음 |
| 46 | 6 | A_note | note_r2 | `a0a8e2e706ca122db` | 정상 | 03:12:36 | `64f96269adf5…` | 865B | 있음 |
| 47 | 6 | B_note | note_r2 | `ae8ef06a84ab9cf4c` | 정상 | 03:13:06 | `56eef51654fd…` | 579B | 있음 |
| 48 | 6 | P_note | essay_r2 | `aaf2db367abdc9274` | 정상 | 03:12:51 | `091bd7f40230…` | 1220B | 있음 |
| 49 | 7 | A_note | essay_r3 | `a23900e7e75821a67` | 정상 | 03:15:01 | `096cd61fa542…` | 1166B | 있음 |
| 50 | 7 | B_note | essay_r3 | `aa7f3fdf418f1ddcb` | 정상 | 03:15:16 | `e47cc9325a91…` | 1461B | 있음 |
| 51 | 7 | P_note | note_r2 | `ad4ebde73d1a5b06c` | 정상 | 03:15:11 | `64723b5b4e7e…` | 758B | 있음 |
| 52 | 8 | A_note | recall | `a3cb1a8ae59041d8a` | 정상 | 03:17:56 | `9e1865de2a1b…` | 762B | 있음 |
| 53 | 8 | B_note | recall | `ac3d2c8907cf823b5` | 정상 | 03:18:06 | `d2a7e02c9222…` | 1125B | 있음 |
| 54 | 8 | P_note | essay_r3 | `a7733e6f120d9f66b` | 정상 | 03:18:16 | `f2ad1835c99a…` | 1201B | 있음 |
| 55 | 9 | P_note | recall | `abd811f91810530e5` | 정상 | 03:20:01 | `2ec137d0f023…` | 779B | 있음 |

### 검증 (전부 리포에서 재계산)
- 계보 행 55 = 저장 54 + 폐기 1
- answers 실제 파일 54 → 일치
- partial 호출 행 합 54 → 일치
- 완성 run JSON 9 → 일치
- answer 본문 == partial 응답: 54/54 → 전건 일치
- agent ID 중복 0건
- 대조 오류 0건

## 3. 저장 54개와 실제 55호출의 차이

행 10 `P_note / essay_r0` (`a1858cbfbbff4d85c`)가 첫 시도에서 실패했다. 하위 에이전트가
pending 파일을 읽고 답을 생성했으나 **Write 도구를 호출하지 않고 본문을 보고에 적었다.**
나는 그 본문을 저장하지 않고 버린 뒤, 새 에이전트(행 12, `aaf77901a31a35efd`)를 세워
같은 pending 파일로 처음부터 다시 생성하게 했다.

Hermes가 정한 어휘로 적으면:

- `transport/write failure` — 도구 호출 누락. 모델 생성 자체는 성공
- `discarded_unobserved_generation` — 첫 생성물 미보존. **복원 불가**
- `replacement_call` — 행 12

**결과를 보고 고른 것이 아니다.** 파일이 없어서 다시 돌렸다. 다만 첫 생성물이 어디에도
남지 않았고 `deviations: []`도 이를 잡지 못했다. **실행 편차로 기록한다.**

폐기된 생성물의 내용은 복원하지 않고 추측하지도 않는다. 남은 것은 "그런 호출이 한 번
있었다"는 사실뿐이다.

## 4. 실행 시점 코드·재료 지문

| 파일 | SHA-256 | 워크트리 상태 |
|---|---|---|
| `experiments/memory_structure/run_solo.py` | `8130a256b39350691bef2ed4af86ca8b176ec2a38a4a7b0fcd2d1344a95c8fac` | **modified_uncommitted** |
| `experiments/memory_structure/analyze_solo.py` | `85e3f398c965ba7e03af0f0d03466bd2433383321b9bf79e48bc67edc49d99c5` | **modified_uncommitted** |
| `experiments/scenario_generalization/scan_pilot_haiku.py` | `93d9d8ecd2fc6b754aca18d5cad754b90eecffabdf2d6e1d1fc9ebdd1a81ce68` | committed |
| `data/issues/issue_throne.json` | `a818e61afc6eab6d986ae0f44c90b007a706975cf71c5099e487ebad1d194044` | **untracked** |
| `data/facts/facts_issue_throne.json` | `2d156dfbc7f369ef9d9d479d584cd3037e87cb608f639f33037cdec1a035a0e5` | **untracked** |
| `data/assignments/assignment_issue_throne.json` | `b1a12d57cd18710ee2af0a1c0717bf8c85f71097dd810ecf1e37fee63d8c0df6` | untracked |

여섯 개 전부 Hermes 감사(§2)의 해시와 일치한다 — 독립 재계산으로 확인.

**위 「워크트리 상태」는 실행 시점 값이다.** 이 문서를 올리는 커밋에서 여섯 파일과 원자료
(9런·partial·answers 54)를 함께 보존한다(규약 8: 원자료는 생성 즉시 커밋). 커밋 뒤에는
`modified_uncommitted`·`untracked`가 아니게 되지만, **파일럿이 돌던 순간에는 저 상태였다**는
것이 provenance다. 해시는 안 바뀌므로 위 표로 그 순간을 다시 짚을 수 있다.

**두 러너 파일이 커밋 안 된 수정본인 이유**: 파일럿 직전에 `issue_award`를
`ISSUE_PROMPTS`(`run_solo.py`)와 `ANCHORS_BY_ISSUE`(`analyze_solo.py`)에 등록했다.
**throne 문면·앵커는 한 글자도 안 건드렸다.** 그래도 이 해시는 어떤 커밋과도 안 맞는다.

**재료 3종이 untracked인 이유**: 재료화 보드 제안의 이의 창(8/20 21시)이 닫히기 전에
`시나리오/`에서 `data/`로 복사해 실행했다. 사용자 판단이며, 이 판을 분류할 때 알아야 할
사실이라 적는다.

## 5. 함께 발견한 결함 — `analyze_solo.py`가 비-camp 이슈에서 camp 앵커를 쓴다

계보를 맞추다 확인했다. 이 파일럿 숫자에는 영향이 없지만 **다음 판에 바로 걸린다.**

```python
ANCHORS = ANCHORS_BY_ISSUE["issue_camp"]          # :85  하위 호환 별칭
...
recall_hits = {fid for fid, pat in ANCHORS.items() ...}   # :169
for fid, pat in ANCHORS.items():                          # :175
```

8/19에 `ANCHORS_BY_ISSUE`와 `anchors_for(issue_id)`를 만들면서 **소비 지점 두 곳을 안
갈아 끼웠다.** throne을 `analyze_solo`로 돌리면 회상을 `38[,.]?000`·`배관`·`증서` 같은
camp 정규식으로 채점해 조용히 0에 가까운 값이 나오고, 판정기-앵커 불일치율도 같이 망가진다.

오늘 보고한 숫자는 `scan_pilot_haiku.py`가 `anchors_for()`를 쓰므로 영향받지 않았다.
**judge를 돌려 정식 분석에 들어가는 순간 걸린다.** `analyze_solo.py`는 민옥 트랙이라
고치지 않고 인계 안건으로 올린다. 독립 설계 에이전트의 DetectionSpec 인터페이스가
이 소비 경로를 대체할 예정이라면 거기서 함께 처리하는 편이 나을 수도 있다.

## 6. 완료 기준 대조

| Hermes 기준 | 이 문서 |
|---|---|
| 실제 호출 55행과 저장 응답 54개의 차이가 설명된다 | §3 |
| 폐기 생성물을 복원하거나 내용을 추측하지 않는다 | §3 — 사실만 기록 |
| 저장소 근거와 세션 기록 근거를 구분한다 | 표 머리 · §2 각주 |
| 9 run_id와 54 호출 태그가 모두 한 번씩 대응 | 검증 블록 |
| 파일 수와 호출 수가 감사 수치와 맞음 | 검증 블록 |
| 기존 원자료를 건드리지 않음 | 읽기만 함 |

## 부록 — 재현

계보 표는 손으로 적지 않고 생성했다. agent ID 55개만 세션 기록에서 옮긴 값이고, 파일 존재·
행 대응·해시·본문 일치는 전부 리포에서 읽어 계산한다. 생성기는 스크래치패드에 있다
(`gen_lineage.py`). 리포에 두려면 `experiments/scenario_generalization/`로 옮기면 된다.

**후속(같은 날)**: 이 문서를 올리는 사이 `analyze_solo.py`가 수정됐다 — `lexical_anchor_hits(issue_id, text)`가
신설되고 `main()`이 `anchors_for(run_issue_id)`를 쓰며 이슈 불일치 시 즉사하는 관문이 붙었다.
camp 별칭 직접 순회는 사라졌고 `ANCHORS`는 하위 호환 정의로만 남았다. **결함 해소 확인.**
따라서 위 §5는 「발견 시점의 상태」로 읽어야 한다. 파일럿 숫자에는 애초에 영향이 없었다.
