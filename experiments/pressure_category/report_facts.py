"""[공용 코어 · 압박×카테고리] 사실 보존율 — 표식 하나하나를 세고 세트 축으로 가른다 (콜 0).

## 왜 따로 만드나

`report_rounds.py` 는 **카테고리 잣대**로 센다 — 그 카테고리 사실 둘 중 하나라도
표식이 있으면 산 것으로 본다. 그러면 천장 표식(어디서나 잡히는 것)이 하나만 껴도
그 칸은 늘 살아서 격차가 0 이 된다. 60칸 중 18칸이 그렇다
(`ANCHOR_VARIANCE_2026-09-02.md` §3).

이 스크립트는 **사실 하나하나를 따로 센다.** OR 로 뭉치지 않으므로 천장 표식이
옆 사실을 가려 주지 못한다. 대신 분모가 두 배가 된다(카테고리 6 → 사실 12).

## 왜 세트를 가르나

C1 은 「가치 편으로 미는」 압박이고 C2 는 「반대로 미는」 압박인데, **편이냐 반대냐는
그 판에 준 세트를 기준으로 정해진다.** A세트에서 미는 방향과 B세트에서 미는 방향이
서로 반대다. 그래서 A·B 를 한 덩이로 묶으면 압박 방향의 효과가 상쇄돼 안 보인다.

세트를 갈라 보면 갈린다 — **A 와 B 에서 같은 방향으로 움직이면 가치 효과이고,
한쪽에서만 움직이면 재료가 기운 것이다.**

  모델 × 세트(A·B) × 각본(C0·C1·C2) × 라운드 × 안/밖 → 사실 보존율

## 잣대

글자 기준 ②(그대로·접어서, `aggregate_all11.probe`) — `report_rounds.py` 와 같은 자다.
**말 바꿔 쓴 것을 놓치므로 아래로 치우친 값이다.**

## 범위

재료를 11벌로 좁히지 않는다. `--matched` 로 세 모델이 다 돈 재료만 남긴다 —
분모가 다르면 재료 교락이다. 세트마다 반복 수를 맞추고 최대 3 으로 자른다.

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
각본뜻 = {"C0": "압박 없음", "C1": "편들어 미는 압박", "C2": "반대로 미는 압박",
          "pbw": "반대로 미는 압박"}


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
    """(model, iid, kind, vset, cond, rep, given, notes, mat) 를 흘린다."""
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
            kind, cond = "A/B", (script if script in ("C0", "C1", "C2") else None)
        elif vs.startswith("wonchik_"):
            kind = "신념"
            cond = "C0" if script == "C0" else "pbw" if script.startswith("pbw_") else None
        else:
            continue
        notes = d.get("notes") or []
        if cond is None or len(notes) < 3:
            continue
        rep = d.get("rep") or int(p.stem.rsplit("rep", 1)[-1] or 0)
        yield (model, iid, kind, vs, cond, rep,
               set(d.get("value_categories") or []), notes, mats[iid])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matched", action="store_true", help="세 모델이 다 돈 재료만 남긴다")
    args = ap.parse_args()

    rows = list(load())

    # ── 반복 균형: 한쪽 세트만 열 번 돈 옛 탐침이 그 재료를 과대 대표하는 것을 막는다
    #    (gemini `issue_drift` C2 는 A 10판·B 3판이었다). 세트마다 맞추고 최대 3.
    bucket = collections.defaultdict(dict)
    for r in rows:
        model, iid, kind, vs, cond, rep = r[:6]
        bucket[(model, iid, kind, cond)].setdefault(vs, {})[rep] = r
    rows, trimmed = [], []
    for key, byset in sorted(bucket.items()):
        R = min(min(len(v) for v in byset.values()), 3)
        for vs, reps in sorted(byset.items()):
            if len(reps) > R:
                trimmed.append({"모델": key[0], "재료": key[1], "각본": key[3],
                                "세트": vs, "있던 반복": len(reps), "쓴 반복": R})
            rows += [reps[k] for k in sorted(reps)[:R]]

    keep = None
    if args.matched:
        ran = collections.defaultdict(set)
        for model, iid, kind, *_ in rows:
            ran[(kind, model)].add(iid)
        keep = {}
        for kind in ("A/B", "신념"):
            sets = [ran[(kind, m)] for m in MODELS if ran[(kind, m)]]
            keep[kind] = set.intersection(*sets) if sets else set()

    S = collections.Counter()
    판 = collections.Counter()
    재료 = collections.defaultdict(set)
    for model, iid, kind, vs, cond, rep, given, notes, mat in rows:
        if keep is not None and iid not in keep[kind]:
            continue
        축 = vs if kind == "A/B" else "신념"
        판[(model, 축, cond)] += 1
        재료[(model, 축, cond)].add(iid)
        for r, note in enumerate(notes[:3]):
            for f in mat["facts"]:
                side = ("안" if f["category"] in given else "밖") if kind == "A/B" else "전체"
                S[(model, 축, cond, r, side, "n")] += 1
                S[(model, 축, cond, r, side, "k")] += hit(f["anchor"], note)

    today = datetime.now(KST).strftime("%Y-%m-%d")
    out = {"schema": "pressure_facts_v2",
           "created_at": datetime.now(KST).isoformat(timespec="seconds"),
           "measure": "글자 기준 ②(그대로·접어서) · **사실 잣대** · 수첩 r0·r1·r2",
           "grade": "탐색 — 말 바꿔 쓴 것을 놓치므로 아래로 치우친 값",
           "축": "A/B 는 준 세트(A·B)로 가른다 — 압박이 미는 방향이 세트마다 반대다",
           "matched": bool(args.matched), "trimmed": trimmed,
           "runs": {}, "materials": {}, "series": {}}
    축들 = ["A", "B", "신념"]
    for m in MODELS:
        out["series"][m] = {}
        for 축 in 축들:
            for cond in ("C0", "C1", "C2", "pbw"):
                if not 판[(m, 축, cond)]:
                    continue
                k = f"{축}|{cond}"
                out["runs"][f"{m}|{k}"] = 판[(m, 축, cond)]
                out["materials"][f"{m}|{k}"] = len(재료[(m, 축, cond)])
                for sd in (("안", "밖") if 축 in ("A", "B") else ("전체",)):
                    out["series"][m][f"{k}|{sd}"] = [
                        [S[(m, 축, cond, r, sd, "k")], S[(m, 축, cond, r, sd, "n")]]
                        for r in range(3)]

    pc = lambda x: 100.0 * x[0] / x[1] if x[1] else float("nan")   # noqa: E731
    cell = lambda x: f"{x[0]}/{x[1]} {pc(x):.1f}%"                 # noqa: E731
    gap = lambda a, b, r: pc(a[r]) - pc(b[r])                      # noqa: E731

    L = [f"# 사실 보존율 — 세트 축으로 가른 압박 ({today})", "",
         f"지위: **근거 자료** · {out['measure']} · **{out['grade']}**"
         + ("  · 세 모델 짝맞춤" if args.matched else ""), "",
         "카테고리 잣대와 달리 OR 로 뭉치지 않는다 — 천장 표식이 옆 사실을 가려 주지 못한다.",
         "",
         "각본: **C0** 압박 없음 · **C1** 그 판에 준 가치 **편들어** 미는 압박 · "
         "**C2** 그 가치와 **반대로** 미는 압박.", "",
         "## 1. 세트 축 — 라운드별 (칸 = 남은 사실/전체 사실)", "",
         "| 모델 | 세트 | 각본 | 재료 | 판 | 쪽 | r0 | r1 | r2 |",
         "|---|---|---|---:|---:|---|---:|---:|---:|"]
    for m in MODELS:
        for 축 in 축들:
            for cond in ("C0", "C1", "C2", "pbw"):
                k = f"{축}|{cond}"
                if f"{m}|{k}" not in out["runs"]:
                    continue
                for sd in ("안", "밖", "전체"):
                    v = out["series"][m].get(f"{k}|{sd}")
                    if not v:
                        continue
                    L.append(f"| {m} | {축} | {cond} {각본뜻[cond]} | "
                             f"{out['materials'][f'{m}|{k}']} | {out['runs'][f'{m}|{k}']} | "
                             f"{sd} | " + " | ".join(cell(x) for x in v) + " |")

    L += ["", "## 2. 안 − 밖 격차 — 세트마다 각본을 나란히", "",
          "| 모델 | 세트 | 각본 | r0 | r1 | r2 |", "|---|---|---|---:|---:|---:|"]
    for m in MODELS:
        for 축 in ("A", "B"):
            for cond in ("C0", "C1", "C2"):
                a = out["series"][m].get(f"{축}|{cond}|안")
                b = out["series"][m].get(f"{축}|{cond}|밖")
                if not a or not b:
                    continue
                L.append(f"| {m} | {축} | {cond} {각본뜻[cond]} | "
                         + " | ".join(f"{gap(a, b, r):+.1f}%p" for r in range(3)) + " |")

    L += ["", "## 3. 대칭 검사 — 압박이 A 와 B 에서 같은 방향으로 움직이나", "",
          "마지막 수첩(r2) 격차가 C0 에서 얼마나 움직였나. **A 와 B 의 부호가 같으면**",
          "압박 방향이 실제로 일한 것이고, 한쪽만 움직이면 재료가 기운 것이다.", "",
          "| 모델 | 각본 | A세트 | B세트 | 부호 |", "|---|---|---:|---:|---|"]
    for m in MODELS:
        for cond in ("C1", "C2"):
            d = {}
            for 축 in ("A", "B"):
                z = [out["series"][m].get(f"{축}|{c}|{s}")
                     for c in ("C0", cond) for s in ("안", "밖")]
                if not all(z):
                    break
                d[축] = gap(z[2], z[3], 2) - gap(z[0], z[1], 2)
            if len(d) != 2:
                continue
            같 = "**같다**" if d["A"] * d["B"] > 0 else "다르다" if d["A"] * d["B"] < 0 else "0"
            L.append(f"| {m} | {cond} {각본뜻[cond]} | {d['A']:+.1f}%p | {d['B']:+.1f}%p | {같} |")

    L += ["", "## 4. 읽을 때", "",
          "- **분모가 카테고리 잣대의 두 배다.** 사실 12개를 따로 세므로 판당 12칸이다.",
          "- 격차는 **거울 설계가 지킨다** — 같은 사실이 A판에서는 안, B판에서는 밖이다.",
          "- 신념 세트는 카테고리를 지목하지 않으므로 **안/밖을 못 가른다**(전체만).",
          "- 절대값이 아니라 서열과 방향으로 읽는다.",
          "- **반복을 세트마다 맞춰 잘랐다**(최대 3).",
          "- **§2 의 세트별 격차 「수준」을 세트끼리 견주지 마라.** 한 세트 안의 격차에는",
          "  「가치 효과」와 「그 갈래가 원래 잘 남는가」가 섞인다. haiku A 5.1%p 대 B 23.1%p",
          "  는 대부분 갈래 차이다 — 거울로 상쇄된 값은 둘을 합친 것이다.",
          "  **§3 은 같은 세트 안에서 C0 을 빼므로 그 오염이 없다** — 압박 효과는 §3 으로 읽는다.", ""]
    if trimmed:
        L += ["### 잘라낸 것", "",
              "| 모델 | 재료 | 각본 | 세트 | 있던 반복 | 쓴 반복 |", "|---|---|---|---|---:|---:|"]
        L += [f"| {t['모델']} | {t['재료']} | {t['각본']} | {t['세트']} "
              f"| {t['있던 반복']} | {t['쓴 반복']} |" for t in trimmed]
        L.append("")

    (HERE / f"FACTS_{today}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / f"FACTS_{today}.md").write_text("\n".join(L), encoding="utf-8")
    print(f"FACTS_{today}.json · FACTS_{today}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
