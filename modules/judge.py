"""[공용 코어 · 8/21 요한 결정 (구 패키지 A · 신동범, 8/21 이적)] 채점기(judge) — 순수 함수로 구현.
계약: 입력 debate 로그 + facts 목록 → 출력 paths.judgment(issue, run) (스키마 5번)
사양(확정): Sonnet 단일, temperature 0, n_votes=3 다수결, votes 원본 보존.
순수 함수 원칙: 입력→출력만. 대조군에선 사후 오프라인, 실험군에선 루프 안에서 동일 함수 호출.

이 파일의 상태: 초안(v0.1). 핵심 순수함수(judge_fact) + CLI 래퍼 + FAR 집계 구현 완료.
미확정으로 남긴 것(코드가 아니라 결정 대기):
  - FAR 수식 방향 — 동범.md 열린 질문. 아래 SURVIVING/far() 는 '잠정' 정의이며 노션 확정 시 교체.
  - judge 프롬프트 — v0.2(7/22)에서 저자 evaluate_fact 규칙 계승한 이진 판정으로 정렬.
    근거: judgment 구조 확정(보드 결정 로그 7/22)의 "refuted/ignored 는 v1 전까지 0" 문구와
    코드 일치. accepted/refuted/ignored 세분화는 v1 상태 추적 몫(STATUSES 는 자리 보유).
  - far_agent_mean — 에이전트별 FAR 은 assignments 필요 + 수식 확정 필요. 지금은 null.

사용:
  # 실측(API 호출, 키 필요)
  python -m modules.judge --issue issue_esa --run run001 --config configs/sprint_mini.yaml
  # 오프라인 스텁(키 없이 뼈대·스키마 검증용, 결정론적)
  python -m modules.judge --issue issue_esa --run run001 --config configs/sprint_mini.yaml --offline
막히면: 노션 작업 지시서 #1 패키지 A 항목 아래에 질문."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import llm as _llm   # 별칭 표·공급자 유도의 단일 소스 (모듈 상단은 stdlib 뿐 — SDK 불필요 유지)
from . import paths

SCHEMA_VER = "0.2"
JUDGE_PROMPT_VER = "judge-v0.2-binary"

# 확정 사양의 temperature — 표 생성 경로(_online_vote·_llm_vote)가 **실제로 보내는 값**.
# judgment 의 judge.temperature 에는 cfg 가 아니라 이 상수를 적는다(7/30 보드 회신 ②:
# 기록은 실제 전송값이어야 한다 — cfg 를 적으면 config 에 다른 값을 넣는 순간 산출물
# 메타데이터가 실체와 갈라진다. 기록과 실체의 괴리는 이 파이프라인이 연구하는 실패다).
JUDGE_TEMPERATURE = 0

# 스키마 5번의 status 5종 (validate.py 와 동일 집합).
STATUSES = ("unmentioned", "mentioned", "accepted", "refuted", "ignored")

# 잠정(TODO: FAR 수식 확정) — '살아남음'으로 볼 status. 나머지는 소실로 집계.
# 동범.md 열린 질문 "FAR 수식 방향(선결)" 확정되면 이 한 줄과 far() 만 교체하면 됨.
SURVIVING = {"mentioned", "accepted"}

# 다수결 동점 시 우선순위(보수적 = 소실 쪽을 우선 보고). 앞일수록 먼저 채택.
_TIEBREAK_ORDER = ("unmentioned", "ignored", "refuted", "mentioned", "accepted")

# config 의 짧은 별칭 → 실제 모델 ID. **llm.MODEL_ALIASES 가 단일 소스** (7/30 사본 제거
# 1단계 — 보드 회신 ⑥). 종전엔 judge 가 자기 사본(2항목)을 들고 있어 ⓐ gpt/gemini
# 별칭을 config 로 지정할 수 없었고 ⓑ 별칭 값 수정 시 두 곳을 동시에 고쳐야 했다
# (예: claude-sonnet 별칭은 llm.py·judge.py 두 곳 — "사본의 첫 실제 비용").
# 참조 바인딩이므로 값 분기가 구조적으로 불가능하다. 프롬프트·판정 규칙은 무변경.
MODEL_ALIASES = _llm.MODEL_ALIASES

JUDGE_SYSTEM = (
    "너는 멀티에이전트 토론 로그의 사실 보존을 채점하는 판정기다. "
    "하나의 '팩트'와 한 라운드의 에이전트 발화 원문들을 받는다. "
    "그 라운드 발화들에 이 팩트가 표현되어 있는지 이진 판정하라.\n"
    "판정 규칙 (저자 evaluate_fact 계승):\n"
    "- 발화가 이 팩트를 명시적 또는 암묵적으로 표현하면 mentioned\n"
    "- 바꿔 말한 표현(패러프레이즈)도 인정한다\n"
    "- 부분적으로만 뒷받침되면 인정하지 않는다\n"
    "- 발화 원문에만 근거하라. 없는 내용을 추정하지 마라. 외부 지식 사용 금지\n"
    "- 위에 해당하지 않으면 unmentioned\n"
    "(v0 는 이진 판정만 한다 — accepted/refuted/ignored 세분화는 v1 상태 추적에서)\n"
    '반드시 아래 JSON 만 출력하라(설명 텍스트 금지): '
    '{"status": "mentioned 또는 unmentioned", "agents_mentioning": ["<이 팩트를 표현한 agent_id>"], '
    '"reason": "<한 문장 근거>"}'
)


# ---------------------------------------------------------------------------
# 입력 로딩 (순수)
# ---------------------------------------------------------------------------
def load_utterances(debate_path: Path) -> list[dict]:
    """debate jsonl 에서 발화 이벤트만 뽑아 stage(=round) 순으로 반환."""
    out: list[dict] = []
    for line in debate_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("event") == "utterance":
            out.append(ev)
    return out


def group_by_stage(utterances: list[dict]) -> dict[int, list[dict]]:
    """발화를 round(=stage) 별로 묶는다. 키 오름차순."""
    stages: dict[int, list[dict]] = {}
    for u in utterances:
        stages.setdefault(u.get("round"), []).append(u)
    return dict(sorted(stages.items(), key=lambda kv: kv[0]))


# ---------------------------------------------------------------------------
# 한 표(vote) — 온라인(API) / 오프라인(결정론적 스텁)
# ---------------------------------------------------------------------------
def _resolve_model(name: str) -> str:
    return _llm.resolve_model(name)   # 위임 — 해석 규칙도 llm 이 단일 소스


def _user_prompt(fact: dict, stage_utterances: list[dict]) -> str:
    lines = [
        f"[팩트] id={fact['fact_id']} critical={fact.get('critical')}",
        f"내용: {fact['text']}",
        "",
        "[이 라운드 발화 원문]",
    ]
    for u in stage_utterances:
        lines.append(f"- ({u.get('agent_id')}) {u.get('response_text', '')}")
    return "\n".join(lines)


def _online_vote(client, model: str, fact: dict, stage_utterances: list[dict]) -> dict:
    """API 한 번 호출 = 한 표. 실패해도 파이프라인이 죽지 않게 안전 파싱."""
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        temperature=JUDGE_TEMPERATURE,  # 확정 사양 — 기록(judge.temperature)과 같은 상수
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": _user_prompt(fact, stage_utterances)}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return _parse_vote(text, stage_utterances)


def _llm_vote(model_alias: str, fact: dict, stage_utterances: list[dict]) -> dict:
    """API 한 번 호출 = 한 표 — **공급자 무관** 경로 (2026-07-30 · 민옥, 추가분).

    왜 추가하는가: 위 _online_vote 는 Anthropic SDK 에 직결돼 있어, ANTHROPIC_API_KEY 가
    없으면 채점 자체가 불가능하다 — 그러면 FAR 이 영원히 안 나온다. llm 모듈은 이미
    3사 공급자를 유도하므로 그 경로를 한 갈래 더 놓는다.

    **기존 경로는 한 글자도 바꾸지 않았다.** judge_model 이 claude 계열이면 종전
    _online_vote 가 그대로 쓰이고, 그 외 공급자일 때만 이 함수가 쓰인다. 확정 사양
    (Sonnet 단일·temp 0·n=3 다수결)의 기본값도 그대로다 — 넓힌 것은 사양이 아니라
    사양이 표현할 수 있는 좌표다.

    ⚠ 조립 편차 1건 (조용히 넘기지 않는다): llm.obtain_response 는 system 역할을 받지
    않으므로 JUDGE_SYSTEM 을 사용자 프롬프트 앞에 붙인다. 같은 문장이지만 역할 배치가
    달라 판정이 달라질 수 있다. 그래서 이 경로로 만든 judgment 은 prompt_ver 에
    `+merged_system` 이 붙는다 — 나중에 두 판정을 나란히 놓을 때 잣대가 달랐음이
    산출물에서 드러나야 한다(조용한 프롬프트 변경은 재현성을 깬다).
    ⚠ 지위: judge.py 는 동범 님 담당 파일(패키지 A)이다. 이 추가는 사후 보고 대상이며,
    판정 사양의 공급자 좌표는 보드 확인이 필요하다.
    """
    text = _llm.obtain_response(
        JUDGE_SYSTEM + "\n\n" + _user_prompt(fact, stage_utterances),
        model=model_alias, temperature=JUDGE_TEMPERATURE)  # 확정 사양 — 기록과 같은 상수
    return _parse_vote(text, stage_utterances)


def _offline_vote(fact: dict, stage_utterances: list[dict]) -> dict:
    """키 없이 도는 결정론적 스텁 — 뼈대·스키마 검증 전용(모델 판정 아님).
    규칙: 발화 원문에 fact_id 또는 팩트 텍스트가 나타나면 mentioned, 아니면 unmentioned."""
    needle = fact["text"].strip()
    mentioning = []
    for u in stage_utterances:
        body = u.get("response_text", "") or ""
        if fact["fact_id"] in body or (needle and needle in body):
            mentioning.append(u.get("agent_id"))
    status = "mentioned" if mentioning else "unmentioned"
    return {"status": status, "agents_mentioning": mentioning, "reason": "offline-stub(substring)"}


def _parse_vote(text: str, stage_utterances: list[dict]) -> dict:
    """모델 출력 JSON 파싱 + 방어. status 가 5종 밖이면 unmentioned 로 강등."""
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        obj = json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"status": "unmentioned", "agents_mentioning": [], "reason": f"parse_fail: {text[:120]}"}
    status = obj.get("status")
    if status not in STATUSES:
        status = "unmentioned"
    valid_ids = {u.get("agent_id") for u in stage_utterances}
    mentioning = [a for a in obj.get("agents_mentioning", []) if a in valid_ids]
    return {"status": status, "agents_mentioning": mentioning, "reason": obj.get("reason", "")}


def _is_parse_fail(vote: dict) -> bool:
    """이 표가 모델 출력 JSON 파싱에 실패했는지 — reason 이 'parse_fail:' 로 시작하면 실패.
    _parse_vote 가 파싱 실패 시 그 접두사를 reason 에 남긴다(성공 시엔 모델의 한 문장 근거).
    판정에는 영향 없는 관측(계기판)용 판별 — vote 값을 읽기만 한다."""
    return str(vote.get("reason", "")).startswith("parse_fail:")


# ---------------------------------------------------------------------------
# 핵심 순수 함수: judge_fact
# ---------------------------------------------------------------------------
def _majority(statuses: list[str]) -> str:
    counts = Counter(statuses)
    top = max(counts.values())
    tied = [s for s, c in counts.items() if c == top]
    if len(tied) == 1:
        return tied[0]
    # 동점 → 보수적 우선순위(소실 쪽 우선)
    return min(tied, key=lambda s: _TIEBREAK_ORDER.index(s))


def judge_fact(stage_utterances: list[dict], fact: dict, *, vote_fn, n_votes: int = 3) -> dict:
    """한 라운드 발화 + 한 팩트 → 판정 레코드(순수).
    vote_fn(fact, stage_utterances) -> {status, agents_mentioning, reason} 를 n_votes 회 호출.
    votes 원본 3표를 그대로 보존(불일치율 = judge 신뢰도 지표, 7/16 파일럿 핵심).
    반환: {fact_id, status(다수결), votes[], agents_mentioning[](표 합집합)}"""
    votes = [vote_fn(fact, stage_utterances) for _ in range(n_votes)]
    status = _majority([v["status"] for v in votes])
    mentioning = sorted({a for v in votes for a in v["agents_mentioning"]})
    return {
        "fact_id": fact["fact_id"],
        "status": status,
        "votes": votes,
        "agents_mentioning": mentioning,
    }


def judge_stage(stage_utterances: list[dict], facts: list[dict], *, vote_fn,
                n_votes: int = 3) -> list[dict]:
    """[통합용 얇은 진입점 — INTEGRATION_ledger.md 확정 요청 1의 구현 제안]
    한 라운드 발화 목록(in-memory) + 전체 팩트 목록 → 판정 레코드 목록(순수, 파일 미접근).

    루프 안 실험군(ledger on)은 debate 파일이 생기기 전에 라운드를 채점해야 하므로
    파일 기반 judge_debate 를 못 쓴다. 이 진입점은 judge_debate 와 **같은 judge_fact 를
    호출**하므로 대조군/실험군의 측정 잣대 동일성이 코드로 보장된다.
    ⚠ 제안 상태: 시그니처는 동범 님 확인 대기(패키지 A). 변경 시 debate_engine 결합부도 함께.
    """
    return [judge_fact(stage_utterances, f, vote_fn=vote_fn, n_votes=n_votes) for f in facts]


# ---------------------------------------------------------------------------
# same-parent A/B/C 사후 판정 adapter
# ---------------------------------------------------------------------------
def make_same_parent_bundle_evaluator(model_config: dict):
    """단일 parent + 단일 bundle을 기존 ``modules.llm`` 경계로 판정한다.

    provider SDK, API key, retry/backoff를 이 모듈에 복제하지 않는다. factory에서 기존
    preflight를 한 번 실행하고, 반환 callable은 coordinate마다 obtain_response를 정확히
    한 번 호출해 **raw 문자열 그대로** runner에 돌려준다. 파싱·append/fsync·resume은
    :mod:`modules.abc_same_parent_runner`의 소관이다.
    """
    if not isinstance(model_config, dict):
        raise ValueError("model_config must be an object")
    model = model_config.get("model")
    if not isinstance(model, str) or not model.strip():
        raise KeyError("model_config.model is required")
    temperature = model_config.get("temperature", JUDGE_TEMPERATURE)
    if isinstance(temperature, bool) or float(temperature) != float(JUDGE_TEMPERATURE):
        raise ValueError(f"same-parent judge temperature must be {JUDGE_TEMPERATURE}")
    reasoning = model_config.get("reasoning", "default")
    if reasoning != "default":
        raise ValueError("same-parent judge reasoning must be 'default'")
    _llm.preflight(model, temperature=float(JUDGE_TEMPERATURE), reasoning=reasoning)

    def evaluate(parent_r0: bytes, bundle: dict, coordinate: dict) -> str:
        # strict decode: replacement characters would mean the model did not receive the frozen
        # parent represented by parent_r0 bytes. Fail before provider invocation instead.
        parent_text = parent_r0.decode("utf-8", errors="strict")
        if not isinstance(bundle, dict) or bundle.get("role") != "posthoc_judge":
            raise ValueError("posthoc_judge bundle required")
        if not isinstance(coordinate, dict):
            raise ValueError("coordinate object required")
        prompt = (
            "[COMMON SEMANTIC JUDGE PROTOCOL]\n"
            + str(bundle.get("common_protocol") or "")
            + "\n\n[COORDINATE JSON]\n"
            + json.dumps(coordinate, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
            + "\n\n[POSTHOC BUNDLE JSON]\n"
            + json.dumps(bundle, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
            + "\n\n[FROZEN PARENT R0 — UTF-8, EXACT TEXT]\n"
            + parent_text
            + "\n[END FROZEN PARENT R0]\n"
        )
        return _llm.obtain_response(
            prompt, model=model, temperature=float(JUDGE_TEMPERATURE),
            reasoning=reasoning)

    return evaluate


# ---------------------------------------------------------------------------
# FAR 집계 (잠정 — 수식 확정 시 교체)
# ---------------------------------------------------------------------------
def far(fact_records: list[dict], facts_by_id: dict[str, dict], *, critical_only: bool = False) -> float | None:
    """소실률 = 소실 팩트 수 / 대상 팩트 수. '소실' = status not in SURVIVING.
    TODO(FAR 수식 미확정): refuted 를 소실로 볼지, unmentioned 만 셀지 등은 노션 확정 대기.
    현재 잠정: SURVIVING={mentioned,accepted} 외 전부 소실."""
    rows = fact_records
    if critical_only:
        rows = [r for r in rows if facts_by_id.get(r["fact_id"], {}).get("critical")]
    if not rows:
        return None
    lost = sum(1 for r in rows if r["status"] not in SURVIVING)
    return round(lost / len(rows), 4)


# ---------------------------------------------------------------------------
# 오케스트레이터 + CLI 래퍼
# ---------------------------------------------------------------------------
def _load_config(config_path: Path | None) -> dict:
    cfg = {"judge_model": "claude-sonnet", "judge_temperature": 0, "judge_n_votes": 3,
           "max_llm_calls": None, "promotion_tier": "confirmatory",
           "aggregate_eligible": True, "report_eligible": True}
    if config_path:
        import yaml  # requirements.txt

        allowed = set(cfg)
        cfg.update({k: v for k, v in yaml.safe_load(config_path.read_text(encoding="utf-8")).items()
                    if k in allowed or k.startswith("judge")})
    return cfg


def _make_client():
    from anthropic import Anthropic  # 지연 import — offline 모드는 SDK 불필요

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("[judge] ANTHROPIC_API_KEY 없음 — .env 설정하거나 --offline 로 실행")
    return Anthropic()


def judge_debate(issue_id: str, run_id: str, cfg: dict, *, offline: bool = False) -> dict:
    """debate 로그 + facts → judgment(스키마 5번) dict 생성(파일 쓰기는 호출측/CLI)."""
    facts = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))["facts"]
    facts_by_id = {f["fact_id"]: f for f in facts}
    stages_utt = group_by_stage(load_utterances(paths.debate(issue_id, run_id)))
    n_votes = int(cfg.get("judge_n_votes", 3))
    expected_calls = len(facts) * len(stages_utt) * n_votes
    if cfg.get("promotion_tier") == "pilot_unvetted" and not offline:
        max_calls = cfg.get("max_llm_calls")
        if not isinstance(max_calls, int) or isinstance(max_calls, bool) or max_calls <= 0:
            raise SystemExit("[judge] pilot_unvetted requires positive max_llm_calls")
        if max_calls > 30:
            raise SystemExit(f"[judge] pilot max_llm_calls={max_calls} exceeds hard limit 30")
        if expected_calls > max_calls:
            raise SystemExit(
                f"[judge] pilot expected calls {expected_calls} exceed max_llm_calls={max_calls}")
        if cfg.get("aggregate_eligible") is not False or cfg.get("report_eligible") is not False:
            raise SystemExit("[judge] pilot_unvetted must be aggregate/report ineligible")
    cfg_temp = cfg.get("judge_temperature", JUDGE_TEMPERATURE)
    if float(cfg_temp) != float(JUDGE_TEMPERATURE):
        # 조용히 무시하지 않는다 — cfg 에 다른 값을 적은 사람은 그 값이 쓰였다고 믿는다.
        print(f"[judge] ⚠ config judge_temperature={cfg_temp} 는 사용되지 않습니다 — "
              f"확정 사양이 temperature={JUDGE_TEMPERATURE} 를 하드코딩합니다(임의 변경 금지). "
              f"산출물에는 실제 전송값 {JUDGE_TEMPERATURE} 이 기록됩니다.")

    prompt_ver = JUDGE_PROMPT_VER
    if offline:
        base_vote_fn = _offline_vote
        model_id = "offline-stub"
    else:
        judge_alias = cfg.get("judge_model", "claude-sonnet")
        # 공급자 분기 (7/30 민옥 추가 / 7/30 동범 개정 — 담당 파일 후속). claude 계열은
        # 종전 _online_vote 그대로, 그 외 공급자만 llm 경유. 경로는 prompt_ver 에 남는다.
        # 개정 2건: ① 미지 별칭 → Anthropic 임시 폴백을 제거하고 **즉사**로 — 오타가
        # 조용히 Anthropic 으로 흘러 "다른 모델이 돌았는데 로그엔 맞다고 적힌" run 을
        # 만드는 구멍(리뷰 ⑥ⓑ). llm.resolve_provider 의 즉사 가드를 그대로 쓴다.
        # ② preflight 를 Anthropic 경로에도 — 자리표시자 키(24자 미만)·SDK 부재를
        # 144콜 태우기 전에 잡는다(_make_client 는 키 '존재'만 봤다).
        provider = _llm.resolve_provider(judge_alias)   # 미지 모델은 여기서 KeyError
        _llm.preflight(judge_alias, temperature=JUDGE_TEMPERATURE)  # 키·자리표시자·SDK·온도 관문
        if provider == "anthropic":
            client = _make_client()
            model_id = _resolve_model(judge_alias)
            base_vote_fn = lambda fact, utts: _online_vote(client, model_id, fact, utts)  # noqa: E731
        else:
            model_id = _llm.resolve_model(judge_alias)
            prompt_ver = JUDGE_PROMPT_VER + "+merged_system"
            base_vote_fn = lambda fact, utts: _llm_vote(judge_alias, fact, utts)  # noqa: E731

    # --- 진행 계기판 (관측 전용, 판정 불변) ----------------------------------
    # judge 는 표 하나당 vote 를 한 번 부르고(총 stage x 팩트 x n_votes 회), 실패해도
    # 죽지 않고 조용히 unmentioned 로 강등된다(_parse_vote). 그래서 base_vote_fn 을
    # 얇게 감싸 (1) 표마다 진행 한 줄 출력 (2) 파싱실패 표 수를 집계한다. 감싼 함수는
    # base_vote_fn 의 반환값을 그대로 통과시키므로 judge_fact·판정 잣대에는 영향이 없다.
    # 위치(stage/팩트/표)는 전역 표 순번에서 역산한다 — 매 stage 는 전 팩트 완전 스냅샷이라
    # stage 하나 = (팩트 수 x n_votes) 표로 일정하다.
    total_stages = len(stages_utt)
    total_facts = len(facts)
    votes_per_stage = max(total_facts * n_votes, 1)
    # 공백 발화 계수 (7/30 보드 회신 ⑤ — 관측 전용, 판정 불변). llm 폴백(' ')이 만든
    # 공백 발화가 채점에 섞이면 팩트가 있을 수 없으니 전 팩트 unmentioned →
    # far_system=1.0 인데, 종전 계기판(n_calls·n_parse_fail)만으로는 그 판정 파일이
    # 정상 산출물과 구별되지 않았다. "모델이 팩트를 잃었다"와 "호출이 실패했다"를
    # 산출물이 스스로 구별하도록 입력 발화의 공백 수를 센다(뷰어에만 있던 검사의 이식).
    n_blank = sum(1 for utts in stages_utt.values() for u in utts
                  if not str(u.get("response_text") or "").strip())
    health = {"n_calls": 0, "n_parse_fail": 0, "n_blank_utterances": n_blank}

    def instrumented_vote(fact, utts):
        vote = base_vote_fn(fact, utts)
        idx = health["n_calls"]  # 이번 표의 0-기반 순번
        health["n_calls"] += 1
        if _is_parse_fail(vote):
            health["n_parse_fail"] += 1
        within = idx % votes_per_stage
        print(f"[judge] stage {idx // votes_per_stage + 1}/{total_stages} · "
              f"팩트 {within // n_votes + 1}/{total_facts} · "
              f"표 {within % n_votes + 1}/{n_votes} · "
              f"파싱실패 누적 {health['n_parse_fail']}")
        return vote

    vote_fn = instrumented_vote

    stages_out, far_by_stage = [], []
    for stage, utts in stages_utt.items():
        recs = judge_stage(utts, facts, vote_fn=vote_fn, n_votes=n_votes)
        stages_out.append({"stage": stage, "facts": recs})
        far_by_stage.append({
            "stage": stage,
            "far_system": far(recs, facts_by_id),
            "far_critical": far(recs, facts_by_id, critical_only=True),
        })

    last = far_by_stage[-1] if far_by_stage else {"far_system": None, "far_critical": None}
    return {
        "schema_ver": SCHEMA_VER,
        "created_by": "modules.judge",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "issue_id": issue_id,
        "run_id": run_id,
        "promotion_tier": cfg.get("promotion_tier", "confirmatory"),
        "aggregate_eligible": bool(cfg.get("aggregate_eligible", True)),
        "report_eligible": bool(cfg.get("report_eligible", True)),
        "expected_llm_calls": 0 if offline else expected_calls,
        "max_llm_calls": 0 if offline else cfg.get("max_llm_calls"),
        "judge": {
            "model": model_id,
            # 실제 전송값을 적는다 — cfg 값이 아니라(7/30 보드 회신 ② 불일치 수정).
            # 두 vote 경로 모두 JUDGE_TEMPERATURE 를 보내므로 이 기록은 항상 실체와 같다.
            "temperature": JUDGE_TEMPERATURE,
            "n_votes": n_votes,
            "aggregation": "majority",
            "prompt_ver": prompt_ver,   # 비-Anthropic 경로면 +merged_system 이 붙는다
        },
        "stage_type": "round",  # 실험 트랙. 관찰 트랙(summary_layer)은 별도 실행에서.
        "stages": stages_out,
        # recall_probe[](A4, 선택)는 이번 스프린트 범위 밖 — 빈 배열로 자리만 유지.
        "recall_probe": [],
        "summary": {
            "far_by_stage": far_by_stage,
            "far_system": last["far_system"],
            "far_agent_mean": None,  # TODO: assignments + FAR 수식 확정 후 산출
            "far_critical": last["far_critical"],
            "judge_health": health,  # 관측 계기판(추가 필드): {n_calls, n_parse_fail, n_blank_utterances} — 소비자 P2·ledger 무관
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="채점기(judge) — debate 로그 → judgment")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--offline", action="store_true", help="API 없이 결정론적 스텁으로 판정")
    args = ap.parse_args()

    cfg = _load_config(args.config)
    result = judge_debate(args.issue, args.run, cfg, offline=args.offline)

    out_path = paths.judgment(args.issue, args.run)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[judge] 작성: {out_path}")
    print(f"[judge] far_system={result['summary']['far_system']} "
          f"far_critical={result['summary']['far_critical']} (잠정 수식)")
    h = result["summary"]["judge_health"]
    warn = "  ⚠ 파싱실패 있음 — 해당 판 재채점 검토" if h["n_parse_fail"] else ""
    blank = h.get("n_blank_utterances", 0)
    warn2 = (f"  ⚠ 공백 발화 {blank}건 입력 — far 오염 가능(llm 폴백 흔적), debate 로그 확인"
             if blank else "")
    print(f"[judge] 건강: 표 {h['n_calls']}회 · 파싱실패 {h['n_parse_fail']}회 · "
          f"공백 발화 {blank}건{warn}{warn2}")
    print("[judge] 자기검사: python -m modules.validate " + str(out_path))


if __name__ == "__main__":
    main()
