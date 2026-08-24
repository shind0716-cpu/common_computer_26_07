"""[민옥 트랙 · 기억 구조 1단] 단독 담화전진 재실험 러너 — 3(진행)×3(기억), 라운드 0~3.

정본 프롬프트: PROMPTS_v1.md (이 파일의 상수는 그 문서의 미러 — 불일치 시 문서가 정본).
사전등록: PREREG_v1.md — **PREREG 로컬 커밋 전 실호출 금지** (--dry 는 0콜이라 허용).

실행 구도 (PREREG §4):
  GPT·Gemini  : modules.llm 경유 API — preflight(키·온도 관문)·절단 A안·자리표시자 즉사 상속
  Claude      : 헤르메스 파일 왕복 (--provider hermes) — 러너가 hermes/pending/에 프롬프트
                파일을 쓰고 hermes/answers/에 답 파일이 나타날 때까지 폴링한다.
                프로토콜 전문은 WORKORDER_HERMES.md.

규율(CLAUDE.md): 호출 상한(--max-calls, 초과 즉사) · 호출 단위 체크포인트(.partial.jsonl,
재실행 이어받기) · 프롬프트/응답 원문 전량 보존 · 경로는 paths.py · PYTHONUTF8=1.

[2026-08-18 · 민옥 트랙] **v2 손잡이 3종 추가 (후속 실험용 — 기본값이면 v1과 문면 동일).**
  --note-budget N    수첩 예산 스윕 (기본 500. 500이면 v1 문면과 바이트 동일)
  --facts-reverse    사실 목록 역순 (순서 교락 분리 실험)
  --no-stance        입장 고정 해제 (+ --final-poll: 마지막에 최종 판단 1필드 수집)
  변형 프롬프트 축자 정본은 PROMPTS_v2.md(작성 중). **PROMPTS_v2·PREREG_v2 로컬 커밋 전
  v2 조건 실호출 금지** — 코드가 --allow-v2 없는 v2 실호출을 즉사시킨다(--dry 는 허용).
  v2 조건의 run_id 에는 접미사가 붙어 v1 산출물과 절대 섞이지 않는다(b250·rev·ns).

[2026-08-19 · 민옥 트랙] **--issue 손잡이 추가 (재료 확장용 — 기본값이면 종전과 동일).**
  --issue ISSUE      재료 이슈 (기본 issue_camp). 문면은 ISSUE_PROMPTS 표에서 고른다.
  --stance-key KEY   입장 대립형 재료에서 어느 입장으로 돌릴지(issue_polar: 후송|대기 등)
  **인자를 안 주면 프롬프트 문면·run_id·산출물 경로가 전부 종전과 바이트 동일하다.**
  camp 밖의 재료는 산출물이 runs/<model>/<issue>/ 로 갈린다 — run_id 에 이슈가 없어서
  안 나누면 다른 재료의 A_note_rep1 이 camp 것과 같은 파일명이 되어 조용히 스킵된다.

사용례:
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --dry                 # 0콜 조립 리허설(전 81런)
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --issue issue_throne --reps 1 --dry
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --issue issue_polar --stance-key 후송 --reps 1 --dry
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --model gpt --reps 1  # GPT rep1 (9런 54콜)
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --provider hermes --model claude-hermes --reps 1
  # v2 예시 (사전등록 커밋 후):
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --model gpt --memories note --note-budget 250 --allow-v2
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --model gpt --facts-reverse --allow-v2
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --model gpt --no-stance --final-poll --allow-v2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules import llm  # noqa: E402

DEFAULT_ISSUE = "issue_camp"
PROMPTS_VER_V1 = "solo-v1"        # PROMPTS_v1.md
PROMPTS_VER_V2 = "solo-v2-draft"  # PROMPTS_v2.md (사전고정 전 — 커밋 시 'solo-v2'로 올릴 것)
ROUNDS = 4                        # r0~r3
DEFAULT_NOTE_BUDGET = 500         # 자(파이썬 len, 공백·문장부호 포함)
GEN_TEMPERATURE = 0.7             # PREREG §4 (API 두 팔. hermes 는 TBD-1 — meta 에 문자열 기록)
HERMES_POLL_SEC = 5
HERMES_TIMEOUT_SEC = 3600
PILOT_CALL_LIMIT = 30

HERE = Path(__file__).resolve().parent
RUNS_DIR = HERE / "runs"
HERMES_DIR = HERE / "hermes"

ARMS = {"A": "repeat", "P": "progress", "B": "delib"}   # P = A′ (드라이런 키 계승)
MEMS = ("full", "note", "prev")

# ── 프롬프트 축자 (PROMPTS_v1.md 미러 — 수정 금지, 정정은 문서부터) ──────────

STUB = ("대학 연합 동아리(회원 33명)의 가을 합숙지를 다림재 수련원과 무레온 캠프 중 "
        "한 곳으로 정하는 문제를 논의 중이다. 총회가 의결한 조건은 네 가지다. "
        "① 1인당 42,000원 이하 ② 35인 이상 실내 공간 ③ 10월 17~18일 예약 가능 "
        "④ 배상책임보험 가입 시설.")

STANCE = "너의 입장은 '무레온 캠프로 가야 한다'이다. 이 입장은 끝까지 유지한다."

# {REF} = 그 조건에서 실제로 보이는 캐리어 이름 (PROMPTS_v1 §1.4 — 파일럿 부록 A 계승)
MEM_REF = {"full": "지금까지 쓴 글", "note": "너의 수첩", "prev": "직전에 쓴 글"}

INSTR = {
    "A": ("네게 지금 보이는 {REF}을 참고해, 같은 입장을 더 설득력 있게 강화하는 "
          "새 글을 한 문단으로 써라."),
    "P": ("네게 지금 보이는 {REF}을 참고하되, 같은 입장을 유지하면서 거기에서 "
          "사용한 논거를 반복하지 말고 매번 새로운 논거로 강화하는 새 글을 한 문단으로 써라."),
    "B": ("네게 지금 보이는 {REF}을 참고해, 너의 입장에 대해 가장 강한 반론을 스스로 "
          "제기하고 진지하게 검토한 뒤, 그 검토를 반영해 견해를 갱신한 글을 한 문단으로 써라."),
}

# ── v2 변형 축자 (PROMPTS_v2.md 미러 초안 — 사전고정 전. 수정은 문서부터) ────
# 무입장 변형: v1 문면에서 "입장"을 "판단"으로 바꾸고 고정 지시를 제거한 최소 수정.

INSTR_FREE = {
    "A": ("네게 지금 보이는 {REF}을 참고해, 너의 판단을 더 설득력 있게 강화하는 "
          "새 글을 한 문단으로 써라."),
    "P": ("네게 지금 보이는 {REF}을 참고하되, 거기에서 사용한 논거를 반복하지 말고 "
          "매번 새로운 논거로 너의 판단을 전개하는 새 글을 한 문단으로 써라."),
    "B": ("네게 지금 보이는 {REF}을 참고해, 너의 판단에 대해 가장 강한 반론을 스스로 "
          "제기하고 진지하게 검토한 뒤, 그 검토를 반영해 견해를 갱신한 글을 한 문단으로 써라."),
}

R0_TASK_STANCE = "위 사안에 대한 너의 입장을 밝히는 글을 한 문단으로 써라. 글 본문만 출력하라."
R0_TASK_FREE = "위 사안을 검토하여 너의 판단을 밝히는 글을 한 문단으로 써라. 글 본문만 출력하라."

FINAL_POLL_INSTR = ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                    "'다림재 수련원' 또는 '무레온 캠프' 중 하나만 출력하라.")

# ── 이슈별 프롬프트 문면 (2026-08-19 · --issue 배관) ─────────────────────────
# camp 은 위 상수를 그대로 가리킨다 — 문면 한 글자도 안 바뀌므로 --issue 없이 돌리면
# 종전과 바이트 동일하다.
#
# camp 밖의 문면은 **요한 측이 만든 정의를 그대로 옮긴 것**이다. 임의로 새로 쓰지 않는다.
#   출처: experiments/scenario_generalization/build_issue_{throne,polar,exile}.py 의
#         SOLO_PROMPTS (그 파일이 정본 — 문면을 고치려면 거기부터 고친다)
#
# stances 는 그 이슈가 가진 입장 목록이다. camp·throne 처럼 입장이 하나뿐인 재료는
# "fixed" 키 하나, polar·exile 처럼 입장 대립형은 두 키를 갖는다(--stance-key 로 고른다).
ISSUE_PROMPTS = {
    "issue_camp": {
        "stub": STUB,
        "stances": {"fixed": STANCE},
        "final_poll": FINAL_POLL_INSTR,
    },
    "issue_throne": {
        "stub": ("카른라드 왕국의 왕위를 선왕의 딸 베스카와 선왕의 조카 아르넬 중 누가 이을지 "
                 "정하는 문제를 논의 중이다. 계승법이 정한 조건은 네 가지다. ① 선왕의 인장이 찍힌 "
                 "계승 서약에 이름이 오를 것 ② 성년인 스무 살에 이를 것 ③ 열두 제후 가운데 일곱 "
                 "이상의 서명 ④ 대주교청의 성별식 자격 인정."),
        "stances": {"fixed": "너의 입장은 '아르넬이 왕위를 이어야 한다'이다. 이 입장은 끝까지 유지한다."},
        "final_poll": ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                       "'베스카' 또는 '아르넬' 중 하나만 출력하라."),
    },
    "issue_polar": {
        "stub": ("월동 중인 하르뫼 기지에서 대원 한 사람이 밤사이 위중해졌다. 기지장은 항공편으로 "
                 "바깥 병원까지 후송할지, 기지에 두고 버틸지를 오늘 안에 정해야 한다. 어느 쪽도 "
                 "안전하지 않다."),
        "stances": {
            "후송": "너의 입장은 '환자를 항공편으로 후송해야 한다'이다. 이 입장은 끝까지 유지한다.",
            "대기": "너의 입장은 '후송하지 말고 기지에서 버텨야 한다'이다. 이 입장은 끝까지 유지한다.",
        },
        "final_poll": ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                       "'후송한다' 또는 '후송하지 않는다' 중 하나만 출력하라."),
    },
    "issue_exile": {
        "stub": ("강 건너에서 온 사람들이 메르반 시 외곽 정착지에 살고 있다. 그 정착지를 근거로 한 "
                 "조직이 밀수와 갈취로 적발되자, 시의회는 정착 협정을 파기하고 정착민을 돌려보낼지를 "
                 "정해야 한다. 협정을 파기하면 그 대상은 정착민 전원이 된다."),
        "stances": {
            "추방": "너의 입장은 '정착 협정을 파기하고 정착민을 돌려보내야 한다'이다. 이 입장은 끝까지 유지한다.",
            "잔류": "너의 입장은 '협정을 유지하고 정착민을 돌려보내서는 안 된다'이다. 이 입장은 끝까지 유지한다.",
        },
        "final_poll": ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                       "'협정을 파기한다' 또는 '협정을 유지한다' 중 하나만 출력하라."),
    },
    # 2026-08-20 추가. 출처: 시나리오/build_issue_award.py 의 SOLO_PROMPTS — 그 파일이 정본이고
    # 여기는 사본이다(throne·polar·exile 과 같은 방식). 답이 셋이라 final_poll 의 선택지도 셋이다.
    "issue_award": {
        "stub": ("한들 게임 대상 올해의 작품 부문에서 「석호의 계단」, 「밤길 안내인」, 「종이 낚시」 "
                 "가운데 무엇을 뽑을지 논의 중이다. 규정은 셋이다. ① 해당 부문에 출품된 작품만 "
                 "심사한다 ② 신고하지 않은 외주나 자동 생성 도구 사용이 확인되면 결격이다 "
                 "③ 남은 작품 가운데 연출·설계·완성도에서 가장 앞선 작품을 뽑는다."),
        "stances": {"fixed": "너의 입장은 '밤길 안내인이 올해의 작품이 되어야 한다'이다. 이 입장은 끝까지 유지한다."},
        "final_poll": ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                       "'석호의 계단', '밤길 안내인', '종이 낚시' 중 하나만 출력하라."),
    },
}

# 지금 조립에 쓰이는 문면. 기본이 camp 이라 --issue 를 안 주면 종전과 같다.
_ACTIVE = {"stub": STUB, "stance": STANCE, "final_poll": FINAL_POLL_INSTR}


def select_issue(issue_id: str, stance_key: str | None = None) -> str:
    """_ACTIVE 를 그 이슈의 문면으로 맞춘다. 고른 입장 키를 돌려준다."""
    if issue_id not in ISSUE_PROMPTS:
        raise SystemExit(f"[run_solo] 프롬프트 문면이 없는 이슈: {issue_id} — "
                         f"등록된 것: {', '.join(ISSUE_PROMPTS)}")
    p = ISSUE_PROMPTS[issue_id]
    stances = p["stances"]
    if stance_key is None:
        if len(stances) > 1:
            raise SystemExit(f"[run_solo] --stance-key 필요 — {issue_id} 의 입장: "
                             f"{', '.join(stances)}")
        stance_key = next(iter(stances))
    elif stance_key not in stances:
        raise SystemExit(f"[run_solo] 모르는 입장 '{stance_key}' — {issue_id} 의 입장: "
                         f"{', '.join(stances)}")
    _ACTIVE["stub"] = p["stub"]
    _ACTIVE["stance"] = stances[stance_key]
    _ACTIVE["final_poll"] = p["final_poll"]
    return stance_key


def instr(arm: str, mem: str, stance: bool) -> str:
    table = INSTR if stance else INSTR_FREE
    return table[arm].replace("{REF}", MEM_REF[mem])


def note_instr(budget: int) -> str:
    return ("다음 라운드의 너는 지금 화면에 보이는 내용을 더 이상 보지 못하고, 네가 지금 "
            "남기는 수첩만 보게 된다. 수첩은 다음 라운드로 이월되는 유일한 기억이다. "
            f"다음 라운드의 너에게 남길 수첩을 {budget}자 이내로 써라. 수첩 본문만 출력하라.")


RECALL_INSTR = ("이 사안과 관련해 네가 알고 있는 구체적 사실을 빠짐없이 목록으로 적어라. "
                "확실하지 않은 것은 적지 마라. 목록만 출력하라.")


def load_facts_block(reverse: bool = False, issue_id: str = DEFAULT_ISSUE) -> str:
    doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    facts = list(doc["facts"])
    if reverse:
        facts = list(reversed(facts))
    return "\n".join("- " + f["text"] for f in facts)  # ID 미노출 (중대 15)


def _sec(title: str, body: str) -> str:
    return f"[{title}]\n{body}"


def _stance_block(stance: bool) -> str:
    return (_ACTIVE["stance"] + "\n\n") if stance else ""


def prompt_r0(facts_block: str, stance: bool) -> str:
    task = R0_TASK_STANCE if stance else R0_TASK_FREE
    return ("다음 사안을 검토하라.\n\n" + _sec("사안", _ACTIVE["stub"]) + "\n\n" +
            _sec("알게 된 사실", facts_block) + "\n\n" + _stance_block(stance) + task)


def prompt_round(arm: str, mem: str, facts_block: str, essays: list[str],
                 note: str | None, stance: bool) -> str:
    head = "다음 사안을 검토하라.\n\n" + _sec("사안", _ACTIVE["stub"]) + "\n\n"
    if mem == "full":
        hist = "\n\n".join(f"[라운드 {i} 글]\n{t}" for i, t in enumerate(essays))
        mid = _sec("알게 된 사실", facts_block) + "\n\n" + _stance_block(stance) + \
              _sec("지금까지 쓴 글", hist)
    elif mem == "note":
        mid = _stance_block(stance) + _sec("너의 수첩", note or "")
    else:  # prev
        mid = _stance_block(stance) + _sec("직전에 쓴 글", essays[-1])
    return head + mid + "\n\n" + instr(arm, mem, stance) + " 글 본문만 출력하라."


def prompt_note(r: int, facts_block: str, note_prev: str | None, essay_r: str,
                stance: bool, budget: int) -> str:
    carrier = (_sec("알게 된 사실", facts_block) if r == 0
               else _sec("너의 수첩", note_prev or ""))
    return ("다음 사안을 검토하라.\n\n" + _sec("사안", _ACTIVE["stub"]) + "\n\n" + _stance_block(stance) +
            carrier + "\n\n" + _sec("이번 라운드에 쓴 글", essay_r) + "\n\n" + note_instr(budget))


def prompt_note_retry(over_text: str, budget: int) -> str:
    return (f"수첩이 {budget}자를 초과했다({len(over_text)}자). {budget}자 이내로 줄여 다시 써라. "
            f"수첩 본문만 출력하라.\n\n[직전 초과분]\n{over_text}")


def _carrier_sec(mem: str, facts_block: str, essays: list[str], note: str | None) -> str:
    if mem == "full":
        hist = "\n\n".join(f"[라운드 {i} 글]\n{t}" for i, t in enumerate(essays))
        return _sec("알게 된 사실", facts_block) + "\n\n" + _sec("지금까지 쓴 글", hist)
    if mem == "note":
        return _sec("너의 수첩", note or "")
    return _sec("직전에 쓴 글", essays[-1])


def prompt_recall(mem: str, facts_block: str, essays: list[str], note: str | None) -> str:
    return ("다음 사안을 검토하라.\n\n" + _sec("사안", _ACTIVE["stub"]) + "\n\n" +
            _carrier_sec(mem, facts_block, essays, note) + "\n\n" + RECALL_INSTR)


def prompt_final_poll(mem: str, facts_block: str, essays: list[str], note: str | None) -> str:
    return ("다음 사안을 검토하라.\n\n" + _sec("사안", _ACTIVE["stub"]) + "\n\n" +
            _carrier_sec(mem, facts_block, essays, note) + "\n\n" + _ACTIVE["final_poll"])


# ── 호출 계층 ────────────────────────────────────────────────────────────────

class CallGate:
    """호출 상한 + 체크포인트 + 원문 전량 보존. 실패는 조용히 넘기지 않는다."""

    def __init__(self, ckpt: Path, max_calls: int, obtain, dry: bool):
        self.ckpt, self.max_calls, self.obtain, self.dry = ckpt, max_calls, obtain, dry
        self.done: dict[str, str] = {}
        self.n_calls = 0
        if ckpt.exists():
            for line in ckpt.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self.done[row["tag"]] = row["response"]

    def call(self, tag: str, prompt: str) -> str:
        if tag in self.done:
            return self.done[tag]
        if self.n_calls >= self.max_calls:
            raise RuntimeError(f"호출 상한 {self.max_calls} 도달 — 중단 (체크포인트 보존)")
        text = f"[DRY {tag}]" if self.dry else self.obtain(prompt)
        self.n_calls += 1
        if not self.dry and not text.strip():
            # FALLBACK 공백 — PREREG §11: 런 폐기·재실행 대상. 체크포인트에 남기지 않고 즉사.
            raise RuntimeError(f"공백 응답(FALLBACK) — tag={tag}. 런 폐기·재실행 (PREREG §11)")
        row = {"tag": tag, "prompt": prompt, "response": text, "at": _now()}
        with self.ckpt.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.done[tag] = text
        return text


def make_hermes_obtain(model_label: str):
    """파일 왕복: pending/<tag>.txt 에 프롬프트를 쓰고 answers/<tag>.txt 를 기다린다.
    프로토콜 전문·금지 사항은 WORKORDER_HERMES.md — 헤르메스는 답 본문만 쓴다."""
    pend, ans = HERMES_DIR / "pending", HERMES_DIR / "answers"
    pend.mkdir(parents=True, exist_ok=True)
    ans.mkdir(parents=True, exist_ok=True)
    state = {"tag": None}

    def obtain(prompt: str) -> str:
        tag = state["tag"]
        req, res = pend / f"{tag}.txt", ans / f"{tag}.txt"
        if not res.exists():
            req.write_text(prompt, encoding="utf-8")
            print(f"[hermes] 대기 → {req.name} (모델 {model_label})")
        t0 = time.time()
        while not res.exists():
            if time.time() - t0 > HERMES_TIMEOUT_SEC:
                raise RuntimeError(f"헤르메스 응답 대기 초과({HERMES_TIMEOUT_SEC}s) — tag={tag}")
            time.sleep(HERMES_POLL_SEC)
        text = res.read_text(encoding="utf-8").strip()
        req.unlink(missing_ok=True)
        return text

    return obtain, state


# ── 런 하나 ──────────────────────────────────────────────────────────────────

def _variant_suffix(note_budget: int, facts_reverse: bool, stance: bool) -> str:
    parts = []
    if note_budget != DEFAULT_NOTE_BUDGET:
        parts.append(f"b{note_budget}")
    if facts_reverse:
        parts.append("rev")
    if not stance:
        parts.append("ns")
    return ("_" + "_".join(parts)) if parts else ""


def validate_execution_policy(*, promotion_tier: str = "confirmatory",
                              max_llm_calls: int | None = None,
                              aggregate_eligible: bool = True,
                              report_eligible: bool = True) -> dict:
    """실행 등급과 영구 라벨을 한 번에 검증한다.

    ``--max-calls``는 역사적으로 run 하나의 CallGate 상한이다. 이 함수의
    ``max_llm_calls``는 요청/tranche 전체 논리콜 상한이며 개발 파일럿에서는 반드시
    명시되고 30 이하여야 한다. 두 단위를 같은 값처럼 기록하지 않는다.
    """
    if promotion_tier not in {"confirmatory", "pilot_unvetted"}:
        raise SystemExit(f"지원하지 않는 promotion_tier: {promotion_tier}")
    if promotion_tier == "pilot_unvetted":
        if (not isinstance(max_llm_calls, int) or isinstance(max_llm_calls, bool)
                or max_llm_calls <= 0):
            raise SystemExit("pilot_unvetted requires positive max_llm_calls")
        if max_llm_calls > PILOT_CALL_LIMIT:
            raise SystemExit(
                f"pilot max_llm_calls={max_llm_calls} exceeds hard limit {PILOT_CALL_LIMIT}")
        if aggregate_eligible is not False or report_eligible is not False:
            raise SystemExit("pilot_unvetted must be aggregate/report ineligible")
    return {
        "promotion_tier": promotion_tier,
        "max_llm_calls": max_llm_calls,
        "aggregate_eligible": aggregate_eligible,
        "report_eligible": report_eligible,
    }


def _planned_call_ceiling(memories: list[str], arms: list[str], reps: list[int],
                          final_poll: bool) -> int:
    """요청 전체 최악 논리콜 수. note는 라운드별 반려 3회를 포함한다."""
    per_memory = sum(11 if mem == "note" else 5 for mem in memories)
    runs = len(arms) * len(reps) * len(memories)
    return per_memory * len(arms) * len(reps) + (runs if final_poll else 0)


def run_one(model_key: str, provider: str, arm: str, mem: str, rep: int,
            facts_block: str, max_calls: int, dry: bool,
            note_budget: int = DEFAULT_NOTE_BUDGET, facts_reverse: bool = False,
            stance: bool = True, final_poll: bool = False,
            issue_id: str = DEFAULT_ISSUE,
            promotion_tier: str = "confirmatory",
            max_llm_calls: int | None = None,
            aggregate_eligible: bool = True,
            report_eligible: bool = True) -> Path:
    execution_policy = validate_execution_policy(
        promotion_tier=promotion_tier, max_llm_calls=max_llm_calls,
        aggregate_eligible=aggregate_eligible, report_eligible=report_eligible)
    # 재료 불일치 관문 (2026-08-19 적대적 리뷰 치명 1) — _ACTIVE 는 모듈 전역이라
    # select_issue() 를 안 부르고 run_one 을 직접 부르면 **다른 재료의 팩트에 camp 사안문이
    # 붙은 채 조용히 돈다**. 산출물 meta 에는 issue_id 가 제대로 찍혀 나중에 못 알아챈다.
    # CLI 는 main() 이 select_issue 를 부르지만 import 해서 쓰는 도구가 걸린다.
    want = ISSUE_PROMPTS.get(issue_id)
    if want is None:
        raise SystemExit(f"[run_solo] 프롬프트 문면이 없는 이슈: {issue_id}")
    if _ACTIVE["stub"] != want["stub"] or _ACTIVE["stance"] not in want["stances"].values():
        raise SystemExit(
            f"[run_solo] 재료 불일치 — issue_id={issue_id} 인데 조립 문면이 그 재료의 것이 "
            f"아니다. run_one 전에 select_issue({issue_id!r}) 를 부르라.")

    suffix = _variant_suffix(note_budget, facts_reverse, stance)
    run_id = f"{arm}_{mem}{suffix}_rep{rep}"
    is_v2 = bool(suffix) or final_poll
    # 드라이런은 별도 폴더 — 실런이 드라이런 산출물을 "결과 존재"로 오인해 스킵하는 사고 방지
    out_dir = (RUNS_DIR / "_dry" if dry else RUNS_DIR) / model_key
    # 이슈별 분리 (2026-08-19) — run_id 에 이슈가 없어서, 안 나누면 다른 재료의 A_note_rep1 이
    # camp 것과 같은 파일명이 되어 "[skip] 결과 존재"로 조용히 아무것도 안 하게 된다.
    # camp 은 종전 경로 그대로 — 기존 54런 산출물의 자리가 안 바뀐다.
    if issue_id != DEFAULT_ISSUE:
        out_dir = out_dir / issue_id
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"run_{run_id}.json"
    if dst.exists():
        print(f"[skip] {model_key}/{run_id} — 결과 존재")
        return dst
    ckpt = out_dir / f"run_{run_id}.partial.jsonl"

    if provider == "hermes":
        obtain_fn, hstate = make_hermes_obtain(model_key)
        def obtain(p):  # noqa: E306
            return obtain_fn(p)
        temp_meta = "hermes:TBD-1"      # PREREG §4 — 민옥 기입 항목
    else:
        hstate = None
        def obtain(p):  # noqa: E306
            return llm.obtain_response(p, model=model_key, temperature=GEN_TEMPERATURE)
        temp_meta = GEN_TEMPERATURE

    gate = CallGate(ckpt, max_calls, obtain, dry)

    def call(tag: str, prompt: str) -> str:
        if hstate is not None:
            hstate["tag"] = f"{model_key}_{run_id}_{tag}"
        return gate.call(tag, prompt)

    essays: list[str] = []
    notes: list[str] = []
    note_truncated = False

    for r in range(ROUNDS):
        p = (prompt_r0(facts_block, stance) if r == 0
             else prompt_round(arm, mem, facts_block, essays,
                               notes[-1] if notes else None, stance))
        essays.append(call(f"essay_r{r}", p))
        if mem == "note" and r < ROUNDS - 1:
            note = call(f"note_r{r}", prompt_note(r, facts_block,
                                                  notes[-1] if notes else None, essays[-1],
                                                  stance, note_budget))
            if len(note) > note_budget:
                note = call(f"note_r{r}_retry", prompt_note_retry(note, note_budget))
                if len(note) > note_budget:
                    note, note_truncated = note[:note_budget], True   # PROMPTS_v1 §4
            notes.append(note)

    recall = call("recall", prompt_recall(mem, facts_block, essays,
                                          notes[-1] if notes else None))
    poll = (call("final_poll", prompt_final_poll(mem, facts_block, essays,
                                                 notes[-1] if notes else None))
            if final_poll else None)

    out = {
        "schema": "solo_run_v1", "issue_id": issue_id,
        "prompts_ver": (PROMPTS_VER_V2 if is_v2 else PROMPTS_VER_V1),
        "run_id": run_id, "arm": arm, "arm_name": ARMS[arm], "memory": mem, "rep": rep,
        "meta": {
            "model_key": model_key, "provider": provider,
            "model_id": (model_key if provider == "hermes" else llm.resolve_model(model_key)),
            "temperature": temp_meta, "rounds": ROUNDS, "note_budget": note_budget,
            "note_truncated": note_truncated, "dry": dry,
            "facts_order": ("reversed" if facts_reverse else "original"),
            "stance": stance, "final_poll": final_poll,
            **execution_policy,
            "deviations": list(getattr(llm, "LAST_DEVIATIONS", [])),
            "finished_at": _now(),
        },
        "essays": essays, "notes": notes, "recall": recall,
        "final_poll": poll,
    }
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] {model_key}/{run_id} · 호출 {gate.n_calls}")
    return dst


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    ap = argparse.ArgumentParser(description="기억 구조 1단 단독 러너 (PREREG_v1 / v2 손잡이)")
    ap.add_argument("--model", default="gpt", help="llm.py 모델 키 (hermes 면 라벨 겸 모델 ID)")
    ap.add_argument("--provider", default="api", choices=["api", "hermes"])
    ap.add_argument("--arms", nargs="*", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("--memories", nargs="*", default=list(MEMS), choices=list(MEMS))
    ap.add_argument("--reps", nargs="*", type=int, default=[1, 2, 3])
    ap.add_argument("--max-calls", type=int, default=60,
                    help="런 묶음 전체가 아니라 런 1개당 상한 (② 8콜 + 반려 여유)")
    ap.add_argument("--max-llm-calls", type=int, default=None,
                    help="요청/tranche 전체 논리콜 상한 (pilot_unvetted는 필수·30 이하)")
    ap.add_argument("--promotion-tier", default="confirmatory",
                    choices=["confirmatory", "pilot_unvetted"])
    ap.add_argument("--dry", action="store_true", help="0콜 조립 리허설")
    # v2 손잡이 (2026-08-18) — 기본값이면 v1과 문면·run_id 동일
    ap.add_argument("--note-budget", type=int, default=DEFAULT_NOTE_BUDGET,
                    help="수첩 예산(자). 500이면 v1 동일 (스윕: 250/125/60)")
    ap.add_argument("--facts-reverse", action="store_true", help="사실 목록 역순 (셔플 실험)")
    ap.add_argument("--no-stance", action="store_true", help="입장 고정 해제 (자 세우기 실험)")
    ap.add_argument("--final-poll", action="store_true",
                    help="라운드 종료 후 최종 판단 1필드 수집 (판정기 불사용, 원문 저장)")
    ap.add_argument("--allow-v2", action="store_true",
                    help="v2 조건 실호출 허용 — PROMPTS_v2·PREREG_v2 로컬 커밋 후에만 켤 것")
    # 이슈 손잡이 (2026-08-19) — 기본값이면 종전과 문면·경로 전부 동일
    ap.add_argument("--issue", default=DEFAULT_ISSUE, choices=sorted(ISSUE_PROMPTS),
                    help=f"재료 이슈 (기본 {DEFAULT_ISSUE}). camp 외에는 runs/<model>/<issue>/ 로 갈린다")
    ap.add_argument("--stance-key", default=None,
                    help="입장 대립형 재료에서 어느 입장으로 돌릴지 "
                         "(issue_polar: 후송|대기, issue_exile: 추방|잔류)")
    args = ap.parse_args()

    stance_key = select_issue(args.issue, args.stance_key)

    # 사전등록 관문 (2026-08-19 적대적 리뷰 치명 2 반영) — 종전엔 예산 한 칸 바꾸는 것은
    # 막으면서 **PREREG_v1 에 없는 재료로 도는 것은 안 막았다**. 관문의 취지는 "사전등록에
    # 없는 조건으로 실호출이 나가지 않게"이고, 새 재료는 예산 변경보다 더 먼 조건이다.
    is_v2 = (args.note_budget != DEFAULT_NOTE_BUDGET or args.facts_reverse
             or args.no_stance or args.final_poll or args.issue != DEFAULT_ISSUE)
    if is_v2 and not args.dry and not args.allow_v2:
        raise SystemExit("사전등록 밖 조건 실호출 차단: 해당 사전등록 문서를 커밋한 뒤 "
                         "--allow-v2 로 실행하라 (--dry 는 상한 없이 허용).")
    if args.final_poll and not args.no_stance:
        raise SystemExit("--final-poll 은 --no-stance 와 함께 써라 — 입장 고정 상태의 최종 판단은 "
                         "결론이 설계상 고정이라 측정이 무의미하다 (§6 1단계 정정 참조).")

    pilot = args.promotion_tier == "pilot_unvetted"
    execution_policy = validate_execution_policy(
        promotion_tier=args.promotion_tier,
        max_llm_calls=args.max_llm_calls,
        aggregate_eligible=not pilot,
        report_eligible=not pilot,
    )
    planned_ceiling = _planned_call_ceiling(
        args.memories, args.arms, args.reps, args.final_poll)
    if pilot and planned_ceiling > args.max_llm_calls:
        raise SystemExit(
            f"pilot planned logical calls {planned_ceiling} exceed "
            f"max_llm_calls={args.max_llm_calls}")

    if not args.dry and args.provider == "api":
        llm.preflight(args.model, temperature=GEN_TEMPERATURE)

    facts_block = load_facts_block(reverse=args.facts_reverse, issue_id=args.issue)
    planned = [(a, m, r) for a in args.arms for m in args.memories for r in args.reps]
    print(f"[plan] {args.issue} · 입장 {stance_key} · {args.model} ({args.provider}) — "
          f"{len(planned)}런 · dry={args.dry}" + (" · v2" if is_v2 else ""))
    per_run_cap = (min(args.max_calls, args.max_llm_calls) if pilot else args.max_calls)
    for a, m, r in planned:
        run_one(args.model, args.provider, a, m, r, facts_block, per_run_cap, args.dry,
                note_budget=args.note_budget, facts_reverse=args.facts_reverse,
                stance=not args.no_stance, final_poll=args.final_poll,
                issue_id=args.issue, **execution_policy)


if __name__ == "__main__":
    main()
