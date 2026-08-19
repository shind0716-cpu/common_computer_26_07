"""[민옥 트랙 · 시나리오 검사기] material_lint v0 — 재료(사실·사연·앵커)의 측정 가능성 린트.

지시: 작업 요청 2026-08-19 (시나리오 검사기 단독 스크립트). 실호출 0.
단독 도구 규약: 표준 라이브러리만(외부 패키지 0) · 리포의 다른 모듈 import 금지
(경로 규칙 예외 — 인자로 받은 경로만 사용, 작업 요청 명시 승인분).

사용법:
  PYTHONUTF8=1 python tools/material_lint.py \
      --facts data/facts/facts_issue_camp.json \
      --issue data/issues/issue_camp.json \
      --anchors data/facts/anchors_issue_camp.json
  옵션: --budget N   수첩 예산(기본 500) — 검사 [4]의 비교 기준
        --suggest    앵커가 없거나 자기 적중에 실패한 사실에 앵커 후보 제안

앵커 파일 형식 (스키마 무변경 임시안):
  {"fact_id": ["정규식", ...], "_allowlist": [{"anchor_fact", "hits_fact", "reason"}], "_comment": ...}
  "_" 프리픽스 키는 앵커가 아니다. 첫 실물 data/facts/anchors_issue_camp.json 은
  analyze_solo.py ANCHORS(정본)를 문면 그대로 옮긴 사본이다.

검사 항목 (v0):
  [1] 자기 적중   각 앵커가 자기 사실 원문에서 걸리는가 (전부 O 필수)
  [2] 교차 오발   다른 사실 원문에 걸리는 앵커 0 (_allowlist 항목은 사유와 함께 통과 처리·표시)
  [3] 본문 누출   issue 의 텍스트 필드(메타·"_" 프리픽스 제외)에서 걸리는 앵커 0
  [4] 예산        사실 원문 총자수(공백 포함 len) < 수첩 예산
  [5] 태그 완비   favors / critical / share 키가 전 사실에 있는가 (favors null = 중립 표기로 인정·표시)
  [6] 위치 편향   favors 진영별 목록 앞/뒤 절반 분포 보고 (통과/실패 아님 — 경고 수준)
  +  표기 확장    숫자 앵커의 표기 변형(콤마 유무·물결/하이픈·띄어쓰기)을 정규식으로 자동
                  확장해 검사에 사용. 의미 동의어 확장은 하지 않는다(설계 결정 — 의미
                  매칭은 판정기 층의 몫).

종료 코드: [1]~[5] 전부 통과 0, 하나라도 실패 1. ([6]은 보고 전용.)

실행 예시 (camp 재료, 2026-08-19 실측 — 이 출력이 곧 기지 결과):
  $ PYTHONUTF8=1 python tools/material_lint.py --facts data/facts/facts_issue_camp.json \
        --issue data/issues/issue_camp.json --anchors data/facts/anchors_issue_camp.json
  ==== material_lint v0 — 시나리오 재료 검사 ====
  재료: 사실 12개 · 앵커 12개(표기 확장 적용 4개) · issue 텍스트 필드 3개(title, question, body)

  [1] 자기 적중   PASS  12/12
  [2] 교차 오발   PASS  오발 1건 — 전부 허용 목록 처리
      - 허용: fact_camp_01 앵커 '38[,.]?000' -> fact_camp_05 원문 "다림재의 38,000원 패키지는 평일 기준이라 주말엔 1인 51,000원이다"
        (사유: f05 원문('다림재의 38,000원 패키지는 평일 기준이라…')이 f01의 수치 38,000원을 의도적으로 인용해 두 사실을 잇는 설계(팩트스펙의 의도적 중복) — f05 발화가 f01 앵커로도 잡히는 것은 정본 앵커의 알려진 공유 수치)
  [3] 본문 누출   PASS  0건 (검사 필드: title, question, body)
  [4] 예산        PASS  사실 원문 총 409자 < 수첩 예산 500자
  [5] 태그 완비   PASS  favors/critical/share 12/12 기입 (favors null=중립 1개: fact_camp_04)
  [6] 위치 편향   보고  favors 분포 앞절반/뒤절반 — 다림재 3/2 · 무레온 2/4 · 중립 1/0

  ==== 결과: 통과 (종료 코드 0) ====
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ISSUE_META_KEYS = {"schema_ver", "created_by", "created_at", "issue_id",
                   "source", "source_meta"}


# ── 로딩 ────────────────────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_anchors(path: str) -> tuple[dict[str, list[str]], list[dict]]:
    doc = load_json(path)
    anchors = {k: v for k, v in doc.items() if not k.startswith("_")}
    for fid, pats in anchors.items():
        if not isinstance(pats, list) or not all(isinstance(p, str) for p in pats):
            raise SystemExit(f"[형식 오류] {fid}: 앵커 값은 정규식 문자열 리스트여야 한다")
    return anchors, doc.get("_allowlist", [])


def issue_text_fields(issue: dict) -> dict[str, str]:
    """검사 대상 텍스트 필드 — 최상위 str 값 중 메타·'_' 프리픽스 제외 (title·question·body 류)."""
    return {k: v for k, v in issue.items()
            if isinstance(v, str) and not k.startswith("_") and k not in ISSUE_META_KEYS}


# ── 표기 변형 자동 확장 (숫자 앵커 한정 — 의미 동의어 확장 없음) ────────────

def expand_notation(pat: str) -> str:
    """콤마 숫자·물결/하이픈 범위·숫자+한글 단위의 표기 변형을 흡수하는 정규식으로 확장.
    이미 확장된 패턴(문자 클래스·\\s* 포함)은 매치되지 않아 그대로 통과한다."""
    out = re.sub(r"(\d{1,3}),(\d{3})", r"\1[,.]?\\s*\2", pat)      # 38,000 -> 콤마/점/없음+공백
    out = re.sub(r"(\d+)~(\d+)", r"\1\\s*[~\\-]\\s*\2", out)       # 17~18 -> 물결/하이픈+공백
    out = re.sub(r"(\d)([가-힣])", r"\1\\s*\2", out)               # 60명 -> 숫자·단위 사이 공백
    return out


# ── 검사 ────────────────────────────────────────────────────────────────────

def check_self_hit(facts: list[dict], patterns: dict[str, list[str]]) -> tuple[bool, list[str]]:
    lines, ok = [], True
    text_by_id = {f["fact_id"]: f["text"] for f in facts}
    for fid in text_by_id:
        pats = patterns.get(fid)
        if not pats:
            ok = False
            lines.append(f"    - {fid}: 앵커 없음")
            continue
        misses = [p for p in pats if not re.search(p, text_by_id[fid])]
        if misses:
            ok = False
            for p in misses:
                lines.append(f"    - {fid} 앵커 '{p}' 이(가) 자기 원문에서 안 걸림: "
                             f"\"{text_by_id[fid]}\"")
    return ok, lines


def check_cross_hit(facts: list[dict], patterns: dict[str, list[str]],
                    allowlist: list[dict]) -> tuple[bool, list[str]]:
    lines, ok = [], True
    allowed = {(a["anchor_fact"], a["hits_fact"]): a.get("reason", "(사유 없음)")
               for a in allowlist}
    used = set()
    for f in facts:
        for fid, pats in patterns.items():
            if fid == f["fact_id"]:
                continue
            for p in pats:
                if not re.search(p, f["text"]):
                    continue
                key = (fid, f["fact_id"])
                if key in allowed:
                    used.add(key)
                    lines.append(f"    - 허용: {fid} 앵커 '{p}' -> {f['fact_id']} 원문 "
                                 f"\"{f['text']}\"\n      (사유: {allowed[key]})")
                else:
                    ok = False
                    lines.append(f"    - 오발: {fid} 앵커 '{p}' -> {f['fact_id']} 원문 "
                                 f"\"{f['text']}\"")
    for key in set(allowed) - used:
        lines.append(f"    - 주의: 허용 목록 {key[0]}->{key[1]} 은 실제로 발생하지 않음 (사문 항목)")
    return ok, lines


def check_issue_leak(fields: dict[str, str],
                     patterns: dict[str, list[str]]) -> tuple[bool, list[str]]:
    lines, ok = [], True
    for name, text in fields.items():
        for fid, pats in patterns.items():
            for p in pats:
                m = re.search(p, text)
                if m:
                    ok = False
                    s = max(0, m.start() - 20)
                    lines.append(f"    - {fid} 앵커 '{p}' -> issue.{name} "
                                 f"\"…{text[s:m.end() + 20]}…\"")
    return ok, lines


def check_budget(facts: list[dict], budget: int) -> tuple[bool, str]:
    total = sum(len(f["text"]) for f in facts)
    ok = total < budget
    return ok, f"사실 원문 총 {total}자 {'<' if ok else '>='} 수첩 예산 {budget}자"


def check_tags(facts: list[dict]) -> tuple[bool, list[str], str]:
    lines, ok = [], True
    neutral = []
    for f in facts:
        missing = [k for k in ("favors", "critical", "share") if k not in f]
        if missing:
            ok = False
            lines.append(f"    - {f['fact_id']}: {', '.join(missing)} 키 없음")
        elif f["favors"] is None:
            neutral.append(f["fact_id"])
    note = (f" (favors null=중립 {len(neutral)}개: {', '.join(neutral)})" if neutral else "")
    return ok, lines, note


def report_position_bias(facts: list[dict]) -> str:
    half = len(facts) // 2
    front, back = facts[:half], facts[half:]
    sides = []
    for side in sorted({str(f.get("favors")) for f in facts}, key=lambda s: s == "None"):
        label = "중립" if side == "None" else side
        nf = sum(1 for f in front if str(f.get("favors")) == side)
        nb = sum(1 for f in back if str(f.get("favors")) == side)
        sides.append(f"{label} {nf}/{nb}")
    return "favors 분포 앞절반/뒤절반 — " + " · ".join(sides)


# ── 앵커 제안기 (--suggest) ─────────────────────────────────────────────────

def suggest_candidates(text: str, corpus: str, k: int = 3) -> list[tuple[str, str]]:
    """그 사실에만 나오는(다른 사실·issue 텍스트에 없는) 부분문자열을 길이순으로 k개.
    반환: (원문 조각, 표기 확장 적용한 정규식 제안) 쌍. 위치가 겹치는 후보는 최소형만.
    어절 시작(문두 또는 공백 다음)에서 시작하는 조각만 — 어절 중간 조각은 앵커 품질이 낮다."""
    taken: list[tuple[int, int, str]] = []
    for length in range(2, 13):
        for i in range(len(text) - length + 1):
            if i > 0 and text[i - 1] != " ":
                continue
            s = text[i:i + length]
            if s != s.strip() or not s:
                continue
            if (i + length < len(text) and text[i + length].isdigit()
                    and (s[-1].isdigit() or s[-1] == ",")):
                continue                  # 숫자 시퀀스 중간 절단("4,0") 방지
            if s in corpus:
                continue
            if any(not (i + length <= a or i >= a + al) for a, al, _ in taken):
                continue
            taken.append((i, length, s))
            if len(taken) >= k:
                return [(s, expand_notation(re.escape(s))) for _, _, s in taken]
    return [(s, expand_notation(re.escape(s))) for _, _, s in taken]


# ── 결과지 ──────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="시나리오 재료 측정 가능성 린트 (v0)")
    ap.add_argument("--facts", required=True)
    ap.add_argument("--issue", required=True)
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--budget", type=int, default=500, help="수첩 예산(자), 기본 500")
    ap.add_argument("--suggest", action="store_true", help="실패·부재 사실에 앵커 후보 제안")
    args = ap.parse_args()

    facts = load_json(args.facts)["facts"]
    issue = load_json(args.issue)
    anchors_raw, allowlist = load_anchors(args.anchors)

    patterns: dict[str, list[str]] = {}
    n_expanded = 0
    for fid, pats in anchors_raw.items():
        expanded = [expand_notation(p) for p in pats]
        if expanded != pats:
            n_expanded += 1
        patterns[fid] = expanded

    fields = issue_text_fields(issue)
    print("==== material_lint v0 — 시나리오 재료 검사 ====")
    print(f"재료: 사실 {len(facts)}개 · 앵커 {len(patterns)}개"
          f"(표기 확장 적용 {n_expanded}개) · issue 텍스트 필드 {len(fields)}개"
          f"({', '.join(fields)})")
    print()

    fails = 0

    ok1, lines1 = check_self_hit(facts, patterns)
    n_self = sum(1 for f in facts
                 if patterns.get(f["fact_id"])
                 and all(re.search(p, f["text"]) for p in patterns[f["fact_id"]]))
    print(f"[1] 자기 적중   {'PASS' if ok1 else 'FAIL'}  {n_self}/{len(facts)}")
    print("\n".join(lines1)) if lines1 else None
    fails += 0 if ok1 else 1

    hollow = "" if patterns else " — 검사할 앵커가 0개인 공허한 통과"
    ok2, lines2 = check_cross_hit(facts, patterns, allowlist)
    n_allowed = sum(1 for l in lines2 if l.lstrip().startswith("- 허용"))
    n_bad = sum(1 for l in lines2 if l.lstrip().startswith("- 오발"))
    desc2 = (f"오발 {n_allowed}건 — 전부 허용 목록 처리" if ok2 and n_allowed
             else (f"0건{hollow}" if ok2 else f"오발 {n_bad}건 (허용 외)"))
    print(f"[2] 교차 오발   {'PASS' if ok2 else 'FAIL'}  {desc2}")
    print("\n".join(lines2)) if lines2 else None
    fails += 0 if ok2 else 1

    ok3, lines3 = check_issue_leak(fields, patterns)
    print(f"[3] 본문 누출   {'PASS' if ok3 else 'FAIL'}  "
          f"{0 if ok3 else len(lines3)}건{hollow} (검사 필드: {', '.join(fields)})")
    print("\n".join(lines3)) if lines3 else None
    fails += 0 if ok3 else 1

    ok4, desc4 = check_budget(facts, args.budget)
    print(f"[4] 예산        {'PASS' if ok4 else 'FAIL'}  {desc4}")
    fails += 0 if ok4 else 1

    ok5, lines5, note5 = check_tags(facts)
    print(f"[5] 태그 완비   {'PASS' if ok5 else 'FAIL'}  favors/critical/share "
          f"{len(facts) - len(lines5)}/{len(facts)} 기입{note5}")
    print("\n".join(lines5)) if lines5 else None
    fails += 0 if ok5 else 1

    print(f"[6] 위치 편향   보고  {report_position_bias(facts)}")

    if args.suggest:
        print()
        print("[제안] 앵커 후보 (--suggest — 부재·자기 적중 실패 사실만)")
        targets = [f for f in facts
                   if not patterns.get(f["fact_id"])
                   or any(not re.search(p, f["text"]) for p in patterns[f["fact_id"]])]
        if not targets:
            print("    (제안 대상 없음 — 전 사실 자기 적중)")
        for f in targets:
            others = [g["text"] for g in facts if g["fact_id"] != f["fact_id"]]
            corpus = "\n".join(others + list(fields.values()))
            cands = suggest_candidates(f["text"], corpus)
            shown = " · ".join(f"\"{s}\" (정규식: {rx})" for s, rx in cands) or "(후보 없음)"
            print(f"    - {f['fact_id']}: {shown}")

    print()
    verdict = "통과" if fails == 0 else f"실패 {fails}개 항목"
    print(f"==== 결과: {verdict} (종료 코드 {0 if fails == 0 else 1}) ====")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
