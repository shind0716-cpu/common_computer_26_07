"""[공용 코어 · 압박×카테고리] 3모델 ALL 균형 런플랜 — 무엇을 얼마나 돌릴지 고정 (콜 0).

## 무엇을 정하나

ALL 세트(가치 여섯을 전부 주는 판)를 **claude-haiku · gemini-flash · gpt 셋이 같은
재료 34벌에서** 갖도록, 모델마다 빠진 판을 세어 배치로 나눈다.

## 왜 34벌인가 · 왜 어떤 판은 못 쓰나

`values/all_*.json`(8/27)과 `values/allb1_*.json`(9/1)은 둘 다 「A+B 병합」이지만
병합한 가치문의 판이 다르다. 재료 개정으로 카테고리 축이 바뀌면서 구판 세트 아홉은
현행 재료 카테고리와 **겹침이 0** 이 되었다 — 그 세트로 돈 판은 안/밖을 가를 수 없다.
그래서 「세트의 카테고리 ⊆ 현행 재료의 카테고리」인 세트만 현행으로 친다.

## 규율

호출 상한은 판마다 두고(--max-calls), 배치는 셋씩 끊는다 — ALL11 gpt 실행(9/1)과
같은 단위다. 러너가 완료 판을 건너뛰므로 배치 스크립트 재실행이 곧 재개다.

사용: PYTHONUTF8=1 python build_all34_runplan.py [--batch-size 3]
산출: ALL34_RUNPLAN_<날짜>.json · _run_all34_<model>.sh
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from modules import content_hash  # noqa: E402

HERE = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
MODELS = ["claude-haiku", "gemini-flash", "gpt"]
SCRIPT = "C0"
REPS = [1, 2, 3]
MAX_CALLS = 11              # 판당 상한 — 8콜 예상 + 수첩 반려 최대 3
EXPECT_CALLS = 8


def materials() -> dict:
    reg = {}
    for p in sorted((HERE / "materials").glob("*.json")):
        if p.name == "MATERIALS_TEMPLATE.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            reg[d["issue_id"]] = (p, d)
    return reg


def current_all_sets(reg: dict) -> tuple[dict, list]:
    """현행 ALL 세트만 고른다 — 세트 카테고리가 현행 재료 카테고리의 부분집합인 것."""
    cur, dead = {}, []
    for p in sorted((HERE / "values").glob("all*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        iid = d["materials"]
        if iid not in reg:
            dead.append((d["vset_id"], iid, "재료 없음"))
            continue
        mc = set(reg[iid][1]["categories"])
        if set(d["categories"]) <= mc:
            if iid in cur:                       # 한 재료에 현행 ALL 세트가 둘이면 즉사
                raise SystemExit(f"현행 ALL 세트 중복: {iid} — {cur[iid]} vs {d['vset_id']}")
            cur[iid] = d["vset_id"]
        else:
            dead.append((d["vset_id"], iid, f"겹침 {len(set(d['categories']) & mc)}/{len(mc)}"))
    return cur, dead


def existing(cur: dict) -> dict:
    """이미 있는 라이브 판 — (model, issue_id) → 반복 번호 집합."""
    got = collections.defaultdict(set)
    for p in (HERE / "runs").glob("*/*/run_*.json"):
        if "_dry" in p.parts or "_stale" in str(p):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        vs = d.get("value_set_id") or d.get("value_set") or ""
        iid = d.get("issue_id") or p.parts[-2]
        if cur.get(iid) == vs:
            try:
                got[(p.parts[-3], iid)].add(int(p.stem.rsplit("rep", 1)[-1]))
            except ValueError:
                pass
    return got


DRIVER = """#!/usr/bin/env bash
# 3모델 ALL 균형 — {model} 따라잡기 (런플랜 {plan_id})
# 배치 {nb}개 · 판 {runs} · 예상 콜 {calls} (판당 상한 {maxc})
# 중단·재개: 이 스크립트를 그대로 재실행하면 완료 판은 러너가 [skip], 미완 판은
#            .partial.jsonl 체크포인트에서 이어받는다.
# 배치 하나만 돌리려면: BATCH=2 bash {fname}
set -u
LOG=runs/all34_{slug}_{today}.log
echo "=== ALL34 {model} 시작 $(date -Iseconds) ===" | tee -a "$LOG"
consec_fail=0
run_one() {{  # $1=배치 $2=재료 $3=세트 $4..=반복
  local b=$1 id=$2 vs=$3; shift 3
  echo "--- [배치 $b] $id / $vs / rep $* ---" | tee -a "$LOG"
  PYTHONUTF8=1 python run_pressure.py --materials "$id" --model {model} \
    --scripts C0 --vsets "$vs" --reps "$@" --max-calls {maxc} --allow-live 2>&1 | tee -a "$LOG"
  local code=${{PIPESTATUS[0]}}
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
}}
{body}
echo "=== 끝 $(date -Iseconds) ===" | tee -a "$LOG"
"""


def emit_drivers(doc: dict, today: str) -> None:
    for m, p in doc["models"].items():
        lines = []
        for b in p["batches"]:
            lines.append(f'if [ -z "${{BATCH:-}}" ] || [ "${{BATCH}}" = "{b["batch"]}" ]; then')
            for it in b["items"]:
                reps = " ".join(str(r) for r in it["reps"])
                lines.append(f'  run_one {b["batch"]} {it["issue_id"]} {it["vset_id"]} {reps}')
            lines.append("fi")
        slug = m.replace("-", "_")
        fname = f"_run_all34_{slug}.sh"
        (HERE / fname).write_text(DRIVER.format(
            model=m, slug=slug, today=today, plan_id=doc["plan_id"], fname=fname,
            nb=len(p["batches"]), runs=p["expected_runs"],
            calls=p["expected_logical_calls"], maxc=doc["condition"]["max_logical_calls_per_run"],
            body=chr(10).join(lines)), encoding="utf-8")
        print(f"   드라이버 {fname} — 배치 {len(p['batches'])} · 판 {p['expected_runs']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=3)
    a = ap.parse_args()

    reg = materials()
    cur, dead = current_all_sets(reg)
    got = existing(cur)
    today = datetime.now(KST).strftime("%Y-%m-%d")

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip()
    except Exception:
        commit = None

    plan, totals = {}, collections.Counter()
    for m in MODELS:
        todo = []
        for iid in sorted(cur):
            miss = [r for r in REPS if r not in got[(m, iid)]]
            if miss:
                todo.append({"issue_id": iid, "vset_id": cur[iid], "reps": miss,
                             "materials_hash": content_hash.sha256_file(reg[iid][0])[:12]})
        batches = [todo[i:i + a.batch_size] for i in range(0, len(todo), a.batch_size)]
        runs = sum(len(t["reps"]) for t in todo)
        plan[m] = {"missing_materials": len(todo), "expected_runs": runs,
                   "expected_logical_calls": runs * EXPECT_CALLS,
                   "max_logical_calls": runs * MAX_CALLS,
                   "batches": [{"batch": i + 1, "items": b,
                                "expected_runs": sum(len(t["reps"]) for t in b)}
                               for i, b in enumerate(batches)]}
        totals["runs"] += runs
        totals["calls"] += runs * EXPECT_CALLS
        totals["max"] += runs * MAX_CALLS

    doc = {
        "schema": "pressure_live_runplan_v1",
        "plan_id": f"ALL34_3MODEL_{today}",
        "created_at": datetime.now(KST).isoformat(timespec="seconds"),
        "approval": "요한 2026-09-01 — 34벌로 가고 모델별 배치로 따라잡는다",
        "source_commit": commit,
        "source_hashes": {
            "run_pressure_py": content_hash.sha256_file(HERE / "run_pressure.py"),
            "build_allsets_b1_py": content_hash.sha256_file(HERE / "build_allsets_b1.py"),
        },
        "condition": {"script": SCRIPT, "reps": REPS, "value_once": False,
                      "max_logical_calls_per_run": MAX_CALLS,
                      "expected_logical_calls_per_run": EXPECT_CALLS},
        "target_materials": len(cur),
        "value_sets": cur,
        "excluded_stale_sets": [{"vset_id": v, "issue_id": i, "reason": r} for v, i, r in dead],
        "models": plan,
        "totals": dict(totals),
    }
    out = HERE / f"ALL34_RUNPLAN_{today}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    emit_drivers(doc, today)

    print(f"현행 ALL 세트 {len(cur)}벌 · 구판 제외 {len(dead)}개")
    for m in MODELS:
        p = plan[m]
        print(f"  {m:14s} 빠진 재료 {p['missing_materials']:2d}벌 · 판 {p['expected_runs']:3d} · "
              f"예상 콜 {p['expected_logical_calls']:4d} (상한 {p['max_logical_calls']}) · "
              f"배치 {len(p['batches'])}")
    print(f"  {'합계':14s} 판 {totals['runs']} · 예상 콜 {totals['calls']} · 상한 {totals['max']}")
    print(f"→ {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
