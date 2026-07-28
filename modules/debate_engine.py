"""[패키지 A · 신동범 · 마감 수 20시] 토론 엔진 — DelibTrace 저자 코드(discussion.py) 포팅.

계약: 입력 paths.facts(issue), paths.assignment(issue), config
      → 출력 paths.debate(issue, run)  (스키마 4번, 이벤트 jsonl)
완료 기준: 바닐라(ledger_mode=off) 1회 완주 + validate 통과 + 응답 원문 전량 기록.

저자 코드에서 글자 단위로 계승한 것:
- 프롬프트 원문 (authors_prompts로 원본에서 직접 읽음)
- initial: 관점별 yes/no 2개씩 생성, temp 1.2
- 위치 셔플: seed 고정 후 8개 인덱스를 섞어 토폴로지 위치에 배정
- edges 구성: full(자기 제외 전원) / tree(이진트리 부모·좌·우) / line(좌우 이웃)
- others 포맷: "View {n}: {text}\\n"
- 응답 None이면 공백으로 대체

우리가 추가한 것 (스키마 v0.2 요구):
- 발화마다 이벤트 jsonl 기록 (원문 전량, 요약 금지)
- prompt_hash(sha256) — 재현·재생 검증용 (7/16 파일럿 방식)

[2026-07-22 수 밤 통합 · 민옥] Ledger v0 결합 (docs/INTEGRATION_ledger.md 설계도 구현):
- ledger_mode=v0 이면 라운드 루프 안에서 (A)주입 → 발화 → (C)즉시판정이 한 바퀴로 돈다.
  (A) r>=2: 직전 라운드 소실 팩트를 others 뒤에 재주입(ledger_inject 이벤트 기록)
  (C) 라운드 종료 시 judge.judge_stage(in-memory)로 즉시 채점 → 다음 라운드 주입 근거
- ledger_mode=off 는 기존 동작과 완전 동일(대조군). 정식 judgment 는 두 모드 모두
  사후 오프라인 judge 로 산출한다(같은 잣대). 루프-내 판정은 주입 결정 전용.
- 안전장치(INTEGRATION §5): LLM 호출 상한(max_llm_calls) + 라운드별 체크포인트 저장.
- utterance_fn/judge_vote_fn 파라미터는 테스트 주입용(기본 None = 실호출).
⚠ 동범 확인 대기 2건: judge_stage 시그니처(judge.py), 재주입 블록의 프롬프트 위치(others 뒤).
  → 두 건 모두 7/22 보드에서 동범 승인 완료.

[2026-07-23 · 민옥] 진행 계기판 (관측 전용, 판정·산출물 불변 — judge 계기판의 debate 쪽 절반):
- 발화마다 콘솔 한 줄: `[debate] round 1/4 · 발화 3/8 · 폴백 누적 0`
  (표시는 judge 계기판과 통일해 1-기반 — 파일의 round 필드는 종전대로 0-기반.)
- 폴백 = 무음 공백 발화(llm 5회 재시도 실패 폴백 포함, _is_fallback 참조) 누적 집계.
- 콘솔 출력만 추가한다 — debate.jsonl 이벤트 종류·필드는 한 글자도 바꾸지 않는다
  (파일 기반 progress/run_end 이벤트는 스키마 v0.3 제안 상태라 합의 전 미구현).

[2026-07-28 · 요한 — 작업 이관분(민옥 승인 7/28 보드, 소유권 이전 아님)] 스키마 v0.3 구현:
- 발화마다 `prompt_assembly` 이벤트 방출 — 프롬프트 전문이 아니라 조립 명세(template·
  slots 참조·prompt_hash)를 기록. 검증 계약: 명세대로 재조립한 텍스트의 sha256 ==
  utterance.prompt_hash (validate --deep 가 검사). 조립 로직은 assemble_initial/
  assemble_continue 순수 함수로 추출해 엔진과 검증기가 같은 코드를 쓴다(재조립 드리프트 차단).
- `ledger_inject`에 `injected_text` 원문 전문 추가 — 저장된 사건에서 복원 불가능한
  유일한 프롬프트 텍스트(v0.3 경계 조항 A-1의 첫 사례).
- 기존 이벤트·필드는 한 글자도 바꾸지 않는다(append 호환). LLM 호출 0 증가.

실행: python -m modules.debate_engine --issue issue_esa --run run001 --config configs/sprint_mini.yaml
"""
import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import yaml

from modules import authors_prompts, ledger, llm, paths
from modules import judge as judge_mod

DEBATE_ROUNDS = 3  # 논문 상수. config에서 덮어쓸 수 있게 아래에서 읽는다.

# 이번 통합이 아는 ledger_mode. v1/v2/a1 은 사다리 후속 칸 — 스키마엔 있으나 미구현.
SUPPORTED_LEDGER_MODES = ("off", "v0")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_fallback(resp) -> bool:
    """이 발화가 '무음 공백'인지 — llm 5회 재시도 실패 시의 FALLBACK(공백) 또는 빈 응답.
    판정·산출물에 영향 없는 관측(계기판)용 판별 — 응답 값을 읽기만 한다(judge._is_parse_fail 와 대칭).
    llm.obtain_response 는 성공했어도 빈 텍스트면 FALLBACK 으로 정규화하므로, 여기서는
    '비어 있음' 자체를 센다 — "빈 발화 자체가 관측 대상"(llm.py 원칙)과 동일한 정의."""
    return resp is None or (isinstance(resp, str) and resp.strip() == "")


def build_edges(structure: str, length: int) -> list[list[int]]:
    """토폴로지별 이웃 목록. 저자 discussion.py의 분기를 그대로 옮김."""
    if structure == "full":
        return [[j for j in range(length) if i != j] for i in range(length)]
    if structure == "line":
        edges = []
        for i in range(length):
            if i == 0:
                edges.append([i + 1])
            elif i == length - 1:
                edges.append([i - 1])
            else:
                edges.append([i - 1, i + 1])
        return edges
    if structure == "tree":
        edges = []
        for i in range(length):
            edge = []
            father = (i + 1) // 2 - 1
            left = (i + 1) * 2 - 1
            right = (i + 1) * 2 + 1 - 1
            if i != father and 0 <= father < length:
                edge.append(father)
            if i != left and 0 <= left < length:
                edge.append(left)
            if i != right and 0 <= right < length:
                edge.append(right)
            edges.append(edge)
        return edges
    raise KeyError(f"알 수 없는 토폴로지: {structure} (full|tree|line)")


def assemble_initial(question: str, fact_text: str, answer: str) -> str:
    """discussion_initial 프롬프트 조립(순수). 엔진과 validate --deep 재조립의 단일 소스 —
    치환 순서까지 계약이다(순서가 다르면 hash 가 달라진다)."""
    prompt = authors_prompts.load("discussion_initial")
    inputs = prompt.replace("<===facts===>", fact_text)
    inputs = inputs.replace("<===answer===>", answer)
    inputs = inputs.replace("<===question===>", question)
    return inputs


def assemble_continue(question: str, previous: str, others: str, setting: str) -> str:
    """discussion_continue 프롬프트 조립(순수). assemble_initial 과 동일한 지위."""
    prompt = authors_prompts.load("discussion_continue")
    inputs = prompt.replace("<===others===>", others)
    inputs = inputs.replace("<===previous===>", previous)
    inputs = inputs.replace("<===setting===>", setting)
    inputs = inputs.replace("<===question===>", question)
    return inputs


def initial_utterance(question: str, fact_text: str, answer: str, model: str, temp: float,
                      respond=None):
    """저자 obtain_discussion_initial_each() 계승. respond 는 테스트 주입용."""
    inputs = assemble_initial(question, fact_text, answer)
    fn = respond or llm.obtain_response
    return inputs, fn(inputs, model=model, temperature=temp)


def continue_utterance(question: str, previous: str, others: str, setting: str,
                       model: str, temp: float, respond=None):
    """저자 discussion_continue() 내부 조립 계승. respond 는 테스트 주입용."""
    inputs = assemble_continue(question, previous, others, setting)
    fn = respond or llm.obtain_response
    return inputs, fn(inputs, model=model, temperature=temp)


def run(issue_id: str, run_id: str, config_path: Path, *,
        utterance_fn=None, judge_vote_fn=None) -> Path:
    """utterance_fn(inputs, model=, temperature=) -> str,
    judge_vote_fn(fact, stage_utterances) -> {status, agents_mentioning, reason}.
    둘 다 None(기본)이면 실호출 — 테스트에서만 가짜를 주입한다."""
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model = cfg["debate_model"]
    temp = float(cfg["debate_temperature"])
    rounds = int(cfg.get("rounds", DEBATE_ROUNDS))
    structure = cfg.get("structure", "full")
    ledger_mode = cfg.get("ledger_mode", "off")
    seed = int(cfg["seed"])

    if ledger_mode not in SUPPORTED_LEDGER_MODES:
        raise KeyError(f"미구현 ledger_mode: {ledger_mode} (지원: {SUPPORTED_LEDGER_MODES} — "
                       "v1/v2/a1 은 DESIGN 사다리 후속 칸)")

    facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    assign_doc = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    issue_doc = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))

    question = issue_doc.get("question") or issue_doc["title"]
    facts_list = facts_doc["facts"]
    fact_by_id = {f["fact_id"]: f["text"] for f in facts_list}
    facts_by_id_full = {f["fact_id"]: f for f in facts_list}
    agents = assign_doc["agents"]
    length = len(agents)

    respond = utterance_fn  # None 이면 initial/continue 가 llm.obtain_response 사용

    # --- ledger v0: 루프-내 judge 준비 (INTEGRATION_ledger.md §2C·§4) ----------
    n_votes = int(cfg.get("judge_n_votes", 3))
    if ledger_mode == "v0" and judge_vote_fn is None:
        client = judge_mod._make_client()  # 키 없으면 여기서 즉시 멈춤(시작 전에)
        judge_model = judge_mod._resolve_model(cfg.get("judge_model", "claude-sonnet"))
        judge_vote_fn = lambda fact, utts: judge_mod._online_vote(  # noqa: E731
            client, judge_model, fact, utts)

    # --- 비용 안전장치: 호출 상한 (INTEGRATION_ledger.md §5) -------------------
    expected = length * (rounds + 1)                     # 발화: 초기 + 라운드별
    if ledger_mode == "v0":
        expected += rounds * len(facts_list) * n_votes   # 루프-내 판정 표
    max_calls = int(cfg.get("max_llm_calls", expected))
    n_calls = 0

    prompt_ver = authors_prompts.version_tag()
    settings = authors_prompts.load_settings()
    setting_key = cfg.get("persona", "default")  # 논문 기본값은 default
    setting_text = settings[setting_key]

    out_path = paths.debate(issue_id, run_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    events = []

    def emit(event: str, **fields):
        rec = {"event": event, "run_id": run_id, "ts": now(), **fields}
        events.append(rec)

    def flush():
        """체크포인트: 지금까지의 이벤트를 파일로. 라운드마다 호출(중단 시 유실 최소화)."""
        with out_path.open("w", encoding="utf-8") as f:
            for rec in events:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def spend():
        """LLM 호출 1회 계상. 상한 초과 시 체크포인트 저장 후 중단."""
        nonlocal n_calls
        n_calls += 1
        if n_calls > max_calls:
            flush()
            raise SystemExit(
                f"[ABORT] LLM 호출 상한 초과 (호출 {n_calls} > max_llm_calls={max_calls}) — "
                f"체크포인트 저장됨: {out_path}")

    def counted_vote(fact, utts):
        spend()
        return judge_vote_fn(fact, utts)

    # --- 진행 계기판 (관측 전용, 판정·산출물 불변) ---------------------------
    # 발화 하나 끝날 때마다 콘솔 한 줄 + 폴백(무음 공백) 누적 집계. judge 계기판
    # (`[judge] stage 2/4 · …`)과 형식·1-기반 표시를 통일 — 라이브 뷰어가 양쪽을
    # 같은 규칙으로 소비할 수 있게. 파일(debate.jsonl)에는 아무것도 추가하지 않는다.
    n_fallbacks = 0

    def note_utterance(r: int, i: int, resp) -> None:
        """r = 파일 기준 round(0-기반), i = 이번 라운드 내 발화 순번(0-기반)."""
        nonlocal n_fallbacks
        if _is_fallback(resp):
            n_fallbacks += 1
        print(f"[debate] round {r + 1}/{rounds + 1} · 발화 {i + 1}/{length} · "
              f"폴백 누적 {n_fallbacks}")

    # --- round 0: initial ---------------------------------------------------
    # 저자는 관점별로 yes/no 2개를 만든다. 우리 배분표는 이미 agent마다 stance가 있으므로
    # stance(pro/con) → answer(yes/no)로 바로 대응시킨다.
    current = []
    for agent_idx, ag in enumerate(agents):
        fact_text = ""
        for fid in ag["assigned_fact_ids"]:
            fact_text += f"{fact_by_id[fid]}\n"
        answer = "yes" if ag["stance"] == "pro" else "no"
        spend()
        inputs, resp = initial_utterance(question, fact_text, answer, model, temp,
                                         respond=respond)
        current.append(resp)
        note_utterance(0, agent_idx, resp)
        # v0.3: 발화 입력의 조립 명세 — utterance 와 prompt_hash 로 결합(같은 값).
        emit(
            "prompt_assembly",
            round=0, agent_id=ag["agent_id"],
            template="discussion_initial", prompt_ver=prompt_ver, setting_key=None,
            slots={"assigned_fact_ids": list(ag["assigned_fact_ids"]),
                   "others": [], "previous": None, "inject": None},
            prompt_hash=sha256(inputs),
        )
        emit(
            "utterance",
            ledger_mode=ledger_mode, round=0, agent_id=ag["agent_id"],
            position=None, stance=ag["stance"], perspective=ag["perspective"],
            model=llm.resolve_model(model), temperature=temp,
            prompt_ver=prompt_ver, prompt_hash=sha256(inputs),
            response_text=resp,
        )

    # --- 위치 셔플 ----------------------------------------------------------
    # 저자: random.seed(...) 후 8개 인덱스를 섞어 initial을 재배열한다.
    # 위치 i에 원래 order[i]번 에이전트가 앉는다 — 관점·입장이 토폴로지에 쏠리지 않게.
    order = list(range(length))
    random.Random(seed).shuffle(order)
    seated = [agents[order[i]] for i in range(length)]
    previous = [current[order[i]] for i in range(length)]
    previous = [p if p is not None else " " for p in previous]

    emit("seating", seed=seed, structure=structure,
         order=[agents[order[i]]["agent_id"] for i in range(length)])
    flush()  # 체크포인트: 초기 라운드

    edges = build_edges(structure, length)

    # 루프-내 판정 누적(주입 결정 전용 — 정식 judgment 는 사후 오프라인 judge 몫).
    inloop_judgment = {"stages": []} if ledger_mode == "v0" else None

    # --- rounds 1..N --------------------------------------------------------
    for r in range(1, rounds + 1):
        # (A) 주입: 직전 라운드 소실 팩트를 이번 라운드 프롬프트에 전량 재게시.
        #     r>=2 인 이유: 첫 루프-내 판정이 라운드 1 종료 후에 나오므로.
        inject_block = ""
        if ledger_mode == "v0" and r >= 2:
            inject_ids = ledger.missing_facts(inloop_judgment, r - 1)
            inject_block = ledger.build_injection_block(inject_ids, facts_by_id_full)
            if inject_ids:
                inject_ev = ledger.make_inject_event(run_id, r, inject_ids)
                # v0.3: 재주입 블록 원문 전문 — 저장 사건에서 복원 불가능한 유일한
                # 프롬프트 텍스트라 여기만 전문 저장(경계 조항 A-1). ledger.py 무수정.
                inject_ev["injected_text"] = inject_block
                events.append(inject_ev)

        nxt = []
        for i in range(length):
            others = ""
            for k, j in enumerate(edges[i]):
                others += f"View {k + 1}: {previous[j]}\n"
            # (B) 재주입 블록은 others 뒤에 잇는다 — 저자 프롬프트 슬롯 훼손 최소
            #     (INTEGRATION §3-2 제안, 동범 확인 대기).
            spend()
            inputs, resp = continue_utterance(
                question, previous[i] or "", others + inject_block, setting_text,
                model, temp, respond=respond,
            )
            nxt.append(resp)
            note_utterance(r, i, resp)
            # v0.3: 조립 명세 — others/previous 는 저장된 발화 참조(좌석 j = seated[j]).
            emit(
                "prompt_assembly",
                round=r, agent_id=seated[i]["agent_id"],
                template="discussion_continue", prompt_ver=prompt_ver,
                setting_key=setting_key,
                slots={"assigned_fact_ids": [],
                       "others": [{"round": r - 1, "agent_id": seated[j]["agent_id"]}
                                  for j in edges[i]],
                       "previous": {"round": r - 1, "agent_id": seated[i]["agent_id"]},
                       "inject": {"round": r} if inject_block else None},
                prompt_hash=sha256(inputs),
            )
            emit(
                "utterance",
                ledger_mode=ledger_mode, round=r, agent_id=seated[i]["agent_id"],
                position=i, stance=seated[i]["stance"], perspective=seated[i]["perspective"],
                model=llm.resolve_model(model), temperature=temp,
                prompt_ver=prompt_ver, prompt_hash=sha256(inputs),
                response_text=resp,
            )
        previous = nxt

        # (C) 판정: 이번 라운드를 judge 순수 함수로 즉시 채점 → 다음 라운드 주입 근거.
        #     judge_debate(사후)와 같은 judge_fact 잣대 — judge.judge_stage 참조.
        if ledger_mode == "v0":
            stage_utts = [e for e in events
                          if e.get("event") == "utterance" and e.get("round") == r]
            recs = judge_mod.judge_stage(stage_utts, facts_list,
                                         vote_fn=counted_vote, n_votes=n_votes)
            inloop_judgment["stages"].append({"stage": r, "facts": recs})

        flush()  # 체크포인트: 라운드별

    n_inject = sum(1 for e in events if e.get("event") == "ledger_inject")
    warn = "  ⚠ 폴백(무음 공백) 있음 — 해당 발화 검토" if n_fallbacks else ""
    print(f"[OK] {out_path.name} — 이벤트 {len(events)}건 "
          f"(에이전트 {length} x 라운드 {rounds}+초기, ledger_mode={ledger_mode}, "
          f"ledger_inject {n_inject}건, LLM 호출 {n_calls}/{max_calls}, "
          f"폴백 {n_fallbacks}건){warn}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="토론 엔진 (DelibTrace 포팅)")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--config", required=True, type=Path)
    args = ap.parse_args()
    run(args.issue, args.run, args.config)


if __name__ == "__main__":
    main()
