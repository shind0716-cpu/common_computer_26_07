"""[재료 확장 · 김요한] 본문 판본 만들기 — 역할 묘사만 바꾼 대조군 (LLM 호출 0)

계기: 2026-08-19 요한. `{{body}}` 는 `coop_initial`·`coop_continue`·`coop_final` 등
**모든 토론 프롬프트에 들어간다**. 그래서 본문이 나열한 역할을 에이전트가 매 라운드 본다.
그런데 자기가 그중 누구인지는 모른다 — `perspective` 는 프롬프트 밖이다.

## 왜 이게 변수인가

에이전트는 자기 역할을 모르지만 **자기가 쥔 팩트로 유추해 자칭할 수 있다.** 접수 번호를
아는 쪽이 "제가 접수를 맡았는데" 라고 말하면 그 순간 권위가 생긴다. 그러면 다른 쪽이
검증 없이 따를 수 있고, 재료가 재려던 것(흩어진 사실이 모이는가)이 "누가 말했나"로 바뀐다.
문헌 카드 12(권위 −43%)·카드 04(동조)가 가리키는 자리다.

## 축은 세 칸이고 지금 첫 칸이 비어 있다

| 칸 | 뜻 | 재료 |
|---|---|---|
| `flat` 평평 | 역할을 아예 안 적는다 | **없음** |
| `source` 정보 출처 | 누가 무엇을 알아봤나 (회계 담당·서기) | camp · hire · throne |
| `authority` 판정 권위 | 누가 무엇을 판정할 권한이 있나 (심사위원·의무관·법무) | polar · exile · award |

**지금까지 돌린 런은 전부 역할이 있는 조건이었다.** 통제된 적이 없다.

## 이 도구가 하는 일

원본 재료의 **본문 한 대목만** 갈아 새 이슈를 만든다. 팩트·배분·앵커는 손대지 않고
`issue_id` 만 바꿔 복사한다. 그래서

- **prior 프로브를 다시 안 돌려도 된다** — 팩트 문면이 글자 하나 안 바뀌므로 원본의
  known 0/12 가 그대로 유효하다(복사한 `prior` 칸이 그 증거를 들고 간다)
- 앵커도 그대로다. 다만 **새 본문에 앵커가 새는지는 다시 검사한다**
- 두 판본의 차이가 본문 한 대목뿐이므로 결과 차이를 그 대목에 돌릴 수 있다

실행: `python 시나리오/make_body_variant.py issue_award flat`
산출: 같은 폴더에 `issue_<원본>_<판본>.json` · `facts_...` · `assignment_...` 3종
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 재료별 판본 사전. cut 은 원본 본문에서 **정확히 한 번** 나와야 하고, put 이 그 자리를
# 대신한다. 통째로 새 본문을 적지 않는 이유: 무엇이 바뀌었는지가 이 파일에 남아야
# 나중에 "본문 어느 대목이 결과를 갈랐나"를 말할 수 있기 때문이다.
VARIANTS: dict[str, dict[str, dict[str, str]]] = {
    "issue_award": {
        "flat": {
            "cut": ("심사위원장은 네 사람을 불러 모았다. 접수를 받은 사무국 간사, "
                    "제작 자료를 살핀 기술 심사위원, 작품을 평한 비평 심사위원, "
                    "규정을 다루는 법무 담당이다. 저마다 아는 것이 다르다."),
            "put": ("심사위원장은 네 사람을 불러 모았다. 넷은 각자 다른 자료를 "
                    "살펴본 뒤 모여 아는 것을 나누고 하나를 정하기로 했다."),
        },
    },
}


def anchors_of(src: str) -> dict[str, str]:
    """앵커는 그 재료의 build 스크립트가 정본이다.

    채점기(analyze_solo)에서 읽지 않는다 — 거기 등록돼 있어야만 판본을 만들 수 있게
    되면, 본문 한 줄 바꾸는 일에 채점기 수정이 딸려 온다. 판본 만들기는 본문만
    건드리는 일로 두고, 채점기 등록은 그 재료를 실제로 채점할 때 따로 한다.
    """
    import importlib.util
    p = HERE / f"build_{src}.py"
    if not p.exists():
        raise SystemExit(f"빌드 스크립트가 없다: {p.name} — 앵커 정본을 못 찾는다.")
    spec = importlib.util.spec_from_file_location(f"_build_{src}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ANCHORS


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("사용: make_body_variant.py <원본 이슈> <판본 이름>\n"
                         f"  등록된 것: "
                         + " · ".join(f"{k} → {'/'.join(v)}" for k, v in VARIANTS.items()))
    src, tag = sys.argv[1], sys.argv[2]
    if src not in VARIANTS or tag not in VARIANTS[src]:
        raise SystemExit(f"등록 안 된 판본: {src} / {tag}")
    spec = VARIANTS[src][tag]
    dst = f"{src}_{tag}"

    issue = json.loads((HERE / f"{src}.json").read_text(encoding="utf-8"))
    facts = json.loads((HERE / f"facts_{src}.json").read_text(encoding="utf-8"))
    assign = json.loads((HERE / f"assignment_{src}.json").read_text(encoding="utf-8"))

    body = issue["body"]
    if body.count(spec["cut"]) != 1:
        raise SystemExit(f"cut 대목이 본문에 {body.count(spec['cut'])}번 나온다 — 1번이어야 한다.")
    new_body = body.replace(spec["cut"], spec["put"])

    issue["body"] = new_body
    issue["issue_id"] = dst
    issue["title"] = issue["title"] + f" [{tag}]"
    issue["_note"] = (f"본문 판본 — 원본 {src} 에서 역할 묘사 대목만 갈았다({tag}). "
                      f"팩트·배분·앵커는 원본과 글자 하나 안 다르므로 prior 프로브 재실행이 "
                      f"필요 없다(복사한 prior 칸이 원본의 known 결과를 들고 간다). "
                      f"두 판본의 차이가 이 한 대목뿐이라 결과 차이를 여기에 돌릴 수 있다. "
                      f"⚠ 이 판본은 원본과 fact_id 가 같다 — 두 판본의 산출물을 합칠 때는 "
                      f"반드시 (issue_id, fact_id) 쌍을 키로 잡아라. fact_id 만으로 세면 "
                      f"두 조건이 한 칸으로 합쳐진다. "
                      f"원본 메모: {issue.get('_note', '')}")
    facts["issue_id"] = dst
    # 원본 메모에는 "prior 값이 null 이면 아직 안 돈 것" 같은 안내가 들어 있는데 판본에는
    # 안 맞는다 — 판본은 원본의 프로브 결과를 그대로 들고 오기 때문이다. 그 문장을 찾아
    # 갈아 끼우면 원본 문면이 바뀔 때 조용히 깨지므로, 앞에 덮어쓰는 문장을 둔다.
    facts["_note"] = (
        f"본문 판본 {tag} — 팩트는 {src} 와 글자 하나 안 다르고, prior 도 {src} 의 "
        f"프로브 결과를 그대로 들고 왔다(재실행 불필요). fact_id 도 원본과 같으므로 "
        f"산출물을 합칠 때는 (issue_id, fact_id) 쌍을 키로 잡아라. "
        f"아래는 원본 메모이며, 그 안의 prior 안내 문장은 이 판본에 해당하지 않는다. "
        + facts.get("_note", ""))
    assign["issue_id"] = dst

    out = {HERE / f"{dst}.json": issue,
           HERE / f"facts_{dst}.json": facts,
           HERE / f"assignment_{dst}.json": assign}
    for p, d in out.items():
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[생성] {', '.join(p.name for p in out)}\n")

    # ── 검사 ──
    bad = 0

    def line(name: str, ok: bool, detail: str = "") -> None:
        nonlocal bad
        bad += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}{('  ' + detail) if detail else ''}")

    src_facts = json.loads((HERE / f"facts_{src}.json").read_text(encoding="utf-8"))
    line("팩트 문면이 원본과 동일",
         [f["text"] for f in facts["facts"]] == [f["text"] for f in src_facts["facts"]])
    line("prior 가 그대로 따라왔다",
         all(f["prior"]["score"] is not None for f in facts["facts"]),
         f"{sum(1 for f in facts['facts'] if f['prior']['score'] is not None)}/12 기입")
    src_assign = json.loads((HERE / f"assignment_{src}.json").read_text(encoding="utf-8"))
    line("배분이 원본과 동일",
         [a["assigned_fact_ids"] for a in assign["agents"]]
         == [a["assigned_fact_ids"] for a in src_assign["agents"]])

    anchors = anchors_of(src)
    leak = [k for k, rx in anchors.items() if re.search(rx, new_body)]
    line("새 본문에 앵커 누출 0", not leak, str(leak) if leak else f"본문 {len(new_body)}자")
    line("본문이 실제로 바뀌었다", new_body != body,
         f"{len(body)}자 → {len(new_body)}자")
    # fact_id 는 일부러 원본과 같게 둔다 — 판본 비교가 이 도구의 목적이라 이름이 달라지면
    # 나란히 못 놓는다. 대신 합칠 때의 키 약속을 메모에 못 박았는지 검사한다.
    line("합칠 때의 키 약속이 메모에 있다",
         "(issue_id, fact_id)" in issue["_note"] and "(issue_id, fact_id)" in facts["_note"])

    print(f"\n원본 대목: {spec['cut'][:40]}…")
    print(f"바뀐 대목: {spec['put'][:40]}…")
    print(f"\n{'전부 통과' if not bad else f'실패 {bad}건'}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
