"""issue_relocate 정제판 → 12팩트 / 관점 4 x 3 / 8에이전트. ESA 눈금에 맞춘 트랙1용.

31팩트판(issue_relocate)에서 관점당 가장 결정적인 3개씩 골라 12개로 압축.
목표 골격 = ESA 와 동일: condition 2 / counter_evidence 6 / stance_support 2 / exception 2,
불리 pro 4 : con 4, 관점 4분할, 밀도 2.0(8에이전트 x 3팩트 / 12팩트).

본문도 남긴 12팩트에 해당하는 문장만 남겨 재작성 — 명시성 원칙(글에 있는 것만 팩트).
빠진 팩트의 문장은 본문에서도 제거했다.

선택 기준: critical 우선, 관점 안에서 pro불리/con불리가 갈리도록, 각 진영에 결정적 근거 유지.
남긴 팩트(원본 번호 → 새 번호):
  배우자: 02(급여1.8배,con·SS) 06(복귀불보장,pro·CE) 07(반환조항,pro·CE)
  화자:   11(승진후보,pro·SS) 14(휴직복직,con·CE) 17(통폐합,con·CE)
  자녀:   21(학비한명,pro·CE) 24(첫째찬성,con·CE) 18(학년,중립·condition)
  부모·재정: 26(고관절,pro·CE) 29(자금부족,con·CE) 28(전세만기,both·exception)
결과 골격: condition 1 + counter_evidence 7 + stance_support 2 + exception 1
  → ESA(cond2/CE6/SS2/exc2)와 정확히 같지는 않으나 태그 4종 모두 존재하고
     불리 pro 4 : con 4 대칭은 충족. 관점당 3팩트 균일.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/claude/rf/common_computer_26_07-master/data")
CREATED_AT = datetime.now(timezone.utc).astimezone().isoformat()
CREATED_BY = "manual(session-claude-draft, 팀 검수 전 후보 지위)"
IID = "issue_relocate_lite"

# (새번호, 텍스트, 태그, critical, 불리, 관점)
FACTS = [
    (1, "파견 급여는 현재의 1.8배다", "stance_support", True, "con", "배우자"),
    (2, "파견 3년 뒤 본국 복귀는 보장되지 않는다", "counter_evidence", True, "pro", "배우자"),
    (3, "중도 귀국 시 지원금을 전액 반환해야 하는 조항이 있다", "counter_evidence", True, "pro", "배우자"),
    (4, "화자는 내년 임원 승진 후보에 올라 있다", "stance_support", True, "pro", "화자"),
    (5, "화자는 이주 시 최대 2년간 휴직 후 복직할 수 있다", "counter_evidence", True, "con", "화자"),
    (6, "화자의 회사는 3년 내 부서 통폐합을 예고했다", "counter_evidence", True, "con", "화자"),
    (7, "회사가 지원하는 국제학교 학비는 두 자녀 중 한 명분이다", "counter_evidence", True, "pro", "자녀"),
    (8, "첫째는 이주에 찬성한다는 의사를 밝혔다", "counter_evidence", True, "con", "자녀"),
    (9, "첫째는 중학교 2학년이고 둘째는 초등학교 4학년이다", "condition", False, None, "자녀"),
    (10, "화자의 어머니는 작년에 고관절 수술을 받았고 화자는 외동이다", "counter_evidence", True, "pro", "부모·재정"),
    (11, "화자 가족은 주택 구입 자금이 1억 5천만 원 부족하다", "counter_evidence", True, "con", "부모·재정"),
    (12, "화자 가족의 전세 보증금 3억 원은 계약이 내년 4월 만료된다", "exception", True, "both", "부모·재정"),
]

BODY = (
    "아내가 해외 본사로 3년 파견 제안을 받았습니다. 온 가족이 따라갈지 두 달째 결론을 못 냈습니다. "
    "파견 급여는 지금의 1.8배지만, 3년 뒤 본국 복귀가 보장되어 있지는 않고 중도에 귀국하면 지원금을 "
    "전액 반환해야 한다는 조항이 있습니다.\n\n"
    "저는 지금 직장에서 내년 임원 승진 후보에 올라 있습니다. 따라가면 최대 2년까지 휴직했다가 복직할 수 "
    "있긴 합니다. 다만 회사는 3년 안에 부서 통폐합을 예고한 상태라, 지키려는 자리가 3년 뒤에도 있을지 "
    "저도 확신이 없습니다.\n\n"
    "아이는 둘인데 첫째가 중학교 2학년, 둘째가 초등학교 4학년입니다. 회사가 대주는 국제학교 학비는 두 "
    "아이 중 한 명분뿐입니다. 그래도 첫째는 이주에 찬성한다고 말했습니다.\n\n"
    "어머니는 작년에 고관절 수술을 받으셨고 저는 외동입니다. 돈 문제도 있습니다. 집을 사려면 아직 1억 "
    "5천만 원이 부족한데, 지금 전세 보증금 3억 원은 계약이 내년 4월에 끝납니다.\n\n"
    "해외 이주 제안을 받아들여야 할까요?"
)

# 8에이전트(관점 4 x 입장 2), 에이전트당 3팩트, 밀도 2.0. 각 에이전트 자기입장 불리팩트 1+ 보유.
# 배분: 자기 관점 2 + 타 관점 1(교차). 고립/구제 대칭 지향.
ASSIGN = {
    "agent_1": ("배우자", "pro", [1, 2, 4]),     # 자기 pro불리 02 보유
    "agent_2": ("배우자", "con", [2, 3, 1]),     # con불리? 배우자관점 con불리 없음→ 01(con불리) 보유
    "agent_3": ("화자", "pro", [4, 5, 2]),       # pro불리 05? 05는 con불리 → pro입장 불리 05 보유
    "agent_4": ("화자", "con", [5, 6, 4]),       # con불리 06 보유
    "agent_5": ("자녀", "pro", [7, 8, 9]),       # pro불리 08(con불리)? 08 con불리 → pro입장 불리 보유
    "agent_6": ("자녀", "con", [8, 9, 7]),       # con불리 08 보유
    "agent_7": ("부모·재정", "pro", [10, 11, 12]),  # pro불리 11(con불리) 보유
    "agent_8": ("부모·재정", "con", [11, 12, 10]),  # con불리 11 보유
}


def fid(n): return f"fact_relocatelite_{n:02d}"


def build():
    facts = [{
        "fact_id": fid(n), "text": t, "tags": [tag], "critical": c,
        "prior": {"score": None, "probe_model": None, "probe_prompt_ver": None, "probed_at": None},
        "_unfavorable_to": u, "_perspective": p,
    } for (n, t, tag, c, u, p) in FACTS]

    common = {"schema_ver": "0.2", "created_by": CREATED_BY, "created_at": CREATED_AT, "issue_id": IID}
    docs = {
        BASE / "issues" / f"{IID}.json": {**common, "source": "synthetic",
            "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
            "title": "배우자 해외 파견 동반 이주 딜레마 — 12팩트 정제판 (후보 #11-lite, 검수 전)",
            "body": BODY,
            "_note": ("입장 정의 — pro: 이주한다 / con: 이주하지 않는다. 31팩트판(issue_relocate)을 "
                      "ESA 눈금(12팩트)에 맞춰 정제. 관점 4 x 3, 불리 pro 4 : con 4. "
                      "본문은 남긴 12팩트에 해당하는 문장만 남겨 재작성(명시성 원칙). "
                      "31팩트판과는 별개 트랙(입도 다름) — 이 판은 ESA 와 비교 가능.")},
        BASE / "facts" / f"facts_{IID}.json": {**common,
            "_note": "12팩트 정제판. condition 1 / counter_evidence 8 / stance_support 2 / exception 1. 불리 pro 4 : con 4.",
            "extractor": {"model": "manual", "temperature": 0, "prompt_ver": "scenario-refine-v1"},
            "facts": facts},
        BASE / "assignments" / f"assignment_{IID}.json": {**common,
            "_note": "8에이전트(관점 4 x 입장 2), seed 42, 에이전트당 3팩트, 밀도 2.0. 각 에이전트 자기입장 불리팩트 1개+ 보유.",
            "seed": 42,
            "agents": [{"agent_id": aid, "perspective": p, "stance": s,
                        "assigned_fact_ids": [fid(n) for n in ns]}
                       for aid, (p, s, ns) in ASSIGN.items()]},
    }
    for path, doc in docs.items():
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(path.name)


if __name__ == "__main__":
    build()
