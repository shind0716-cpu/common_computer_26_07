"""[민옥 트랙 · 토론 배역 미니테스트] 앵커 스캔 — LLM 0콜 (FAR·survival 마지노선과 동일).

입력: runs/debate_*.jsonl (utterance 이벤트)
출력: scan_result.json + scan_table.md (조건×라운드 생존 표, 개인/채널)

앵커 정의는 본실험 정본을 import 로 재사용한다 —
experiments/memory_structure/analyze_solo.py 의 ANCHORS (드라이런 정본 계승분).
복사하지 않는 이유: 사본은 정본 개정 시 조용히 낡는다 (SCHEMA 길잡이 사고와 같은 기전).

지표 (지시문 §3~§4):
  개인 생존   = 발화자 기준 — 라운드 r 의 S/O 발화 각각의 앵커 적중 팩트 집합 크기
  채널 생존   = 라운드 r 의 양측 합집합 (r3 은 S 만 — O3 생략 설계)
  상대 신규   = O_r 적중 중 상대 자신의 이전 발화(O_0..O_{r-1})에 없던 것 (배역 판정 보조)
                + 그 시점까지 채널 전체(양측 r-1 까지 + S_r)에 없던 것 (엄격판)
주의: 탐색 · 사전등록 없음 · n=1/셀 — 수치는 어떤 주장의 증거로도 인용 금지.

실행: PYTHONUTF8=1 python experiments/debate_role_minitest/scan_minitest.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from experiments.memory_structure.analyze_solo import ANCHORS  # noqa: E402 — 앵커 정본

HERE = Path(__file__).resolve().parent
ROUNDS = 4


def hits(text: str) -> set[str]:
    return {fid for fid, pat in ANCHORS.items() if re.search(pat, text)}


def scan_run(path: Path) -> dict:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    meta = rows[0]
    utts = [r for r in rows if r["event"] == "utterance"]
    by_key = {(u["speaker"], u["round"]): u for u in utts}

    per_utt = []
    s_hits: list[set[str]] = []
    o_hits: list[set[str]] = []
    for r in range(ROUNDS):
        for spk in ("S", "O"):
            u = by_key.get((spk, r))
            if u is None:
                continue                      # O3 생략
            h = hits(u["response"])
            per_utt.append({"round": r, "speaker": spk, "n": len(h),
                            "fact_ids": sorted(h)})
            (s_hits if spk == "S" else o_hits).append(h)

    channel = [s_hits[r] | (o_hits[r] if r < len(o_hits) else set())
               for r in range(ROUNDS)]
    opp_new_self, opp_new_channel = [], []
    seen_self: set[str] = set()
    for r, h in enumerate(o_hits):
        opp_new_self.append(sorted(h - seen_self))
        before = set().union(*s_hits[:r + 1], *o_hits[:r]) if r or s_hits else set()
        opp_new_channel.append(sorted(h - before))
        seen_self |= h

    return {
        "run_id": meta["run_id"], "arm": meta["arm"], "model_key": meta["model_key"],
        "model_id": meta["model_id"], "per_utterance": per_utt,
        "personal_S": [len(h) for h in s_hits],
        "personal_O": [len(h) for h in o_hits],
        "channel": [len(c) for c in channel],
        "channel_fact_ids": [sorted(c) for c in channel],
        "opponent_new_anchors_vs_self": opp_new_self,
        "opponent_new_anchors_vs_channel": opp_new_channel,
    }


def main() -> None:
    runs = sorted((HERE / "runs").glob("debate_*.jsonl"))
    if not runs:
        raise SystemExit("[scan] runs/ 에 판별 원문이 없다 — run_minitest.py 먼저")
    results = [scan_run(p) for p in runs]
    (HERE / "scan_result.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 앵커 스캔 생존 표 — 토론 배역 미니테스트",
             "",
             "> 탐색 · 사전등록 없음 · n=1/셀 · **수치 인용 금지** (WORKORDER 2026-08-19).",
             "> 개인 = 그 라운드 발화의 앵커 적중 팩트 수(/12) · 채널 = 양측 합집합.",
             "> r3 의 상대(O) 칸은 설계상 없음(O3 생략) — 채널 r3 = S3 단독.",
             "",
             "| 팔 | 모델 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 | 상대 신규(자기 대비) r0→r2 |",
             "|---|---|---|---|---|---|"]
    for r in results:
        s = "→".join(str(n) for n in r["personal_S"])
        o = "→".join(str(n) for n in r["personal_O"])
        c = "→".join(str(n) for n in r["channel"])
        nw = "→".join(str(len(x)) for x in r["opponent_new_anchors_vs_self"])
        lines.append(f"| {r['arm']} | {r['model_key']} | {s} | {o} | {c} | {nw} |")
    lines.append("")
    (HERE / "scan_table.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[scan] {len(results)}판 → scan_result.json · scan_table.md")


if __name__ == "__main__":
    main()
