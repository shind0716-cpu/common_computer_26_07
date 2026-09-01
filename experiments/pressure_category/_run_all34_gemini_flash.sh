#!/usr/bin/env bash
# 3모델 ALL 균형 — gemini-flash 따라잡기 (런플랜 ALL34_3MODEL_2026-09-01)
# 배치 4개 · 판 36 · 예상 콜 288 (판당 상한 11)
# 중단·재개: 이 스크립트를 그대로 재실행하면 완료 판은 러너가 [skip], 미완 판은
#            .partial.jsonl 체크포인트에서 이어받는다.
# 배치 하나만 돌리려면: BATCH=2 bash _run_all34_gemini_flash.sh
set -u
LOG=runs/all34_gemini_flash_2026-09-01.log
echo "=== ALL34 gemini-flash 시작 $(date -Iseconds) ===" | tee -a "$LOG"
consec_fail=0
run_one() {  # $1=배치 $2=재료 $3=세트 $4..=반복
  local b=$1 id=$2 vs=$3; shift 3
  echo "--- [배치 $b] $id / $vs / rep $* ---" | tee -a "$LOG"
  PYTHONUTF8=1 python run_pressure.py --materials "$id" --model gemini-flash     --scripts C0 --vsets "$vs" --reps "$@" --max-calls 11 --allow-live 2>&1 | tee -a "$LOG"
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
  run_one 1 issue_cat_feeding_days_list allb1_cat_days 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "2" ]; then
  run_one 2 issue_childcare allb1_childcare 1 2 3
  run_one 2 issue_elderdrive allb1_elderdrive 1 2 3
  run_one 2 issue_eol allb1_eol 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "3" ]; then
  run_one 3 issue_euthanasia allb1_euthanasia 1 2 3
  run_one 3 issue_examaccom allb1_examaccom 1 2 3
  run_one 3 issue_parentalreturn allb1_parental 1 2 3
fi
if [ -z "${BATCH:-}" ] || [ "${BATCH}" = "4" ]; then
  run_one 4 issue_remotewatch allb1_remotewatch 1 2 3
  run_one 4 issue_shelter allb1_shelter 1 2 3
  run_one 4 issue_workmind allb1_workmind 1 2 3
fi
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
