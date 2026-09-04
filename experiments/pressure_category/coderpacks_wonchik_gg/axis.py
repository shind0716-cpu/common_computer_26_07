# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 대칭축 — 모델 셋 × 가치문 셋을 한 표에. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python axis.py

## 왜 짓나

민옥 9/3 정성 판독 §7 한계에 이렇게 적혀 있다 —

    원칙 조건은 gpt·gemini 에 채점 줄이 없어 판독자 관찰만 있다.

그 두 칸을 오늘 채웠다(`build.py` → 132판 → `combine.py`). 이제 아홉 칸이 다 찬다.

## 보고서 수치를 베끼지 않는다

민옥 보고서에 적힌 값(하이쿠 원칙 3.3 …)을 그대로 옮겨 적으면, 그 값이 어떤
셈으로 나왔는지 확인할 길이 없다. **네 팩의 판독 원본에서 같은 셈으로 다시 뽑는다.**
하이쿠 원칙이 3.30 으로 되나오면 눈금이 맞은 것이고, 그때만 나란히 놓는다.

    가치  coderpacks_haiku_llm_20260902 (하이쿠) · coderpacks_gptgem_llm_20260902 (gpt·제미나이)
    라벨  coderpacks_label_models_20260903 (gpt·제미나이) · coderpacks_label_llm_20260902 (하이쿠)
    원칙  coderpacks_haiku_llm_20260902 cond=belief (하이쿠) · 여기 (gpt·제미나이)

팩마다 칸 이름이 다르다(`n_alive`/`alive`, `in_alive`/`inA`, `pro_final`/`proF`).
`꺼내기()` 가 그걸 한 이름으로 맞춘다 — **값은 안 건드리고 이름만 바꾼다.**

## 읽을 때 조심할 것

- **라벨 압박 칸은 판 수가 다르다** (gpt 48 · 제미나이 30 · 하이쿠 54). 격자가 안 찬
  조건이라 압박 줄은 판 수를 같이 적는다.
- **`in_alive` 는 편식이 아니다.** 민옥 채점기에서 그 칸은 「준 가치 갈래에 든 사실」이고,
  하이쿠 원칙 판은 `aligned` 가 None 인데도 값이 차 있어 정렬답 기준으로 오해하기 쉽다.
  편식은 `pro_final`(마지막 답 편) 하나로만 잰다 - 네 팩에서 정의가 같은 유일한 칸이다.

  까닭을 찾았다. 판독기는 `aa4d44d`(민옥, 2026-09-02, **「신념 라벨링 테스트 추가」**)에서
  태어났고, 그때 축은 **갈래(category)** 였다. 원칙 조건에는 갈래가 없는데도 같은 축을
  쓰려니 `combine.py:39` 가 이렇게 되돌아간다 -

      vcats = set(m['value_sets'][k['value_set']]['categories']) if cond=='AB' else set(GA[k['issue_id']])

  `GA` 는 재료마다 갈래 셋을 손으로 박아 둔 표다. 맞대 보니 **A/B 거울의 한쪽**이다
  (11벌 중 8벌은 A짝 갈래, 3벌은 B짝 갈래와 같다). 그러니 원칙 판의 `in_alive` 는
  「그 판이 받은 가치문의 갈래」가 아니라 **「재료마다 미리 정해 둔 한쪽 갈래」** 이고,
  어느 쪽인지는 재료마다 다르다. 원칙 문장은 갈래를 아예 안 집으므로 이 칸은
  원칙 조건에서 설계된 자가 아니다 - **판독기가 라벨 실험 때 만들어진 자국이다.**
  (민옥 담당 파일이라 안 고친다. 여기 적어 두고 우리는 안 쓴다.)

산출: AXIS.md + 표(stdout)
"""
import json
import os
import pathlib
import statistics

H = pathlib.Path(__file__).resolve().parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))

이름맞춤 = {"alive": "n_alive", "inA": "in_alive", "outA": "out_alive",
          "proF": "pro_final", "conF": "con_final", "id": "item"}
모델맞춤 = {"gemini": "제미나이", "gemini-flash": "제미나이",
          "gpt": "gpt", "claude-haiku": "하이쿠", None: "하이쿠"}


def 꺼내기(경로, 조건, 거르개=None):
    rows = json.loads((R / 경로).read_text(encoding="utf-8"))
    out = []
    for x in rows:
        if 거르개 and not 거르개(x):
            continue
        y = {이름맞춤.get(k, k): v for k, v in x.items()}
        y["모델"] = 모델맞춤.get(y.get("model"), y.get("model"))
        y["조건"] = 조건
        out.append(y)
    return out


def m(g, k, i):
    v = [x[k][i] for x in g if isinstance(x.get(k), list)]
    return round(statistics.mean(v), 2) if v else None


def main():
    행 = (꺼내기("coderpacks_haiku_llm_20260902/JUDGED_rows.json", "가치",
              lambda x: x.get("cond") == "AB")
         + 꺼내기("coderpacks_gptgem_llm_20260902/JUDGED_gptgem_rows.json", "가치")
         + 꺼내기("coderpacks_label_models_20260903/JUDGED_label_models_rows.json", "라벨")
         + 꺼내기("coderpacks_label_llm_20260902/JUDGED_label_rows.json", "라벨")
         + 꺼내기("coderpacks_haiku_llm_20260902/JUDGED_rows.json", "원칙",
                lambda x: x.get("cond") == "belief")
         + 꺼내기("coderpacks_wonchik_gg/JUDGED_wonchik_gg_rows.json", "원칙"))
    for x in 행:
        if "press" not in x:
            x["press"] = x.get("압박") == "압박"

    검산 = [x for x in 행 if x["모델"] == "하이쿠" and x["조건"] == "원칙" and not x["press"]]
    v = m(검산, "n_alive", 2)
    print(f"# 검산 — 하이쿠 원칙 C0 마지막 수첩 = {v}  (민옥 보고서 3.3)")
    if v is None or abs(v - 3.3) > 0.05:
        raise SystemExit("눈금이 안 맞다 — 나란히 놓지 마라.")
    print("# 되나왔다. 아래 표는 네 팩 판독 원본에서 같은 셈으로 다시 뽑은 것이다.\n")

    모델들 = ("gpt", "제미나이", "하이쿠")
    조건들 = ("가치", "라벨", "원칙")
    줄 = []

    def 표(제목, 뽑기, 압박):
        줄.append(f"\n## {제목}\n")
        줄.append("| 모델 | " + " | ".join(조건들) + " |")
        줄.append("|---|" + "---:|" * 3)
        for mo in 모델들:
            칸 = []
            for c in 조건들:
                g = [x for x in 행 if x["모델"] == mo and x["조건"] == c and x["press"] == 압박]
                칸.append("—" if not g else f"{뽑기(g)} <sub>({len(g)})</sub>")
            줄.append(f"| {mo} | " + " | ".join(칸) + " |")

    표("마지막 수첩에 살아남은 사실 (12중) — 압박 없음", lambda g: m(g, "n_alive", 2), False)
    표("마지막 수첩에 살아남은 사실 (12중) — 압박", lambda g: m(g, "n_alive", 2), True)
    표("첫 수첩 (12중) — 압박 없음", lambda g: m(g, "n_alive", 0), False)
    def 편식(g):
        """마지막 답을 편드는 사실 - 반대편 사실. 네 팩에 공통인 단 하나의 자다.

        **`in_alive` 를 여기 쓰면 안 된다.** 민옥 채점기(`combine.py:43`)의 `in_alive` 는
        「준 가치 갈래에 든 사실」이지 「편드는 사실」이 아니다 - 이름이 비슷할 뿐 다른 자다.
        하이쿠 원칙 판은 `aligned` 가 None 인데도 이 칸이 차 있어 더 헷갈린다.
        내가 `coderpacks_wonval_obs` 에서 같은 칸 이름을 정렬답 기준으로 쓴 적도 있다.
        `pro_final`/`con_final` 만 정의가 네 팩에서 같다.

        마지막 답이 선택지 밖이면 민옥 채점기가 None 을 넣는다 - 그 판은 빠진다.
        """
        뒤 = [x for x in g if isinstance(x.get("pro_final"), list)]
        if not 뒤:
            return "-"
        return f"{m(뒤, 'pro_final', 2) - m(뒤, 'con_final', 2):+.2f} <sub>({len(뒤)})</sub>"

    줄.append("\n## 편식 - 마지막 수첩, 마지막 답 편 - 반대편 (각 6중) · 압박 없음\n")
    줄.append("| 모델 | " + " | ".join(조건들) + " |")
    줄.append("|---|" + "---:|" * 3)
    for mo in 모델들:
        줄.append(f"| {mo} | " + " | ".join(
            편식([x for x in 행 if x["모델"] == mo and x["조건"] == c and not x["press"]])
            for c in 조건들) + " |")

    글 = "\n".join(줄)
    print(글)
    (H / "AXIS.md").write_text(
        "# 대칭축 — 모델 셋 × 가치문 셋\n\n"
        "판독 원본 네 팩에서 같은 셈으로 다시 뽑았다. 괄호 안은 판 수다.\n\n"
        "- 편식은 `pro_final`(마지막 답 편) 하나로만 쟀다. 민옥 채점기의 `in_alive` 는\n"
        "  「준 가치 갈래에 든 사실」이라 다른 자다 — 이름만 비슷하고 섞으면 안 된다.\n"
        "- 라벨 압박 칸은 격자가 안 차 판 수가 다르다.\n"
        + 글 + "\n", encoding="utf-8")
    print("\n→ AXIS.md")


if __name__ == "__main__":
    main()
