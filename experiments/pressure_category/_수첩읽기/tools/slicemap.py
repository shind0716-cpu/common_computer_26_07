# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 조각 출처 되짚기 — 판 번호가 어느 실행인가. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/slicemap.py

## 왜 있나

조각 18개(`01_*.md` ~ `하이쿠_06_*.md`)는 판마다 「## 판 07 — issue_… · 세트 A」만
적고 **어느 실행 파일에서 왔는지를 안 적었다.** 그래서 판독물이 「판07이 뒤집혔다」고
해도 그 판의 발화문을 열 수가 없었다(요한 지적, 2026-09-03).

조각을 지은 자가 스크래치패드에 있어 사라질 참이라, **뽑기를 그대로 다시 돌려**
판 번호와 실행 파일을 맞춰 놓는다. 씨앗과 순서를 바꾸면 다른 조각이 된다.

## 그대로 지켜야 하는 것

- 씨앗 20260903
- gpt 는 **자기 rng 하나**로 여섯 조각을 차례로 뽑았다
- 제미나이·하이쿠는 **rng 하나를 둘이 나눠 썼다** — 제미나이 여섯, 그다음 하이쿠 여섯
- 모집단은 `str(경로)` 로 정렬한 뒤 `random.sample`
- 조각마다 20판(모자라면 있는 만큼)

맞는지는 조각 파일의 「## 판 NN — issue · 세트」 줄과 맞대 확인한다. 안 맞으면 멈춘다.

산출: SLICE_MAP.json
"""
import json
import os
import re
import random
import pathlib
import collections

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
SEED = 20260903
SL = collections.OrderedDict([
    ("01_가치_압박없음", ("A/B", "C0")),
    ("02_가치_편들어", ("A/B", "C1")),
    ("03_가치_반대로", ("A/B", "C2")),
    ("04_신념_압박없음", ("신념", "C0")),
    ("05_신념_반대로", ("신념", "pbw")),
    ("06_올세트_압박없음", ("올세트", "C0")),
])
뒤 = {"gemini-flash": "제미나이", "claude-haiku": "하이쿠"}


def 모집단(m):
    d = collections.defaultdict(list)
    for p in sorted((R / "runs" / m).glob("*/run_*.json")):
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
        if not fam or not cond or len((x.get("notes") or [])) < 3:
            continue
        d[(fam, cond)].append((p, x))
    return d


def 뽑기(m, rng, pool):
    """조각 하나 — _slice3.py / _slices.py 와 같은 차례로 돌린다."""
    out = {}
    for name, k in SL.items():
        cand = sorted(pool[k], key=lambda x: str(x[0]))
        if not cand:
            continue
        n = min(20, len(cand))
        pick = rng.sample(cand, n)
        out[name] = [(i, p, x) for i, (p, x) in enumerate(pick, 1)]
    return out


def 조각확인(파일, 뽑힌):
    """조각 파일의 머리줄과 맞대 본다. 하나라도 어긋나면 멈춘다."""
    p = H / f"{파일}.md"
    if not p.exists():
        return f"조각 파일 없음: {파일}.md"
    적힌 = re.findall(r"^## 판 (\d+) — (\S+) · 세트 (\S+)", p.read_text(encoding="utf-8"), re.M)
    if len(적힌) != len(뽑힌):
        return f"{파일}: 판 수가 다르다 — 조각 {len(적힌)} vs 되짚음 {len(뽑힌)}"
    for (번호, iid, vset), (i, _, x) in zip(적힌, 뽑힌):
        if int(번호) != i or iid != x.get("issue_id") or vset != str(x.get("value_set")):
            return (f"{파일} 판 {번호}: 조각은 {iid}/{vset} 인데 "
                    f"되짚음은 {x.get('issue_id')}/{x.get('value_set')}")
    return None


def main():
    지도 = {}
    탈 = []

    # gpt — 자기 rng 하나
    rng = random.Random(SEED)
    for name, 뽑힌 in 뽑기("gpt", rng, 모집단("gpt")).items():
        e = 조각확인(name, 뽑힌)
        (탈.append(e) if e else None)
        지도[name] = dict(모델="gpt", 조건=name, 판={
            f"{i:02d}": dict(경로=str(p.relative_to(R)).replace("\\", "/"),
                             run_id=x.get("run_id"), issue=x.get("issue_id"),
                             세트=x.get("value_set"), 각본=x.get("script"),
                             정렬답=x.get("aligned"), 최종답=x.get("final_poll"),
                             발화=len(x.get("essays") or []), 수첩=len(x.get("notes") or []))
            for i, p, x in 뽑힌})

    # 제미나이·하이쿠 — rng 하나를 둘이 나눠 쓴다
    rng2 = random.Random(SEED)
    for m, kor in 뒤.items():
        for name, 뽑힌 in 뽑기(m, rng2, 모집단(m)).items():
            파일 = f"{kor}_{name}"
            e = 조각확인(파일, 뽑힌)
            (탈.append(e) if e else None)
            지도[파일] = dict(모델=m, 조건=name, 판={
                f"{i:02d}": dict(경로=str(p.relative_to(R)).replace("\\", "/"),
                                 run_id=x.get("run_id"), issue=x.get("issue_id"),
                                 세트=x.get("value_set"), 각본=x.get("script"),
                                 정렬답=x.get("aligned"), 최종답=x.get("final_poll"),
                                 발화=len(x.get("essays") or []), 수첩=len(x.get("notes") or []))
                for i, p, x in 뽑힌})

    if 탈:
        print("어긋났다 — 되짚기가 조각과 안 맞는다:")
        for e in 탈:
            print(f"  {e}")
        raise SystemExit("씨앗·순서·정렬이 조각을 만들 때와 다르다. 지도를 쓰지 마라.")

    (H / "SLICE_MAP.json").write_text(json.dumps(dict(
        씨앗=SEED, 조각수=len(지도),
        판수=sum(len(v["판"]) for v in 지도.values()),
        비고="조각 파일의 「## 판 NN — issue · 세트」 줄과 전부 맞춰 확인했다.",
        조각=지도,
    ), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"조각 {len(지도)}개 · 판 {sum(len(v['판']) for v in 지도.values())}개 되짚었다.")
    print("조각 파일과 전부 맞는다 → SLICE_MAP.json")


if __name__ == "__main__":
    main()
