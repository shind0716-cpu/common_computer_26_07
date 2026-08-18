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

from modules import authors_prompts, ledger, llm, note_slot, our_prompts, paths
from modules import judge as judge_mod

DEBATE_ROUNDS = 3  # 논문 상수. config에서 덮어쓸 수 있게 아래에서 읽는다.

# 이번 통합이 아는 ledger_mode. v1/v2/a1 은 사다리 후속 칸 — 스키마엔 있으나 미구현.
SUPPORTED_LEDGER_MODES = ("off", "v0")

# 기억 축 (설정 사전 v0.1 변경 1 / 스키마 v0.3 §7 — window·memory 는 직교 슬롯).
SUPPORTED_WINDOWS = ("rolling", "cumulative")   # 받은 발화의 창: 직전만 / 누적 전량
SUPPORTED_MEMORY = ("none", "note")             # 개인 수첩 사용 여부
SUPPORTED_NOTE_CALLS = ("utterance", "dedicated")  # 수첩 갱신 호출 방식 (§5)
# 배정 팩트 재주입 (2026-08-14 · 요한). 협력 조건 전용 축이다.
#   always      = 매 라운드 원문 재주입 (종전 동작 · 기본값이라 옛 run 은 무변)
#   round0_only = 라운드 0 에만 제시. 이후엔 자기 직전 발언에 적혀야 산다
#                 = 저자 템플릿(discussion_continue)의 구조. 설정 사전 v0.1 변경 1 이
#                   직전만 좌표를 "논문 세팅·재현 트랙 전용"이라 규정한 것을 집행하는 칸.
SUPPORTED_FACTS_REINJECT = ("always", "round0_only")


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


def assemble_coop_initial(question: str, body: str, fact_text: str) -> str:
    """coop_initial 조립(순수) — 본실험 협력 템플릿(our_prompts, 우리 소유).
    discussion_* 과 같은 지위: 치환 순서까지 계약(validate --deep 재조립의 단일 소스)."""
    t = our_prompts.load("coop_initial")
    t = t.replace("{{question}}", question)
    t = t.replace("{{body}}", body)
    t = t.replace("{{my_facts}}", fact_text)
    return t


def assemble_coop_continue(question: str, body: str, fact_text: str,
                           previous: str, incoming: str,
                           *, template: str = "coop_continue") -> str:
    """coop_continue 조립(순수). incoming = 이웃 발화(+재주입 블록이 있으면 그 뒤에).

    template 인자(2026-08-14): facts_reinject=round0_only 면 `coop_continue_nofacts`.
    그 판에는 `{{my_facts}}` 슬롯이 없어 fact_text 치환이 무효타가 된다 — 호출자는
    빈 문자열을 넘긴다. 조립기를 하나로 두는 이유는 note 쌍과 같다(validate 가
    template 이름으로 같은 함수를 다시 불러 재조립한다)."""
    t = our_prompts.load(template)
    t = t.replace("{{question}}", question)
    t = t.replace("{{body}}", body)
    t = t.replace("{{my_facts}}", fact_text)
    t = t.replace("{{previous}}", previous)
    t = t.replace("{{incoming}}", incoming)
    return t


def assemble_coop_continue_note(question: str, body: str, note: str, incoming: str,
                                *, template: str = "coop_continue_note") -> str:
    """수첩 조건의 발화 프롬프트 조립(순수).

    coop_continue 와 슬롯이 다르다 — `my_facts`·`previous` 가 **없다**:
      · my_facts 없음 = B판(스키마 v0.3 §7 좌표, 설정 사전 v0.1 변경 3). 배정 팩트는
        라운드 0에 1회만 제시하고, 이후엔 수첩에 적어야 생존한다. 자기 브리핑도 기억
        압축의 대상이라는 것이 이 조건의 요지다.
      · previous 없음 = 자기 직전 발언도 기억이다. 수첩에 안 적었으면 자기 말도
        사라진다. (엔진이 previous 를 공짜로 되돌려주면 "수첩만 남는다"는 조건이
        거짓이 된다 — 수첩 밖 통로가 하나 열린 셈.)

    template 인자: note_call=utterance 면 coop_continue_note({"say","note"} 요구),
    dedicated 면 coop_continue_note_say(발화만 요구). 슬롯 구성은 동일하므로 조립
    함수를 하나로 두고 파일만 갈아 끼운다 — validate --deep 이 template 이름으로
    같은 함수를 다시 호출해 재조립한다."""
    t = our_prompts.load(template)
    t = t.replace("{{question}}", question)
    t = t.replace("{{body}}", body)
    t = t.replace("{{note}}", note)
    t = t.replace("{{incoming}}", incoming)
    return t


def assemble_coop_note_update(question: str, note: str, my_say: str, incoming: str,
                              note_budget: int) -> str:
    """별도 호출(note_call=dedicated) 의 수첩 갱신 프롬프트 조립(순수).

    스키마 v0.3 §5: 별도 호출은 독립 LLM 호출이므로 **그 호출의 입력도 prompt_assembly
    로 기록**되어야 한다("입력이 기록되지 않은 LLM 호출"이 v0.3이 없애려던 구멍).
    그래서 이 조립도 발화 조립과 같은 지위의 순수 함수이고, template 등록제(A-3)에
    coop_note_update 가 등재되어 있다."""
    t = our_prompts.load("coop_note_update")
    t = t.replace("{{question}}", question)
    t = t.replace("{{note}}", note)
    t = t.replace("{{my_say}}", my_say)
    t = t.replace("{{incoming}}", incoming)
    t = t.replace("{{note_budget}}", str(note_budget))
    return t


def assemble_coop_final(question: str, body: str, final_context: str) -> str:
    """최종 폴링(coop_final) 조립(순수) — 벌거벗은 판단 {"recommend"} 한 필드.

    final_context 는 조건에 따라 다른 것이 들어온다(수첩 조건이면 수첩, 아니면 마지막
    라운드 발화들). 어느 것이 들어갔는지는 prompt_assembly.slots 가 기록한다."""
    t = our_prompts.load("coop_final")
    t = t.replace("{{question}}", question)
    t = t.replace("{{body}}", body)
    t = t.replace("{{final_context}}", final_context)
    return t


def _reasoning_bound(reasoning: str):
    """추론 좌표를 묶은 실호출 함수를 만든다 (2026-07-30 · 민옥).

    왜 llm.obtain_response 를 직접 안 쓰는가: 주입된 가짜(테스트의 utterance_fn)는
    시그니처가 `(inputs, model=, temperature=)` 이므로 reasoning 을 넘기면 깨진다.
    실호출 경로에만 좌표를 싣고 주입 경로는 종전 계약 그대로 둔다."""
    def _call(inputs, model=None, temperature=None):
        return llm.obtain_response(inputs, model=model, temperature=temperature,
                                   reasoning=reasoning)
    return _call


def initial_utterance(question: str, fact_text: str, answer: str, model: str, temp: float,
                      respond=None, reasoning: str = "default"):
    """저자 obtain_discussion_initial_each() 계승. respond 는 테스트 주입용."""
    inputs = assemble_initial(question, fact_text, answer)
    fn = respond or _reasoning_bound(reasoning)
    return inputs, fn(inputs, model=model, temperature=temp)


def continue_utterance(question: str, previous: str, others: str, setting: str,
                       model: str, temp: float, respond=None, reasoning: str = "default"):
    """저자 discussion_continue() 내부 조립 계승. respond 는 테스트 주입용."""
    inputs = assemble_continue(question, previous, others, setting)
    fn = respond or _reasoning_bound(reasoning)
    return inputs, fn(inputs, model=model, temperature=temp)


def run(issue_id: str, run_id: str, config_path: Path, *,
        utterance_fn=None, judge_vote_fn=None) -> Path:
    """utterance_fn(inputs, model=, temperature=) -> str,
    judge_vote_fn(fact, stage_utterances) -> {status, agents_mentioning, reason}.
    둘 다 None(기본)이면 실호출 — 테스트에서만 가짜를 주입한다."""
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model = cfg["debate_model"]
    temp = float(cfg["debate_temperature"])
    # ⑨ 추론 모드 (2026-07-30). 기본 "default" = 파라미터 미전송 = 종전 동작이므로
    # 이 키가 없는 옛 config 도 그대로 돈다. 값의 의미는 llm.REASONING_MODES 참조.
    reasoning = str(cfg.get("reasoning", "default"))
    rounds = int(cfg.get("rounds", DEBATE_ROUNDS))
    structure = cfg.get("structure", "full")
    ledger_mode = cfg.get("ledger_mode", "off")
    seed = int(cfg["seed"])

    # --- 기억 축 3값 (설정 사전 v0.1 변경 1) ---------------------------------
    # window(받은 발화의 창) 와 memory(수첩) 는 **직교 슬롯**이다(스키마 v0.3 §7).
    # 실험 메뉴로 파는 세 점은 그 곱집합의 세 좌표일 뿐, 계약은 두 칸을 따로 둔다:
    #   전체 기억 = window:cumulative + memory:none   (넘치기 전의 실전 시스템)
    #   요약 기억 = window:rolling    + memory:note   (개인 수첩)
    #   직전만   = window:rolling    + memory:none   (논문 세팅 · 재현 트랙 전용)
    window = cfg.get("window", "rolling")
    memory = cfg.get("memory", "none")
    note_budget = int(cfg.get("note_budget", 500))
    note_call = cfg.get("note_call", "utterance")
    facts_reinject = cfg.get("facts_reinject", "always")

    # 최종 폴링(coop_final): 벌거벗은 판단 {"recommend"} 한 필드. 코어 5종의 채점
    # 원자료 — LLM judge 불사용이므로 이 폴링 결과가 곧 정답 여부다(설정 사전 §4).
    final_poll = bool(cfg.get("final_poll", False))

    if ledger_mode not in SUPPORTED_LEDGER_MODES:
        raise KeyError(f"미구현 ledger_mode: {ledger_mode} (지원: {SUPPORTED_LEDGER_MODES} — "
                       "v1/v2/a1 은 DESIGN 사다리 후속 칸)")
    # 가드: 미지 값을 조용히 기본값으로 흘리지 않는다(stance 가드와 같은 이유 —
    # 오타 하나가 "다른 조건이 돌았는데 로그엔 맞다고 적힌" run 을 만든다).
    if window not in SUPPORTED_WINDOWS:
        raise KeyError(f"미지원 window: {window} (지원: {SUPPORTED_WINDOWS})")
    if memory not in SUPPORTED_MEMORY:
        raise KeyError(f"미지원 memory: {memory} (지원: {SUPPORTED_MEMORY})")
    if note_call not in SUPPORTED_NOTE_CALLS:
        raise KeyError(f"미지원 note_call: {note_call} (지원: {SUPPORTED_NOTE_CALLS})")
    if facts_reinject not in SUPPORTED_FACTS_REINJECT:
        raise KeyError(f"미지원 facts_reinject: {facts_reinject} "
                       f"(지원: {SUPPORTED_FACTS_REINJECT})")
    use_note = memory == "note"
    # 협력 조건 발화 템플릿 — 팩트 재주입 축이 여기서 파일을 고른다(note 쌍과 같은 방식).
    _coop_continue_template = ("coop_continue" if facts_reinject == "always"
                               else "coop_continue_nofacts")

    facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    assign_doc = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    issue_doc = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))

    question = issue_doc.get("question") or issue_doc["title"]
    facts_list = facts_doc["facts"]
    fact_by_id = {f["fact_id"]: f["text"] for f in facts_list}
    facts_by_id_full = {f["fact_id"]: f for f in facts_list}
    agents = assign_doc["agents"]
    length = len(agents)

    # 입장 가드 (설정 사전 §2 입장 3값): 미지 값을 조용히 변환하지 않고 즉사.
    # (종전 코드는 stance!="pro"를 전부 "no"로 변환 — "none"이 소리 없이 반대파가 되는
    #  함정이 있었다. 죽지 않는 파이프라인은 조용히 썩는다.)
    _ALLOWED_STANCES = {"pro", "con", "none"}
    _stances = [ag["stance"] for ag in agents]
    _unknown = set(_stances) - _ALLOWED_STANCES
    if _unknown:
        raise KeyError(f"미지원 stance {sorted(_unknown)} — 허용: pro|con|none")
    coop = "none" in _stances
    if coop and set(_stances) != {"none"}:
        raise KeyError("stance 혼합(none + pro/con)은 미정의 조건 — 전원 none 또는 전원 pro/con")

    # 수첩·누적창은 우리 소유 협력 템플릿에만 있는 슬롯이다. 저자 템플릿
    # (discussion_*)은 글자 단위 계승·무수정이 재현 트랙의 증거물이라 슬롯을 더할 수
    # 없다 — 조용히 무시하고 도는 대신 여기서 즉사시킨다.
    if not coop:
        if use_note:
            raise KeyError("memory=note 는 협력(무입장) 조건 전용 — 저자 템플릿엔 수첩 슬롯이 없다")
        if window != "rolling":
            raise KeyError(f"window={window} 는 협력 조건 전용 — 재현 트랙은 rolling 고정")
        if facts_reinject != "always":
            raise KeyError("facts_reinject 는 협력 조건 전용 — 저자 템플릿엔 팩트 슬롯이 "
                           "없어 이미 round0_only 와 같다")
    elif use_note and facts_reinject != "always":
        # 수첩 조건은 설정 사전 변경 3(B판)에서 이미 라운드 0 1회로 확정돼 있다.
        # 같은 것을 두 칸으로 적으면 로그가 조건을 두 번 말하게 된다.
        raise KeyError("memory=note 는 이미 배정 팩트를 라운드 0 에만 준다(B판) — "
                       "facts_reinject 를 함께 지정하지 마라")

    respond = utterance_fn  # None 이면 initial/continue 가 llm.obtain_response 사용

    # --- 키 관문 (2026-07-30 · 민옥) -----------------------------------------
    # 실호출 경로일 때만 검사한다(테스트는 utterance_fn 을 주입하므로 키 불필요).
    # 왜 시작 전인가: obtain_response 는 어떤 실패도 공백으로 폴백하므로(저자 계승)
    # 키가 죽어 있으면 전 발화가 빈 로그가 조용히 완주한다. 실측 사고 — .env 의
    # ANTHROPIC_API_KEY 가 10자 자리표시자였고 401 이 났는데, 5회 백오프 뒤 공백
    # 폴백으로 넘어가 로그만 보면 성공처럼 보였다(7/30).
    llm_meta = None
    if respond is None:
        # 온도까지 함께 검사한다 — 범위 밖 온도는 400 이고, 400 은 재시도해도 400 이라
        # 공백 폴백으로 넘어가 빈 발화 로그가 완주한다(2026-07-30 · 민옥 온도 관문).
        llm_meta = llm.preflight(model, temperature=temp, reasoning=reasoning)
        print(f"[llm] {llm_meta['provider']} · {llm_meta['model_id']} "
              f"(키: {llm_meta['key_env']})")

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
    if use_note:
        # 라운드 0 첫 수첩: note_call 과 무관하게 항상 별도 호출 1콜/에이전트.
        expected += length
        if note_call == "dedicated":
            # 라운드 1..N-1 끝의 갱신(마지막 라운드는 다음 라운드가 없어 갱신 불필요).
            expected += length * max(0, rounds - 1)
    if final_poll:
        expected += length                               # 최종 폴링 1인 1콜
    max_calls = int(cfg.get("max_llm_calls", expected))
    n_calls = 0

    if coop:
        # 협력 조건은 우리 템플릿만 사용 — 저자 저장소(DelibTrace-main) 불필요.
        prompt_ver = our_prompts.version_tag()
        setting_key = None
        setting_text = None
    else:
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

    # 이 run 이 시작될 때 이미 쌓여 있던 편차는 남의 것이다(LAST_DEVIATIONS 는
    # 프로세스 전역). 여기서부터 늘어난 것만 이 run 의 편차로 센다.
    _dev_base = len(llm.LAST_DEVIATIONS)

    def flush():
        """체크포인트: 지금까지의 이벤트를 파일로. 라운드마다 호출(중단 시 유실 최소화).

        쓰기 전에 run_meta 의 편차 칸을 갱신한다 (2026-07-30 · 민옥).
        왜 여기인가: 편차는 **첫 호출을 해봐야** 드러난다(예: 구형 모델이
        reasoning_effort 를 거부해 제거됨). run_meta 는 로그 첫 줄이라 실행 전에
        나가므로, 그대로 두면 `reasoning: on` 이라 적힌 로그가 실제로는 추론 없이
        돌았을 수 있다 — **기록과 실제가 갈리는** 자리다. flush 가 파일을 통째로
        다시 쓰므로 여기서 채우면 체크포인트에도 그 시점까지의 편차가 남는다."""
        if events and events[0].get("event") == "run_meta":
            events[0]["settings"]["deviations"] = list(llm.LAST_DEVIATIONS[_dev_base:])
        with out_path.open("w", encoding="utf-8") as f:
            for rec in events:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def guarded(fn):
        """LLM 호출 가드: 절단 즉사(A안) 직전에 체크포인트를 남긴다 (요한 PR#33 리뷰 반영).

        LLMTruncated 는 run 을 그 자리에서 끝내는 게 맞지만(절단 논쟁 A안), flush 없이
        죽으면 방금 LAST_DEVIATIONS 에 적힌 절단 기록이 프로세스 메모리와 함께 증발한다 —
        "절단 횟수는 세야 한다"(요한 7/31)가 제어 흐름에서 달성되지 않는 구멍이었다.
        여기서 잡아 flush() 로 run_meta.settings.deviations 까지 내려앉힌 뒤 **같은
        예외를 다시 올린다.** 잡는 것은 절단뿐 — 다른 실패의 동작은 한 글자도 안 바뀐다.
        발화·수첩·폴링·루프 내 채점이 전부 이 가드를 거치도록 각 호출 지점에서 감싼다."""
        def _wrapped(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except llm.LLMTruncated:
                flush()
                raise
        return _wrapped

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
        return guarded(judge_vote_fn)(fact, utts)   # 루프 내 채점의 절단도 같은 가드로

    # --- run_meta: 산출물이 자기 조건을 안다 (스키마 v0.3 §4‴, 로그 첫 줄) --------
    # 조건 정의는 configs/*.yaml 에 있는데 종전 로그는 ledger_mode 한 칸만 실어서,
    # "이 run 이 어떤 조건이었나"가 run_id 문자열과 사람 기억에만 있었다. 설정 사전
    # (docs/proposals/EXPERIMENT_SETTINGS_v0.md) 8축 좌표를 실제 실행값으로 적는다.
    # config_ref.sha256 = 조건 파일의 지문 — 나중에 config 가 바뀌면 옛 run 과 새 run 이
    # 같은 조건이 아님이 드러난다(prompt_hash 가 프롬프트에 한 것과 같은 수법).
    emit(
        "run_meta",
        issue_id=issue_id,
        condition=cfg.get("condition"),          # 사람용 슬러그. 없으면 null
        config_ref={"name": config_path.name,
                    "sha256": sha256(config_path.read_text(encoding="utf-8"))},
        settings={
            # 설정 사전 8축 — 미구현 축은 엔진의 현행 동작을 그대로 적는다
            "window": window,                    # ① 받는 말 범위 (rolling|cumulative)
            "memory": memory,                    # ② 기억 (none|note)
            # 수첩 부속 좌표 — 수첩이 꺼진 run 에도 적는다(값이 없는 것과 기본값인
            # 것을 구별해야 나중에 250/1000 비교가 조건 이름 밖으로 안 밀린다, §7).
            "note_budget": note_budget if use_note else None,
            "note_call": note_call if use_note else None,
            "note_parse_ver": (note_slot.NOTE_PARSE_VER
                               if use_note and note_call == "utterance" else None),
            # 배정 팩트 재주입 (2026-08-14). 수첩 조건은 B판이라 값이 고정이므로
            # 협력·비수첩 조건에서만 의미가 있다 — 그 밖에서는 null 로 적는다.
            "facts_reinject": (facts_reinject if coop and not use_note else None),
            "final_poll": final_poll,
            "rounds": rounds,                    # ③
            "structure": structure,              # ④ 연결 모양
            "stance": "none" if coop else "pro_con",   # ⑤ 입장
            "persona": setting_key,              # ⑥ 성격 (협력 조건은 None)
            "overlap_k": assign_doc.get("overlap_k"),          # ⑦ 정보 나누기
            "assignment_mode": assign_doc.get("created_by"),   # ⑦ 배분 방식
            "ledger_mode": ledger_mode,          # ⑧ 장부
            # ⑨ 추론 모드 (2026-07-30 신설). 종전엔 공급자마다 사고량이 다른데
            # 그 사실이 산출물 어디에도 없었다 — "지정 안 함(default)"도 하나의 상태로
            # 명시해 기록한다. 요청한 좌표와 **실제로 전송된 것**이 갈릴 수 있으므로
            # (구형 모델이 파라미터를 거부하면 제거하고 재시도한다) 그 차이는 아래
            # settings.deviations 에 flush 시점마다 채워진다.
            "reasoning": reasoning,
            "deviations": [],                    # flush() 가 실행 중에 채운다
            # 부수 — 조건은 아니지만 재현에 필요
            "seed": seed, "agents": length,
            "debate_model": model, "debate_temperature": temp,
            # 공급자·실제 모델 ID 를 적는다 — 별칭만 남기면 나중에 .env 의
            # OPENAI_MODEL 이 바뀌었을 때 옛 run 과 새 run 이 같은 모델이었는지
            # 알 수 없다(config_ref 가 config 에 한 것과 같은 수법).
            "provider": (llm_meta or {}).get("provider"),
            "debate_model_id": (llm_meta or {}).get("model_id"),
        },
    )

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
    body = issue_doc.get("body", "")
    for agent_idx, ag in enumerate(agents):
        fact_text = ""
        for fid in ag["assigned_fact_ids"]:
            fact_text += f"{fact_by_id[fid]}\n"
        spend()
        if coop:
            inputs = assemble_coop_initial(question, body, fact_text)
            _fn = guarded(respond or _reasoning_bound(reasoning))
            resp = _fn(inputs, model=model, temperature=temp)
        else:
            answer = "yes" if ag["stance"] == "pro" else "no"
            inputs, resp = initial_utterance(
                question, fact_text, answer, model, temp,
                # 저자 트랙도 절단 가드를 거친다 — 헬퍼 내부의 폴백 대신 가드된 호출자를 주입
                respond=guarded(respond or _reasoning_bound(reasoning)), reasoning=reasoning)
        current.append(resp)
        note_utterance(0, agent_idx, resp)
        # v0.3: 발화 입력의 조립 명세 — utterance 와 prompt_hash 로 결합(같은 값).
        emit(
            "prompt_assembly",
            round=0, agent_id=ag["agent_id"],
            template="coop_initial" if coop else "discussion_initial",
            prompt_ver=prompt_ver, setting_key=None,
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

    # 누적 창(window=cumulative)의 원자료: history[r] = 라운드 r 발화 리스트(좌석 순).
    # 라운드 0은 셔플 후 좌석 순으로 재배열된 initial(= previous 초기값).
    history = {0: list(previous)}

    # --- 수첩 상태 (스키마 v0.3 §2: "사건이 1급, 상태는 뷰") -------------------
    # notes[i] = 좌석 i 에이전트의 현재 수첩 텍스트(없으면 None).
    # note_round[i] = 그 텍스트가 어느 라운드 갱신에서 나왔나 → prompt_assembly.note
    #                 .source_round 로 그대로 적는다. "r-1 로 계산"하지 않는 이유는
    #                 계약 §3에 있다: 갱신이 실패·생략된 라운드가 생기면 r-1 규칙이
    #                 즉시 깨지고, 계산 규칙을 계약에 넣으면 예외마다 계약을 고쳐야 한다.
    notes = [None] * length
    note_round = [None] * length
    n_note_updates = 0
    n_note_parse_fail = 0
    n_note_truncated = 0

    def emit_note_update(r_: int, seat: int, note_text: str, source: str) -> None:
        """note_update 이벤트 방출 + 상태 갱신. 예산 절단은 방출 전에 적용한다
        (저장되는 것이 실제로 다음 라운드에 들어간 텍스트여야 재조립이 성립한다)."""
        nonlocal n_note_updates, n_note_truncated
        text, truncated = note_slot.apply_budget(note_text, note_budget)
        if truncated:
            n_note_truncated += 1
        emit("note_update", agent_id=seated[seat]["agent_id"], round=r_,
             note_text=text,           # 원문 전량(예산 내). 요약·재절단 금지 — A-1
             origin="model",           # 사람이 고쳐 넣은 개입은 intervention (§6)
             source=source)            # "utterance" | "dedicated" (§5)
        notes[seat] = text
        note_round[seat] = r_
        n_note_updates += 1

    # --- 라운드 0 수첩 (수첩 조건 전용) --------------------------------------
    # 라운드 0의 배정 팩트 브리핑은 **한 번만** 제시된다(B판). 라운드 1의 입력에
    # 수첩이 있어야 하므로 라운드 0 끝에 첫 갱신이 일어난다.
    # 왜 라운드 0은 얹기 방식에서도 별도 호출을 쓰는가: 초기 프롬프트(coop_initial)는
    # 저자 대응물 없는 우리 템플릿이지만 배정 팩트 브리핑 발화만 요구하고 note 필드를
    # 요구하지 않는다. 여기에 note 를 얹으면 "첫 발화"의 프롬프트가 조건마다 달라져
    # ③↔④ 비교의 라운드 0이 어긋난다. 라운드 0 발화는 두 조건에서 **글자 단위로
    # 동일**해야 하므로, 첫 수첩만 별도 호출로 만든다(+에이전트수 1회, run 당 1회).
    if use_note:
        for i in range(length):
            orig_idx = order[i]          # 좌석 i 에 앉은 에이전트의 initial 응답 위치
            raw = current[orig_idx]
            spend()
            nu_inputs = assemble_coop_note_update(question, "", raw or "", "", note_budget)
            _fn = guarded(respond or _reasoning_bound(reasoning))
            nu_resp = _fn(nu_inputs, model=model, temperature=temp)
            note_text = note_slot.parse_note_only(nu_resp)
            emit("prompt_assembly", round=0, agent_id=seated[i]["agent_id"],
                 template="coop_note_update", prompt_ver=prompt_ver,
                 setting_key=None,
                 slots={"assigned_fact_ids": [], "others": [], "previous": None,
                        "inject": None, "note": None,
                        "my_say": {"round": 0, "agent_id": seated[i]["agent_id"]},
                        "note_budget": note_budget},
                 prompt_hash=sha256(nu_inputs))
            if note_text is None:
                n_note_parse_fail += 1   # 미갱신 — 이벤트를 만들지 않는다(§2)
            else:
                # source 는 이 호출이 실제로 어떻게 생성됐는지를 적는다 — 라운드 0은
                # note_call 설정과 무관하게 항상 별도 호출이므로 "dedicated".
                emit_note_update(0, i, note_text, "dedicated")
        flush()

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
        round_notes = []   # 이번 라운드 끝에 반영할 (좌석, 수첩텍스트) — 동시 갱신용
        for i in range(length):
            # (B-1) incoming 조립 — window 축이 여기서 갈린다.
            #   rolling    : 직전 라운드 이웃 발화만 (논문 세팅)
            #   cumulative : 라운드 1..r-1 의 이웃 발화 전부 (회의록 전체 재독)
            # 누적은 "안 깎이는 기준선"이다 — ③ 온전 대화의 정정된 좌표(설정 사전 v0.1
            # 변경 2). 라운드 표시를 넣는 이유: 같은 참석자의 여러 라운드 발언이 한
            # 프롬프트에 들어오므로 순서·시점 없이 붙이면 모델이 최신·과거를 구별할 수
            # 없다. 표시 형식도 계약이다(validate --deep 이 글자 단위로 재조립한다).
            others = ""
            if window == "cumulative":
                # 라운드 0..r-1 의 이웃 발화를 전부, 라운드 순으로 붙인다. 마지막
                # 블록(r-1)이 "방금 들은 말"이고 그 앞이 회의록이다.
                # 왜 라운드 0을 포함하나: 초기 브리핑이 이 실험의 정보 원천이다.
                # 누적이 그것을 떨어뜨리면 "안 깎이는 기준선"이 아니게 된다.
                for past_r in range(0, r - 1):
                    for k, j in enumerate(edges[i]):
                        others += f"[라운드 {past_r}] 참석자{k + 1}: {history[past_r][j]}\n"
                for k, j in enumerate(edges[i]):
                    others += f"[라운드 {r - 1} · 방금] 참석자{k + 1}: {previous[j]}\n"
            else:
                for k, j in enumerate(edges[i]):
                    if coop:
                        others += f"참석자{k + 1}: {previous[j]}\n"
                    else:
                        others += f"View {k + 1}: {previous[j]}\n"
            # (B-2) 재주입 블록은 others 뒤에 잇는다 — 저자 프롬프트 슬롯 훼손 최소
            #     (INTEGRATION §3-2 제안, 동범 확인 대기).
            spend()
            _fn = guarded(respond or _reasoning_bound(reasoning))
            if use_note:
                # 수첩 조건: 배정 팩트·직전 발언이 프롬프트에 없다. 남는 것은 수첩뿐.
                # 수첩이 None(라운드 0 파싱 실패)이면 빈 문자열을 넣되 슬롯은 null 로
                # 기록한다 — 계약 §3의 "null 이면 슬롯 블록 자체를 생략"과 구별하기
                # 위해, 우리 템플릿은 {{note}} 치환을 항상 수행하고 슬롯 참조만 null 로
                # 둔다(재조립도 같은 규칙을 쓰므로 hash 는 일치한다).
                tmpl = ("coop_continue_note" if note_call == "utterance"
                        else "coop_continue_note_say")
                inputs = assemble_coop_continue_note(
                    question, body, notes[i] or "", others + inject_block, template=tmpl)
                raw = _fn(inputs, model=model, temperature=temp)
                if note_call == "utterance":
                    resp, note_text = note_slot.parse_say_and_note(raw)
                    if note_text is None:
                        n_note_parse_fail += 1
                    elif r < rounds:      # 마지막 라운드 갱신은 쓰이지 않으므로 생략
                        round_notes.append((i, note_text, "utterance"))
                else:
                    resp = raw
            elif coop:
                # 협력 조건 기본(facts_reinject=always): 배정 팩트를 매 라운드 유지한다.
                # round0_only 면 저자 템플릿과 같은 구조가 된다 — 팩트가 라운드 0 이후
                # 안 들어오므로 자기 직전 발언에 적힌 것만 산다(논문 정합 좌표).
                _ft = ""
                if facts_reinject == "always":
                    for _fid in seated[i]["assigned_fact_ids"]:
                        _ft += f"{fact_by_id[_fid]}\n"
                inputs = assemble_coop_continue(question, body, _ft,
                                                previous[i] or "", others + inject_block,
                                                template=_coop_continue_template)
                resp = _fn(inputs, model=model, temperature=temp)
            else:
                inputs, resp = continue_utterance(
                    question, previous[i] or "", others + inject_block, setting_text,
                    model, temp, reasoning=reasoning,
                    # 저자 트랙도 절단 가드를 거친다 (위 initial 과 동일)
                    respond=guarded(respond or _reasoning_bound(reasoning)),
                )
            nxt.append(resp)
            note_utterance(r, i, resp)
            # v0.3: 조립 명세 — others/previous 는 저장된 발화 참조(좌석 j = seated[j]).
            # others 참조 목록이 window 축을 그대로 반영한다 — 누적이면 과거 라운드가
            # 전부 목록에 들어오고, 재조립은 이 목록 순서대로 붙인다(순서도 계약).
            if window == "cumulative":
                others_refs = [{"round": pr, "agent_id": seated[j]["agent_id"]}
                               for pr in range(0, r - 1) for j in edges[i]]
                others_refs += [{"round": r - 1, "agent_id": seated[j]["agent_id"]}
                                for j in edges[i]]
            else:
                others_refs = [{"round": r - 1, "agent_id": seated[j]["agent_id"]}
                               for j in edges[i]]
            if use_note:
                _tmpl_name = ("coop_continue_note" if note_call == "utterance"
                              else "coop_continue_note_say")
            elif coop:
                _tmpl_name = _coop_continue_template
            else:
                _tmpl_name = "discussion_continue"
            emit(
                "prompt_assembly",
                round=r, agent_id=seated[i]["agent_id"],
                template=_tmpl_name,
                prompt_ver=prompt_ver,
                setting_key=setting_key,
                slots={"assigned_fact_ids": (list(seated[i]["assigned_fact_ids"])
                                             if coop and not use_note
                                             and facts_reinject == "always" else []),
                       "others": others_refs,
                       # 수첩 조건은 previous 슬롯이 없다(자기 직전 발언도 기억이다).
                       "previous": (None if use_note else
                                    {"round": r - 1, "agent_id": seated[i]["agent_id"]}),
                       "inject": {"round": r} if inject_block else None,
                       # 계약 §3: source_round 는 계산하지 않고 실제 사용 판본을 적는다.
                       "note": ({"agent_id": seated[i]["agent_id"],
                                 "source_round": note_round[i]}
                                if use_note and note_round[i] is not None else None),
                       # window 를 슬롯에 명시하는 이유: 참조 목록만으로는 라운드 1에서
                       # 누적과 직전만을 구별할 수 없다(둘 다 라운드 0 하나뿐). 재조립이
                       # 추론에 의존하면 조건 경계에서 조용히 틀린다 — 계약은 추론하지
                       # 않고 읽는다. (A-3 재조립 규칙의 일부로 등록)
                       "window": window},
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
        history[r] = list(nxt)   # 누적 창의 원자료 (좌석 순서 그대로)

        # (C-note) 수첩 갱신 — 발화 루프가 **끝난 뒤** 일괄 반영한다.
        # 왜 루프 안이 아닌가: 루프 안에서 notes[i] 를 바로 갱신하면 같은 라운드
        # 뒷순번 에이전트가 앞순번의 새 수첩을 보게 되어(자기 것만 봐야 하는데)
        # 라운드 경계가 무너진다. 수첩은 라운드 단위로 동시에 넘어간다.
        if use_note and note_call == "utterance":
            for seat, note_text, src in round_notes:
                emit_note_update(r, seat, note_text, src)
        elif use_note and note_call == "dedicated" and r < rounds:
            # 별도 호출: 발화와 분리된 선별. 이 호출의 입력도 prompt_assembly 로
            # 기록한다(계약 §5 — "입력이 기록되지 않은 LLM 호출"을 만들지 않는다).
            for i in range(length):
                inc = ""
                for k, j in enumerate(edges[i]):
                    inc += f"참석자{k + 1}: {nxt[j]}\n"
                spend()
                nu_inputs = assemble_coop_note_update(
                    question, notes[i] or "", nxt[i] or "", inc, note_budget)
                _fn2 = guarded(respond or _reasoning_bound(reasoning))
                nu_resp = _fn2(nu_inputs, model=model, temperature=temp)
                emit("prompt_assembly", round=r, agent_id=seated[i]["agent_id"],
                     template="coop_note_update", prompt_ver=prompt_ver,
                     setting_key=None,
                     slots={"assigned_fact_ids": [], "previous": None, "inject": None,
                            "others": [{"round": r, "agent_id": seated[j]["agent_id"]}
                                       for j in edges[i]],
                            "my_say": {"round": r, "agent_id": seated[i]["agent_id"]},
                            "note": ({"agent_id": seated[i]["agent_id"],
                                      "source_round": note_round[i]}
                                     if note_round[i] is not None else None),
                            "note_budget": note_budget},
                     prompt_hash=sha256(nu_inputs))
                note_text = note_slot.parse_note_only(nu_resp)
                if note_text is None:
                    n_note_parse_fail += 1
                else:
                    emit_note_update(r, i, note_text, "dedicated")

        # (C) 판정: 이번 라운드를 judge 순수 함수로 즉시 채점 → 다음 라운드 주입 근거.
        #     judge_debate(사후)와 같은 judge_fact 잣대 — judge.judge_stage 참조.
        if ledger_mode == "v0":
            stage_utts = [e for e in events
                          if e.get("event") == "utterance" and e.get("round") == r]
            recs = judge_mod.judge_stage(stage_utts, facts_list,
                                         vote_fn=counted_vote, n_votes=n_votes)
            inloop_judgment["stages"].append({"stage": r, "facts": recs})

        flush()  # 체크포인트: 라운드별

    # --- 최종 폴링 (final_poll) ---------------------------------------------
    # 벌거벗은 판단: {"recommend"} 한 필드. 회고·이유 필드 없음 — 결과가 자명한
    # 측정을 배제한다(설정 사전 v0.1 변경 6, 민옥 7/29).
    # 조건별로 final_context 에 들어가는 것이 다르고, 그 차이가 곧 조건의 정의다:
    #   수첩 조건 : 자기 수첩만 — 수첩에서 떨어진 것은 그 에이전트에게 진짜로 없다
    #   그 외     : 마지막 라운드 발언들(자기 것 + 이웃) — 대화가 그대로 남아 있다
    # 이 폴링은 개입 창(수첩을 사람이 고쳐 넣고 1콜 재실행)의 재실행 지점이기도 하다.
    if final_poll:
        for i in range(length):
            if use_note:
                final_context = f"[당신의 수첩]\n{notes[i] or ''}\n"
                fslots = {"note": ({"agent_id": seated[i]["agent_id"],
                                    "source_round": note_round[i]}
                                   if note_round[i] is not None else None),
                          "others": [], "previous": None,
                          "assigned_fact_ids": [], "inject": None}
            else:
                fc = f"[당신의 마지막 발언]\n{previous[i] or ''}\n\n[참석자들의 마지막 발언]\n"
                for k, j in enumerate(edges[i]):
                    fc += f"참석자{k + 1}: {previous[j]}\n"
                final_context = fc
                fslots = {"note": None,
                          "others": [{"round": rounds, "agent_id": seated[j]["agent_id"]}
                                     for j in edges[i]],
                          "previous": {"round": rounds, "agent_id": seated[i]["agent_id"]},
                          "assigned_fact_ids": [], "inject": None}
            spend()
            f_inputs = assemble_coop_final(question, body, final_context)
            _fn3 = guarded(respond or _reasoning_bound(reasoning))
            f_resp = _fn3(f_inputs, model=model, temperature=temp)
            emit("prompt_assembly", round=rounds + 1, agent_id=seated[i]["agent_id"],
                 template="coop_final", prompt_ver=prompt_ver, setting_key=None,
                 slots=fslots, prompt_hash=sha256(f_inputs))
            # 응답 원문 전량 저장 — 파싱된 선택지가 아니라 원문이 1급이다. 정답 대조는
            # 하류(분석)에서 이 원문을 파싱해서 한다(판정기 불사용).
            emit("final_poll", agent_id=seated[i]["agent_id"], round=rounds + 1,
                 prompt_ver=prompt_ver, prompt_hash=sha256(f_inputs),
                 model=llm.resolve_model(model), temperature=temp,
                 response_text=f_resp)
        flush()

    n_inject = sum(1 for e in events if e.get("event") == "ledger_inject")
    warn = "  ⚠ 폴백(무음 공백) 있음 — 해당 발화 검토" if n_fallbacks else ""
    note_bit = ""
    if use_note:
        note_bit = (f", 수첩갱신 {n_note_updates}건/파싱실패 {n_note_parse_fail}"
                    f"/절단 {n_note_truncated}")
        if n_note_parse_fail:
            warn += "  ⚠ 수첩 파싱 실패 있음 — 해당 라운드는 미갱신으로 돌았다"
    poll_bit = f", 최종폴링 {length}건" if final_poll else ""
    print(f"[OK] {out_path.name} — 이벤트 {len(events)}건 "
          f"(에이전트 {length} x 라운드 {rounds}+초기, window={window}, memory={memory}"
          f"{note_bit}{poll_bit}, ledger_mode={ledger_mode}, "
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
