from __future__ import annotations

from pathlib import Path
import json
import sys

import yaml

HERE = Path(__file__).resolve().parent
PATH = HERE / "SCENARIOS_12_V03_DEVELOPMENT.yaml"
EXPECTED_TOPICS = [
    "길고양이 급식",
    "일반 공용 주차",
    "층간 생활소음",
    "쓰레기·재활용",
    "공용 화단",
    "빈 텃밭",
    "버스 노선",
    "임산부 우선 주차석",
    "공동 흡연 구역",
    "택배 보관공간",
    "공용 세탁실",
    "주민 공용실",
]
AGENT_HINTS = [
    "정당한 경계",
    "최소 보호선",
    "협의 영역",
    "절충안",
    "시간대 배분",
    "요일 배정",
    "시험 운영",
    "임시 우선",
    "정기 재검토",
    "모범답안",
    "권장 결론",
]
VALUE_CONTAMINANTS = [
    "경계",
    "최소선",
    "절충",
    "재검토",
    "시험",
    "배분",
    "요일",
    "시간대",
]


def main() -> int:
    doc = yaml.safe_load(PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    scenarios = doc.get("scenarios", [])
    scenario_ids: list[str] = []
    domains: list[str] = []
    fact_ids: list[str] = []

    for scenario in scenarios:
        sid = scenario["scenario_id"]
        scenario_ids.append(sid)
        domains.append(scenario["topic_domain"])
        if len(scenario.get("round_1", [])) != 3:
            errors.append(f"round1_count:{sid}")
        if len(scenario.get("round_2", [])) != 4:
            errors.append(f"round2_count:{sid}")
        variants = scenario.get("round_3_variants", {})
        if set(variants) != {"baseline", "focal_change", "partial_change"}:
            errors.append(f"variant_set:{sid}")

        local_ids = [item["fact_id"] for item in scenario.get("round_1", [])]
        local_ids.extend(item["fact_id"] for item in scenario.get("round_2", []))
        local_ids.extend(item["fact_id"] for item in variants.values())
        if len(local_ids) != 10 or len(set(local_ids)) != 10:
            errors.append(f"local_fact_ids:{sid}")
        fact_ids.extend(local_ids)

        shown_text = [scenario["title"], scenario["decision_question"]]
        shown_text.extend(item["text"] for item in scenario["round_1"])
        shown_text.extend(item["text"] for item in scenario["round_2"])
        shown_text.extend(item["text"] for item in variants.values())
        joined = " ".join(shown_text)
        for phrase in AGENT_HINTS:
            if phrase in joined:
                errors.append(f"agent_hint:{sid}:{phrase}")

    if len(scenarios) != 12:
        errors.append(f"scenario_count:{len(scenarios)}")
    if len(set(scenario_ids)) != len(scenario_ids):
        errors.append("scenario_id_not_unique")
    if domains != EXPECTED_TOPICS:
        errors.append("topic_order_or_membership")
    if len(set(domains)) != 12:
        errors.append("topic_domain_not_unique")
    if len(fact_ids) != 120 or len(set(fact_ids)) != 120:
        errors.append(f"global_fact_ids:{len(fact_ids)}:{len(set(fact_ids))}")

    profiles = doc.get("value_profiles", {}).get("profiles", [])
    if len(profiles) != 3:
        errors.append(f"profile_count:{len(profiles)}")
    value_text = " ".join(profile.get("prompt", "") for profile in profiles)
    for phrase in VALUE_CONTAMINANTS:
        if phrase in value_text:
            errors.append(f"value_contamination:{phrase}")

    governance = doc.get("governance", {})
    if governance.get("intended_use") != "development_only":
        errors.append("intended_use")
    if governance.get("confirmatory_use_allowed") is not False:
        errors.append("confirmatory_gate")

    print("V03_12_SCENARIO_VERIFICATION=" + ("PASS" if not errors else "FAIL"))
    print("ERRORS=" + ("none" if not errors else json.dumps(errors, ensure_ascii=False)))
    print(
        "COUNTS "
        f"scenarios={len(scenarios)} unique_topics={len(set(domains))} "
        f"facts={len(fact_ids)} unique_facts={len(set(fact_ids))} "
        f"variants={len(scenarios) * 3} profiles={len(profiles)}"
    )
    print("TOPICS=" + " | ".join(domains))
    print("AGENT_HINT_SCAN=" + ("PASS" if not any(e.startswith("agent_hint:") for e in errors) else "FAIL"))
    print(
        "VALUE_CONTAMINATION_SCAN="
        + ("PASS" if not any(e.startswith("value_contamination:") for e in errors) else "FAIL")
    )
    print("GOVERNANCE_GATE=" + ("PASS" if not any(e in {"intended_use", "confirmatory_gate"} for e in errors) else "FAIL"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
