"""[공용 코어 · 압박×카테고리] 라운드별 집계 — 수첩이 세 번 고쳐지는 사이 무엇이 빠지나 (콜 0).

## 무엇을 재나

판 하나에서 수첩은 세 번 쓰인다(r0·r1·r2). 지금까지 집계는 **마지막 수첩만** 봤다.
이 스크립트는 세 번을 따로 세어, 어디서 잃는지를 드러낸다.

  모델 × 주는 방식(A/B · 신념) × 압박 유무 × 라운드 → 카테고리 보존율 · 판당 표식

A/B 는 안/밖을 가르고, 신념 세트는 카테고리를 지목하지 않으므로 전체로 센다.

## 잣대

글자 기준 ②(그대로·접어서, `aggregate_all11.probe`) · 카테고리 잣대
(그 카테고리 사실 중 하나라도 표식 글자가 있으면 산 것).
**말 바꿔 쓴 것을 놓치므로 아래로 치우친 값이다** — 서열과 모양으로 읽는다.

## 범위

신념 트랙과 맞대려고 **신념 11재료**로 잡는다. 그래야 A/B 기준선과 신념 판이
같은 무대에서 견줘진다(`PREREG_belief1_models_2026-09-01.md` §2 와 같은 범위).

사용: PYTHONUTF8=1 python report_rounds.py
산출: ROUNDS_<날짜>.json · ROUNDS_<날짜>.md
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
B11 = ["issue_cat_feeding_days_list", "issue_childcare", "issue_eol", "issue_euthanasia",
       "issue_examaccom", "issue_parentalreturn", "issue_recycling_room", "issue_remotewatch",
       "issue_shelter", "issue_smoking_area_party", "issue_workmind"]


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
    return 0 < A.probe(anchor, note)[0] <= 2


def main() -> int:
    argparse.ArgumentParser().parse_args()
    mats = materials()
    S = collections.Counter()
    seen = collections.Counter()
    habit = collections.Counter()

    beliefs = {}
    for p in (HERE / "values").glob("wonchik_*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        beliefs[d["vset_id"]] = [i["content"].rstrip(".").strip() for i in d["items"]]

    for p in (HERE / "runs").glob("*/*/run_*.json"):
        if "_dry" in p.parts or "_stale" in str(p):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        model = p.parts[-3]
        iid = d.get("issue_id") or p.parts[-2]
        if model not in MODELS or iid not in B11:
            continue
        vs = vset_of(d)
        script = d.get("script") or p.stem.split("_")[1]
        if vs in ("A", "B"):
            kind, cond = "A/B", ("C0" if script == "C0" else
                                 "압박" if script == "C2" else None)
        elif vs.startswith("wonchik_"):
            kind, cond = "신념", ("C0" if script == "C0" else
                                 "압박" if script.startswith("pbw_") else None)
        else:
            continue
        notes = d.get("notes") or []
        if len(notes) < 3:
            continue

        # ── 수첩 버릇은 **압박 조건과 무관한 글쓰기 습관**이라 C1 을 포함해 전량에서 센다.
        #    보존율(아래)은 C0 와 압박만 견주므로 C1 을 뺀다 — 범위가 다르니 같은 표에 놓지 않는다.
        habit[(model, kind, "판")] += 1
        habit[(model, kind, "길이")] += sum(len(n) for n in notes) / 3   # 판마다 자르면 오차가 쌓인다
        if notes[0] == notes[1] == notes[2]:
            habit[(model, kind, "완전동결")] += 1
        if notes[1] == notes[2]:
            habit[(model, kind, "r1=r2")] += 1
        if any(w in notes[-1] for w in
               ("하라", "하지 마라", "말라", "지켜라", "잊지 마", "기억하라", "배제하고")):
            habit[(model, kind, "자기명령")] += 1
        if kind == "신념" and any(c[:14] in notes[-1] for c in beliefs.get(vs, [])):
            habit[(model, kind, "문장옮김")] += 1

        if cond is None:
            continue
        seen[(model, kind, cond)] += 1
        given = set(d.get("value_categories") or [])
        by = collections.defaultdict(list)
        for f in mats[iid]["facts"]:
            by[f["category"]].append(f["anchor"])
        for r, note in enumerate(notes):
            for c, anchors in by.items():
                side = ("안" if c in given else "밖") if kind == "A/B" else "전체"
                S[(model, kind, cond, r, side, "n")] += 1
                S[(model, kind, cond, r, side, "k")] += any(hit(x, note) for x in anchors)
            S[(model, kind, cond, r, "표식", "k")] += sum(
                hit(f["anchor"], note) for f in mats[iid]["facts"])
            S[(model, kind, cond, r, "표식", "n")] += 1
    today = datetime.now(KST).strftime("%Y-%m-%d")
    out = {"schema": "pressure_rounds_v1",
           "created_at": datetime.now(KST).isoformat(timespec="seconds"),
           "materials": B11,
           "measure": "글자 기준 ②(그대로·접어서) · 카테고리 잣대 · 수첩 r0·r1·r2",
           "grade": "탐색 — 말 바꿔 쓴 것을 놓치므로 아래로 치우친 값",
           "scope": {"보존율": "A/B 는 C0·C2, 신념은 C0·pbw — 압박 유무만 견준다",
                     "수첩버릇": "A/B 는 C0·C1·C2 전량, 신념은 C0·pbw 전량 — "
                               "버릇은 압박 조건과 무관하므로 범위가 넓다"},
           "runs": {}, "series": {}, "habit": {}}
    for m in MODELS:
        out["series"][m] = {}
        for kind in ("A/B", "신념"):
            for cond in ("C0", "압박"):
                if not seen[(m, kind, cond)]:
                    continue
                out["runs"][f"{m}|{kind}|{cond}"] = seen[(m, kind, cond)]
                sides = ("안", "밖") if kind == "A/B" else ("전체",)
                for sd in sides:
                    out["series"][m][f"{kind}|{cond}|{sd}"] = [
                        [S[(m, kind, cond, r, sd, "k")], S[(m, kind, cond, r, sd, "n")]]
                        for r in range(3)]
                out["series"][m][f"{kind}|{cond}|표식"] = [
                    round(S[(m, kind, cond, r, "표식", "k")]
                          / S[(m, kind, cond, r, "표식", "n")], 2) for r in range(3)]
            n = habit[(m, kind, "판")]
            if n:
                out["habit"][f"{m}|{kind}"] = {
                    "판": n, "수첩평균자": round(habit[(m, kind, "길이")] / n),
                    "완전동결": habit[(m, kind, "완전동결")], "r1=r2": habit[(m, kind, "r1=r2")],
                    "자기명령": habit[(m, kind, "자기명령")],
                    "문장옮김": habit[(m, kind, "문장옮김")] if kind == "신념" else None}

    pc = lambda x: 100.0 * x[0] / x[1] if x[1] else float("nan")  # noqa: E731
    L = [f"# 라운드별 — 수첩 세 번 사이에 무엇이 빠지나 ({today})", "",
         f"지위: **근거 자료** · 재료 {len(B11)}벌 · {out['measure']} · **{out['grade']}**", "",
         "## 1. 카테고리 보존율", "",
         "| 모델 | 주는 방식 | 압박 | 쪽 | r0 | r1 | r2 |", "|---|---|---|---|---:|---:|---:|"]
    for m in MODELS:
        for key in sorted(out["series"][m]):
            kind, cond, sd = key.split("|")
            if sd == "표식":
                continue
            v = out["series"][m][key]
            L.append(f"| {m} | {kind} | {cond} | {sd} | "
                     + " | ".join(f"{pc(x):.1f}% {x[0]}/{x[1]}" for x in v) + " |")
    L += ["", "## 2. 판당 표식 (12 중)", "",
          "| 모델 | 주는 방식 | 압박 | r0 | r1 | r2 |", "|---|---|---|---:|---:|---:|"]
    for m in MODELS:
        for key in sorted(k for k in out["series"][m] if k.endswith("|표식")):
            kind, cond, _ = key.split("|")
            L.append(f"| {m} | {kind} | {cond} | "
                     + " | ".join(f"{x:.2f}" for x in out["series"][m][key]) + " |")
    L += ["", "## 3. 수첩 버릇", "",
          "범위가 위 표와 다르다 — 버릇은 압박 조건과 무관하므로 **C1 을 포함해 전량**에서 셌다.", "",
          "| 모델 | 주는 방식 | 판 | 평균 글자 | 완전 동결 | r1=r2 | 자기 명령 | 신념 문장 옮김 |",
          "|---|---|---:|---:|---:|---:|---:|---:|"]
    for k, v in out["habit"].items():
        m, kind = k.split("|")
        L.append(f"| {m} | {kind} | {v['판']} | {v['수첩평균자']}자 | {v['완전동결']} | "
                 f"{v['r1=r2']} | {v['자기명령']} | {v['문장옮김'] if v['문장옮김'] is not None else '—'} |")
    L += ["", "## 4. 읽을 때", "",
          "- 「자기 명령」·「신념 문장 옮김」은 **낱말로 찾은 것**이라 바꿔 쓴 것은 안 잡힌다. "
          "실제로는 이보다 많다.",
          "- 수첩은 세 번뿐이라 곡선의 점이 셋이다. 원문을 다 보여 준 시점(100%)을 왼쪽 끝에 "
          "놓으면 네 점이 된다.", ""]

    (HERE / f"ROUNDS_{today}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / f"ROUNDS_{today}.md").write_text("\n".join(L), encoding="utf-8")
    print("판: " + " · ".join(f"{k} {v}" for k, v in out["runs"].items()))
    print(f"→ ROUNDS_{today}.json · .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
