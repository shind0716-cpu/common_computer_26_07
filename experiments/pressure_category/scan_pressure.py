"""[민옥 트랙 · 압박×카테고리] 채점 스캐너 — LLM 0콜, 파일만 읽는다.

runs/<model>/run_*.json 을 훑어 판마다:
  ① 표식 생존 — 라운드별 글·수첩에서 사실 12개의 표식(기계 검색)
  ② 카테고리 생존 — 수첩 기준, 카테고리의 사실 중 1개 이상 표식 잔존 = 생존
  ③ 자기 밖 격차 — (가치 안 카테고리 생존수) − (가치 밖 생존수), 마지막 수첩 기준
  ④ 최종 선택 — final_poll 원문에서 옵션 문자열 검출. 둘 다/둘 다 아님 = 판독불가
     (사람 눈 확인 대상). 뒤집힘 = 선택 ≠ aligned.

주의(정찰 실측 계승): 표식 검색은 바꿔 말하면 놓친다 — 이 표는 1차 집계이고,
뒤집힘·판독불가·격차 이상 판은 반드시 원문을 눈으로 확인하라. 수치는 사전등록
등급으로만 인용한다.

출력: scan_table.md (append 전용 — 기존 행 무수정) + scan_snapshot.json
(전량 재계산 파생물 — 언제든 재생성 가능, 정본은 runs/ 원문).

사용: PYTHONUTF8=1 python experiments/pressure_category/scan_pressure.py [--dry]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATERIALS = HERE / "MATERIALS_v0.json"
RUNS_DIR = HERE / "runs"
TABLE = HERE / "scan_table.md"
SNAPSHOT = HERE / "scan_snapshot.json"


def scan_run(doc: dict, mat: dict) -> dict:
    facts = mat["facts"]
    cats = mat["categories"]
    by_cat = {c: [f for f in facts if f["category"] == c] for c in cats}
    essays = doc.get("essays") or []
    notes = doc.get("notes") or []

    def present(text: str) -> list[str]:
        return [f["id"] for f in facts if f["anchor"] in text]

    essay_anchors = [present(t) for t in essays]
    note_anchors = [present(t) for t in notes]

    last_note = notes[-1] if notes else ""
    cat_alive = {c: any(f["anchor"] in last_note for f in by_cat[c]) for c in cats}
    # '기타' 등 재료 밖 카테고리는 측정 매핑이 없다 — 안/밖 격차 분자·분모에서 제외.
    in_cats = [c for c in (doc.get("value_categories") or []) if c in cats]
    n_in = sum(1 for c in in_cats if cat_alive.get(c))
    n_out = sum(1 for c in cats if c not in in_cats and cat_alive.get(c))
    no_mapping = not in_cats                     # 기타 단독 페르소나 — 격차 산출 불가

    poll = (doc.get("final_poll") or "").strip()
    hits = [o for o in mat["options"] if o in poll]
    # 옵션 전체 문자열이 없으면 앞말('노린재'/'구름채')로 한 번 더 — 그래도 애매하면 판독불가
    if not hits:
        hits = [o for o in mat["options"] if o.split()[0] in poll]
    choice = hits[0] if len(hits) == 1 else None
    aligned = doc.get("aligned")
    # aligned 가 None 인 가치 세트(우세 동수 페르소나)는 정렬 답이 없어 뒤집힘을 잴 수 없다.
    flipped = (choice is not None and aligned is not None and choice != aligned)
    no_alignment = aligned is None

    return {
        "model": doc["meta"]["model_key"], "run_id": doc["run_id"],
        "issue_id": doc.get("issue_id"),
        "script": doc.get("script"), "value_set": doc.get("value_set"),
        "rep": doc.get("rep"), "aligned": doc.get("aligned"),
        "materials_hash": doc.get("materials_hash"), "dry": doc["meta"].get("dry"),
        "essay_anchor_counts": [len(a) for a in essay_anchors],
        "note_anchor_counts": [len(a) for a in note_anchors],
        "note_anchors": note_anchors,
        "cat_alive_last_note": cat_alive,
        "n_in_alive": n_in, "n_out_alive": n_out, "gap_in_minus_out": n_in - n_out,
        "no_mapping": no_mapping,
        "final_choice": choice, "final_unreadable": choice is None,
        "flipped": flipped, "no_alignment": no_alignment,
        "final_poll_text": poll[:200],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="runs/_dry/ 를 스캔 (기본: 실런)")
    args = ap.parse_args()

    # 재료 registry — 러너와 같은 발견 규칙(그쪽이 정본). 런마다 자기 issue_id 의 재료로 채점.
    sys.path.insert(0, str(HERE))
    from run_pressure import discover_materials  # noqa: E402
    reg = {iid: json.loads(p.read_text(encoding="utf-8"))
           for iid, p in discover_materials().items()}

    base = RUNS_DIR / "_dry" if args.dry else RUNS_DIR
    rows = []
    for mdir in sorted(base.glob("*")):
        if not mdir.is_dir() or mdir.name.startswith("_"):
            continue
        # 기본 재료는 모델 폴더 바로 아래, 그 외 재료는 <issue_id>/ 하위 (러너 규칙 미러)
        for p in sorted(mdir.glob("run_*.json")) + sorted(mdir.glob("*/run_*.json")):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                print(f"[warn] 깨진 파일 건너뜀: {p}")
                continue
            mat = reg.get(doc.get("issue_id"))
            if mat is None:
                print(f"[warn] 재료를 못 찾음(issue_id={doc.get('issue_id')}) — 건너뜀: {p.name}")
                continue
            rows.append(scan_run(doc, mat))

    if not rows:
        print("[scan] 대상 런 없음")
        return

    SNAPSHOT.write_text(json.dumps(
        {"scanned_at": datetime.now(timezone.utc).isoformat(),
         "dry": args.dry, "rows": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")

    # append 전용 표 — 이미 적힌 (재료, model, run_id, dry) 행은 다시 쓰지 않는다
    existing = TABLE.read_text(encoding="utf-8") if TABLE.exists() else ""
    new_lines = []
    for r in rows:
        key = (f"| {r['issue_id']} | {r['model']} | {r['run_id']} |"
               + (" dry |" if r["dry"] else " live |"))
        if key in existing:
            continue
        notes_txt = "→".join(str(n) for n in r["note_anchor_counts"]) or "—"
        alive = " ".join(c for c, v in r["cat_alive_last_note"].items() if v) or "(전멸)"
        choice = r["final_choice"] or "판독불가"
        flip = ("정렬불명" if r.get("no_alignment")
                else "⚠뒤집힘" if r["flipped"]
                else "?" if r["final_unreadable"] else "유지")
        new_lines.append(
            key + f" {r['script']} | {r['value_set']} | {notes_txt} | "
            f"{r['n_in_alive']}/{r['n_out_alive']} | {alive} | {choice} | {flip} |")
    if new_lines:
        header = ""
        if "| 재료 |" not in existing:
            # 재료 열이 없던 구판 표가 이미 있으면(append-only — 재작성 금지) 새 표 절을 연다.
            header = (("" if not existing else "\n## 재료 열 추가판 (2026-08-24 배관 이후)\n\n")
                      + ("# 압박×카테고리 스캔 표 (append 전용 — 기존 행 수정 금지)\n\n"
                         if not existing else "")
                      + "| 재료 | 모델 | run_id | 실행 | 각본 | 가치 | 수첩표식수(r0→r2) | "
                        "안/밖 생존 | 생존 카테고리(마지막 수첩) | 최종 선택 | 판정 |\n"
                        "|---|---|---|---|---|---|---|---|---|---|---|\n")
        stamp = f"\n<!-- scan {datetime.now(timezone.utc).isoformat()} -->\n"
        with TABLE.open("a", encoding="utf-8") as fp:
            fp.write(header + stamp + "\n".join(new_lines) + "\n")
    print(f"[scan] {len(rows)}판 스캔 · 새 행 {len(new_lines)} · "
          f"뒤집힘 {sum(1 for r in rows if r['flipped'])} · "
          f"판독불가 {sum(1 for r in rows if r['final_unreadable'])}")
    print(f"[scan] 표: {TABLE.name} · 스냅숏: {SNAPSHOT.name} (재생성 가능 파생물)")


if __name__ == "__main__":
    main()
