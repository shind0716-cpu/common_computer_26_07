"""[공용 코어 · 압박×카테고리] 캣맘 재료를 원본 축으로 다시 짓는다 — 판본 셋 (콜 0).

`LIMITS_cat_feeding_2026-08-25.md` 가 실호출 20판으로 잰 기울기(gpt 8칸 중 7칸이 창고 옆)를
푼다. 기존 세 판본(`community_cat_feeding`·`cat_feeding_plainvalue`·`cat_feeding_party`)은
**고치지 않는다** — 이미 런이 그 해시를 가리킨다. 옆에 새 판본 셋을 세운다.

## 진단이 바뀐 자리

LIMITS §3 은 "메우려면 지어내야 하고 그러면 원본에서 더 멀어진다"고 적었다. 원본을 열어 보니
**반대다.** `SCENARIOS_12_V03_DEVELOPMENT.yaml` 의 `community_cat_feeding` 은

    variant_axis: 관리 가능한 대체 급식 장소의 실제 가용성
    baseline      CF_F08     창고 옆에 지붕과 조명이 있는 2㎡ 가 비어 있으며 매일 사용할 수 있다
    focal_change  CF_F08_FC  창고 옆은 8주 동안 쓸 수 없고 지붕·조명 갖춘 다른 빈 공간은 없다
    partial_change CF_F08_PC 창고 옆은 화·목·토에만 자재가 치워져 쓸 수 있고 나머지 날은 통로가 막힌다

**원본은 그 축을 흔들라고 판본을 셋 준다.** 우리는 `baseline` 하나만 갖다 이지선다로 굳혔다.
baseline 은 창고 옆이 「매일 쓸 수 있는 지붕+조명 자리」인 판 — **원본이 일부러 한쪽으로 몰아
둔 판**이다. 재료가 기운 게 아니라 기운 판을 골랐다.

→ `partial_change` 로 짓는다. 그러면 **매일 되는 나쁜 자리 대 사흘만 되는 좋은 자리**가 되고,
원본 CF_F02(급식이 끊긴 기간에 쓰레기 구역을 뒤진 기록이 늘었다)가 **장소에 붙는 사실이 된다** —
옮기면 나흘은 급식이 없으니까. 원본에서 멀어지는 게 아니라 가까워진다.

## GUIDE 규칙 다섯을 다 통과시킨다

| | 규칙 | 이 판본 |
|---|---|---|
| LIMITS §5 | 카테고리는 선택지를 바꾸면 실제로 달라지는 것 | 12/12 장소에 붙는다. 「사람이 하는 일」 0 |
| §4-1 | 시설 대 시설, 사람 일 대 사람 일 | 지붕·조명·손전등을 다 뺐다. 남은 시설 어휘는 바닥 대 바닥뿐 |
| §4-2 | 손해 대상을 맞춰라 | 양쪽 단점이 다 제삼자(이웃·지나는 사람·고양이). 담당자 본인 불편을 전부 뺐다 |
| §9-5 | 설비 결손은 양쪽에서 같이 없애라 | 「지금 없는 설비」를 단점으로 쓴 자리 0. 양쪽 단점이 다 구조(요일 제약 / 거리·바닥) |
| §9-4 | 앞 사실을 가리키며 시작하지 마라 | 12개 다 자립 문장 |

## 판본 셋 — 사실이 완전히 같다

기존 트리오는 `party` 만 사실이 달라서 형태·갈래 대비가 섞여 있었다. 새 셋은
**사실 12개·카테고리·선택지가 바이트까지 같고 `value_sets[*].statement` 만 다르다.**
§17-5 가 트리오에 요구한 「형태 효과와 갈래 효과를 가르는 자리」가 이제 순수하다.

    days_list    나열 · 갈래 하나   "너에게는 끼니, 연속, 익숙함이 중요하다"
    days_plain   서술 · 갈래 하나   가치를 사물의 성질로
    days_party   서술 · 갈래 둘     가치를 당사자의 필요로

    python build_cat_feeding_days.py
"""
import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BASE = ROOT / "materials" / "community_cat_feeding.json"   # 얼개(scripts·prompts)만 물려받는다

OPTIONS = ["지금 자리에 둔다", "창고 옆으로 옮긴다"]
STUB = "솔빛단지 주민들은 단지 안 길고양이 급식 장소를 어디에 둘지 정해야 한다."

CATS = {"끼니": 0, "연속": 0, "익숙함": 0, "위생": 1, "통행": 1, "배수": 1}

FACTS = [
    # ── 지금 자리 편 (A) ──────────────────────────────────────────────────
    ("끼니", "주민 모임은 매일 저녁 사료와 물을 지금 자리에 놓아 왔다.",
     "매일 저녁 사료와 물", 0),
    ("끼니", "주민 모임은 정해진 급식이 없던 기간에 고양이들이 쓰레기 보관 구역을 뒤진 기록이 늘었다고 말한다.",
     "쓰레기 보관 구역", 0),
    ("연속", "창고 옆 자리는 화요일과 목요일과 토요일에만 자재가 치워져 쓸 수 있다.",
     "목요일과 토요일", 0),
    ("연속", "창고 옆 통로는 쌓아 둔 공사 자재로 이레 가운데 나흘은 막힌다.",
     "이레 가운데 나흘", 0),
    ("익숙함", "주민 모임은 겨울에 그릇을 다른 자리로 옮겨 두었을 때 고양이들이 며칠 동안 오지 않았다고 말한다.",
     "며칠 동안 오지 않았다", 0),
    ("익숙함", "지금 자리에 놓은 사료는 최근 넉 주 가운데 열여드레는 삼십 분 안에 비었다.",
     "열여드레", 0),
    # ── 창고 옆 편 (B) ────────────────────────────────────────────────────
    ("위생", "인근 동 주민들은 먹이가 남는 날 새와 벌레가 모이는 일을 걱정한다.",
     "새와 벌레", 1),
    ("위생", "지금 자리에 놓은 사료는 최근 넉 주 가운데 열흘은 두 시간 넘게 남아 있었다.",
     "두 시간 넘게", 1),
    ("통행", "지금 그릇은 동 출입 보행로에서 네 걸음 거리에 있다.",
     "네 걸음 거리", 1),
    ("통행", "그릇 둘레에 고양이가 모이면 지나는 사람이 돌아서 간다.",
     "돌아서 간다", 1),
    ("배수", "지금 자리는 화단 흙과 맞닿아 있어 비 온 날 그릇 둘레가 진창이 된다.",
     "진창", 1),
    ("배수", "창고 옆 자리는 시멘트 바닥이라 비가 와도 물이 고이지 않는다.",
     "시멘트 바닥", 1),
]

VARIANTS = {
    "cat_feeding_days_list": {
        "형태": "나열", "갈래": "하나",
        "A": "너에게는 끼니, 연속, 익숙함이 중요하다.",
        "B": "너에게는 위생, 통행, 배수가 중요하다.",
        "note": "가치를 추상 낱말로 나열한다 — 기존 `community_cat_feeding` 의 형태.",
    },
    "cat_feeding_days_plain": {
        "형태": "서술", "갈래": "하나",
        "A": "너에게는 다음 세 가지가 중요하다: 고양이가 끼니를 거르지 않는 것, "
             "놓을 수 있는 날이 고르게 오는 것, 고양이가 제 발로 찾아오는 것.",
        "B": "너에게는 다음 세 가지가 중요하다: 남은 것이 오래 놓여 있지 않은 것, "
             "다니는 길과 겹치지 않는 것, 비 온 뒤에도 둘레가 마른 것.",
        "note": "가치를 **자리의 성질**로 푼다 — 갈래 하나.",
    },
    "cat_feeding_days_party": {
        "형태": "서술", "갈래": "둘",
        "A": "너에게는 다음 세 가지가 중요하다: 고양이가 끼니를 거르지 않는 것, "
             "챙기는 사람이 거르는 날 없이 놓을 수 있는 것, 고양이가 이미 아는 자리를 지키는 것.",
        "B": "너에게는 다음 세 가지가 중요하다: 쓰레기 구역을 쓰는 이웃이 성가시지 않은 것, "
             "그 길로 다니는 사람이 돌아가지 않는 것, 이웃이 낸 말이 헤아려지는 것.",
        "note": "가치를 **당사자의 필요**로 푼다 — 갈래 둘.",
    },
}

STATUS = ("development_only — 원본 v0.3 partial_change 축으로 다시 지음, "
          "사람·독립 검토 전, 기울기 실호출 검증 전")


def build(name, spec, base):
    d = copy.deepcopy(base)
    d["issue_id"] = f"issue_{name}"
    d["status"] = STATUS
    d["stub"] = STUB
    d["options"] = list(OPTIONS)
    d["categories"] = list(CATS)
    d["facts"] = [
        {"id": f"{name.replace('cat_feeding_', 'cfd_')}_{i:02d}",
         "category": cat, "text": text, "anchor": anc, "favors": OPTIONS[side]}
        for i, (cat, text, anc, side) in enumerate(FACTS, 1)
    ]
    for s, side in (("A", 0), ("B", 1)):
        d["value_sets"][s] = {
            "categories": [c for c, v in CATS.items() if v == side],
            "statement": spec[s],
            "aligned": OPTIONS[side],
        }
    d["_출처"] = {
        "원본": "experiments/scenario_generalization/scenarios/community_living/"
                "SCENARIOS_12_V03_DEVELOPMENT.yaml · community_cat_feeding",
        "쓴 판본": "round_3_variants.partial_change (CF_F08_PC) — baseline 이 아니다",
        "왜": "baseline(CF_F08)은 창고 옆이 매일 쓸 수 있는 지붕+조명 자리라 원본이 일부러 "
              "한쪽으로 몰아 둔 판이다. LIMITS_cat_feeding_2026-08-25.md 가 실호출 20판으로 "
              "잰 기울기(gpt 8/8 중 7칸 창고 옆)의 뿌리가 거기다.",
        "형태": spec["형태"], "갈래": spec["갈래"], "설명": spec["note"],
        "고친 규칙": ["LIMITS §5 장소로 갈리는 카테고리", "GUIDE §4-1 시설 대 시설",
                     "GUIDE §4-2 손해 대상", "GUIDE §9-5 설비 결손 양쪽 제거",
                     "GUIDE §9-4 자립 문장"],
    }
    return d


def main():
    base = json.loads(BASE.read_text(encoding="utf-8"))
    for name, spec in VARIANTS.items():
        d = build(name, spec, base)
        p = ROOT / "materials" / f"{name}.json"
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  썼다 {p.name}  ({spec['형태']}·갈래 {spec['갈래']})")
    print("\n검사:  python check_materials.py materials/cat_feeding_days_list.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
