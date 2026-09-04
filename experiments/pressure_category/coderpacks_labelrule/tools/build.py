# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 팩 「라벨과 규칙」 생성기. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/build.py

사전고정 `PREREG_labelrule_2026-09-04.md` 그대로다. 씨앗·가릴 것을 바꾸지 마라.

  재료 두 벌 × 갈래 3(라벨보수·라벨진보·원칙) × 압박 2 × 모델 3 × 반복 3 = 108판
  판마다 마지막 수첩 한 장 + 그 사안의 갈래 여섯

가린다: 모델 · 갈래 · 라벨 방향 · 압박 · **준 문장**
보인다: 사안 한 줄 · 선택지 둘 · 갈래 여섯(섞음) · 마지막 수첩

산출: packs/PACK_LR_*.md · _KEY_LR.json · PACK_HASHES.txt
"""
import json
import os
import glob
import random
import hashlib
import pathlib
import collections

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
SEED = 20260904
PER_PACK = 9
재료 = ("issue_examaccom", "issue_parentalreturn")


def 갈래(vs):
    if vs.startswith("lcons"):
        return "라벨보수"
    if vs.startswith("lprog"):
        return "라벨진보"
    if vs.startswith("wonchik"):
        return "원칙"
    return None


def main():
    mats = {}
    for p in glob.glob(str(R / "materials" / "*.json")):
        d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        if d.get("issue_id"):
            mats[d["issue_id"]] = d

    항목 = []
    for p in sorted((R / "runs").glob("*/*/run_*.json")):
        parts = p.parts
        if parts[-2] not in 재료:
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        vs = str(d.get("value_set") or "")
        g = 갈래(vs)
        if not g or len(d.get("notes") or []) < 3:
            continue
        항목.append(dict(경로=str(p.relative_to(R)).replace("\\", "/"),
                        모델=parts[-3], issue=d["issue_id"], 갈래=g,
                        압박=("없음" if d.get("script") == "C0" else "있음"),
                        각본=d.get("script"), 세트=vs, 반복=str(d.get("rep")),
                        최종답=d.get("final_poll"), 수첩=d["notes"][-1]))

    칸 = collections.Counter((x["갈래"], x["압박"], x["모델"]) for x in 항목)
    if len(칸) != 18 or set(칸.values()) != {6}:
        raise SystemExit(f"격자가 안 맞다 — 칸 {len(칸)}개, 크기 {sorted(set(칸.values()))}")

    rng = random.Random(SEED)
    rng.shuffle(항목)
    for i, it in enumerate(항목, 1):
        it["lid"] = f"L-{i:03d}"
        cats = list(mats[it["issue"]]["categories"])
        rng.shuffle(cats)
        it["갈래여섯"] = cats

    (H / "packs").mkdir(exist_ok=True)
    머리 = pathlib.Path(H / "tools" / "head.md").read_text(encoding="utf-8")
    해시 = []
    덩이들 = [항목[i:i + PER_PACK] for i in range(0, len(항목), PER_PACK)]
    for pi, 덩이 in enumerate(덩이들, 1):
        nn = f"{pi:02d}"
        줄 = [머리.replace("{nn}", nn).replace("{n}", str(len(덩이)))]
        for it in 덩이:
            m = mats[it["issue"]]
            줄.append(f"\n## {it['lid']}\n")
            줄.append(f"**사안** — {m['stub']}\n")
            줄.append(f"**선택지** — {m['options'][0]} · {m['options'][1]}\n")
            줄.append(f"**따질 만한 여섯 갈래** — {' · '.join(it['갈래여섯'])}\n")
            줄.append(f"**수첩**\n\n{it['수첩']}\n")
        p = H / "packs" / f"PACK_LR_{nn}.md"
        p.write_text("\n".join(줄), encoding="utf-8")
        해시.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()[:12]}  packs/PACK_LR_{nn}.md")

    (H / "PACK_HASHES.txt").write_text("\n".join(해시) + "\n", encoding="utf-8")
    (H / "_KEY_LR.json").write_text(json.dumps(dict(
        pack="PACK_LR", seed=SEED, 판=len(항목), 칸=len(항목) * 6,
        note="판독 전에는 열지 않는다.",
        items={it["lid"]: {k: v for k, v in it.items() if k not in ("lid", "수첩")}
               for it in 항목}), ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"판 {len(항목)} · 칸 {len(항목)*6} · 팩 {len(덩이들)}개 ({PER_PACK}판씩)")
    for k in sorted(칸):
        print(f"  {k[0]:8s} 압박{k[1]:4s} {k[2]:14s} {칸[k]}판")


if __name__ == "__main__":
    main()
