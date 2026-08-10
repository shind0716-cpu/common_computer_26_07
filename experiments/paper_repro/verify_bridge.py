# -*- coding: utf-8 -*-
"""논문 재현 트랙 — 브리지 계약 독립 검증기 (접합 계층 · 요한, 2026-08-10).

지위: 접합 계층의 **교차 리뷰 도구.** extractor·배분기(저자 충실 계층)가 자기 오딧을
갖고 있으나, 산출자와 검증자가 같은 코드를 공유하면 같은 오해를 두 번 통과시킨다.
그래서 이 검증기는 extract_facts / assign_perspective 를 **import 하지 않고**
README 「브리지 계약」과 저자 prompts/perspective.txt 지침에서 독립적으로 다시 구현했다.

무엇을 검사하나 (LLM 호출 0)
  [경성 — 하나라도 걸리면 exit 1. 브리지 계약 위반 = 하류(ledger·access_window) 무효]
    H1  facts[] 배열 순서 == origin_index == fact_id 순번 (인덱스↔ID 대응)
    H2  critical 이 bool · tags 가 빈 배열 (§7 임시 처리)
    H3  extractor 좌표 고정 (model gpt-5 · temperature 0)
    H4  관점 정확히 4개 = 에이전트 8명, 같은 관점 pro/con 쌍의 assigned_fact_ids 완전 동일
    H5  perspective_sets.sets 를 facts 순서로 번역한 결과 == agents 의 assigned_fact_ids
        (원형 보존과 번역이 어긋나면 저자 축과의 대응이 침묵 속에 끊긴다)
    H6  assigned_fact_ids ⊆ facts 의 fact_id 전집합 · seed == 20260810
    H7  issue.source == "paper" 이고 question 이 명시돼 있다 (§1′ 경계 1 — 폴백 금지)
    H8  bridge.py 실물 왕복 — sets 를 to_fact_ids 로 번역하면 assigned_fact_ids 와 같고
        역번역(to_positions)은 원 인덱스로 돌아온다. H5 가 자체 구현 대조라면 H8 은
        번역층(bridge.py) 그 자체를 검사한다 (2026-08-10 플랜 승인분)
    H9  완전성 — manifest 가 "단계 완료"를 주장하면 그 주장과 실물 파일을 대조한다
        (PR#34 리뷰: 빈 산출 루트가 "경성 전건 통과"로 끝나던 결함). sample_manifest
        의 표본 전건에 대해 issue 실물 필수, facts_manifest 존재 시 facts 실물 필수
        (예외: failed_parse), assignments_manifest 존재 시 assignment 실물 필수
        (예외: failed_parse ∪ excluded_refined_lt5 ∪ skipped). manifest 부재 =
        해당 단계 미실행으로 보고 검사를 생략하되 그 사실을 출력에 명시한다.
  [연성 — 저자 프롬프트 지침. 위반은 집계·보고만 (지침이지 형식 계약이 아님)]
    S1  모든 팩트가 최소 1개 관점에 등장 (커버리지)
    S2  전체 팩트를 다 가진 관점 없음
    S3  important(critical) 팩트가 각 관점에 포함
  [분포 — 판정 없이 기록만. 리뷰에서 나온 관찰: critical 비율이 1에 붙으면
    관점 간 정보 비대칭이 무너진다 — 히든 프로필 성립 여부의 관찰 지표]
    D1  항목별 critical 비율 · refined 팩트 수

사용:
  PYTHONUTF8=1 python experiments/paper_repro/verify_bridge.py --data-dir experiments/paper_repro/fixtures/data
  PYTHONUTF8=1 python experiments/paper_repro/verify_bridge.py                # 기본: data/ (라이브 산출)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge  # noqa: E402 — H8 전용. H1~H7 은 종전대로 bridge 미사용(독립 구현 유지)

EXPECT_SEED = 20260810
EXPECT_MODEL = "gpt-5"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def verify_issue(issue: dict, errors: list[str]) -> None:
    iid = issue.get("issue_id", "?")
    if issue.get("source") != "paper":
        errors.append(f"{iid}: H7 source != paper ({issue.get('source')})")
    q = issue.get("question")
    if not isinstance(q, str) or not q.strip():
        errors.append(f"{iid}: H7 question 부재/공백 — §1′ 폴백은 이 트랙에서 금지")


def verify_facts(doc: dict, errors: list[str]) -> list[str]:
    """경성 H1~H3. 반환값은 fact_id 목록(배열 순서 그대로) — assignment 대조에 쓴다."""
    iid = doc.get("issue_id", "?")
    ex = doc.get("extractor", {})
    if not (ex.get("model") == EXPECT_MODEL and ex.get("temperature") == 0.0):
        # 픽스처(model=fixture)는 호출자가 --fixture 로 완화한다
        errors.append(f"{iid}: H3 extractor 좌표 이탈 ({ex.get('model')}, {ex.get('temperature')})")
    suffix = iid[len("issue_"):]
    ids = []
    for i, f in enumerate(doc.get("facts", [])):
        fid = f.get("fact_id", "?")
        ids.append(fid)
        if f.get("origin_index") != i:
            errors.append(f"{iid}: H1 facts[{i}] origin_index={f.get('origin_index')} (배열 순서와 불일치)")
        if fid != f"fact_{suffix}_{i + 1:02d}":
            errors.append(f"{iid}: H1 fact_id {fid} != fact_{suffix}_{i + 1:02d} (순번 규칙 위반)")
        if not isinstance(f.get("critical"), bool):
            errors.append(f"{iid}: H2 critical 이 bool 아님 ({type(f.get('critical')).__name__})")
        if f.get("tags") != []:
            errors.append(f"{iid}: H2 tags != [] ({f.get('tags')})")
    return ids


def verify_assignment(doc: dict, fact_ids: list[str],
                      errors: list[str], soft: list[str]) -> None:
    iid = doc.get("issue_id", "?")
    if doc.get("seed") != EXPECT_SEED:
        errors.append(f"{iid}: H6 seed {doc.get('seed')} != {EXPECT_SEED}")
    agents = doc.get("agents", [])
    if len(agents) != 8:
        errors.append(f"{iid}: H4 에이전트 {len(agents)}명 != 8")
        return
    sets = (doc.get("perspective_sets") or {}).get("sets")
    if not (isinstance(sets, list) and len(sets) == 4):
        errors.append(f"{iid}: H4 perspective_sets.sets 가 4개 배열 아님")
        return
    all_ids = set(fact_ids)
    n = len(fact_ids)
    used = set()
    critical_missing = 0
    for k in range(4):
        a, b = agents[2 * k], agents[2 * k + 1]
        if a.get("perspective") != b.get("perspective"):
            errors.append(f"{iid}: H4 쌍 {k} 관점 불일치")
        if {a.get("stance"), b.get("stance")} != {"pro", "con"}:
            errors.append(f"{iid}: H4 쌍 {k} stance 가 pro/con 쌍 아님")
        if a.get("assigned_fact_ids") != b.get("assigned_fact_ids"):
            errors.append(f"{iid}: H4 쌍 {k} assigned_fact_ids 불일치 — 저자 규칙 위반")
        group = sets[k]
        bad = [i for i in group if not isinstance(i, int) or isinstance(i, bool)
               or i < 0 or i >= n]
        if bad:
            errors.append(f"{iid}: H5 sets[{k}] 무효 인덱스 {bad}")
            continue
        translated = [fact_ids[i] for i in group]
        if translated != a.get("assigned_fact_ids"):
            errors.append(f"{iid}: H5 sets[{k}] 번역({translated}) != assigned({a.get('assigned_fact_ids')})")
        if not set(a.get("assigned_fact_ids", [])) <= all_ids:
            errors.append(f"{iid}: H6 미지 fact_id 참조")
        used.update(group)
        if len(set(group)) == n:
            soft.append(f"{iid}: S2 관점 {k} 가 전체 팩트 보유")
    if used != set(range(n)):
        soft.append(f"{iid}: S1 미등장 팩트 인덱스 {sorted(set(range(n)) - used)}")
    # S3 는 facts 문서가 필요해 호출자에서 계산하지 않고 여기선 생략하지 않는다 —
    # fact_ids 와 병행 전달되는 critical 정보가 없으므로 호출자가 채운다 (아래 main).
    _ = critical_missing


def check_completeness(root: Path) -> tuple[list[str], list[str]]:
    """H9 — manifest 의 완료 주장과 실물 파일 대조. (경성 오류 목록, 안내 목록) 반환."""
    errors: list[str] = []
    notes: list[str] = []
    sm = root / "sample_manifest.json"
    if not sm.exists():
        notes.append("H9 생략: sample_manifest 부재 — 표본 미확정 루트(픽스처 등)")
        return errors, notes
    expected = [x["issue_id"] for x in _load(sm)["sample"]["ids"]]
    for iid in expected:
        if not (root / "issues" / f"{iid}.json").exists():
            errors.append(f"{iid}: H9 표본에 있는 issue 실물 부재")

    fm = root / "facts_manifest.json"
    failed_ids: set[str] = set()
    excluded_ids: set[str] = set()
    if not fm.exists():
        notes.append("H9 부분 생략: facts_manifest 부재 — 추출 단계 미실행으로 간주")
        return errors, notes
    fman = _load(fm)
    failed_ids = {x["issue_id"] for x in fman.get("failed_parse", [])}
    excluded_ids = set(fman.get("excluded_refined_lt5", []))
    for iid in expected:
        if iid in failed_ids:
            continue  # 설명된 누락 — extractor 가 사유를 기록했다
        if not (root / "facts" / f"facts_{iid}.json").exists():
            errors.append(f"{iid}: H9 facts 실물 부재 — manifest 에 설명(failed_parse) 없음")

    am = root / "assignments_manifest.json"
    if not am.exists():
        notes.append("H9 부분 생략: assignments_manifest 부재 — 배분 단계 미실행으로 간주")
        return errors, notes
    skipped_ids = {x["issue_id"] for x in _load(am).get("skipped", [])}
    allowed_missing = failed_ids | excluded_ids | skipped_ids
    for iid in expected:
        if iid in allowed_missing:
            continue
        if not (root / "assignments" / f"assignment_{iid}.json").exists():
            errors.append(f"{iid}: H9 assignment 실물 부재 — manifest 에 설명 없음")
    return errors, notes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=HERE / "data")
    ap.add_argument("--fixture", action="store_true",
                    help="픽스처 검사 모드 — extractor 좌표(H3) 검사를 생략")
    args = ap.parse_args()
    root = Path(args.data_dir).resolve()

    issues = sorted((root / "issues").glob("issue_*.json"))
    if not issues:
        print(f"[FAIL] issues/ 가 비어 있음: {root}")
        sys.exit(1)

    errors: list[str] = []
    soft: list[str] = []
    dist: list[dict] = []
    n_facts_seen = 0
    n_assign_seen = 0

    for ip in issues:
        issue = _load(ip)
        iid = issue.get("issue_id", ip.stem)
        verify_issue(issue, errors)

        fp = root / "facts" / f"facts_{iid}.json"
        if not fp.exists():
            continue  # 추출 전 — 이슈만 검사
        n_facts_seen += 1
        fdoc = _load(fp)
        local_errors: list[str] = []
        fact_ids = verify_facts(fdoc, local_errors)
        if args.fixture:
            local_errors = [e for e in local_errors if ": H3 " not in e]
        errors.extend(local_errors)
        crit = [f["fact_id"] for f in fdoc.get("facts", []) if f.get("critical") is True]
        dist.append({"issue_id": iid, "n_facts": len(fact_ids),
                     "critical_ratio": round(len(crit) / len(fact_ids), 3) if fact_ids else None})

        ap_ = root / "assignments" / f"assignment_{iid}.json"
        if not ap_.exists():
            continue
        n_assign_seen += 1
        adoc = _load(ap_)
        verify_assignment(adoc, fact_ids, errors, soft)
        # S3: critical 팩트가 각 관점에 포함되는가 (연성)
        sets = (adoc.get("perspective_sets") or {}).get("sets") or []
        crit_idx = {f["origin_index"] for f in fdoc.get("facts", []) if f.get("critical") is True}
        for k, group in enumerate(sets):
            if isinstance(group, list) and not crit_idx <= {i for i in group if isinstance(i, int)}:
                soft.append(f"{iid}: S3 관점 {k} 에 critical 미포함")
        # H8: bridge 실물 왕복 (경성) — 번역층 자체를 데이터로 검사
        agents = adoc.get("agents", [])
        if len(agents) == 8 and isinstance(sets, list) and len(sets) == 4:
            for k, group in enumerate(sets):
                try:
                    translated = bridge.to_fact_ids(fdoc, group)
                    back = bridge.to_positions(fdoc, translated)
                except ValueError as e:
                    errors.append(f"{iid}: H8 번역 실패 sets[{k}] — {e}")
                    continue
                if translated != agents[2 * k].get("assigned_fact_ids"):
                    errors.append(f"{iid}: H8 sets[{k}] bridge 번역 != assigned_fact_ids")
                if back != list(group):
                    errors.append(f"{iid}: H8 sets[{k}] 왕복 비항등 {group} -> {back}")

    h9_errors, h9_notes = check_completeness(root)
    errors.extend(h9_errors)

    print(f"[verify_bridge] root={root}")
    print(f"  이슈 {len(issues)} · facts {n_facts_seen} · assignments {n_assign_seen}")
    for note in h9_notes:
        print(f"  [안내] {note}")
    if dist:
        ratios = sorted(d["critical_ratio"] for d in dist if d["critical_ratio"] is not None)
        mid = ratios[len(ratios) // 2] if ratios else None
        print(f"  D1 critical 비율 중앙 {mid} · 1.0 항목 {sum(1 for r in ratios if r == 1.0)}건"
              f" · 0.9 이상 {sum(1 for r in ratios if r >= 0.9)}건")
    for s in soft:
        print(f"  [연성] {s}")
    if errors:
        for e in errors:
            print(f"  [경성 FAIL] {e}")
        print(f"[verify_bridge] 경성 위반 {len(errors)}건 — 브리지 계약 위반")
        sys.exit(1)
    print(f"[verify_bridge] 경성 전건 통과 (연성 {len(soft)}건 보고)")


if __name__ == "__main__":
    main()
