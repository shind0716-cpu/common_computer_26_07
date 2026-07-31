"""[P0 · 탐색 계측 · 동범] 결정 1건의 가격 — 기존 debate 로그의 호출·글자 전수조사 (실호출 0).

지위: 탐색(계기 교정). "숙의 비용 실험"(P1)의 확증 지표는 사전등록으로 별도 고정하며,
이 스크립트는 기존 로그를 소급 계수해 비용 축의 자릿수를 확인하는 용도다.

방법 (고정):
  입력  = prompt_assembly 슬롯을 debate_engine.assemble_*(단일 소스)로 재조립한 텍스트.
          sha256 이 로그의 prompt_hash 와 일치하는 것만 계수한다 — 조립 규칙이
          드리프트하면 수치가 조용히 틀리는 대신 hash_mismatch 로 시끄럽게 빠진다.
          (재조립 글루는 modules.validate 의 --deep 경로와 같은 헬퍼·같은 조립 함수를
           쓴다. 글루 자체의 사본화 위험은 hash 대조가 상쇄한다.)
  출력  = utterance.response_text + final_poll.response_text + note_update.note_text
          (origin 이 intervention 인 수첩은 제외 — 사람 입력이지 모델 출력이 아니다).
  글자  = 정확값. 토큰 = 추정(글자 x 0.45~0.7 tok/char 구간) — 한글 토크나이저 실측 전.

한계 (미리 적음):
  - note_call=utterance 모드의 수첩은 발화와 한 호출의 출력이라 JSON 래퍼 오버헤드가
    빠져 있다(출력 과소추정 방향, 소폭).
  - discussion_* 템플릿(재현 트랙)은 저자 저장소(DELIBTRACE_DIR)가 있어야 재조립된다 —
    없으면 그 run 은 출력만 계수하고 입력은 "재조립 불가"로 보고한다.
  - API usage 필드가 로그에 없어(스키마 밖) 공급자 보고 토큰과의 대조는 P1 에서.

사용: python experiments/cost_frontier/p0_census.py
산출: experiments/cost_frontier/p0_census.json (+ stdout 표)
"""
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")  # cp949 콘솔 방어

from modules import paths  # noqa: E402
from modules.validate import (  # noqa: E402 — --deep 과 같은 헬퍼(단일 소스)
    _assemble_incoming, _assembly_ref_text, _note_ref_text)

TOK_LO, TOK_HI = 0.45, 0.7  # 한글 혼합 텍스트 tok/char 추정 구간 (가정 — P1 에서 실측 대체)


def _reassemble(pa: dict, ctx: dict) -> str:
    """prompt_assembly 이벤트 하나 → 입력 전문. validate.deep_check_debate 의 분기와
    같은 조립 함수를 부른다. 미등록 template 은 ValueError."""
    from modules import debate_engine
    slots = pa["slots"]
    utts, injects, note_evs = ctx["utts"], ctx["injects"], ctx["note_evs"]
    question, body, fact_by_id = ctx["question"], ctx["body"], ctx["fact_by_id"]
    where = f"round={pa.get('round')} agent={pa.get('agent_id')}"

    def fact_text() -> str:
        return "".join(f"{fact_by_id[fid]}\n" for fid in slots.get("assigned_fact_ids", []))

    t = pa["template"]
    if t == "discussion_initial":
        u = utts.get((pa["round"], pa["agent_id"]))
        answer = "yes" if (u or {}).get("stance") == "pro" else "no"
        return debate_engine.assemble_initial(question, fact_text(), answer)
    if t == "discussion_continue":
        from modules import authors_prompts  # 저자 저장소 필요 — 부재 시 여기서 예외
        others = "".join(f"View {k + 1}: {_assembly_ref_text(utts, ref, where)}\n"
                         for k, ref in enumerate(slots.get("others", [])))
        if slots.get("inject"):
            others += injects[slots["inject"]["round"]]["injected_text"]
        ptxt = _assembly_ref_text(utts, slots["previous"], where)
        setting = authors_prompts.load_settings()[pa["setting_key"]]
        return debate_engine.assemble_continue(question, ptxt or "", others, setting)
    if t == "coop_initial":
        return debate_engine.assemble_coop_initial(question, body, fact_text())
    if t == "coop_continue":
        incoming = _assemble_incoming(utts, slots, injects, where)
        ptxt = _assembly_ref_text(utts, slots["previous"], where)
        return debate_engine.assemble_coop_continue(question, body, fact_text(),
                                                    ptxt or "", incoming)
    if t in ("coop_continue_note", "coop_continue_note_say"):
        incoming = _assemble_incoming(utts, slots, injects, where)
        note_text = _note_ref_text(note_evs, slots.get("note"), where)
        return debate_engine.assemble_coop_continue_note(
            question, body, note_text or "", incoming, template=t)
    if t == "coop_note_update":
        incoming = "".join(f"참석자{k + 1}: {_assembly_ref_text(utts, ref, where)}\n"
                           for k, ref in enumerate(slots.get("others", [])))
        my_ref = slots.get("my_say")
        my_say = _assembly_ref_text(utts, my_ref, where) if my_ref else ""
        note_text = _note_ref_text(note_evs, slots.get("note"), where)
        return debate_engine.assemble_coop_note_update(
            question, note_text or "", my_say or "", incoming, slots["note_budget"])
    if t == "coop_final":
        if slots.get("note") is not None:
            note_text = _note_ref_text(note_evs, slots["note"], where)
            final_context = f"[당신의 수첩]\n{note_text or ''}\n"
        else:
            pref = slots.get("previous")
            ptxt = _assembly_ref_text(utts, pref, where) if pref else ""
            fc = f"[당신의 마지막 발언]\n{ptxt or ''}\n\n[참석자들의 마지막 발언]\n"
            for k, ref in enumerate(slots.get("others", [])):
                fc += f"참석자{k + 1}: {_assembly_ref_text(utts, ref, where)}\n"
            final_context = fc
        return debate_engine.assemble_coop_final(question, body, final_context)
    raise ValueError(f"미등록 template {t}")


def census_run(path: Path) -> dict:
    events = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    meta = next((e for e in events if e.get("event") == "run_meta"), None)
    pas = [e for e in events if e.get("event") == "prompt_assembly"]
    utt = [e for e in events if e.get("event") == "utterance"]
    polls = [e for e in events if e.get("event") == "final_poll"]
    notes = [e for e in events if e.get("event") == "note_update"
             and e.get("origin") != "intervention"]

    out_chars = (sum(len(e.get("response_text") or "") for e in utt)
                 + sum(len(e.get("response_text") or "") for e in polls)
                 + sum(len(e.get("note_text") or "") for e in notes))
    blank = sum(1 for e in utt if not (e.get("response_text") or "").strip())

    rec = {
        "run": path.name,
        "condition": (meta or {}).get("condition"),
        "model": ((meta or {}).get("settings") or {}).get("debate_model"),
        "calls": len(pas), "utterances": len(utt), "polls": len(polls),
        "notes": len(notes), "blank_utterances": blank,
        "output_chars": out_chars,
        "input_chars": None, "hash_verified": 0, "hash_mismatch": 0,
        "input_error": None,
    }
    if not pas:
        rec["input_error"] = "구 로그(v0.2) — prompt_assembly 없음, 출력만 계수"
        return rec

    # 형제 산출물 로딩 (validate --deep 과 같은 파일명 규약)
    run_id = pas[0].get("run_id")
    stem = path.name[len("debate_"):].rsplit(".", 1)[0]
    issue_id = stem[: -len(run_id) - 1]
    try:
        issue = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
        facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        rec["input_error"] = f"형제 산출물 없음: {e}"
        return rec
    ctx = {
        "utts": {(e.get("round"), e.get("agent_id")): e for e in utt},
        "injects": {e.get("round"): e for e in events if e.get("event") == "ledger_inject"},
        "note_evs": {(e.get("agent_id"), e.get("round")): e
                     for e in events if e.get("event") == "note_update"},
        "question": issue.get("question") or issue["title"],
        "body": issue.get("body", ""),
        "fact_by_id": {f["fact_id"]: f["text"] for f in facts_doc["facts"]},
    }

    total, ok, bad = 0, 0, 0
    per_template: dict[str, dict] = {}
    for pa in pas:
        try:
            inputs = _reassemble(pa, ctx)
        except SystemExit as e:            # validate 헬퍼의 fail() — 참조 결손
            rec["input_error"] = f"재조립 실패: {e}"
            return rec
        except (KeyError, ValueError, FileNotFoundError, ImportError) as e:
            rec["input_error"] = f"재조립 불가({type(e).__name__}): {e}"
            return rec
        digest = hashlib.sha256(inputs.encode("utf-8")).hexdigest()
        if digest == pa["prompt_hash"]:
            ok += 1
            total += len(inputs)
            bucket = per_template.setdefault(pa["template"], {"n": 0, "chars": 0})
            bucket["n"] += 1
            bucket["chars"] += len(inputs)
        else:
            bad += 1
    rec.update(input_chars=total, hash_verified=ok, hash_mismatch=bad,
               per_template=per_template)
    return rec


def main() -> None:
    debates = sorted((paths.DATA / "debates").glob("debate_*.jsonl"))
    rows = [census_run(p) for p in debates]

    print(f"{'run':<42}{'조건':<14}{'콜':>4}{'공백':>4}{'입력자':>9}{'출력자':>8}"
          f"{'검증':>6}  비고")
    for r in rows:
        ic = r["input_chars"]
        print(f"{r['run']:<42}{str(r['condition']):<14}{r['calls']:>4}"
              f"{r['blank_utterances']:>4}{(f'{ic:,}' if ic is not None else '—'):>9}"
              f"{r['output_chars']:>8,}"
              f"{r['hash_verified']:>4}/{r['hash_verified'] + r['hash_mismatch']:<3}"
              f"  {r['input_error'] or ''}")

    verified = [r for r in rows if r["input_chars"]]
    if verified:
        print("\n── 결정 1건의 가격 (검증된 run, 글자 = 정확 / 토큰 = 추정 구간) ──")
        for r in verified:
            tot = r["input_chars"] + r["output_chars"]
            print(f"  {r['run']}: 총 {tot:,}자 ≈ {int(tot * TOK_LO):,}~{int(tot * TOK_HI):,}"
                  f" 토큰 (입력 {r['input_chars'] / max(tot, 1):.0%})")

    out = Path(__file__).parent / "p0_census.json"
    out.write_text(json.dumps(
        {"method": "hash-verified reassembly (modules.validate 헬퍼 + debate_engine.assemble_*)",
         "token_estimate_band_tok_per_char": [TOK_LO, TOK_HI],
         "runs": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[p0] 작성: {out}")


if __name__ == "__main__":
    main()
