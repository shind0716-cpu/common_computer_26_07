# -*- coding: utf-8 -*-
"""계보 시트 생성기 — 미공유 팩트 전량의 원형→경로를 사람이 읽을 마크다운으로 (0콜).

지위: 관측 노드 파생 뷰 생성기(요한 측). 계약: docs/proposals/HIDDEN_PROFILE_NODE.md §3-5.
계기(lineage)는 좌표로 묶기만 한다 — 판정·요약·발췌 없음, 전량. 무엇이 남고 굴절됐는지는
읽는 사람이 정한다(§5-2·5-3).

산출물은 리포에 커밋하지 않는다 — 기본 출력은 리포 부모 폴더(파생 뷰·재생성 가능).

사용:
  PYTHONUTF8=1 python experiments/hidden_profile_node/gen_lineage_sheet.py --run gpt001
  PYTHONUTF8=1 python experiments/hidden_profile_node/gen_lineage_sheet.py \
      --run 테스트 --out D:/somewhere/sheet.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from modules import hidden_profile as hp  # noqa: E402
from modules import paths  # noqa: E402


def build_sheet(events: list[dict], assignment: dict, facts_doc: dict,
                issue_id: str, run_id: str) -> tuple[str, dict]:
    """시트 본문과 완전성 수치(개수만)를 돌려준다. 파일 쓰기 없음(순수)."""
    unshared = [f["fact_id"] for f in facts_doc["facts"] if f.get("share") == "unshared"]
    out = []
    out.append(f"# 계보 시트 — {issue_id} · run {run_id} (미공유 팩트 {len(unshared)}개 전량)")
    out.append("")
    out.append("지위: **파생 뷰** (0콜 — 원자료는 리포 debate/facts/assignment, 재생성 가능). "
               "계기는 좌표로 묶기만 했다 — **무엇이 남고 굴절됐는지는 읽는 사람이 정한다** "
               "(HIDDEN_PROFILE_NODE.md §5-2·5-3). 단판이면 여기서 보이는 것은 "
               "관찰 재료이지 가설이 아니다(§8).")
    out.append("")
    out.append("읽는 법: 각 팩트마다 ① 원형(설계값) ② 보유자의 발화 원문(라운드순) "
               "③ 보유자의 수첩 판본 원문 ④ 입력 참조(prompt_assembly 슬롯). "
               "비보유자 발화는 없다(§3-5 — 전달 여부는 등장 좌표 라벨 뒤의 질문).")

    n_notes = 0
    for fid in unshared:
        ln = hp.lineage(events, assignment, facts_doc, fid)
        f = ln["fact"]
        out.append("")
        out.append("---")
        out.append(f"## {fid} — 보유자 {', '.join(ln['holders'])}")
        out.append("")
        out.append(f"**원형**: {f['text']}")
        out.append(f"(favors={f['favors']} · requirement={f['requirement']} · apparent={f['apparent']})")
        out.append("")
        out.append("### 보유자 발화 (원문 전량, 라운드순)")
        for u in ln["utterances"]:
            out.append("")
            out.append(f"**r{u['round']} · {u['agent_id']}**")
            out.append("")
            out.append("> " + u["response_text"].replace("\n", "\n> "))
        out.append("")
        out.append("### 보유자 수첩 판본 (원문 전량)")
        if ln["notes"]:
            for n in ln["notes"]:
                n_notes += 1
                out.append("")
                out.append(f"**r{n['round']} · {n['agent_id']} · {n['source']} · {n['n_chars']}자**")
                out.append("")
                out.append("> " + n["note_text"].replace("\n", "\n> "))
        else:
            out.append("(note_update 없음)")
        out.append("")
        out.append("### 입력 참조 (prompt_assembly)")
        for r in ln["inputs_ref"]:
            slots = json.dumps(r["slots"], ensure_ascii=False)
            out.append(f"- r{r['round']} {r['agent_id']} · hash {str(r['prompt_hash'])[:12]}… · slots {slots}")

    counts = {"n_facts": len(unshared), "n_note_blocks": n_notes,
              "n_notes_ledger": len(hp.note_trace(events))}
    return "\n".join(out) + "\n", counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", default="issue_hire")
    ap.add_argument("--run", required=True, help="run_id (예: gpt001)")
    ap.add_argument("--data-dir", type=Path, default=None,
                    help="데이터 루트 (기본: 팀 data/ — modules.paths)")
    ap.add_argument("--out", type=Path, default=None,
                    help="출력 파일 (기본: 리포 부모 폴더 LINEAGE_<issue>_<run>.md — 리포 밖)")
    args = ap.parse_args()

    old_data = paths.DATA
    if args.data_dir:
        paths.DATA = Path(args.data_dir).resolve()
    try:
        events = [json.loads(l) for l in paths.debate(args.issue, args.run).read_text(
            encoding="utf-8").splitlines() if l.strip()]
        assignment = json.loads(paths.assignment(args.issue).read_text(encoding="utf-8"))
        facts_doc = json.loads(paths.facts(args.issue).read_text(encoding="utf-8"))
    finally:
        paths.DATA = old_data

    sheet, counts = build_sheet(events, assignment, facts_doc, args.issue, args.run)
    dst = args.out or (ROOT.parent / f"LINEAGE_{args.issue}_{args.run}.md")
    if ROOT in dst.resolve().parents:
        raise SystemExit(f"출력이 리포 안이다: {dst} — 파생 뷰는 리포 밖에만 쓴다(README)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(sheet, encoding="utf-8")
    print(f"[lineage-sheet] 저장: {dst}")
    print(f"[lineage-sheet] 팩트 {counts['n_facts']} · 수첩 블록 {counts['n_note_blocks']}"
          f" (원장 판본 {counts['n_notes_ledger']} — 보유 팩트 수만큼 중복 수록)")


if __name__ == "__main__":
    main()
