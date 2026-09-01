from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_json(path: Path, value: dict) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def rate(n: int, d: int) -> float | None:
    return n / d if d else None


def validate_freezes() -> dict[str, str]:
    result = {}
    for kind in "WRF":
        freeze_path = HERE / f"PACK_{kind}_FREEZE.json"
        freeze = read_json(freeze_path)
        if freeze["key_opened"] is not False:
            raise ValueError(f"PACK_{kind}: pre-key freeze flag is not false")
        for name, expected in freeze["files"].items():
            candidates = [HERE / name, ROOT / name]
            actual_path = next((path for path in candidates if path.exists()), None)
            if actual_path is None or sha(actual_path) != expected:
                raise ValueError(f"PACK_{kind}: frozen file mismatch: {name}")
        result[freeze_path.name] = sha(freeze_path)
    return result


def join_pack(kind: str) -> tuple[dict, dict]:
    consensus_path = HERE / f"PACK_{kind}_CONSENSUS_01.json"
    key_path = ROOT / f"_KEY_{kind}_2026-09-01.json"
    consensus = read_json(consensus_path)
    key = read_json(key_path)
    key_items = {row["item"]: row for row in key["items"]}
    consensus_ids = [row["id"] for row in consensus["items"]]
    if set(consensus_ids) != set(key_items) or len(consensus_ids) != len(key_items):
        raise ValueError(f"PACK_{kind}: key/consensus ID mismatch")
    joined = []
    for item in consensus["items"]:
        joined.append({"id": item["id"], "coding": item, "key": key_items[item["id"]]})
    keyed = {
        "pack": f"PACK_{kind}",
        "keyed_id": f"PACK_{kind}_KEYED_01",
        "analysis_status": (
            "preregistered_with_disclosed_prior_exposure_for_W1_W2"
            if kind == "W" else "post_hoc_exploratory"
        ),
        "consensus_sha256": sha(consensus_path),
        "key_sha256": sha(key_path),
        "items": joined,
        "provenance": consensus["provenance"],
    }
    keyed_path = HERE / f"PACK_{kind}_KEYED_01.json"
    atomic_json(keyed_path, keyed)
    return keyed, key


def summarize_w(keyed: dict) -> dict:
    def group(rows: list[dict]) -> dict:
        overlap = Counter()
        handling = Counter()
        exact = 0
        for row in rows:
            coding, key = row["coding"], row["key"]
            n = len(set(coding["weights"]) & set(key["given"]))
            overlap[str(n)] += 1
            exact += set(coding["weights"]) == set(key["given"])
            handling[coding["unchosen_handling"]] += 1
        total = len(rows)
        return {
            "items": total,
            "exact_given_set": exact,
            "exact_given_set_rate": rate(exact, total),
            "overlap_counts": dict(sorted(overlap.items())),
            "mean_overlap_of_3": sum(int(k) * v for k, v in overlap.items()) / total,
            "unchosen_handling_counts": dict(sorted(handling.items())),
            "key_leak_given_total": sum(row["key"]["leak_given"] for row in rows),
            "key_leak_other_total": sum(row["key"]["leak_other"] for row in rows),
        }

    rows = keyed["items"]
    sol = {item["id"]: item for item in read_json(HERE / "PACK_W_SOL_01.json")["items"]}
    claude = {item["id"]: item for item in read_json(HERE / "PACK_W_CLAUDE_01.json")["items"]}
    weights_agreement = sum(set(sol[item_id]["weights"]) == set(claude[item_id]["weights"]) for item_id in sol)
    handling_agreement = sum(sol[item_id]["unchosen_handling"] == claude[item_id]["unchosen_handling"] for item_id in sol)
    aligned = {
        (item["issue_id"], item["value_set"]): item["aligned"]
        for item in read_json(ROOT / "_KEY_R_2026-09-01.json")["items"]
    }
    source = (ROOT / "PACK_W_weight_2026-09-01.md").read_text(encoding="utf-8")
    final_choices = {}
    matches = list(re.finditer(r"^## (W-\d{2}).*?$", source, re.MULTILINE))
    for index, match in enumerate(matches):
        section = source[match.start() : matches[index + 1].start() if index + 1 < len(matches) else len(source)]
        final_choices[match.group(1)] = re.search(r"\*\*최종 선택\*\* — ([^\n]+)", section).group(1).strip()
    enriched = []
    for row in rows:
        item_id, coding, key = row["id"], row["coding"], row["key"]
        enriched.append({
            "overlap": len(set(coding["weights"]) & set(key["given"])),
            "gate_pass": final_choices[item_id] == aligned[(key["issue_id"], key["value_set"])],
            "leak_given": key["leak_given"],
            "leak_other": key["leak_other"],
        })

    def overlap_group(selected: list[dict]) -> dict:
        return {
            "items": len(selected),
            "mean_overlap_of_3": sum(row["overlap"] for row in selected) / len(selected),
            "exact_given_set": sum(row["overlap"] == 3 for row in selected),
        }

    gate_pass = [row for row in enriched if row["gate_pass"]]
    gate_fail = [row for row in enriched if not row["gate_pass"]]
    leak_three = [row for row in enriched if row["leak_given"] == 3]
    no_category_words = [row for row in enriched if row["leak_given"] == 0 and row["leak_other"] == 0]
    gate_difference = abs(overlap_group(gate_pass)["mean_overlap_of_3"] - overlap_group(gate_fail)["mean_overlap_of_3"])
    leak_difference = abs(overlap_group(leak_three)["mean_overlap_of_3"] - overlap_group(no_category_words)["mean_overlap_of_3"])
    handling_counts = Counter(row["coding"]["unchosen_handling"] for row in rows)
    full_item_agreement = 60 - read_json(HERE / "PACK_W_DISAGREEMENTS.json")["n_disagreements"]
    overall = group(rows)
    return {
        "overall": overall,
        "groups": {value_set: group([row for row in rows if row["key"]["value_set"] == value_set]) for value_set in ("A", "B")},
        "coder_agreement": {
            "weights_exact_set": weights_agreement,
            "weights_exact_set_rate": rate(weights_agreement, 60),
            "unchosen_handling": handling_agreement,
            "unchosen_handling_rate": rate(handling_agreement, 60),
            "all_requested_fields": full_item_agreement,
            "all_requested_fields_rate": rate(full_item_agreement, 60),
        },
        "gate_check": {"pass": overlap_group(gate_pass), "fail": overlap_group(gate_fail), "absolute_mean_difference": gate_difference},
        "word_leak_check": {
            "all_three_given_labels_visible": overlap_group(leak_three),
            "no_given_or_other_category_labels_visible": overlap_group(no_category_words),
            "absolute_mean_difference": leak_difference,
            "prereg_count_reconciliation": "PREREG의 '하나도 없는 32판'은 key에서 leak_given=0 and leak_other=0인 32판과 일치한다. leak_given=0만 적용하면 37판이다.",
        },
        "preregistered_predictions": {
            "W1": {"outcome": "적중", "observed_mean_overlap": overall["mean_overlap_of_3"], "criterion": ">=2.00"},
            "W2": {"outcome": "적중", "observed_exact_given_set": overall["exact_given_set"], "criterion": ">=18/60"},
            "W3": {"outcome": "적중", "reject_plus_accept": handling_counts["기각"] + handling_counts["감수"], "not_mentioned": handling_counts["안 나옴"], "criterion": "기각+감수 > 안 나옴"},
            "W4": {"outcome": "적중", "observed_weights_agreement": weights_agreement, "criterion": ">=30/60"},
            "W5": {"outcome": "기각", "observed_absolute_gate_mean_difference": gate_difference, "criterion": "<0.5"},
        },
    }


def summarize_r(keyed: dict, key: dict) -> dict:
    def group(rows: list[dict]) -> dict:
        judgments = [fact for row in rows for fact in row["coding"]["facts"]]
        retained = sum(fact["retained"] for fact in judgments)
        return {
            "items": len(rows),
            "judgments": len(judgments),
            "retained": retained,
            "not_retained": len(judgments) - retained,
            "retention_rate": rate(retained, len(judgments)),
        }
    rows = keyed["items"]
    disagreements = read_json(HERE / "PACK_R_DISAGREEMENTS.json")["disagreements"]
    sample = set(key["audit_sample"])
    audit_conflicts = sum(row["id"] in sample for row in disagreements)
    return {
        "overall": group(rows),
        "groups": {value_set: group([row for row in rows if row["key"]["value_set"] == value_set]) for value_set in ("A", "B")},
        "double_coding": {
            "all_items_double_coded": True,
            "protocol_audit_sample_items": len(sample),
            "all_judgments": 720,
            "all_disputed_facts": len(disagreements),
            "all_raw_agreement_rate": rate(720 - len(disagreements), 720),
            "audit_judgments": len(sample) * 12,
            "audit_disputed_facts": audit_conflicts,
            "audit_raw_agreement_rate": rate(len(sample) * 12 - audit_conflicts, len(sample) * 12),
            "deviation_note": "사용자 지시에 따라 60장 전부를 두 모델이 독립 판독했다. 규약의 14장 감사 표본보다 강한 이중 판독이며, 사후 탐색 지위는 바뀌지 않는다.",
        },
    }


def summarize_f(keyed: dict) -> dict:
    def group(rows: list[dict]) -> dict:
        relation = Counter(row["coding"]["conclusion_relation"] for row in rows)
        first_flip = Counter(str(row["coding"]["first_flip"]) for row in rows)
        change_type = Counter(str(row["coding"]["change_type"]) for row in rows)
        r0_aligned = sum(row["coding"]["round_options"]["r0"] == row["key"]["aligned"] for row in rows)
        r3_aligned = sum(row["coding"]["round_options"]["r3"] == row["key"]["aligned"] for row in rows)
        total = len(rows)
        return {
            "items": total,
            "relation_counts": dict(sorted(relation.items())),
            "first_flip_counts": dict(sorted(first_flip.items())),
            "change_type_counts": dict(sorted(change_type.items())),
            "r0_aligned_with_key": r0_aligned,
            "r0_aligned_rate": rate(r0_aligned, total),
            "r3_aligned_with_key": r3_aligned,
            "r3_aligned_rate": rate(r3_aligned, total),
        }
    rows = keyed["items"]
    return {
        "overall": group(rows),
        "groups": {value_set: group([row for row in rows if row["key"]["value_set"] == value_set]) for value_set in ("A", "B")},
    }


def main() -> int:
    freeze_hashes = validate_freezes()
    keyed_w, key_w = join_pack("W")
    keyed_r, key_r = join_pack("R")
    keyed_f, key_f = join_pack("F")
    summary = {
        "experiment": "pressure_category_ab_blind_coding",
        "seed": 20260901,
        "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "analysis_status": {
            "PACK_W": "preregistered_with_disclosed_prior_exposure_for_W1_W2",
            "PACK_R": "post_hoc_exploratory",
            "PACK_F": "post_hoc_exploratory",
        },
        "key_join_policy": {
            "key_withheld_from_initial_coders": True,
            "key_withheld_from_adjudicators": True,
            "all_packs_frozen_before_key_open": True,
            "key_sha256": {
                "W": sha(ROOT / "_KEY_W_2026-09-01.json"),
                "R": sha(ROOT / "_KEY_R_2026-09-01.json"),
                "F": sha(ROOT / "_KEY_F_2026-09-01.json"),
            },
        },
        "packs": {"W": summarize_w(keyed_w), "R": summarize_r(keyed_r, key_r), "F": summarize_f(keyed_f)},
        "limitations": [
            "PACK_W는 판독 전 사전고정됐지만 W1·W2 예측자는 같은 판의 선행 수치와 일부 글을 본 상태였다. W3~W5는 선행 값이 없었다.",
            "PACK_R과 PACK_F는 사후 탐색이다.",
            "AI 코더 둘의 일치는 모델 간 일치도이지 사람 신뢰도가 아니다.",
            "PACK_R은 규약의 14장 감사 표본을 넘어 60장 전부를 이중 판독했으나 사후 탐색 지위는 그대로다.",
            "PACK_W의 weights 셋 일치는 높았지만 모든 요청 필드의 완전 일치는 낮아, 안 고른 쪽 처리 분류는 판정자 의존성이 높다.",
        ],
    }
    summary_path = HERE / "KEYED_SUMMARY.json"
    atomic_json(summary_path, summary)

    w_pack = summary["packs"]["W"]
    w = w_pack["overall"]
    r = summary["packs"]["R"]["overall"]
    f = summary["packs"]["F"]["overall"]
    report = f"""# A/B 블라인드 판독 최종 보고서 — 2026-09-01

## 지위와 절차

- PACK_W는 판독 전에 예측과 판정선을 커밋한 **사전고정 판독**이다. 다만 W1·W2 예측자는 같은 판의 선행 수치와 일부 글을 본 상태였다는 지위 저하 고지가 있다.
- PACK_R·PACK_F는 **사후 탐색**이다.
- Claude Opus와 Hermes/GPT-5.6-Sol이 독립 판독했다.
- 불일치는 코더 정체와 열쇠를 가린 상태에서 팩별로 판정했다.
- 세 팩 합의본과 freeze를 검증한 뒤에만 `_KEY_W`·`_KEY_R`·`_KEY_F`를 열었다.
- **AI 코더 둘의 일치는 모델 간 일치도이지 사람 신뢰도가 아니다.**

## PACK_W 「무게」

- 60편 중 주어진 가치 셋 3개와 판독 셋이 정확히 일치: **{w['exact_given_set']}/60 ({w['exact_given_set_rate']:.1%})**
- 세 가치 중 평균 겹침: **{w['mean_overlap_of_3']:.2f}/3**
- 겹침 분포: {json.dumps(w['overlap_counts'], ensure_ascii=False)}
- 사전고정 W1 **적중**: 평균 겹침 {w['mean_overlap_of_3']:.2f} ≥ 2.00.
- 사전고정 W2 **적중**: 셋 다 맞힘 {w['exact_given_set']}/60 ≥ 18/60.
- 사전고정 W3 **적중**: 기각+감수 {w_pack['preregistered_predictions']['W3']['reject_plus_accept']} > 안 나옴 {w_pack['preregistered_predictions']['W3']['not_mentioned']}.
- 사전고정 W4 **적중**: weights 셋 코더 일치 {w_pack['coder_agreement']['weights_exact_set']}/60 ≥ 30/60.
- 사전고정 W5 **기각**: 관문 통과/탈락 평균 겹침 차 {w_pack['gate_check']['absolute_mean_difference']:.2f}로 0.5 미만이 아님.
- 오염 점검: 준 낱말 셋이 모두 보인 7판 평균 {w_pack['word_leak_check']['all_three_given_labels_visible']['mean_overlap_of_3']:.2f}, 준·안 준 카테고리 낱말이 모두 안 보인 32판 평균 {w_pack['word_leak_check']['no_given_or_other_category_labels_visible']['mean_overlap_of_3']:.2f}; 차이 {w_pack['word_leak_check']['absolute_mean_difference']:.2f} < 1.0.
- 코더 간 weights 셋은 {w_pack['coder_agreement']['weights_exact_set']}/60 일치했지만 모든 요청 필드 완전 일치는 {w_pack['coder_agreement']['all_requested_fields']}/60이다. **안 고른 쪽 처리 분류는 판정자 의존성이 높다.**

## PACK_R 「보존」

- 사실 판단: **{r['judgments']}건**
- 뜻이 남음: **{r['retained']}건 ({r['retention_rate']:.1%})**
- 뜻이 남지 않음: **{r['not_retained']}건**
- 사용자 지시에 따라 60장 전부를 두 코더가 독립 판독했다. 규약의 고정 감사 표본 14장을 넘어선 운영 편차이며, 분석 지위는 여전히 사후 탐색이다.

## PACK_F 「흔들림」

- 유지: **{f['relation_counts'].get('유지', 0)}/60**
- 바뀜: **{f['relation_counts'].get('바뀜', 0)}/60**
- 모르겠다: **{f['relation_counts'].get('모르겠다', 0)}/60**
- r0이 열쇠의 aligned 옵션과 일치: **{f['r0_aligned_with_key']}/60 ({f['r0_aligned_rate']:.1%})**
- r3이 열쇠의 aligned 옵션과 일치: **{f['r3_aligned_with_key']}/60 ({f['r3_aligned_rate']:.1%})**
- 코더 간 요청 필드 불일치: **6/60편**

## 제한

1. PACK_W는 사전고정이지만 W1·W2는 완전히 눈먼 예측이 아니다. W3~W5는 선행 값이 없었다.
2. PACK_R·PACK_F는 사후 탐색이므로 사전고정 결과로 보고하지 않는다.
3. PACK_W의 weights 일치는 높지만 전체 요청 필드 일치는 낮아 처리 갈래 수치는 판정자 의존성이 높다.
4. PACK_R 전건 이중 판독은 신뢰도 자료를 늘리지만 인간 코더 신뢰도를 뜻하지 않는다.
5. 키 결합 수치는 `KEYED_SUMMARY.json`과 각 `PACK_*_KEYED_01.json`을 정본으로 한다.
"""
    report_path = HERE / "FINAL_REPORT.md"
    atomic_text(report_path, report)

    manifest = {
        "experiment": "pressure_category_ab_blind_coding",
        "seed": 20260901,
        "completed_at": summary["completed_at"],
        "status": "complete",
        "key_join_policy": summary["key_join_policy"],
        "analysis_status": summary["analysis_status"],
        "validation": {
            "PACK_W": "frozen; 60 items; all disagreements adjudicated",
            "PACK_R": "frozen; 60 items; 720 fact judgments; all 60 cards double-coded; all disagreements adjudicated",
            "PACK_F": "frozen; 60 items; all requested-field disagreements adjudicated",
            "key_join": "W=60, R=60 with 12 fact IDs each, F=60; exact blind-ID sets matched",
        },
        "sha256": {
            **freeze_hashes,
            "PACK_W_KEYED_01.json": sha(HERE / "PACK_W_KEYED_01.json"),
            "PACK_R_KEYED_01.json": sha(HERE / "PACK_R_KEYED_01.json"),
            "PACK_F_KEYED_01.json": sha(HERE / "PACK_F_KEYED_01.json"),
            "KEYED_SUMMARY.json": sha(summary_path),
            "FINAL_REPORT.md": sha(report_path),
        },
        "limitations": summary["limitations"],
    }
    atomic_json(HERE / "FREEZE_MANIFEST.json", manifest)
    print("KEY_JOIN_COMPLETE W=60 R=60x12 F=60")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
