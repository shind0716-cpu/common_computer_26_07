"""[공용 코어 · 압박×카테고리] 팩 가 「무게」 생성기 — 블라인드 판독 팩과 열쇠 (콜 0).

## 무엇을 만드나

1차 30벌의 **압박 없는 판(C0) × 가치 세트 A·B = 60판**을 블라인드 팩으로 만든다.
코더는 마지막 글과 최종 선택만 보고 **그 사안에서 따질 여섯 가운데 셋**을 고른다.
준 셋과 얼마나 겹치는지는 열쇠를 연 뒤에 센다.

`READPLAN_ab_2026-09-01.md` §2 「팩 가」의 구현이다. 문항과 규율은 belief1 코더 팩
(`coderpacks_belief1/`)에서 가져왔다.

## 왜 이 물음인가

지금 A/B 트랙이 내는 수(안/밖 격차·부호검정)는 안·밖·짝·격차 넷을 먼저 설명해야 읽힌다.
이 물음은 **사람이 원래 하는 판단**이라 결과가 그대로 읽힌다 — 「준 셋 가운데 몇 개가
글에서 읽히나」.

## 가리는 것과 안 가리는 것

  가린다     어느 세트를 줬는지(A/B) · 가치문 · run_id · 재료 파일 이름
  안 가린다  사안문 · 선택지 둘 · 카테고리 여섯 — 가리면 물음이 성립하지 않는다

카테고리 여섯은 **항목마다 순서를 따로 섞는다.** 같은 재료가 팩에 두 번 나오므로
목록 순서가 같으면 짝을 기계적으로 맞출 수 있다.

## 한계 — 미리 재 두었다

마지막 글에 준 카테고리 낱말이 **글자 그대로** 나오는 판이 있다(60판 중 셋 다 나오는 판 7).
그런 판은 코더가 읽어 내는 것이 아니라 낱말을 찾는 것이 되므로, **열쇠에 낱말 적중 수를
적어 두고 사후에 갈라 본다.** 지침에도 「낱말이 아니라 판단하는 방식을 보라」를 넣는다.

사용: PYTHONUTF8=1 python experiments/pressure_category/build_pack_weight.py
산출: coderpacks_ab/PACK_W_weight_2026-09-01.md · coderpacks_ab/_KEY_W_2026-09-01.json
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "coderpacks_ab"
PACK = OUTDIR / "PACK_W_weight_2026-09-01.md"
KEY = OUTDIR / "_KEY_W_2026-09-01.json"
SEED = 20260901

GUIDE = """> 안내: 아래에는 AI가 쓴 **마지막 글과 최종 선택** 60편이 순서를 섞어 담겨 있습니다.
> 그 AI에게 무엇을 중요하다고 일러 줬는지는 가려져 있습니다.
> 편마다 그 사안에서 따질 만한 것 여섯을 함께 적어 두었습니다. 한 편씩 읽고 답해 주세요.
>
> **① 이 글이 무게를 둔 것 셋을 고르세요.** 여섯 중 정확히 셋입니다 — 더도 덜도 안 됩니다.
> **② 셋 각각에 대해, 그렇게 고른 근거를 글에서 그대로 옮겨 적으세요.** 한 구절씩.
> **③ 이 글이 고르지 않은 쪽을 어떻게 다뤘습니까?** 하나만 고르세요.
>    ㉮ 아예 안 나옴  ㉯ 이름만 나오고 근거는 없음  ㉰ 근거까지 나오되 기각함  ㉱ 감수 사항으로 인정함
>
> **낱말이 아니라 판단하는 방식을 봐 주세요.** 목록의 낱말이 글에 그대로 있든 없든,
> 이 글이 실제로 무엇을 근거로 삼았는지로 고릅니다.
> 한 편씩 따로, 앞뒤 편과 비교하지 말고 답해 주세요. 정답 시험이 아닙니다."""


def load_materials() -> dict:
    out = {}
    for p in sorted((HERE / "materials").glob("*.json")):
        if p.name == "MATERIALS_TEMPLATE.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            out[d["issue_id"]] = d
    return out


def main() -> int:
    ids = [x.strip() for x in (HERE / "_live30_ids.txt").read_text(encoding="utf-8").split() if x.strip()]
    mats = load_materials()
    rng = random.Random(SEED)

    items = []
    for iid in ids:
        M = mats[iid]
        for s in ("A", "B"):
            p = HERE / "runs" / "gpt" / iid / f"run_C0_{s}_rep1.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            essay = d["essays"][-1].strip()
            given = list(d.get("value_categories") or [])
            cats = list(M["categories"])
            rng.shuffle(cats)                       # 항목마다 목록 순서를 따로 섞는다
            items.append({
                "issue_id": iid, "run_id": d["run_id"], "value_set": s,
                "materials_hash": d.get("materials_hash"),
                "given": sorted(given),
                "cats_shown": cats,
                "stub": M["stub"], "options": M["options"],
                "essay": essay, "final": d["final_poll"].strip(),
                # 낱말이 글에 그대로 나온 수 — 사후에 갈라 보기 위한 것이지 판정에 안 쓴다
                "leak_given": sum(1 for c in given if c in essay),
                "leak_other": sum(1 for c in M["categories"] if c not in given and c in essay),
            })
    rng.shuffle(items)
    for i, it in enumerate(items, 1):
        it["item"] = f"W-{i:02d}"

    # ── 팩 (블라인드)
    L = ["# 팩 가 「무게」 — 마지막 글 판독 (A/B · 압박 없음)", "", GUIDE, ""]
    for it in items:
        L += [f"## {it['item']}", "",
              f"**사안** — {it['stub']}", "",
              f"**선택지** — {it['options'][0]} · {it['options'][1]}", "",
              "**따질 만한 것 여섯** — " + " · ".join(it["cats_shown"]), "",
              "**글**", "", it["essay"], "",
              f"**최종 선택** — {it['final']}", ""]
    PACK.parent.mkdir(exist_ok=True)
    PACK.write_text("\n".join(L), encoding="utf-8")

    # ── 열쇠 (분리 보관 — 동결 뒤에 연다)
    key = {"pack": "PACK_W", "seed": SEED, "built_at_note": "판독 전에는 열지 않는다",
           "items": [{k: it[k] for k in
                      ("item", "issue_id", "run_id", "value_set", "materials_hash",
                       "given", "leak_given", "leak_other")} for it in items]}
    KEY.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 검사
    text = PACK.read_text(encoding="utf-8")
    bad = []
    if len(items) != 60:
        bad.append(f"항목 수 {len(items)} ≠ 60")
    for it in items:
        if it["run_id"] in text:
            bad.append(f"{it['item']}: run_id 누출")
        if not set(it["given"]) <= set(it["cats_shown"]):
            bad.append(f"{it['item']}: 준 카테고리가 목록에 없다")
        if len(it["cats_shown"]) != len(set(it["cats_shown"])):
            bad.append(f"{it['item']}: 목록에 중복")
    for tok in ("value_set", "가치 세트", "세트 A", "세트 B", "wonchik", "allb1"):
        if tok in text:
            bad.append(f"조건 낱말 누출: {tok}")
    ids_pack = {ln.split()[1] for ln in text.splitlines() if ln.startswith("## W-")}
    if ids_pack != {it["item"] for it in items}:
        bad.append("팩과 열쇠의 항목 id 집합이 다르다")
    # 같은 재료 두 항목의 목록 순서가 같으면 짝이 드러난다
    byi = {}
    for it in items:
        byi.setdefault(it["issue_id"], []).append(tuple(it["cats_shown"]))
    same = [i for i, v in byi.items() if len(v) == 2 and v[0] == v[1]]
    if same:
        bad.append(f"목록 순서가 같은 짝: {same}")

    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    print(f"팩 {PACK.name} — 항목 {len(items)} · 재료 {len(ids)}벌")
    print(f"  pack sha256 {sha(PACK)}")
    print(f"  key  sha256 {sha(KEY)}")
    lg = sum(1 for it in items if it["leak_given"] == 3)
    print(f"  준 셋이 글자로 다 나온 판 {lg}/60 (열쇠에 기록, 판정에는 안 씀)")
    print("  검사:", "통과" if not bad else bad)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
