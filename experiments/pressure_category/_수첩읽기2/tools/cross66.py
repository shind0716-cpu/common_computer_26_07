# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 원칙 66판 — 뜻 판독과 기계 표식을 판 대 판으로. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/cross66.py

## 왜 이 66판인가

코워크 지시서가 원칙 조건을 전수로 채우라 한 까닭이다.
1차가 20판, 2차가 나머지 13판을 읽어 **33/33 이 됐고**, 압박 판도 마찬가지다.
뜻 판독(`coderpacks_meaning2`)도 같은 조건을 전수로 읽었다.
파일 이름으로 맞대 보니 **겹침 66/66, 어느 쪽에만 있는 판 0** 이다.

즉 **재료를 맞출 필요 없이 같은 판을 둘이 읽은 상태**다.

## 무엇을 맞대나 — 그리고 무엇은 못 맞대나

| | 무엇을 내나 | 맞댈 수 있나 |
|---|---|---|
| 뜻 판독 | 판마다 사실 12개 × (첫 수첩·마지막 수첩) × 3등급 | ○ |
| 기계 표식 | 판마다 사실 12개의 표식이 수첩에 있나 | ○ |
| 우리 수첩 판독 | 줄글 서술(뼈대·접힘·채움) | **×** — 판당 숫자가 없다 |

그래서 여기서 재는 것은 **뜻 판독 대 기계 표식**이다.
우리 수첩 판독은 숫자로 못 맞대고, 사례로 붙는다(`READ_*.md`).

## 눈금

- 뜻 판독은 사전고정 §3 대로 **「있음」만 살았다고 센다**(「이름만」은 죽은 쪽).
- 기계는 트랙이 쓰는 기준 ②(그대로+접어서) — `aggregate_all11.probe`.
  못 불러오면 멈춘다. 다른 자를 조용히 쓰지 않는다.
- 뜻 판독의 쌍은 [첫 수첩, 마지막 수첩] 이다(채점기가 그렇게 읽는다).

산출: CROSS66.md · CROSS66.json
"""
import json
import os
import sys
import glob
import pathlib
import statistics as st

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
sys.path.insert(0, str(R))
try:
    import aggregate_all11 as A

    def 표식있나(anchor, text):
        return 0 < A.probe(anchor, text)[0] <= 2
    자 = "기준 ②(그대로+접어서) · aggregate_all11.probe"
except Exception as e:
    sys.exit(f"aggregate_all11 을 못 불러왔다({e}). 트랙과 다른 자를 조용히 쓰지 않는다.")

W = []


def w(s=""):
    print(s)
    W.append(s)


def main():
    뜻키 = json.loads((R / "coderpacks_meaning2" / "_KEY_2026-09-02.json")
                     .read_text(encoding="utf-8"))
    뜻값 = json.loads((R / "coderpacks_meaning2" / "_COLLECTED_meaning2.json")
                     .read_text(encoding="utf-8"))
    mats = {}
    for p in glob.glob(str(R / "materials" / "*.json")):
        d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        if d.get("issue_id"):
            mats[d["issue_id"]] = d

    # 우리 66판 — 1차 20 + 2차 13, 조건 둘
    우리 = {}
    m1 = json.loads((H.parent / "_수첩읽기" / "SLICE_MAP.json").read_text(encoding="utf-8"))["조각"]
    for 조각, 조건 in (("04_신념_압박없음", "압박없음"), ("05_신념_반대로", "반대로")):
        for v in m1[조각]["판"].values():
            우리[os.path.basename(v["경로"])] = 조건
    k2 = json.loads((H / "_KEY2.json").read_text(encoding="utf-8"))["판"]
    for v in k2.values():
        if v["조각"].startswith(("07", "08")):
            우리[os.path.basename(v["경로"])] = "압박없음" if v["조각"].startswith("07") else "반대로"

    행 = []
    for pid, k in 뜻키.items():
        if k["arm"] != "belief":
            continue
        이름 = os.path.basename(str(k["file"]).replace("\\", "/"))
        if 이름 not in 우리 or pid not in 뜻값:
            continue
        run = json.loads((R / "runs" / "gpt" / f"issue_{k['issue_id'].replace('issue_', '')}"
                          / 이름).read_text(encoding="utf-8")) \
            if False else None
        # 경로는 SLICE_MAP·_KEY2 에 있는 것을 그대로 쓴다
        경로 = None
        for src in (m1["04_신념_압박없음"]["판"], m1["05_신념_반대로"]["판"]):
            for v in src.values():
                if os.path.basename(v["경로"]) == 이름:
                    경로 = v["경로"]
        for v in k2.values():
            if os.path.basename(v["경로"]) == 이름:
                경로 = v["경로"]
        if not 경로:
            continue
        d = json.loads((R / 경로).read_text(encoding="utf-8"))
        facts = mats[d["issue_id"]]["facts"]
        notes = d["notes"][:3]
        등급 = 뜻값[pid]
        if len(등급) != len(facts):
            continue
        뜻첫 = sum(1 for g in 등급 if g[0] == "있음")
        뜻끝 = sum(1 for g in 등급 if g[1] == "있음")
        기첫 = sum(1 for f in facts
                  if (f.get("anchor") or "").strip() and 표식있나(f["anchor"].strip(), notes[0]))
        기끝 = sum(1 for f in facts
                  if (f.get("anchor") or "").strip() and 표식있나(f["anchor"].strip(), notes[-1]))
        칸 = []
        for f, g in zip(facts, 등급):
            a = (f.get("anchor") or "").strip()
            if not a:
                continue
            칸.append((g[0] == "있음", 표식있나(a, notes[0]), "첫"))
            칸.append((g[1] == "있음", 표식있나(a, notes[-1]), "끝"))
        행.append(dict(pid=pid, 판=이름, 조건=우리[이름], issue=d["issue_id"],
                       뜻첫=뜻첫, 뜻끝=뜻끝, 기첫=기첫, 기끝=기끝, 칸=칸))

    w("# 원칙 66판 — 뜻 판독과 기계 표식을 판 대 판으로 (2026-09-03)")
    w("")
    w("> 기계 산출물. `tools/cross66.py` 가 쓴다. 손으로 고치지 마라.")
    w(f"> 기계 자 = {자} · 뜻 판독은 「있음」만 살았다고 센다(사전고정 §3)")
    w("")
    w(f"맞댄 판 **{len(행)}**. 재료를 맞출 필요가 없었다 — **같은 판을 둘이 읽었다.**")
    w("")
    w("**우리 수첩 판독(`READ_*.md`)은 이 표에 안 들어간다.** 줄글이라 판당 숫자가 없다.")
    w("여기서 재는 것은 뜻 판독(사람 눈금) 대 기계 표식이다.")

    if not 행:
        w("\n맞댄 판이 없다 — 경로 맞추기를 확인하라.")
        (H / "CROSS66.md").write_text("\n".join(W) + "\n", encoding="utf-8")
        return

    # ── 1. 판당 살아남은 사실 수 ────────────────────────────────
    w("\n## 1. 판당 살아남은 사실 수\n")
    w("| 조건 | 판 | 뜻 첫 | 기계 첫 | 뜻 끝 | 기계 끝 |")
    w("|---|---:|---:|---:|---:|---:|")
    for 조 in ("압박없음", "반대로"):
        s = [r for r in 행 if r["조건"] == 조]
        if not s:
            continue
        w(f"| {조} | {len(s)} | {st.mean(r['뜻첫'] for r in s):.2f} |"
          f" {st.mean(r['기첫'] for r in s):.2f} |"
          f" {st.mean(r['뜻끝'] for r in s):.2f} |"
          f" {st.mean(r['기끝'] for r in s):.2f} |")
    w(f"| **합** | **{len(행)}** | {st.mean(r['뜻첫'] for r in 행):.2f} |"
      f" {st.mean(r['기첫'] for r in 행):.2f} |"
      f" {st.mean(r['뜻끝'] for r in 행):.2f} |"
      f" {st.mean(r['기끝'] for r in 행):.2f} |")

    # ── 2. 칸 단위 일치 ────────────────────────────────────────
    w("\n## 2. 칸 단위 — 사실 하나하나에서 둘이 같은 말을 하나\n")
    모든칸 = [c for r in 행 for c in r["칸"]]
    n = len(모든칸)
    둘다 = sum(1 for a, b, _ in 모든칸 if a and b)
    둘다없 = sum(1 for a, b, _ in 모든칸 if not a and not b)
    뜻만 = sum(1 for a, b, _ in 모든칸 if a and not b)
    기만 = sum(1 for a, b, _ in 모든칸 if not a and b)
    맞 = 둘다 + 둘다없
    w("| | 기계 있음 | 기계 없음 |")
    w("|---|---:|---:|")
    w(f"| **뜻 있음** | {둘다} | {뜻만} |")
    w(f"| **뜻 없음** | {기만} | {둘다없} |")
    w("")
    w(f"칸 {n}개 · **같은 말 {맞} = {맞 / n * 100:.1f}%**")
    w("")
    w(f"- **뜻은 살았다는데 기계가 못 잡음 {뜻만} ({뜻만 / n * 100:.1f}%)** — 말을 바꿔 쓴 자리다.")
    w(f"  기계가 놓치는 몫이고, 표식 자가 **하한**이라는 뜻이다.")
    w(f"- **기계는 잡았는데 뜻은 죽었다 함 {기만} ({기만 / n * 100:.1f}%)** — 표식은 남았는데")
    w(f"  구체가 빠졌거나 뜻이 달라진 자리다(엄격 눈금의 오탐).")

    # 코헨 카파
    p0 = 맞 / n
    p뜻 = (둘다 + 뜻만) / n
    p기 = (둘다 + 기만) / n
    pe = p뜻 * p기 + (1 - p뜻) * (1 - p기)
    k = (p0 - pe) / (1 - pe) if pe < 1 else 0.0
    w("")
    w(f"**카파 {k:.3f}** (우연 일치 {pe * 100:.1f}% 를 뺀 값)")

    # ── 3. 첫 수첩과 마지막 수첩을 갈라서 ─────────────────────────
    w("\n## 3. 첫 수첩과 마지막 수첩을 갈라서\n")
    w("| 자리 | 칸 | 같은 말 | 뜻만 있음 | 기계만 있음 |")
    w("|---|---:|---:|---:|---:|")
    for 자리 in ("첫", "끝"):
        s = [c for c in 모든칸 if c[2] == 자리]
        m = sum(1 for a, b, _ in s if a == b)
        w(f"| {자리} 수첩 | {len(s)} | {m / len(s) * 100:.1f}% |"
          f" {sum(1 for a, b, _ in s if a and not b)} |"
          f" {sum(1 for a, b, _ in s if not a and b)} |")

    # ── 4. 못 하는 말 ──────────────────────────────────────────
    w("\n## 4. 이 표가 못 하는 말\n")
    w("- **우리 수첩 판독은 안 들어갔다.** 줄글이라 판당 숫자가 없다.")
    w("  코워크 지시서 §5-2 가 말한 「두 판독의 일치도」는 이 표로는 못 낸다 —")
    w("  **이 표는 뜻 판독 대 기계다.** 수첩 판독을 넣으려면 판당 수치를 내는 물음이 따로 필요하다.")
    w("- 뜻 판독은 코더가 사람이 아니고, 코더 하나가 한 팩을 읽었다.")
    w("- 기계는 표식이 **글자로 남았나**만 본다. 말을 바꿔 쓴 자리를 놓친다(§2 의 「뜻만」).")
    w("- 원칙 판 66개다. 가치 판으로 넓혀 말하지 마라.")

    (H / "CROSS66.md").write_text("\n".join(W) + "\n", encoding="utf-8")
    (H / "CROSS66.json").write_text(json.dumps(dict(
        판=len(행), 자=자, 카파=k,
        칸=dict(전체=n, 같음=맞, 뜻만=뜻만, 기계만=기만, 둘다=둘다, 둘다없음=둘다없),
        행=[{k2: v for k2, v in r.items() if k2 != "칸"} for r in 행],
    ), ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n→ CROSS66.md · CROSS66.json 썼다.")


if __name__ == "__main__":
    main()
