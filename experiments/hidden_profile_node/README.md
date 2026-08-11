# 히든 프로필 관측 노드 — 계보 시트 생성기

지위: **현행** (요한 측 관측 레이어 · 계약 정본: `docs/proposals/HIDDEN_PROFILE_NODE.md` §3-5)

`modules/hidden_profile.lineage()`(순수 함수·판정 0)가 좌표로 묶은 원문을
사람이 읽을 마크다운 시트로 펼친다. **산출물은 파생 뷰다** — 리포에 커밋하지 않고
리포 밖에 쓴다(기본: 리포 부모 폴더). 원자료(debate·facts·assignment)가 정본이며
시트는 언제든 재생성 가능하다.

사용:

```bash
PYTHONUTF8=1 python experiments/hidden_profile_node/gen_lineage_sheet.py --run gpt001
```

읽는 법·금지(무엇을 계기가 판단하지 않는가)는 시트 머리말과 계약 §5 참조.
화면(뷰어 2층) 착수 트리거: 판 3개 이상 · 같은 비교 2회 이상 반복 · 소비자 증가
(2026-08-10 요한 결정 — 그 전에는 시트가 정답).
