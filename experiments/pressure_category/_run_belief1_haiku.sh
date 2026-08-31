#!/usr/bin/env bash
# 기획 1 「원칙주의 × 압박」 실호출 — 요한 승인 2026-08-31 (PREREG_belief1 커밋 e0afdff 이후)
# wonchik(원칙주의) 세트 × (C0 + pbw_<재료>) × 11재료 × rep1~3 = 66판, claude-haiku.
# 중단·재개: 그대로 재실행하면 완료 판 skip, 미완 판은 체크포인트에서 이어받는다.
LOG=runs/belief1_haiku_2026-08-31.log
echo "=== belief1 실호출 시작 $(date -Iseconds) ===" | tee -a "$LOG"
n=0
consec_fail=0
while read -r iid sfx; do
  [ -z "$iid" ] && continue
  n=$((n+1))
  echo "--- [$n/11] $iid ---" | tee -a "$LOG"
  PYTHONUTF8=1 python run_pressure.py --materials "$iid" --model claude-haiku \
    --scripts C0 "pbw_$sfx" --vsets "wonchik_$sfx" --reps 1 2 3 --allow-live 2>&1 | tee -a "$LOG"
  code=${PIPESTATUS[0]}
  if [ "$code" -ne 0 ]; then
    consec_fail=$((consec_fail+1))
    echo "[driver] ✗ $iid 종료코드 $code (연속 실패 $consec_fail)" | tee -a "$LOG"
    if [ "$consec_fail" -ge 3 ]; then
      echo "[driver] 연속 실패 3회 — 중단 (체크포인트 보존, 재실행으로 재개)" | tee -a "$LOG"
      exit 1
    fi
  else
    consec_fail=0
  fi
done <<'EOF'
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
EOF
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
