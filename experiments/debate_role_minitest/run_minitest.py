"""[민옥 트랙 · 토론 배역 미니테스트] 2인 맞토론 러너 — 배역(natural/stubborn/advance) × 2모델.

지시문: WORKORDER_2026-08-19.md (이 폴더 — 프롬프트 축자 정본. 불일치 시 지시문이 정본).
확장(MT2): WORKORDER2_2026-08-19.md — revision 팔(수정형 장르, 각 2런) + nostance 실행.
  revision = 양측 입장 고정·배역 없음. 첫 발화(S0·O0)만 성명서형(고칠 직전 글이 없음),
  이후(S1~S3·O1~O2)는 입장 문장 그대로 두고 마지막 지시만 수정형으로 교체.
  실행: --mt2 (revision×2모델×각2런 + nostance×2모델×각1런 = 6판 42콜).
확장(MT3): WORKORDER3_2026-08-19.md — 기억 축의 토론 진입(수첩 vs 직전, 각 2런).
  r0만 사실 12개 전문(1호 natural 화면과 동일 — "MT2 natural과 동일" 조항), r1 이후 화면은
  [사안]+(note:[너의 수첩]/prev:[직전에 네가 쓴 글])+[상대의 직전 글]+입장+기억 중립형 수정
  지시. 수첩 갱신=매 발화 직후 별도 콜(PROMPTS_v1 §4 축자 — 500자·1회 반려·재초과 절단),
  수첩 화면=방금 그 발화 화면+[이번 라운드에 쓴 글]. 실행: --mt3 (8판 84콜, 상한 128).
지위: 탐색 미니테스트 — 사전등록 없음, n=1~2/셀, 결과 수치는 어떤 주장의 증거로도 인용 금지.

왜 독립 스크립트인가 (지시문 §3 판단 기준 이행, 2026-08-19 확인):
  modules/debate_engine.py 의 persona 슬롯은 저자 저장소(DelibTrace) settings 파일의
  사전 정의 텍스트를 읽는 구조(debate_engine.py:365 · authors_prompts.load_settings)이고,
  화면도 저자 프롬프트(authors_prompts) 기반이다. 이 미니테스트가 요구하는
  PROMPTS_v1 화면 + [지금까지의 토론] 칸 + 축자 배역 문구 + 2인 교대(S/O, O3 생략)는
  그 구조로 재현할 수 없다. 엔진을 고쳐 맞추는 것은 규약 5(파일 소유권) 위반 —
  독립 스크립트로 간다. modules/llm.py 는 읽기 전용 재사용, 경로는 modules/paths.py.

구조 (지시문 §1): 2인 맞토론, 4라운드 교대, 피험자(S) 선발화.
  S0 → O0 → S1 → O1 → S2 → O2 → S3  (O3 생략 — 어떤 지표의 입력도 아님)
  판당 생성 7콜. 기본 6판(natural/stubborn/advance × gpt-mini/gemini-flash) = 42콜.
  (지시문 표의 "48콜"은 판당 8콜 셈 — O3 생략 조항이 우선하므로 실제는 판당 7콜.)
  nostance(선택 팔)는 구현만 해 둔다 — 민옥이 원하면 --arms nostance 로 실행.

조립 규칙: PROMPTS_v1 §6 계승 — 블록 사이 빈 줄 1개, 축자 문면 밖 텍스트 추가 없음,
  system 메시지 없음(user 단일 채널). 상대 배역 문구는 STANCE 문장 다음 줄에 잇는다
  (지시문 "(natural 문구에 더해)" — 같은 블록 안 줄바꿈 연결).
  [지금까지의 토론]: 첫 발화면 "아직 없음", 이후 화자 관점의 "나:"/"상대:" 라벨로
  시간순 전문, 발화 블록 사이 빈 줄 1개.

규율(CLAUDE.md): 호출 상한 총 64콜(지시문 축자, 신규 호출 기준 즉사) · 호출 단위
  체크포인트(.partial.jsonl 재개) · 프롬프트/응답 원문 전량 보존(요약 저장 금지) ·
  공백 응답 즉사(재실행 대상) · 경로는 paths.py · 판정기(judge) 불사용.

사용례:
  PYTHONUTF8=1 python experiments/debate_role_minitest/run_minitest.py --dry   # 0콜 조립 리허설
  PYTHONUTF8=1 python experiments/debate_role_minitest/run_minitest.py         # 본 6판 42콜
  PYTHONUTF8=1 python experiments/debate_role_minitest/run_minitest.py --arms nostance  # 선택 팔
  PYTHONUTF8=1 python experiments/debate_role_minitest/run_minitest.py --mt2 --dry      # MT2 리허설
  PYTHONUTF8=1 python experiments/debate_role_minitest/run_minitest.py --mt2            # MT2 6판 42콜
  PYTHONUTF8=1 python experiments/debate_role_minitest/run_minitest.py --mt3 --dry      # MT3 리허설
  PYTHONUTF8=1 python experiments/debate_role_minitest/run_minitest.py --mt3            # MT3 8판 84콜
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from modules import llm  # noqa: E402
from modules import paths  # noqa: E402

ISSUE_ID = "issue_camp"
PROMPTS_VER = "debate-role-minitest-v1"   # 정본 = WORKORDER_2026-08-19.md §2
ROUNDS = 4
GEN_TEMPERATURE = 0.7                     # 본실험과 동일 (지시문 §1)
MAX_TOTAL_CALLS = 64                      # 지시문 축자 — 전 판 합산 신규 호출 상한

HERE = Path(__file__).resolve().parent
RUNS_DIR = HERE / "runs"

MODELS = ("gpt-mini", "gemini-flash")     # llm.py 별칭 → gpt-5.4-mini / gemini-3-flash-preview
ARMS = ("natural", "stubborn", "advance", "nostance", "revision")
DEFAULT_ARMS = ("natural", "stubborn", "advance")   # 1호 기본 팔 (완주분 — 재실행 시 [skip])
MT2_REVISION_RUNS = 2                     # WORKORDER2 §1: revision 은 모델당 2런

MT3_ARMS = ("note", "prev")               # WORKORDER3 §1: 기억 축 (별도 콜 구성이라 ARMS 밖)
MT3_RUNS = 2                              # 모델당 2런
MT3_MAX_TOTAL_CALLS = 128                 # WORKORDER3 §1 축자 (본 84콜 + 수첩 반려 여지)
NOTE_BUDGET = 500                         # PROMPTS_v1 §4 (파이썬 len, 공백·문장부호 포함)

# ── 프롬프트 축자 (WORKORDER §2 미러 — 수정 금지. 화면은 PROMPTS_v1 §1 계승) ──

STUB = ("대학 연합 동아리(회원 33명)의 가을 합숙지를 다림재 수련원과 무레온 캠프 중 "
        "한 곳으로 정하는 문제를 논의 중이다. 총회가 의결한 조건은 네 가지다. "
        "① 1인당 42,000원 이하 ② 35인 이상 실내 공간 ③ 10월 17~18일 예약 가능 "
        "④ 배상책임보험 가입 시설.")

STANCE_SUBJ = "너의 입장은 '무레온 캠프로 가야 한다'이다. 이 입장은 끝까지 유지한다."
STANCE_OPP = "너의 입장은 '다림재 수련원으로 가야 한다'이다. 이 입장은 끝까지 유지한다."

ROLE_EXTRA = {
    "natural": None,
    "stubborn": ("첫 라운드에 네가 낸 논거 하나를 정하고, 이후 라운드에는 그 논거만 "
                 "표현을 다듬어 다시 주장하라. 새로운 논거나 새로운 사실을 꺼내지 마라."),
    "advance": ("매 라운드, 이전 라운드까지 나오지 않은 새로운 논거로 너의 입장을 "
                "주장하라. 같은 논거를 반복하지 마라."),
    "nostance": None,
    "revision": None,                     # WORKORDER2: 배역 없음 — 장르만 다르다
}

TASK_STANCE = "위 사안에 대한 너의 입장을 밝히는 글을 한 문단으로 써라. 글 본문만 출력하라."
TASK_NOSTANCE = ("위 사안을 검토하고, 두 후보 중 어느 쪽이 좋다고 판단하는지 너의 판단을 "
                 "밝히는 글을 한 문단으로 써라. 글 본문만 출력하라.")
TASK_REVISION = ("상대의 글을 참고하여, 직전에 네가 쓴 글을 고쳐 써라. "
                 "고쳐 쓴 글 본문만 출력하라.")   # WORKORDER2 §2 축자 — S1~S3·O1~O2 만

# ── MT3 축자 (WORKORDER3 §2 — 기억 중립형 수정 지시 + PROMPTS_v1 §4 수첩 계승) ──

TASK_MT3 = "상대의 글을 참고하여, 너의 글을 고쳐 써라. 고쳐 쓴 글 본문만 출력하라."
MT3_MEM_LABEL = {"note": "너의 수첩", "prev": "직전에 네가 쓴 글"}

NOTE_INSTR = ("다음 라운드의 너는 지금 화면에 보이는 내용을 더 이상 보지 못하고, 네가 지금 "
              "남기는 수첩만 보게 된다. 수첩은 다음 라운드로 이월되는 유일한 기억이다. "
              f"다음 라운드의 너에게 남길 수첩을 {NOTE_BUDGET}자 이내로 써라. "
              "수첩 본문만 출력하라.")            # PROMPTS_v1 §4 축자 (budget=500)


def note_retry_prompt(over_text: str) -> str:
    """수첩 반려 축자 — run_solo.prompt_note_retry 계승 (PROMPTS_v1 §4 집행 규칙)."""
    return (f"수첩이 {NOTE_BUDGET}자를 초과했다({len(over_text)}자). "
            f"{NOTE_BUDGET}자 이내로 줄여 다시 써라. "
            f"수첩 본문만 출력하라.\n\n[직전 초과분]\n{over_text}")


def load_facts_block() -> str:
    """facts JSON 정본에서 text 만, 파일 순서 그대로, ID 미노출 (run_solo 계승)."""
    doc = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))
    return "\n".join("- " + f["text"] for f in doc["facts"])


def stance_block(speaker: str, arm: str) -> str | None:
    """화자의 입장(+배역) 블록. nostance 팔은 양측 모두 입장 문장 없음."""
    if arm == "nostance":
        return None
    if speaker == "S":
        return STANCE_SUBJ
    extra = ROLE_EXTRA[arm]
    return STANCE_OPP if extra is None else STANCE_OPP + "\n" + extra


def history_block(history: list[tuple[str, str]], viewer: str) -> str:
    """[지금까지의 토론] 본문 — viewer 관점의 나/상대 라벨, 시간순 전문."""
    if not history:
        return "아직 없음"
    return "\n\n".join(("나: " if spk == viewer else "상대: ") + text
                       for spk, text in history)


def task_line(arm: str, rnd: int) -> str:
    """마지막 지시문. revision 은 첫 발화(r0)만 성명서형 — 고칠 직전 글이 없기 때문
    (WORKORDER2 §2). 입장 문장·화면 구조는 그대로, 이 줄만 교체된다."""
    if arm == "nostance":
        return TASK_NOSTANCE
    if arm == "revision" and rnd >= 1:
        return TASK_REVISION
    return TASK_STANCE


def build_prompt(speaker: str, arm: str, facts_block: str,
                 history: list[tuple[str, str]], rnd: int) -> str:
    parts = ["다음 사안을 검토하라.",
             f"[사안]\n{STUB}",
             f"[알게 된 사실]\n{facts_block}"]
    sb = stance_block(speaker, arm)
    if sb is not None:
        parts.append(sb)
    parts.append(f"[지금까지의 토론]\n{history_block(history, speaker)}")
    parts.append(task_line(arm, rnd))
    return "\n\n".join(parts)


# ── MT3 화면 조립 (WORKORDER3 §2) ────────────────────────────────────────────

def mt3_context(speaker: str, mem: str, facts_block: str, rnd: int,
                history: list[tuple[str, str]], my_note: str | None) -> list[str]:
    """발화 화면의 지시 줄 앞까지 — 수첩 갱신 화면이 이 블록들을 그대로 재사용한다
    (WORKORDER3: 수첩 갱신 화면 = 방금 그 발화 화면 + 자기 방금 쓴 글).
    r0 = 1호 natural 화면과 동일(사실 12개 전문 + [지금까지의 토론]).
    r1 이후 = [사안] + 기억 블록 + [상대의 직전 글] + 입장 (지시서 명시 순서)."""
    stance = STANCE_SUBJ if speaker == "S" else STANCE_OPP
    if rnd == 0:
        return ["다음 사안을 검토하라.",
                f"[사안]\n{STUB}",
                f"[알게 된 사실]\n{facts_block}",
                stance,
                f"[지금까지의 토론]\n{history_block(history, speaker)}"]
    if mem == "note":
        mem_block = f"[{MT3_MEM_LABEL['note']}]\n{my_note or ''}"
    else:
        my_prev = next(t for spk, t in reversed(history) if spk == speaker)
        mem_block = f"[{MT3_MEM_LABEL['prev']}]\n{my_prev}"
    opp_prev = next(t for spk, t in reversed(history) if spk != speaker)
    return ["다음 사안을 검토하라.",
            f"[사안]\n{STUB}",
            mem_block,
            f"[상대의 직전 글]\n{opp_prev}",
            stance]


def mt3_utterance_prompt(speaker: str, mem: str, facts_block: str, rnd: int,
                         history: list[tuple[str, str]], my_note: str | None) -> str:
    task = TASK_STANCE if rnd == 0 else TASK_MT3
    return "\n\n".join(mt3_context(speaker, mem, facts_block, rnd, history, my_note)
                       + [task])


def mt3_note_prompt(speaker: str, facts_block: str, rnd: int,
                    history_before: list[tuple[str, str]], my_note: str | None,
                    essay: str) -> str:
    """수첩 갱신 화면 — 방금 그 발화 화면(지시 줄 제외) + [이번 라운드에 쓴 글] + 수첩 지시."""
    return "\n\n".join(
        mt3_context(speaker, "note", facts_block, rnd, history_before, my_note)
        + [f"[이번 라운드에 쓴 글]\n{essay}", NOTE_INSTR])


# ── 호출 계층 (run_solo.CallGate 계승 — 전역 상한판) ─────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GlobalGate:
    """전 판 합산 호출 상한 + 판 단위 체크포인트 + 원문 전량 보존."""

    def __init__(self, max_calls: int, dry: bool):
        self.max_calls, self.dry = max_calls, dry
        self.n_calls = 0
        self.ckpt: Path | None = None
        self.done: dict[str, dict] = {}

    def open_run(self, ckpt: Path) -> None:
        self.ckpt, self.done = ckpt, {}
        if ckpt.exists():
            for line in ckpt.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self.done[row["tag"]] = row

    def call(self, tag: str, prompt: str, model_key: str) -> dict:
        if tag in self.done:
            print(f"  [ckpt] {tag} — 체크포인트 재사용")
            return self.done[tag]
        if self.n_calls >= self.max_calls:
            raise SystemExit(f"[ABORT] 호출 상한 {self.max_calls} 도달 — 중단 (체크포인트 보존)")
        if self.dry:
            text = f"[DRY {tag}]"
        else:
            text = llm.obtain_response(prompt, model=model_key,
                                       temperature=GEN_TEMPERATURE)
        self.n_calls += 1
        if not self.dry and not text.strip():
            # FALLBACK 공백 — 지시문·CLAUDE.md: 중단·재실행 (체크포인트에 남기지 않는다)
            raise RuntimeError(f"공백 응답(FALLBACK) — tag={tag}. 중단·재실행 대상")
        row = {"tag": tag, "prompt": prompt, "response": text, "at": _now()}
        with self.ckpt.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.done[tag] = row
        return row


# ── 판 하나 ──────────────────────────────────────────────────────────────────

def run_one(arm: str, model_key: str, facts_block: str, gate: GlobalGate,
            dry: bool, run_idx: int | None = None) -> Path:
    run_id = f"{arm}_{model_key.replace('-', '')}"
    if run_idx is not None:               # revision 팔: 모델당 2런 (WORKORDER2 §1)
        run_id += f"_run{run_idx}"
    out_dir = (RUNS_DIR / "_dry") if dry else RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"debate_{run_id}.jsonl"
    if dst.exists():
        print(f"[skip] {run_id} — 결과 존재")
        return dst
    ckpt = out_dir / f"debate_{run_id}.partial.jsonl"
    gate.open_run(ckpt)

    events: list[dict] = [{
        "event": "run_meta", "run_id": run_id, "ts": _now(),
        "issue_id": ISSUE_ID, "prompts_ver": PROMPTS_VER, "arm": arm,
        "model_key": model_key, "model_id": llm.resolve_model(model_key),
        "temperature": GEN_TEMPERATURE, "rounds": ROUNDS,
        "order": "S0 O0 S1 O1 S2 O2 S3 (O3 생략)", "dry": dry,
        "subject_stance": (None if arm == "nostance" else "무레온"),
        "opponent_stance": (None if arm == "nostance" else "다림재"),
        "opponent_role": ("none" if arm == "revision" else arm),
        "genre": ("revision" if arm == "revision" else "statement"),  # MT2 추가 필드
        "run_idx": run_idx,
    }]
    history: list[tuple[str, str]] = []   # (speaker, text) 시간순

    for r in range(ROUNDS):
        for speaker in ("S", "O"):
            if speaker == "O" and r == ROUNDS - 1:
                continue                  # O3 생략 (지시문 §1)
            tag = f"{speaker}{r}"
            prompt = build_prompt(speaker, arm, facts_block, history, r)
            row = gate.call(tag, prompt, model_key)
            history.append((speaker, row["response"]))
            events.append({
                "event": "utterance", "run_id": run_id, "round": r,
                "speaker": speaker,
                "role": (arm if speaker == "O" and ROLE_EXTRA[arm] else None),
                "task": ("revise" if arm == "revision" and r >= 1 else "statement"),
                "model_key": model_key, "model_id": llm.resolve_model(model_key),
                "temperature": GEN_TEMPERATURE,
                "prompt": prompt, "response": row["response"], "ts": row["at"],
            })

    events[0]["deviations"] = list(getattr(llm, "LAST_DEVIATIONS", []))
    with dst.open("w", encoding="utf-8") as fp:
        for rec in events:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
    ckpt.unlink(missing_ok=True)          # 완주 — 원문은 전부 dst 에 있다
    print(f"[done] {run_id} · 신규 호출 누계 {gate.n_calls}")
    return dst


def run_one_mt3(mem: str, model_key: str, facts_block: str, gate: GlobalGate,
                dry: bool, run_idx: int) -> Path:
    """MT3 판 하나 — 기억 축(note/prev) 2인 토론. note 팔은 매 발화 직후 수첩 콜.

    콜 순서(note): S0 → S0수첩 → O0 → O0수첩 → S1 → S1수첩 → … → S3 → S3수첩
    (O3 생략이라 O 수첩은 O0~O2 3개, S 수첩은 S0~S3 4개 — 마지막 2개는 측정용).
    수첩 원문 전량 보존: note 이벤트에 1차 prompt/response + 반려(retry) 원문 + 채택본(adopted).
    """
    run_id = f"{mem}_{model_key.replace('-', '')}_run{run_idx}"
    out_dir = (RUNS_DIR / "_dry") if dry else RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"debate_{run_id}.jsonl"
    if dst.exists():
        print(f"[skip] {run_id} — 결과 존재")
        return dst
    ckpt = out_dir / f"debate_{run_id}.partial.jsonl"
    gate.open_run(ckpt)

    events: list[dict] = [{
        "event": "run_meta", "run_id": run_id, "ts": _now(),
        "issue_id": ISSUE_ID, "prompts_ver": "debate-mt3-v1", "arm": mem,
        "memory": mem, "model_key": model_key, "model_id": llm.resolve_model(model_key),
        "temperature": GEN_TEMPERATURE, "rounds": ROUNDS,
        "order": "S0 O0 S1 O1 S2 O2 S3 (O3 생략) · note 팔은 각 발화 직후 수첩 콜",
        "dry": dry, "subject_stance": "무레온", "opponent_stance": "다림재",
        "opponent_role": "none", "genre": "revision-neutral",
        "note_budget": (NOTE_BUDGET if mem == "note" else None), "run_idx": run_idx,
    }]
    history: list[tuple[str, str]] = []
    notes: dict[str, list[str]] = {"S": [], "O": []}   # 채택 수첩(시간순)

    for r in range(ROUNDS):
        for speaker in ("S", "O"):
            if speaker == "O" and r == ROUNDS - 1:
                continue                  # O3 생략
            hist_before = list(history)
            my_note = (notes[speaker][-1]
                       if mem == "note" and notes[speaker] else None)
            prompt = mt3_utterance_prompt(speaker, mem, facts_block, r,
                                          hist_before, my_note)
            row = gate.call(f"{speaker}{r}", prompt, model_key)
            history.append((speaker, row["response"]))
            events.append({
                "event": "utterance", "run_id": run_id, "round": r,
                "speaker": speaker, "role": None,
                "task": ("statement" if r == 0 else "revise"),
                "model_key": model_key, "model_id": llm.resolve_model(model_key),
                "temperature": GEN_TEMPERATURE,
                "prompt": prompt, "response": row["response"], "ts": row["at"],
            })
            if mem != "note":
                continue
            nprompt = mt3_note_prompt(speaker, facts_block, r, hist_before,
                                      my_note, row["response"])
            nrow = gate.call(f"{speaker}{r}.note", nprompt, model_key)
            adopted, retry_ev, truncated = nrow["response"], None, False
            if len(adopted) > NOTE_BUDGET:      # PROMPTS_v1 §4: 1회 반려 → 절단
                rrow = gate.call(f"{speaker}{r}.note_retry",
                                 note_retry_prompt(adopted), model_key)
                retry_ev = {"prompt": rrow["prompt"], "response": rrow["response"],
                            "ts": rrow["at"]}
                adopted = rrow["response"]
                if len(adopted) > NOTE_BUDGET:
                    adopted, truncated = adopted[:NOTE_BUDGET], True
            notes[speaker].append(adopted)
            events.append({
                "event": "note", "run_id": run_id, "round": r, "speaker": speaker,
                "model_key": model_key, "model_id": llm.resolve_model(model_key),
                "temperature": GEN_TEMPERATURE,
                "prompt": nprompt, "response": nrow["response"],
                "retry": retry_ev, "adopted": adopted, "truncated": truncated,
                "ts": nrow["at"],
            })

    events[0]["deviations"] = list(getattr(llm, "LAST_DEVIATIONS", []))
    with dst.open("w", encoding="utf-8") as fp:
        for rec in events:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
    ckpt.unlink(missing_ok=True)
    print(f"[done] {run_id} · 신규 호출 누계 {gate.n_calls}")
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description="토론 배역 미니테스트 러너 (WORKORDER 2026-08-19 · WORKORDER2)")
    ap.add_argument("--arms", nargs="*", default=list(DEFAULT_ARMS), choices=list(ARMS))
    ap.add_argument("--models", nargs="*", default=list(MODELS), choices=list(MODELS))
    ap.add_argument("--mt2", action="store_true",
                    help="WORKORDER2 계획: revision×2모델×각2런 + nostance×2모델×각1런")
    ap.add_argument("--mt3", action="store_true",
                    help="WORKORDER3 계획: {note,prev}×2모델×각2런 (84콜, 상한 128)")
    ap.add_argument("--dry", action="store_true", help="0콜 조립 리허설 (runs/_dry/)")
    args = ap.parse_args()
    if args.mt2 and args.mt3:
        raise SystemExit("[ABORT] --mt2 와 --mt3 는 동시 지정 불가 — 따로 실행하라")

    if not args.dry:
        for m in args.models:
            llm.preflight(m, temperature=GEN_TEMPERATURE)

    facts_block = load_facts_block()
    per_utt = ROUNDS * 2 - 1              # 판당 발화 콜 (O3 생략 = 7)

    if args.mt3:                          # 기억 축 — 콜 구성이 달라 별도 러너 경로
        planned3 = [(mem, m, i + 1) for mem in MT3_ARMS for m in args.models
                    for i in range(MT3_RUNS)]
        n_calls = sum(per_utt * 2 if mem == "note" else per_utt
                      for mem, _, _ in planned3)
        print(f"[plan] MT3 {len(planned3)}판 (note 판 {per_utt}+{per_utt}콜 · "
              f"prev 판 {per_utt}콜) = {n_calls}콜 "
              f"(상한 {MT3_MAX_TOTAL_CALLS}, 수첩 반려 시 +1/건) · dry={args.dry}")
        for m in args.models:
            print(f"  모델 {m} → {llm.resolve_model(m)}")
        gate = GlobalGate(MT3_MAX_TOTAL_CALLS, args.dry)
        for mem, model_key, run_idx in planned3:
            run_one_mt3(mem, model_key, facts_block, gate, args.dry, run_idx)
        print(f"[end] 신규 호출 합계 {gate.n_calls}")
        return

    if args.mt2:                          # (arm, model, run_idx) — revision 만 run_idx 부여
        planned = [("revision", m, i + 1) for m in args.models
                   for i in range(MT2_REVISION_RUNS)]
        planned += [("nostance", m, None) for m in args.models]
    else:
        planned = [(a, m, None) for a in args.arms for m in args.models]
    print(f"[plan] {len(planned)}판 × 판당 {per_utt}콜 = {len(planned) * per_utt}콜 "
          f"(상한 {MAX_TOTAL_CALLS}) · dry={args.dry}")
    for m in args.models:
        print(f"  모델 {m} → {llm.resolve_model(m)}")
    gate = GlobalGate(MAX_TOTAL_CALLS, args.dry)
    for arm, model_key, run_idx in planned:
        run_one(arm, model_key, facts_block, gate, args.dry, run_idx=run_idx)
    print(f"[end] 신규 호출 합계 {gate.n_calls}")


if __name__ == "__main__":
    main()
