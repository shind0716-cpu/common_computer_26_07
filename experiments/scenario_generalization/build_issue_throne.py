"""[재료 확장 · 김요한] `issue_throne` — 중세 왕위 계승 시나리오 (LLM 호출 0)

계기: 2026-08-19 중간보고서 리뷰 — *"시나리오 자체에 오버피팅이 되었다고 해도 반박할 수
없다."* 기존 재료가 전부 현대 한국 일상 딜레마(합숙지·채용·경비·차 키·빚·태양광·대학원·
이주)라서, **세계와 어휘가 통째로 다른 재료**를 하나 만든다.

## 골격은 `issue_camp` 을 그대로 베낀다

재료만 바꾸고 나머지를 고정해야 "이 이야기에서만 되는 게 아니다"를 보일 수 있다. 그래서
`facts_issue_camp.json` 의 설계를 항목별로 따른다.

1. **팩트 12개 · 요건 4개.** 요건마다 공유 1 + 미공유 2(후보별 1개씩).
2. **공유 4개는 표면 정보**이고 **3개가 오답 후보 쪽으로 기운다** — 함정. 나머지 1개는 중립.
3. **미공유 8개는 전부 `critical`**, favors 소계는 정답 6 : 오답 2 (camp 과 같은 기울기).
4. **정답은 요건 3/4 충족.** 완벽한 후보가 아니어야 판단이 필요해진다.
5. **본문(`body`)에는 요건 4개만 싣고 팩트 원문을 싣지 않는다.** camp `_note` 의 규칙:
   *"팩트 노출은 배분층 소관 — 본문에 넣으면 2단 미공유 구조가 무너진다."*
   (2026-08-19 실측: `issue_relocate_lite` 는 본문에 12팩트가 전부 들어 있어 토론 판에서
   배분표가 무의미해진다. 그 함정을 여기서는 설계로 피한다.)
6. **앵커는 팩트마다 고유**하고 본문·요약문에 새지 않는다.

## 이 재료가 camp 과 다르게 만드는 것

- 세계: 중세 가상 왕국. 고유명사·제도·단위가 전부 현대 한국어 밖이다.
- 어휘: 「봉인」·「정족수」·「성별식」·「파종제」처럼 일상 대화에 안 나오는 말.
- **불리한 사실의 위치**: camp 은 오답 편 팩트가 목록 앞쪽에 몰려 순서 교락이 남았다
  (중간보고서 §5 ③ 이 탐색에 머문 이유). 여기서는 오답 편 미공유 2개를 목록 중간
  (09·10)에 둔다 — camp 과 같은 자리이므로 교락은 **재현**되고, `--facts-reverse` 로
  뒤집으면 분리된다.

## 아직 안 한 것

**prior 프로브 미실행.** camp 은 팩트 12개를 모델에 물어 "이미 아는 것 0/12"를 확인한 뒤
사연을 썼다(`_note` 의 ms1). 여기 이름·수치는 전부 지어낸 것이지만 그 확인은 실호출이
필요하므로 `prior` 는 null 로 둔다. **실행 전에 프로브를 돌려야 한다.**

실행: `python experiments/scenario_generalization/build_issue_throne.py`
산출: 같은 폴더에 issue / facts / assignment 3종 + 자체 검사 출력
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from modules import assignment_gen  # noqa: E402

IID = "issue_throne"
CREATED_AT = "2026-08-19T00:00:00+09:00"
CREATED_BY = "manual(요한 측 Claude 초안 — 팀 검수 전 후보 지위)"
ANSWER = "아르넬"      # 요건 3/4 충족
DECOY = "베스카"       # 요건 1/4 충족

# (번호, 본문, 요건, 공유, favors, critical, apparent, 앵커)
FACTS = [
    # ── 공유 4개: 표면 정보. 3개가 오답(베스카) 쪽으로 기운다 = 함정 ──
    (1, "베스카는 선왕의 유일한 친딸로 궁정 명부에 올라 있다",
     1, "shared", DECOY, False, True, r"친딸"),
    (2, "궁정 연대기는 베스카를 열아홉 살, 아르넬을 열여섯 살로 적었다",
     2, "shared", DECOY, False, True, r"열여섯"),
    (3, "아르넬이 제후들에게 보낸 서신이 두 달째 회신을 받지 못했다는 말이 돈다",
     3, "shared", DECOY, False, False, r"회신"),
    (4, "대주교청은 두 후보 어느 쪽에도 성별식 거부를 통보하지 않았다",
     4, "shared", None, False, True, r"거부를\s*통보"),
    # ── 미공유 8개: 전부 critical. 정답 6 : 오답 2 ──
    (5, "선왕의 계승 서약서에는 아르넬의 이름만 인장과 함께 올라 있다",
     1, "unshared", ANSWER, True, None, r"서약서"),
    (6, "베스카의 생모는 정식 혼인 전 소생으로 기록돼 적자 표기가 취소됐다",
     1, "unshared", ANSWER, True, None, r"적자"),
    (7, "아르넬의 세례 기록은 출생을 다섯 해 앞서 적어 실제 나이는 스물하나다",
     2, "unshared", ANSWER, True, None, r"스물하나"),
    (8, "베스카가 성년인 스무 살이 되는 것은 이듬해 파종제 이후다",
     2, "unshared", ANSWER, True, None, r"파종제"),
    (9, "베스카를 지지한 제후 여덟의 서명이 봉인되어 대주교청에 접수됐다",
     3, "unshared", DECOY, True, None, r"봉인"),
    (10, "아르넬을 지지한 제후는 넷뿐이라 정족수 일곱에 못 미친다",
     3, "unshared", DECOY, True, None, r"넷뿐"),
    (11, "베스카는 세 해 전 이단 재판에 연루돼 성별식 자격이 정지됐다",
     4, "unshared", ANSWER, True, None, r"이단"),
    (12, "아르넬의 이름은 대주교청 파문 명부 어디에도 없다",
     4, "unshared", ANSWER, True, None, r"파문\s*명부"),
]

QUESTION = "아르넬과 베스카 중 누가 왕위를 이어야 할까요?"

# 본문 — 상황과 요건 4개만. 팩트 원문은 싣지 않는다(설계 규칙 5).
BODY = (
    "카른라드 왕국의 선왕이 겨울을 넘기지 못하고 세상을 떠났다. 왕위를 두고 남은 이는 "
    "둘이다 — 선왕의 딸 베스카와, 변경백의 아들이자 선왕의 조카인 아르넬. 왕국의 계승법은 "
    "왕관을 쓰려는 자가 갖춰야 할 것을 넷으로 정해 두었다. ① 선왕의 인장이 찍힌 계승 "
    "서약에 이름이 오를 것 ② 성년인 스무 살에 이를 것 ③ 열두 제후 가운데 일곱 이상의 "
    "서명을 받을 것 ④ 대주교청이 성별식을 집전할 자격을 인정할 것. 재상은 왕궁의 네 "
    "가신을 불러 모았다. 문서고를 지키는 서기, 궁정의 계보를 아는 시종장, 제후들과 서신을 "
    "주고받는 전령장, 대주교청에 드나드는 사제다. 저마다 아는 것이 다르다."
)

# 사안 요약문 — 러너가 프롬프트에 넣는 압축본(camp 의 STUB 자리).
STUB = (
    "카른라드 왕국의 왕위를 선왕의 딸 베스카와 선왕의 조카 아르넬 중 누가 이을지 "
    "정하는 문제를 논의 중이다. 계승법이 정한 조건은 네 가지다. ① 선왕의 인장이 찍힌 "
    "계승 서약에 이름이 오를 것 ② 성년인 스무 살에 이를 것 ③ 열두 제후 가운데 일곱 "
    "이상의 서명 ④ 대주교청의 성별식 자격 인정."
)


def fid(n: int) -> str:
    return f"fact_throne_{n:02d}"


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
        "_note": (f"후보 초안(팀 검수 전). issue_camp 골격 이식 — 요건 4 × (공유 1 + 미공유 2), "
                  f"공유 4 중 3이 오답({DECOY}) 쪽으로 기우는 함정, 미공유 favors {ANSWER} 6 : {DECOY} 2, "
                  f"미공유 전량 critical. 정답={ANSWER}(요건 1·2·4 충족, 3 미충족 = 3/4), "
                  f"{DECOY} 는 요건 3만 충족(1/4). 인명·지명·수치 전부 허구. "
                  f"⚠ prior 프로브 미실행 — 실행 전 확인 필요."),
        "extractor": {"name": "manual", "ver": "1"},
        "facts": facts,
    }
    issue_doc = {
        **common,
        "source": "synthetic",
        "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
        "title": "카른라드 왕위 계승 — 재상과 네 가신의 평의",
        "question": QUESTION,
        "body": BODY,
        "_note": ("팩트 우선 설계(camp 계승). 본문에는 요건 4종만 싣고 팩트 원문은 싣지 않는다 "
                  "— 팩트 노출은 배분층 소관이며 본문에 넣으면 2단 미공유 구조가 무너진다. "
                  "러너용 사안 요약문(STUB)은 build 스크립트 상단에 있다."),
    }
    return {"issue": issue_doc, "facts": facts_doc}


def check(facts_doc: dict, assign_doc: dict) -> int:
    """자체 검사 — 통과하지 못한 항목 수를 돌려준다."""
    anchors = {fid(n): a for n, *_rest, a in [(f[0], *f[1:]) for f in FACTS]}
    texts = {f["fact_id"]: f["text"] for f in facts_doc["facts"]}
    bad = 0

    def line(name: str, ok: bool, detail: str = "") -> None:
        nonlocal bad
        bad += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}{('  ' + detail) if detail else ''}")

    print("── 앵커")
    miss = [k for k, rx in anchors.items() if not re.search(rx, texts[k])]
    line("자기 팩트 적중", not miss, f"미적중 {miss}" if miss else "12/12")
    cross = {k: [j for j, t in texts.items() if j != k and re.search(rx, t)]
             for k, rx in anchors.items()}
    cross = {k: v for k, v in cross.items() if v}
    line("교차 오검출 0", not cross, str(cross) if cross else "")
    leak_body = [k for k, rx in anchors.items() if re.search(rx, BODY)]
    line("본문 누출 0", not leak_body, str(leak_body) if leak_body else f"본문 {len(BODY)}자")
    leak_stub = [k for k, rx in anchors.items() if re.search(rx, STUB)]
    line("요약문 누출 0", not leak_stub, str(leak_stub) if leak_stub else f"요약문 {len(STUB)}자")

    print("── 구조 (camp 골격)")
    fs = facts_doc["facts"]
    sh = [f for f in fs if f["share"] == "shared"]
    un = [f for f in fs if f["share"] == "unshared"]
    line("팩트 12개", len(fs) == 12, str(len(fs)))
    line("공유 4 / 미공유 8", len(sh) == 4 and len(un) == 8, f"{len(sh)} / {len(un)}")
    line("요건별 미공유 2개씩", all(v == 2 for v in Counter(f["requirement"] for f in un).values()),
         str(dict(sorted(Counter(f["requirement"] for f in un).items()))))
    sh_decoy = sum(1 for f in sh if f["favors"] == DECOY)
    line(f"공유 함정(오답 쪽 3개)", sh_decoy == 3, f"{DECOY} {sh_decoy}/4")
    unf = Counter(f["favors"] for f in un)
    line("미공유 기울기 6:2", unf[ANSWER] == 6 and unf[DECOY] == 2,
         f"{ANSWER} {unf[ANSWER]} : {DECOY} {unf[DECOY]}")
    line("미공유 전량 critical", all(f["critical"] for f in un))

    print("── 배분 (split_pairs · 4에이전트 · overlap_k 1)")
    agents = assign_doc["agents"]
    own = Counter(i for a in agents for i in a["assigned_fact_ids"])
    shared_ids = {f["fact_id"] for f in sh}
    line("에이전트 4명", len(agents) == 4, str(len(agents)))
    line("공유 4개는 전원 보유", all(shared_ids <= set(a["assigned_fact_ids"]) for a in agents))
    iso = [k for k, v in own.items() if v == 1]
    line("고립(1명만 보유) 8개", len(iso) == 8, f"{len(iso)}개")
    line("미배분 0", len(own) == 12, f"배분된 팩트 {len(own)}개")
    return bad


def main() -> None:
    docs = build_docs()
    assign_doc = assignment_gen.generate_split_pairs(docs["facts"], n_agents=4, seed=42, overlap_k=1)
    paths = {
        HERE / f"{IID}.json": docs["issue"],
        HERE / f"facts_{IID}.json": docs["facts"],
        HERE / f"assignment_{IID}.json": assign_doc,
    }
    for p, doc in paths.items():
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[생성] {', '.join(p.name for p in paths)}\n")
    bad = check(docs["facts"], assign_doc)
    print(f"\n{'전부 통과' if not bad else f'실패 {bad}건'}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
