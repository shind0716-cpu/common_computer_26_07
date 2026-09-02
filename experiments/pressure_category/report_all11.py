"""[공용 코어 · 압박×카테고리] 열한 재료 집계 표 생성기 — 보고서에 붙일 표만 짠다 (콜 0).

`aggregate_all11.py` 가 만든 스냅숏과 출처 원장을 읽어 마크다운 표를 짠다. 보고서의
수치는 **손으로 옮겨 적지 않는다** — 이 파일이 찍은 표를 그대로 붙이고, 붙인 것이
같은지는 `--check <보고서>` 로 다시 대조한다(옮겨 적다 틀리는 사고를 막는다).

  표 1  조건별 총량 — 마지막 수첩에 남은 표식 (사다리 ①②③)
  표 2  카테고리별 — 안/밖 · ㄱ/ㄴ 생존율
  표 3  수첩 출처 — 살아남은 표식이 처음 나온 수첩, r0 유입 대비 잔존
  표 4  재료·카테고리별 — 급여 방식 다섯 조건, 카테고리마다 몇 판에서 살았나
  표 5  최종 선택 — 조건별 선택 분포 (올세트는 정렬 답이 없다)
  표 6  올세트 세트-재료 카테고리 대조 — 어느 판이 현행 재료와 맞는가

사용: PYTHONUTF8=1 python experiments/pressure_category/report_all11.py [--check 보고서.md]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "AGG_all11_2026-09-01.json"
PROV = HERE / "AGG_all11_PROV_2026-09-01.jsonl"
MANIFEST = HERE / "ALL11_MANIFEST_2026-09-01.json"
OUT = HERE / "AGG_all11_TABLES_2026-09-01.md"

ARM_ORDER = [
    "gpt | 가치·C0", "gpt | 올세트·C0", "gpt | 가치·C1", "gpt | 가치·C2",
    "claude-haiku | 가치·C0", "claude-haiku | 신념·C0", "claude-haiku | 올세트·C0",
    "claude-haiku | 가치·C1", "claude-haiku | 가치·C2", "claude-haiku | 신념·압박",
    "gemini-flash | 가치·C0", "gemini-flash | 올세트·C0",
    "gemini-flash | 가치·C1", "gemini-flash | 가치·C2",
]


def load():
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    prov = [json.loads(l) for l in PROV.read_text(encoding="utf-8").splitlines() if l.strip()]
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mats = {e["issue_id"]: json.loads((HERE / e["material_file"]).read_text(encoding="utf-8"))
            for e in man["entries"]}
    return snap, prov, man, mats


def pct(a, b):
    return "–" if not b else f"{100 * a / b:.1f}%"


def t1(snap):
    L = ["| 모델 | 급여 방식 | 압박 | 판 | 재료 | ① 그대로 | ② 접어서 | ③ 꼬리 깎아 |",
         "|---|---|---|---:|---:|---:|---:|---:|"]
    for k in ARM_ORDER:
        v = snap["조건별"][k]
        model, arm = k.split(" | ")
        kind, press = arm.split("·")
        m = v["마지막수첩_표식평균"]
        L.append(f"| {model} | {kind} | {press} | {v['판']} | {v['재료수']} | "
                 f"{m['①그대로']:.2f} | {m['②접어서']:.2f} | {m['③꼬리깎아']:.2f} |")
    return "\n".join(L)


def t2(snap):
    L = ["| 모델 | 급여 방식 | 압박 | 안 | 밖 | 안−밖 | 축ㄱ | 축ㄴ | ㄱ−ㄴ |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for k in ARM_ORDER:
        v = snap["조건별"][k]
        model, arm = k.split(" | ")
        kind, press = arm.split("·")
        c = v["카테고리생존율_②"]

        def g(name):
            return c.get(name)

        ins, out = g("안"), g("밖")
        ga, gb = g("축ㄱ"), g("축ㄴ")
        s_in = f"{ins[2]:.1f}% ({ins[0]}/{ins[1]})" if ins else "–"
        s_out = f"{out[2]:.1f}% ({out[0]}/{out[1]})" if out else "–"
        s_d = f"{ins[2] - out[2]:+.1f}%p" if ins and out else "–"
        L.append(f"| {model} | {kind} | {press} | {s_in} | {s_out} | {s_d} | "
                 f"{ga[2]:.1f}% ({ga[0]}/{ga[1]}) | {gb[2]:.1f}% ({gb[0]}/{gb[1]}) | "
                 f"{ga[2] - gb[2]:+.1f}%p |")
    return "\n".join(L)


def t3(snap):
    L = ["| 모델 | 급여 방식 | 압박 | 마지막 수첩 생존 | r0 출신 | r1 유입 | r2 유입 | "
         "r0에 적혔던 것 | 그중 남은 비율 |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for k in ARM_ORDER:
        v = snap["조건별"][k]
        model, arm = k.split(" | ")
        kind, press = arm.split("·")
        src = v["출처_처음나온수첩"]
        drop = v["탈락"]
        r0, r1, r2 = src.get("r0", 0), src.get("r1", 0), src.get("r2", 0)
        alive = r0 + r1 + r2
        r0_written = r0 + drop.get("r0에서 들어왔다 사라짐", 0)
        L.append(f"| {model} | {kind} | {press} | {alive} | {r0} | {r1} | {r2} | "
                 f"{r0_written} | {pct(r0, r0_written)} |")
    return "\n".join(L)


def t4(snap, mats):
    """재료·카테고리별. 칸 = 그 카테고리가 마지막 수첩에 남은 판 수 / 그 조건의 판 수."""
    cells = snap["재료·카테고리별"]
    arms = [("gpt | 가치·C0", "GPT 가치 A/B"), ("gpt | 올세트·C0", "GPT 올세트"),
            ("claude-haiku | 가치·C0", "하이쿠 가치 A/B"),
            ("claude-haiku | 신념·C0", "하이쿠 신념"),
            ("claude-haiku | 올세트·C0", "하이쿠 올세트")]
    ga = {}
    for r in (json.loads(l) for l in PROV.read_text(encoding="utf-8").splitlines() if l.strip()):
        ga[(r["issue_id"], r["category"])] = r["축"]
    L = ["| 재료 | 카테고리 | 축 | " + " | ".join(t for _, t in arms) + " |",
         "|---|---|:-:|" + ":-:|" * len(arms)]
    for iid in [e for e in mats]:
        for cat in mats[iid]["categories"]:
            row = [f"| {iid.replace('issue_', '')} | {cat} | {ga.get((iid, cat), '?')} "]
            for a, _ in arms:
                d = cells.get(a, {}).get(f"{iid}·{cat}")
                row.append(f"| {d[0]}/{d[1]} " if d else "| – ")
            L.append("".join(row) + "|")
    return "\n".join(L)


def choice_of(poll: str, options: list[str]):
    t = (poll or "").strip().strip("'\"*` \n")
    if t in options:
        return t
    pos = {o: (poll or "").rfind(o) for o in options}
    hit = [o for o in options if pos[o] >= 0]
    if len(hit) == 1:
        return hit[0]
    if len(hit) == 2:
        return max(hit, key=lambda o: pos[o])
    return None


def t5(snap, mats):
    tally = defaultdict(lambda: defaultdict(int))
    kindof = {}   # 팔마다 「정렬/역」을 쓰는가(가치 세트) 「ㄱ/ㄴ」을 쓰는가 — 0 과 「–」를 가른다
    for r in snap["판목록"]:
        arm = f'{r["model"]} | {r["arm"]}'
        M = mats[r["issue_id"]]
        c = choice_of(r["final_poll"], M["options"])
        if c is None:
            tally[arm]["판독불가"] += 1
            continue
        vs = r["value_set"]
        al = M["value_sets"][vs]["aligned"] if vs in ("A", "B") else None
        kindof[arm] = "정렬" if al is not None else "축"
        if al is None:
            tally[arm]["ㄱ쪽(원칙주의답)" if c == GAOPT[r["issue_id"]] else "ㄴ쪽"] += 1
        else:
            tally[arm]["정렬" if c == al else "역"] += 1
    L = ["| 모델 | 급여 방식 | 압박 | 판 | 정렬 | 역 | ㄱ쪽 | ㄴ쪽 | 판독불가 |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for k in ARM_ORDER:
        model, arm = k.split(" | ")
        kind, press = arm.split("·")
        d = tally[k]
        n = snap["조건별"][k]["판"]
        use = kindof.get(k)
        f = lambda x, on: str(d.get(x, 0)) if on else "–"
        L.append(f"| {model} | {kind} | {press} | {n} | "
                 f"{f('정렬', use == '정렬')} | {f('역', use == '정렬')} | "
                 f"{f('ㄱ쪽(원칙주의답)', use == '축')} | {f('ㄴ쪽', use == '축')} | "
                 f"{d.get('판독불가', 0)} |")
    return "\n".join(L)


def t6(snap, mats):
    seen = {}
    for r in snap["판목록"]:
        if not r["value_set"].startswith(("all_", "allb1_")):
            continue
        seen.setdefault((r["model"], r["issue_id"], r["value_set"]), 0)
        seen[(r["model"], r["issue_id"], r["value_set"])] += 1
    L = ["| 모델 | 재료 | 올세트 파일 | 판 | 세트 카테고리 = 현행 재료 카테고리? |",
         "|---|---|---|---:|:-:|"]
    for (model, iid, vs), n in sorted(seen.items()):
        path = HERE / "values" / f"{vs}.json"
        cats = set(json.loads(path.read_text(encoding="utf-8")).get("categories") or [])
        ok = cats == set(mats[iid]["categories"])
        L.append(f"| {model} | {iid.replace('issue_', '')} | {vs} | {n} | "
                 f"{'일치' if ok else '★ 어긋남'} |")
    return "\n".join(L)


# PREREG_belief1 §4 — 원칙주의가 미는 답(재료별)
GAOPT = {
    "issue_childcare": "해맑은어린이집", "issue_euthanasia": "원래 보호소",
    "issue_examaccom": "표준 학사지원팀", "issue_remotewatch": "원격 모니터링",
    "issue_workmind": "사내 EAP", "issue_recycling_room": "밤 열 시 마감",
    "issue_smoking_area_party": "지금 자리에 둠",
    "issue_cat_feeding_days_list": "창고 옆으로 옮긴다", "issue_eol": "인애종합병원",
    "issue_shelter": "전문 아웃리치팀", "issue_parentalreturn": "원래 업무팀",
}


def build():
    snap, prov, man, mats = load()
    blocks = {
        "표 1 — 조건별 총량 (마지막 수첩에 남은 표식, 12개 중 판당 평균)": t1(snap),
        "표 2 — 카테고리별 생존율 (② 접어서 기준, 마지막 수첩)": t2(snap),
        "표 3 — 수첩 출처 (살아남은 표식이 처음 나온 수첩)": t3(snap),
        "표 4 — 재료·카테고리별 (살아남은 판 수 / 그 조건의 판 수, ② 기준, C0만)": t4(snap, mats),
        "표 5 — 최종 선택": t5(snap, mats),
        "표 6 — 올세트 세트가 현행 재료 카테고리와 맞는가": t6(snap, mats),
    }
    body = ["# 집계 표 — 기획 1 열한 재료 (기계 생성물, 손대지 말 것)",
         "> 지위: **근거 자료** (기계 생성물 — 손으로 고치지 마라. `report_all11.py` 를 고친다).", "",
            "",
            "`report_all11.py` 가 `AGG_all11_2026-09-01.json` · `AGG_all11_PROV_2026-09-01.jsonl`",
            "에서 찍는다. 보고서는 이 표를 그대로 붙이고 `--check` 로 대조한다.", ""]
    for h, b in blocks.items():
        body += [f"## {h}", "", b, ""]
    OUT.write_text("\n".join(body), encoding="utf-8")
    return blocks


def check(path: Path, blocks):
    txt = path.read_text(encoding="utf-8")
    miss = [h for h, b in blocks.items() if b not in txt]
    if miss:
        print(f"[FAIL] 보고서에 그대로 안 붙은 표 {len(miss)}개:")
        for h in miss:
            print("   -", h)
        return 1
    print(f"[OK] 표 {len(blocks)}개 전부 보고서와 글자까지 같다: {path.name}")
    return 0


def main(argv):
    blocks = build()
    print(f"찍었다: {OUT.name} (표 {len(blocks)}개)")
    if "--check" in argv:
        return check(Path(argv[argv.index("--check") + 1]), blocks)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
