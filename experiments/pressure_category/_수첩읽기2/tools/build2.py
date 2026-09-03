# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 조각 2차 — 1차가 안 읽은 판만 뽑는다. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/build2.py

코워크 지시서 `WORKORDER_수첩읽기2_2026-09-03.md` 그대로다.

## 무엇을 뽑나

    07_원칙_압박없음_보충   신념 C0  33판 중 1차가 안 읽은 13판 전부 → 33/33 전수
    08_원칙_반대로_보충     신념 pbw 33판 중 안 읽은 13판 전부      → 33/33 전수
    09_가치_편들어_보충A    A/B C1 240판 중 안 읽은 220판에서 20판  (씨앗 20260903b)
    10_가치_편들어_보충B    같음, 09 와 안 겹치게 20판

## 1차가 읽은 판을 어떻게 아나

1차 조각 파일에는 실행 이름이 없다. 선행 작업이 `_수첩읽기/tools/slicemap.py` 로
씨앗 20260903 뽑기를 그대로 다시 돌려 되짚었고, **조각 파일의 판 머리줄과 전부
대조해 확인**했다(판 360개, 어긋남 0). 그 결과가 `_수첩읽기/SLICE_MAP.json` 이다.
여기서는 그 파일을 읽어 쓰고, **없거나 판 수가 안 맞으면 멈춘다.**

## 1차와 다른 것 하나

판 머리에 실행 이름을 붙인다. **뒷부분은 1차와 같게 둔다**(파서가 그대로 돌아야 한다).

    ## 판 07 — issue_workmind · 세트 wonchik_workmind · 준 가치 [...] · run_C0_..._rep2

1차 조각은 손대지 않는다 — 증거물이다.

산출: 07_*.md · 08_*.md · 09_*.md · 10_*.md · _KEY2.json
"""
import json
import os
import random
import pathlib
import collections

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
일차 = H.parent / "_수첩읽기"

# (조각 이름, 갈래, 각본, 뽑는 법)
할것 = [
    ("07_원칙_압박없음_보충", "신념", "C0", "전부"),
    ("08_원칙_반대로_보충", "신념", "pbw", "전부"),
    ("09_가치_편들어_보충A", "A/B", "C1", 20),
    ("10_가치_편들어_보충B", "A/B", "C1", 20),
]
# 1차 조각 이름 ← (갈래, 각본)
일차조각 = {("신념", "C0"): "04_신념_압박없음",
          ("신념", "pbw"): "05_신념_반대로",
          ("A/B", "C1"): "02_가치_편들어"}


def 모집단():
    d = collections.defaultdict(list)
    for p in sorted((R / "runs" / "gpt").glob("*/run_*.json")):
        try:
            x = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        vs = x.get("value_set_id") or x.get("value_set") or ""
        sc = x.get("script") or ""
        fam = ("A/B" if vs in ("A", "B")
               else "신념" if vs.startswith("wonchik_")
               else "올세트" if vs.startswith(("all_", "allb1_")) else None)
        cond = sc if sc in ("C0", "C1", "C2") else ("pbw" if sc.startswith("pbw_") else None)
        if not fam or not cond or len(x.get("notes") or []) < 3:
            continue
        d[(fam, cond)].append((p, x))
    return d


def 이미읽음():
    p = 일차 / "SLICE_MAP.json"
    if not p.exists():
        raise SystemExit("SLICE_MAP.json 이 없다. _수첩읽기/tools/slicemap.py 를 먼저 돌려라.")
    m = json.loads(p.read_text(encoding="utf-8"))["조각"]
    if sum(len(v["판"]) for v in m.values()) != 360:
        raise SystemExit("SLICE_MAP 의 판 수가 360이 아니다. 되짚기를 다시 확인하라.")
    out = {}
    for (fam, cond), 조각 in 일차조각.items():
        if 조각 not in m:
            raise SystemExit(f"SLICE_MAP 에 조각 {조각} 이 없다.")
        out[(fam, cond)] = {v["경로"] for v in m[조각]["판"].values()}
    return out


def 판블록(i, p, x):
    줄 = [f"## 판 {i:02d} — {x.get('issue_id')} · 세트 {x.get('value_set')}"
          f" · 준 가치 {x.get('value_categories')} · {pathlib.Path(p).stem}\n"]
    for j, nt in enumerate(x["notes"][:3]):
        줄.append(f"**수첩 {j + 1}** ({len(nt)}자)\n\n> {nt}\n")
    줄.append("---\n")
    return 줄


def main():
    pop = 모집단()
    읽음 = 이미읽음()
    rng = random.Random("20260903b")
    key = {}
    쓴것 = []
    C1남은 = None

    for 이름, fam, cond, 법 in 할것:
        전체 = pop.get((fam, cond)) or []
        본것 = 읽음[(fam, cond)]
        남은 = [(p, x) for p, x in 전체
                if str(p.relative_to(R)).replace("\\", "/") not in 본것]
        if len(남은) != len(전체) - len(본것):
            raise SystemExit(f"{이름}: 뺀 판 수가 안 맞는다 "
                             f"(전체 {len(전체)} · 1차 {len(본것)} · 남은 {len(남은)})")
        남은.sort(key=lambda t: str(t[0]))

        if 법 == "전부":
            뽑음 = 남은
        else:
            # 09 와 10 은 같은 남은 더미에서 겹치지 않게 이어 뽑는다
            if C1남은 is None:
                C1남은 = list(남은)
                rng.shuffle(C1남은)
            뽑음, C1남은 = C1남은[:법], C1남은[법:]

        줄 = [f"# gpt 수첩 읽기 2차 — {이름.split('_', 1)[1]}"
              f" ({len(뽑음)}판 · 수첩 {len(뽑음) * 3}장)\n",
              "판마다 수첩 세 장을 순서대로 싣는다. 원문 그대로다.\n",
              "판 머리의 `run_*` 이름은 되짚기용이다. 판정에 쓰지 마라.\n",
              "---\n"]
        for i, (p, x) in enumerate(뽑음, 1):
            줄 += 판블록(i, p, x)
            key[f"{이름}|{i:02d}"] = dict(
                조각=이름, 판=f"{i:02d}",
                경로=str(p.relative_to(R)).replace("\\", "/"),
                run_id=x.get("run_id"), issue=x.get("issue_id"),
                세트=x.get("value_set"), 각본=x.get("script"),
                정렬답=x.get("aligned"), 최종답=x.get("final_poll"))
        (H / f"{이름}.md").write_text("\n".join(줄), encoding="utf-8")
        쓴것.append((이름, len(전체), len(본것), len(뽑음)))

    (H / "_KEY2.json").write_text(json.dumps(dict(
        씨앗="20260903b (가치 편들어만) · 원칙은 나머지 전부라 뽑기 없음",
        일차되짚음="_수첩읽기/SLICE_MAP.json (판 360, 조각 파일과 대조 확인)",
        판=key), ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{'조각':26s}{'모집단':>7s}{'1차':>6s}{'이번':>6s}{'덮은 몫':>9s}")
    for 이름, 전, 본, 새 in 쓴것:
        print(f"{이름:26s}{전:>7d}{본:>6d}{새:>6d}{(본 + 새) / 전 * 100:>8.0f}%")
    print(f"\n판 {sum(x[3] for x in 쓴것)}개 · 수첩 {sum(x[3] for x in 쓴것) * 3}장 · _KEY2.json")


if __name__ == "__main__":
    main()
