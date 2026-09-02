# -*- coding: utf-8 -*-
"""「변형」 점검 팩을 짓는다 — 팩2가 「있음」이라 한 칸이 원문과 같은 뜻인가. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/build_variant_pack.py

사전고정 「정정 3」 그대로다. 층·몫·씨앗을 바꾸지 마라 — 바꾸면 사전고정이 아니게 된다.
산출: variant/PACK_V_01..04.md (20칸씩) · variant/_SAMPLE.json (뽑은 칸 목록 · 열쇠)
"""
import json, glob, os, random, collections, pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
R = os.environ.get("PC_ROOT", str(HERE.parent))

SEED = 20260902
QUOTA = {("가치", "안", "첫"): 16, ("가치", "밖", "첫"): 16,
         ("가치", "안", "마지막"): 12, ("가치", "밖", "마지막"): 12,
         ("신념", "전체", "첫"): 12, ("신념", "전체", "마지막"): 12}
PER_PACK = 20

key = json.loads((HERE / "_KEY_2026-09-02.json").read_text(encoding="utf-8"))
M = json.loads((HERE / "_COLLECTED_meaning2.json").read_text(encoding="utf-8"))
mats = {}
for p in glob.glob(f"{R}/materials/*.json"):
    d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    if d.get("issue_id"): mats[d["issue_id"]] = d

# ── 모집단 : 팩2가 「있음」이라 한 칸 전부
pool = collections.defaultdict(list)
for pid, k in key.items():
    cats = set(k.get("value_categories") or [])
    arm = "가치" if k["arm"] == "value" else "신념"
    run = json.loads(pathlib.Path(
        f"{R}/runs/gpt/{k['issue_id']}/{k['file']}").read_text(encoding="utf-8"))
    for j, f in enumerate(mats[k["issue_id"]]["facts"]):
        side = ("안" if f["category"] in cats else "밖") if arm == "가치" else "전체"
        for col, stage in ((0, "첫"), (1, "마지막")):
            if M[pid][j][col] != "있음":
                continue
            pool[(arm, side, stage)].append(dict(
                pid=pid, j=j, col=col, arm=arm, side=side, stage=stage,
                issue=k["issue_id"], fact_id=f["id"], fact=f["text"],
                note=run["notes"][0 if col == 0 else -1]))

rng = random.Random(SEED)
sample = []
for kq, n in sorted(QUOTA.items()):
    got = pool[kq]
    if len(got) < n:
        raise SystemExit(f"층 {kq} 모집단 {len(got)} < 몫 {n}")
    sample += rng.sample(got, n)
rng.shuffle(sample)                      # 층이 순서로 드러나지 않게 섞는다

out = HERE / "variant"
out.mkdir(exist_ok=True)
for i, s in enumerate(sample):
    s["vid"] = f"V-{i+1:03d}"

HEAD = """# 「변형」 점검 팩 — {nn}번 묶음 ({n}칸)

당신은 판독자입니다. 칸마다 **사실 한 문장**과 **수첩 한 장**이 있습니다.

## 묻는 것 — 이 하나뿐입니다

수첩이 그 사실을 **원문과 같은 뜻으로** 담고 있습니까.

| 판정 | 뜻 |
|---|---|
| **그대로** | 수첩에 그 사실이 있고, 뜻이 원문과 같다. 말을 바꿔 썼어도 알맹이가 같으면 그대로다 |
| **달라짐** | 수첩에 있긴 한데 **뜻이 원문과 다르다** — 숫자가 바뀌었거나, 반대 뜻이 되었거나, 원문에 없던 것이 생겼다 |
| **없음** | 수첩에 그 사실의 흔적이 없다 |

## 지킬 것

1. **얼마나 자세히 남았는지는 묻지 않습니다.** 짧게 줄여 적었어도 뜻이 같으면 `그대로`입니다.
2. **뜻이 달라진 것만 `달라짐`입니다.** 숫자가 다르거나, 조건이 뒤집혔거나, 원문에 없던
   내용이 붙었을 때입니다.
3. 애매하면 `그대로`를 주십시오. 이 팩은 **분명히 달라진 것만** 세려는 것입니다.
4. **근거를 쓰지 마십시오.** 표만 채웁니다.

## 내는 방법

`Write` 로 지시받은 `OUT_V_{nn}.md` 에 아래 형식 그대로 씁니다. 다른 글자는 넣지 마십시오.

```
| 칸 | 판정 |
|---|---|
| V-001 | 그대로 |
| V-002 | 달라짐 |
```

최종 답변에는 `쓴 파일: <경로> · 칸 <개수>` 한 줄만 적으십시오.

---
"""

packs = [sample[i:i+PER_PACK] for i in range(0, len(sample), PER_PACK)]
for pi, chunk in enumerate(packs, 1):
    nn = f"{pi:02d}"
    body = [HEAD.format(nn=nn, n=len(chunk))]
    for s in chunk:
        body.append(f"## {s['vid']}\n")
        body.append(f"**사실** — {s['fact']}\n")
        body.append(f"**수첩**\n\n> {s['note']}\n")
        body.append("---\n")
    (out / f"PACK_V_{nn}.md").write_text("\n".join(body), encoding="utf-8")

(out / "_SAMPLE.json").write_text(json.dumps(
    {"seed": SEED, "quota": {"|".join(k): v for k, v in QUOTA.items()},
     "n": len(sample), "cells": sample}, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"뽑은 칸 {len(sample)} · 팩 {len(packs)}개 ({PER_PACK}칸씩)")
for kq, n in sorted(QUOTA.items()):
    print(f"  {kq[0]:3s} {kq[1]:3s} {kq[2]:4s}수첩  모집단 {len(pool[kq]):4d} → {n}")
