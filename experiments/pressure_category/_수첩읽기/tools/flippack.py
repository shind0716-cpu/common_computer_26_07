# -*- coding: utf-8 -*-
"""[공용 코어 · 압박×카테고리] 뒤집힌 판의 발화문 팩 — 궤적 전체를 편다. 호출 0.

    PC_ROOT=<...>/experiments/pressure_category python tools/flippack.py

## 왜 있나

판독물 18개는 **수첩만** 읽었다. 그래서 「결론이 뒤집혔다」는 말은 수첩 얘기다.
그런데 실제 답은 발화문에서 갈리고, 마지막에 `final_poll` 로 굳는다.
하이쿠 가치·반대로 조각에서 **수첩은 15/20 이 넘어갔는데 최종 답이 정렬답과
다른 것은 8/20** 이다 — 일곱 판이 수첩에서 넘어갔다가 답에서 돌아왔다(요한 지적).

그래서 뒤집혔다고 적힌 판만 골라 **발화문·수첩·최종 답을 시간 순으로** 편다.

## 팩에 무엇이 들어가나

  사안 · 선택지 둘 · 준 가치문 · 압박 대사
  발화0 → 수첩1 → 발화1 → 수첩2 → 발화2 → 수첩3 → 발화3 → 최종 답

**원문 그대로다. 자르거나 요약하지 않는다**(규약 5).

## 가리는 것

`aligned`(정렬답)를 가린다 — 실험자가 붙인 이름표지 판 안에 있는 것이 아니다.
읽는 사람은 발화0 이 무엇을 골랐는지 보면 되돌아왔는지 알 수 있다.
`script`(각본 이름)와 세트도 가린다. 압박 대사는 판 안의 말이므로 보인다.

들어오는 것: `_FLIPS.json` — 판독물이 짚은 뒤집힌 판 목록
산출: flippacks/PACK_R_*.md · _KEY_R.json
"""
import json
import os
import pathlib
import hashlib
import collections

H = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("PC_ROOT", str(H.parent)))
NAME = {"gpt": "gpt", "gemini-flash": "제미나이", "claude-haiku": "하이쿠"}
PER = 5   # 팩 하나에 판 다섯


def main():
    지도 = json.loads((H / "SLICE_MAP.json").read_text(encoding="utf-8"))["조각"]
    뒤 = json.loads((H / "_FLIPS.json").read_text(encoding="utf-8"))
    mats = {}
    for p in (R / "materials").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("issue_id"):
            mats[d["issue_id"]] = d

    항목 = []
    빠짐 = []
    for row in 뒤["rows"]:
        조각 = row["f"][5:]          # READ_ 떼기
        if 조각 not in 지도:
            빠짐.append(f"조각 없음: {조각}")
            continue
        판표 = 지도[조각]["판"]
        for fl in row["flipped"]:
            키 = f"{fl['pan']:02d}"
            if 키 not in 판표:
                빠짐.append(f"{조각} 판 {키} 가 지도에 없다")
                continue
            항목.append(dict(조각=조각, 모델=row["model"], 조건=row["cond"],
                            판=키, 판독물말=fl, **판표[키]))

    if 빠짐:
        print("짚은 판 중 못 찾은 것:")
        for x in 빠짐:
            print(f"  {x}")

    # 조각·판 순으로 — 무작위로 섞지 않는다. 이 팩은 대조가 아니라 궤적 읽기다.
    항목.sort(key=lambda x: (x["조각"], x["판"]))
    for i, it in enumerate(항목, 1):
        it["rid"] = f"R-{i:03d}"

    (H / "flippacks").mkdir(exist_ok=True)
    묶음 = collections.defaultdict(list)
    for it in 항목:
        묶음[it["조각"]].append(it)

    해시 = []
    팩수 = 0
    for 조각, lst in 묶음.items():
        for c in range(0, len(lst), PER):
            덩이 = lst[c:c + PER]
            팩수 += 1
            nn = f"{팩수:02d}"
            줄 = [f"# 팩 「되돌아옴」 {nn} — {조각} ({len(덩이)}판)\n",
                  "판마다 **발화문과 수첩을 시간 순으로** 싣는다. 원문 그대로다.\n",
                  "정렬답·각본 이름은 가렸다. 압박 대사는 판 안의 말이므로 보인다.\n",
                  "---\n"]
            for it in 덩이:
                d = json.loads((R / it["경로"]).read_text(encoding="utf-8"))
                mat = mats.get(it["issue"], {})
                opts = mat.get("options", [])
                줄.append(f"## {it['rid']}\n")
                줄.append(f"**사안** {it['issue']}\n")
                if opts:
                    줄.append(f"**선택지** 1) {opts[0]} · 2) {opts[1]}\n")
                줄.append(f"**이 판에 준 가치문**\n\n> {(d.get('value_statement') or '').strip()}\n")
                대사 = d.get("script_lines") or []
                if 대사:
                    본 = sorted(set(x for x in 대사 if x))
                    줄.append("**상대가 건넨 말**\n")
                    for x in 본:
                        줄.append(f"\n> {x}\n")
                줄.append("\n### 시간 순\n")
                에 = d.get("essays") or []
                노 = d.get("notes") or []
                for j in range(max(len(에), len(노) + 1)):
                    if j < len(에):
                        줄.append(f"\n**발화 {j}** ({len(에[j])}자)\n\n> {에[j]}\n")
                    if j < len(노):
                        줄.append(f"\n**수첩 {j + 1}** ({len(노[j])}자)\n\n> {노[j]}\n")
                줄.append(f"\n**최종 답** {d.get('final_poll')}\n")
                줄.append("\n---\n")
            p = H / "flippacks" / f"PACK_R_{nn}.md"
            p.write_text("\n".join(줄), encoding="utf-8")
            해시.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()[:12]}  flippacks/PACK_R_{nn}.md")

    (H / "flippacks" / "PACK_HASHES.txt").write_text("\n".join(해시) + "\n", encoding="utf-8")
    (H / "_KEY_R.json").write_text(json.dumps({
        it["rid"]: {k: v for k, v in it.items() if k != "rid"} for it in 항목
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"판 {len(항목)}개 · 팩 {팩수}개 ({PER}판씩)")
    for m in ("gpt", "gemini-flash", "claude-haiku"):
        n = sum(1 for x in 항목 if x["모델"] == m)
        돌 = sum(1 for x in 항목 if x["모델"] == m and x["정렬답"] and x["최종답"] == x["정렬답"])
        print(f"  {NAME[m]:6s} {n:3d}판 (그중 최종 답이 정렬답으로 돌아온 것 {돌})")


if __name__ == "__main__":
    main()
