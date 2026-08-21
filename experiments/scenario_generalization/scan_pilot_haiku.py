"""[재료 확장 · 김요한] 파일럿 앵커 스캔 — 새 재료가 3×3 신호를 내는가 (LLM 0콜).

무엇을 보는가: 이 재료로 단독 3×3 을 돌렸을 때 본실험에서 나온 두 패턴이 재현되는가.
  ① 기억 사다리   full > note > prev
  ② 팔 순서       A(반복) > B(숙의) ≈ A′(전진)
안 나오면 그 재료로는 본실험을 못 돌린다. **통과/탈락 관문이 아니라 적합성 확인이다.**

선례: REPORT_v1 §6 의 8/11 haiku 파일럿이 앵커 스캔·반복 1 로 같은 두 패턴을 봤다.
그때는 프롬프트·재료가 본실험과 달라 같은 표에 못 올렸는데, `run_solo.py --issue`
배관(2026-08-19) 이후로는 같은 러너·같은 프롬프트로 돈다.

측정: judge 를 쓰지 않고 정규식 앵커로 센다(0콜). judge 판정과는 불일치가 있을 수 있고,
그래서 이 산출물은 **증거가 아니라 재료 적합성 판단 재료**다(v1 §6 과 같은 지위).

실행: PYTHONUTF8=1 python experiments/scenario_generalization/scan_pilot_haiku.py \
          --model claude-haiku-4-5 --issue issue_throne
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "memory_structure"))

from analyze_solo import anchors_for  # noqa: E402  — 앵커 정본은 민옥 트랙 사전

ARMS = [("A", "반복"), ("P", "전진"), ("B", "숙의")]
MEMS = [("full", "①전체"), ("note", "②수첩"), ("prev", "③직전")]


def bigrams(s: str) -> set[str]:
    s = re.sub(r"\s+", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def progression(prev: str, cur: str) -> float:
    """전진 점수 = 1 − 문자 2그램 자카드. A′ 가 A 보다 커야 조작이 먹은 것."""
    a, b = bigrams(prev), bigrams(cur)
    if not a or not b:
        return 0.0
    return 1.0 - len(a & b) / len(a | b)


def scan(text: str, anchors: dict[str, str]) -> set[str]:
    return {fid for fid, pat in anchors.items() if re.search(pat, text)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--issue", required=True)
    args = ap.parse_args()

    anchors = anchors_for(args.issue)
    n_facts = len(anchors)
    runs_dir = ROOT / "experiments" / "memory_structure" / "runs" / args.model / args.issue
    if not runs_dir.exists():
        raise SystemExit(f"런 폴더 없음: {runs_dir}")

    rows = {}
    for f in sorted(runs_dir.glob("run_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        essays = d["essays"]
        hits = [scan(e, anchors) for e in essays]
        prog = [progression(essays[i - 1], essays[i]) for i in range(1, len(essays))]
        rec = scan(d.get("recall") or "", anchors)
        rows[(d["arm"], d["memory"])] = {
            "per_round": [len(h) for h in hits],
            "auc": sum(len(h) for h in hits),
            "r0": len(hits[0]),
            "final": len(hits[-1]),
            "죽음": len(hits[0] - hits[-1]),      # r0 에 있었는데 마지막에 없는 것
            "final_from_r0": len(hits[0] & hits[-1]),   # r0 진입분 중 끝까지 살아남은 것
            "부활": len(hits[-1] - hits[0]),
            "전진": round(sum(prog) / len(prog), 3) if prog else 0.0,
            "회상": len(rec),
        }

    print(f"==== 파일럿 앵커 스캔 · {args.issue} · {args.model} · 반복 1 · 팩트 {n_facts}개 ====")
    print("(앵커 스캔이라 judge 판정과 다를 수 있다. 증거가 아니라 재료 적합성 판단용.)\n")

    print("라운드별 발화 앵커 적중 (r0→r3) · AUC · r0사망 · 전진점수 · 회상")
    print(f"{'':6s} {'①전체':>22s} {'②수첩':>22s} {'③직전':>22s}")
    for arm, arm_ko in ARMS:
        cells = []
        for mem, _ in MEMS:
            r = rows.get((arm, mem))
            cells.append("없음".rjust(22) if not r else
                         f"{'-'.join(map(str, r['per_round']))} AUC{r['auc']:>3d} 死{r['죽음']}".rjust(22))
        print(f"{arm_ko:6s} {cells[0]} {cells[1]} {cells[2]}")

    def mean(keys, field):
        vals = [rows[k][field] for k in keys if k in rows]
        return sum(vals) / len(vals) if vals else float("nan")

    def cond_surv(keys):
        """조건부 생존율 = r0 진입 팩트 중 r3 까지 남은 비율. **PREREG §6 주 지표**의 여집합.

        AUC 를 셀끼리 직접 비교하면 안 된다 — 셀마다 r0 진입 수가 다르고(여기선 1~7),
        REPORT_v2 §4.1 이 같은 이유로 모델 간 절대값 비교를 금지했다(분모 이질성).
        진입을 분모로 잡아야 조건이 만든 차이만 남는다."""
        num = sum(rows[k]["final_from_r0"] for k in keys if k in rows)
        den = sum(rows[k]["r0"] for k in keys if k in rows)
        return (num / den * 100) if den else float("nan")

    print("\n── ① 기억 사다리 · 주 지표 = 조건부 생존율 (r0 진입 대비 %, 건수 병기)")
    ladder = []
    for m, ko in MEMS:
        keys = [(a, m) for a, _ in ARMS]
        num = sum(rows[k]["final_from_r0"] for k in keys if k in rows)
        den = sum(rows[k]["r0"] for k in keys if k in rows)
        ladder.append((ko, cond_surv(keys), num, den))
        print(f"   {ko}  {cond_surv(keys):5.1f}%  ({num}/{den})")
    order_ok = ladder[0][1] > ladder[1][1] > ladder[2][1]
    print(f"   → full > note > prev {'성립' if order_ok else '불성립'}"
          f"  (본실험 GPT·Gemini 에서 성립한 패턴)")
    print(f"   참고 AUC 평균: " + " · ".join(
        f"{ko} {mean([(a, m) for a, _ in ARMS], 'auc'):.1f}" for m, ko in MEMS))

    print("\n── ② 팔 순서 · 조건부 생존율")
    arms = []
    for a, ko in ARMS:
        keys = [(a, m) for m, _ in MEMS]
        num = sum(rows[k]["final_from_r0"] for k in keys if k in rows)
        den = sum(rows[k]["r0"] for k in keys if k in rows)
        arms.append((ko, cond_surv(keys)))
        print(f"   {ko}  {cond_surv(keys):5.1f}%  ({num}/{den})")
    d = dict(arms)
    a_top = d["반복"] > d["전진"] and d["반복"] > d["숙의"]
    print(f"   → A(반복)가 가장 높음 {'성립' if a_top else '불성립'}"
          f"  (본실험 패턴 A > B ≈ A′)")
    print(f"   참고 AUC 평균: " + " · ".join(
        f"{ko} {mean([(a, m) for m, _ in MEMS], 'auc'):.1f}" for a, ko in ARMS))

    print("\n── 조작 점검 (전진 점수 평균, A′>A 여야 전진 강제가 먹은 것)")
    for a, ko in ARMS:
        print(f"   {ko}  {mean([(a, m) for m, _ in MEMS], '전진'):.3f}")

    print("\n── 회상 (마지막 회상 프롬프트에서 앵커 적중 수)")
    for a, ko in ARMS:
        line = " · ".join(f"{mko}{rows[(a, m)]['회상']:>2d}" if (a, m) in rows else f"{mko} --"
                          for m, mko in MEMS)
        print(f"   {ko}  {line}")


if __name__ == "__main__":
    main()
