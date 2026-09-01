"""[공용 코어 · 압박×카테고리] 진단 — 셈씨 표기 차이가 채점을 얼마나 깎아먹나 (콜 0).

## 왜 이 파일이 따로 있나

집계(`aggregate_all11.py`)에서 `cat_feeding_days_list` 의 표식 생존율이 11.0%로
열한 재료 중 꼴찌였고, 여섯 카테고리 중 **셋은 741판 전체에서 한 번도** 안 잡혔다.
원문을 보니 사실이 없는 게 아니었다. 재료가 **고유어 셈씨**로 쓰였고
(「이레 가운데 나흘」·「열여드레」·「네 걸음 거리」), 모델은 수첩에 **아라비아 숫자**로
옮겨 적는다(「7일 중 4일」·「18일」·「4걸음」). 문자열 검색이 전부 놓친다.

이 파일은 그 크기를 **잰다**. 채점을 고치지 않는다 — 본 집계의 수치는 그대로 두고,
"셈씨만 접었다면 얼마나 달라졌겠나"를 따로 찍는다. 접을지 말지는 사람이 정한다
(스캐너 판정 사양을 바꾸는 일이라 보드 결정 로그에 한 줄 남길 사안이다).

## 접는 것 — 구절 단위, 전부 여기 적혀 있다

낱자 단위로 「네」→「4」 같은 것을 접으면 「네 생각」이 「4 생각」이 되어 엉뚱한 데가
걸린다. 그래서 **구절 단위**로만 접고, 접는 목록을 전부 이 파일에 적어 둔다.
표식과 수첩 **양쪽에** 같은 규칙을 건다.

접지 않는 것(관찰만): 요일 줄임(「목요일과 토요일」→「화·목·토」), 뜻 바꿔 말하기
(「진창」→「질척」). 이건 표기 변형이 아니라 말 바꾸기라 판독이 할 일이다.

사용: PYTHONUTF8=1 python experiments/pressure_category/diag_numword.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate_all11 as A  # noqa: E402

HERE = A.HERE
OUT = HERE / "DIAG_numword_2026-09-01.md"

# 고유어 셈씨 → 아라비아 숫자. 구절 단위. 긴 것부터 걸리도록 순서를 지킨다.
FOLD = [
    ("열여드레", "18일"),
    ("이레 가운데 나흘", "7일가운데4일"),
    ("이레", "7일"),
    ("나흘", "4일"),
    ("열흘", "10일"),
    ("넉 주", "4주"),
    ("네 걸음", "4걸음"),
    ("두 시간", "2시간"),
    ("세 시간", "3시간"),
    ("한 시간", "1시간"),
]


def fold(t: str) -> str:
    for a, b in FOLD:
        t = t.replace(a, b)
    return A.norm(t)


def hit4(anchor: str, note: str) -> bool:
    """④ 진단 잣대 = ③ 사다리에 셈씨 접기를 더한 것."""
    a, n = fold(anchor), fold(note)
    if a in n:
        return True
    for k in range(1, A.MAX_TRIM + 1):
        a2 = a[: len(a) - k]
        if len(a2) < A.MIN_KEEP:
            break
        if a2 in n:
            return True
    return False


def main():
    man, mats, allsets = A.load_materials()
    per_mat = defaultdict(lambda: [0, 0, 0])   # iid → [③생존, ④생존, 전체]
    per_arm = defaultdict(lambda: [0, 0, 0])
    gained = defaultdict(int)                   # 표식 → ④에서만 잡힌 횟수
    for p in sorted(A.RUNS.rglob("run_*.json")):
        if p.relative_to(A.RUNS).parts[0].startswith("_"):
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        iid = doc.get("issue_id")
        if iid not in mats:
            continue
        arm = A.arm_of(doc, allsets[iid])
        if arm is None:
            continue
        notes = doc.get("notes") or []
        if not notes:
            continue
        last = notes[-1]
        for f in mats[iid]["facts"]:
            lv3 = A.probe(f["anchor"], last)[0] > 0
            lv4 = hit4(f["anchor"], last)
            key_arm = f'{p.relative_to(A.RUNS).parts[0]} | {arm}'
            for d, k in ((per_mat, iid), (per_arm, key_arm)):
                d[k][0] += lv3
                d[k][1] += lv4
                d[k][2] += 1
            if lv4 and not lv3:
                gained[f'{iid}·{f["id"]}·{f["anchor"]}'] += 1

    L = ["# 진단 — 셈씨 표기 차이가 채점을 얼마나 깎았나 (2026-09-01, 기계 생성물)",
         "",
         "> 지위: **진단**. 본 집계(`AGG_all11_2026-09-01.json`)의 수치는 이 표로 바뀌지",
         "> 않는다. 스캐너 판정 사양을 바꿀지는 사람이 정한다.",
         "",
         "접은 목록: " + " · ".join(f"`{a}`→`{b}`" for a, b in FOLD),
         "",
         "## 재료별", "",
         "| 재료 | ③ 꼬리 깎아 | ④ 셈씨까지 접어 | 늘어난 칸 |", "|---|---:|---:|---:|"]
    for iid, (a, b, n) in sorted(per_mat.items(), key=lambda x: x[1][1] - x[1][0], reverse=True):
        L.append(f"| {iid.replace('issue_', '')} | {100*a/n:.1f}% ({a}/{n}) | "
                 f"{100*b/n:.1f}% ({b}/{n}) | {b-a:+d} |")
    L += ["", "## 조건별", "", "| 모델 · 조건 | ③ | ④ | 늘어난 칸 |", "|---|---:|---:|---:|"]
    for k, (a, b, n) in sorted(per_arm.items()):
        L.append(f"| {k} | {100*a/n:.1f}% | {100*b/n:.1f}% | {b-a:+d} |")
    L += ["", "## ④ 에서만 잡힌 표식", "", "| 재료·사실·표식 | 늘어난 판 |", "|---|---:|"]
    for k, v in sorted(gained.items(), key=lambda x: -x[1]):
        L.append(f"| {k} | {v} |")
    if not gained:
        L.append("| (없음) | 0 |")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    tot3 = sum(v[0] for v in per_mat.values())
    tot4 = sum(v[1] for v in per_mat.values())
    totn = sum(v[2] for v in per_mat.values())
    print(f"찍었다: {OUT.name}")
    print(f"전체 {totn}칸 · ③ {tot3} ({100*tot3/totn:.1f}%) → ④ {tot4} ({100*tot4/totn:.1f}%) · 늘어난 칸 {tot4-tot3:+d}")
    for k, v in sorted(gained.items(), key=lambda x: -x[1])[:12]:
        print(f"   +{v:3d}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
