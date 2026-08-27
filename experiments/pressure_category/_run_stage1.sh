#!/usr/bin/env bash
# 1차 1단계 — gpt × 30벌 × (A·B) × C0 × 반복1 = 60판 480콜
# 사전고정 SELECTION_live30 §15·§18·§19·§20·§21 (커밋 20e6908)
LOG=runs/stage1_gpt_2026-08-27.log
echo "=== 1차 1단계 시작 $(date -Iseconds) ===" | tee -a "$LOG"
n=0
while read -r id; do
  [ -z "$id" ] && continue
  n=$((n+1))
  echo "--- [$n/30] $id ---" | tee -a "$LOG"
  PYTHONUTF8=1 python run_pressure.py --materials "$id" --model gpt \
    --scripts C0 --vsets A B --reps 1 --max-calls 11 --allow-live 2>&1 | tee -a "$LOG"
done < _live30_ids.txt
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
