#!/usr/bin/env bash
# 라벨 한 문장 실험 — gpt·gemini 확장 (민옥 트랙, 2026-09-03). 하이쿠 9/2와 같은 절차.
# 용법: bash run_label_models.sh <model:gpt|gemini-flash> <stage:c0|press> [scenario 목록 파일]
#   c0    : 11시나리오 × lcons/lprog × 3반복 (관문)
#   press : 관문에서 갈린 시나리오만, pxc_*(보수용)·pxp_*(진보용) × 3반복
# 러너가 결과 있는 판을 건너뛰므로 끊긴 자리에서 다시 돌려도 된다.
set -u
MODEL="$1"; STAGE="$2"; LIST="${3:-}"
cd "$(dirname "$0")"
export PYTHONUTF8=1
declare -A SUF=( [issue_childcare]=childcare [issue_euthanasia]=euthanasia [issue_examaccom]=examaccom
  [issue_parentalreturn]=parentalreturn [issue_eol]=eol [issue_remotewatch]=remotewatch [issue_shelter]=shelter
  [issue_workmind]=workmind [issue_cat_feeding_days_list]=cf_days_list [issue_recycling_room]=recycling_room
  [issue_smoking_area_party]=smoking_party )
ORDER="issue_childcare issue_euthanasia issue_examaccom issue_parentalreturn issue_eol issue_remotewatch issue_shelter issue_workmind issue_cat_feeding_days_list issue_recycling_room issue_smoking_area_party"
if [ -n "$LIST" ]; then ORDER="$(cat "$LIST")"; fi
LOG="runs/label_${STAGE}_${MODEL}_2026-09-03.log"
echo "=== label $STAGE $MODEL 시작 $(date -Is) ===" >> "$LOG"
for iss in $ORDER; do
  s="${SUF[$iss]}"
  echo "--- $iss ---" >> "$LOG"
  if [ "$STAGE" = c0 ]; then
    python3 run_pressure.py --materials "$iss" --scripts C0 --vsets "lcons_$s" "lprog_$s" --reps 1 2 3 --model "$MODEL" --allow-live >> "$LOG" 2>&1
  else
    python3 run_pressure.py --materials "$iss" --scripts "pxc_$s" --vsets "lcons_$s" --reps 1 2 3 --model "$MODEL" --allow-live >> "$LOG" 2>&1
    python3 run_pressure.py --materials "$iss" --scripts "pxp_$s" --vsets "lprog_$s" --reps 1 2 3 --model "$MODEL" --allow-live >> "$LOG" 2>&1
  fi
done
echo "=== label $STAGE $MODEL 끝 $(date -Is) ===" >> "$LOG"
