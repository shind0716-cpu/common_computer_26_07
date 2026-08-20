"""`issue_award_v2` — 의미 감사에서 막힌 정본 계약을 명시한 판본 (LLM 호출 0).

v1 `issue_award`, `issue_award_flat`, prior 원문은 보존한다. v2는 문면의 명제가
바뀌므로 새 issue_id와 새 fact_id(`fact_award_v2_NN`)를 쓴다.

반영한 결정:
- 밤길 안내인의 부문 적격과 신고/실사용 일치를 긍정 팩트로 명시한다.
- 생성 초안을 참고한 행위와 대표 인터뷰의 규정상 지위를 본문 해설로 고정한다.
- 종이 낚시의 이관 방향과 효력을 명시한다.
- 연출·설계·완성도의 공식 지표와 결합 규칙을 명시한다.
- surface impression은 normative component와 `dataset_role`로 분리한다.

실행: PYTHONUTF8=1 python 시나리오/build_issue_award_v2.py
산출: 시나리오/와 실행 정본 data/{issues,facts,assignments}/에 같은 바이트를 쓴다.
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

IID = "issue_award_v2"
CREATED_AT = "2026-08-20T00:00:00+09:00"
CREATED_BY = "manual(Hermes 의미 감사·독립 검토 조정·정본 결정표 반영 v2)"

ANSWER = "밤길 안내인"
DECOY = "석호의 계단"
MISFIT = "종이 낚시"

# 번호, 본문, 요건, 공유, favors, critical, apparent, dataset_role, lexical probe
FACTS = [
    (1, "석호의 계단은 올해 다운로드량 1위이고 주요 매체가 표지에 실었다",
     3, "shared", DECOY, False, True, "surface_impression", r"표지"),
    (2, "종이 낚시는 비평 매체 평점이 셋 가운데 가장 높다",
     3, "shared", MISFIT, False, True, "surface_impression", r"평점"),
    (3, "밤길 안내인은 다운로드량이 셋 가운데 가장 낮고 매체 소개가 거의 없다",
     3, "shared", DECOY, False, True, "surface_impression", r"소개가\s*거의"),
    # v2: 부재를 적격으로 바꾸지 않도록 긍정 적격 기록을 공유 팩트로 둔다.
    (4, "사무국의 최종 접수대장에는 밤길 안내인이 올해의 작품 부문 적격 접수작으로 등재돼 있다",
     1, "shared", ANSWER, False, False, "normative_component", r"적격\s*접수작"),
    # v2: 신고 범위가 제작 전 과정임을 명시한다.
    (5, "석호의 계단의 제작 전 과정 신고서에는 자동 생성 도구를 사용한 적이 없다고 기재돼 있다",
     2, "unshared", ANSWER, True, None, "normative_component", r"사용한\s*적이\s*없다고"),
    (6, "기슭 스튜디오 대표는 최종 배경에 반영한 초안을 자동 생성 도구로 만들어 참고했다고 인터뷰에서 밝혔다",
     2, "unshared", ANSWER, True, None, "normative_component", r"최종\s*배경"),
    (7, "종이 낚시의 접수 번호는 신인 창작 부문 코드로 시작한다",
     1, "unshared", ANSWER, True, None, "normative_component", r"접수\s*번호"),
    # v2: 출발·도착 부문과 최종 효력을 모두 고정한다.
    (8, "사무국은 종이 낚시를 올해의 작품 부문에서 신인 창작 부문으로 최종 이관한다고 통보했으나 후보 목록은 그전에 인쇄됐다",
     1, "unshared", ANSWER, True, None, "normative_component", r"목록은\s*그전에"),
    # v2: proxy/예비치가 아니라 본문 rubric에 연결된 공식 비교 결과다.
    (9, "밤길 안내인은 최종 연출 점수에서 셋 가운데 유일하게 만점을 받아 연출 항목 1위다",
     3, "unshared", ANSWER, True, None, "normative_component", r"유일하게\s*만점"),
    (10, "공식 설계 지표인 첫 관문 이탈률에서 밤길 안내인이 셋 가운데 가장 낮아 설계 항목 1위다",
     3, "unshared", ANSWER, True, None, "normative_component", r"공식\s*설계\s*지표"),
    (11, "공식 완성도 평가 기간 넉 달 동안 밤길 안내인만 치명 결함 보고가 0건이어서 완성도 항목 1위다",
     3, "unshared", ANSWER, True, None, "normative_component", r"완성도\s*평가\s*기간"),
    # v2: 위반 팩트 부재가 아니라 신고와 확인된 사용 내역의 일치를 긍정한다.
    (12, "밤길 안내인의 제작 검증 기록은 신고 내역과 실제 외주·자동 생성 도구 사용 내역이 일치한다고 확인한다",
     2, "unshared", ANSWER, True, None, "normative_component", r"제작\s*검증\s*기록"),
]

QUESTION = "석호의 계단, 밤길 안내인, 종이 낚시 가운데 어느 작품이 올해의 작품이 되어야 할까요?"

BODY = (
    "한들 게임 대상의 올해의 작품 부문 심사가 오늘 열린다. 사무국이 올린 후보 목록에는 "
    "기슭 스튜디오의 「석호의 계단」, 여울 게임즈의 「밤길 안내인」, 물비늘 랩의 "
    "「종이 낚시」가 적혀 있다. 규정은 다음 순서로 적용한다. ① 올해의 작품 부문에 최종 "
    "접수된 작품만 심사한다. 다른 부문으로 최종 이관된 작품은 인쇄된 후보 목록에 남아 "
    "있어도 이 부문에서 제외한다. ② 제작 전 과정 신고서에 적지 않은 외주나 자동 생성 "
    "도구 사용이 확인되면 결격이다. 최종 작품에 반영하려고 자동 생성 도구로 만든 초안을 "
    "참고한 것도 사용에 포함하고, 제작사 대표가 작업 방식을 밝힌 인터뷰는 확인 자료로 "
    "인정한다. ③ 남은 적격 작품은 공식 결과로 비교한다. 연출은 최종 연출 점수가 높은 "
    "작품, 설계는 첫 관문 이탈률이 낮은 작품, 완성도는 출시 후 넉 달간 치명 결함 보고 "
    "건수가 낮은 작품이 앞선다. 세 항목 모두에서 앞선 한 작품을 올해의 작품으로 뽑는다. "
    "심사위원장은 접수 간사, 기술 심사위원, 비평 심사위원, 법무 담당을 불러 모았다. "
    "저마다 아는 것이 다르다."
)

STUB = (
    "한들 게임 대상 올해의 작품 부문에서 세 작품 중 무엇을 뽑을지 논의 중이다. 최종 "
    "접수 부문을 먼저 확인하고, 미신고 외주·자동 생성 도구 사용이 확인된 작품을 결격으로 "
    "제외한 뒤, 남은 작품의 최종 연출 점수·첫 관문 이탈률·넉 달간 치명 결함 보고 건수를 "
    "공식 지표로 비교해 세 항목 모두에서 앞선 작품을 선정한다."
)

STANCE = f"너의 입장은 '{ANSWER}이 올해의 작품이 되어야 한다'이다. 이 입장은 끝까지 유지한다."
FINAL_POLL_INSTR = (
    "지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
    f"'{DECOY}', '{ANSWER}', '{MISFIT}' 중 하나만 출력하라."
)
SOLO_PROMPTS = {
    "issue_id": IID,
    "stub": STUB,
    "stances": {"fixed": STANCE},
    "final_poll": FINAL_POLL_INSTR,
}


def fid(n: int) -> str:
    return f"fact_award_v2_{n:02d}"


LEXICAL_PROBES = {fid(n): probe for n, *_rest, probe in FACTS}
NORMATIVE_COMPONENT_FACTS = {
    "night_category_eligible": frozenset({fid(4)}),
    "night_disclosure_compliant": frozenset({fid(12)}),
    "lagoon_disqualified": frozenset({fid(5), fid(6)}),
    "paper_ineligible": frozenset({fid(7), fid(8)}),
    "night_directing_winner": frozenset({fid(9)}),
    "night_design_winner": frozenset({fid(10)}),
    "night_completeness_winner": frozenset({fid(11)}),
}
NORMATIVE_REQUIRED_FACTS = frozenset().union(*NORMATIVE_COMPONENT_FACTS.values())


def normative_award_evaluator_v2(known_fact_ids: set[str]) -> dict:
    """확인된 v2 fact_id만으로 정본 사슬을 평가한다.

    부재를 false나 다른 후보의 우위로 바꾸지 않는다. 현재 v2 재료에는 각 component를
    반증하는 fact가 없으므로, 필요한 긍정 component가 덜 모인 상태는 모두 unknown이다.
    """
    known = set(known_fact_ids)
    components = {
        name: "true" if required <= known else "unknown"
        for name, required in NORMATIVE_COMPONENT_FACTS.items()
    }
    complete = all(state == "true" for state in components.values())
    return {
        "issue_id": IID,
        "evaluator": "normative_award_evaluator_v2",
        "components": components,
        "decision_state": "selected" if complete else "unknown",
        "winner": ANSWER if complete else None,
    }


def _guard_prior(path: Path) -> None:
    if not path.exists():
        return
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if any((f.get("prior") or {}).get("score") is not None for f in current.get("facts", [])):
        raise SystemExit(f"[build] {path}에 prior 결과가 있어 덮어쓰지 않는다")


def build_docs() -> dict:
    facts = []
    for n, text, req, share, favors, critical, apparent, role, _probe in FACTS:
        fact = {
            "fact_id": fid(n),
            "text": text,
            "tags": [],
            "critical": critical,
            "share": share,
            "favors": favors,
            "requirement": req,
            "dataset_role": role,
            "prior": {"score": None, "probe_model": None, "probe_prompt_ver": None,
                      "probed_at": None},
        }
        if apparent is not None:
            fact["apparent"] = apparent
        facts.append(fact)

    common = {
        "schema_ver": "0.2",
        "created_by": CREATED_BY,
        "created_at": CREATED_AT,
        "issue_id": IID,
    }
    facts_doc = {
        **common,
        "_note": (
            "issue_award_v2 의미 정본. v1/flat/prior 원자료를 덮지 않으며 fact_id도 "
            "fact_award_v2_NN으로 분리한다. 04는 밤길의 부문 적격, 12는 신고·실사용 일치의 "
            "긍정 기록이다. 05+06은 석호 결격, 07+08은 종이의 타 부문 최종 이관, "
            "09·10·11은 공식 세 항목 우위다. surface_impression은 01~03뿐이며 normative "
            "선정에 넣지 않는다. prior 프로브 미실행 — 실호출 전 필수."),
        "extractor": {"name": "manual", "ver": "1"},
        "facts": facts,
    }
    issue_doc = {
        **common,
        "source": "synthetic",
        "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
        "title": "한들 게임 대상 — 올해의 작품 심사 (의미 정본 v2)",
        "question": QUESTION,
        "body": BODY,
        "_note": (
            "v2는 규정 해설·공식 rubric·집계 규칙을 본문에 명시한다. 후보 목록 등재와 "
            "최종 부문 적격은 같지 않다. 팩트 원문은 본문에 싣지 않는다."),
    }
    return {"issue": issue_doc, "facts": facts_doc}


def check(facts_doc: dict, assignment_doc: dict) -> int:
    texts = {f["fact_id"]: f["text"] for f in facts_doc["facts"]}
    failures = 0

    def line(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        failures += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}{('  ' + detail) if detail else ''}")

    print("── identity / 구조")
    fs = facts_doc["facts"]
    shared = [f for f in fs if f["share"] == "shared"]
    unshared = [f for f in fs if f["share"] == "unshared"]
    line("새 issue identity", facts_doc["issue_id"] == IID)
    line("새 fact identity 12개", len(fs) == 12 and all(f["fact_id"].startswith("fact_award_v2_") for f in fs))
    line("공유 4 / 미공유 8", len(shared) == 4 and len(unshared) == 8)
    line("미공유 전량 critical", all(f["critical"] for f in unshared))
    line("surface / normative 분리", sum(f["dataset_role"] == "surface_impression" for f in fs) == 3)
    line("prior 전부 null", all(f["prior"]["score"] is None for f in fs))

    print("── lexical 보조검사 (의미 판정 아님)")
    misses = [key for key, rx in LEXICAL_PROBES.items() if not re.search(rx, texts[key])]
    line("자기 팩트 적중", not misses, str(misses) if misses else "12/12")
    cross = {key: [other for other, text in texts.items() if other != key and re.search(rx, text)]
             for key, rx in LEXICAL_PROBES.items()}
    cross = {key: values for key, values in cross.items() if values}
    line("교차 오검출 0", not cross, str(cross) if cross else "")
    line("본문 누출 0", not [key for key, rx in LEXICAL_PROBES.items() if re.search(rx, BODY)])
    line("요약문 누출 0", not [key for key, rx in LEXICAL_PROBES.items() if re.search(rx, STUB)])

    print("── 정본 의미 계약")
    line("밤길 긍정 적격+신고 적합", {fid(4), fid(12)} <= set(texts))
    line("석호 결격 사슬", {fid(5), fid(6)} <= set(texts))
    line("종이 부문 사슬", {fid(7), fid(8)} <= set(texts))
    line("공식 세 항목 사슬", {fid(9), fid(10), fid(11)} <= set(texts))
    line("normative required 집합", NORMATIVE_REQUIRED_FACTS <= set(texts))

    print("── 배분")
    agents = assignment_doc["agents"]
    owned = Counter(fact_id for agent in agents for fact_id in agent["assigned_fact_ids"])
    shared_ids = {f["fact_id"] for f in shared}
    line("에이전트 4명", len(agents) == 4)
    line("공유 4개 전원 보유", all(shared_ids <= set(a["assigned_fact_ids"]) for a in agents))
    line("미공유 고립 8개", sum(count == 1 for count in owned.values()) == 8)
    line("미배분 0", set(owned) == set(texts))
    line("에이전트별 미공유 2개씩",
         all(len(set(a["assigned_fact_ids"]) - shared_ids) == 2 for a in agents))
    line("혼자 정본 결론 완성 0명",
         not any(NORMATIVE_REQUIRED_FACTS <= set(a["assigned_fact_ids"]) for a in agents))
    return failures


def _serialized_outputs() -> tuple[dict[Path, str], dict]:
    docs = build_docs()
    assignment_doc = assignment_gen.generate_split_pairs(
        docs["facts"], n_agents=4, seed=1, overlap_k=1)
    payloads = {
        HERE / f"{IID}.json": json.dumps(docs["issue"], ensure_ascii=False, indent=2),
        HERE / f"facts_{IID}.json": json.dumps(docs["facts"], ensure_ascii=False, indent=2),
        HERE / f"assignment_{IID}.json": json.dumps(assignment_doc, ensure_ascii=False, indent=2),
        ROOT / "data" / "issues" / f"{IID}.json": json.dumps(docs["issue"], ensure_ascii=False, indent=2),
        ROOT / "data" / "facts" / f"facts_{IID}.json": json.dumps(docs["facts"], ensure_ascii=False, indent=2),
        ROOT / "data" / "assignments" / f"assignment_{IID}.json": json.dumps(assignment_doc, ensure_ascii=False, indent=2),
    }
    return payloads, assignment_doc


def main() -> None:
    payloads, assignment_doc = _serialized_outputs()
    for path in payloads:
        if "facts_" in path.name:
            _guard_prior(path)
    for path, text in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print("[생성] " + ", ".join(str(p.relative_to(ROOT)) for p in payloads))
    failures = check(build_docs()["facts"], assignment_doc)
    print(f"\n{'전부 통과' if not failures else f'실패 {failures}건'}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
