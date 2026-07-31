# -*- coding: utf-8 -*-
"""[신동범 · 판정기 재검증] 요한 님 7/29 반례쌍을 2×2(프롬프트 × 모델)로 재채점한다.

판별 기준은 이 파일보다 **먼저** 커밋됐다: experiments/judge_crossmodel/PREREG.md (5bb7644).
결과 해석은 그 문서 §3 표를 따르며, 이 러너는 표를 채울 숫자만 만든다.

■ 무엇을 재는가
7/29 판정기 비일관성은 **팀 확정 judge 가 아닌** 파일럿 채점기에서 관측됐다
(gpt-5.4-mini · temp0 · n=1 · tp-judge-v0.1). 파일럿과 팀 확정 사양은 네 축이 동시에 다르고,
그중 판정 규칙 조항 차이가 특히 크다 — 팀 프롬프트에만 "부분적으로만 뒷받침되면 인정하지
않는다"가 있다. 이 러너는 프롬프트와 모델을 각각 두 값으로 교차해 어느 축의 산물인지 가른다.

■ 잣대 단일 소스 (설계상 가장 중요한 점)
네 조건 **전부** `judge.judge_fact()` 를 경유한다. 다수결·동점 처리·votes 원본 보존이 전부
정본 코드에서 나오게 하고, 이 러너가 바꾸는 것은 `vote_fn`(프롬프트 + 모델) 하나뿐이다.
정본과 다른 경로로 재채점하면 무엇을 검증한 것인지 알 수 없다.
**modules/judge.py · modules/llm.py 는 이 실험에서 한 줄도 수정하지 않는다.**

■ run_pilot 을 import 하지 않는 이유
`experiments/transmission_pilot/run_pilot.py` 는 모듈 로드 시점에 `.env` 를 읽고, 파일이
없으면 FileNotFoundError 로 죽는다(run_pilot.py:64). 이 리포에는 `.env` 가 없으므로
import 자체가 불가하다. 게다가 비교 대상 프롬프트는 **연구 대상**이라 실험 기록에 고정돼
있어야 한다(나중에 run_pilot 이 바뀌어도 "무엇을 비교했나"가 남아야 한다). 그래서 파일럿
프롬프트를 아래에 **인용으로 고정**하고, 산출물에 두 프롬프트의 sha256 을 함께 적는다.
run_pilot 을 읽을 수 있는 환경에서는 `--verify-prompts` 로 원문 일치를 확인할 수 있다.

■ 안전장치
호출 상한(--max-calls) · 조건별 체크포인트(.part, 완료 조건 스킵) · 절단 즉시 에러(D1 교훈)
· `--offline` 스텁(호출 0, 구조 검증 전용).

사용:
  python experiments/judge_crossmodel/run_rejudge.py --phase cells --offline   # 셀 적출 확인
  python experiments/judge_crossmodel/run_rejudge.py --phase run --offline     # 구조 검증(호출 0)
  python experiments/judge_crossmodel/run_rejudge.py --phase verify-prompts    # 프롬프트 원문 대조
  python experiments/judge_crossmodel/run_rejudge.py --phase run --condition team_sonnet
  python experiments/judge_crossmodel/run_rejudge.py --phase report            # 집계(호출 0)

실호출은 리더 창구 승인 후 집행한다(규약 7 예외: 실호출 창구는 리더 소관).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from modules import judge, llm  # noqa: E402  — 정본 재사용(사본 만들지 않는다)

TP = ROOT / "experiments/transmission_pilot"
PILOT_DATA = TP / "data"
PILOT_FIX = TP / "fixtures"

N_VOTES = 3          # 팀 확정 사양
TEMPERATURE = 0.0    # 팀 확정 사양
MAX_JUDGE_TOKENS = 512

# ─── 비교 대상 프롬프트 고정 인용 ────────────────────────────────────────────
# 출처: experiments/transmission_pilot/run_pilot.py (JUDGE_SYSTEM · judge_prompt),
# prompt_ver "tp-judge-v0.1". 아래는 그 원문을 글자 그대로 옮긴 것이며,
# --verify-prompts 로 대조할 수 있다. 팀 프롬프트는 judge.JUDGE_SYSTEM 을 직접 참조한다.
PILOT_JUDGE_SYSTEM = ("당신은 토론 기록 분석가입니다. 주어진 발언들에서 특정 사실이 언급되는지 "
                      "판정합니다. 의역(paraphrase)도 언급으로 칩니다. 반드시 JSON 하나만 "
                      "출력하세요.")


def pilot_judge_prompt(fact_text: str, utterances: list[tuple[str, str]]) -> str:
    utt = "".join(f"[{aid}] {text}\n\n" for aid, text in utterances)
    return (f"발언 기록:\n{utt}\n판정 대상 사실: \"{fact_text}\"\n\n"
            "위 사실(의역 포함)을 언급한 발언자가 있습니까?\n"
            '다음 JSON 형식으로만 답하세요: {"mentioned": true/false, '
            '"agents_mentioning": ["agent_..."]}')


PILOT_PROMPT_VER = "tp-judge-v0.1"
TEAM_PROMPT_VER = judge.JUDGE_PROMPT_VER

# ─── 조건 (PREREG §2-1) ──────────────────────────────────────────────────────
CONDITIONS = {
    "pilot_gpt":    {"prompt": "pilot", "model": "gpt-mini"},          # 재현 대조군
    "pilot_sonnet": {"prompt": "pilot", "model": "claude-sonnet-4-6"},
    "team_gpt":     {"prompt": "team",  "model": "gpt-mini"},
    "team_sonnet":  {"prompt": "team",  "model": "claude-sonnet-4-6"},  # 팀 확정 사양
}

# ─── 대상 셀 (PREREG §2-3 — 사전 고정, 사후 추가 금지) ───────────────────────
CELLS = [
    ("esa", "fact_esa_03", 2, "unmentioned", "축약우대 반례: 원문에 더 가까운 표현"),
    ("esa", "fact_esa_03", 3, "mentioned",   "축약우대 반례: 더 축약된 표현"),
    ("esa", "fact_esa_11", 2, "mentioned",   "샌드위치 앞"),
    ("esa", "fact_esa_11", 3, "unmentioned", "샌드위치 가운데"),
    ("esa", "fact_esa_11", 4, "mentioned",   "샌드위치 뒤"),
    ("esa", "fact_esa_01", 1, "mentioned",   "오탈락 실증 팩트 생존 구간"),
    ("esa", "fact_esa_01", 2, "unmentioned", "오탈락 실증 팩트 소실 전이"),
    ("carkey", "fact_car_03", 0, "mentioned",   "3라운드 폭 샌드위치 앞"),
    ("carkey", "fact_car_03", 1, "unmentioned", "샌드위치 가운데(이 구간 내내 3~4명 발화)"),
    ("carkey", "fact_car_03", 4, "mentioned",   "샌드위치 뒤"),
    ("carkey", "fact_car_04", 0, "unmentioned", "재판정 5:0 뒤집힘 사례"),
]

# 사전 고정 패턴 3종 (PREREG §2-4) — (이름, 이슈, 팩트, (앞, 가운데, 뒤) stage)
SANDWICHES = [
    ("sandwich_esa_11", "esa", "fact_esa_11", (2, 3, 4)),
    ("sandwich_car_03", "carkey", "fact_car_03", (0, 1, 4)),
]
SHORTCUT = ("shortcut_esa_03", "esa", "fact_esa_03", 2, 3)  # (원문近 stage, 축약 stage)


# ─── 재료 로드 ───────────────────────────────────────────────────────────────
def _facts(issue: str) -> dict:
    """팩트 목록. esa 는 팀 정본, carkey 는 파일럿 픽스처(tp1 이 쓴 것과 동일 파일)."""
    p = (ROOT / "data/facts/facts_issue_esa.json" if issue == "esa"
         else PILOT_FIX / "facts_issue_carkey.json")
    return {f["fact_id"]: f for f in json.loads(p.read_text(encoding="utf-8"))["facts"]}


def _utterances(issue: str) -> dict[int, list[dict]]:
    """tp1 발화 로그를 stage(round)별로. 발화 생성은 하지 않는다 — 판정만 다시 한다."""
    p = PILOT_DATA / f"debate_issue_{issue}_tp1.jsonl"
    out: dict[int, list[dict]] = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        ev = json.loads(ln)
        if ev.get("event") == "utterance":
            out.setdefault(ev["round"], []).append(ev)
    return out


def _pilot_original(issue: str) -> dict[tuple[str, int], dict]:
    """파일럿 원판정 — 뒤집힘 판정의 기준선."""
    j = json.loads((PILOT_DATA / f"judgment_issue_{issue}_tp1.json").read_text(encoding="utf-8"))
    return {(f["fact_id"], st["stage"]): f for st in j["stages"] for f in st["facts"]}


# ─── 호출층 (얇게, 공급자 2종 + 절단 가드) ───────────────────────────────────
_N_CALLS = 0
_MAX_CALLS = 200
_clients: dict = {}


def _chat(model_id: str, provider: str, system: str, user: str, seed: int) -> str:
    """system + user 한 번 호출. 절단은 즉시 에러(D1 교훈 — 폐기 대상이므로 조용히 넘기지 않는다).

    llm.py 를 쓰지 않는 이유: llm.obtain_response 는 system 프롬프트를 받지 않는다(단일 user
    메시지). 판정 프롬프트는 system/user 분리가 본질이라 여기서 직접 부른다. 단 모델 ID·공급자
    해석은 llm 의 함수를 그대로 쓴다(별칭 표 사본을 만들지 않는다)."""
    global _N_CALLS
    _N_CALLS += 1
    if _N_CALLS > _MAX_CALLS:
        raise SystemExit(f"[ABORT] 호출 상한 초과 ({_N_CALLS} > {_MAX_CALLS})")

    if provider == "anthropic":
        if "anthropic" not in _clients:
            from anthropic import Anthropic
            import os
            _clients["anthropic"] = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = _clients["anthropic"].messages.create(
            model=model_id, max_tokens=MAX_JUDGE_TOKENS, temperature=TEMPERATURE,
            system=system, messages=[{"role": "user", "content": user}])
        if msg.stop_reason == "max_tokens":
            raise RuntimeError(f"출력 절단(stop_reason=max_tokens) model={model_id} — 폐기 대상")
        return "".join(b.text for b in msg.content
                       if getattr(b, "type", None) == "text")

    if provider == "openai":
        import os
        import requests
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": model_id,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}],
                  "max_completion_tokens": MAX_JUDGE_TOKENS,
                  "temperature": TEMPERATURE,
                  "seed": seed},          # OpenAI 만 지원 — best-effort
            timeout=180)
        if r.status_code != 200:
            raise RuntimeError(f"OpenAI {r.status_code}: {r.text[:300]}")
        ch = r.json()["choices"][0]
        if ch.get("finish_reason") == "length":
            raise RuntimeError(f"출력 절단(finish_reason=length) model={model_id} — 폐기 대상")
        return ch["message"]["content"] or ""

    raise KeyError(f"이 실험이 지원하지 않는 공급자: {provider}")


# ─── vote_fn 조립 — judge.judge_fact 에 주입되는 유일한 가변부 ───────────────
def make_vote_fn(prompt_kind: str, model: str, *, offline: bool, seed_base: int):
    """(프롬프트 종류, 모델) → vote_fn(fact, stage_utterances) -> judge 표 스키마.

    반환 스키마는 judge.judge_fact 가 기대하는 {status, agents_mentioning, reason} 이다.
    파일럿 프롬프트는 {"mentioned": bool} 로 답하므로 여기서 정규화한다 — 정규화 규칙을
    러너에 두는 이유는 judge.py 를 건드리지 않기 위해서다."""
    model_id = llm.resolve_model(model)
    provider = None if offline else llm.resolve_provider(model)
    counter = {"n": 0}

    def vote(fact: dict, utts: list[dict]) -> dict:
        counter["n"] += 1
        if offline:
            # 구조 검증 전용 스텁. 판정 내용에 의미 없음 — 원문 부분일치(judge 오프라인 규칙과
            # 동일)로 결정론적 값을 낸다. 프롬프트 종류를 reason 에 적어 경로를 구분한다.
            v = judge._offline_vote(fact, utts)
            return {**v, "reason": f"offline-stub({prompt_kind})"}

        seed = seed_base + counter["n"]
        if prompt_kind == "team":
            system, user = judge.JUDGE_SYSTEM, judge._user_prompt(fact, utts)
            raw = _chat(model_id, provider, system, user, seed)
            return judge._parse_vote(raw, utts)          # 정본 파서 재사용

        pairs = [(u.get("agent_id"), u.get("response_text", "")) for u in utts]
        raw = _chat(model_id, provider, PILOT_JUDGE_SYSTEM,
                    pilot_judge_prompt(fact["text"], pairs), seed)
        try:
            s = raw[raw.index("{"): raw.rindex("}") + 1]
            d = json.loads(s)
        except (ValueError, json.JSONDecodeError):
            return {"status": "unmentioned", "agents_mentioning": [],
                    "reason": f"parse_fail: {raw[:120]}"}
        valid = {u.get("agent_id") for u in utts}
        return {"status": "mentioned" if d.get("mentioned") else "unmentioned",
                "agents_mentioning": [a for a in d.get("agents_mentioning", [])
                                      if a in valid],
                "reason": "pilot-prompt(normalized)"}

    return vote


# ─── phase: cells — 셀 적출이 PREREG 와 맞는지 확인(호출 0) ──────────────────
def phase_cells() -> None:
    ok = True
    for issue, fid, stage, expect, why in CELLS:
        orig = _pilot_original(issue).get((fid, stage))
        facts = _facts(issue)
        utts = _utterances(issue).get(stage, [])
        got = orig["status"] if orig else "<없음>"
        mark = "OK " if got == expect else "MISMATCH"
        if got != expect:
            ok = False
        print(f"[{mark}] {issue}/{fid}/s{stage}: 원판정={got} (기대 {expect}) · "
              f"발화 {len(utts)}명 · 팩트존재={fid in facts} · {why}")
    print(f"\n총 {len(CELLS)} 셀 · 조건 {len(CONDITIONS)} · 표 {N_VOTES} "
          f"→ 실호출 {len(CELLS) * len(CONDITIONS) * N_VOTES} 콜")
    print("PREREG 대조:", "일치" if ok else "⚠ 불일치 — PREREG 수정 없이 진행 금지")
    if not ok:
        raise SystemExit(1)


# ─── phase: verify-prompts — 고정 인용이 run_pilot 원문과 같은가 ─────────────
def phase_verify_prompts() -> None:
    src = (TP / "run_pilot.py").read_text(encoding="utf-8")
    sys_ok = PILOT_JUDGE_SYSTEM.replace("  ", " ")[:30] in src.replace("\n", " ").replace('"', '')
    probe = pilot_judge_prompt("X", [("agent_1", "Y")])
    tokens = ["발언 기록:", "판정 대상 사실:", '"mentioned": true/false']
    tok_ok = all(t in src for t in tokens)
    print("run_pilot.py 원문 대조:")
    print(f"  JUDGE_SYSTEM 앞부분 일치: {sys_ok}")
    print(f"  judge_prompt 구성 토큰 일치: {tok_ok} ({tokens})")
    print(f"  고정 인용 sha256: pilot_system={_h(PILOT_JUDGE_SYSTEM)} "
          f"pilot_prompt_shape={_h(probe)}")
    print(f"  팀 프롬프트 sha256: {_h(judge.JUDGE_SYSTEM)} ({TEAM_PROMPT_VER})")
    if not (sys_ok and tok_ok):
        raise SystemExit("⚠ 고정 인용이 run_pilot 원문과 어긋남 — 실행 전 정정 필요")


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# ─── phase: run ──────────────────────────────────────────────────────────────
def phase_run(only: str | None, offline: bool) -> None:
    conds = {only: CONDITIONS[only]} if only else CONDITIONS
    for cname, cfg in conds.items():
        dst = HERE / f"votes_{cname}{'_offline' if offline else ''}.json"
        if dst.exists():
            print(f"[{cname}] {dst.name} 존재 — 스킵")
            continue
        if not offline:
            llm.preflight(cfg["model"])      # 키 없으면 여기서 죽는다(재작성된 llm 관문 사용)
        vote_fn = make_vote_fn(cfg["prompt"], cfg["model"], offline=offline,
                              seed_base=hash(cname) % 100000)
        rows = []
        for i, (issue, fid, stage, expect, why) in enumerate(CELLS):
            fact = _facts(issue)[fid]
            utts = _utterances(issue)[stage]
            rec = judge.judge_fact(utts, fact, vote_fn=vote_fn, n_votes=N_VOTES)
            statuses = [v["status"] for v in rec["votes"]]
            rows.append({
                "issue": issue, "fact_id": fid, "stage": stage,
                "pilot_original": expect, "why_selected": why,
                "majority": rec["status"],
                "split": len(set(statuses)) > 1,
                "flip_vs_pilot": rec["status"] != expect,
                "attrib_set": rec["agents_mentioning"],
                "attrib_split": len({tuple(sorted(v["agents_mentioning"]))
                                     for v in rec["votes"]}) > 1,
                "n_parse_fail": sum(1 for v in rec["votes"]
                                    if judge._is_parse_fail(v)),
                "votes": rec["votes"],          # 원본 전량 보존(확정 사양)
            })
            print(f"[{cname}] {issue}/{fid}/s{stage}: {rec['status']} "
                  f"{statuses} (원판정 {expect})")
            (HERE / f"votes_{cname}.json.part").write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        meta = {
            "condition": cname, "prompt_kind": cfg["prompt"], "model": cfg["model"],
            "model_id": llm.resolve_model(cfg["model"]),
            "n_votes": N_VOTES, "temperature": TEMPERATURE, "offline_stub": offline,
            "prompt_ver": TEAM_PROMPT_VER if cfg["prompt"] == "team" else PILOT_PROMPT_VER,
            "prompt_sha256": _h(judge.JUDGE_SYSTEM if cfg["prompt"] == "team"
                                else PILOT_JUDGE_SYSTEM),
            "prereg": "experiments/judge_crossmodel/PREREG.md (5bb7644)",
            "status": ("구조 검증 스텁 — 판정 내용 무의미" if offline
                       else "실측. 해석은 PREREG §3 표에 대조할 것"),
            "n_calls": _N_CALLS,
        }
        dst.write_text(json.dumps({"meta": meta, "rows": rows},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        part = HERE / f"votes_{cname}.json.part"
        if part.exists():
            part.unlink()
        print(f"[{cname}] 완료 → {dst.name} (호출 누적 {_N_CALLS})")


# ─── phase: report — PREREG §2-4 지표 집계(호출 0) ───────────────────────────
def phase_report(offline: bool) -> None:
    suffix = "_offline" if offline else ""
    res: dict = {"prereg": "experiments/judge_crossmodel/PREREG.md (5bb7644)",
                 "note": ("오프라인 스텁 집계 — 구조 검증용, 해석 금지" if offline
                          else "해석은 PREREG §3 해석 기준표에 대조할 것"),
                 "conditions": {}}
    for cname in CONDITIONS:
        p = HERE / f"votes_{cname}{suffix}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        rows = d["rows"]
        by = {(r["issue"], r["fact_id"], r["stage"]): r for r in rows}
        n = len(rows)
        pats = {}
        for name, issue, fid, (a, m, b) in SANDWICHES:
            ra, rm, rb = (by.get((issue, fid, s)) for s in (a, m, b))
            pats[name] = (None if not (ra and rm and rb) else
                          rm["majority"] != ra["majority"] and rm["majority"] != rb["majority"])
        sname, sissue, sfid, s_lit, s_gist = SHORTCUT
        rl, rg = by.get((sissue, sfid, s_lit)), by.get((sissue, sfid, s_gist))
        pats[sname] = (None if not (rl and rg) else
                       rg["majority"] == "mentioned" and rl["majority"] == "unmentioned")
        res["conditions"][cname] = {
            "meta": d["meta"],
            "n_cells": n,
            "split_rate": round(sum(r["split"] for r in rows) / n, 4),
            "flip_rate": round(sum(r["flip_vs_pilot"] for r in rows) / n, 4),
            "attrib_split_rate": round(sum(r["attrib_split"] for r in rows) / n, 4),
            "n_parse_fail": sum(r["n_parse_fail"] for r in rows),
            "patterns": pats,
            "n_patterns_reproduced": sum(1 for v in pats.values() if v is True),
            "flipped_cells": [f"{r['issue']}/{r['fact_id']}/s{r['stage']}"
                              for r in rows if r["flip_vs_pilot"]],
        }
    # PREREG §5 무효 조건 자동 점검
    pg = res["conditions"].get("pilot_gpt")
    if pg:
        res["validity_pilot_gpt_reproduces"] = (
            "무효 — 재현 실패(뒤집힘 4개 이상)" if len(pg["flipped_cells"]) >= 4
            else "유효 — 재현 대조군 통과")
    dst = HERE / f"results{suffix}.json"
    dst.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"\n[saved] {dst}", file=sys.stderr)


def main() -> None:
    global _MAX_CALLS
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["cells", "verify-prompts", "run", "report"])
    ap.add_argument("--condition", choices=sorted(CONDITIONS))
    ap.add_argument("--offline", action="store_true",
                    help="스텁으로 구조만 검증(LLM 호출 0)")
    ap.add_argument("--max-calls", type=int, default=200)
    a = ap.parse_args()
    _MAX_CALLS = a.max_calls
    if a.phase == "cells":
        phase_cells()
    elif a.phase == "verify-prompts":
        phase_verify_prompts()
    elif a.phase == "run":
        phase_run(a.condition, a.offline)
    else:
        phase_report(a.offline)
    print(f"[calls] 이번 실행 LLM 호출 {_N_CALLS}회")


if __name__ == "__main__":
    main()
