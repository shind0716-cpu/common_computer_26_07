"""[공용 코어 · 압박×카테고리] 수첩 케이스 원장 — 볼 만한 수첩을 골라 원문 그대로 모은다 (콜 0).

## 왜 필요한가

수첩 원문은 판독 팩에 많이 있지만 그건 **채점용**이다 — 섞어 놓고 조건을 가렸다.
원자료 `runs/**/*.json` 에는 전부 있지만 **어느 것이 볼 만한지는 적혀 있지 않다.**
그래서 좋은 수첩을 찾을 때마다 사람이 매번 다시 뒤진다.

이 원장은 그 사이를 메운다. **고르는 것은 사람, 채우는 것은 기계다.**
`_cases.json` 에 판 좌표와 고른 사유와 짚을 구절만 적으면, 이 스크립트가 원자료에서
수첩 원문·재료 지문·카테고리 산죽음을 읽어 채운다.

## 관문 — 손으로 옮기다 틀리는 것을 막는다

`_cases.json` 의 `quotes` 는 그 수첩에 **글자 그대로** 있어야 한다. 하나라도 없으면
원장을 쓰지 않고 즉사한다(종료코드 1). 실제로 이 장치가 필요했다 — 2026-09-01 에
「haiku 수첩에 선례라는 낱말이 없다」고 적었다가 대조에서 틀린 것이 잡혔다.

강조 표시는 `**...**` 를 앞뒤에 두어 적을 수 있고, 대조할 때는 벗겨서 찾는다.

## 무엇이 원장에 들어가나

  왜 골랐나 · 판 좌표(모델·재료·세트·각본·반복) · 재료 지문 · 최종 선택
  · 카테고리 여섯의 산죽음 · **수첩 원문 그대로** · 짚을 구절

원문은 요약하지 않는다(CLAUDE.md 규약 5).

사용: PYTHONUTF8=1 python build_cases.py
산출: CASES_<날짜>.md
"""
from __future__ import annotations

import collections
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from modules import content_hash  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aggregate_all11 as A  # noqa: E402

KST = timezone(timedelta(hours=9))


def materials() -> dict:
    reg = {}
    for p in sorted((HERE / "materials").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            reg[d["issue_id"]] = (p, d)
    return reg


def hit(anchor: str, note: str) -> bool:
    return 0 < A.probe(anchor, note)[0] <= 2


def bare(q: str) -> str:
    """강조 표시를 벗긴 대조용 문자열."""
    return q.replace("**", "")


def main() -> int:
    spec = json.loads((HERE / "_cases.json").read_text(encoding="utf-8"))
    mats = materials()
    today = datetime.now(KST).strftime("%Y-%m-%d")

    bad, blocks, n = [], [], 0
    for g in spec["groups"]:
        blocks.append(f"\n## {g['id']}. {g['title']}\n\n{g['lede']}\n")
        for c in g["cases"]:
            n += 1
            p = HERE / "runs" / c["model"] / c["issue_id"] / c["run"]
            if not p.exists():
                bad.append(f"{c['model']}/{c['issue_id']}/{c['run']} — 판이 없다")
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            mp, mat = mats[c["issue_id"]]
            note = (d.get("notes") or [""])[-1]

            miss = [q for q in c["quotes"] if bare(q) not in note]
            if miss:
                bad += [f"{c['model']}/{c['issue_id']}/{c['run']} — 원문에 없는 구절: {q!r}"
                        for q in miss]
                continue
            if d.get("materials_hash") != content_hash.sha256_file(mp)[:12]:
                bad.append(f"{c['model']}/{c['issue_id']}/{c['run']} — 재료 지문이 현행과 다르다")
                continue

            given = set(d.get("value_categories") or [])
            # 신념 세트는 카드 이름을 value_categories 에 싣는데 그건 **재료 카테고리가 아니다**.
            # 재료와 겹치지 않으면 「준 가치」로 부르지 않는다 — 부르면 안/밖이 있는 것처럼 읽힌다.
            named = bool(given) and given <= set(mat["categories"])
            by = collections.defaultdict(list)
            for f in mat["facts"]:
                by[f["category"]].append(f["anchor"])
            alive = {ct: any(hit(x, note) for x in v) for ct, v in by.items()}
            kept = sum(1 for f in mat["facts"] if hit(f["anchor"], note))
            chips = " · ".join(
                ("**" if alive[ct] else "~~")
                + (("●" if ct in given else "○") if named else "·") + ct
                + ("**" if alive[ct] else "~~") for ct in mat["categories"])

            body = note
            for q in c["quotes"]:
                marked = q if "**" in q else f"**{q}**"
                if marked in body:                 # 수첩이 이미 굵게 쓴 자리 — 겹쳐 감싸지 않는다
                    continue
                body = body.replace(bare(q), marked, 1)

            blocks += [
                f"\n### {n}. {c['model']} · {c['issue_id'].replace('issue_', '')} · {c['label']}\n",
                f"**왜 골랐나.** {c['why']}\n",
                f"| 판 | 재료 지문 | 지목한 카테고리 | 남은 사실 | 수첩 | 최종 선택 |",
                f"|---|---|---|---|---|---|",
                (f"| `{c['run']}` | `{d.get('materials_hash')}` | "
                 + (f"{'·'.join(sorted(given))}" if named
                    else f"없음 — 신념 카드({'·'.join(sorted(given))})" if given else "없음")
                 + f" | **{kept}/12** | {len(note)}자 | "
                 + f"{d.get('final_poll', '').strip()[:24]} |"),
                "",
                ("카테고리 — ● 준 것 · ○ 안 준 것 · **굵게** 산 것 · ~~취소선~~ 죽은 것"
                 if named else
                 "카테고리 — 신념 세트라 지목이 없다 · **굵게** 산 것 · ~~취소선~~ 죽은 것"),
                "",
                chips,
                "",
                "> " + body.replace("\n", "\n> "),
                "",
            ]

    if bad:
        print(f"[즉사] 관문 실패 {len(bad)}건 — 원장을 쓰지 않는다.")
        for b in bad:
            print("   " + b)
        return 1

    L = [f"# 수첩 케이스 원장 ({today})", "",
         "지위: **근거 자료.** 고른 목록은 `_cases.json`, 채우는 것은 `build_cases.py` 다.",
         "수첩은 **원문 그대로**이고 요약하지 않았다(규약 5). 짚은 구절이 원문에 있는지",
         f"기계로 대조했다 — **{sum(len(q['quotes']) for g in spec['groups'] for q in g['cases'])}개 전건 통과.**", "",
         "「남은 사실」은 표식을 글자로 찾은 값이라 **말 바꿔 쓴 것을 놓친다.**",
         "케이스 9번이 바로 그 자리다 — 숫자를 그대로 믿지 말고 수첩을 읽으라는 뜻이다.", ""]
    L += blocks
    L += ["", "---", "",
          "## 더 넣으려면", "",
          "`_cases.json` 에 좌표와 사유와 짚을 구절을 적고 `build_cases.py` 를 다시 돌린다.",
          "구절이 원문에 없으면 관문이 즉사하므로, 옮겨 적다 틀리면 원장에 안 실린다.", ""]

    out = HERE / f"CASES_{today}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"케이스 {n}개 · 짚은 구절 전건 원문 대조 통과 → {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
