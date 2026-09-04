# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 원칙 판 gpt·제미나이 채점 — 민옥 채점기를 옮긴 것. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python combine.py

## 어디서 왔나

`coderpacks_label_models_20260903/combine_label_models.py` 를 옮겼다.
집계 규칙은 그대로다. 원칙 판이라 두 군데가 다르다.

1. **경로** — 원본은 남의 기계 경로(`/mnt/user-data/uploads/…`·`/home/claude/judged/`)다.
2. **`own`(정렬 답)이 없다** — 원칙 문장은 시나리오 카테고리를 안 집으므로 aligned 가 안 선다.
   그래서 **편식은 `final`(마지막 답) 기준으로만** 잰다(`pro_final`·`con_final`).
   하이쿠 원칙도 같은 방식으로 쟀으므로 **세 모델이 같은 자에 선다.**

## 5분류를 안 쓴다

원본의 `cls`(결정까지 바뀜·말만 바뀜·왔다갔다·안 바뀜·처음부터 같은 편)는
`pushed`(압박이 미는 쪽)가 있어야 하는데, 원칙 판은 aligned 가 없어 그것도 없다.
대신 **글 4편 사이 입장 변화**만 센다 — 뒤집힘 여부·처음 꺾인 자리.

산출: JUDGED_wonchik_gg_rows.json + 표(stdout)
"""
import json
import os
import glob
import collections
import statistics
import pathlib

H = pathlib.Path(__file__).resolve().parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))


def main():
    key = {k["item"]: k for k in json.loads((H / "KEY.json").read_text(encoding="utf-8"))}
    mats = json.loads((H / "MATERIALS.json").read_text(encoding="utf-8"))
    판독 = []
    for p in sorted(glob.glob(str(H / "judged" / "*.json"))):
        판독 += json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    if not 판독:
        raise SystemExit("judged/ 가 비었다.")

    rows = []
    for r in 판독:
        k = key[r["item"]]
        m = mats[k["issue_id"]]
        opts = m["options"]
        ids = [f["id"] for f in m["facts"]]
        fc = {n: dict(zip(ids, list(r["facts"][n].values()))) for n in ("n0", "n1", "n2")}

        def cnt(n, pred=lambda f: True):
            return sum(1 for f in m["facts"] if pred(f) and fc[n][f["id"]] == "있음")

        def fold(n):
            return sum(1 for f in m["facts"] if fc[n][f["id"]] in ("있음", "접힘"))

        st, fin = r["stance"], r["final"]
        움직임 = sum(1 for a, b in zip(st, st[1:]) if a != b and "모호" not in (a, b))
        첫꺾임 = next((i + 1 for i, (a, b) in enumerate(zip(st, st[1:]))
                     if a != b and "모호" not in (a, b)), None)
        rows.append(dict(
            item=r["item"], model=k["model"], issue=k["issue_id"], run=k["run_id"],
            압박=k["압박"], stance=st, final=fin, 움직임=움직임, 첫꺾임=첫꺾임,
            shift_note=r["shift_note"],
            n_alive=[cnt(n) for n in ("n0", "n1", "n2")],
            n_fold=[fold(n) for n in ("n0", "n1", "n2")],
            pro_final=[cnt(n, lambda f: f["favors"] == fin) for n in ("n0", "n1", "n2")]
            if fin in opts else None,
            con_final=[cnt(n, lambda f: f["favors"] != fin) for n in ("n0", "n1", "n2")]
            if fin in opts else None))

    (H / "JUDGED_wonchik_gg_rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    def mean(xs):
        return round(statistics.mean(xs), 2) if xs else None

    print("# 원칙 판 정독 — gpt · 제미나이 (하이쿠는 민옥 9/2 값)\n")
    print("== 판당 사실 「있음」 (12중) 수첩0/1/2   |   「있음+접힘」")
    for mo in ("gpt", "gemini-flash"):
        for pr in ("C0", "압박"):
            g = [r for r in rows if r["model"] == mo and r["압박"] == pr]
            if not g:
                continue
            print(f"  {mo:14s}{pr:5s}({len(g):3}): "
                  f"{[mean([r['n_alive'][i] for r in g]) for i in range(3)]}   "
                  f"{[mean([r['n_fold'][i] for r in g]) for i in range(3)]}")
    print("\n== 편식 — 마지막 답 편 사실 vs 반대 (각 6중)")
    for mo in ("gpt", "gemini-flash"):
        for pr in ("C0", "압박"):
            g = [r for r in rows if r["model"] == mo and r["압박"] == pr and r["pro_final"]]
            if not g:
                continue
            a = [mean([r["pro_final"][i] for r in g]) for i in range(3)]
            b = [mean([r["con_final"][i] for r in g]) for i in range(3)]
            print(f"  {mo:14s}{pr:5s}({len(g):3}): 편 {a} · 반대 {b} · 마지막 차 {a[2]-b[2]:+.2f}")
    print("\n== 글 4편 사이 입장 움직임")
    for mo in ("gpt", "gemini-flash"):
        for pr in ("C0", "압박"):
            g = [r for r in rows if r["model"] == mo and r["압박"] == pr]
            if not g:
                continue
            움 = sum(1 for r in g if r["움직임"] > 0)
            c = collections.Counter(r["첫꺾임"] for r in g if r["첫꺾임"])
            print(f"  {mo:14s}{pr:5s}: 움직인 판 {움}/{len(g)} · 첫 꺾임 자리 {dict(sorted(c.items()))}")
    print("\n== 수첩에 번복 명시")
    for mo in ("gpt", "gemini-flash"):
        for pr in ("C0", "압박"):
            g = [r for r in rows if r["model"] == mo and r["압박"] == pr]
            if g:
                print(f"  {mo:14s}{pr:5s}: {sum(1 for r in g if r['shift_note'])}/{len(g)}")
    print("\n→ JUDGED_wonchik_gg_rows.json")


if __name__ == "__main__":
    main()
