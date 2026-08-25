"""anchor_check.py — 안현수 개인 제작 앵커 검사 (팀 재검수 필요)

⚠ 고지 — 개인 제작 코드, 팀 재검수 필요
- 이 코드는 안현수가 개인적으로 작성한 것이다. 팀이 공유·합의한 정식 검수 도구가 아니며,
  팀 차원의 재검수를 거치지 않았다. 따라서 이 결과("12/12 적중")를 팀 공식 검증 결과로
  취급하면 안 되며, 잠정 수치로만 봐야 한다.
- 요청: 이 코드의 로직이 타당한지, 팀의 정식 앵커 스캔(있다면)과 같은 잣대인지 팀이 재검수해 주기 바란다.
- 이 검사는 "토론 전" 단계만 본다: 팩트 원문/본문 사이에서 앵커가 고유한지. 실제 토론 산출물
  (에이전트 발화)에서 앵커 출현을 세어 "팩트가 살아남았는지"를 판정하는 단계는 포함하지 않는다
  (그 단계는 토론을 돌린 뒤에야 가능하며 여기 없음).

검사 항목 (요한 전문의 3개 지표를 재현):
  1) 앵커 적중   — 각 앵커가 자기 팩트 텍스트 안에 있는가 (목표 12/12)
  2) 교차 오작동 — 앵커가 다른 팩트 텍스트에도 잡히는가 (목표 0)
  3) 본문 누출   — 앵커가 이슈 본문에 있는가 (목표 0; 본문에 팩트가 새면 미공유 구조가 깨짐)

사용법:
  facts JSON의 각 팩트에 "_anchor" 필드가 있으면 그걸 쓰고, 없으면 ANCHORS dict로 넘긴다.
  python anchor_check.py                      # data/ 아래 3종 자동 검사
"""
import json
from pathlib import Path


def anchor_check(issue_body: str, facts: list, anchors: dict = None):
    """
    issue_body: 이슈 본문 문자열
    facts: [{"fact_id":..., "text":..., "_anchor"(선택):...}, ...]
    anchors: {fact_id: 앵커문자열} — 주면 이걸 우선 사용. 없으면 각 팩트의 _anchor 필드 사용.
    반환: (ok: bool, report: dict)
    """
    def anchor_of(f):
        if anchors and f["fact_id"] in anchors:
            return anchors[f["fact_id"]]
        return f.get("_anchor")

    hit = 0
    cross = 0
    leak = 0
    problems = []
    missing = []

    for f in facts:
        a = anchor_of(f)
        if not a:
            missing.append(f["fact_id"])
            continue
        # 1) 적중: 자기 팩트에 있는가
        if a in f["text"]:
            hit += 1
        else:
            problems.append(f"{f['fact_id']}: 앵커 '{a}' 가 자기 팩트에 없음")
        # 2) 교차 오작동: 다른 팩트에 있는가
        for g in facts:
            if g["fact_id"] != f["fact_id"] and a in g["text"]:
                cross += 1
                problems.append(f"{f['fact_id']}: 앵커 '{a}' 가 {g['fact_id']} 에도 있음")
        # 3) 본문 누출: 본문에 있는가
        if a in issue_body:
            leak += 1
            problems.append(f"{f['fact_id']}: 앵커 '{a}' 가 본문에 노출됨")

    n = len(facts)
    report = {
        "n_facts": n,
        "anchor_hit": f"{hit}/{n}",
        "cross_fire": cross,
        "body_leak": leak,
        "missing_anchor": missing,
        "problems": problems,
    }
    ok = (hit == n and cross == 0 and leak == 0 and not missing)
    return ok, report


def _run_dir(base="data"):
    base = Path(base)
    ids = ["issue_layoff", "issue_triage", "issue_outreach"]
    all_ok = True
    for iid in ids:
        issue = json.loads((base / "issues" / f"{iid}.json").read_text(encoding="utf-8"))
        facts = json.loads((base / "facts" / f"facts_{iid}.json").read_text(encoding="utf-8"))["facts"]
        ok, rpt = anchor_check(issue["body"], facts)
        all_ok = all_ok and ok
        print(f"\n=== {iid} ===")
        print(f"  앵커 적중 {rpt['anchor_hit']} | 교차 오작동 {rpt['cross_fire']} | 본문 누출 {rpt['body_leak']}")
        if rpt["missing_anchor"]:
            print(f"  ⚠ 앵커 없는 팩트: {rpt['missing_anchor']}")
        for p in rpt["problems"]:
            print(f"  ⚠ {p}")
        if ok:
            print("  ✓ 통과 (단, 개인 제작 코드 — 팀 재검수 필요, 잠정 수치)")
    print("\n" + ("전체 통과 ✓ (개인 제작 검사 — 팀 재검수 필요)" if all_ok else "일부 미통과 ✗"))
    return all_ok


if __name__ == "__main__":
    _run_dir()
