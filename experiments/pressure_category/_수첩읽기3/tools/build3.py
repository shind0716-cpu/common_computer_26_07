# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 조각 3차 — 파일럿(원칙+항목) 수첩. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/build3.py

## 무엇을 뽑나

파일럿 `wonval_*`(원칙 여섯 + A 항목 셋) 66판 **전수**를 조각 여섯으로 나눈다.
표본이 아니다 — 이 조건은 66판이 전부다.

    11_원칙항목_압박없음_1..3   각 11판 33장   (C0 33판을 반복 1·2·3 으로 가름)
    12_원칙항목_반대로_1..3     각 11판 33장   (C2 33판을 같은 방식으로)

반복으로 가르면 조각마다 **재료 11벌이 한 번씩** 들어가 재료 치우침이 안 생긴다.

## 1·2차와 다른 것 — 여섯째 물음이 붙는다

코워크에 회신하며 적은 대로, 지금까지 판독물은 **판당 수치를 안 냈다.**
그래서 뜻 판독·기계와 나란히 못 놓았다. 이번에는 물음 다섯에

> 「처음 준 사실 열둘 중 몇 개가 마지막 수첩에 남았습니까. 번호를 적으십시오.」

를 여섯째로 붙인다. 그러면 **사람·기계 두 값이 같은 66판에서 나란히 선다**
(기계값은 이미 있다 — 압박없음 3.64 · 반대로 3.21).

판 머리에 실행 이름을 넣는다(2차와 같음). 1·2차 조각은 안 건드린다.

산출: 11_*.md · 12_*.md · _KEY3.json
"""
import json
import os
import pathlib
import collections

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))


def 판모으기(각본):
    out = []
    for p in sorted((R / "runs" / "gpt").glob(f"*/run_{각본}_wonval_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if len(d.get("notes") or []) < 3:
            continue
        out.append((p, d))
    return out


def main():
    key = {}
    쓴 = []
    for 각본, 이름, 라벨 in (("C0", "11_원칙항목_압박없음", "압박 없음"),
                          ("C2", "12_원칙항목_반대로", "반대로 압박")):
        판들 = 판모으기(각본)
        묶 = collections.defaultdict(list)
        for p, d in 판들:
            묶[str(d.get("rep"))].append((p, d))
        for rep in sorted(묶):
            덩이 = sorted(묶[rep], key=lambda t: str(t[0]))
            조각 = f"{이름}_{rep}"
            줄 = [f"# gpt 수첩 읽기 3차 — {라벨} · 반복 {rep}"
                  f" ({len(덩이)}판 · 수첩 {len(덩이) * 3}장)\n",
                  "판마다 수첩 세 장을 순서대로 싣는다. 원문 그대로다.\n",
                  "판 머리의 `run_*` 이름은 되짚기용이다. 판정에 쓰지 마라.\n",
                  "---\n"]
            for i, (p, d) in enumerate(덩이, 1):
                줄.append(f"## 판 {i:02d} — {d.get('issue_id')} · 세트 {d.get('value_set')}"
                          f" · 준 가치 {d.get('value_categories')} · {p.stem}\n")
                for j, nt in enumerate(d["notes"][:3]):
                    줄.append(f"**수첩 {j + 1}** ({len(nt)}자)\n\n> {nt}\n")
                줄.append("---\n")
                key[f"{조각}|{i:02d}"] = dict(
                    조각=조각, 판=f"{i:02d}",
                    경로=str(p.relative_to(R)).replace("\\", "/"),
                    run_id=d.get("run_id"), issue=d.get("issue_id"),
                    세트=d.get("value_set"), 각본=d.get("script"),
                    정렬답=d.get("aligned"), 최종답=d.get("final_poll"))
            (H / f"{조각}.md").write_text("\n".join(줄), encoding="utf-8")
            쓴.append((조각, len(덩이)))

    (H / "_KEY3.json").write_text(json.dumps(dict(
        비고=("파일럿 wonval_*(원칙 여섯 + A 항목 셋) 66판 전수. "
            "반복으로 갈라 조각마다 재료 11벌이 한 번씩 들어간다."),
        판=key), ensure_ascii=False, indent=1), encoding="utf-8")
    for 조각, n in 쓴:
        print(f"  {조각:26s} {n}판 · 수첩 {n * 3}장")
    print(f"\n조각 {len(쓴)}개 · 판 {sum(n for _, n in 쓴)} · 수첩 {sum(n for _, n in 쓴) * 3}장")


if __name__ == "__main__":
    main()
