"""Step 1 집계 — 코더 기록 → recode_20cells.jsonl + 게이트 수치 (콜 0).

PREREG §10 스키마로 20줄을 낸다. 판정기 단계가 아직이므로 `grade`·`votes`·`judge`는
비우고 `human` 블록만 채운다(TASK 산출 규정).

coder_b 파일이 없으면 coder_a만 채우고 κ·E0 은 계산하지 않는다 — 1인 κ 는 없다.

usage: python merge_recode.py
"""
import json
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRADES = ["L0", "L1", "L2", "L3", "L4"]
STAGE_TOKEN = {0: "r0", 1: "r1", 2: "r2", 3: "r3"}


def read_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def cohen_kappa(a, b):
    """비가중 Cohen κ. a, b 는 같은 길이의 라벨 리스트."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(g) / n) * (b.count(g) / n) for g in GRADES)
    return po, pe, (po - pe) / (1 - pe) if pe != 1 else float("nan")


def main():
    key = json.loads((HERE / "shuffle_key.json").read_text(encoding="utf-8"))
    units = {u["blind_id"]: u for u in key["units"]}
    sheet = {r["blind_id"]: r for r in read_jsonl(HERE / "blind_sheet.jsonl")}
    ca = {r["blind_id"]: r for r in read_jsonl(HERE / "codes_coder_a.jsonl")}
    pb = HERE / "codes_coder_b.jsonl"
    cb = {r["blind_id"]: r for r in read_jsonl(pb)} if pb.exists() else {}

    rows = []
    for bid in sorted(units):
        u, a = units[bid], ca.get(bid)
        b = cb.get(bid)
        side = u["graded_side"]
        iss = u["issue_id"].split("_")[-1]
        run_id = f"compare2_{iss}" if side == "ours" else f"authors_scruples_gpt_{iss}"
        rows.append({
            "unit_id": f"{run_id}:{STAGE_TOKEN[u['stage_idx']]}:utterance:{u['fact_id']}",
            "codebook_ver": "v1",
            "run_id": run_id,
            "condition": {"memory": "none", "progress": None, "model": "gpt-4.1"},
            "stage": STAGE_TOKEN[u["stage_idx"]],
            "evidence_kind": "utterance",
            "evidence_id": f"{run_id}:{STAGE_TOKEN[u['stage_idx']]}:S1-S8",
            "evidence_text": "\n\n".join(
                f"[{x['speaker']}] {x['text']}" for x in sheet[bid]["utterances"]),
            "fact_id": u["fact_id"],
            "grade": None,
            "ambiguous": bool(a and a["ambiguous"]) or bool(b and b["ambiguous"]),
            "votes": [],
            "flags": sorted(set((a or {}).get("flags", []) + (b or {}).get("flags", []))),
            "pre": {"anchor_hit": None, "prior_binary": u["our_judgment_status"] == "mentioned",
                    "resolved_without_judge": False, "candidate_facts": [u["fact_id"]],
                    "entailment_marked": False},
            "judge": {"model_snapshot": None, "prompt_ver": None,
                      "temperature": None, "usage": {"in": 0, "out": 0}},
            "human": {"coder_a": (a or {}).get("grade"),
                      "coder_b": (b or {}).get("grade"), "resolved": None},
            "blind_id": bid,
            "shuffle_seed": key["seed"],
            "orig_category": u["orig_category"],
        })

    (HERE / "recode_20cells.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    # ---- 게이트 수치 ----
    print(f"rows={len(rows)}  seed={key['seed']}  coder_b={'있음' if cb else '없음'}\n")
    for who, codes in (("coder_a", ca), ("coder_b", cb)):
        if not codes:
            continue
        gs = [codes[b]["grade"] for b in sorted(codes)]
        amb = sum(codes[b]["ambiguous"] for b in codes)
        print(f"[{who}] 등급 분포: " + " ".join(f"{g}={gs.count(g)}" for g in GRADES)
              + f"  관측 등급 {sum(gs.count(g) > 0 for g in GRADES)}단"
              + f"  ambiguous {amb}/{len(codes)} = {amb / len(codes):.0%}")

    # 대응표 — 원판독 범주 × 등급
    for who, codes in (("coder_a", ca), ("coder_b", cb)):
        if not codes:
            continue
        print(f"\n[{who}] 대응표 (행=원판독 범주, 열=등급)")
        print("            " + "  ".join(f"{g:>3}" for g in GRADES))
        for cat, label in (("boundary", "판정 경계"), ("absent", "발화 부재")):
            ids = [b for b in sorted(codes) if units[b]["orig_category"] == cat]
            cnt = [sum(codes[b]["grade"] == g for b in ids) for g in GRADES]
            print(f"{label} ({len(ids):2d})  " + "  ".join(f"{c:>3}" for c in cnt))
            off = [f"{b}={codes[b]['grade']}({units[b]['issue_id'][-4:]} "
                   f"{units[b]['stage']} {units[b]['fact_id'][-2:]})"
                   for b in ids
                   if (cat == "boundary" and codes[b]["grade"] not in ("L1", "L2", "L3"))
                   or (cat == "absent" and codes[b]["grade"] not in ("L3", "L4"))]
            if off:
                print(f"   예상 밖: {', '.join(off)}")

    if not cb:
        print("\nE0(κ ≥ 0.60): **판정 불가** — coder_b 미도착. 1인 코딩으로 κ를 만들지 않는다.")
        return

    ids = sorted(set(ca) & set(cb))
    A = [ca[b]["grade"] for b in ids]
    B = [cb[b]["grade"] for b in ids]
    po, pe, k = cohen_kappa(A, B)
    print(f"\nκ: 일치 {po:.3f} / 우연 {pe:.3f} / **κ = {k:.3f}** (n={len(ids)})")
    print("E0:", "통과" if k >= 0.60 else "**미달 — 재코딩. Step 2 진행 금지**")
    dis = [(b, ca[b]["grade"], cb[b]["grade"]) for b in ids if ca[b]["grade"] != cb[b]["grade"]]
    if dis:
        print(f"\n불일치 {len(dis)}건 — 경계별")
        pairs = {}
        for b, x, y in dis:
            pairs.setdefault("/".join(sorted((x, y))), []).append(b)
        for pair, bs in sorted(pairs.items(), key=lambda t: -len(t[1])):
            print(f"  {pair}: {len(bs)}건  {', '.join(bs)}")
    amb = sum(1 for b in ids if ca[b]["ambiguous"] or cb[b]["ambiguous"])
    print(f"\nG2(ambiguous ≤ 20%): {amb}/{len(ids)} = {amb / len(ids):.0%} →",
          "통과" if amb / len(ids) <= 0.20 else "미달")
    obs = sorted({g for g in A + B})
    print(f"G3(관측 등급 4단 이상): {len(obs)}단 {obs} →",
          "통과" if len(obs) >= 4 else "미달 — 사다리 축소 제안 후 사람 판단 대기")


main()
