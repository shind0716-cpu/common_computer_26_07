# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 관찰용 소배치 팩 — 원칙+항목 24판. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python build.py

## 무엇인가

오늘 돌린 파일럿(원칙 여섯 + 항목 셋, 132판)을 **민옥 판독기로** 읽히려고 짓는다.
지금 파일럿 수치(마지막 수첩 3.56·4.77)는 **기계 표식**이라 민옥의 사람 판독 수치
(가치 8.8 · 라벨 8.1 · 원칙 3.3 …)와 눈금이 달라 나란히 못 놓는다.

**파일럿이므로 관찰용 소배치다.** 판정선도 사전고정도 없다.
- 24판 = 재료 6벌 × 압박 2(C0·C2) × 세트 2(A짝·B짝) × 반복 1
- 재료 6벌은 11벌에서 씨앗 20260904 로 뽑는다
- 코더 하나. **이중 판독을 안 하므로 신뢰도 수치를 못 낸다** — 관찰까지다

## 형식은 민옥 것 그대로

`coderpacks_label_models_20260903/PROTOCOL.md` 와 팩 구조를 그대로 쓴다.
항목마다 options·stub·facts(12)·essays(4)·notes(3)·final_answer.
**사실 12개를 실어 준다** — 이게 민옥 판독기의 핵심이고, 갈래만 주는 뜻 팩과 다른 점이다.

산출: packs/wpackNN.json · KEY.json · MATERIALS.json
"""
import json
import os
import glob
import random
import pathlib
import collections

H = pathlib.Path(__file__).resolve().parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
SEED = 20260904
PER = 6


def main():
    mats = {}
    for p in glob.glob(str(R / "materials" / "*.json")):
        d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        if d.get("issue_id"):
            mats[d["issue_id"]] = d

    격자 = sorted({json.loads(pathlib.Path(p).read_text(encoding="utf-8"))["materials"]
                  for p in glob.glob(str(R / "values" / "wonchik_*.json"))})
    rng = random.Random(SEED)
    뽑은벌 = sorted(rng.sample(격자, 6))

    항목 = []
    for p in sorted((R / "runs" / "gpt").glob("*/run_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        vs = str(d.get("value_set") or "")
        if not vs.startswith(("wonval_", "wonvalb_")):
            continue
        if d["issue_id"] not in 뽑은벌 or str(d.get("rep")) != "1":
            continue
        if len(d.get("notes") or []) < 3 or len(d.get("essays") or []) < 4:
            continue
        항목.append((p, d))

    칸 = collections.Counter((d["issue_id"], d["script"],
                             "A짝" if str(d["value_set"]).startswith("wonval_") else "B짝")
                            for _, d in 항목)
    if len(항목) != 24 or set(칸.values()) != {1}:
        raise SystemExit(f"격자가 안 맞다 — 판 {len(항목)}, 칸 {len(칸)}")

    항목.sort(key=lambda t: str(t[0]))
    rng.shuffle(항목)

    (H / "packs").mkdir(exist_ok=True)
    key = []
    덩이들 = [항목[i:i + PER] for i in range(0, len(항목), PER)]
    for pi, 덩이 in enumerate(덩이들, 1):
        nn = f"{pi:02d}"
        묶 = []
        for j, (p, d) in enumerate(덩이, 1):
            iid = f"wpack{nn}-{j}"
            m = mats[d["issue_id"]]
            묶.append(dict(item=iid, options=m["options"], stub=m["stub"],
                          facts=[dict(id=f["id"], text=f["text"]) for f in m["facts"]],
                          essays=d["essays"][:4], notes=d["notes"][:3],
                          final_answer=d.get("final_poll")))
            key.append(dict(item=iid, model="gpt", issue_id=d["issue_id"],
                            run_id=d["run_id"], value_set=d["value_set"],
                            script=d["script"], aligned=d.get("aligned"),
                            짝=("A짝" if str(d["value_set"]).startswith("wonval_") else "B짝"),
                            경로=str(p.relative_to(R)).replace("\\", "/")))
        (H / "packs" / f"wpack{nn}.json").write_text(
            json.dumps(묶, ensure_ascii=False, indent=1), encoding="utf-8")

    (H / "KEY.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    (H / "MATERIALS.json").write_text(json.dumps(
        {k: mats[k] for k in 뽑은벌}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"재료 {len(뽑은벌)}벌 (씨앗 {SEED}) — {', '.join(x.replace('issue_', '') for x in 뽑은벌)}")
    print(f"판 {len(항목)} · 칸 {len(항목)*36} · 팩 {len(덩이들)}개 ({PER}판씩)")
    c2 = collections.Counter((d["script"], "A짝" if str(d["value_set"]).startswith("wonval_") else "B짝")
                             for _, d in 항목)
    for k in sorted(c2):
        print(f"  {k[0]} {k[1]} {c2[k]}판")


if __name__ == "__main__":
    main()
