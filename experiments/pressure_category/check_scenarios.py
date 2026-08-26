"""[압박×카테고리] 재료 전수 점검 — LLM 0콜, 파일만 읽는다.

check_materials.py 는 **계약**을 본다(표식 고유·구조 대칭·누출). 이 스크립트는 그 위에서
**GUIDE_scenario_writing_2026-08-25.md 가 실호출 60판으로 적어 둔 축**을 센다. 둘은 겹치지
않는다 — 계약을 통과해도 여기서 걸릴 수 있고, 실제로 걸린다.

기계가 세는 것 (아래 7):
  ① 편집 동결 — 실호출 판이 가리키는 재료는 고치면 해시가 어긋난다 (LIMITS §3 선례)
  ② 표식 어절 — GUIDE §2. 한 낱말이라야 남는다. 두 낱말이면 줄고, 조사로 이으면 가운뎃점이 된다
  ③ 표식 조사 — §2-2 갈래 하나. `와`·`과`·`및`
  ④ 표식 수치 — 2026-08-25 사용자 검수로 금지 (숫자 기억을 재어 오염)
  ⑤ 표식이 사실 문장을 통째로 베꼈나 — 요약이 아니라 복사면 스캔이 사실상 문장 검색이 된다
  ⑥ 카테고리 낱말의 종류가 섞였나 — 조건어/당사자필요/사람이하는일/생활영역/규범어
  ⑦ 갈래 혼합 — 사실이 당사자를 지목하는데 카테고리는 조건어·규범어인 경우
  ⑧ 같은 원본 무대에서 나온 재료가 둘 이상 — 하나가 대체본이거나 남의 담당일 수 있다.
     `_lineage.variant_of` 가 있으면 일부러 만든 판본이고, 없으면 확인이 필요하다.
     **소유자는 파일에 안 적혀 있다. WORKLOG 로 확인하라** — 2026-08-26 에 남의 담당 재료를
     제 것으로 알고 고쳤다가 되돌린 일이 있다.

기계가 **못** 세는 것 (사람이 봐야 하는 것, 아래 6): 아래 표로 출력만 하고 판정하지 않는다.
  규칙 ⑤(카테고리가 선택지를 따라가나) · 논증 종류(§4-1) · 손해 대상(§4-2) ·
  낱말 넓이 · favors 방향 · 민감 표현

사용: PYTHONUTF8=1 python experiments/pressure_category/check_scenarios.py [재료파일]
      (인자 생략 시 materials/*.json 전량. 종료코드는 항상 0 — 이 스크립트는 관문이 아니라 점검표다)
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATERIALS_DIR = HERE / "materials"
RUNS_DIR = HERE / "runs"

# 카테고리 낱말 종류 — 사람이 붙인 분류. 새 낱말은 `당사자필요` 로 떨어진다.
KIND: dict[str, str] = {}
for _w in "접근성 편의 안전 평온 위생 이동권 여유 예측 시간 접근권 예측성".split():
    KIND[_w] = "조건어"
for _w in "돌봄 책임".split():
    KIND[_w] = "사람이하는일"
for _w in "식사 이동 수면 교육 환경".split():
    KIND[_w] = "생활영역"
for _w in "자율성 공정성 배려".split():
    KIND[_w] = "규범어"

PARTY_PAT = re.compile(r"\d+호|첫째|둘째|막내|보호자|담당자|이용자|신청자")


def live_counts() -> collections.Counter:
    """실호출 판 수를 재료별로 센다 (_dry 제외)."""
    c: collections.Counter = collections.Counter()
    for p in glob.glob(str(RUNS_DIR / "**" / "run_*.json"), recursive=True):
        q = p.replace(os.sep, "/")
        if "/runs/_dry/" in q:
            continue
        parts = q.split("/runs/")[1].split("/")
        c[parts[1] if len(parts) >= 3 else "issue_dorm"] += 1
    return c


def josa_errors(d: dict) -> list[str]:
    """선택지 이름 뒤 조사가 받침 규칙에 맞나. 이름을 바꾸면 여기가 조용히 어긋난다."""
    pairs = [("은", "는"), ("과", "와"), ("이", "가"), ("을", "를")]
    texts = [d["stub"]] + [f["text"] for f in d["facts"]] + [d["prompts"]["final_poll"]]
    out = []
    for opt in d["options"]:
        c = opt.strip()[-1]
        if not ("가" <= c <= "힣"):
            continue
        bat = (ord(c) - 0xAC00) % 28 != 0
        for a, b in pairs:
            wrong, right = (b, a) if bat else (a, b)
            for t in texts:
                if opt + wrong in t:
                    out.append(f"{opt}{wrong} → {opt}{right}")
    return sorted(set(out))



def inspect(path: Path, live: collections.Counter) -> dict | None:
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("schema") != "pressure_materials_v0":
        return {"file": path.name, "bundle": True}
    facts = d["facts"]
    anchors = [f["anchor"] for f in facts]
    cats = d["categories"]
    kinds = collections.Counter(KIND.get(c, "당사자필요") for c in cats)
    party_named = sum(1 for f in facts if PARTY_PAT.search(f["text"]))
    # 표식이 사실 문장에서 차지하는 글자 비율 — 0.5 넘으면 요약이 아니라 복사에 가깝다
    copy_ratio = [(f["id"], round(len(f["anchor"]) / max(len(f["text"]), 1), 2))
                  for f in facts if len(f["anchor"]) / max(len(f["text"]), 1) > 0.4]
    lin = d.get("_lineage", {})
    return {
        "file": path.name,
        "bundle": False,
        "source_scenario": lin.get("source_scenario_id"),
        "variant_of": lin.get("variant_of"),
        "issue": d["issue_id"],
        "frozen": live.get(d["issue_id"], 0),
        "track": "둘" if any("party" in f for f in facts) else "하나",
        "kinds": kinds,
        "anchor_avg": round(sum(len(a.split()) for a in anchors) / len(anchors), 1),
        "anchor_max": max(len(a.split()) for a in anchors),
        "multiword": [a for a in anchors if len(a.split()) > 1],
        "josa": [a for a in anchors if re.search(r"(와|과|및)\s", a)],
        "digit": [a for a in anchors if re.search(r"\d", a)],
        "copy": copy_ratio,
        "josa": josa_errors(d),
        "kind_mixed": len(kinds) > 1,
        "track_mixed": (party_named >= 6
                        and all(KIND.get(c, "당사자필요") in ("조건어", "규범어") for c in cats)),
    }


def main() -> int:
    live = live_counts()
    targets = ([Path(sys.argv[1])] if len(sys.argv) > 1
               else [p for p in sorted(MATERIALS_DIR.glob("*.json"))
                     if p.name != "MATERIALS_TEMPLATE.json"])
    rows = [r for r in (inspect(t, live) for t in targets) if r]

    print(f"{'재료':32s} {'갈래':4s} {'동결':>5s} {'표식평균/최대':>12s}  {'카테고리 종류'}")
    print("-" * 100)
    for r in rows:
        if r["bundle"]:
            print(f"{r['file']:32s} (번들 — pressure_materials_v0 개별 계약 미충족)")
            continue
        fz = f"{r['frozen']}판" if r["frozen"] else "-"
        kd = "+".join(f"{k}{v}" for k, v in r["kinds"].most_common())
        print(f"{r['issue']:32s} {r['track']:4s} {fz:>5s} "
              f"{r['anchor_avg']:>6.1f}/{r['anchor_max']:<5d} {kd}")

    real = [r for r in rows if not r["bundle"]]
    print("\n=== 기계가 잡은 것 ===")
    findings = [
        ("표식이 두 낱말 이상 (GUIDE §2 — 줄여 쓰면 놓친다)", "multiword", lambda v: len(v) >= 6),
        ("표식에 와/과/및 (§2-2 갈래 하나 — 가운뎃점이 된다)", "josa", bool),
        ("수치 표식 (2026-08-25 검수로 금지)", "digit", bool),
        ("표식이 사실 문장의 40% 넘음 — 요약이 아니라 복사", "copy", lambda v: len(v) >= 3),
    ]
    for label, key, hit in findings:
        rs = [r for r in real if hit(r[key])]
        print(f"\n[{label}] {len(rs)}건")
        for r in rs:
            v = r[key]
            print(f"   {r['issue']:32s} {len(v)}개  예: {v[:3]}")
    josa_bad = [r for r in real if r["josa"]]
    print()
    print(f"[선택지 이름 뒤 조사 어긋남] {len(josa_bad)}건")
    for r in josa_bad:
        print(f"   {r['issue']:32s} {r['josa']}")


    print(f"\n[카테고리 낱말 종류가 섞임] "
          f"{len([r for r in real if r['kind_mixed']])}건")
    for r in real:
        if r["kind_mixed"]:
            print(f"   {r['issue']:32s} {dict(r['kinds'])}")

    print(f"\n[갈래 혼합 — 사실은 당사자를 지목하는데 카테고리는 조건어·규범어] "
          f"{len([r for r in real if r['track_mixed']])}건")
    for r in real:
        if r["track_mixed"]:
            print(f"   {r['issue']:32s} {list(r['kinds'])}")

    src = collections.defaultdict(list)
    for r in real:
        if r["source_scenario"]:
            src[r["source_scenario"]].append(r)
    dup = {k: v for k, v in src.items() if len(v) > 1}
    print()
    print(f"[같은 원본 무대에서 나온 재료가 둘 이상] {len(dup)}건")
    for k, v in sorted(dup.items()):
        print(f"   원본 '{k}' <- {len(v)}벌")
        for r in v:
            mark = (f"판본 (variant_of={r['variant_of']})" if r["variant_of"]
                    else "** 확인 필요 — 대체본이거나 남의 담당일 수 있다 **")
            print(f"      {r['issue']:32s} {mark}")

    print("\n=== 기계가 못 세는 것 — 사람이 재료마다 물어야 한다 ===")
    for i, q in enumerate([
        "규칙 ⑤ — 카테고리마다: 이걸 반대쪽 선택지에서도 똑같이 할 수 있나? 예면 못 쓴다 (§3). "
        "잣대는 '사람이 하는 일인가'가 아니라 '선택지를 바꾸면 따라가는가'다(요한 2026-08-26) — "
        "`직원이 정중하다`는 어느 가게도 할 수 있어 따라가지만 `몰리는 때에 상이 늦다`는 "
        "그 가게의 자리 수·인력에서 나오므로 안 따라간다. 사람 일이라고 다 쳐내지 마라.",
        "논증 종류 — 한쪽이 시설이고 다른 쪽이 남들의 인상·후기로 갈리지 않았나 (§4-1)",
        "손해 대상 — 각 선택지 단점 셋을 세로로 놓고: 이 단점은 누구에게 가나 (§4-3)",
        "낱말 넓이 — 넓은 가치어가 반대편 사실을 빨아들이지 않나 (§4-2 마지막 문단)",
        "favors 방향 — 문장이 실제로 편드는 쪽과 붙은 값이 같나",
        "한 축을 두 카테고리에 흩어 놓지 않았나 · 같은 사실을 장점과 단점으로 두 번 쓰지 않았나",
        "카테고리와 문장이 맞나 — 상대 가게의 아무 단점이나 그 자리에 끌어다 붙이지 않았나",
        "민감 표현·집단 일반화 — 실호출 전 필수 (§8-5)",
        "소유자 — 이 재료가 내 담당인가. 파일에 안 적혀 있으니 WORKLOG 로 확인한다 (규약 5)",
        "선택지 이름 — 업태는 느껴지되 논거는 말하지 않나. 카테고리 여섯 중 하나가 이름에서 "
        "바로 읽히면 걸린다 (§5 확장, 요한 2026-08-26). `무드하우스`→분위기, `런치익스프레스`→신속함, "
        "`키즈가든`→놀거리. 기계로는 못 잡는다 — 글자가 다르다.",
    ], 1):
        print(f"   {i}. {q}")
    print("\n(이 스크립트는 관문이 아니라 점검표다. 종료코드는 늘 0.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
