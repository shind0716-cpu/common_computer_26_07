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
MT2 확장(WORKORDER2 — append 모드): 기존 scan_result.json 행·scan_table.md 행은
  수정하지 않고 신규 런만 스캔해 아래에 덧붙인다. 신규 행 한정 추가 지표 —
  피험자 신규 = S_r 적중 중 자기 이전 발화(S_0..S_{r-1})에 없던 것 (revision 전진 판독)
  탈락       = 직전 자기 발화 대비 빠진 fact_id (수정을 거치며 사실이 빠지는가)
MT3 확장(WORKORDER3 §3 — LLM 0콜 유지): note/prev 런(run_meta 에 memory 필드) 한정 —
  수첩 생존 = 라운드별 수첩(adopted) 내 앵커, favors·critical 태그 병기
  복귀 사건 = f 가 내 수첩·발화(라운드 보유 = 그 라운드 발화 ∪ 수첩)에서 사라진 뒤,
              상대 발화에 f 등장, 그 뒤 내 수첩/발화에 f 재등장 — 전수 나열 (0건이면 0건)
  수첩 오염 = 상대 입장 우호(favors) 사실이 내 수첩에 등장한 자리 전수 (논거 오염은 육안)
MT4 확장(WORKORDER4 §2 — LLM 0콜 유지): 신규 스캔 행 한정 추가 지표(기존 행 무수정) —
  드롭 사건 전수 = f 가 보유에서 사라진 사건별로, 드롭 이후(재등장 전까지) 상대 발화에
  f 가 등장한 라운드 목록(기회 크기) 병기 — §2-2 "기회 대비 복귀율"의 분모.
  MT4 런은 run_meta 의 opponent_memory(비대칭 기억 표시)로 식별해 별도 표 절에 덧붙인다.
주의: 탐색 · 사전등록 없음 · n=1~2/셀 — 수치는 어떤 주장의 증거로도 인용 금지.

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
from modules import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
ROUNDS = 4
ISSUE_ID = "issue_camp"


def hits(text: str) -> set[str]:
    return {fid for fid, pat in ANCHORS.items() if re.search(pat, text)}


def load_fact_tags() -> dict[str, dict]:
    doc = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))
    return {f["fact_id"]: {"favors": f.get("favors"), "critical": f.get("critical")}
            for f in doc["facts"]}


def mt3_extras(rows: list[dict], meta: dict) -> dict:
    """WORKORDER3 §3 지표 — 수첩 생존·복귀 사건·수첩 오염. 시간축은 파일 기록 순서.

    라운드 보유 hold(X,r) = X 의 r 발화 앵커 ∪ r 수첩(adopted) 앵커 (prev 팔은 발화만).
    복귀 사건: hold 에서 f 소멸(드롭 시점 = 그 라운드 X 의 마지막 이벤트) → 이후 상대
    발화에 f → 그 뒤 X 의 발화/수첩에 f 재등장. 상태기계로 전수 나열, 재드롭 후 재사건 허용.
    """
    tags = load_fact_tags()
    timeline = []                               # (t, speaker, kind, round, hitset)
    for r in rows:
        if r["event"] == "utterance":
            timeline.append((len(timeline), r["speaker"], "utterance", r["round"],
                             hits(r["response"])))
        elif r["event"] == "note":
            timeline.append((len(timeline), r["speaker"], "note", r["round"],
                             hits(r["adopted"])))

    notes_grid = [
        {"round": rnd, "speaker": spk, "fact_ids": sorted(h),
         "n": len(h),
         "favors": {fid: tags[fid]["favors"] for fid in sorted(h)},
         "critical": sorted(fid for fid in h if tags[fid]["critical"]),
         "chars": None}                          # chars 는 아래서 채움 (원문 길이)
        for _, spk, kind, rnd, h in timeline if kind == "note"]
    note_rows = [r for r in rows if r["event"] == "note"]
    for g, nr in zip(notes_grid, note_rows):
        g["chars"] = len(nr["adopted"])
        g["truncated"] = nr["truncated"]
        g["retried"] = nr["retry"] is not None

    comebacks = []
    for x in ("S", "O"):
        own = [(t, kind, rnd, h) for t, spk, kind, rnd, h in timeline if spk == x]
        opp = [(t, rnd, h) for t, spk, kind, rnd, h in timeline
               if spk != x and kind == "utterance"]
        x_rounds = sorted({rnd for _, _, rnd, _ in own})
        hold = {rnd: set().union(*(h for _, _, r2, h in own if r2 == rnd))
                for rnd in x_rounds}
        utt_hits = {rnd: next(h for t, k, r2, h in own if r2 == rnd and k == "utterance")
                    for rnd in x_rounds}
        end_t = {rnd: max(t for t, _, r2, _ in own if r2 == rnd) for rnd in x_rounds}
        utt_t = {rnd: next(t for t, k, r2, _ in own if r2 == rnd and k == "utterance")
                 for rnd in x_rounds}
        for f in ANCHORS:
            state, drop_t, drop_r, opp_r = "never", None, None, None
            for rnd in x_rounds:
                if state == "dropped":
                    for t, ornd, h in opp:
                        if drop_t < t < utt_t[rnd] and f in h:
                            state, opp_r = "opp_seen", ornd
                            break
                if f in hold[rnd]:
                    if state == "opp_seen":
                        via = "utterance" if f in utt_hits[rnd] else "note"
                        comebacks.append({
                            "speaker": x, "fact_id": f, "dropped_round": drop_r,
                            "opp_round": opp_r, "reappeared_round": rnd, "via": via,
                            "favors": tags[f]["favors"], "critical": tags[f]["critical"]})
                    state = "held"
                elif state in ("held",):
                    state, drop_t, drop_r = "dropped", end_t[rnd], rnd

    contamination = []
    for g in notes_grid:
        rival = "다림재" if g["speaker"] == "S" else "무레온"
        foreign = [fid for fid in g["fact_ids"] if tags[fid]["favors"] == rival]
        if foreign:
            contamination.append({"round": g["round"], "speaker": g["speaker"],
                                  "fact_ids": foreign})

    # MT4 §2-2 — 드롭 사건 전수 + 기회 크기. comebacks 와 같은 timeline·hold 정의.
    # 기회 = 드롭 시점(그 라운드 자기 마지막 이벤트) 이후 ~ 재등장 라운드 자기 발화
    # 시점 전, 상대 발화에 f 가 등장한 라운드들 (재등장 없으면 판 끝까지).
    drop_events = []
    for x in ("S", "O"):
        own = [(t, kind, rnd, h) for t, spk, kind, rnd, h in timeline if spk == x]
        opp = [(t, rnd, h) for t, spk, kind, rnd, h in timeline
               if spk != x and kind == "utterance"]
        x_rounds = sorted({rnd for _, _, rnd, _ in own})
        hold = {rnd: set().union(*(h for _, _, r2, h in own if r2 == rnd))
                for rnd in x_rounds}
        end_t = {rnd: max(t for t, _, r2, _ in own if r2 == rnd) for rnd in x_rounds}
        utt_t = {rnd: next(t for t, k, r2, _ in own if r2 == rnd and k == "utterance")
                 for rnd in x_rounds}
        x_events = []
        for f in ANCHORS:
            open_ev, was_held = None, False
            for rnd in x_rounds:
                if f in hold[rnd]:
                    if open_ev is not None:       # 재등장 — 열린 드롭 사건 닫기
                        open_ev["reappeared_round"] = rnd
                        open_ev["_until"] = utt_t[rnd]
                        open_ev = None
                    was_held = True
                elif was_held:                    # 보유 → 소멸 = 드롭 사건 개시
                    open_ev = {"speaker": x, "fact_id": f, "dropped_round": rnd,
                               "favors": tags[f]["favors"],
                               "critical": tags[f]["critical"],
                               "reappeared_round": None,
                               "_from": end_t[rnd], "_until": None}
                    x_events.append(open_ev)
                    was_held = False
        for ev in x_events:
            lo, hi = ev.pop("_from"), ev.pop("_until")
            ev["opp_rounds_after"] = sorted(
                {ornd for t, ornd, h in opp
                 if t > lo and (hi is None or t < hi) and ev["fact_id"] in h})
            ev["n_opportunity_rounds"] = len(ev["opp_rounds_after"])
        drop_events += x_events

    return {"memory": meta["memory"], "note_survival": notes_grid,
            "comeback_events": comebacks, "note_contamination": contamination,
            "drop_events": drop_events}


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

    # MT2 추가 지표 (신규 행 한정 — 기존 행은 재계산하지 않는다)
    subj_new_self = []
    seen_s: set[str] = set()
    for h in s_hits:
        subj_new_self.append(sorted(h - seen_s))
        seen_s |= h
    dropped_s = [sorted(s_hits[r - 1] - s_hits[r]) for r in range(1, len(s_hits))]
    dropped_o = [sorted(o_hits[r - 1] - o_hits[r]) for r in range(1, len(o_hits))]

    result = {
        "run_id": meta["run_id"], "arm": meta["arm"], "model_key": meta["model_key"],
        "model_id": meta["model_id"], "per_utterance": per_utt,
        "personal_S": [len(h) for h in s_hits],
        "personal_O": [len(h) for h in o_hits],
        "channel": [len(c) for c in channel],
        "channel_fact_ids": [sorted(c) for c in channel],
        "opponent_new_anchors_vs_self": opp_new_self,
        "opponent_new_anchors_vs_channel": opp_new_channel,
        "subject_new_anchors_vs_self": subj_new_self,
        "dropped_vs_prev_S": dropped_s,   # r1..r3 — 직전 자기 발화 대비 빠진 fact_id
        "dropped_vs_prev_O": dropped_o,   # r1..r2
    }
    if "memory" in meta:                  # MT3/MT4 런 — WORKORDER3 §3 지표 공유
        result.update(mt3_extras(rows, meta))
        if "opponent_memory" in meta:     # MT4 런 (비대칭 기억) — WORKORDER4 §1
            result["opponent_memory"] = meta["opponent_memory"]
            result["opponent_role"] = meta["opponent_role"]
    return result


def main() -> None:
    runs = sorted((HERE / "runs").glob("debate_*.jsonl"))
    if not runs:
        raise SystemExit("[scan] runs/ 에 판별 원문이 없다 — run_minitest.py 먼저")

    # append 모드 (WORKORDER2 §3): 기존 행은 파일에서 읽은 그대로 보존, 신규 런만 스캔
    res_path = HERE / "scan_result.json"
    existing = (json.loads(res_path.read_text(encoding="utf-8"))
                if res_path.exists() else [])
    known = {r["run_id"] for r in existing}
    new = [scan_run(p) for p in runs
           if p.stem[len("debate_"):] not in known]
    if not new:
        print("[scan] 신규 런 없음 — 파일 무변경")
        return
    res_path.write_text(json.dumps(existing + new, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    table = HERE / "scan_table.md"
    plain = [r for r in new if "memory" not in r]
    mt3 = [r for r in new if "memory" in r and "opponent_memory" not in r]
    mt4 = [r for r in new if "opponent_memory" in r]
    lines: list[str] = []
    if plain:
        lines += ["",
                  "## MT2 추가분 (WORKORDER2 2026-08-19) — 기존 행 무수정, 아래 덧붙임",
                  "",
                  "> 탐색 · 사전등록 없음 · n=1~2/셀 · **수치 인용 금지**.",
                  "> revision = 수정형 장르(첫 발화만 성명서형) · nostance = 성명서형·양측 입장 없음.",
                  "> 신규 컬럼 — S/O 신규 = 그 화자의 자기 이전 발화 대비 신규 앵커 수 ·",
                  "> 탈락 = 직전 자기 발화 대비 빠진 앵커 수 (fact_id 목록은 scan_result.json).",
                  "",
                  "| 런 | 모델 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 | O 신규 r0→r2 "
                  "| S 신규 r0→r3 | S 탈락 r1→r3 | O 탈락 r1→r2 |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for r in plain:
            s = "→".join(str(n) for n in r["personal_S"])
            o = "→".join(str(n) for n in r["personal_O"])
            c = "→".join(str(n) for n in r["channel"])
            onw = "→".join(str(len(x)) for x in r["opponent_new_anchors_vs_self"])
            snw = "→".join(str(len(x)) for x in r["subject_new_anchors_vs_self"])
            sdr = "→".join(str(len(x)) for x in r["dropped_vs_prev_S"])
            odr = "→".join(str(len(x)) for x in r["dropped_vs_prev_O"])
            lines.append(f"| {r['run_id']} | {r['model_key']} | {s} | {o} | {c} "
                         f"| {onw} | {snw} | {sdr} | {odr} |")
        lines.append("")
    if mt3:
        lines += ["",
                  "## MT3 추가분 (WORKORDER3 2026-08-19) — 기존 행 무수정, 아래 덧붙임",
                  "",
                  "> 탐색 · 사전등록 없음 · n=2/셀 · **수치 인용 금지**.",
                  "> note = 수첩 500자+상대 직전 글 · prev = 자기 직전 글+상대 직전 글 —",
                  "> r0 이후 사실 12개·토론 전문 화면 소멸. 수첩 = 라운드별 수첩(adopted) 내",
                  "> 앵커 수(S r0→r3 · O r0→r2, prev 팔은 —) · 복귀 = 복귀 사건 수(내 보유",
                  "> 소멸→상대 발화 등장→내 재등장) · 오염 = 상대 우호 사실의 내 수첩 등장 자리",
                  "> 수. fact_id·favors·critical 상세는 scan_result.json.",
                  "",
                  "| 런 | 기억 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 "
                  "| 수첩 S r0→r3 | 수첩 O r0→r2 | 복귀 | 오염 |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for r in mt3:
            s = "→".join(str(n) for n in r["personal_S"])
            o = "→".join(str(n) for n in r["personal_O"])
            c = "→".join(str(n) for n in r["channel"])
            ns = "→".join(str(g["n"]) for g in r["note_survival"] if g["speaker"] == "S")
            no = "→".join(str(g["n"]) for g in r["note_survival"] if g["speaker"] == "O")
            lines.append(f"| {r['run_id']} | {r['memory']} | {s} | {o} | {c} "
                         f"| {ns or '—'} | {no or '—'} | {len(r['comeback_events'])} "
                         f"| {len(r['note_contamination'])} |")
        lines.append("")
    if mt4:
        lines += ["",
                  "## MT4 추가분 (WORKORDER4 2026-08-20) — 기존 행 무수정, 아래 덧붙임",
                  "",
                  "> 탐색 · 사전등록 없음 · n=2/셀 · **수치 인용 금지**.",
                  "> 비대칭 기억(승인 기본안): S = 수첩 500자+상대 직전 글(MT3 note 축자) ·",
                  "> O = 전체 기억+배역(stubborn = 대조분석 §3-1 수정 문안 · advance = 1호",
                  "> 축자). 드롭 S(기회) = S 드롭 사건 수(괄호 = 그중 상대가 이후 말해준",
                  "> 사건 수 — §2-2 복귀율의 분모) · 복귀 = 복귀 사건 수 · 오염 = 상대 우호",
                  "> 사실의 S 수첩 등장 자리 수 · O 신규 = 자기 이전 발화 대비 신규 앵커",
                  "> (1호 방식 배역 이행 점검). 상세는 scan_result.json 의 drop_events.",
                  "",
                  "| 런 | 배역 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 "
                  "| 수첩 S r0→r3 | 드롭 S(기회) | 복귀 | 오염 | O 신규 r0→r2 |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for r in mt4:
            s = "→".join(str(n) for n in r["personal_S"])
            o = "→".join(str(n) for n in r["personal_O"])
            c = "→".join(str(n) for n in r["channel"])
            ns = "→".join(str(g["n"]) for g in r["note_survival"] if g["speaker"] == "S")
            sd = [e for e in r["drop_events"] if e["speaker"] == "S"]
            sd_opp = sum(1 for e in sd if e["n_opportunity_rounds"] > 0)
            onw = "→".join(str(len(x)) for x in r["opponent_new_anchors_vs_self"])
            lines.append(f"| {r['run_id']} | {r['opponent_role']} | {s} | {o} | {c} "
                         f"| {ns or '—'} | {len(sd)}({sd_opp}) "
                         f"| {len(r['comeback_events'])} "
                         f"| {len(r['note_contamination'])} | {onw} |")
        lines.append("")
    with table.open("a", encoding="utf-8") as fp:
        fp.write("\n".join(lines))
    print(f"[scan] 신규 {len(new)}판 덧붙임 (기존 {len(existing)}판 무수정) "
          f"→ scan_result.json · scan_table.md")


if __name__ == "__main__":
    main()
