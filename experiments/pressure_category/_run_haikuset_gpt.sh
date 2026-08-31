#!/usr/bin/env bash
# gpt 하이쿠 동일셋 — 올세트 제외 (요한 결정 2026-08-31, 노션 전문 3cd0261412b0 참조)
# 39재료 × C0/C1/C2 × A/B × rep1~3 = 702판. 기존 유효 C0 rep1 52판은 러너가 [skip] 재사용.
# 중단·재개: 이 스크립트를 그대로 재실행하면 완료 판은 skip, 미완 판은 체크포인트에서 이어받는다.
# 스테일 함정 없음 — 옛 재료 런 18판은 runs/_stale_hash/gpt/ 로 격리 완료(커밋 6466eb3).
LOG=runs/haikuset_gpt_2026-08-31.log
echo "=== 하이쿠 동일셋(올세트 제외) 시작 $(date -Iseconds) ===" | tee -a "$LOG"
n=0
consec_fail=0
while read -r id; do
  [ -z "$id" ] && continue
  n=$((n+1))
  echo "--- [$n/39] $id ---" | tee -a "$LOG"
  PYTHONUTF8=1 python run_pressure.py --materials "$id" --model gpt \
    --scripts C0 C1 C2 --vsets A B --reps 1 2 3 --allow-live 2>&1 | tee -a "$LOG"
  code=${PIPESTATUS[0]}
  if [ "$code" -ne 0 ]; then
    consec_fail=$((consec_fail+1))
    echo "[driver] ✗ $id 종료코드 $code (연속 실패 $consec_fail)" | tee -a "$LOG"
    if [ "$consec_fail" -ge 3 ]; then
      echo "[driver] 연속 실패 3회 — 구조적 문제로 보고 중단 (체크포인트 보존, 재실행으로 재개)" | tee -a "$LOG"
      exit 1
    fi
  else
    consec_fail=0
  fi
done < _haikuset_ids.txt
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
