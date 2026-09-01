"""[공용 코어 · 압박×카테고리] 가치 세트 지문 표기 — 폐기하지 않고 출처만 적는다 (콜 0).

## 왜

`values/all_*.json` 서른하나에 `materials_hash` 가 없다. 그래서 세트가 **어느 재료
판본을 보고 지어졌는지** 파일만 봐서는 알 수 없었고, 재료가 개정되었을 때 그 어긋남이
드러나지 않았다 — ALL 트랙에서 실제로 터진 구멍이다(`PREREG_all34_2026-09-01.md` §2).

이 스크립트는 **아무것도 폐기하지 않는다.** 세트를 그대로 두고 지문만 적는다.
적힌 지문이 현행 재료 지문과 다르면 그 사실이 **파일에서 바로 보인다** — 그게 표기의
목적이다. 무엇을 쓸지 말지는 사람이 그 표기를 보고 정한다.

## 어느 판본인지 어떻게 정하나

두 단계로 정하고, 둘이 어긋나면 **적지 않는다**(모르는 것을 적느니 비워 둔다).

  ① 시점  세트 파일이 처음 커밋된 시각에 **살아 있던** 재료 판본
  ② 문면  그 판본의 `value_sets.A.categories + B.categories` 가 세트의
          `categories` 와 순서까지 같은가 — ALL 세트는 A+B 병합이므로 같아야 한다

②가 ①을 검산한다. `all_*` 의 note 가 「A+B 병합(전부 주기)」라고 적고 있고,
`allb1_*` 의 `derived_from.rule` 이 `exact_clause_union` 인 것과 같은 규칙이다.

## 적는 것

  materials_hash         작성 시점 재료 판본의 지문 (LF 정규화 sha256 앞 12자)
  materials_hash_source  그 지문을 어떻게 정했는지 — 되짚은 커밋·날짜·검산 방법

**현행 지문을 적지 않는다.** 세트가 옛 판을 보고 지어졌는데 현행 지문을 박으면
거짓 출처가 된다. 어긋남은 지우는 것이 아니라 보이게 하는 것이다.

사용:
  PYTHONUTF8=1 python stamp_valueset_hash.py            # 대조만 (쓰지 않음)
  PYTHONUTF8=1 python stamp_valueset_hash.py --write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from modules import content_hash  # noqa: E402

HERE = Path(__file__).resolve().parent
VALUES = HERE / "values"
MATERIALS = HERE / "materials"
STAMP_NOTE = ("작성 시점 재료 판본을 git 에서 되짚어 적음 (stamp_valueset_hash.py, "
              "2026-09-01). 세트 파일 창설 커밋 시각에 살아 있던 판본을 고르고, "
              "그 판본의 A+B 카테고리가 이 세트의 categories 와 순서까지 같은지로 검산했다. "
              "현행 재료 지문과 다르면 그 세트는 옛 판을 보고 지어진 것이다 — "
              "폐기 표시가 아니라 출처 표시다.")


def git(*a: str) -> bytes:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True).stdout


def git_text(*a: str) -> str:
    return git(*a).decode("utf-8", "replace")


def fp(raw: bytes) -> str:
    """재료 지문 — content_hash 와 같은 자(CRLF→LF 정규화 후 sha256 앞 12자)."""
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()[:12]


def material_index() -> dict:
    reg = {}
    for p in sorted(MATERIALS.glob("*.json")):
        if p.name == "MATERIALS_TEMPLATE.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            reg[d["issue_id"]] = p
    return reg


def ab_categories(d: dict) -> list:
    vs = d.get("value_sets") or {}
    return [c for k in ("A", "B") for c in (vs.get(k, {}).get("categories") or [])]


def resolve(set_path: Path, want: list, mat_rel: str) -> dict | None:
    """작성 시점 판본을 정한다 — 시점으로 고르고 문면으로 검산한다."""
    rel = set_path.relative_to(ROOT).as_posix()
    born = git_text("log", "--diff-filter=A", "--format=%aI", "--", rel).strip().split("\n")[-1]
    if not born:
        return None
    revs = []
    for line in git_text("log", "--format=%H %aI", "--", mat_rel).strip().split("\n"):
        if line.strip():
            h, when = line.split()
            revs.append((h, when))
    # 시점 — 세트가 태어난 때보다 앞선 재료 커밋 중 가장 최근 것
    by_time = next(((h, w) for h, w in revs if w <= born), None)
    # 문면 — A+B 가 세트 categories 와 같은 판본들
    by_text = []
    for h, when in revs:
        raw = git("show", f"{h}:{mat_rel}")
        if not raw.strip():
            continue
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        if ab_categories(d) == want:
            by_text.append((h, when, fp(raw)))
    if not by_text:
        return None
    picked = None
    if by_time:
        picked = next((t for t in by_text if t[0] == by_time[0]), None)
    agree = picked is not None
    if picked is None:                     # 시점이 못 고르면 문면 일치 중 가장 최근
        picked = by_text[0]
    return {"commit": picked[0][:12], "date": picked[1][:10], "hash": picked[2],
            "set_born": born[:10], "text_matches": len(by_text), "time_agrees": agree}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    reg = material_index()
    rows, skipped = [], []
    for p in sorted(VALUES.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        iid = d.get("materials")
        if iid not in reg or "categories" not in d:
            continue
        cur = content_hash.sha256_file(reg[iid])[:12]
        mat = json.loads(reg[iid].read_text(encoding="utf-8"))
        usable = set(d["categories"]) <= set(mat["categories"])
        have = d.get("materials_hash")
        r = resolve(p, list(d["categories"]), reg[iid].relative_to(ROOT).as_posix())
        rows.append((p, d, iid, cur, have, r, usable))
        if r is None:
            skipped.append(p.name)

    print(f"가치 세트 {len(rows)}개 — 지문 있음 {sum(1 for r in rows if r[4])} · "
          f"없음 {sum(1 for r in rows if not r[4])} · 판본 못 정함 {len(skipped)}")
    print()
    print(f"{'세트':26s}{'작성 시':14s}{'현행':14s}{'같나':5s}{'지금 쓸 수 있나':16s}적을 것")
    wrote = conflict = 0
    for p, d, iid, cur, have, r, usable in rows:
        if r is None:
            print(f"{d['vset_id']:26s}{'—':14s}{cur:14s}{'—':5s}"
                  f"{('예' if usable else '아니오 — 카테고리 안 맞음'):16s}판본 못 정함 → 비워 둠")
            continue
        drift = "다름" if r["hash"] != cur else "같음"
        use = "예" if usable else "아니오 — 카테고리 안 맞음"
        if have and have != r["hash"]:
            print(f"{d['vset_id']:26s}{r['hash']:14s}{cur:14s}{drift:5s}{use:16s}"
                  f"어긋남! 이미 적힌 {have} — 손대지 않음")
            conflict += 1
            continue
        if have:
            continue                        # 이미 있고 같다
        if a.write:
            d["materials_hash"] = r["hash"]
            d["materials_hash_source"] = (
                f"{STAMP_NOTE} 되짚은 커밋 {r['commit']} ({r['date']}), "
                f"세트 창설 {r['set_born']}, 문면 일치 판본 {r['text_matches']}개"
                + ("" if r["time_agrees"] else ", 시점으로는 못 고르고 문면으로만 정함"))
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            wrote += 1
        print(f"{d['vset_id']:26s}{r['hash']:14s}{cur:14s}{drift:5s}{use:16s}"
              + ("적음" if a.write else "적을 것"))

    drifted = [d["vset_id"] for _, d, _, cur, _, r, _ in rows if r and r["hash"] != cur]
    unusable = [d["vset_id"] for _, d, _, _, _, _, u in rows if not u]
    print()
    print(f"작성 시 지문 ≠ 현행 지문 — {len(drifted)}개")
    print("  뜻: 세트를 지은 뒤 재료가 바뀌었다. 폐기가 아니다.")
    print(f"  {', '.join(drifted) if drifted else '없음'}")
    print()
    print(f"그중 지금 쓸 수 없는 것(카테고리가 현행 재료에 없음) — {len(unusable)}개")
    print("  뜻: 안/밖을 가를 수 없다. 이것도 폐기가 아니라 표시다.")
    print(f"  {', '.join(unusable) if unusable else '없음'}")
    print(f"  나머지 {len(drifted) - len(unusable)}개는 재료 본문만 바뀌고 카테고리는 그대로다 — 쓸 수 있다.")
    if conflict:
        print(f"[경고] 이미 적힌 지문과 되짚은 값이 다른 세트 {conflict}개 — 사람이 볼 것")
    if a.write:
        print(f"\n{wrote}개 파일에 적었다.")
    else:
        print("\n(대조만 했다 — 적으려면 --write)")
    return 1 if conflict else 0


if __name__ == "__main__":
    sys.exit(main())
