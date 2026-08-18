# -*- coding: utf-8 -*-
"""[히든 프로필 · 기억 축] 통제 팔 러너 — 폴링 1콜/에이전트만 다시 던진다.

적대적 리뷰 v1 의 치명 지적 둘을 가르기 위한 것이다. 둘 다 **폴링 입력 한 칸만** 바꾼다.

  C1 폴링 격리 : 이미 완주한 토론 run 을 읽어, 폴링 입력에서 **이웃 발언을 뺀다**.
                 (엔진의 폴링 블록은 structure=full 이면 이웃 3명의 마지막 발언을 전부
                  넣는다 — ①③의 만점이 기억 조건이 아니라 그 프롬프트 덕일 수 있다.)
                 같은 토론 위에서 폴링만 갈아 끼우므로 **짝지은 대조**다.
  C2 기준선 문면 : 단독 기준선을 원래 문면("논의가 끝났습니다")으로 다시 잰다.
                 (S 팔은 도입 2문장을 "아직 논의는 없었습니다"로 바꿔 돌렸다 — 그 문면이
                  판단을 보수적으로 만들어 기준선을 낮췄을 수 있다.)

엔진·프롬프트 자산·기존 러너는 수정하지 않는다. 산출물은 debate jsonl 형식이라
modules.hidden_profile.outcome() 과 modules.validate 가 그대로 읽는다.

규율: 호출 상한(config max_llm_calls) · 콜마다 append+flush · 프롬프트 전문 보존 ·
이미 있는 run 파일은 덮어쓰지 않는다 · 경로는 paths.py.

사용:
  PYTHONUTF8=1 python experiments/hidden_profile_memory/repoll.py \
      --config configs/hire_mem3_c1_selfpoll.yaml --source-run prev_rep1 --run c1_prev_rep1 --live
  PYTHONUTF8=1 python experiments/hidden_profile_memory/repoll.py \
      --config configs/hire_mem3_c2_introfix.yaml --run c2_rep1 --live
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

# coop_final 도입부. 단독 팔(run_solo_baseline)이 쓰는 교체분과 같은 문자열이다.
DISCUSSED = "당신은 한 논의에 참석한 구성원이었습니다. 논의가 끝났습니다."
SOLO = "당신은 아래 안건을 결정하는 자리에 참석했습니다. 아직 논의는 없었습니다."

CONTEXTS = ("self_utterance", "assigned_facts", "last_utterances")
INTROS = ("discussed", "solo")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def last_utterances(events: list[dict]) -> dict[str, dict]:
    """에이전트별 마지막 발화. 엔진이 좌석을 섞으므로 agent_id 로 잡는다."""
    out: dict[str, dict] = {}
    for e in events:
        if e.get("event") != "utterance":
            continue
        cur = out.get(e["agent_id"])
        if cur is None or e.get("round", 0) >= cur.get("round", 0):
            out[e["agent_id"]] = e
    return out


def neighbor_order(events: list[dict]) -> dict[str, list[str]]:
    """에이전트별 이웃 목록을 **엔진과 같은 순서로** 복원한다.

    순서도 계약이다 — 엔진은 이웃을 `edges[i]`(좌석 인덱스) 순서로 붙이고 재조립 검증도
    그 순서를 따른다. 좌석은 seed 로 섞이므로 agent_id 순으로 붙이면 같은 정보를 다른
    순서로 준 run 이 된다. `seating` 이벤트가 그 배열의 정본이다."""
    seat = [e for e in events if e.get("event") == "seating"]
    if not seat:
        raise SystemExit("source run 에 seating 이벤트가 없다 — 이웃 순서를 복원할 수 없다")
    order = seat[0]["order"]                       # 좌석 인덱스 → agent_id
    edges = debate_engine.build_edges(seat[0].get("structure", "full"), len(order))
    return {order[i]: [order[j] for j in edges[i]] for i in range(len(order))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--run", required=True)
    ap.add_argument("--source-run", help="C1 전용 — 폴링을 다시 던질 토론 run_id")
    ap.add_argument("--max-calls", type=int, default=0)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true")
    mode.add_argument("--live", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    issue_id = cfg["issue_id"]
    model = cfg["debate_model"]
    temp = float(cfg["debate_temperature"])
    reasoning = str(cfg.get("reasoning", "default"))
    context_mode = cfg["poll_context"]
    intro_mode = cfg["poll_intro"]
    if context_mode not in CONTEXTS:
        raise SystemExit(f"미지원 poll_context: {context_mode} (지원: {CONTEXTS})")
    if intro_mode not in INTROS:
        raise SystemExit(f"미지원 poll_intro: {intro_mode} (지원: {INTROS})")
    cap = args.max_calls or int(cfg.get("max_llm_calls", 0))
    if cap <= 0:
        raise SystemExit("호출 상한이 없다 — config 의 max_llm_calls 또는 --max-calls 필요")

    issue_doc = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
    facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    assign_doc = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    question = issue_doc.get("question") or issue_doc["title"]
    body = issue_doc["body"]
    fact_by_id = {f["fact_id"]: f["text"] for f in facts_doc["facts"]}

    source_ref = None
    lasts: dict[str, dict] = {}
    neighbors: dict[str, list[str]] = {}
    if context_mode in ("self_utterance", "last_utterances"):
        if not args.source_run:
            raise SystemExit(f"poll_context={context_mode} 는 --source-run 이 필요하다")
        src = paths.debate(issue_id, args.source_run)
        src_text = src.read_text(encoding="utf-8")
        src_events = [json.loads(l) for l in src_text.splitlines() if l.strip()]
        lasts = last_utterances(src_events)
        if context_mode == "last_utterances":
            neighbors = neighbor_order(src_events)
        source_ref = {"run_id": args.source_run, "file": src.name,
                      "sha256": sha256(src_text)}

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
         source_ref=source_ref,
         settings={"window": cfg.get("window", "none"), "memory": "none",
                   "rounds": int(cfg.get("rounds", 0)),
                   "note_budget": None, "note_call": None, "note_parse_ver": None,
                   "final_poll": True, "ledger_mode": "off", "structure": None,
                   "seed": cfg["seed"], "stance": "none", "persona": None,
                   "overlap_k": assign_doc.get("overlap_k"),
                   "assignment_mode": assign_doc.get("created_by"),
                   "poll_context": context_mode, "poll_intro": intro_mode,
                   "reasoning": reasoning, "deviations": []},
         model=llm.resolve_model(model), temperature=temp,
         prompt_ver=f"{our_prompts.version_tag()}+repoll_{context_mode}_{intro_mode}")

    n_calls = 0
    n_fallback = 0
    for ag in assign_doc["agents"]:
        aid = ag["agent_id"]
        if context_mode == "self_utterance":
            src_e = lasts.get(aid)
            if src_e is None:
                raise SystemExit(f"{args.source_run} 에 {aid} 발화가 없다")
            final_context = f"[당신의 마지막 발언]\n{src_e['response_text']}\n"
            slot = {"source_round": src_e.get("round")}
        elif context_mode == "last_utterances":
            # 엔진의 비수첩 폴링과 **글자 그대로 같은 형식**이어야 한다 — 이 컨텍스트는
            # 전 팔 공통 잣대(폴링 B)이고, 형식이 어긋나면 팔 간 비교가 그 차이를 탄다.
            src_e = lasts.get(aid)
            if src_e is None:
                raise SystemExit(f"{args.source_run} 에 {aid} 발화가 없다")
            final_context = (f"[당신의 마지막 발언]\n{src_e['response_text']}\n\n"
                             f"[참석자들의 마지막 발언]\n")
            for k, nb in enumerate(neighbors.get(aid, [])):
                nb_e = lasts.get(nb)
                if nb_e is None:
                    raise SystemExit(f"{args.source_run} 에 {nb} 발화가 없다")
                final_context += f"참석자{k + 1}: {nb_e['response_text']}\n"
            slot = {"source_round": src_e.get("round"),
                    "others": list(neighbors.get(aid, []))}
        else:
            lines = "\n".join(f"- {fact_by_id[i]}" for i in ag["assigned_fact_ids"])
            final_context = f"[당신이 받은 자료]\n{lines}"
            slot = {"assigned_fact_ids": ag["assigned_fact_ids"]}

        prompt = debate_engine.assemble_coop_final(question, body, final_context)
        if DISCUSSED not in prompt:
            raise SystemExit("coop_final 도입부가 바뀌었다 — 문안 교체 전제가 깨졌다")
        if intro_mode == "solo":
            prompt = prompt.replace(DISCUSSED, SOLO)

        emit("repoll_prompt", agent_id=aid, round=0, prompt_hash=sha256(prompt),
             poll_context=context_mode, poll_intro=intro_mode, slot=slot,
             prompt_text=prompt)
        if args.dry:
            print(f"[dry] {aid} · {context_mode}/{intro_mode} · 프롬프트 {len(prompt)}자")
            continue
        if n_calls >= cap:
            raise SystemExit(f"호출 상한 초과 — {n_calls}/{cap}")
        n_calls += 1
        resp = llm.obtain_response(prompt, model=model, temperature=temp,
                                   reasoning=reasoning)
        # 폴백 감지 — obtain_response 는 일시 장애를 5회 재시도 뒤 공백으로 돌려준다.
        # 세지 않으면 "폴링 4/4 성공"으로 찍히고 빈 응답이 채점에 섞인다(무음 실패).
        if not resp.strip():
            n_fallback += 1
        emit("final_poll", agent_id=aid, round=0, prompt_hash=sha256(prompt),
             prompt_ver=f"{our_prompts.version_tag()}+repoll_{context_mode}_{intro_mode}",
             model=llm.resolve_model(model), temperature=temp, response_text=resp)

    if fh is not None:
        emit("run_deviations", deviations=list(llm.LAST_DEVIATIONS),
             n_fallback=n_fallback)
        fh.close()
        tag = "[OK]" if n_fallback == 0 else "[무효]"
        print(f"{tag} {out_path.name} — 폴링 {n_calls}/{cap}, 폴백 {n_fallback}건, "
              f"편차 {list(llm.LAST_DEVIATIONS) or '없음'}")
        if n_fallback:
            # 사전등록 §6-7: 폴백이 0 이 아니면 그 런은 무효다. 조용히 넘기면 빈 응답이
            # 채점에 섞이고, 러너는 성공으로 찍는다(리뷰 중대 6 의 구멍).
            # 파일은 남긴다 — 장애의 기록이고, 원자료는 지우지 않는다(규약 8).
            raise SystemExit(
                f"폴백 {n_fallback}건 — 이 런은 무효다. 엔드포인트를 확인하고 "
                f"새 run_id 로 다시 돌려라. 파일은 남긴다: {out_path.name}")
    else:
        print(f"[dry OK] 조립 {len(assign_doc['agents'])}건 · 실호출 0 · 파일 안 씀")


if __name__ == "__main__":
    main()
