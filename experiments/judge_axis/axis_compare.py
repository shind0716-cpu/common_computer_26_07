"""판정 축 대조 분석 — 저자 축 체크포인트 vs 기존 judgment. LLM 호출 0.

축 정의:
  저자 축: 발화 1건마다 독립 호출. (round, agent, fact) 격자를 **직접** 얻는다.
           셀(round, fact) 판정 = 그 라운드 어느 발화에서든 매치되면 mentioned.
  우리 축: 팩트 1개 x 라운드 전체 발화, n_votes=3 다수결. 셀 status 를 직접 얻고
           화자 명단(agents_mentioning)은 같은 호출에서 LLM 이 열거한 값이다.

이 스크립트는 판정하지 않는다 — 두 산출을 좌표로 맞춰 세기만 한다.
"""
import argparse
import json
from pathlib import Path

from modules import paths
from modules.judge import SURVIVING


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    facts = json.loads(paths.facts(args.issue).read_text(encoding="utf-8"))["facts"]
    fid_of = {i: f["fact_id"] for i, f in enumerate(facts)}
    critical = {f["fact_id"]: bool(f.get("critical")) for f in facts}
    judgment = json.loads(paths.judgment(args.issue, args.run).read_text(encoding="utf-8"))

    # --- 저자 축 격자 -------------------------------------------------------
    rows = [json.loads(l) for l in Path(args.ckpt).read_text(encoding="utf-8").splitlines()
            if l.strip()]
    n_fail = sum(1 for r in rows if r["parse"] == "parse_fail")
    author = {}      # (round, fact_id) -> set(agent_id)
    rounds = sorted({r["round"] for r in rows})
    for r in rows:
        if r["matched_fact_ids"] is None:
            continue
        for i in r["matched_fact_ids"]:
            author.setdefault((r["round"], fid_of[i]), set()).add(r["agent_id"])

    # --- 우리 축 격자 -------------------------------------------------------
    ours = {}        # (stage, fact_id) -> (status, set(agents))
    for st in judgment["stages"]:
        for f in st["facts"]:
            ours[(st["stage"], f["fact_id"])] = (
                f.get("status"), set(f.get("agents_mentioning") or []))

    # --- 1. 셀 수준 일치 ----------------------------------------------------
    both, only_ours, only_author, neither = [], [], [], []
    for rnd in rounds:
        for f in facts:
            fid = f["fact_id"]
            a_alive = bool(author.get((rnd, fid)))
            o_status, _ = ours.get((rnd, fid), (None, set()))
            o_alive = o_status in SURVIVING
            cell = {"round": rnd, "fact_id": fid, "our_status": o_status,
                    "author_speakers": sorted(author.get((rnd, fid), []))}
            (both if (a_alive and o_alive) else
             only_ours if o_alive else
             only_author if a_alive else neither).append(cell)

    n = len(rounds) * len(facts)
    agree = len(both) + len(neither)

    # --- 2. 화자 수준 (uncounted 가설) --------------------------------------
    speaker_gap = []
    for rnd in rounds:
        for f in facts:
            fid = f["fact_id"]
            a_set = author.get((rnd, fid), set())
            o_status, o_set = ours.get((rnd, fid), (None, set()))
            if not a_set and not o_set:
                continue
            missed = sorted(a_set - o_set)      # 저자는 셌는데 우리가 안 센 화자
            extra = sorted(o_set - a_set)       # 우리만 센 화자
            if missed or extra:
                speaker_gap.append({
                    "round": rnd, "fact_id": fid, "our_status": o_status,
                    "n_author": len(a_set), "n_ours": len(o_set),
                    "our_missed": missed, "our_extra": extra})
    tot_author_sp = sum(len(v) for v in author.values())
    tot_our_sp = sum(len(s) for _, s in ours.values())

    # --- 3. FAR 재계산 (저자 축) --------------------------------------------
    far_author = []
    for rnd in rounds:
        lost = [f["fact_id"] for f in facts if not author.get((rnd, f["fact_id"]))]
        crit = [fid for fid in (f["fact_id"] for f in facts) if critical[fid]]
        lost_c = [fid for fid in lost if critical[fid]]
        far_author.append({
            "stage": rnd,
            "far_system": round(len(lost) / len(facts), 4),
            "far_critical": round(len(lost_c) / len(crit), 4) if crit else None})
    far_ours = judgment["summary"]["far_by_stage"]

    # --- 보고 ---------------------------------------------------------------
    print(f"[대조] 발화 {len(rows)}건 · 파싱 실패 {n_fail} · 셀 {n}개 "
          f"(라운드 {len(rounds)} x 팩트 {len(facts)})")
    print(f"\n== 1. 셀 수준 (살아있음 판정) ==")
    print(f"  양쪽 살아있음   {len(both):3d}")
    print(f"  양쪽 사라짐     {len(neither):3d}")
    print(f"  우리만 살아있음 {len(only_ours):3d}")
    print(f"  저자만 살아있음 {len(only_author):3d}")
    print(f"  -> 일치율 {agree}/{n} = {agree / n:.3f}")
    for c in only_ours:
        print(f"     [우리만] r{c['round']} {c['fact_id']} ({c['our_status']})")
    for c in only_author:
        print(f"     [저자만] r{c['round']} {c['fact_id']} "
              f"(우리 {c['our_status']}) 저자 화자 {c['author_speakers']}")

    print(f"\n== 2. 화자 수준 ==")
    print(f"  저자 축 (발화,팩트) 매치 총계 {tot_author_sp} · 우리 축 화자 명단 총계 {tot_our_sp}")
    print(f"  화자 집합이 갈린 셀 {len(speaker_gap)}개")
    n_missed = sum(len(g["our_missed"]) for g in speaker_gap)
    n_extra = sum(len(g["our_extra"]) for g in speaker_gap)
    print(f"  우리가 빠뜨린 화자 {n_missed}명분 · 우리만 센 화자 {n_extra}명분")
    for g in sorted(speaker_gap, key=lambda x: -len(x["our_missed"]))[:12]:
        print(f"     r{g['round']} {g['fact_id']} ({g['our_status']}) "
              f"저자 {g['n_author']}명 vs 우리 {g['n_ours']}명 "
              f"· 빠뜨림 {g['our_missed']} · 추가 {g['our_extra']}")

    print(f"\n== 3. FAR ==")
    print(f"  {'stage':>5} {'저자축':>10} {'우리축':>10} {'저자 critical':>14} {'우리 critical':>14}")
    for a, o in zip(far_author, far_ours):
        print(f"  {a['stage']:>5} {a['far_system']:>10.4f} {o['far_system']:>10.4f} "
              f"{a['far_critical']:>14.4f} {o['far_critical']:>14.4f}")

    if args.out:
        Path(args.out).write_text(json.dumps({
            "issue_id": args.issue, "run_id": args.run,
            "n_utterances": len(rows), "n_parse_fail": n_fail,
            "cell_level": {"both": len(both), "neither": len(neither),
                           "only_ours": only_ours, "only_author": only_author,
                           "agreement": round(agree / n, 4)},
            "speaker_level": {"n_divergent_cells": len(speaker_gap),
                              "n_our_missed": n_missed, "n_our_extra": n_extra,
                              "cells": speaker_gap},
            "far": {"author_axis": far_author, "our_axis": far_ours},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[대조] 저장: {args.out}")


if __name__ == "__main__":
    main()
