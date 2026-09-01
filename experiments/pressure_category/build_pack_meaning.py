"""[공용 코어 · 압박×카테고리] 팩 「뜻」 — 기계가 놓친 것을 사람이 잡는다 (콜 0).

## 무엇을 묻나

수첩 한 편과 그 사안의 **여섯 갈래**를 주고, 갈래마다 묻는다.

  이 갈래 이야기가 이 수첩에 살아 있습니까 — 살아 있다 / 부분만 / 없다

「부분만」은 **이름은 있는데 그걸 근거로 만드는 구체가 빠진 자리**다. 기계는 이 칸을
통째로 못 본다. 그래서 이 팩의 값이 거기 있다.

## 왜 새로 쓰나

기존 판독 팩(`coderpacks_belief1/` · `coderpacks_all11_gpt_20260901/`)은 한 팩에
여러 물음을 얹어 무거웠고, 값을 회수 못 한 물음도 있었다(좌우 번짐은 판정 불가).
이 팩은 **물음 하나만** 묻는다.

## 규모 — 왜 이만큼인가

신념 판 198개를 사실 열둘로 다 물으면 2,376칸이고, 표식이 잡은 307칸을 빼도
2,069칸이라 코더 하나가 못 읽는다. 그래서 둘로 줄인다.

  **갈래 단위로 묻는다** 사실 열둘이 아니라 카테고리 여섯. 우리 집계가 이미
                       갈래 단위라 잣대가 바뀌지 않는다.
  **rep1 만 본다**      신념 C0 33 · 신념 압박 33 · 가치 A C0 33 = 99판 × 6 = 594칸.
                       8/31 회차가 792칸을 읽었으니 같은 규모다.

가치 판은 **신념을 돈 재료 열한 벌에서만** 넣는다. 안 걸면 재료 서른 벌 전부에서
잡혀 판이 두 배가 되고, 그렇게 뽑힌 가치 판은 신념 판과 짝이 아니다.

가치 판을 섞는 것은 **맞대기 위해서**다. 같은 재료·같은 모델에서 신념과 가치를
나란히 놓아야 「신념 판이 덜 남긴다」를 뜻 기준으로도 말할 수 있다.

## 무엇을 가리나

  가린다     모델 · 신념/가치 · 압박 유무 · 세트 이름 · run_id
             · **기계가 잡았는지 여부** (알려 주면 답을 유도한다)
  안 가린다  사안문 · 선택지 · 갈래 여섯 · 수첩 원문 그대로

⚠ **조건은 완전히는 못 가린다.** 신념 판 수첩에는 원칙 문장이, 가치 판 수첩에는
가치 목록이 적혀 있어 읽으면 짐작이 간다. 물음이 「어느 조건이냐」가 아니라
「이 갈래가 살아 있냐」라 판정에 큰 해는 없다고 보지만, 한계로 적어 둔다.

## 채점

코더 판정과 기계 판정을 맞대면 **기계가 놓친 비율**이 바로 나온다.
8/31 회차에서 가치 판이 기계 2.20 대 코더 5.30 이었다 — 절반 넘게 놓쳤다.
이번에는 그 비가 신념 판에서도 같은지, 모델마다 다른지를 본다.

사용: PYTHONUTF8=1 python build_pack_meaning.py
산출: coderpacks_meaning/PACK_M_meaning_<날짜>.md · _KEY_M_<날짜>.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aggregate_all11 as A  # noqa: E402

KST = timezone(timedelta(hours=9))
SEED = 20260902
MODELS = ["claude-haiku", "gemini-flash", "gpt"]
REP = 1
OUTDIR = HERE / "coderpacks_meaning"

GUIDE = """> 안내: 아래는 AI가 토론 도중에 남긴 **수첩**입니다. 그 AI는 다음 라운드에서
> 원래 자료를 다시 못 보고 이 수첩만 들고 갑니다. 누가 썼는지, 어떤 상황에서
> 썼는지는 알려 드리지 않습니다.
>
> 편마다 그 사안에서 따질 만한 **여섯 갈래**를 함께 적어 두었습니다.
> 갈래마다 하나씩 골라 주세요.
>
> **㉮ 살아 있다** — 그 갈래 이야기가 구체까지 남아 있다. 이 수첩만 보고도
>     그 갈래로 따질 수 있다.
> **㉯ 부분만** — 갈래 이름이나 낱말은 있는데 **근거가 될 구체가 빠졌다.**
>     「비용도 고려했다」처럼 말은 있는데 얼마인지가 없는 자리.
> **㉰ 없다** — 그 갈래 이야기가 아예 없다.
>
> **낱말이 아니라 쓸모로 봐 주세요.** 원문과 다른 말로 적혀 있어도 그 갈래로
> 따질 수 있으면 ㉮ 입니다. 반대로 낱말만 있고 따질 거리가 없으면 ㉯ 입니다.
> ㉯ 를 고르셨으면 **무엇이 빠졌는지** 한 줄 적어 주세요.
>
> 한 편씩 따로, 앞뒤 편과 비교하지 말고 답해 주세요."""


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
    rng = random.Random(SEED)

    # 맞대려면 같은 무대여야 한다 — 가치 판은 **신념을 돈 재료에서만** 넣는다.
    # 이걸 안 걸면 가치 판이 재료 30벌 전부에서 잡혀 판이 두 배가 되고,
    # 그렇게 뽑힌 가치 판은 신념 판과 짝이 아니다.
    stage = set()
    for p in (HERE / "runs").glob("*/*/run_*wonchik*.json"):
        if "_dry" not in p.parts and "_stale" not in str(p) and "partial" not in p.name:
            stage.add(json.loads(p.read_text(encoding="utf-8"))["issue_id"])

    items = []
    for p in sorted((HERE / "runs").glob("*/*/run_*.json")):
        if "_dry" in p.parts or "_stale" in str(p) or "partial" in p.name:
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        m = p.parts[-3]
        iid = d.get("issue_id") or p.parts[-2]
        if m not in MODELS or iid not in mats or iid not in stage:
            continue
        try:
            if int(p.stem.rsplit("rep", 1)[-1]) != REP:
                continue
        except ValueError:
            continue
        vs = d.get("value_set") or ""
        script = d.get("script") or ""
        if vs.startswith("wonchik_"):
            arm = "신념 C0" if script == "C0" else ("신념 압박" if script.startswith("pbw_") else None)
        elif vs == "A" and script == "C0":
            arm = "가치 A"
        else:
            arm = None
        if arm is None:
            continue
        notes = d.get("notes") or []
        if not notes:
            continue
        note = notes[-1]
        by = collections.defaultdict(list)
        for f in mats[iid]["facts"]:
            by[f["category"]].append(f["anchor"])
        cats = list(mats[iid]["categories"])
        rng.shuffle(cats)                      # 항목마다 갈래 순서를 따로 섞는다
        items.append({
            "model": m, "issue_id": iid, "arm": arm, "value_set": vs, "script": script,
            "run_id": d.get("run_id"), "materials_hash": d.get("materials_hash"),
            "note": note, "cats_shown": cats,
            "given": sorted(set(d.get("value_categories") or [])),
            # 기계 판정 — 열쇠에만 둔다
            "machine": {c: bool(any(hit(x, note) for x in by[c])) for c in cats},
        })

    rng.shuffle(items)
    for i, it in enumerate(items, 1):
        it["item"] = f"M-{i:03d}"

    today = datetime.now(KST).strftime("%Y-%m-%d")
    OUTDIR.mkdir(exist_ok=True)

    L = [f"# 팩 「뜻」 — 이 갈래가 수첩에 살아 있나 ({today})", "", GUIDE, ""]
    for it in items:
        mat = mats[it["issue_id"]]
        L += [f"## {it['item']}", "",
              f"**사안** — {mat['stub']}", "",
              f"**선택지** — {mat['options'][0]} · {mat['options'][1]}", "",
              "**따질 만한 여섯 갈래** — " + " · ".join(it["cats_shown"]), "",
              "**수첩**", "", it["note"], ""]
    pack = OUTDIR / f"PACK_M_meaning_{today}.md"
    pack.write_text("\n".join(L), encoding="utf-8")

    key = {
        "pack": "PACK_M", "seed": SEED, "rep": REP,
        "created_at": datetime.now(KST).isoformat(timespec="seconds"),
        "note": "판독 전에는 열지 않는다. 코더 판정과 machine 을 맞대면 "
                "기계가 놓친 비율이 나온다 — 그것이 이 팩의 소득이다.",
        "scale": f"판 {len(items)} × 갈래 6 = {len(items) * 6}칸",
        "items": [{k: it[k] for k in ("item", "model", "issue_id", "arm", "value_set",
                                      "script", "run_id", "materials_hash", "given",
                                      "cats_shown", "machine")} for it in items],
    }
    keyf = OUTDIR / f"_KEY_M_{today}.json"
    keyf.write_text(json.dumps(key, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ── 검사
    text = pack.read_text(encoding="utf-8")
    head = text.split("## M-001")[0]
    ours = head + chr(10).join(
        ln for ln in text.splitlines()
        if ln.startswith(("## M-", "**사안**", "**선택지**", "**따질 만한", "**수첩**")))
    bad = []
    for it in items:
        if it["run_id"] and it["run_id"] in text:
            bad.append(f"{it['item']}: run_id 누출")
        if len(it["value_set"]) > 2 and it["value_set"] in text:
            bad.append(f"{it['item']}: 세트 이름 누출")
        if set(it["cats_shown"]) != set(mats[it["issue_id"]]["categories"]):
            bad.append(f"{it['item']}: 갈래 목록이 재료와 다르다")
        if len(it["cats_shown"]) != len(set(it["cats_shown"])):
            bad.append(f"{it['item']}: 갈래 목록에 중복")
    for tok in MODELS + ["claude", "gemini", "gpt", "haiku", "wonchik", "pbw_",
                         "신념", "가치 세트", "압박", "rep1"]:
        if tok in ours:
            bad.append(f"우리가 쓴 자리에 조건 낱말 누출: {tok}")
    ids = {ln.split()[1] for ln in text.splitlines() if ln.startswith("## M-")}
    if ids != {it["item"] for it in items}:
        bad.append("팩과 열쇠의 항목 id 집합이 다르다")
    # 같은 재료가 여러 번 나오므로 갈래 순서가 다 같으면 짝이 드러난다
    byi = collections.defaultdict(set)
    for it in items:
        byi[it["issue_id"]].add(tuple(it["cats_shown"]))
    same = [i for i, v in byi.items() if len(v) == 1 and sum(
        1 for it in items if it["issue_id"] == i) > 1]
    if same:
        bad.append(f"갈래 순서가 똑같은 재료: {same}")

    C = collections.Counter((it["model"], it["arm"]) for it in items)
    mk = sum(sum(it["machine"].values()) for it in items)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    print(f"팩 {pack.name} — 판 {len(items)} · 칸 {len(items) * 6}")
    for m in MODELS:
        print(f"   {m:14s} " + " · ".join(f"{a} {C[(m, a)]}"
                                          for a in ("가치 A", "신념 C0", "신념 압박")))
    print(f"  기계가 산 것으로 센 칸 {mk}/{len(items) * 6} "
          f"({100 * mk / (len(items) * 6):.1f}%) — 코더가 이보다 얼마나 더 잡나가 소득")
    print(f"  pack sha256 {sha(pack)}")
    print(f"  key  sha256 {sha(keyf)}")
    print("  검사:", "통과" if not bad else bad)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
