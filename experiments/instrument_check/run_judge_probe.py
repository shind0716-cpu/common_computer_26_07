# -*- coding: utf-8 -*-
"""[요한 · 계기 점검] H1·H2 — 판정기 자체를 재는 실험 (실호출, 탐색적 지위).

지위: 계기 점검. 판별표 밖·가설 검정 아님. 단일 이슈(carkey)·파일럿 판정기(gpt-5.4-mini·
temp 0·tp1 프롬프트 원문 재사용)이며 일반화하지 않는다. 개인 키·experiments/ 분리·팀 정본
무접촉(tp1 전례).

**실행 전 기록한 예측** (대화 기록 및 아래 PREDICTIONS 상수):
  H1 — 판정 불일치율이 stage와 함께 단조 증가한다
  H2 — 검출률이 추상도 사다리를 따라 단조 감소하며, 3단(요지 압축)에서 급락한다

H1 (재판정 일관성): tp1 carkey 발화 로그는 그대로 두고 **판정만 n=5로 재실행**한다. 발화
생성이 없으므로 모델 행동 교란이 0이고, 순수하게 "같은 입력에 같은 답을 내는가"만 잰다.
표마다 seed를 달리한다 — 재실행 시 재현되는가가 실무 질문이므로.
  · 이진 불일치: mentioned 판정이 5표 안에서 갈리는 비율
  · 귀속 불일치: agents_mentioning 집합이 5표 안에서 갈리는 비율 (층1·접근 창이 쓰는 값)

H2 (추상도-검출 곡선): 팩트마다 4단 표현 사다리를 **한 번 생성해 고정**하고(temp 0), 각 단을
동일한 캐리어 문장에 넣어 합성 발화로 판정기에 먹인다. 캐리어가 고정이므로 단 간 차이는
추상도뿐이다. 각 단의 원문 근접도(문자 3-gram containment)도 함께 기록해 H3 결과와 접속한다.
  한정: 실제 발화는 다른 내용과 섞인 긴 단락이라 캐리어 단문과 검출 조건이 다를 수 있다.

안전장치: 호출 상한 · 단계별 체크포인트(완료 파일 스킵) · 절단 즉시 에러(D1 교훈).

사용 (리포 루트에서):
  python experiments/instrument_check/run_judge_probe.py --phase ladder   # H2 사다리 생성(36콜)
  python experiments/instrument_check/run_judge_probe.py --phase h2       # H2 판정(144콜)
  python experiments/instrument_check/run_judge_probe.py --phase h1       # H1 재판정(300콜)
  python experiments/instrument_check/run_judge_probe.py --phase report   # 집계(호출 0)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments/transmission_pilot"))

import run_pilot as rp  # noqa: E402  — 판정 프롬프트·호출층 원문 재사용

PREDICTIONS = {
    "H1": "판정 불일치율이 stage와 함께 단조 증가한다",
    "H2": "검출률이 사다리를 따라 단조 감소하며 3단(요지 압축)에서 급락한다",
}
ISSUE = "carkey"
N_VOTES_H1 = 5
N_VOTES_H2 = 3
CARRIER = "제 생각을 말씀드리면, {}. 그래서 신중하게 접근해야 한다고 봅니다."
RUNGS = ["r1_verbatim", "r2_lexical", "r3_gist", "r4_abstract"]

LADDER_SYSTEM = ("당신은 문장을 정해진 추상도 단계로 다시 쓰는 도구입니다. "
                 "반드시 JSON 하나만 출력하세요.")


def ngrams(text: str, n: int = 3) -> set:
    t = re.sub(r"[^0-9A-Za-z가-힣]", "", text or "")
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def containment(fact: str, utterance: str) -> float:
    F, U = ngrams(fact), ngrams(utterance)
    return len(F & U) / len(F) if F else 0.0


def materials() -> dict:
    return rp.materials(ISSUE)


# ---------------------------------------------------------------------------
# H2 단계 1 — 사다리 생성 (한 번만, 고정)
# ---------------------------------------------------------------------------
def phase_ladder() -> None:
    dst = HERE / "ladder.json"
    if dst.exists():
        print(f"[ladder] {dst.name} 존재 — 스킵")
        return
    m = materials()
    rows = []
    for k, f in enumerate(m["facts"]["facts"]):
        user = (
            f'다음 사실을 세 단계로 다시 쓰세요.\n\n사실: "{f["text"]}"\n\n'
            "2단(어휘 치환): 구체 정보(숫자·고유명사·시점)를 모두 유지하되 어휘와 어순만 바꿉니다.\n"
            "3단(요지 압축): 구체 수치·고유명사·시점을 지우고 요지만 한 문장으로 남깁니다.\n"
            "4단(상위 개념): 한 번 더 압축해 짧은 명사구로 만듭니다.\n\n"
            'JSON만 출력: {"r2": "...", "r3": "...", "r4": "..."}'
        )
        raw = rp.chat(rp.GEN_MODEL, LADDER_SYSTEM, user, temperature=0,
                      max_tokens=400, seed=7000 + k)
        s = raw[raw.index("{"): raw.rindex("}") + 1]
        d = json.loads(s)
        rows.append({"fact_id": f["fact_id"], "r1_verbatim": f["text"],
                     "r2_lexical": d["r2"], "r3_gist": d["r3"],
                     "r4_abstract": d["r4"]})
        print(f"[ladder] {f['fact_id']} ok")
    dst.write_text(json.dumps({"issue": ISSUE, "model": rp.GEN_MODEL, "rows": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ladder] 완료 → {dst.name}")


# ---------------------------------------------------------------------------
# H2 단계 2 — 사다리 각 단을 판정기에 먹임
# ---------------------------------------------------------------------------
def phase_h2() -> None:
    dst = HERE / "h2_votes.json"
    if dst.exists():
        print(f"[h2] {dst.name} 존재 — 스킵")
        return
    ladder = json.loads((HERE / "ladder.json").read_text(encoding="utf-8"))
    m = materials()
    ftext = {f["fact_id"]: f["text"] for f in m["facts"]["facts"]}
    out = []
    for k, row in enumerate(ladder["rows"]):
        fid = row["fact_id"]
        for ri, rung in enumerate(RUNGS):
            utter = CARRIER.format(row[rung].rstrip(" ."))
            votes = []
            for v in range(N_VOTES_H2):
                raw = rp.chat(rp.JUDGE_MODEL, rp.JUDGE_SYSTEM,
                              rp.judge_prompt(ftext[fid], [("agent_x", utter)]),
                              temperature=0, max_tokens=rp.MAX_JUDGE_TOKENS,
                              seed=8000 + 100 * k + 10 * ri + v)
                try:
                    s = raw[raw.index("{"): raw.rindex("}") + 1]
                    votes.append(bool(json.loads(s).get("mentioned")))
                except Exception:  # noqa: BLE001
                    votes.append(None)
            out.append({"fact_id": fid, "rung": rung, "text": row[rung],
                        "utterance": utter,
                        "proximity": round(containment(ftext[fid], utter), 4),
                        "votes": votes})
            print(f"[h2] {fid} {rung}: {votes}")
        (HERE / "h2_votes.json.part").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    dst.write_text(json.dumps({"carrier": CARRIER, "n_votes": N_VOTES_H2, "rows": out},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[h2] 완료 → {dst.name}")


# ---------------------------------------------------------------------------
# H1 — tp1 로그 재판정 n=5
# ---------------------------------------------------------------------------
def phase_h1() -> None:
    dst = HERE / "h1_votes.json"
    if dst.exists():
        print(f"[h1] {dst.name} 존재 — 스킵")
        return
    m = materials()
    issue_id = m["issue_id"]
    lines = (rp.out_path("debate", issue_id)).read_text(encoding="utf-8").splitlines()
    utts: dict = {}
    for ln in lines:
        if not ln.strip():
            continue
        ev = json.loads(ln)
        if ev.get("event") == "utterance":
            utts.setdefault(ev["round"], []).append((ev["agent_id"], ev["response_text"]))
    facts = m["facts"]["facts"]
    out = []
    for r in sorted(utts):
        for k, f in enumerate(facts):
            votes = []
            for v in range(N_VOTES_H1):
                raw = rp.chat(rp.JUDGE_MODEL, rp.JUDGE_SYSTEM,
                              rp.judge_prompt(f["text"], utts[r]),
                              temperature=0, max_tokens=rp.MAX_JUDGE_TOKENS,
                              seed=9000 + 1000 * r + 10 * k + v)
                try:
                    s = raw[raw.index("{"): raw.rindex("}") + 1]
                    d = json.loads(s)
                    votes.append({"mentioned": bool(d.get("mentioned")),
                                  "agents": sorted(a for a in d.get("agents_mentioning", [])
                                                   if isinstance(a, str))})
                except Exception:  # noqa: BLE001
                    votes.append(None)
            out.append({"stage": r, "fact_id": f["fact_id"], "votes": votes})
            print(f"[h1] stage {r} {f['fact_id']}: "
                  f"{[v['mentioned'] if v else None for v in votes]}")
        (HERE / "h1_votes.json.part").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    dst.write_text(json.dumps({"n_votes": N_VOTES_H1, "rows": out},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[h1] 완료 → {dst.name}")


# ---------------------------------------------------------------------------
# 집계
# ---------------------------------------------------------------------------
def phase_report() -> None:
    res = {"status": "탐색적 계기 점검 — 판별표 밖·단일 이슈·파일럿 판정기(n=1 정본)",
           "predictions_before_run": PREDICTIONS}

    h1p = HERE / "h1_votes.json"
    if h1p.exists():
        rows = json.loads(h1p.read_text(encoding="utf-8"))["rows"]
        by_stage: dict = {}
        for row in rows:
            vs = [v for v in row["votes"] if v]
            if not vs:
                continue
            binary = {v["mentioned"] for v in vs}
            attrib = {tuple(v["agents"]) for v in vs}
            d = by_stage.setdefault(row["stage"], {"n": 0, "binary_split": 0,
                                                   "attrib_split": 0})
            d["n"] += 1
            d["binary_split"] += int(len(binary) > 1)
            d["attrib_split"] += int(len(attrib) > 1)
        for s, d in by_stage.items():
            d["binary_split_rate"] = round(d["binary_split"] / d["n"], 4)
            d["attrib_split_rate"] = round(d["attrib_split"] / d["n"], 4)
        res["H1_rejudge_consistency"] = {"by_stage": dict(sorted(by_stage.items()))}

    h2p = HERE / "h2_votes.json"
    if h2p.exists():
        rows = json.loads(h2p.read_text(encoding="utf-8"))["rows"]
        by_rung: dict = {}
        for row in rows:
            vs = [v for v in row["votes"] if v is not None]
            if not vs:
                continue
            d = by_rung.setdefault(row["rung"], {"n": 0, "detected_majority": 0,
                                                 "votes_true": 0, "votes_total": 0,
                                                 "split": 0, "prox_sum": 0.0})
            d["n"] += 1
            d["votes_true"] += sum(vs)
            d["votes_total"] += len(vs)
            d["detected_majority"] += int(sum(vs) * 2 > len(vs))
            d["split"] += int(0 < sum(vs) < len(vs))
            d["prox_sum"] += row["proximity"]
        for k, d in by_rung.items():
            d["detection_rate_majority"] = round(d["detected_majority"] / d["n"], 4)
            d["detection_rate_votes"] = round(d["votes_true"] / d["votes_total"], 4)
            d["split_rate"] = round(d["split"] / d["n"], 4)
            d["proximity_mean"] = round(d["prox_sum"] / d["n"], 4)
            del d["prox_sum"]
        res["H2_abstraction_detection"] = {"by_rung": {k: by_rung[k]
                                                       for k in RUNGS if k in by_rung}}

    dst = HERE / "judge_probe_results.json"
    dst.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"\n[saved] {dst}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["ladder", "h2", "h1", "report"])
    ap.add_argument("--max-calls", type=int, default=600)
    args = ap.parse_args()
    rp.MAX_CALLS = args.max_calls
    {"ladder": phase_ladder, "h2": phase_h2, "h1": phase_h1,
     "report": phase_report}[args.phase]()
    print(f"[calls] 이번 실행 LLM 호출 {rp.N_CALLS}회")


if __name__ == "__main__":
    main()
