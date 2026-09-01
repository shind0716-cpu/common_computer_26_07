"""[공용 코어 · 압박×카테고리] 팩 「손」 — 수첩을 쓴 손이 몇인지 묶는 블라인드 팩 (콜 0).

## 무엇을 묻나

수첩 아홉 편을 주고 **같은 손이 쓴 것끼리 묶으라**고 한다. 모델 이름은 주지 않는다.
세 묶음 셋씩이라는 것만 알려 준다. 채점은 열쇠를 연 뒤에 한다.

  ① 아홉을 세 묶음으로 나눈다 (묶음마다 셋)
  ② 묶음마다 그 손의 버릇을 한 줄로 적는다  ← 이쪽이 이 팩의 진짜 소득이다
  ③ 어느 묶음이 가장 갈라내기 쉬웠는지, 그 단서가 무엇이었는지 적는다

## 왜 한 재료 안에서만 묻나

여러 재료를 섞으면 코더가 **화제로 묶는다.** 「어린이집 얘기끼리, 병원 얘기끼리」로
묶으면 손에 대해 아무것도 안 나온다. 한 재료 안에서 아홉 편을 주면 **사안·사실·
가치문이 전부 같으므로 남는 변수가 손뿐**이다.

## 무엇을 가리나

  가린다     모델 이름 · 반복 번호 · run_id · 파일 경로
  안 가린다  사안문 · 수첩 원문 그대로 — 가리면 물음이 성립하지 않는다

수첩 안에 모델 이름이 나오는 일은 없지만 검사한다.

## 우연히 맞을 확률

아홉을 셋씩 세 묶음으로 나누는 방법이 280가지라 통째로 맞을 확률은 0.36% 다.
그러나 부분 점수가 필요하므로 **짝 단위**로 잰다 — 서른여섯 짝마다 「같은 손인가」를
코더의 묶음과 열쇠가 같게 답했는지 센다. 이 자의 우연 기댓값은 **62.5%** 다
(같은 손 짝이 36 중 9 = 25% 이고 코더도 25% 비율로 묶으므로 0.25² + 0.75²).

## 길이가 답을 흘린다 — 그래서 두 벌로 낸다

팩을 짓고 재 보니 **길이 순으로 정렬해 셋씩 끊기만 해도 짝 78~100% 가 맞는다**
(우연 62.5%). 원문만 내면 「갈라진다」가 자동으로 통과하고, 정작 알고 싶은
「무엇으로 알아보는가」는 안 나온다. 그래서 같은 열쇠로 두 벌을 낸다.

  **전문** 수첩 원문 그대로. 판정선은 우연이 아니라 **그 묶음의 길이 기준선**이다
          (열쇠에 적어 둔다). 길이보다 잘해야 무언가를 읽은 것이다.
  **토막** 그 묶음에서 가장 짧은 수첩의 길이로 전부 자른 것. 길이 단서가 없으므로
          판정선이 우연 62.5% 다. 잘린 것은 **글머리**만 남으므로 문단 짜는 버릇을 본다.

두 벌의 차가 곧 「길이 말고 무엇이 있었나」다. 토막이 우연 언저리면
**모델 버릇은 길이뿐**이라는 뜻이고, 그것도 답이다.

사용: PYTHONUTF8=1 python build_pack_hand.py [--issues 3]
산출: coderpacks_hand/PACK_H_hand_<날짜>.md · _KEY_H_<날짜>.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
SEED = 20260902
MODELS = ["claude-haiku", "gemini-flash", "gpt"]
OUTDIR = HERE / "coderpacks_hand"

GUIDE = """> 안내: 아래 묶음마다 **수첩 아홉 편**이 있습니다. 같은 사안을 놓고 쓴 것이라
> 사안문·사실·가치문은 아홉 편이 전부 같습니다. 다른 것은 **누가 썼는가**뿐입니다.
>
> 아홉 편은 **세 손**이 세 편씩 쓴 것입니다. 누구인지는 알려 드리지 않습니다.
>
> **① 아홉을 세 묶음으로 나눠 주세요.** 묶음마다 정확히 셋입니다.
> **② 묶음마다 그 손의 버릇을 한 줄로 적어 주세요.** 무엇을 보고 그렇게 묶었는지.
> **③ 어느 묶음이 가장 갈라내기 쉬웠습니까? 단서가 무엇이었습니까?**
>
> 길이나 문단 모양 같은 겉모습도 단서로 써도 됩니다 — 다만 **그것만으로 묶었다면
> 그렇게 적어 주세요.** 겉모습 말고 무엇이 달랐는지가 이 물음의 핵심입니다.
> 묶음에 이름을 붙이지 마시고 「묶음 1·2·3」으로만 부르세요."""


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


def collect(mats: dict) -> dict:
    """재료 → 모델 → 반복 → 마지막 수첩. 신념 세트 · 압박 없음만."""
    out = {}
    for p in (HERE / "runs").glob("*/*/run_C0_wonchik_*.json"):
        if "_dry" in p.parts or "_stale" in str(p) or "partial" in p.name:
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        m, iid = p.parts[-3], d["issue_id"]
        if m not in MODELS or iid not in mats:
            continue
        notes = d.get("notes") or []
        if not notes:
            continue
        out.setdefault(iid, {}).setdefault(m, {})[int(p.stem[-1])] = {
            "note": notes[-1], "run_id": d.get("run_id"), "final": d.get("final_poll", "").strip(),
            "materials_hash": d.get("materials_hash"),
        }
    return {i: v for i, v in out.items()
            if len(v) == 3 and all(len(r) == 3 for r in v.values())}


def length_baseline(items: list) -> dict:
    """길이 순으로 정렬해 셋씩 끊었을 때 짝 몇을 맞히나 — 전문 벌의 판정선."""
    srt = sorted(items, key=lambda x: len(x["note"]))
    g = {}
    for gi in range(3):
        for it in srt[gi * 3:gi * 3 + 3]:
            g[it["item"]] = gi
    truth = {it["item"]: it["model"] for it in items}
    ks = sorted(truth)
    ok = sum(1 for i in range(9) for j in range(i + 1, 9)
             if (g[ks[i]] == g[ks[j]]) == (truth[ks[i]] == truth[ks[j]]))
    return {"pairs_correct": ok, "pairs_total": 36, "pct": round(100 * ok / 36, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issues", type=int, default=3, help="묶음 수(재료 수)")
    a = ap.parse_args()

    mats = materials()
    pool = collect(mats)
    if len(pool) < a.issues:
        print(f"[즉사] 세 모델 × 반복 셋이 다 있는 재료가 {len(pool)}벌뿐이다")
        return 1

    rng = random.Random(SEED)
    # 손이 갈리는지 보려면 무대가 치우치면 안 된다 — 재료는 씨앗 고정으로 뽑는다
    chosen = sorted(rng.sample(sorted(pool), a.issues))
    today = datetime.now(KST).strftime("%Y-%m-%d")
    OUTDIR.mkdir(exist_ok=True)

    L = [f"# 팩 「손」 (전문) — 수첩 아홉 편을 세 손으로 묶기 ({today})", "", GUIDE, ""]
    LT = [f"# 팩 「손」 (토막) — 수첩 아홉 편을 세 손으로 묶기 ({today})", "",
          "> 이 벌은 수첩을 **묶음마다 같은 길이로 잘랐습니다.** 길이가 단서가 되지",
          "> 않게 하려는 것이고, 잘린 뒷부분은 없는 셈 치고 봐 주세요.", "", GUIDE, ""]
    key = {"pack": "PACK_H", "seed": SEED, "created_at": datetime.now(KST).isoformat(timespec="seconds"),
           "chance_pair_accuracy": 0.625,
           "note": "판독 전에는 열지 않는다. 채점은 짝 단위(36짝)로 한다. "
                   "전문 벌의 판정선은 우연이 아니라 length_baseline 이다.",
           "bundles": []}

    for bi, iid in enumerate(chosen, 1):
        items = [{"model": m, "rep": r, **pool[iid][m][r]} for m in MODELS for r in (1, 2, 3)]
        rng.shuffle(items)
        for i, it in enumerate(items, 1):
            it["item"] = f"H{bi}-{i}"
        head = [f"## 묶음 {bi}", "",
                f"**사안** — {mats[iid]['stub']}", "",
                f"**선택지** — {mats[iid]['options'][0]} · {mats[iid]['options'][1]}", ""]
        L += head
        cut = min(len(it["note"]) for it in items)
        LT += head
        for it in items:
            L += [f"### {it['item']}", "", it["note"], "",
                  f"*최종 선택 — {it['final']}*", ""]
            LT += [f"### {it['item']}", "", it["note"][:cut], "",
                   f"*최종 선택 — {it['final']}*", ""]
        key["bundles"].append({
            "bundle": bi, "issue_id": iid,
            "materials_hash": items[0]["materials_hash"],
            "truncate_to": cut,
            "length_baseline": length_baseline(items),
            "items": [{k: it[k] for k in ("item", "model", "rep", "run_id")} for it in items],
        })

    pack = OUTDIR / f"PACK_H_hand_{today}.md"
    packt = OUTDIR / f"PACK_H_hand_cut_{today}.md"
    keyf = OUTDIR / f"_KEY_H_{today}.json"
    pack.write_text("\n".join(L), encoding="utf-8")
    packt.write_text("\n".join(LT), encoding="utf-8")
    keyf.write_text(json.dumps(key, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ── 검사
    text = pack.read_text(encoding="utf-8") + packt.read_text(encoding="utf-8")
    bad = []
    for b in key["bundles"]:
        if len(b["items"]) != 9:
            bad.append(f"묶음 {b['bundle']}: 항목 {len(b['items'])} ≠ 9")
        for it in b["items"]:
            if it["run_id"] and it["run_id"] in text:
                bad.append(f"{it['item']}: run_id 누출")
    for tok in MODELS + ["claude", "gemini", "gpt", "haiku", "wonchik", "rep1", "rep2", "rep3"]:
        if tok in text:
            bad.append(f"조건 낱말 누출: {tok}")
    ids = {ln.split()[1] for ln in text.splitlines() if ln.startswith("### H")}
    want = {it["item"] for b in key["bundles"] for it in b["items"]}
    if ids != want:
        bad.append("팩과 열쇠의 항목 id 집합이 다르다")
    # 한 묶음 안에서 재료 지문이 하나여야 한다 — 섞이면 무대가 통제되지 않는다
    for b in key["bundles"]:
        hs = {pool[b["issue_id"]][m][r]["materials_hash"] for m in MODELS for r in (1, 2, 3)}
        if len(hs) != 1:
            bad.append(f"묶음 {b['bundle']}: 재료 지문이 {len(hs)}종")

    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    print(f"팩 {pack.name} · {packt.name} — 묶음 {len(chosen)} · 항목 {len(chosen) * 9} × 2벌")
    print(f"  재료: {', '.join(i.replace('issue_', '') for i in chosen)}")
    print(f"  pack sha256 {sha(pack)}")
    print(f"  cut  sha256 {sha(packt)}")
    for b in key["bundles"]:
        print(f"  묶음 {b['bundle']} {b['issue_id'].replace('issue_', ''):22s} "
              f"길이 기준선 {b['length_baseline']['pct']:5.1f}% · {b['truncate_to']}자로 자름")
    print(f"  key  sha256 {sha(keyf)}")
    print(f"  우연 기댓값(짝 단위) {key['chance_pair_accuracy']:.1%}")
    print("  검사:", "통과" if not bad else bad)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
