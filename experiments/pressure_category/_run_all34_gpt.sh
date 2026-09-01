#!/usr/bin/env bash
# 3모델 ALL 균형 — gpt 따라잡기 (런플랜 ALL34_3MODEL_2026-09-01)
# 배치 8개 · 판 69 · 예상 콜 552 (판당 상한 11)
# 중단·재개: 이 스크립트를 그대로 재실행하면 완료 판은 러너가 [skip], 미완 판은
#            .partial.jsonl 체크포인트에서 이어받는다.
# 배치 하나만 돌리려면: BATCH=2 bash _run_all34_gpt.sh
set -u
LOG=runs/all34_gpt_2026-09-01.log
echo "=== ALL34 gpt 시작 $(date -Iseconds) ===" | tee -a "$LOG"
consec_fail=0
run_one() {  # $1=배치 $2=재료 $3=세트 $4..=반복
  local b=$1 id=$2 vs=$3; shift 3
  echo "--- [배치 $b] $id / $vs / rep $* ---" | tee -a "$LOG"
  PYTHONUTF8=1 python run_pressure.py --materials "$id" --model gpt     --scripts C0 --vsets "$vs" --reps "$@" --max-calls 11 --allow-live 2>&1 | tee -a "$LOG"
  local code=${PIPESTATUS[0]}
  if [ "$code" -ne 0 ]; then
    consec_fail=$((consec_fail+1))
    echo "[driver] X $id 종료코드 $code (연속 실패 $consec_fail)" | tee -a "$LOG"
    if [ "$consec_fail" -ge 3 ]; then
      echo "[driver] 연속 실패 3회 — 구조적 문제로 보고 중단 (체크포인트 보존)" | tee -a "$LOG"
      exit 1
    fi
  else
    consec_fail=0
  fi
}
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "1" ]; then
  run_one 1 issue_ambulance allb1_ambulance 1 2 3
  run_one 1 issue_caregiverprotect allb1_caregiverprotect 1 2 3
  run_one 1 issue_cat_feeding_party all_cat_feeding_party 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "2" ]; then
  run_one 2 issue_cat_feeding_plainvalue all_cat_feeding_plainval 1 2 3
  run_one 2 issue_childcare_party all_childcare_party 1 2 3
  run_one 2 issue_childcare_room all_childcare_room 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "3" ]; then
  run_one 3 issue_community_cat_feeding all_community_cat_feedin 1 2 3
  run_one 3 issue_community_room all_community_room 1 2 3
  run_one 3 issue_elderdrive allb1_elderdrive 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "4" ]; then
  run_one 4 issue_floor_noise all_floor_noise 1 2 3
  run_one 4 issue_garden_plot all_garden_plot 1 2 3
  run_one 4 issue_recycling_room_party all_recycling_room_party 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "5" ]; then
  run_one 5 issue_restaurant_anniversary all_r_anniversary 1 2 3
  run_one 5 issue_restaurant_biz_meeting all_r_biz_meeting 1 2 3
  run_one 5 issue_restaurant_brunch all_r_brunch 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "6" ]; then
  run_one 6 issue_restaurant_date all_r_date 1 2 3
  run_one 6 issue_restaurant_elders all_r_elders 1 2 3
  run_one 6 issue_restaurant_kids all_r_kids 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "7" ]; then
  run_one 7 issue_restaurant_office_lunch all_r_office_lunch 1 2 3
  run_one 7 issue_restaurant_sanggyeollye all_r_sanggyeollye 1 2 3
  run_one 7 issue_restaurant_sogaeting all_r_sogaeting 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "8" ]; then
  run_one 8 issue_restaurant_solo all_r_solo 1 2 3
  run_one 8 issue_smoking_area all_smoking_area 1 2 3
fi
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
