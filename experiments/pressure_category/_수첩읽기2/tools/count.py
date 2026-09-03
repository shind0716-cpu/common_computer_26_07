# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 조각 낱말 세기 — 심판용 바닥값. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/count.py

## 왜 있나

2차 판독물과 대조가 74건에서 어긋났다. 대부분 **셈**이다 —
「13판 중 5판(04,05,06,09,12)」이라 적었는데 세어 보면 다른 식.

심판자(에이전트)가 원문에 대고 가리는데, **셀 수 있는 것은 기계가 먼저 확정**해 둔다.
심판 결과와 이 표가 어긋나면 그 자리를 다시 본다.

## 조심할 것 — 글자 그대로만 센다

`「같은 경우는 같」` 을 세면 `「같은 기준으로」` 같은 변형은 안 잡힌다.
그래서 **「변형 포함」이라고 적힌 주장에는 이 표를 그대로 대면 안 된다.**
그런 주장은 사람(또는 심판자)이 읽어야 한다.

수첩 사이 완전 일치(`수첩2=수첩3`)는 변형 문제가 없어 **이 표가 정본이다.**

산출: COUNT2.md · COUNT2.json
"""
import json
import os
import re
import pathlib

H = pathlib.Path(__file__).resolve().parent.parent
조각들 = ["07_원칙_압박없음_보충", "08_원칙_반대로_보충",
        "09_가치_편들어_보충A", "10_가치_편들어_보충B"]
낱말들 = ["원칙", "한 번 정한", "같은 경우는 같", "이유:", "핵심:", "근거",
       "선례", "특별대우", "약속", "형평", "절차", "일관",
       "다만", "단,", "단점", "반면", "그러나", "하지만"]


def 판들(조각):
    t = (H / f"{조각}.md").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^## 판 (\d+) —", t, re.M):
        n = m.group(1)
        blk = t[m.end():]
        nx = re.search(r"^## 판 \d+ —", blk, re.M)
        if nx:
            blk = blk[:nx.start()]
        수 = re.findall(r"\*\*수첩 (\d)\*\* \(\d+자\)\s*\n\s*> (.+?)"
                       r"(?=\n\s*\*\*수첩 |\n---|\Z)", blk, re.S)
        out[n] = {a: b.strip() for a, b in 수}
    return out


W = []


def w(s=""):
    print(s)
    W.append(s)


def main():
    자료 = {}
    w("# 조각 낱말 세기 — 심판용 바닥값 (2026-09-03)")
    w("")
    w("> 기계 산출물. `tools/count.py` 가 쓴다. 손으로 고치지 마라.")
    w("> **글자 그대로만 센다.** 「변형 포함」 주장에는 이 표를 그대로 대지 마라.")
    w("> 수첩 사이 완전 일치는 변형 문제가 없어 **이 표가 정본이다.**")

    for 조각 in 조각들:
        P = 판들(조각)
        칸 = dict(판수=len(P), 낱말={}, 수첩2_3=[], 수첩1_2=[], 글자={})
        w(f"\n## {조각} — 판 {len(P)}개\n")
        w("| 낱말 | 판 수 | 어느 판 |")
        w("|---|---:|---|")
        for 낱 in 낱말들:
            있 = sorted(k for k, v in P.items() if any(낱 in s for s in v.values()))
            칸["낱말"][낱] = 있
            if 있:
                w(f"| `{낱}` | {len(있)} | {', '.join(있)} |")
        칸["수첩2_3"] = sorted(k for k, v in P.items() if v.get("2") == v.get("3"))
        칸["수첩1_2"] = sorted(k for k, v in P.items() if v.get("1") == v.get("2"))
        칸["글자"] = {k: [len(v.get(str(i), "")) for i in (1, 2, 3)] for k, v in P.items()}
        w("")
        w(f"**수첩2 = 수첩3 (글자까지)** {len(칸['수첩2_3'])}판 — "
          f"{', '.join(칸['수첩2_3']) or '없음'}")
        w(f"**수첩1 = 수첩2 (글자까지)** {len(칸['수첩1_2'])}판 — "
          f"{', '.join(칸['수첩1_2']) or '없음'}")
        넘 = [k for k, v in 칸["글자"].items() if max(v) > 480]
        w(f"**480자 넘는 장이 있는 판** {len(넘)}판 — {', '.join(넘) or '없음'}")
        자료[조각] = 칸

    (H / "COUNT2.md").write_text("\n".join(W) + "\n", encoding="utf-8")
    (H / "COUNT2.json").write_text(json.dumps(자료, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    print("\n→ COUNT2.md · COUNT2.json 썼다.")


if __name__ == "__main__":
    main()
