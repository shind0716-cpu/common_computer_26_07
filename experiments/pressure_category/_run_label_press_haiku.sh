#!/usr/bin/env bash
# 라벨 실험 2단계 — 반대편 압박: lcons×pxc, lprog×pxp × 갈린 9재료 × rep1~3 = 54판 (민옥 9/2)
LOG=runs/label_press_haiku_2026-09-02.log
echo "=== label press 시작 $(date -Iseconds) ===" | tee -a "$LOG"
while read -r iid sfx; do
  [ -z "$iid" ] && continue
  echo "--- $iid ---" | tee -a "$LOG"
  PYTHONUTF8=1 python3 run_pressure.py --materials "$iid" --model claude-haiku --scripts "pxc_$sfx" --vsets "lcons_$sfx" --reps 1 2 3 --allow-live 2>&1 | tee -a "$LOG"
  PYTHONUTF8=1 python3 run_pressure.py --materials "$iid" --model claude-haiku --scripts "pxp_$sfx" --vsets "lprog_$sfx" --reps 1 2 3 --allow-live 2>&1 | tee -a "$LOG"
done <<'LIST'
issue_childcare childcare
issue_euthanasia euthanasia
issue_examaccom examaccom
issue_remotewatch remotewatch
issue_workmind workmind
issue_cat_feeding_days_list cf_days_list
issue_eol eol
issue_shelter shelter
issue_parentalreturn parentalreturn
LIST
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
