"""[공용 코어 · 압박×카테고리] 사실 보존율 — 표식 하나하나를 세어 안/밖을 가른다 (콜 0).

## 왜 따로 만드나

`report_rounds.py` 는 **카테고리 잣대**로 센다 — 그 카테고리 사실 둘 중 하나라도
표식이 있으면 산 것으로 본다. 그러면 천장 표식(어디서나 잡히는 것)이 하나만 껴도
그 칸은 늘 살아서 격차가 0 이 된다. 60칸 중 18칸이 그렇다
(`ANCHOR_VARIANCE_2026-09-02.md` §3).

이 스크립트는 **사실 하나하나를 따로 센다.** OR 로 뭉치지 않으므로 천장 표식이
옆 사실을 가려 주지 못한다. 대신 분모가 두 배가 된다(카테고리 6 → 사실 12).

  모델 × 주는 방식 × 압박 유무 × 라운드 × 안/밖 → 사실 보존율

## 잣대

글자 기준 ②(그대로·접어서, `aggregate_all11.probe`) — `report_rounds.py` 와 같은 자다.
**말 바꿔 쓴 것을 놓치므로 아래로 치우친 값이다.**

## 범위

재료를 11벌로 좁히지 않는다. **모델마다 실제로 돈 재료 전부**를 세고 재료 수를
같이 적는다. 모델을 견줄 때는 `--matched` 로 세 모델이 다 돈 재료만 남긴다 —
분모가 다르면 재료 교락이다.

사용: PYTHONUTF8=1 python report_facts.py [--matched]
산출: FACTS_<날짜>.json · FACTS_<날짜>.md
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aggregate_all11 as A  # noqa: E402

KST = timezone(timedelta(hours=9))
MODELS = ["claude-haiku", "gemini-flash", "gpt"]


def hit(anchor: str, note: str) -> bool:
    return 0 < A.probe(anchor, note)[0] <= 2


def materials() -> dict:
    reg = {}
    for p in sorted((HERE / "materials").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            reg[d["issue_id"]] = d
    return reg


def load():
    """(model, iid, kind, cond, vset, rep, given, notes, mat) 를 흘린다."""
    mats = materials()
    for p in (HERE / "runs").glob("*/*/run_*.json"):
        if "_dry" in p.parts or "_stale" in str(p):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        model = p.parts[-3]
        iid = d.get("issue_id") or p.parts[-2]
        if model not in MODELS or iid not in mats:
            continue
        vs = d.get("value_set_id") or d.get("value_set") or ""
        script = d.get("script") or p.stem.split("_")[1]
        if vs in ("A", "B"):
            kind = "A/B"
            cond = "C0" if script == "C0" else "압박" if script == "C2" else None
        elif vs.startswith("wonchik_"):
            kind = "신념"
            cond = "C0" if script == "C0" else "압박" if script.startswith("pbw_") else None
        else:
            continue
        notes = d.get("notes") or []
        if cond is None or len(notes) < 3:
            continue
        rep = d.get("rep") or int(p.stem.rsplit("rep", 1)[-1] or 0)
        yield (model, iid, kind, cond, vs, rep,
               set(d.get("value_categories") or []), notes, mats[iid])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matched", action="store_true",
                    help="세 모델이 다 돈 재료만 남긴다")
    args = ap.parse_args()

    rows = list(load())

    # ── 반복 균형: 한 재료 안에서 A 만 열 번 돈 옛 탐침이 있다(gemini `issue_drift` C2).
    #    그대로 세면 그 재료의 A 쪽이 3배 실린다. 세트마다 반복 수를 맞추고 최대 3 으로 자른다.
    bucket = collections.defaultdict(dict)
    for r in rows:
        model, iid, kind, cond, vs, rep = r[:6]
        bucket[(model, iid, kind, cond)].setdefault(vs, {})[rep] = r
    rows, trimmed = [], []
    for key, byset in sorted(bucket.items()):
        R = min(min(len(v) for v in byset.values()), 3)
        for vs, reps in sorted(byset.items()):
            kept = sorted(reps)[:R]
            if len(reps) > R:
                trimmed.append({"모델": key[0], "재료": key[1], "주는 방식": key[2],
                                "압박": key[3], "세트": vs,
                                "있던 반복": len(reps), "쓴 반복": R})
            rows += [reps[k] for k in kept]

    ran = collections.defaultdict(set)
    for model, iid, kind, *_ in rows:
        ran[(kind, model)].add(iid)

    keep = None
    if args.matched:
        keep = {}
        for kind in ("A/B", "신념"):
            sets = [ran[(kind, m)] for m in MODELS if ran[(kind, m)]]
            keep[kind] = set.intersection(*sets) if sets else set()

    S = collections.Counter()
    판 = collections.Counter()
    재료 = collections.defaultdict(set)
    for model, iid, kind, cond, vs, rep, given, notes, mat in rows:
        if keep is not None and iid not in keep[kind]:
            continue
        판[(model, kind, cond)] += 1
        재료[(model, kind, cond)].add(iid)
        for r, note in enumerate(notes[:3]):
            for f in mat["facts"]:
                side = ("안" if f["category"] in given else "밖") if kind == "A/B" else "전체"
                S[(model, kind, cond, r, side, "n")] += 1
                S[(model, kind, cond, r, side, "k")] += hit(f["anchor"], note)

    today = datetime.now(KST).strftime("%Y-%m-%d")
    out = {"schema": "pressure_facts_v1",
           "created_at": datetime.now(KST).isoformat(timespec="seconds"),
           "measure": "글자 기준 ②(그대로·접어서) · **사실 잣대** · 수첩 r0·r1·r2",
           "grade": "탐색 — 말 바꿔 쓴 것을 놓치므로 아래로 치우친 값",
           "matched": bool(args.matched),
           "trimmed": trimmed,
           "runs": {}, "materials": {}, "series": {}}
    for m in MODELS:
        out["series"][m] = {}
        for kind in ("A/B", "신념"):
            for cond in ("C0", "압박"):
                if not 판[(m, kind, cond)]:
                    continue
                key = f"{kind}|{cond}"
                out["runs"][f"{m}|{key}"] = 판[(m, kind, cond)]
                out["materials"][f"{m}|{key}"] = len(재료[(m, kind, cond)])
                for sd in (("안", "밖") if kind == "A/B" else ("전체",)):
                    out["series"][m][f"{key}|{sd}"] = [
                        [S[(m, kind, cond, r, sd, "k")], S[(m, kind, cond, r, sd, "n")]]
                        for r in range(3)]

    pc = lambda x: 100.0 * x[0] / x[1] if x[1] else float("nan")  # noqa: E731
    cell = lambda x: f"{pc(x):.1f}% {x[0]}/{x[1]}"                # noqa: E731
    L = [f"# 사실 보존율 — 표식 하나하나 ({today})", "",
         f"지위: **근거 자료** · {out['measure']} · **{out['grade']}**"
         + ("  · 세 모델 짝맞춤" if args.matched else ""), "",
         "카테고리 잣대와 달리 OR 로 뭉치지 않는다 — 천장 표식이 옆 사실을 가려 주지 못한다.", "",
         "## 1. 라운드별", "",
         "| 모델 | 주는 방식 | 압박 | 재료 | 판 | 쪽 | r0 | r1 | r2 |",
         "|---|---|---|---:|---:|---|---:|---:|---:|"]
    for m in MODELS:
        for key in sorted(out["series"][m]):
            kind, cond, sd = key.split("|")
            v = out["series"][m][key]
            L.append(f"| {m} | {kind} | {cond} | {out['materials'][f'{m}|{kind}|{cond}']} "
                     f"| {out['runs'][f'{m}|{kind}|{cond}']} | {sd} | "
                     + " | ".join(cell(x) for x in v) + " |")

    L += ["", "## 2. 안 − 밖 격차 (A/B)", "",
          "| 모델 | 압박 | 재료 | r0 | r1 | r2 |", "|---|---|---:|---:|---:|---:|"]
    for m in MODELS:
        for cond in ("C0", "압박"):
            a = out["series"][m].get(f"A/B|{cond}|안")
            b = out["series"][m].get(f"A/B|{cond}|밖")
            if not a or not b:
                continue
            L.append(f"| {m} | {cond} | {out['materials'][f'{m}|A/B|{cond}']} | "
                     + " | ".join(f"**{pc(a[r]) - pc(b[r]):+.1f}%p**" for r in range(3)) + " |")

    L += ["", "## 3. 읽을 때", "",
          "- **분모가 카테고리 잣대의 두 배다.** 사실 12개를 따로 세므로 판당 12칸이다.",
          "- 격차는 **거울 설계가 지킨다** — 같은 사실이 A판에서는 안, B판에서는 밖이다.",
          "- 절대값이 아니라 서열과 방향으로 읽는다.",
          "- **반복을 세트마다 맞춰 잘랐다**(최대 3). 한쪽만 많이 돈 옛 탐침이 "
          "그 재료를 과대 대표하는 것을 막는다.", ""]
    if trimmed:
        L += ["### 잘라낸 것", "",
              "| 모델 | 재료 | 주는 방식 | 압박 | 세트 | 있던 반복 | 쓴 반복 |",
              "|---|---|---|---|---|---:|---:|"]
        L += [f"| {t['모델']} | {t['재료']} | {t['주는 방식']} | {t['압박']} | {t['세트']} "
              f"| {t['있던 반복']} | {t['쓴 반복']} |" for t in trimmed]
        L.append("")

    (HERE / f"FACTS_{today}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / f"FACTS_{today}.md").write_text("\n".join(L), encoding="utf-8")
    print(f"FACTS_{today}.json · FACTS_{today}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
