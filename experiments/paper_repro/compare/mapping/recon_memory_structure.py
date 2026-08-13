#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
원자료 정찰 재현 스크립트 — 2026-08-13
DECISION_2026-08-13.md 의 모든 수치를 재현한다. API 콜 0, 원자료 무수정(읽기 전용).

실행:  python experiments/paper_repro/compare/mapping/recon_memory_structure.py
       (cwd = 리포 루트)

주의: ANCHORS 는 정찰 시점의 **임시 사전**이다. 표기 변형이 불완전하고
      약한 앵커 3팩트(09·11·12)를 포함한다. 확정 사전은 anchors_camp.json 이며,
      그것이 만들어지면 이 스크립트의 ANCHORS 를 거기서 로드하도록 교체한다.
"""
import json, io, glob, os, re, sys
from collections import Counter, defaultdict

MS = os.path.join("experiments", "memory_structure")
FACTS = os.path.join("data", "facts", "facts_issue_camp.json")

# --- 임시 앵커 사전 (정찰 시점) -------------------------------------------
ANCHORS = {
    "fact_camp_01": ["38,000", "38000", "3.8만"],
    "fact_camp_02": ["60명", "60인"],
    "fact_camp_03": ["사흘", "3일"],
    "fact_camp_04": ["10월 2일", "10/2"],
    "fact_camp_05": ["51,000", "51000", "5.1만"],
    "fact_camp_06": ["39,500", "39500", "3.95만"],
    "fact_camp_07": ["배관"],
    "fact_camp_08": ["40인", "40명"],
    "fact_camp_09": ["확인서"],
    "fact_camp_10": ["24~25", "24-25", "24∼25"],
    "fact_camp_11": ["명단"],
    "fact_camp_12": ["증서"],
}
# 고유 숫자가 없어 앵커가 성립하지 않는 팩트 — 앵커 스캔에서 제외(D6)
WEAK = {"fact_camp_09", "fact_camp_11", "fact_camp_12"}

# 과제 스텁에 이미 있는 값 — 앵커가 될 수 없다(항상 등장한다)
STUB_VALUES = ["42,000", "35인", "10월 17~18", "33명"]

NORM = re.compile(r"(했어야|해야\s*(한다|했)|하는\s*게\s*맞|바람직|권장|마땅|당연히|해야만|필요가\s*있)")


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def runs():
    for p in sorted(glob.glob(os.path.join(MS, "runs", "*", "run_*.json"))):
        if ".partial" in p:
            continue
        yield p, load(p)


def hits(text):
    return {k for k, alts in ANCHORS.items() if any(a in text for a in alts)}


def section(t):
    print("\n" + "=" * 68)
    print(t)
    print("=" * 68)


# --- 1. 재료 구조 ----------------------------------------------------------
def recon_structure():
    section("1. 재료 구조")
    rows = list(runs())
    print("총 런:", len(rows))
    print("memory:", dict(Counter(d.get("memory") for _, d in rows)))
    print("arm   :", dict(Counter(d.get("arm") for _, d in rows)))
    print("model :", dict(Counter(d["meta"]["model_key"] for _, d in rows)))
    print("essays 개수:", dict(Counter(len(d.get("essays") or []) for _, d in rows)))
    print("notes  개수:", dict(Counter(len(d.get("notes") or []) for _, d in rows)))
    print("recall 보유:", sum(1 for _, d in rows if d.get("recall")), "/", len(rows))

    el = [len(e) for _, d in rows for e in (d.get("essays") or [])]
    nl = [len(n) for _, d in rows for n in (d.get("notes") or [])]
    rl = [len(d["recall"]) for _, d in rows if d.get("recall")]
    for name, v in [("essay", el), ("note", nl), ("recall", rl)]:
        v = sorted(v)
        print(f"{name:7s} 길이 min {v[0]} / 중앙 {v[len(v)//2]} / max {v[-1]}  (n={len(v)})")

    # 판정 기록 범위
    keys = Counter()
    for p in glob.glob(os.path.join(MS, "judgments", "*", "judge_*.json")):
        if ".partial" in p:
            continue
        keys[tuple(sorted(load(p)["records"].keys()))] += 1
    print("\n판정 records 키 조합:")
    for k, v in keys.items():
        print(f"  {v:2d}런 → {list(k)}")
    print("→ recall 채점 기록:", "있음" if any("recall" in k for k in keys) else "**없음**")

    # 팩트 태그
    facts = load(FACTS)["facts"]
    print("\n팩트 태그:", "anchors 필드", "있음" if "anchors" in facts[0] else "**없음**")
    fav = Counter(f.get("favors") for f in facts)
    print("favors:", dict(fav), "→ 입장=무레온 기준 우호 6 · 불리 5 · 중립 1")
    print("prior.score 전부 0.0:", all(f["prior"]["score"] == 0.0 for f in facts))


# --- 2. 규범문 빈도 (구 L3 존재 여부) ---------------------------------------
def recon_normative():
    section("2. 규범문 빈도 — 구 L3 존재 여부")
    buckets = defaultdict(list)
    for _, d in runs():
        buckets["essay"] += d.get("essays") or []
        buckets["note"] += d.get("notes") or []
        if d.get("recall"):
            buckets["recall"].append(d["recall"])
    for k in ["essay", "note", "recall"]:
        v = buckets[k]
        h = [t for t in v if NORM.search(t)]
        print(f"  {k:7s} n={len(v):4d}  규범표현 포함 {len(h):3d} ({100*len(h)/len(v):.0f}%)")
    print("\n→ note 0% : 구 L3(문법 변형 잔존)은 이 재료에 없다 (D1 근거)")


# --- 3. 스텁 값 오염 점검 ---------------------------------------------------
def recon_stub():
    section("3. 스텁 값 — 앵커가 될 수 없는 값")
    blob = "\n".join(t for _, d in runs()
                     for t in (d.get("essays") or []) + (d.get("notes") or []) + ([d["recall"]] if d.get("recall") else []))
    for v in STUB_VALUES:
        print(f"  {v:14s} {blob.count(v):4d}회  ← 과제 스텁에 상시 제시. 앵커 금지")


# --- 4. 해리 재현 (앵커 스캔 단독, 콜 0) ------------------------------------
def recon_dissociation():
    section("4. 해리 재현 — 앵커 스캔만 (LLM 0)")
    agg = defaultdict(list)
    for _, d in runs():
        if d.get("memory") != "note":
            continue
        e, n, r = hits(d["essays"][-1]), hits(d["notes"][-1]), hits(d["recall"])
        agg[(d["meta"]["model_key"], d["arm"])].append((len(e), len(n), len(r)))
    print(f"{'model':13s} {'arm':4s} {'글':>5s} {'수첩':>5s} {'회고':>5s} {'해리':>6s}")
    for k in sorted(agg):
        v = agg[k]
        m = lambda i: sum(x[i] for x in v) / len(v)
        print(f"{k[0]:13s} {k[1]:4s} {m(0):5.1f} {m(1):5.1f} {m(2):5.1f} {m(1)-m(0):+6.1f}")
    print("\n  REPORT_v2 판정기(9,072표) 해리: GPT 0.7/3.0/8.7 · Gemini 2.0/3.3/5.0")
    print("  → 전부 1팩트 이내 (비교 파일럿 '1팩트 규칙' 기준 구분 불가)")


# --- 5. 3창 판정 대상 집계 (D5 범위) ----------------------------------------
def recon_scope():
    section("5. 1차 범위 집계 — ② 수첩 조건 18런 × 3창 (D5)")
    tot = Counter()
    for _, d in runs():
        if d.get("memory") != "note":
            continue
        mk = d["meta"]["model_key"]
        j = load(os.path.join(MS, "judgments", mk,
                              f"judge_{d['arm']}_{d['memory']}_rep{d['rep']}.json"))
        windows = {
            "note":   (d["notes"][-1],  j["records"]["carrier"]),
            "essay":  (d["essays"][-1], j["records"]["essay_r3"]),
            "recall": (d["recall"],     None),          # 기존 판정 없음
        }
        for w, (text, recs) in windows.items():
            anc = hits(text)
            for fid in ANCHORS:
                if fid in WEAK:
                    tot[(w, "약한앵커")] += 1
                    continue
                a = fid in anc
                if recs is None:
                    tot[(w, "자동L0" if a else "판독필요")] += 1
                else:
                    jd = next(x for x in recs if x["fact_id"] == fid)["status"] == "mentioned"
                    if a and jd:      tot[(w, "자동L0")] += 1
                    elif not a and not jd: tot[(w, "자동L4")] += 1
                    else:             tot[(w, "판독필요")] += 1
    cols = ["자동L0", "자동L4", "판독필요", "약한앵커"]
    print(f"{'창':8s}" + "".join(f"{c:>9s}" for c in cols) + f"{'계':>6s}")
    S = Counter()
    for w in ["note", "essay", "recall"]:
        row = [tot[(w, c)] for c in cols]
        for c, x in zip(cols, row): S[c] += x
        print(f"{w:8s}" + "".join(f"{x:>9d}" for x in row) + f"{sum(row):>6d}")
    print(f"{'합계':8s}" + "".join(f"{S[c]:>9d}" for c in cols) + f"{sum(S.values()):>6d}")
    auto = S["자동L0"] + S["자동L4"]
    human = S["판독필요"] + S["약한앵커"]
    print(f"\n  자동 확정 {auto} ({100*auto/(auto+human):.0f}%) · 사람 판독 {human} ({100*human/(auto+human):.0f}%)")
    print(f"  2인 코딩 {human*2}건 · 건당 30초 가정 {human*2/120:.1f}시간/2인 · API 콜 0")
    print("\n  recall 자동L4가 0인 이유: 기존 판정이 없어 앵커X를 확정할 상대가 없다")


if __name__ == "__main__":
    if not os.path.isdir(MS):
        sys.exit("리포 루트에서 실행하세요 (experiments/memory_structure 없음)")
    recon_structure()
    recon_normative()
    recon_stub()
    recon_dissociation()
    recon_scope()
    print("\n[완료] 원자료 무수정 · API 콜 0")
