# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 원칙 판 gpt·제미나이 132판 팩 — 대칭축 채우기. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python build.py

## 왜

민옥 9/3 정성 판독 §7 한계에 이렇게 적혀 있다 —

    원칙 조건은 gpt·gemini 에 채점 줄이 없어 판독자 관찰만 있다.

하이쿠 원칙 66판은 정독으로 채점돼 마지막 수첩 3.3 이 나와 있는데,
gpt·제미나이는 그 칸이 비어 있다. **세 모델 대칭축이 안 선다.**

여기서 그 132판(gpt 66 + 제미나이 66)을 민옥 판독기 형식으로 짓는다.

## 형식은 민옥 것 그대로

`coderpacks_label_models_20260903/PROTOCOL.md` 와 팩 구조를 그대로 쓴다.
항목마다 options·stub·facts(12)·essays(4)·notes(3)·final_answer.

## 원칙 판이라 다른 것 하나

**`aligned` 가 없다.** 원칙 문장은 시나리오 카테고리를 안 집으므로 정렬 답이 안 선다.
그래서 편식은 `own`(정렬 답) 기준으로 못 재고 **`final`(마지막 답) 기준**으로만 잰다 —
민옥 채점기의 `pro_final`·`con_final` 칸이 그것이고, 하이쿠 원칙도 같은 방식으로 쟀다.

산출: packs/kpackNN.json · KEY.json · MATERIALS.json
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
모델 = ("gpt", "gemini-flash")


def main():
    mats = {}
    for p in glob.glob(str(R / "materials" / "*.json")):
        d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        if d.get("issue_id"):
            mats[d["issue_id"]] = d

    항목 = []
    for m in 모델:
        for p in sorted((R / "runs" / m).glob("*/run_*.json")):
            if "_stale" in str(p):
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            if not str(d.get("value_set") or "").startswith("wonchik"):
                continue
            if len(d.get("notes") or []) < 3 or len(d.get("essays") or []) < 4:
                continue
            if d["issue_id"] not in mats:
                continue
            항목.append((m, p, d))

    칸 = collections.Counter((m, "C0" if d.get("script") == "C0" else "압박")
                            for m, _, d in 항목)
    if len(항목) != 132 or set(칸.values()) != {33}:
        raise SystemExit(f"격자가 안 맞다 — 판 {len(항목)}, 칸 {dict(칸)}")

    rng = random.Random(SEED)
    항목.sort(key=lambda t: (t[0], str(t[1])))
    rng.shuffle(항목)   # 모델·조건을 섞어 코더가 눈치 못 채게

    (H / "packs").mkdir(exist_ok=True)
    key = []
    덩이들 = [항목[i:i + PER] for i in range(0, len(항목), PER)]
    for pi, 덩이 in enumerate(덩이들, 1):
        nn = f"{pi:02d}"
        묶 = []
        for j, (m, p, d) in enumerate(덩이, 1):
            iid = f"kpack{nn}-{j}"
            mm = mats[d["issue_id"]]
            묶.append(dict(item=iid, options=mm["options"], stub=mm["stub"],
                          facts=[dict(id=f["id"], text=f["text"]) for f in mm["facts"]],
                          essays=d["essays"][:4], notes=d["notes"][:3],
                          final_answer=d.get("final_poll")))
            key.append(dict(item=iid, model=m, issue_id=d["issue_id"],
                            run_id=d.get("run_id"), value_set=d["value_set"],
                            script=d["script"],
                            압박=("C0" if d.get("script") == "C0" else "압박"),
                            경로=str(p.relative_to(R)).replace("\\", "/")))
        (H / "packs" / f"kpack{nn}.json").write_text(
            json.dumps(묶, ensure_ascii=False, indent=1), encoding="utf-8")

    (H / "KEY.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    쓴재료 = sorted({d["issue_id"] for _, _, d in 항목})
    (H / "MATERIALS.json").write_text(json.dumps(
        {k: mats[k] for k in 쓴재료}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"판 {len(항목)} · 칸 {len(항목)*36} · 팩 {len(덩이들)}개 ({PER}판씩) · 재료 {len(쓴재료)}벌")
    for k in sorted(칸):
        print(f"  {k[0]:14s} {k[1]:5s} {칸[k]}판")


if __name__ == "__main__":
    main()
