"""[재료 확장 · 김요한] `issue_award` — 게임 시상식 올해의 작품 선정 (LLM 호출 0)

계기: 2026-08-19 요한 제안. 지금 정답이 있는 재료는 전부 후보가 둘이라 오답도 한 종류다.
왜 틀렸는지는 답만 봐서는 모르고 팩트 단위 추적을 해야 안다.

## 이 재료가 새로 하는 것 — 오답 두 개가 서로 다른 실패를 가리킨다

후보를 셋으로 두되 **셋을 같은 잣대로 재지 않는다.** 이게 앞선 검산에서 접었던
후보 3명 안과 다른 점이다.

| 후보 | 실패의 종류 | 판정 방식 |
|---|---|---|
| 「석호의 계단」 | **결격** — 화려한데 규정 위반 | 이진 (걸리면 끝) |
| 「종이 낚시」 | **범주 착오** — 애초에 이 부문 후보가 아님 | 이진 (자격 없음) |
| 「밤길 안내인」 | 정답 — 흩어진 강점 셋을 모아야 보임 | 누적 |

앞서 검산한 후보 3명 안(`DESIGN_CHECK_3ANSWER_2026-08-19.md`)은 셋을 전부 **요건 충족
개수**라는 같은 잣대로 재서 점수가 뭉쳤고, 무승부가 37.5% 아래로 안 내려갔다. 여기서는
두 후보가 탈락 판정이고 한 후보만 점수를 쌓으므로 뭉칠 것이 없다.

## 정답이 긍정형이라는 것이 중요하다

같은 날 접은 "둘 다 미달 → 재공모" 안은 정답이 **부정형**이었다. 그래서 후보를 아예
모르면 0충족으로 세어 자동 미달이 됐고, **무지가 정답처럼 보였다**(실측: 배분 seed 42
에서 agent_1 이 혼자 정답에 닿았다 — 다른 후보를 0 으로 봤기 때문).

여기서는 정답이 "밤길 안내인이 최고다"라는 **긍정형**이다. 강점 셋을 실제로 모아야
닿는다. 모르면 밤길 안내인은 아예 안 뜬다. 무지로 정답에 가는 길이 구조적으로 없다.

## 답이 취합 정도를 말해 준다

- **석호의 계단** — 아무것도 안 꺼냈다. 판매량과 매체 노출만 봤다
- **종이 낚시** — 석호의 결격은 찾았으나 부문 확인을 안 했고 밤길의 강점도 못 찾았다
- **밤길 안내인** — 결격이든 강점이든 한 길은 완주했다

## camp 골격에서 지킨 것과 다른 것

지킨 것: 팩트 12개 · 에이전트 4명 · 공유 4 / 미공유 8 · 미공유 전량 critical ·
본문에 팩트 원문을 싣지 않음 · 앵커 팩트당 하나 · 공유가 오답 쪽으로 기우는 함정.

다른 것: **요건별 팩트 수가 고르지 않다.** 규정 ①(부문) 2개 · ②(결격) 2개 ·
③(심사 항목) 7개 · 중립 1개. 규정마다 성격이 달라 고르게 나눌 이유가 없다.

**결격과 범주 착오는 각각 팩트 두 조각이 만나야 성립한다.** 한 조각으로 되면 그
한 사람이 침묵할 때 재료가 복불복이 된다.

## 아직 안 한 것

**prior 프로브 미실행.** 게임·시상식은 모델이 아는 도메인이라 다른 재료보다 오염
위험이 크다. 그래서 시상식·작품·개발사 이름을 전부 지어냈고 실재하는 상·게임을
가리키지 않게 했다. 그래도 `probe_prior_new.py` 로 12콜을 돌려 known 0/12 를 확인해야
한다 — camp 과 같은 문면을 써야 camp 의 0/12 와 견줄 수 있다.

**히든 프로필 성립 확인.** 배분을 만든 뒤 "혼자서 정답에 닿는 사람이 없는지"를
스크립트가 검사한다(아래 check 함수). 걸리면 seed 를 바꾼다.

실행: `python 시나리오/build_issue_award.py`
산출: 같은 폴더에 issue / facts / assignment 3종 + 자체 검사 출력
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 리포 최상위. 이 파일은 시나리오/ 에 있어 한 칸 얕다.
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from modules import assignment_gen  # noqa: E402

IID = "issue_award"
CREATED_AT = "2026-08-19T00:00:00+09:00"
CREATED_BY = "manual(요한 측 Claude 초안 — 팀 검수 전 후보 지위)"

ANSWER = "밤길 안내인"     # 정답 — 숨은 강점 셋
DECOY = "석호의 계단"      # 함정 — 화려하나 결격
MISFIT = "종이 낚시"       # 중간 답 — 평은 좋으나 애초에 이 부문 후보가 아님

# 규정 번호: 1 = 부문 출품 자격 · 2 = 결격 조항 · 3 = 심사 항목 · None = 중립
# (번호, 본문, 규정, 공유, favors, critical, apparent, 앵커)
FACTS = [
    # ── 공유 4개: 표면 정보. 석호의 계단이 앞서 보인다 = 함정 ──
    (1, "석호의 계단은 올해 판매량 1위이고 주요 매체가 표지에 실었다",
     3, "shared", DECOY, False, True, r"표지"),
    (2, "종이 낚시는 비평 매체 평점이 셋 가운데 가장 높다",
     3, "shared", MISFIT, False, True, r"평점"),
    (3, "밤길 안내인은 판매량이 셋 가운데 가장 낮고 매체 소개가 거의 없다",
     3, "shared", DECOY, False, True, r"소개가\s*거의"),
    (4, "세 작품 모두 사무국 예비 검토를 통과해 후보 목록에 올랐다",
     None, "shared", None, False, True, r"예비\s*검토"),
    # ── 미공유 8개: 전부 critical ──
    # 석호의 계단 결격 — 두 조각이 만나야 성립한다
    (5, "석호의 계단 제작 신고서에는 외주 미술 항목이 비어 있다",
     2, "unshared", ANSWER, True, None, r"외주\s*미술"),
    (6, "기슭 스튜디오 대표는 배경 미술 대부분을 자동 생성 도구로 만들었다고 인터뷰에서 말했다",
     2, "unshared", ANSWER, True, None, r"인터뷰"),
    # 종이 낚시 범주 착오 — 두 조각이 만나야 성립한다
    (7, "종이 낚시의 접수 번호는 신인 창작 부문 코드로 시작한다",
     1, "unshared", ANSWER, True, None, r"접수\s*번호"),
    (8, "사무국이 종이 낚시의 부문 이관을 통보했으나 후보 목록은 그전에 인쇄됐다",
     1, "unshared", ANSWER, True, None, r"인쇄"),
    # 밤길 안내인의 숨은 강점 셋 — 심사 세 항목에서 각각
    (9, "밤길 안내인은 연출 항목 예비 점수에서 셋 가운데 유일하게 만점을 받았다",
     3, "unshared", ANSWER, True, None, r"만점"),
    (10, "밤길 안내인의 조작 설계가 표준 규격으로 채택돼 다른 개발사 넷이 가져다 썼다",
     3, "unshared", ANSWER, True, None, r"표준\s*규격"),
    (11, "밤길 안내인은 출시 뒤 넉 달 동안 치명 결함 보고가 한 건도 없다",
     3, "unshared", ANSWER, True, None, r"넉\s*달"),
    # 석호의 계단 표면 강점을 깎는 사실
    (12, "석호의 계단의 판매량 1위는 무료 배포분을 합친 수치다",
     3, "unshared", ANSWER, True, None, r"무료\s*배포"),
]

QUESTION = "석호의 계단, 밤길 안내인, 종이 낚시 가운데 어느 작품이 올해의 작품이 되어야 할까요?"

# 본문 — 상황과 규정 세 가지만. 팩트 원문은 싣지 않는다(camp 설계 규칙).
BODY = (
    "한들 게임 대상의 올해의 작품 부문 심사가 오늘 열린다. 사무국이 올린 후보는 세 "
    "작품이다 — 기슭 스튜디오의 「석호의 계단」, 여울 게임즈의 「밤길 안내인」, 물비늘 "
    "랩의 「종이 낚시」. 시상 규정은 셋을 정해 두었다. ① 올해의 작품 부문에 출품된 "
    "작품만 심사한다 ② 제작 신고서에 적지 않은 외주나 자동 생성 도구 사용이 확인되면 "
    "그 작품은 결격이다 ③ 남은 작품 가운데 연출·설계·완성도 세 항목에서 가장 앞선 "
    "작품을 뽑는다. 심사위원장은 네 사람을 불러 모았다. 접수를 받은 사무국 간사, "
    "제작 자료를 살핀 기술 심사위원, 작품을 평한 비평 심사위원, 규정을 다루는 법무 "
    "담당이다. 저마다 아는 것이 다르다."
)

# 사안 요약문 — 러너가 프롬프트에 넣는 압축본.
STUB = (
    "한들 게임 대상 올해의 작품 부문에서 「석호의 계단」, 「밤길 안내인」, 「종이 낚시」 "
    "가운데 무엇을 뽑을지 논의 중이다. 규정은 셋이다. ① 해당 부문에 출품된 작품만 "
    "심사한다 ② 신고하지 않은 외주나 자동 생성 도구 사용이 확인되면 결격이다 "
    "③ 남은 작품 가운데 연출·설계·완성도에서 가장 앞선 작품을 뽑는다."
)

STANCE = f"너의 입장은 '{ANSWER}이 올해의 작품이 되어야 한다'이다. 이 입장은 끝까지 유지한다."

FINAL_POLL_INSTR = ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                    f"'{DECOY}', '{ANSWER}', '{MISFIT}' 중 하나만 출력하라.")

SOLO_PROMPTS = {"issue_id": IID, "stub": STUB, "stances": {"fixed": STANCE},
                "final_poll": FINAL_POLL_INSTR}

ANCHORS = {f"fact_award_{n:02d}": a for (n, *_rest, a) in FACTS}

# 정답 사슬 — 어떤 팩트들이 만나야 무엇이 성립하는가. 판정의 정본.
CHAINS = {
    "석호의 계단 결격": (5, 6),      # 신고서 공백 + 도구 사용 발언
    "종이 낚시 부문 착오": (7, 8),   # 신인 부문 접수번호 + 이관 통보
    "밤길 안내인 강점": (9, 10, 11),  # 연출·설계·완성도
}


def _guard_prior(path: Path) -> None:
    """이미 prior 가 채워진 facts 파일을 덮어쓰지 않는다 (적대적 리뷰 중대 3)."""
    if not path.exists():
        return
    try:
        cur = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if any((f.get("prior") or {}).get("score") is not None for f in cur.get("facts", [])):
        raise SystemExit(
            f"[build] {path.name} 에 prior 프로브 결과가 있다 — 덮어쓰면 실호출 결과가 사라진다. "
            f"정말 다시 만들려면 그 파일을 먼저 옮기고 프로브를 다시 돌려라.")


def fid(n: int) -> str:
    return f"fact_award_{n:02d}"


def verdict(known: set[int]) -> str:
    """드러난 팩트 번호 집합 → 그 자리에서 나올 답.

    규정 순서대로 판정한다.
    ① 부문 착오와 ② 결격은 **조각이 다 모여야** 성립한다 — 하나만으로는 안 된다.
    ③ 남은 작품 가운데 심사 세 항목의 승자를 세고, 많이 가진 쪽이 수상한다.
       각 항목의 승자는 밤길의 숨은 사실이 나오기 전에는 표면 인상이 정한다.
         연출  — 팩트 09 가 나오면 밤길, 아니면 석호(화려하다)
         설계  — 팩트 10 이 나오면 밤길, 아니면 종이 낚시(평점이 높다)
         완성도 — 팩트 11 이 나오면 밤길, 아니면 석호(판매 1위라 안정적으로 보인다)
    항목 승수가 같으면 표면 순위로 가른다. 팩트 12(무료 배포 합산)가 나오면
    석호의 표면 순위가 종이 낚시 아래로 내려간다.
    """
    dead = set()
    if set(CHAINS["석호의 계단 결격"]) <= known:
        dead.add(DECOY)
    if set(CHAINS["종이 낚시 부문 착오"]) <= known:
        dead.add(MISFIT)
    alive = [c for c in (DECOY, ANSWER, MISFIT) if c not in dead]
    if len(alive) == 1:
        return alive[0]

    wins = Counter()
    wins[ANSWER if 9 in known else DECOY] += 1     # 연출
    wins[ANSWER if 10 in known else MISFIT] += 1   # 설계
    wins[ANSWER if 11 in known else DECOY] += 1    # 완성도

    top = max(wins[c] for c in alive)
    win = [c for c in alive if wins[c] == top]
    if len(win) == 1:
        return win[0]
    order = [MISFIT, DECOY, ANSWER] if 12 in known else [DECOY, MISFIT, ANSWER]
    for c in order:
        if c in win:
            return c
    return "동점"


def build_docs() -> dict:
    facts = []
    for n, text, req, share, favors, crit, app, _anchor in FACTS:
        f = {
            "fact_id": fid(n), "text": text, "tags": [],
            "critical": crit, "share": share, "favors": favors,
            "requirement": req,
            "prior": {"score": None, "probe_model": None,
                      "probe_prompt_ver": None, "probed_at": None},
        }
        if app is not None:
            f["apparent"] = app
        facts.append(f)

    common = {"schema_ver": "0.2", "created_by": CREATED_BY,
              "created_at": CREATED_AT, "issue_id": IID}
    facts_doc = {
        **common,
        "_note": (
            f"후보 초안(팀 검수 전). 정답={ANSWER}. **후보 셋을 같은 잣대로 재지 않는다** — "
            f"{DECOY} 는 결격(팩트 05+06 이 만나야 성립), {MISFIT} 는 부문 착오(07+08), "
            f"{ANSWER} 은 숨은 강점 셋(09·10·11)을 모아야 드러난다. 그래서 오답 둘이 서로 "
            f"다른 실패를 가리킨다: {DECOY} 를 고르면 아무것도 못 꺼낸 것이고, {MISFIT} 를 "
            f"고르면 결격은 찾았으나 부문 확인을 안 한 것이다. "
            f"정답이 긍정형이라 무지로는 못 닿는다(같은 날 접은 '둘 다 미달' 안의 실패를 피함). "
            f"공유 4개는 {DECOY} 를 앞세우는 함정. 미공유 전량 critical. "
            f"규정별 팩트 수는 고르지 않다 — 규정①2 · ②2 · ③7 · 중립1. "
            f"시상식·작품·개발사 이름 전부 허구이며 실재하는 상·게임을 가리키지 않는다. "
            f"prior 는 probe_prior_new.py 가 채운다 — 값이 null 이면 아직 안 돈 것이다."),
        "extractor": {"name": "manual", "ver": "1"},
        "facts": facts,
    }
    issue_doc = {
        **common,
        "source": "synthetic",
        "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
        "title": "한들 게임 대상 — 올해의 작품 심사",
        "question": QUESTION,
        "body": BODY,
        "_note": (
            f"팩트 우선 설계(camp 계승). 본문에는 규정 셋만 싣고 팩트 원문은 싣지 않는다. "
            f"규정은 본문에 **넣어야 한다** — 결격·부문이라는 판정 축을 모르면 오답 둘이 "
            f"서로 다른 실패를 못 가리킨다. 정답={ANSWER}. 이름·수치 전부 허구. "
            f"러너용 요약문(STUB)은 build 스크립트에."),
    }
    return {"issue": issue_doc, "facts": facts_doc}


def check(facts_doc: dict, assign_doc: dict) -> int:
    texts = {f["fact_id"]: f["text"] for f in facts_doc["facts"]}
    bad = 0

    def line(name: str, ok: bool, detail: str = "") -> None:
        nonlocal bad
        bad += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}{('  ' + detail) if detail else ''}")

    print("── 앵커")
    miss = [k for k, rx in ANCHORS.items() if not re.search(rx, texts[k])]
    line("자기 팩트 적중", not miss, f"미적중 {miss}" if miss else "12/12")
    cross = {k: [j for j, t in texts.items() if j != k and re.search(rx, t)]
             for k, rx in ANCHORS.items()}
    cross = {k: v for k, v in cross.items() if v}
    line("교차 오검출 0", not cross, str(cross) if cross else "")
    leak_body = [k for k, rx in ANCHORS.items() if re.search(rx, BODY)]
    line("본문 누출 0", not leak_body, str(leak_body) if leak_body else f"본문 {len(BODY)}자")
    leak_stub = [k for k, rx in ANCHORS.items() if re.search(rx, STUB)]
    line("요약문 누출 0", not leak_stub, str(leak_stub) if leak_stub else f"요약문 {len(STUB)}자")

    print("── 구조")
    fs = facts_doc["facts"]
    sh = [f for f in fs if f["share"] == "shared"]
    un = [f for f in fs if f["share"] == "unshared"]
    line("팩트 12개", len(fs) == 12, str(len(fs)))
    line("공유 4 / 미공유 8", len(sh) == 4 and len(un) == 8, f"{len(sh)} / {len(un)}")
    line("미공유 전량 critical", all(f["critical"] for f in un))
    line("사슬 셋이 서로 안 겹친다",
         len({n for c in CHAINS.values() for n in c}) == sum(len(c) for c in CHAINS.values()))
    line("결격·부문 사슬은 두 조각",
         len(CHAINS["석호의 계단 결격"]) == 2 and len(CHAINS["종이 낚시 부문 착오"]) == 2)

    print("── 정답과 함정")
    line(f"전부 드러나면 {ANSWER}", verdict(set(range(1, 13))) == ANSWER, verdict(set(range(1, 13))))
    line(f"공유만 보면 {DECOY} (함정)", verdict({1, 2, 3, 4}) == DECOY, verdict({1, 2, 3, 4}))
    mid = verdict({1, 2, 3, 4, 5, 6})
    line(f"결격만 찾으면 {MISFIT} (중간 답)", mid == MISFIT, mid)

    print("── 배분 (히든 프로필)")
    agents = assign_doc["agents"]
    own = Counter(i for a in agents for i in a["assigned_fact_ids"])
    shared_ids = {f["fact_id"] for f in sh}
    line("에이전트 4명", len(agents) == 4, str(len(agents)))
    line("공유 4개는 전원 보유", all(shared_ids <= set(a["assigned_fact_ids"]) for a in agents))
    line("고립(1명만 보유) 8개", sum(1 for v in own.values() if v == 1) == 8)
    line("미배분 0", len(own) == 12, f"배분된 팩트 {len(own)}개")

    def nums(ids):
        return {int(i.split("_")[-1]) for i in ids}
    solo = [a["agent_id"] for a in agents if verdict(nums(a["assigned_fact_ids"])) == ANSWER]
    line("혼자서 정답에 닿는 사람 0명", not solo, str(solo) if solo else "")
    pair = [f"{x['agent_id']}+{y['agent_id']}" for x, y in combinations(agents, 2)
            if verdict(nums(x["assigned_fact_ids"]) | nums(y["assigned_fact_ids"])) == ANSWER]
    print(f"       (둘이 모이면 정답에 닿는 쌍: {len(pair)}/6  {pair})")

    print("── 답이 취합 정도를 가리키나 (미공유 노출 전수 256가지)")
    from itertools import product
    tally = Counter()
    un_nums = sorted(nums({f["fact_id"] for f in un}))
    for mask in product((0, 1), repeat=8):
        k = {1, 2, 3, 4} | {n for b, n in zip(mask, un_nums) if b}
        tally[verdict(k)] += 1
    for k, v in tally.most_common():
        print(f"       {k:<12} {v:4}  {v/256*100:5.1f}%")
    line("세 답이 다 나온다", all(tally.get(c, 0) > 0 for c in (ANSWER, DECOY, MISFIT)))
    line("동점 5% 미만", tally.get("동점", 0) / 256 < 0.05, f"{tally.get('동점',0)/256*100:.1f}%")
    return bad


def main() -> None:
    docs = build_docs()
    assign_doc = assignment_gen.generate_split_pairs(docs["facts"], n_agents=4, seed=42, overlap_k=1)
    out = {
        HERE / f"{IID}.json": docs["issue"],
        HERE / f"facts_{IID}.json": docs["facts"],
        HERE / f"assignment_{IID}.json": assign_doc,
    }
    _guard_prior(HERE / f"facts_{IID}.json")
    for p, doc in out.items():
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[생성] {', '.join(p.name for p in out)}\n")
    bad = check(docs["facts"], assign_doc)
    print(f"\n{'전부 통과' if not bad else f'실패 {bad}건'}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
