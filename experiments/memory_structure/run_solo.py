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

사용례:
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --dry                 # 0콜 조립 리허설(전 81런)
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --model gpt --reps 1  # GPT rep1 (9런 54콜)
  PYTHONUTF8=1 python experiments/memory_structure/run_solo.py --provider hermes --model claude-hermes --reps 1
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

ISSUE_ID = "issue_camp"
PROMPTS_VER = "solo-v1"          # PROMPTS_v1.md
ROUNDS = 4                        # r0~r3
NOTE_BUDGET = 500                 # 자(파이썬 len, 공백·문장부호 포함)
GEN_TEMPERATURE = 0.7             # PREREG §4 (API 두 팔. hermes 는 TBD-1 — meta 에 문자열 기록)
HERMES_POLL_SEC = 5
HERMES_TIMEOUT_SEC = 3600

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


def instr(arm: str, mem: str) -> str:
    return INSTR[arm].replace("{REF}", MEM_REF[mem])

NOTE_INSTR = ("다음 라운드의 너는 지금 화면에 보이는 내용을 더 이상 보지 못하고, 네가 지금 "
              "남기는 수첩만 보게 된다. 수첩은 다음 라운드로 이월되는 유일한 기억이다. "
              "다음 라운드의 너에게 남길 수첩을 500자 이내로 써라. 수첩 본문만 출력하라.")

RECALL_INSTR = ("이 사안과 관련해 네가 알고 있는 구체적 사실을 빠짐없이 목록으로 적어라. "
                "확실하지 않은 것은 적지 마라. 목록만 출력하라.")


def load_facts_block() -> str:
    doc = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))
    return "\n".join("- " + f["text"] for f in doc["facts"])  # ID 미노출 (중대 15)


def _sec(title: str, body: str) -> str:
    return f"[{title}]\n{body}"


def prompt_r0(facts_block: str) -> str:
    return ("다음 사안을 검토하라.\n\n" + _sec("사안", STUB) + "\n\n" +
            _sec("알게 된 사실", facts_block) + "\n\n" + STANCE +
            "\n\n위 사안에 대한 너의 입장을 밝히는 글을 한 문단으로 써라. 글 본문만 출력하라.")


def prompt_round(arm: str, mem: str, facts_block: str, essays: list[str],
                 note: str | None) -> str:
    head = "다음 사안을 검토하라.\n\n" + _sec("사안", STUB) + "\n\n"
    if mem == "full":
        hist = "\n\n".join(f"[라운드 {i} 글]\n{t}" for i, t in enumerate(essays))
        mid = _sec("알게 된 사실", facts_block) + "\n\n" + STANCE + "\n\n" + \
              _sec("지금까지 쓴 글", hist)
    elif mem == "note":
        mid = STANCE + "\n\n" + _sec("너의 수첩", note or "")
    else:  # prev
        mid = STANCE + "\n\n" + _sec("직전에 쓴 글", essays[-1])
    return head + mid + "\n\n" + instr(arm, mem) + " 글 본문만 출력하라."


def prompt_note(r: int, facts_block: str, note_prev: str | None, essay_r: str) -> str:
    carrier = (_sec("알게 된 사실", facts_block) if r == 0
               else _sec("너의 수첩", note_prev or ""))
    return ("다음 사안을 검토하라.\n\n" + _sec("사안", STUB) + "\n\n" + STANCE + "\n\n" +
            carrier + "\n\n" + _sec("이번 라운드에 쓴 글", essay_r) + "\n\n" + NOTE_INSTR)


def prompt_note_retry(over_text: str) -> str:
    return (f"수첩이 500자를 초과했다({len(over_text)}자). 500자 이내로 줄여 다시 써라. "
            f"수첩 본문만 출력하라.\n\n[직전 초과분]\n{over_text}")


def prompt_recall(mem: str, facts_block: str, essays: list[str], note: str | None) -> str:
    if mem == "full":
        hist = "\n\n".join(f"[라운드 {i} 글]\n{t}" for i, t in enumerate(essays))
        carrier = _sec("알게 된 사실", facts_block) + "\n\n" + _sec("지금까지 쓴 글", hist)
    elif mem == "note":
        carrier = _sec("너의 수첩", note or "")
    else:
        carrier = _sec("직전에 쓴 글", essays[-1])
    return ("다음 사안을 검토하라.\n\n" + _sec("사안", STUB) + "\n\n" + carrier +
            "\n\n" + RECALL_INSTR)


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

def run_one(model_key: str, provider: str, arm: str, mem: str, rep: int,
            facts_block: str, max_calls: int, dry: bool) -> Path:
    run_id = f"{arm}_{mem}_rep{rep}"
    # 드라이런은 별도 폴더 — 실런이 드라이런 산출물을 "결과 존재"로 오인해 스킵하는 사고 방지
    out_dir = (RUNS_DIR / "_dry" if dry else RUNS_DIR) / model_key
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
        p = (prompt_r0(facts_block) if r == 0
             else prompt_round(arm, mem, facts_block, essays,
                               notes[-1] if notes else None))
        essays.append(call(f"essay_r{r}", p))
        if mem == "note" and r < ROUNDS - 1:
            note = call(f"note_r{r}", prompt_note(r, facts_block,
                                                  notes[-1] if notes else None, essays[-1]))
            if len(note) > NOTE_BUDGET:
                note = call(f"note_r{r}_retry", prompt_note_retry(note))
                if len(note) > NOTE_BUDGET:
                    note, note_truncated = note[:NOTE_BUDGET], True   # PROMPTS_v1 §4
            notes.append(note)

    recall = call("recall", prompt_recall(mem, facts_block, essays,
                                          notes[-1] if notes else None))

    out = {
        "schema": "solo_run_v1", "issue_id": ISSUE_ID, "prompts_ver": PROMPTS_VER,
        "run_id": run_id, "arm": arm, "arm_name": ARMS[arm], "memory": mem, "rep": rep,
        "meta": {
            "model_key": model_key, "provider": provider,
            "model_id": (model_key if provider == "hermes" else llm.resolve_model(model_key)),
            "temperature": temp_meta, "rounds": ROUNDS, "note_budget": NOTE_BUDGET,
            "note_truncated": note_truncated, "dry": dry,
            "deviations": list(getattr(llm, "LAST_DEVIATIONS", [])),
            "finished_at": _now(),
        },
        "essays": essays, "notes": notes, "recall": recall,
    }
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] {model_key}/{run_id} · 호출 {gate.n_calls}")
    return dst


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    ap = argparse.ArgumentParser(description="기억 구조 1단 단독 러너 (PREREG_v1)")
    ap.add_argument("--model", default="gpt", help="llm.py 모델 키 (hermes 면 라벨 겸 모델 ID)")
    ap.add_argument("--provider", default="api", choices=["api", "hermes"])
    ap.add_argument("--arms", nargs="*", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("--memories", nargs="*", default=list(MEMS), choices=list(MEMS))
    ap.add_argument("--reps", nargs="*", type=int, default=[1, 2, 3])
    ap.add_argument("--max-calls", type=int, default=60,
                    help="런 묶음 전체가 아니라 런 1개당 상한 (② 8콜 + 반려 여유)")
    ap.add_argument("--dry", action="store_true", help="0콜 조립 리허설")
    args = ap.parse_args()

    if not args.dry and args.provider == "api":
        llm.preflight(args.model, temperature=GEN_TEMPERATURE)

    facts_block = load_facts_block()
    planned = [(a, m, r) for a in args.arms for m in args.memories for r in args.reps]
    print(f"[plan] {args.model} ({args.provider}) — {len(planned)}런"
          f" · dry={args.dry}")
    for a, m, r in planned:
        run_one(args.model, args.provider, a, m, r, facts_block, args.max_calls, args.dry)


if __name__ == "__main__":
    main()
