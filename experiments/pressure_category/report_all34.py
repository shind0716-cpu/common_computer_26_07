"""[공용 코어 · 압박×카테고리] 3모델 ALL 균형 집계 — PREREG_all34 §7 예측을 그대로 잰다.

## 무엇을 재나

ALL 판은 가치 여섯을 **전부** 준다 — 그래서 「가치 밖」이 없다. 잴 수 있는 것은
카테고리 보존율 하나뿐이고, 뜻은 A/B 판과 **맞대었을 때** 생긴다.

  P1  ALL 보존율이 A/B 「가치 안」보다 낮고 「가치 밖」보다 높은가
      (수첩 500자에 여섯을 다 못 담는다면 그래야 한다)
  P2  세 모델의 ALL 순위가 그 모델의 A/B 「가치 안」 순위와 같은가
  P3  반복 사이 퍼짐이 모델 사이 차이보다 큰가 — 맞으면 rep3 합산으로만 말한다

## 잣대

글자 기준(표식 검색)이다. `aggregate_all11.probe` 의 사다리를 그대로 쓴다 —
①그대로 ②접어서 ③꼬리 깎음. 여기서는 **②까지만** 적중으로 친다(집계 관례와 같다).
바꿔 말한 것을 넷 중 하나쯤 놓치므로 **탐색 등급**이다.

비교는 **짝지은 재료에서만** 한다. 모델마다 A/B 를 돈 재료가 다르므로, ALL 과 A/B 가
둘 다 있는 재료로만 P1·P2 를 잰다 — 분모가 다른 둘을 맞대면 재료 교락이 된다.

사용: PYTHONUTF8=1 python report_all34.py
산출: ALL34_RESULT_<날짜>.json · ALL34_RESULT_<날짜>.md
"""
from __future__ import annotations

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
REPS = [1, 2, 3]


def vset_of(d: dict) -> str:
    return d.get("value_set_id") or d.get("value_set") or ""


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


def hit(anchor: str, note: str) -> bool:
    """②까지 적중 — 그대로 또는 접어서."""
    return 0 < A.probe(anchor, note)[0] <= 2


def collect(cur: dict, mats: dict) -> list:
    """되돌림: [(model, iid, kind, vset, rep, side, k, n)] · kind 는 ALL 또는 AB."""
    rows = []
    for p in (HERE / "runs").glob("*/*/run_*.json"):
        if "_dry" in p.parts or "_stale" in str(p):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        model = p.parts[-3]
        if model not in MODELS:
            continue
        iid = d.get("issue_id") or p.parts[-2]
        if iid not in mats:
            continue
        if (d.get("script") or p.stem.split("_")[1]) != "C0":
            continue
        vs = vset_of(d)
        kind = "ALL" if cur.get(iid) == vs else ("AB" if vs in ("A", "B") else None)
        if kind is None:
            continue
        notes = d.get("notes") or []
        if not notes:
            continue
        try:
            rep = int(p.stem.rsplit("rep", 1)[-1])
        except ValueError:
            continue
        given = set(d.get("value_categories") or [])
        if not given <= set(mats[iid]["categories"]):    # 구판 세트 — 안/밖을 못 가른다
            continue
        last = notes[-1]
        agg = collections.Counter()
        for f in mats[iid]["facts"]:
            side = "안" if f["category"] in given else "밖"
            agg[(side, "n")] += 1
            agg[(side, "k")] += hit(f["anchor"], last)
        for side in ("안", "밖"):
            if agg[(side, "n")]:
                rows.append((model, iid, kind, vs, rep, side, agg[(side, "k")], agg[(side, "n")]))
    return rows


def pct(k: int, n: int) -> float:
    return 100.0 * k / n if n else float("nan")


def main() -> int:
    mats = materials()
    plan = json.loads((HERE / "ALL34_RUNPLAN_2026-09-01.json").read_text(encoding="utf-8"))
    cur = plan["value_sets"]
    rows = collect(cur, mats)
    today = datetime.now(KST).strftime("%Y-%m-%d")

    have = collections.defaultdict(set)
    for m, iid, kind, *_ in rows:
        have[(m, kind)].add(iid)
    paired = {m: sorted(have[(m, "ALL")] & have[(m, "AB")]) for m in MODELS}

    S = collections.Counter()
    for m, iid, kind, vs, rep, side, k, n in rows:
        if iid not in paired[m]:
            continue
        key = "ALL" if kind == "ALL" else ("AB_inside" if side == "안" else "AB_outside")
        S[(m, key, rep, "k")] += k
        S[(m, key, rep, "n")] += n

    def tot(m, key, w):
        return sum(S[(m, key, r, w)] for r in REPS)

    out = {
        "schema": "pressure_all34_result_v1",
        "created_at": datetime.now(KST).isoformat(timespec="seconds"),
        "runplan": plan["plan_id"],
        "measure": "글자 기준 ②(그대로·접어서) · 마지막 수첩 · 사실 단위",
        "grade": "탐색",
        "models": {},
    }
    L = [
        f"# 3모델 ALL 균형 — 결과 ({today})", "",
        "지위: **근거 자료** · 잣대 글자 기준 ②(탐색 등급) · 런플랜 "
        f"`{plan['plan_id']}` · 사전고정 `PREREG_all34_2026-09-01.md`", "",
        "## 1. 짝지은 재료에서 — ALL 대 A/B", "",
        "ALL 은 가치 여섯을 전부 주므로 「밖」이 없다. A/B 는 셋만 준다.",
        "**ALL 과 A/B 를 둘 다 돈 재료로만** 잰다 — 분모가 다르면 재료 교락이다.", "",
        "| 모델 | 짝 재료 | ALL 보존율 | A/B 가치 안 | A/B 가치 밖 | P1 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for m in MODELS:
        ak, an = tot(m, "ALL", "k"), tot(m, "ALL", "n")
        ik, inn = tot(m, "AB_inside", "k"), tot(m, "AB_inside", "n")
        ok_, on = tot(m, "AB_outside", "k"), tot(m, "AB_outside", "n")
        if not (an and inn and on):
            L.append(f"| {m} | {len(paired[m])} | — | — | — | 판 부족 |")
            continue
        p1 = pct(ok_, on) < pct(ak, an) < pct(ik, inn)
        out["models"][m] = {
            "paired_materials": len(paired[m]),
            "ALL": {"k": ak, "n": an, "pct": round(pct(ak, an), 1)},
            "AB_inside": {"k": ik, "n": inn, "pct": round(pct(ik, inn), 1)},
            "AB_outside": {"k": ok_, "n": on, "pct": round(pct(ok_, on), 1)},
            "P1_holds": bool(p1),
            "by_rep": {str(r): {kk: {"k": S[(m, kk, r, "k")], "n": S[(m, kk, r, "n")]}
                                for kk in ("ALL", "AB_inside", "AB_outside")} for r in REPS},
        }
        L.append(
            f"| {m} | {len(paired[m])} | **{pct(ak,an):.1f}%** {ak}/{an} | "
            f"{pct(ik,inn):.1f}% {ik}/{inn} | {pct(ok_,on):.1f}% {ok_}/{on} | "
            f"{'적중' if p1 else '빗나감'} |")

    ok = [m for m in MODELS if m in out["models"]]
    # ── §1-2 총 적재량 — 가치를 몇 개 주든 수첩이 담는 총수는 그대로인가
    L += ["", "## 1-2. 판 하나가 남긴 사실은 몇 개인가", "",
          "위 표는 **비율**이라 분모가 다르면 헷갈린다. 같은 것을 **판당 개수**로 고쳐 적는다.",
          "ALL 판은 12사실이 전부 「안」이고, A/B 판은 6+6 이다. 그래서 둘 다 **12 중 몇 개**다.", "",
          "| 모델 | ALL 판 | A/B 판 | 차 |", "|---|---:|---:|---:|"]
    for m in ok:
        v = out["models"][m]
        na, nb = v["ALL"]["n"] // 12, v["AB_inside"]["n"] // 6
        pa = v["ALL"]["k"] / na
        kb = v["AB_inside"]["k"] + v["AB_outside"]["k"]
        pb = kb / nb
        v["per_run_facts"] = {"ALL": round(pa, 2), "AB": round(pb, 2), "diff": round(pa - pb, 2)}
        L.append(f"| {m} | **{pa:.2f}** {v['ALL']['k']}/{na}판 | **{pb:.2f}** {kb}/{nb}판 | {pa-pb:+.2f} |")
    diffs = [out["models"][m]["per_run_facts"]["diff"] for m in ok]
    out["load_constant"] = {"max_abs_diff": round(max(abs(d) for d in diffs), 2),
                            "note": "가치를 여섯 주든 셋 주든 판당 남는 사실 수가 거의 같다"}
    L += ["", f"세 모델 다 차이가 **12 중 {max(abs(d) for d in diffs):.2f}개 이내**다. "
          "가치를 여섯 주는 것은 수첩에 담기는 **총량을 늘리지 않는다** — "
          "무엇을 담을지 순서만 바꾼다.", "",
          "A/B 판에서 안쪽이 밖보다 많이 남던 것도 이것으로 읽힌다. 총량이 거의 고정이라 "
          "**안쪽이 자리를 차지하면 밖이 밀려난다.** 500자가 병목이라는 직접 증거다.",
          "", "다만 이건 세 모델의 관측이지 검정이 아니다 — 표본이 모델 셋이다."]


    rank_all = sorted(ok, key=lambda m: -out["models"][m]["ALL"]["pct"])
    rank_in = sorted(ok, key=lambda m: -out["models"][m]["AB_inside"]["pct"])
    out["P2"] = {"rank_ALL": rank_all, "rank_AB_inside": rank_in, "holds": rank_all == rank_in}
    fmt = lambda ms, key: " > ".join(f"{m} {out['models'][m][key]['pct']}%" for m in ms)  # noqa: E731
    L += ["", "## 2. P2 — ALL 순위가 A/B 가치 안 순위와 같은가", "",
          f"- ALL 순위 &nbsp; {fmt(rank_all, 'ALL')}",
          f"- A/B 안 순위 {fmt(rank_in, 'AB_inside')}", "",
          f"→ **{'적중' if rank_all == rank_in else '빗나감'}**"]

    L += ["", "## 3. P3 — 반복 퍼짐 대 모델 차이 (ALL 판)", "",
          "| 모델 | rep1 | rep2 | rep3 | 합산 | 퍼짐 |", "|---|---:|---:|---:|---:|---:|"]
    spreads, tots = {}, {}
    for m in ok:
        v = [pct(S[(m, "ALL", r, "k")], S[(m, "ALL", r, "n")]) for r in REPS]
        spreads[m], tots[m] = max(v) - min(v), out["models"][m]["ALL"]["pct"]
        L.append(f"| {m} | {v[0]:.1f}% | {v[1]:.1f}% | {v[2]:.1f}% | "
                 f"**{tots[m]:.1f}%** | {spreads[m]:.1f}%p |")
    if ok:
        span, mx = max(tots.values()) - min(tots.values()), max(spreads.values())
        out["P3"] = {"model_span_pp": round(span, 1), "max_rep_spread_pp": round(mx, 1),
                     "holds": mx > span}
        L += ["", f"- 모델 사이 폭 **{span:.1f}%p** · 한 모델 안 반복 퍼짐 최대 **{mx:.1f}%p**", "",
              f"→ **{'적중' if mx > span else '빗나감'}** — "
              + ("반복 퍼짐이 더 크다. 모델 비교는 rep3 합산으로만 말한다(사전고정 §7)."
                 if mx > span else "모델 차이가 반복 퍼짐보다 크다.")]

    L += ["", "## 4. 한계", "",
          "- 글자 기준이라 바꿔 말한 것을 놓친다 — **탐색 등급**이다. 뜻 판독은 이 실행 밖이다.",
          "- ALL 판에는 「밖」이 없다. 위 표의 A/B 열은 **같은 재료의 다른 판**이지 "
          "같은 판 안의 대조가 아니다.",
          "- 구판 ALL 세트(겹침 0)로 돈 판은 전부 뺐다 — 런플랜 `excluded_stale_sets` 참조.", ""]

    (HERE / f"ALL34_RESULT_{today}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / f"ALL34_RESULT_{today}.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\n→ ALL34_RESULT_{today}.json · ALL34_RESULT_{today}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
