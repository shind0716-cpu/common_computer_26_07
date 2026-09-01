#!/usr/bin/env bash
# 기획 1 「원칙주의 × 압박」 모델 축 — gpt (사전고정 PREREG_belief1_models_2026-09-01.md)
# wonchik 세트 × (C0 + pbw_<재료>) × 11재료 × rep1~3 = 66판 · 예상 528콜 (판당 상한 11)
# 중단·재개: 그대로 재실행하면 완료 판 skip, 미완 판은 체크포인트에서 이어받는다.
set -u
LOG=runs/belief1_gpt_2026-09-01.log
echo "=== belief1 gpt 시작 $(date -Iseconds) ===" | tee -a "$LOG"
n=0; consec_fail=0
while read -r iid sfx; do
  [ -z "$iid" ] && continue
  n=$((n+1))
  echo "--- [$n/11] $iid / wonchik_$sfx / pbw_$sfx ---" | tee -a "$LOG"
  PYTHONUTF8=1 python run_pressure.py --materials "$iid" --model gpt     --scripts C0 "pbw_$sfx" --vsets "wonchik_$sfx" --reps 1 2 3     --max-calls 11 --allow-live 2>&1 | tee -a "$LOG"
  code=${PIPESTATUS[0]}
  if [ "$code" -ne 0 ]; then
    consec_fail=$((consec_fail+1))
    echo "[driver] X $iid 종료코드 $code (연속 실패 $consec_fail)" | tee -a "$LOG"
    if [ "$consec_fail" -ge 3 ]; then
      echo "[driver] 연속 실패 3회 — 중단 (체크포인트 보존, 재실행으로 재개)" | tee -a "$LOG"
      exit 1
    fi
  else
    consec_fail=0
  fi
done <<'IDS'
issue_childcare childcare
issue_euthanasia euthanasia
issue_examaccom examaccom
issue_remotewatch remotewatch
issue_workmind workmind
issue_recycling_room recycling_room
issue_smoking_area_party smoking_party
issue_cat_feeding_days_list cf_days_list
issue_eol eol
issue_shelter shelter
issue_parentalreturn parentalreturn
IDS
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
