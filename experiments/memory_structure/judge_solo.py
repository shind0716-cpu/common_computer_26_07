"""[민옥 트랙 · 기억 구조 1단] 판정 러너 — 발화·캐리어를 팀 정본 judge 로 채점.

잣대: modules.judge.judge_fact (확정 사양: 비교 묶음 내 단일 판정기 · temp 0 · n=3
다수결 · votes 원본 보존). 판정기 좌표 = gpt-mini (PREREG_v1 §5). 공급자 무관 경로
(_llm_vote)를 쓰므로 prompt_ver 에 +merged_system 이 붙는다 — judge.py 독스트링 참조.

채점 대상 (런당):
  essay_r0~r3  발화 4편 (전 조건)
  carrier      최종 캐리어 — ② 최종 수첩 / ③ 최종 글 (①은 설계상 12 보존, 채점 없음)
회상(recall)의 정답 판정은 앵커 일치 필수(PREREG §6)라 LLM 없이 analyze_solo.py 가 한다.

규모: 런당 ①=144표 ②③=180표 → 54런(2모델) ≈ 9,072콜 (gpt-mini, 수 달러).
체크포인트가 표 단위라 끊겨도 같은 명령으로 이어 돈다.

실행:
  PYTHONUTF8=1 python experiments/memory_structure/judge_solo.py --offline   # 0콜 뼈대 점검
  PYTHONUTF8=1 python experiments/memory_structure/judge_solo.py             # 전 런 채점
  PYTHONUTF8=1 python experiments/memory_structure/judge_solo.py --models gpt
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules import judge as J  # noqa: E402
from modules import llm  # noqa: E402

ISSUE_ID = "issue_camp"
JUDGE_MODEL = "gpt-mini"          # PREREG_v1 §5 — 비교 묶음 내 단일
N_VOTES = 3
HERE = Path(__file__).resolve().parent
RUNS_DIR = HERE / "runs"
OUT_DIR = HERE / "judgments"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def targets_of(run: dict) -> list[tuple[str, str]]:
    """(태그, 원문) 목록 — 채점 대상."""
    t = [(f"essay_r{i}", e) for i, e in enumerate(run["essays"])]
    if run["memory"] == "note":
        t.append(("carrier", run["notes"][-1]))
    elif run["memory"] == "prev":
        t.append(("carrier", run["essays"][-1]))
    return t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=None, help="runs/ 하위 폴더명 (기본: 전부)")
    ap.add_argument("--offline", action="store_true", help="0콜 스텁 (뼈대 점검 전용)")
    ap.add_argument("--max-calls", type=int, default=12000)
    args = ap.parse_args()

    facts = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))["facts"]

    if args.offline:
        vote_fn = J._offline_vote
        prompt_ver = J.JUDGE_PROMPT_VER + "+offline_stub"
    else:
        llm.preflight(JUDGE_MODEL, temperature=J.JUDGE_TEMPERATURE)
        vote_fn = lambda f, u: J._llm_vote(JUDGE_MODEL, f, u)  # noqa: E731
        prompt_ver = J.JUDGE_PROMPT_VER + "+merged_system"

    budget = {"n": 0}

    def counted_vote(f, u):
        if budget["n"] >= args.max_calls:
            raise RuntimeError(f"호출 상한 {args.max_calls} 도달 — 중단 (체크포인트 보존)")
        budget["n"] += 1
        if budget["n"] % 50 == 0:
            print(f"  … {budget['n']}표 진행 중", flush=True)
        return vote_fn(f, u)

    model_dirs = ([RUNS_DIR / m for m in args.models] if args.models
                  else [p for p in sorted(RUNS_DIR.iterdir())
                        if p.is_dir() and not p.name.startswith("_")])

    for md in model_dirs:
        # 오프라인 스텁은 별도 폴더 — 실판정이 스텁 산출물을 "결과 존재"로 오인해 스킵하는 사고 방지
        out_md = (OUT_DIR / "_offline" if args.offline else OUT_DIR) / md.name
        out_md.mkdir(parents=True, exist_ok=True)
        for run_path in sorted(md.glob("run_*.json")):
            if run_path.name.endswith(".partial.jsonl"):
                continue
            run = json.loads(run_path.read_text(encoding="utf-8"))
            dst = out_md / f"judge_{run['run_id']}.json"
            if dst.exists():
                print(f"[skip] {md.name}/{run['run_id']}")
                continue
            ckpt = out_md / f"judge_{run['run_id']}.partial.jsonl"
            done: dict[str, dict] = {}
            if ckpt.exists():
                for line in ckpt.read_text(encoding="utf-8").splitlines():
                    row = json.loads(line)
                    done[row["key"]] = row["rec"]
            with ckpt.open("a", encoding="utf-8") as fp:
                records: dict[str, list[dict]] = {}
                for tag, text in targets_of(run):
                    utt = [{"agent_id": "solo", "response_text": text}]
                    recs = []
                    for f in facts:
                        key = f"{tag}:{f['fact_id']}"
                        if key in done:
                            recs.append(done[key])
                            continue
                        rec = J.judge_fact(utt, f, vote_fn=counted_vote, n_votes=N_VOTES)
                        fp.write(json.dumps({"key": key, "rec": rec}, ensure_ascii=False) + "\n")
                        fp.flush()
                        recs.append(rec)
                    records[tag] = recs
            out = {
                "schema": "solo_judgment_v1", "issue_id": ISSUE_ID,
                "run_id": run["run_id"], "run_model": run["meta"]["model_key"],
                "judge": {"model": JUDGE_MODEL, "model_id": llm.resolve_model(JUDGE_MODEL),
                          "temperature": J.JUDGE_TEMPERATURE, "n_votes": N_VOTES,
                          "prompt_ver": prompt_ver, "judged_at": _now()},
                "records": records,
            }
            dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[done] {md.name}/{run['run_id']} · 누적 {budget['n']}표")

    print(f"[judge] 완료 — 총 {budget['n']}표")


if __name__ == "__main__":
    main()
