# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 판독물 원장 — 줄글을 표로 엮는다. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/ledger.py

## 왜 있나

`READ_*.md` 18개는 사람이 읽으라고 쓴 줄글이다. 그래서 「20판 중 14판」이
문장 안에 박혀 있고, 열여덟을 나란히 놓고 볼 수가 없다(요한 지적, 2026-09-03).

에이전트 18명이 각자 자기 판독물 하나를 읽고 **판독물이 이미 적어 놓은 것만**
구조로 옮겼다. 새로 판단한 것이 아니다. 그 뒤 다른 18명이 원문과 맞대 봤다.

## 이 자가 하는 일

원장(`_LEDGER_RAW.json`)을 받아 —

1. **인용을 원문과 글자 그대로 맞대 본다.** 지어낸 인용을 기계로 잡는다.
   에이전트 대조와 별개다 — 대조는 에이전트가 하고, 이건 자가 한다.
2. 판독물 18개를 한 표로 편다.
3. 채움 갈래·접힘 표지·세는 말을 모델별로 모은다.

## 조심할 것

- **원장은 판독물의 말이지 수첩의 말이 아니다.** 「20판 중 14판」은 그 조각 안의
  몫이지 모집단 비율이 아니다. 조각마다 20판씩이고 씨앗은 20260903 이다.
- **모델 사이 합산을 하지 마라.** 조건 여섯이 모델마다 같은 크기가 아니다
  (가치 판 20 · 신념 판 20 인데 모집단은 324 대 33 이다).
- -1 은 「판독물이 안 적었다」는 뜻이다. 0 과 다르다. 평균에 넣지 마라.

산출: READS_LEDGER.json · READS_TABLE.md
"""
import json
import os
import re
import pathlib
import collections

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
NAME = {"gpt": "gpt", "gemini-flash": "제미나이", "claude-haiku": "하이쿠"}
ORD = ["gpt", "gemini-flash", "claude-haiku"]

W = []


def w(s=""):
    W.append(s)


def 씻기(s):
    """맞대 보기 전에 공백·강조기호만 지운다. 글자는 안 건드린다."""
    return re.sub(r"[\s*`_]+", "", s or "")


def 인용확인(원장):
    """인용이 판독물 원문에 글자 그대로 있나 — 자가 직접 본다."""
    결과 = []
    for rec in 원장:
        p = H / f"{rec['file']}.md"
        원문 = 씻기(p.read_text(encoding="utf-8")) if p.exists() else ""
        칸 = []
        for 자리, q in 인용모으기(rec):
            if not q:
                continue
            칸.append((자리, q, 씻기(q) in 원문))
        결과.append((rec, 칸))
    return 결과


def 인용모으기(rec):
    yield "skeleton_follow", (rec.get("skeleton_follow") or {}).get("quote", "")
    yield "flips", (rec.get("flips") or {}).get("quote", "")
    for m in rec.get("fold_markers") or []:
        yield f"fold:{m.get('marker', '')}", m.get("quote", "")
    for k in rec.get("fill_kinds") or []:
        yield f"fill:{k.get('name', '')}", k.get("quote", "")
    for c in rec.get("counts") or []:
        yield f"count:{c.get('item', '')}", c.get("quote", "")


def kn(d):
    if not d:
        return "—"
    k, n = d.get("k", -1), d.get("n", -1)
    if k < 0 and n < 0:
        return "—"
    if n < 0:
        return str(k)
    return f"{k}/{n}"


def main():
    raw = json.loads((H / "_LEDGER_RAW.json").read_text(encoding="utf-8"))
    원장 = raw["ledger"]
    원장.sort(key=lambda r: (ORD.index(r["model"]), r["cond"]))
    확인 = 인용확인(원장)
    총인용 = sum(len(c) for _, c in 확인)
    맞은인용 = sum(1 for _, c in 확인 for _, _, ok in c if ok)

    w("# 판독물 원장 — 줄글을 표로 (2026-09-03)")
    w("")
    w("> 기계 산출물. `tools/ledger.py` 가 쓴다. 손으로 고치지 마라.")
    w(f"> 판독물 {len(원장)}개 · 조각마다 20판 × 수첩 3장 · 씨앗 20260903")
    w("")
    w("**원장은 판독물의 말이지 수첩의 말이 아니다.** 「20판 중 14판」은 그 조각 안의")
    w("몫이지 모집단 비율이 아니다. `—` 는 판독물이 안 적었다는 뜻이고 0 과 다르다.")

    # ── 0. 두 겹 대조 ──────────────────────────────────────────────
    w("\n## 0. 먼저 — 지어낸 것이 있나\n")
    w(f"에이전트 대조: **맞음 {raw.get('clean', 0)}/{raw.get('got', 0)}**")
    for d in raw.get("dirty") or []:
        w(f"  - `{d['file'] if 'file' in d else d.get('f', '')}` 어긋남 {d.get('n', 0)}건")
    w("")
    w(f"자가 인용 대조: **원문에 글자 그대로 있는 인용 {맞은인용}/{총인용}"
      f" = {맞은인용 / 총인용 * 100:.0f}%**" if 총인용 else "인용 없음")
    안맞음 = [(rec, 자리, q) for rec, c in 확인 for 자리, q, ok in c if not ok]
    if 안맞음:
        w("")
        w("원문에서 못 찾은 인용 — **손으로 봐야 한다**:")
        w("")
        for rec, 자리, q in 안맞음[:40]:
            w(f"  - `{rec['file']}` · {자리} · 「{q[:70]}」")
        if len(안맞음) > 40:
            w(f"  - … 그 밖 {len(안맞음) - 40}건")

    # ── 1. 판독물 한 줄씩 ──────────────────────────────────────────
    w("\n## 1. 판독물 열여덟 — 한 줄씩\n")
    w("| 모델 | 조각 | 틀 따름 | 결론 뒤집힘 | 접힘 표지 | 채움 갈래 | 세는 말 |")
    w("|---|---|---:|---:|---|---:|---:|")
    for r in 원장:
        표지 = " · ".join(f"`{m['marker']}`" for m in (r.get("fold_markers") or [])[:4]) or "—"
        w(f"| {NAME[r['model']]} | {r['cond']} | {kn(r.get('skeleton_follow'))} |"
          f" {kn(r.get('flips'))} | {표지} |"
          f" {len(r.get('fill_kinds') or [])} | {len(r.get('counts') or [])} |")

    # ── 2. 뼈대 ───────────────────────────────────────────────────
    w("\n## 2. 뼈대 — 판독물이 그린 도식\n")
    for m in ORD:
        w(f"\n### {NAME[m]}\n")
        for r in [x for x in 원장 if x["model"] == m]:
            도 = (r.get("skeleton") or "").strip().replace("\n", " ")
            w(f"- **{r['cond']}** ({kn(r.get('skeleton_follow'))}) — {도 or '—'}")

    # ── 3. 채움 갈래 — 이 원장의 알맹이 ────────────────────────────
    w("\n## 3. 채움 갈래 — 사실이 아닌 문장은 무엇으로 채워지나\n")
    w("판독물이 붙인 이름 그대로다. 인용은 수첩 원문이다.\n")
    for m in ORD:
        갈 = [(r["cond"], k) for r in 원장 if r["model"] == m
              for k in (r.get("fill_kinds") or [])]
        w(f"\n### {NAME[m]} — 갈래 {len(갈)}개\n")
        w("| 조각 | 이름 | 판수 | 무엇인가 | 수첩 원문 |")
        w("|---|---|---:|---|---|")
        for 조건, k in 갈:
            판 = k.get("cases", -1)
            인 = (k.get("quote") or "").replace("|", "\\|").replace("\n", " ")
            설 = (k.get("desc") or "").replace("|", "\\|").replace("\n", " ")
            w(f"| {조건[:2]} | **{k.get('name', '')}** | {판 if 판 >= 0 else '—'} |"
              f" {설[:80]} | 「{인[:110]}」 |")

    # ── 4. 접힘 표지 ──────────────────────────────────────────────
    w("\n## 4. 접힘 표지 — 판독물이 지목한 것\n")
    w("| 표지 | " + " | ".join(NAME[m] for m in ORD) + " |")
    w("|---|" + "---|" * len(ORD))
    모두 = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in 원장:
        for mk in r.get("fold_markers") or []:
            모두[mk.get("marker", "")][r["model"]].append(
                (r["cond"], mk.get("count", -1)))
    for 표지 in sorted(모두, key=lambda t: -sum(len(v) for v in 모두[t].values())):
        칸 = []
        for m in ORD:
            v = 모두[표지].get(m) or []
            센것 = [f"{c[0][:2]}:{c[1]}" for c in v if c[1] >= 0]
            칸.append(f"{len(v)}조각" + (f" ({', '.join(센것)})" if 센것 else "") if v else "—")
        w(f"| `{표지}` | " + " | ".join(칸) + " |")

    # ── 5. 세는 말 전부 ───────────────────────────────────────────
    w("\n## 5. 세는 말 — 판독물 안의 모든 수치\n")
    총 = sum(len(r.get("counts") or []) for r in 원장)
    w(f"{총}건. 조각 안의 몫이다 — 모델 사이로 더하지 마라.\n")
    for m in ORD:
        w(f"\n### {NAME[m]}\n")
        w("| 조각 | 무엇을 | k/n | 판독물 원문 |")
        w("|---|---|---:|---|")
        for r in [x for x in 원장 if x["model"] == m]:
            for c in r.get("counts") or []:
                인 = (c.get("quote") or "").replace("|", "\\|").replace("\n", " ")
                w(f"| {r['cond'][:2]} | {c.get('item', '')[:44]} | {kn(c)} | 「{인[:120]}」 |")

    # ── 6. 한 줄씩 ────────────────────────────────────────────────
    w("\n## 6. 판독물이 꼽은 것 한 줄씩\n")
    for m in ORD:
        w(f"\n**{NAME[m]}**\n")
        for r in [x for x in 원장 if x["model"] == m]:
            w(f"- {r['cond']} — {(r.get('headline') or '').strip()}")

    (H / "READS_TABLE.md").write_text("\n".join(W) + "\n", encoding="utf-8")
    (H / "READS_LEDGER.json").write_text(json.dumps(dict(
        판독물수=len(원장),
        에이전트대조=dict(맞음=raw.get("clean", 0), 전체=raw.get("got", 0),
                    어긋남=raw.get("dirty") or []),
        자가인용대조=dict(맞음=맞은인용, 전체=총인용,
                    못찾음=[dict(file=rec["file"], 자리=자리, 인용=q)
                          for rec, 자리, q in 안맞음]),
        원장=원장,
    ), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ READS_TABLE.md · READS_LEDGER.json 썼다.")
    print(f"  판독물 {len(원장)} · 세는 말 {총}건 · "
          f"자가 인용 대조 {맞은인용}/{총인용}")


if __name__ == "__main__":
    main()
