# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 수첩 모양 세기 — 세 모델 전량. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/shape.py

수첩이 **어떻게 생겼는지**를 낱말 무늬로 센다. 사실 보존이나 답을 재지 않는다.
그건 report_facts.py · report_choice.py 가 한다.

## 왜 있나

2026-09-03, gpt 수첩 890판을 눈으로 읽고 「수첩은 결재 양식이다」라고 적었다.
그 말이 다른 모델에도 서는지 보려고 전량을 셌다. 그 수치가 스크래치패드에만
남아 증발할 뻔해서 이리로 옮겼다(요한 지적).

## 무엇을 세나

수첩 한 장마다 — 글자 수 · 번호 목록 · 접힘 표지 · 머리 60자 안의 결론말
판 하나마다 — 수첩1=수첩2 · 수첩2=수첩3 · 첫끝 닮음 · 번호가 사라졌나 생겼나
모델마다 — 접힘 표지 낱말별 빈도 · 글자 분포(450자 초과 몫)

## 조심할 것 — 이 자는 gpt 무늬로 지어졌다

「번호 목록」 「머리에 결론」 「꼬리 표지」는 전부 gpt 판독물에서 뽑은 무늬다.
그래서 다른 모델의 수치는 **「gpt 틀을 얼마나 따르나」**로 읽어야지
**「그 모델이 무엇을 하나」**로 읽으면 안 된다.

실측 사고: 제미나이 「머리에 결론 45%」는 결론을 안 쓴다는 뜻이 아니다.
제미나이는 결론 앞에 가치를 자기 말로 다시 부르는 자리가 하나 더 있어
첫 60자 안에 안 잡힐 뿐이다. 눈으로 읽은 쪽이 이걸 잡았다.

## 물린 자 하나

「라운드 사이 입장 뒤집힘」을 첫 90자에서 어느 선택지가 먼저 불리는지로 쟀더니
하이쿠 21.9%가 나왔는데, 같은 구간을 눈으로 읽은 판독물 둘이 0/20 을 봤다.
「A보다 B」 문형을 자가 잘못 읽은 것이다. 지우지 않고 §5 에 남기되 **쓰지 않는다.**

산출: SHAPE_3MODEL.json · SHAPE_3MODEL.md
"""
import json
import re
import os
import sys
import glob
import pathlib
import difflib
import collections
import statistics as st

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
MOD = ["gpt", "gemini-flash", "claude-haiku"]
NAME = {"gpt": "gpt", "gemini-flash": "제미나이", "claude-haiku": "하이쿠"}

NUM = re.compile(r"(①|②|③|[1-3]\)|[1-3]\.\s)")
CONC = re.compile(r"(결론|판단|권고|총평|우선|적합|선택)")
# 접힘 표지 — gpt 판독물에서 뽑은 것에 제미나이·하이쿠 판독물이 지목한 것을 더했다
TAILS = ["단,", "다만", "반면", "그러나", "하지만", "단점",
         "하나,", "있으나", "있지만", "겠지만", "불구하고"]
TAIL = re.compile("(" + "|".join(re.escape(t) for t in TAILS) + ")")

# 이름표로 접는 자리 — 하이쿠 판독물이 지목한 것이다.
# 「접속사로 접는가」만 세면 하이쿠가 덜 접는 것처럼 보인다. 자리는 있는데 말이 다르다.
LABELS = ["주의사항", "고려사항", "보완필요", "보완점", "유보", "제약사항",
          "미검증", "한계", "리스크", "위험요소", "확인사항", "선행 조건", "전제조건"]
LABEL = re.compile("(" + "|".join(re.escape(t) for t in LABELS) + ")")


def 판모으기():
    rows = []
    for m in MOD:
        for p in sorted((R / "runs" / m).glob("*/run_*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            vs = d.get("value_set_id") or d.get("value_set") or ""
            sc = d.get("script") or ""
            fam = ("A/B" if vs in ("A", "B")
                   else "신념" if vs.startswith("wonchik_")
                   else "올세트" if vs.startswith(("all_", "allb1_")) else None)
            cond = sc if sc in ("C0", "C1", "C2") else ("pbw" if sc.startswith("pbw_") else None)
            ns = d.get("notes") or []
            if not fam or not cond or len(ns) < 3:
                continue
            rows.append(dict(모델=m, 갈래=fam, 각본=cond, 수첩=ns[:3],
                             판=p.name, 재료=p.parent.name))
    return rows


def 세기(rows):
    표 = {}
    for m in MOD:
        sub = [r for r in rows if r["모델"] == m]
        장 = [n for r in sub for n in r["수첩"]]
        표[m] = dict(
            판=len(sub), 장=len(장),
            뼈대셋다=sum(1 for r in sub if all(
                CONC.search(n[:60]) and NUM.search(n) and TAIL.search(n) for n in r["수첩"])),
            머리결론=sum(1 for n in 장 if CONC.search(n[:60])),
            번호=sum(1 for n in 장 if NUM.search(n)),
            꼬리=sum(1 for n in 장 if TAIL.search(n)),
            n1n2=sum(1 for r in sub if r["수첩"][0] == r["수첩"][1]),
            n2n3=sum(1 for r in sub if r["수첩"][1] == r["수첩"][2]),
            닮음=(st.mean(difflib.SequenceMatcher(None, r["수첩"][0], r["수첩"][2]).ratio()
                         for r in sub) if sub else 0.0),
            번호사라짐=sum(1 for r in sub
                       if NUM.search(r["수첩"][0]) and not NUM.search(r["수첩"][2])),
            번호생김=sum(1 for r in sub
                      if NUM.search(r["수첩"][2]) and not NUM.search(r["수첩"][0])),
            글자중앙=(st.median(len(n) for n in 장) if 장 else 0),
            글자최대=max((len(n) for n in 장), default=0),
            초과450=sum(1 for n in 장 if len(n) > 450),
            표지=dict(collections.Counter(t for n in 장 for t in TAILS if t in n)),
            이름표=sum(1 for n in 장 if LABEL.search(n)),
            접힘아무거나=sum(1 for n in 장 if TAIL.search(n) or LABEL.search(n)),
            이름표낱말=dict(collections.Counter(t for n in 장 for t in LABELS if t in n)),
        )
    return 표


def 갈래별(rows):
    d = collections.defaultdict(collections.Counter)
    for r in rows:
        a = d[(r["모델"], r["갈래"], r["각본"])]
        a["판"] += 1
        a["장"] += 3
        a["번호"] += sum(1 for n in r["수첩"] if NUM.search(n))
        a["꼬리"] += sum(1 for n in r["수첩"] if TAIL.search(n))
        a["머리결론"] += sum(1 for n in r["수첩"] if CONC.search(n[:60]))
        a["n2n3"] += (r["수첩"][1] == r["수첩"][2])
        a["글자"] += sum(len(n) for n in r["수첩"])
    return d


def 물린자(rows):
    """쓰지 않는 자 — 기록으로만 남긴다. 눈검사와 어긋났다."""
    mats = {}
    for p in glob.glob(str(R / "materials" / "*.json")):
        x = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        if x.get("issue_id"):
            mats[x["issue_id"]] = x

    def 앞선것(n, opts):
        머리 = n[:90]
        pos = [(머리.find(o), o) for o in opts if o in 머리]
        return min(pos)[1] if pos else None

    out = {}
    for m in MOD:
        읽힘 = 뒤집힘 = 0
        for r in (x for x in rows if x["모델"] == m):
            mat = mats.get(r["재료"])
            if not mat:
                continue
            이름 = [x for x in (앞선것(n, mat["options"]) for n in r["수첩"]) if x]
            if len(이름) >= 2:
                읽힘 += 1
            if len(set(이름)) > 1:
                뒤집힘 += 1
        out[m] = dict(뒤집힘=뒤집힘, 읽힘=읽힘)
    return out


W = []


def w(s=""):
    print(s)
    W.append(s)


def pct(k, n):
    return f"{k / n * 100:.0f}%" if n else "—"


def main():
    rows = 판모으기()
    if not rows:
        sys.exit(f"판을 못 찾았다. PC_ROOT={R} 가 맞나.")
    표 = 세기(rows)
    갈 = 갈래별(rows)
    물 = 물린자(rows)

    w("# 수첩 모양 — 세 모델 전량 (2026-09-03)")
    w("")
    w("> 기계 산출물. `tools/shape.py` 가 쓴다. 손으로 고치지 마라.")
    w(f"> 판 {len(rows)} · 수첩 {len(rows) * 3}장")
    w("")
    w("**이 자는 gpt 무늬로 지어졌다.** 다른 모델 수치는 「gpt 틀을 얼마나 따르나」로 읽어라 —")
    w("「그 모델이 무엇을 하나」는 눈으로 읽은 `READ_*.md` 가 답한다. 독스트링 참조.")

    w("\n## 1. 모델별\n")
    w("| 모델 | 판 | 뼈대 셋 다 | 머리에 결론 | 번호 목록 | 꼬리 표지 |"
      " 수첩1=2 | 수첩2=3 | 첫끝 닮음 | 번호 사라짐 | 번호 생김 |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for m in MOD:
        a = 표[m]
        n, L = a["판"], a["장"]
        w(f"| {NAME[m]} | {n} | {pct(a['뼈대셋다'], n)} | {pct(a['머리결론'], L)} |"
          f" {pct(a['번호'], L)} | {pct(a['꼬리'], L)} | {pct(a['n1n2'], n)} |"
          f" {pct(a['n2n3'], n)} | {a['닮음'] * 100:.0f}% |"
          f" {a['번호사라짐']} | {a['번호생김']} |")

    w("\n## 2. 접힘 표지 — 낱말별 (수첩 장 단위, 겹쳐 셈)\n")
    w("| 표지 | " + " | ".join(NAME[m] for m in MOD) + " |")
    w("|---|" + "---:|" * len(MOD))
    for t in TAILS:
        row = [표[m]["표지"].get(t, 0) for m in MOD]
        if not any(row):
            continue
        칸 = " | ".join(f"{v} ({pct(v, 표[m]['장'])})" for v, m in zip(row, MOD))
        w(f"| `{t}` | " + 칸 + " |")
    w("")
    w("**낱말로 접힘을 세는 자는 모델을 넘으면 못 쓴다.** 위 표가 그 근거다.")

    w("\n## 3. 글자 — 500자 예산\n")
    w("| 모델 | 중앙 | 최대 | 450자 초과 |")
    w("|---|---:|---:|---:|")
    for m in MOD:
        a = 표[m]
        w(f"| {NAME[m]} | {a['글자중앙']:.0f} | {a['글자최대']} |"
          f" {a['초과450']} / {a['장']} = {pct(a['초과450'], a['장'])} |")
    w("")
    w("`ALL34_RESULT` §1-2 의 「500자가 병목」 정정 근거다. gpt 는 예산 근처에 안 간다.")

    w("\n## 4. 갈래·각본별\n")
    w("| 모델 | 갈래 | 각본 | 판 | 글자 | 번호 | 꼬리 | 머리에 결론 | 수첩2=3 |")
    w("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for k in sorted(갈, key=lambda x: (MOD.index(x[0]), x[1], x[2])):
        a = 갈[k]
        n, L = a["판"], a["장"]
        w(f"| {NAME[k[0]]} | {k[1]} | {k[2]} | {n} | {a['글자'] / L:.0f} |"
          f" {pct(a['번호'], L)} | {pct(a['꼬리'], L)} | {pct(a['머리결론'], L)} |"
          f" {pct(a['n2n3'], n)} |")

    w("\n## 5. 쓰지 않는 자 — 기록으로만\n")
    w("첫 90자에서 어느 선택지가 먼저 불리는지로 「라운드 사이 입장 뒤집힘」을 재 봤다.")
    w("")
    w("| 모델 | 뒤집힘 / 읽힘 | 몫 |")
    w("|---|---:|---:|")
    for m in MOD:
        a = 물[m]
        w(f"| {NAME[m]} | {a['뒤집힘']} / {a['읽힘']} | {pct(a['뒤집힘'], a['읽힘'])} |")
    w("")
    w("**이 수치는 안 쓴다.** 같은 구간을 눈으로 읽은 판독물 둘이 압박 없는 판에서")
    w("0/20 을 봤다. 「A보다 B」 문형을 자가 잘못 읽은 것이다. 지우지 않고 남겨 둔다.")

    (H / "SHAPE_3MODEL.md").write_text("\n".join(W) + "\n", encoding="utf-8")
    (H / "SHAPE_3MODEL.json").write_text(json.dumps(dict(
        판수=len(rows), 장수=len(rows) * 3,
        모델별=표,
        갈래별={"|".join(k): dict(v) for k, v in 갈.items()},
        안쓰는자_입장뒤집힘=물,
    ), ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n→ SHAPE_3MODEL.md · SHAPE_3MODEL.json 썼다.")


if __name__ == "__main__":
    main()
