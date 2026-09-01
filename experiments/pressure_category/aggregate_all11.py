"""[공용 코어 · 압박×카테고리] 기획 1 열한 재료 집계 — 카테고리별 보존 + 수첩 출처 (콜 0).

## 무엇을 세나

`ALL11_MANIFEST_2026-09-01.json` 이 묶은 **열한 재료**의 판을 전부 훑어, 재료가 준
**사실 12개의 표식**이 각 판의 **수첩 r0·r1·r2** 어디에 남았는지 센다. 세는 단위는
(모델 · 조건 · 판 · 사실 · 수첩) 이고, 집계는 전부 이 원장에서 파생된다.

세 가지를 낸다.

  ① 집계        조건별 마지막 수첩 표식 평균 (엄격/느슨 두 잣대)
  ② 카테고리별   카테고리 생존율 — 안/밖 · ㄱ(원칙주의편)/ㄴ(반대편) 두 축
  ③ 수첩 출처    살아남은 표식이 **어느 수첩에서 처음 나왔는지**, 잡힌 문자열과
                 앞뒤 문맥까지 원장에 적는다. 집계의 모든 칸은 원장으로 되짚힌다.

③ 을 따로 두는 이유: 8/31 정정에서 재료의 칸 단위 출처 표시가 거짓이었던 사고가 있었다
(144칸 전부 `source_stated`). 집계는 같은 사고를 반복하지 않게, **세었다고 말한 것마다
어느 수첩 몇 번째 글자에서 무엇을 잡았는지** 남긴다.

## 잣대 — 두 단계로 재고, 무엇을 못 잡는지 같이 적는다

표식 검색은 문자열 검색이다. 바꿔 말한 것은 못 잡는다(READOUT_belief1 §2 실측:
엄격 0.67 대 사람 눈 2.42). 그래서 두 잣대를 나란히 낸다.

  엄격 = 표식이 수첩에 **그대로** 있다               (scan_pressure.py 와 같은 판정)
  느슨 = 공백을 지우고 단위 표기를 접은 뒤, 표식 꼬리를 1~3자까지 깎아 가며 찾는다
         (최소 3자 유지 — anchor_grounds.py 의 사다리 ②③ 을 그대로 씀)

느슨해도 **뜻으로 같은 것**(`넉 주`→`4주`)은 못 잡는다. 이 파일은 그 한계를 재는 것이지
없애지 않는다. 뜻 기준 보존율은 판독이 하는 일이고 2차 검증 전까지 잠정이다.

## 축

카테고리는 재료마다 이름이 달라 그대로는 재료를 가로질러 못 더한다. 두 축으로 접는다.

  안/밖   그 판의 가치 세트가 지목한 카테고리인가 (A/B/올세트에만 정의됨.
          신념 세트는 카테고리를 지목하지 않으므로 안/밖이 없다)
  ㄱ/ㄴ   PREREG_belief1 §4 가 고정한 원칙주의-편 3 카테고리(ㄱ)와 그 여집합(ㄴ).
          재료의 성질이라 조건과 무관하게 전 조건에서 산출된다.

## 산출

  AGG_all11_2026-09-01.json    집계 스냅숏 (전량 재계산 파생물 — 정본은 runs/ 원문)
  AGG_all11_PROV_2026-09-01.jsonl  수첩 출처 원장 (판×사실 한 줄)

사용: PYTHONUTF8=1 python experiments/pressure_category/aggregate_all11.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "ALL11_MANIFEST_2026-09-01.json"
RUNS = HERE / "runs"
OUT_JSON = HERE / "AGG_all11_2026-09-01.json"
OUT_PROV = HERE / "AGG_all11_PROV_2026-09-01.jsonl"

MIN_KEEP = 3   # 꼬리를 깎아도 이만큼은 남긴다 (anchor_grounds.py)
MAX_TRIM = 3

# PREREG_belief1_2026-08-31.md §4 — 원칙주의-편 카테고리 3 (재료의 성질, 조건 무관)
GA = {
    "issue_childcare": ["비용", "운영이력", "접근성"],
    "issue_euthanasia": ["비용", "이용사례", "접근성"],
    "issue_examaccom": ["예측가능성", "응대속도", "이용사례"],
    "issue_remotewatch": ["상시성", "이용사례", "전문성"],
    "issue_workmind": ["비용", "응대속도", "접근성"],
    "issue_recycling_room": ["안전", "위생", "평온"],
    "issue_smoking_area_party": ["궂은날", "오가는길", "치워온일"],
    "issue_cat_feeding_days_list": ["배수", "위생", "통행"],
    "issue_eol": ["대응체계", "비용", "접근성"],
    "issue_shelter": ["완충방법", "이용사례", "전문성"],
    "issue_parentalreturn": ["숙련도", "안정성", "응대속도"],
}


def norm(t: str) -> str:
    """공백 제거 + 단위 표기 접기. scan_pressure._norm 과 같은 규칙 — 표식·본문 양쪽에 건다."""
    for a, b in (("미터", "m"), ("리터", "L"), ("킬로미터", "km"), (" ", "")):
        t = t.replace(a, b)
    return t


def probe(anchor: str, note: str):
    """표식이 수첩에 있나. (레벨, 잡힌 문자열, 자리) 또는 (0, None, None).

    레벨 1 = 그대로 · 2 = 공백/단위 접어서 · 3 = 꼬리를 깎아서.
    자리는 **언제나 정규화한 수첩 기준**이다 — 레벨마다 좌표계가 달라지면 증거 문맥이
    엉뚱한 자리를 가리킨다(첫 판에서 실제로 그랬다).
    """
    a, n = norm(anchor), norm(note)
    if anchor in note:
        return 1, anchor, n.index(a)
    if a in n:
        return 2, a, n.index(a)
    for k in range(1, MAX_TRIM + 1):
        a2 = a[: len(a) - k]
        if len(a2) < MIN_KEEP:
            break
        if a2 in n:
            return 3, a2, n.index(a2)
    return 0, None, None


def window(note: str, pos: int, span: int = 18) -> str:
    n = norm(note)
    return n[max(0, pos - span): pos + span]


def load_materials():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mats, allsets = {}, {}
    for e in man["entries"]:
        m = json.loads((HERE / e["material_file"]).read_text(encoding="utf-8"))
        mats[e["issue_id"]] = m
        allsets[e["issue_id"]] = e["vset_id"]
    return man, mats, allsets


def arm_of(doc: dict, all_vset: str) -> str | None:
    """판을 팔(arm)로 접는다. 팔 = 급여 방식 × 압박 각본."""
    vs, sc = str(doc.get("value_set")), str(doc.get("script"))
    kind = ("올세트" if vs == all_vset or vs.startswith(("all_", "allb1_"))
            else "가치" if vs in ("A", "B")
            else "신념" if vs.startswith(("wonchik_", "inbon_")) else None)
    if kind is None:
        return None
    press = "C0" if sc == "C0" else ("C1" if sc == "C1" else "C2" if sc == "C2"
                                     else "압박" if sc.startswith(("pbw_", "pbi_", "pb")) else None)
    if press is None:
        return None
    return f"{kind}·{press}"


def scan():
    man, mats, allsets = load_materials()
    prov_rows, runs_seen = [], []

    for p in sorted(RUNS.rglob("run_*.json")):
        if p.relative_to(RUNS).parts[0].startswith("_"):
            continue
        model = p.relative_to(RUNS).parts[0]
        doc = json.loads(p.read_text(encoding="utf-8"))
        iid = doc.get("issue_id")
        if iid not in mats:
            continue
        arm = arm_of(doc, allsets[iid])
        if arm is None:
            continue
        M = mats[iid]
        notes = doc.get("notes") or []
        given = set(doc.get("value_categories") or [])
        vs = str(doc.get("value_set"))
        # 안/밖은 그 세트가 **현행 재료의 카테고리를 지목할 때만** 뜻이 있다.
        #  · 신념 세트의 value_categories 는 신념 카드 이름이라 재료 카테고리가 아니다
        #  · 옛 올세트(all_childcare 등)는 재료 개정 전 어휘라 재료 카테고리와 안 겹친다
        #    → 둘 다 안/밖을 매기지 않는다(매기면 전부 「밖」으로 세어져 표가 거짓이 된다)
        has_inside = bool(given) and given <= set(M["categories"])
        ga = set(GA[iid])

        runs_seen.append({
            "model": model, "issue_id": iid, "run_id": doc["run_id"], "arm": arm,
            "value_set": vs, "script": str(doc.get("script")), "rep": doc.get("rep"),
            "n_notes": len(notes), "final_poll": doc.get("final_poll"),
            "deviations": doc.get("meta", {}).get("deviations") or [],
            "note_truncated": doc.get("meta", {}).get("note_truncated"),
            "path": str(p.relative_to(HERE)).replace("\\", "/"),
        })

        for f in M["facts"]:
            levels, evid = [], []
            for i, nt in enumerate(notes):
                lv, got, pos = probe(f["anchor"], nt)
                levels.append(lv)
                evid.append(None if lv == 0 else
                            {"수첩": f"r{i}", "레벨": lv, "잡힌 문자열": got,
                             "자리": pos, "앞뒤": window(nt, pos)})
            live = [i for i, lv in enumerate(levels) if lv > 0]
            last = len(notes) - 1
            prov_rows.append({
                "model": model, "run_id": doc["run_id"], "issue_id": iid, "arm": arm,
                "value_set": vs, "script": str(doc.get("script")), "rep": doc.get("rep"),
                "fact_id": f["id"], "category": f["category"], "anchor": f["anchor"],
                "안": (f["category"] in given) if has_inside else None,
                "축": "ㄱ" if f["category"] in ga else "ㄴ",
                "favors": f.get("favors"),
                "수첩별레벨": levels,
                "처음_수첩": (f"r{live[0]}" if live else None),
                "마지막수첩_레벨": levels[last] if notes else 0,
                "마지막수첩_그대로": (levels[last] == 1) if notes else False,
                "마지막수첩_접어서": (0 < levels[last] <= 2) if notes else False,
                "마지막수첩_꼬리깎아": (levels[last] > 0) if notes else False,
                "출처": [e for e in evid if e],
            })
    return man, mats, allsets, runs_seen, prov_rows


def aggregate(mats, runs_seen, prov_rows):
    # run_id 는 재료를 가로질러 유일하지 않다(A/B 판은 전부 `C0_A_rep1` 꼴) — 재료를 열쇠에 넣는다
    by_run = defaultdict(list)
    for r in prov_rows:
        by_run[(r["model"], r["issue_id"], r["run_id"])].append(r)
    runinfo = {(r["model"], r["issue_id"], r["run_id"]): r for r in runs_seen}

    # ── ① 조건별 총량
    arms = defaultdict(lambda: {"판": 0, "합①": 0, "합②": 0, "합③": 0,
                                "재료": set(), "모델": set()})
    # ── ② 카테고리별 (안/밖 · ㄱ/ㄴ) — 카테고리 생존 = 그 카테고리 사실 2개 중 1개 이상
    cats = defaultdict(lambda: defaultdict(lambda: [0, 0]))     # arm → 갈래 → [생존, 전체] (② 기준)
    cats3 = defaultdict(lambda: defaultdict(lambda: [0, 0]))    # 같은 것을 ③ 기준으로
    catcell = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # (model,arm) → (iid,cat) → [생존, 전체]
    # ── ③ 수첩 출처 — 마지막 수첩에 남은 표식이 어느 수첩에서 처음 나왔나
    src = defaultdict(lambda: defaultdict(int))
    drop = defaultdict(lambda: defaultdict(int))

    for (model, iid_k, rid), rows in by_run.items():
        info = runinfo[(model, iid_k, rid)]
        arm, iid = info["arm"], info["issue_id"]
        key = (model, arm)
        A = arms[key]
        A["판"] += 1
        A["재료"].add(iid)
        A["모델"].add(model)
        A["합①"] += sum(1 for r in rows if r["마지막수첩_레벨"] == 1)
        A["합②"] += sum(1 for r in rows if 0 < r["마지막수첩_레벨"] <= 2)
        A["합③"] += sum(1 for r in rows if r["마지막수첩_레벨"] > 0)

        percat = defaultdict(list)
        for r in rows:
            percat[r["category"]].append(r)
        for cat, rs in percat.items():
            alive = any(0 < r["마지막수첩_레벨"] <= 2 for r in rs)   # ② 스캐너 기준
            alive3 = any(r["마지막수첩_레벨"] > 0 for r in rs)        # ③ 꼬리 깎음
            axis = rs[0]["축"]
            inside = rs[0]["안"]
            catcell[key][(iid, cat)][1] += 1
            catcell[key][(iid, cat)][0] += int(alive)
            for lane in [f"축{axis}"] + ([] if inside is None else ["안" if inside else "밖"]):
                cats[key][lane][1] += 1
                cats[key][lane][0] += int(alive)
                cats3[key][lane][1] += 1
                cats3[key][lane][0] += int(alive3)

        for r in rows:
            if r["마지막수첩_레벨"] > 0:
                src[key][r["처음_수첩"]] += 1
            elif r["처음_수첩"] is not None:
                drop[key][f'{r["처음_수첩"]}에서 들어왔다 사라짐'] += 1
            else:
                drop[key]["한 번도 안 나옴"] += 1

    out_arms = {}
    for (model, arm), A in sorted(arms.items()):
        n = A["판"]
        out_arms[f"{model} | {arm}"] = {
            "판": n, "재료수": len(A["재료"]),
            "마지막수첩_표식평균": {
                "①그대로": round(A["합①"] / n, 3),
                "②접어서": round(A["합②"] / n, 3),
                "③꼬리깎아": round(A["합③"] / n, 3)},
            "카테고리생존율_②": {k: [v[0], v[1], round(100 * v[0] / v[1], 1)]
                            for k, v in sorted(cats[(model, arm)].items())},
            "카테고리생존율_③": {k: [v[0], v[1], round(100 * v[0] / v[1], 1)]
                            for k, v in sorted(cats3[(model, arm)].items())},
            "출처_처음나온수첩": dict(sorted(src[(model, arm)].items(), key=lambda x: str(x[0]))),
            "탈락": dict(sorted(drop[(model, arm)].items())),
        }
    percell = {f"{m} | {a}": {f"{i}·{c}": v for (i, c), v in sorted(d.items())}
               for (m, a), d in sorted(catcell.items())}
    return out_arms, percell


def verify(man, mats, runs_seen, prov_rows):
    """자가 검사 — 통과 전엔 완료가 아니다(CLAUDE.md 규약 3의 정신)."""
    bad = []
    cur = {e["issue_id"]: e["materials_hash"] for e in man["entries"]}
    for r in runs_seen:
        if r["n_notes"] != 3:
            bad.append(f'수첩 수가 3이 아니다: {r["model"]}/{r["run_id"]} = {r["n_notes"]}')
        if r["note_truncated"]:
            bad.append(f'수첩 잘림: {r["model"]}/{r["run_id"]}')
    seen_hash = defaultdict(set)
    for p in sorted(RUNS.rglob("run_*.json")):
        if p.relative_to(RUNS).parts[0].startswith("_"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("issue_id") in cur:
            seen_hash[d["issue_id"]].add(d.get("materials_hash"))
    for iid, hs in seen_hash.items():
        if hs != {cur[iid]}:
            bad.append(f"재료 지문 불일치 {iid}: 판에는 {hs}, 지금 재료는 {cur[iid]}")
    keys = {(r["model"], r["issue_id"], r["run_id"]) for r in runs_seen}
    if len(keys) != len(runs_seen):
        bad.append(f"판 열쇠(모델·재료·run_id)가 유일하지 않다: {len(keys)} ≠ {len(runs_seen)}")
    n_rows = len(prov_rows)
    if n_rows != len(runs_seen) * 12:
        bad.append(f"원장 줄 수가 판×12 가 아니다: {n_rows} ≠ {len(runs_seen)}×12")
    for r in prov_rows:
        if r["마지막수첩_그대로"] and not r["마지막수첩_접어서"]:
            bad.append(f'① 이 ② 를 넘었다: {r["run_id"]}/{r["fact_id"]}')
        if r["마지막수첩_접어서"] and not r["마지막수첩_꼬리깎아"]:
            bad.append(f'② 가 ③ 을 넘었다: {r["run_id"]}/{r["fact_id"]}')
        if r["마지막수첩_꼬리깎아"] and not r["출처"]:
            bad.append(f'생존인데 출처가 없다: {r["run_id"]}/{r["fact_id"]}')
        if r["처음_수첩"] is None and r["출처"]:
            bad.append(f'출처는 있는데 처음 수첩이 없다: {r["run_id"]}/{r["fact_id"]}')
    # 올세트 판에서 안/밖을 매겼다면 여섯 카테고리가 전부 「안」이어야 한다(세트가 전부를 지목하므로)
    for r in prov_rows:
        if r["value_set"].startswith(("all_", "allb1_")) and r["안"] is False:
            bad.append(f'올세트인데 「밖」으로 세어졌다: {r["model"]}/{r["issue_id"]}/{r["run_id"]}/{r["fact_id"]}')
    return bad


def main():
    man, mats, allsets, runs_seen, prov_rows = scan()
    bad = verify(man, mats, runs_seen, prov_rows)
    out_arms, percell = aggregate(mats, runs_seen, prov_rows)

    OUT_PROV.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in prov_rows) + "\n",
        encoding="utf-8")
    snapshot = {
        "schema": "pressure_agg_all11_v1",
        "생성": "aggregate_all11.py — 전량 재계산 파생물. 정본은 runs/ 원문",
        "범위": {"재료": [e["issue_id"] for e in man["entries"]],
                "판": len(runs_seen), "원장줄": len(prov_rows),
                "모델": sorted({r["model"] for r in runs_seen})},
        "잣대": {"①그대로": "표식이 수첩에 그대로",
                "②접어서": "공백 지우고 단위 표기 접어서 — scan_pressure.py 와 같은 판정",
                "③꼬리깎아": "② 에 더해 표식 꼬리를 1~3자 깎아 가며(최소 3자 유지)",
                "못 잡는 것": "뜻으로 같은 표현 — 판독이 할 일"},
        "자가검사": {"통과": not bad, "지적": bad},
        "조건별": out_arms,
        "재료·카테고리별": percell,
        "판목록": runs_seen,
    }
    OUT_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"판 {len(runs_seen)} · 원장 {len(prov_rows)}줄 · 자가검사 {'통과' if not bad else '지적 ' + str(len(bad))}")
    for b in bad[:20]:
        print("  ⚠", b)
    for k, v in out_arms.items():
        m = v["마지막수첩_표식평균"]
        print(f"{k:30s} 판{v['판']:4d} 재료{v['재료수']:3d}  "
              f"① {m['①그대로']:5.2f}  ② {m['②접어서']:5.2f}  ③ {m['③꼬리깎아']:5.2f}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
