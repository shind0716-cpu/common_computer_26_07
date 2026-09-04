# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 이중 판독 일치도 — 코더 둘이 같은 36판을 따로 읽은 것. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python agree.py

## 왜 필요한가

`combine.py` 가 낸 원칙 판 수치(gpt 6.7 · 제미나이 3.7 …)를 민옥의 하이쿠 3.3 옆에
놓으려면 **눈금이 흔들리지 않는다는 근거**가 있어야 한다. 코더 하나가 한 번 읽은 값은
그 근거가 없다. 그래서 22팩 중 6팩(36판)을 다른 코더가 다시 읽었다.

민옥 채점기에는 일치도 계산 줄이 없다(`combine_label_models.py` 확인). 여기서 짓는다.

## 무엇을 재나

- **사실 칸** 36판 × 12사실 × 수첩 3장 = 1296칸, 세 값(있음/접힘/없음) → 카파
- **입장** 36판 × 글 4편 = 144칸
- **마지막 답** 36칸
- **판당 사실 수** 두 코더가 각각 센 「있음」 개수의 차이 — 이게 표에 실리는 값이라
  카파보다 이쪽이 직접적이다

카파는 우연 일치를 뺀 값이라 칸이 한쪽으로 쏠리면 낮게 나온다. 그래서 생 일치율도
같이 적는다.

산출: 표(stdout)
"""
import json
import glob
import pathlib
import collections
import statistics

H = pathlib.Path(__file__).resolve().parent


def 카파(쌍):
    if not 쌍:
        return None
    라벨 = sorted({v for p in 쌍 for v in p})
    n = len(쌍)
    po = sum(1 for a, b in 쌍 if a == b) / n
    ca = collections.Counter(a for a, _ in 쌍)
    cb = collections.Counter(b for _, b in 쌍)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in 라벨)
    return (po, None if pe >= 1 else (po - pe) / (1 - pe))


def 싣기(d):
    out = {}
    for p in sorted(glob.glob(str(H / d / "*.json"))):
        for r in json.loads(pathlib.Path(p).read_text(encoding="utf-8")):
            out[r["item"]] = r
    return out


def main():
    a, b = 싣기("judged"), 싣기("judged_2nd")
    겹 = sorted(set(a) & set(b))
    if not 겹:
        raise SystemExit("겹치는 판이 없다.")

    사실, 입장, 최종 = [], [], []
    개수차 = []
    for it in 겹:
        ra, rb = a[it], b[it]
        for n in ("n0", "n1", "n2"):
            va, vb = list(ra["facts"][n].values()), list(rb["facts"][n].values())
            사실 += list(zip(va, vb))
        입장 += list(zip(ra["stance"], rb["stance"]))
        최종.append((ra["final"], rb["final"]))
        개수차.append(sum(1 for v in ra["facts"]["n2"].values() if v == "있음")
                    - sum(1 for v in rb["facts"]["n2"].values() if v == "있음"))

    print(f"# 이중 판독 일치도 — 원칙 판 {len(겹)}판 (22팩 중 6팩)")
    print("# 코더 둘이 서로 모르게 같은 판을 읽었다.\n")
    for 이름, 쌍 in (("사실 칸 (있음/접힘/없음)", 사실), ("입장 (글 4편)", 입장), ("마지막 답", 최종)):
        po, k = 카파(쌍)
        print(f"  {이름:24s} {len(쌍):5}칸 · 생 일치 {po*100:5.1f}% · 카파 "
              + ("—(한 값 쏠림)" if k is None else f"{k:.3f}"))

    print(f"\n  마지막 수첩 「있음」 개수 차 — 평균 {statistics.mean(개수차):+.2f}개"
          f" · 절대차 평균 {statistics.mean(map(abs, 개수차)):.2f}개"
          f" · 폭 {min(개수차):+d}~{max(개수차):+d}")
    print(f"  두 코더 판당 평균: 1차 "
          f"{statistics.mean([sum(1 for v in a[i]['facts']['n2'].values() if v=='있음') for i in 겹]):.2f}"
          f" · 2차 "
          f"{statistics.mean([sum(1 for v in b[i]['facts']['n2'].values() if v=='있음') for i in 겹]):.2f}")

    c = collections.Counter()
    for x, y in 사실:
        if x != y:
            c[f"{x}→{y}"] += 1
    print(f"\n  어긋난 칸 {sum(c.values())}: {dict(c.most_common())}")


if __name__ == "__main__":
    main()
