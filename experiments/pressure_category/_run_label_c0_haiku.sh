#!/usr/bin/env bash
# 라벨 한 문장 실험 1단계 — C0 관문: lcons/lprog × 11재료 × rep1~3 = 66판, claude-haiku (민옥 9/2, SilenceBreaker VM 실호출)
LOG=runs/label_c0_haiku_2026-09-02.log
echo "=== label C0 시작 $(date -Iseconds) ===" | tee -a "$LOG"
consec_fail=0
while read -r iid sfx; do
  [ -z "$iid" ] && continue
  echo "--- $iid ---" | tee -a "$LOG"
  PYTHONUTF8=1 python3 run_pressure.py --materials "$iid" --model claude-haiku \
    --scripts C0 --vsets "lcons_$sfx" "lprog_$sfx" --reps 1 2 3 --allow-live 2>&1 | tee -a "$LOG"
  code=${PIPESTATUS[0]}
  if [ "$code" -ne 0 ]; then consec_fail=$((consec_fail+1)); echo "[driver] ✗ $iid code $code" | tee -a "$LOG"; [ "$consec_fail" -ge 3 ] && exit 1; else consec_fail=0; fi
done <<'LIST'
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
LIST
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
