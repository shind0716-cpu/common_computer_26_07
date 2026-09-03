# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 뒤집힘이 답에 닿나 — 기계 절반. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/flipanswer.py

## 왜 있나

판독물이 「수첩에서 결론이 뒤집혔다」고 한 37판 중 16판에서 최종 답이 되돌아왔다.
그런데 러너를 열어 보니 최종 답이 보는 것은 이것뿐이다 —

    prompt_final = 사안 + 가치문(vspec_later) + **마지막 수첩**

**발화 넷도, 압박 대사도 안 본다.** 그러니 되돌아옴은 모델이 버틴 것이 아니라
설득이 최종 물음까지 안 간 것이다. 다만 수첩은 넘어가 있었으니 물음이 남는다 —

    수첩과 가치문이 어긋날 때 무엇이 이기나.

## 자를 새로 만들지 않는다

앞서 「첫 90자에서 어느 선택지가 먼저 불리나」로 입장을 재려다 눈검사와 어긋나
물렸다(`shape.py` §5). 그 잘못을 되풀이하지 않는다.

여기서 쓰는 것은 **전부 기록된 사실**이다 —

- `aligned` — 가치문이 가리키는 쪽. 러너가 재료에서 읽어 적었다
- `final_poll` — 최종 답. 러너가 형식 반려까지 걸어 두 선택지 중 하나로 받았다
- **뒤집힘 딱지** — 눈이 붙였다(`_FLIPS.json`, 판독물 7개가 짚은 37판)

수첩이 어느 쪽인지를 자로 읽지 않는다. **뒤집힘 딱지가 그 자리를 대신한다.**

## 무엇을 못 말하나

- **뒤집힘 딱지는 뽑힌 20판 안에서만 있다.** 모집단 전체의 뒤집힘은 안 세어 봤다
- 신념 판은 `aligned` 가 없다 — 정렬 여부를 못 잰다. 표에서 뺀다
- 짝지은 대조가 아니다. 같은 조각 안의 두 무리를 견주는 것뿐이다
- **인과가 아니다.** 뒤집힌 판이 원래 다른 판이었을 수 있다

산출: FLIPANSWER.md · FLIPANSWER.json
"""
import json
import os
import math
import pathlib
import collections

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
NAME = {"gpt": "gpt", "gemini-flash": "제미나이", "claude-haiku": "하이쿠"}
ORD = ["gpt", "gemini-flash", "claude-haiku"]

W = []


def w(s=""):
    print(s)
    W.append(s)


def pct(k, n):
    return f"{k / n * 100:.0f}%" if n else "—"


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h) * 100, min(1.0, c + h) * 100


def 모집단():
    """조각을 만들 때와 같은 갈래·각본 분류. 판을 통째로 싣는다."""
    out = collections.defaultdict(list)
    for m in ORD:
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
            if not fam or not cond or len(d.get("notes") or []) < 3:
                continue
            out[(m, fam, cond)].append(dict(
                경로=str(p.relative_to(R)).replace("\\", "/"),
                정렬답=d.get("aligned"), 최종답=d.get("final_poll")))
    return out


def 어긋남(판들):
    """최종 답이 정렬답과 다른 판 / 잴 수 있는 판."""
    잴수있음 = [x for x in 판들 if x["정렬답"] and x["최종답"]]
    다름 = sum(1 for x in 잴수있음 if x["최종답"] != x["정렬답"])
    return 다름, len(잴수있음)


def main():
    지도 = json.loads((H / "SLICE_MAP.json").read_text(encoding="utf-8"))["조각"]
    뒤 = json.loads((H / "_FLIPS.json").read_text(encoding="utf-8"))
    뒤집힘딱지 = collections.defaultdict(set)   # 조각 → {판번호}
    for row in 뒤["rows"]:
        조각 = row["f"][5:]
        for fl in row["flipped"]:
            뒤집힘딱지[조각].add(f"{fl['pan']:02d}")

    pop = 모집단()
    SL = {"01_가치_압박없음": ("A/B", "C0"), "02_가치_편들어": ("A/B", "C1"),
          "03_가치_반대로": ("A/B", "C2"), "04_신념_압박없음": ("신념", "C0"),
          "05_신념_반대로": ("신념", "pbw"), "06_올세트_압박없음": ("올세트", "C0")}

    w("# 뒤집힘이 답에 닿나 — 기계 절반 (2026-09-03)")
    w("")
    w("> 기계 산출물. `tools/flipanswer.py` 가 쓴다. 손으로 고치지 마라.")
    w("> 쓰는 값은 전부 러너가 적어 둔 사실(`aligned`·`final_poll`)이고,")
    w("> 뒤집힘 딱지만 눈이 붙인 것이다. **수첩의 쪽을 자로 읽지 않았다.**")
    w("")
    w("최종 답이 보는 것은 `사안 + 가치문 + 마지막 수첩` 뿐이다 — 발화도 압박 대사도 안 본다.")
    w("(`run_pressure.py` `prompt_final`)")

    # ── 1. 모집단에서 답이 얼마나 어긋나나 ────────────────────────────
    w("\n## 1. 모집단 전체 — 최종 답이 가치문과 어긋난 판\n")
    w("| 모델 | 갈래 | 각본 | 잴 수 있는 판 | 어긋남 | 몫 | 95% 구간 |")
    w("|---|---|---|---:|---:|---:|---|")
    표1 = {}
    for m in ORD:
        for name, k in SL.items():
            판들 = pop.get((m, *k)) or []
            a, n = 어긋남(판들)
            if not n:
                continue
            lo, hi = wilson(a, n)
            표1[f"{m}|{name}"] = dict(어긋남=a, 잼=n)
            w(f"| {NAME[m]} | {k[0]} | {k[1]} | {n} | {a} | **{pct(a, n)}** |"
              f" {lo:.0f}\\~{hi:.0f}% |")
    w("")
    w("신념 판은 `aligned` 가 없어 표에서 빠진다(잴 수 있는 판 0).")

    # ── 2. 뽑힌 20판 안에서 뒤집힌 무리 대 안 뒤집힌 무리 ─────────────
    w("\n## 2. 같은 조각 안에서 — 뒤집힌 판과 안 뒤집힌 판\n")
    w("뒤집힘 딱지는 눈이 붙인 것이고, 뽑힌 20판 안에서만 있다.\n")
    w("| 조각 | 뒤집힘 딱지 | 뒤집힌 판 어긋남 | 안 뒤집힌 판 어긋남 | 차 |")
    w("|---|---:|---:|---:|---:|")
    표2 = {}
    for 조각, 딱지 in sorted(뒤집힘딱지.items()):
        판표 = 지도[조각]["판"]
        뒤판 = [v for kk, v in 판표.items() if kk in 딱지]
        안판 = [v for kk, v in 판표.items() if kk not in 딱지]
        a1, n1 = 어긋남(뒤판)
        a2, n2 = 어긋남(안판)
        if not n1 and not n2:
            w(f"| {조각} | {len(딱지)} | — | — | 못 잼(정렬답 없음) |")
            continue
        차 = (a1 / n1 - a2 / n2) * 100 if n1 and n2 else None
        표2[조각] = dict(뒤=[a1, n1], 안=[a2, n2])
        w(f"| {조각} | {len(딱지)} | {a1}/{n1} = {pct(a1, n1)} |"
          f" {a2}/{n2} = {pct(a2, n2)} |"
          f" {f'{차:+.0f}%p' if 차 is not None else '—'} |")

    # ── 3. 합쳐서 ─────────────────────────────────────────────────────
    w("\n## 3. 합쳐서\n")
    A1 = sum(v["뒤"][0] for v in 표2.values())
    N1 = sum(v["뒤"][1] for v in 표2.values())
    A2 = sum(v["안"][0] for v in 표2.values())
    N2 = sum(v["안"][1] for v in 표2.values())
    l1, h1 = wilson(A1, N1)
    l2, h2 = wilson(A2, N2)
    w("| 무리 | 판 | 최종 답이 가치문과 어긋남 | 몫 | 95% 구간 |")
    w("|---|---:|---:|---:|---|")
    w(f"| 수첩이 뒤집힌 판 | {N1} | {A1} | **{pct(A1, N1)}** | {l1:.0f}\\~{h1:.0f}% |")
    w(f"| 안 뒤집힌 판 | {N2} | {A2} | **{pct(A2, N2)}** | {l2:.0f}\\~{h2:.0f}% |")
    if N1 and N2:
        w(f"\n**차 {(A1/N1 - A2/N2)*100:+.1f}%p**")
        w("")
        w("**다만 이 합계를 그대로 믿지 마라.** 조각마다 기저율이 다르고 뒤집힘 몫도 다르다.")
        w("§2 를 보면 조각별 차가 +100 · +67 · 0 · 0 · −7%p 로 갈리는데,")
        w("**뒤집힘이 가장 많은 조각(하이쿠 가치·반대로 15/20)에서 차가 0이다.**")
        w("합계가 큰 것은 뒤집힘이 드문 조각(제미나이 6/20 · gpt 1/20)이 끌어올린 탓이다.")
        w("조각 안에서 견주는 §2 가 정본이고, §3 은 참고다.")
        w("")
        # 조각 안에서만 견준 뒤 합치기 — 기저율 차이를 안 섞는다
        분자 = 분모 = 0.0
        for v in 표2.values():
            (a1, n1), (a2, n2) = v["뒤"], v["안"]
            if n1 and n2:
                분자 += (a1 / n1 - a2 / n2) * min(n1, n2)
                분모 += min(n1, n2)
        if 분모:
            w(f"조각 안에서만 견주고 작은 쪽 크기로 무게를 주면 **차 {분자/분모*100:+.1f}%p** 다.")

    # ── 4. 못 하는 말 ─────────────────────────────────────────────────
    w("\n## 4. 이 표가 못 하는 말\n")
    w("- **인과가 아니다.** 뒤집힌 판이 원래 다른 성질의 판이었을 수 있다.")
    w("  같은 재료·같은 각본으로 짝지은 대조가 아니다.")
    w("- **뒤집힘 딱지는 뽑힌 20판 안에서만 있다.** §1 의 모집단과 §2 의 분모가 다르다.")
    w("- **신념 판은 못 잰다.** `aligned` 가 없다.")
    w("- 뒤집힘 딱지는 판독물 7개가 짚은 것이고, 대조가 그 판독물들에서")
    w("  어긋남을 잡았다(`_FLIPREAD_CHK.json`). 딱지 자체는 대조가 안 짚었다.")

    (H / "FLIPANSWER.md").write_text("\n".join(W) + "\n", encoding="utf-8")
    (H / "FLIPANSWER.json").write_text(json.dumps(dict(
        모집단=표1, 조각별=표2,
        합=dict(뒤집힘=[A1, N1], 안뒤집힘=[A2, N2]),
    ), ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n→ FLIPANSWER.md · FLIPANSWER.json 썼다.")


if __name__ == "__main__":
    main()
