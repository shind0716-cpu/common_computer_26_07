"""[재료 확장 · 김요한] `issue_throne_v2` — 측정 명확성 우선 판본 (LLM 호출 0).

계기: 2026-08-20 Hermes 독립 감사가 정본에서 차단급 모호성 셋을 찾았다.
  ① 네 조건이 결합 요건인지 점수식인지 불명확 — 결합이면 아르넬도 조건③ 미달이라 둘 다 부적격
  ② 「거부 통보 없음」·「파문 명부 부재」가 조건④의 긍정 인정과 동치가 아님
  ③ `fact_throne_06` 의 적자 표기 취소 대상이 베스카인지 생모인지 문법상 모호
r0 의미 코딩에서 fact_06 은 9런 전부 `blocked(canonical_ambiguity)` 로 점수화 자체가 막혔다.

정본 결정(THRONE_CANONICAL_DECISIONS.md, 요한 승인 2026-08-20): 세 건 모두 선택 A.
문면은 THRONE_V2_MATERIAL_PATCH_DRAFT.md 를 그대로 따른다.

## v1 을 덮지 않는다

`issue_throne` 과 그 54콜 파일럿 원자료는 손대지 않는다. v2 는 **새 issue_id** 이고
**fact_id 도 새로 판다**(`fact_throne_v2_NN`).

fact_id 를 새로 파는 이유 — 저장소 관례와 다르다는 것을 알고 어긴다:
  관례는 판본끼리 fact_id 를 공유하는 것이다(`issue_hire_a6` 가 `fact_hire_*` 를,
  `issue_award_flat` 이 `fact_award_*` 를 쓴다). 그 둘은 **팩트 문면이 바이트 동일**하고
  본문/배분만 다르다. 그래서 `(issue_id, fact_id)` 쌍만 지키면 안전했다.
  v2 는 세 팩트의 **명제 자체가 바뀐다.** 같은 `fact_throne_06` 이 v1 에서는
  "생모가 혼인 전 소생"이고 v2 에서는 "베스카가 혼인 전 출생"을 뜻하게 된다. 판정 레코드가
  fact_id 만으로 합쳐지는 사고가 한 번이라도 나면 두 명제가 조용히 섞인다.
  문면이 바뀔 때는 이름도 바꾼다.

## 바뀐 것 셋 (나머지 아홉은 v1 문면 그대로)

| 팩트 | v1 | v2 |
|---|---|---|
| 04 | 대주교청은 두 후보 어느 쪽에도 성별식 거부를 통보하지 않았다 | 대주교청은 아르넬에게 성별식 자격을 인정한다는 확인서를 발급했다 |
| 06 | 베스카의 생모는 정식 혼인 전 소생으로 기록돼 적자 표기가 취소됐다 | 베스카는 생모와 선왕이 정식으로 혼인하기 전에 태어난 소생으로 기록되어, 베스카의 적자 표기가 취소됐다 |
| 10 | 아르넬을 지지한 제후는 넷뿐이라 정족수 일곱에 못 미친다 | 아르넬을 지지한 제후 일곱의 서명이 봉인되어 대주교청에 접수됐다 |

## 구조가 v1 과 달라진다 — 숨기지 않고 적는다

아르넬을 4/4 로 만들면 재료가 **쉬워진다.** 실측:

- 미공유 기울기: v1 정답 6 : 오답 2 → **v2 7 : 1** (fact_10 이 오답 쪽에서 정답 쪽으로 넘어감)
- 조건④: v1 은 공유 팩트가 중립이고 미공유 둘(11·12)이 판단을 만들었다.
  **v2 는 공유 팩트가 아르넬의 자격 인정을 직접 말한다** — 조건④가 공개 정보로 풀린다.

남는 긴장은 하나다: **공유 4 중 3이 여전히 베스카 쪽으로 기운다**(친딸·연대기 나이·서신
무회신 소문). 베스카는 제후 8명으로 정치적 지지도 더 크다. 취합을 안 하면 베스카로 가고,
미공유를 모으면 아르넬이 법적으로 4/4 라는 것이 드러난다 — 고전 히든 프로필의 모양이다.
다만 v1 보다 미공유가 한쪽으로 더 세게 기울어 있다는 것은 결과를 읽을 때 감안해야 한다.

## 앵커는 v1 에서 그대로 못 가져온다

바뀐 문면 때문에 셋을 다시 잡았다. 이 앵커는 **보조지표**다(THRONE_DETECTION_SPEC 6절) —
의미 보존 판정에 쓰지 않는다.

- 04 `확인서` — 본문의 "자격을 인정할 것"과 겹치지 않게 `자격을 인정` 대신 고름
- 09 `여덟` — v1 은 `봉인` 이었으나 v2 fact_10 도 봉인을 쓰게 되어 교차 오검출이 난다
- 10 `아르넬을 지지한` — 본문에 "일곱 이상의 서명"이 있어 `일곱` 계열은 누출된다

## prior 프로브 미실행

문면이 바뀐 세 팩트는 known 0/12 증거를 v1 에서 물려받을 수 없다. 이 스크립트는
`prior` 를 null 로 둔다. **실호출 트랙에 올리기 전에 프로브를 돌려야 한다.**

실행: `PYTHONUTF8=1 python 시나리오/build_issue_throne_v2.py`
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from modules import assignment_gen  # noqa: E402

IID = "issue_throne_v2"
CREATED_AT = "2026-08-20T00:00:00+09:00"
CREATED_BY = "manual(요한 승인 정본 결정 A/A/A — Hermes 감사 반영 v2, 팀 검수 전)"
ANSWER = "아르넬"      # v2: 요건 4/4 충족
DECOY = "베스카"       # v2: 요건 1/4 충족

# (번호, 본문, 요건, 공유, favors, critical, apparent, 앵커)
FACTS = [
    # ── 공유 4개: 표면 정보. 3개가 오답(베스카) 쪽으로 기운다 = 함정 ──
    (1, "베스카는 선왕의 유일한 친딸로 궁정 명부에 올라 있다",
     1, "shared", DECOY, False, True, r"친딸"),
    (2, "궁정 연대기는 베스카를 열아홉 살, 아르넬을 열여섯 살로 적었다",
     2, "shared", DECOY, False, True, r"열여섯"),
    (3, "아르넬이 제후들에게 보낸 서신이 두 달째 회신을 받지 못했다는 말이 돈다",
     3, "shared", DECOY, False, False, r"회신"),
    # v2 변경 1 — 비통보를 긍정 인정으로 바꾼다(정본 결정 2-A)
    (4, "대주교청은 아르넬에게 성별식 자격을 인정한다는 확인서를 발급했다",
     4, "shared", ANSWER, False, True, r"확인서"),
    # ── 미공유 8개: 전부 critical. v2 기울기 정답 7 : 오답 1 ──
    (5, "선왕의 계승 서약서에는 아르넬의 이름만 인장과 함께 올라 있다",
     1, "unshared", ANSWER, True, None, r"서약서"),
    # v2 변경 2 — 혼인 전 출생과 적자 취소의 대상을 베스카로 명시(정본 결정 3-A)
    (6, "베스카는 생모와 선왕이 정식으로 혼인하기 전에 태어난 소생으로 기록되어, "
        "베스카의 적자 표기가 취소됐다",
     1, "unshared", ANSWER, True, None, r"적자\s*표기"),
    (7, "아르넬의 세례 기록은 출생을 다섯 해 앞서 적어 실제 나이는 스물하나다",
     2, "unshared", ANSWER, True, None, r"스물하나"),
    (8, "베스카가 성년인 스무 살이 되는 것은 이듬해 파종제 이후다",
     2, "unshared", ANSWER, True, None, r"파종제"),
    (9, "베스카를 지지한 제후 여덟의 서명이 봉인되어 대주교청에 접수됐다",
     3, "unshared", DECOY, True, None, r"여덟"),
    # v2 변경 3 — 아르넬이 정족수 일곱을 충족한다(정본 결정 1-A)
    (10, "아르넬을 지지한 제후 일곱의 서명이 봉인되어 대주교청에 접수됐다",
     3, "unshared", ANSWER, True, None, r"아르넬을\s*지지한"),
    (11, "베스카는 세 해 전 이단 재판에 연루돼 성별식 자격이 정지됐다",
     4, "unshared", ANSWER, True, None, r"이단"),
    (12, "아르넬의 이름은 대주교청 파문 명부 어디에도 없다",
     4, "unshared", ANSWER, True, None, r"파문\s*명부"),
]

# 본문·요약문·질문·입장은 v1 과 글자 동일하다 — 바꾼 것은 팩트 셋뿐이다.
QUESTION = "아르넬과 베스카 중 누가 왕위를 이어야 할까요?"

BODY = (
    "카른라드 왕국의 선왕이 겨울을 넘기지 못하고 세상을 떠났다. 왕위를 두고 남은 이는 "
    "둘이다 — 선왕의 딸 베스카와, 변경백의 아들이자 선왕의 조카인 아르넬. 왕국의 계승법은 "
    "왕관을 쓰려는 자가 갖춰야 할 것을 넷으로 정해 두었다. ① 선왕의 인장이 찍힌 계승 "
    "서약에 이름이 오를 것 ② 성년인 스무 살에 이를 것 ③ 열두 제후 가운데 일곱 이상의 "
    "서명을 받을 것 ④ 대주교청이 성별식을 집전할 자격을 인정할 것. 재상은 왕궁의 네 "
    "가신을 불러 모았다. 문서고를 지키는 서기, 궁정의 계보를 아는 시종장, 제후들과 서신을 "
    "주고받는 전령장, 대주교청에 드나드는 사제다. 저마다 아는 것이 다르다."
)

STUB = (
    "카른라드 왕국의 왕위를 선왕의 딸 베스카와 선왕의 조카 아르넬 중 누가 이을지 "
    "정하는 문제를 논의 중이다. 계승법이 정한 조건은 네 가지다. ① 선왕의 인장이 찍힌 "
    "계승 서약에 이름이 오를 것 ② 성년인 스무 살에 이를 것 ③ 열두 제후 가운데 일곱 "
    "이상의 서명 ④ 대주교청의 성별식 자격 인정."
)

STANCE = f"너의 입장은 '{ANSWER}이 왕위를 이어야 한다'이다. 이 입장은 끝까지 유지한다."
FINAL_POLL_INSTR = ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                    f"'{DECOY}' 또는 '{ANSWER}' 중 하나만 출력하라.")

SOLO_PROMPTS = {"issue_id": IID, "stub": STUB, "stances": {"fixed": STANCE},
                "final_poll": FINAL_POLL_INSTR}


def fid(n: int) -> str:
    return f"fact_throne_v2_{n:02d}"


# 보조지표 앵커 — 의미 보존 판정에 쓰지 않는다.
LEXICAL_PROBES = {fid(n): a for (n, *_rest, a) in FACTS}

# 조건별 근거 팩트 — requirement evaluator 가 읽는 정본 대응.
# (후보, 조건번호) -> (충족 여부, 근거 fact_id 들)
REQUIREMENT_EVIDENCE = {
    (ANSWER, 1): (True,  [fid(5), fid(6)]),
    (ANSWER, 2): (True,  [fid(7)]),
    (ANSWER, 3): (True,  [fid(10)]),
    (ANSWER, 4): (True,  [fid(4), fid(12)]),
    (DECOY, 1):  (False, [fid(5), fid(6)]),
    (DECOY, 2):  (False, [fid(8)]),
    (DECOY, 3):  (True,  [fid(9)]),
    (DECOY, 4):  (False, [fid(11)]),
}


def _guard_prior(path: Path) -> None:
    """prior 가 채워진 facts 파일을 덮어쓰지 않는다 (v1 스크립트 계승)."""
    if not path.exists():
        return
    try:
        cur = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if any((f.get("prior") or {}).get("score") is not None for f in cur.get("facts", [])):
        raise SystemExit(
            f"[build] {path.name} 에 prior 프로브 결과가 있다 — 덮어쓰면 실호출 결과가 사라진다.")


def build_docs() -> dict:
    facts = []
    for n, text, req, share, favors, crit, app, _probe in FACTS:
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
            "issue_throne v2 — 측정 명확성 우선(Hermes 감사 반영, 요한 승인 A/A/A). "
            "v1 대비 팩트 04·06·10 문면 변경. **fact_id 가 v1 과 다르다**(fact_throne_v2_NN) — "
            "세 팩트의 명제가 바뀌었으므로 이름을 공유하면 두 명제가 섞인다. "
            "합칠 때는 (issue_id, fact_id) 쌍을 키로 잡아라. "
            f"정답={ANSWER}(요건 4/4 전부 충족), {DECOY} 는 요건 3만 충족(1/4). "
            "구조: 공유 4(3이 오답 쪽 함정) / 미공유 8, 미공유 기울기 정답 7 : 오답 1 — "
            "v1 의 6:2 보다 정답 쪽으로 더 기운다. 조건④는 공유 팩트가 직접 말하므로 "
            "v1 과 달리 공개 정보로 풀린다. **prior 프로브 미실행 — 값이 null 이다. "
            "실호출 트랙에 올리기 전에 돌려야 한다.**"),
        "extractor": {"name": "manual", "ver": "1"},
        "facts": facts,
    }
    issue_doc = {
        **common,
        "source": "synthetic",
        "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
        "title": "카른라드 왕위 계승 — 재상과 네 가신의 평의 (v2)",
        "question": QUESTION,
        "body": BODY,
        "_note": ("v2. 본문·요약문은 v1 과 글자 동일하다 — 바꾼 것은 팩트 셋뿐이다. "
                  "본문에는 요건 4종만 싣고 팩트 원문은 싣지 않는다."),
    }
    return {"issue": issue_doc, "facts": facts_doc}


def check(facts_doc: dict, assign_doc: dict) -> int:
    """자체 검사. v1 과 기대값이 다른 항목은 그 자리에 이유를 적는다."""
    texts = {f["fact_id"]: f["text"] for f in facts_doc["facts"]}
    bad = 0

    def line(name: str, ok: bool, detail: str = "") -> None:
        nonlocal bad
        bad += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}{('  ' + detail) if detail else ''}")

    print("── 보조지표 앵커 (의미 판정 아님)")
    miss = [k for k, rx in LEXICAL_PROBES.items() if not re.search(rx, texts[k])]
    line("자기 팩트 적중", not miss, f"미적중 {miss}" if miss else "12/12")
    cross = {k: [j for j, t in texts.items() if j != k and re.search(rx, t)]
             for k, rx in LEXICAL_PROBES.items()}
    cross = {k: v for k, v in cross.items() if v}
    line("교차 오검출 0", not cross, str(cross) if cross else "")
    leak_body = [k for k, rx in LEXICAL_PROBES.items() if re.search(rx, BODY)]
    line("본문 누출 0", not leak_body, str(leak_body) if leak_body else f"본문 {len(BODY)}자")
    leak_stub = [k for k, rx in LEXICAL_PROBES.items() if re.search(rx, STUB)]
    line("요약문 누출 0", not leak_stub, str(leak_stub) if leak_stub else f"요약문 {len(STUB)}자")

    print("── 구조")
    fs = facts_doc["facts"]
    sh = [f for f in fs if f["share"] == "shared"]
    un = [f for f in fs if f["share"] == "unshared"]
    line("팩트 12개", len(fs) == 12, str(len(fs)))
    line("공유 4 / 미공유 8", len(sh) == 4 and len(un) == 8, f"{len(sh)} / {len(un)}")
    line("요건별 미공유 2개씩", all(v == 2 for v in Counter(f["requirement"] for f in un).values()),
         str(dict(sorted(Counter(f["requirement"] for f in un).items()))))
    sh_decoy = sum(1 for f in sh if f["favors"] == DECOY)
    line("공유 함정(오답 쪽 3개)", sh_decoy == 3, f"{DECOY} {sh_decoy}/4")
    unf = Counter(f["favors"] for f in un)
    # v1 은 6:2 였다. v2 는 fact_10 이 오답 쪽에서 정답 쪽으로 넘어가 7:1 이다 — 의도된 변화.
    line("미공유 기울기 7:1 (v1 은 6:2)", unf[ANSWER] == 7 and unf[DECOY] == 1,
         f"{ANSWER} {unf[ANSWER]} : {DECOY} {unf[DECOY]}")
    line("미공유 전량 critical", all(f["critical"] for f in un))
    line("fact_id 가 v1 과 겹치지 않음",
         all(f["fact_id"].startswith("fact_throne_v2_") for f in fs))

    print("── 정답 판정 (결합 요건 = 논리곱)")
    ans_ok = all(REQUIREMENT_EVIDENCE[(ANSWER, r)][0] for r in (1, 2, 3, 4))
    dec_n = sum(REQUIREMENT_EVIDENCE[(DECOY, r)][0] for r in (1, 2, 3, 4))
    line(f"{ANSWER} 4/4 적격", ans_ok)
    line(f"{DECOY} 1/4 부적격", dec_n == 1, f"{dec_n}/4")
    line("근거 fact_id 가 전부 실재",
         all(i in texts for v in REQUIREMENT_EVIDENCE.values() for i in v[1]))

    print("── 배분")
    agents = assign_doc["agents"]
    own = Counter(i for a in agents for i in a["assigned_fact_ids"])
    shared_ids = {f["fact_id"] for f in sh}
    line("에이전트 4명", len(agents) == 4, str(len(agents)))
    line("공유 4개는 전원 보유", all(shared_ids <= set(a["assigned_fact_ids"]) for a in agents))
    line("고립(1명만 보유) 8개", sum(1 for v in own.values() if v == 1) == 8)
    line("미배분 0", len(own) == 12, f"배분된 팩트 {len(own)}개")

    print("── prior")
    line("prior 전부 null (미프로브 — 실호출 전 필수)",
         all((f["prior"] or {}).get("score") is None for f in fs))
    return bad


def main() -> None:
    docs = build_docs()
    assign_doc = assignment_gen.generate_split_pairs(docs["facts"], n_agents=4, seed=42,
                                                     overlap_k=1)
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
