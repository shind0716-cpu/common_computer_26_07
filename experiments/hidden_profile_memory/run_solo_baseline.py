# -*- coding: utf-8 -*-
"""[히든 프로필 · 기억 축] 단독 기준선 러너 — 토론 없이 최종 폴링 1콜/에이전트.

무엇을 재나: 각 에이전트가 **자기 배정 팩트만** 보고 답한 결론. 토론 팔의 정답 수가
"취합의 몫"인지 "원래 알던 것"인지 가르는 분모다(히든 프로필 REPORT_v0 §7-1 정의).

왜 엔진을 안 쓰나: debate_engine 에는 라운드 0 팔이 없다. rounds: 0 으로 돌려도
최종 폴링이 이웃의 초기 발화를 보므로(engine 의 final_poll 블록) 단독이 아니다.
엔진·프롬프트 자산은 수정하지 않는다 — coop_final 템플릿을 읽어서 쓴다.

프롬프트 편차 (사전 기재): coop_final 첫 두 문장은 "논의가 끝났습니다"를 전제한다.
단독 팔에는 논의가 없으므로 그 두 문장만 교체하고 나머지 문면·출력 형식은 그대로
둔다. 교체분을 포함한 프롬프트 전문을 run 파일에 저장한다(재조립 없이 대조 가능).

산출: data/debates/debate_<issue>_<run>.jsonl — run_meta + solo_prompt + final_poll.
      final_poll 이벤트 형식이 엔진과 같으므로 modules.hidden_profile.outcome() 이
      그대로 읽는다(채점기 공용).

규율(CLAUDE.md): 호출 상한(--max-calls 초과 즉사) · 한 콜마다 append+flush ·
프롬프트/응답 원문 전량 보존 · 경로는 paths.py · encoding="utf-8" 명시.

사용:
  PYTHONUTF8=1 python experiments/hidden_profile_memory/run_solo_baseline.py \
      --config configs/hire_mem3_solo.yaml --run solo_rep1 --dry
  (--dry 는 0콜. 실호출은 --live)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from modules import debate_engine, llm, our_prompts, paths  # noqa: E402

# coop_final 의 도입부 — 단독 팔에서는 사실과 다르므로 이 두 문장만 갈아 끼운다.
DISCUSSED = "당신은 한 논의에 참석한 구성원이었습니다. 논의가 끝났습니다."
SOLO = "당신은 아래 안건을 결정하는 자리에 참석했습니다. 아직 논의는 없었습니다."
SOLO_PROMPT_VER_SUFFIX = "+solo_v1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assemble_solo_final(question: str, body: str, fact_lines: str) -> str:
    """coop_final 을 재사용하되 도입부만 단독용으로 바꾼다."""
    prompt = debate_engine.assemble_coop_final(
        question, body, f"[당신이 받은 자료]\n{fact_lines}")
    if DISCUSSED not in prompt:
        raise SystemExit("coop_final 도입부가 바뀌었다 — 이 러너의 문안 교체 전제가 깨졌다")
    return prompt.replace(DISCUSSED, SOLO)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--run", required=True, help="run_id (예: solo_rep1)")
    ap.add_argument("--max-calls", type=int, default=0, help="0이면 config 의 max_llm_calls")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true", help="0콜 조립 리허설")
    mode.add_argument("--live", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    issue_id = cfg["issue_id"]
    model = cfg["debate_model"]
    temp = float(cfg["debate_temperature"])
    reasoning = str(cfg.get("reasoning", "default"))
    cap = args.max_calls or int(cfg.get("max_llm_calls", 0))
    if cap <= 0:
        raise SystemExit("호출 상한이 없다 — config 의 max_llm_calls 또는 --max-calls 필요")

    issue_doc = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
    facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    assign_doc = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    question = issue_doc.get("question") or issue_doc["title"]
    body = issue_doc["body"]
    fact_by_id = {f["fact_id"]: f["text"] for f in facts_doc["facts"]}
    agents = assign_doc["agents"]

    out_path = paths.debate(issue_id, args.run)
    if out_path.exists():
        raise SystemExit(f"이미 있다 — {out_path.name} (덮어쓰지 않는다)")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.live:
        llm.preflight(model, temperature=temp, reasoning=reasoning)

    fh = None if args.dry else out_path.open("w", encoding="utf-8")

    def emit(event: str, **kw) -> None:
        row = {"event": event, "run_id": args.run, "ts": now(), **kw}
        if fh is None:
            return
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()

    emit("run_meta", issue_id=issue_id, condition=cfg.get("condition"),
         config_ref={"name": args.config.name,
                     "sha256": sha256(args.config.read_text(encoding="utf-8"))},
         # 설정 사전 8축 — 엔진 run_meta 와 같은 칸을 채운다. validate 의 debate 계약이
         # window·memory·rounds·structure·stance·overlap_k·ledger_mode·seed 를 요구한다.
         settings={"window": "none", "memory": "none", "rounds": 0,
                   "note_budget": None, "note_call": None, "note_parse_ver": None,
                   "final_poll": True, "ledger_mode": "off",
                   "structure": None, "seed": cfg["seed"],
                   "stance": "none",                       # 협력(무입장) — 배분표 계승
                   "persona": None,
                   "overlap_k": assign_doc.get("overlap_k"),
                   "assignment_mode": assign_doc.get("created_by"),
                   "reasoning": reasoning, "deviations": []},
         model=llm.resolve_model(model), temperature=temp,
         prompt_ver=our_prompts.version_tag() + SOLO_PROMPT_VER_SUFFIX)

    n_calls = 0
    for ag in agents:
        ids = ag["assigned_fact_ids"]
        lines = "\n".join(f"- {fact_by_id[i]}" for i in ids)
        prompt = assemble_solo_final(question, body, lines)
        # 프롬프트 전문 보존 — 이 팔은 prompt_assembly 재조립 경로를 타지 않는다.
        emit("solo_prompt", agent_id=ag["agent_id"], round=0,
             prompt_ver=our_prompts.version_tag() + SOLO_PROMPT_VER_SUFFIX,
             prompt_hash=sha256(prompt), assigned_fact_ids=ids, prompt_text=prompt)
        if args.dry:
            print(f"[dry] {ag['agent_id']} 팩트 {len(ids)}개 · 프롬프트 {len(prompt)}자")
            continue
        if n_calls >= cap:
            raise SystemExit(f"호출 상한 초과 — {n_calls}/{cap}")
        n_calls += 1
        resp = llm.obtain_response(prompt, model=model, temperature=temp,
                                   reasoning=reasoning)
        emit("final_poll", agent_id=ag["agent_id"], round=0,
             prompt_ver=our_prompts.version_tag() + SOLO_PROMPT_VER_SUFFIX,
             prompt_hash=sha256(prompt), model=llm.resolve_model(model),
             temperature=temp, response_text=resp)

    if fh is not None:
        # 편차(파라미터가 갈린 이력)는 조용히 흘리지 않는다 — 없으면 빈 줄로 남긴다.
        emit("run_deviations", deviations=list(llm.LAST_DEVIATIONS))
        fh.close()
        print(f"[OK] {out_path.name} — 에이전트 {len(agents)}, LLM 호출 {n_calls}/{cap}, "
              f"편차 {list(llm.LAST_DEVIATIONS) or '없음'}")
    else:
        print(f"[dry OK] 조립 {len(agents)}건 · 실호출 0 · 파일 안 씀")


if __name__ == "__main__":
    main()
