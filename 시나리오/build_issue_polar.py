"""[재료 확장 · 김요한] `issue_polar` — 입장 대립형 시나리오 (LLM 호출 0)

`issue_camp`·`issue_throne` 과 **다른 골격**이다. 무엇이 다르고 왜 다른지를 먼저 적는다.

## camp 골격이 재는 것과 못 재는 것

camp 계열은 **요건 N개 충족 개수**로 정답이 정해진다. 입장은 프롬프트에 고정으로 박히지만
결론이 설계상 안 움직이므로, 입장은 **배경**이지 변수가 아니다. 그래서 중간보고서 §5 ③
(*"입장은 불리한 사실을 먼저 죽인다"*)이 **탐색**에 머물렀다 — 입장을 바꿔 본 적이 없으니
"불리해서 죽었다"를 대조로 보일 수가 없다.

## 이 재료의 골격

정답을 없애고 **입장을 변수로 올린다.**

1. **정답이 없다.** 가치 판단이라 어느 쪽도 옳지 않다. 요건 충족 개수로 안 풀린다.
2. **불리 대칭.** 후송 편을 깎는 사실 4개 : 대기 편을 깎는 사실 4개. 중립 2, 양쪽 2.
3. **불리한 사실이 목록 앞뒤로 번갈아 놓인다.** camp 은 불리 팩트가 앞쪽에 몰려
   *"불리해서"* 와 *"앞이라서"* 가 안 갈렸다. 여기서는 교대로 배치해 그 교락을 뺀다.
4. **같은 재료를 두 입장으로 각각 돌린다.** 프롬프트의 입장 한 줄만 바꾸고 나머지는 전부
   같다. **입장이 바뀔 때 죽는 사실이 뒤집히면** §5 ③ 이 확증이 된다. 안 뒤집히면
   "입장이 아니라 사실 자체의 성질"이라는 다른 답이 나온다. 어느 쪽이 나와도 답이다.
5. camp 에서 **가져오는 것 하나**: 본문에 팩트 원문을 싣지 않는다. 이건 골격이 아니라
   위생이다(본문에 넣으면 배분층이 무의미해진다 — 2026-08-19 `issue_relocate_lite` 실측).

## 배분에 대하여

단독 실험(에이전트 1명)에는 배분표가 안 쓰인다 — 이 재료의 1차 용도는 단독이다.
토론용 배분표를 같이 만들어 두되 **제약을 하나 건다**: 모든 에이전트가 **자기 입장에
불리한 사실 1개 + 상대 입장에 불리한 사실 1개**를 대칭으로 보유한다. 그래야 "무엇을 말하고
무엇을 삼켰나"가 에이전트마다 같은 조건에서 읽힌다. 12팩트가 각각 한 명에게만 가므로
(밀도 1.0) 아무도 대신 꺼내주지 않는다.

**주의**: `stance` 가 `none` 이 아니면 콘솔이 재현 트랙으로 판정해 수첩 조건을 막는다
(저자 템플릿에 수첩 슬롯이 없다). 토론에 쓰려면 그 경로부터 정리해야 한다 — 이 배분표는
그때를 위한 준비물이고, 지금 당장 도는 것은 단독이다.

## 아직 안 한 것

**prior 프로브 완료** — `probe_prior_new.py`, 2026-08-19, known 0/12(실호출 12콜).

실행: `python experiments/scenario_generalization/build_issue_polar.py`
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 리포 최상위. 이 파일이 시나리오/ 로 옮겨져 한 칸 얕아졌다(2026-08-19) —
# 종전 HERE.parent.parent 를 그대로 두면 리포 밖을 가리켜 modules 를 못 찾는다.
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

IID = "issue_polar"
CREATED_AT = "2026-08-19T00:00:00+09:00"
CREATED_BY = "manual(요한 측 Claude 초안 — 팀 검수 전 후보 지위)"
PRO, CON = "후송", "대기"          # pro = 후송을 강행한다 / con = 기지에서 버틴다

# (번호, 본문, 태그, critical, 불리한 입장, 관점, 앵커)
# 불리를 PRO/CON 교대로 놓아 순서 교락을 뺀다(설계 §3).
FACTS = [
    (1, "활주로 기온이 영하 52도로 항공유 결빙 한계를 넘겼다",
     "counter_evidence", True, PRO, "비행", r"영하\s*52"),
    (2, "환자의 혈색소 수치가 사흘 만에 절반으로 떨어졌다",
     "counter_evidence", True, CON, "의무", r"혈색소"),
    (3, "가장 가까운 대체 착륙장까지 편도 여섯 시간이고 중간 급유지가 없다",
     "counter_evidence", True, PRO, "비행", r"여섯\s*시간"),
    (4, "기지에 남은 수혈용 혈액은 두 팩뿐이다",
     "counter_evidence", True, CON, "의무", r"두\s*팩"),
    (5, "지난겨울 같은 기종이 같은 조건에서 이륙 직후 되돌아온 기록이 있다",
     "counter_evidence", True, PRO, "비행", r"이륙\s*직후"),
    (6, "다음 정기 보급편은 백열흘 뒤다",
     "stance_support", True, CON, "보급", r"백열흘"),
    (7, "의무관은 이송 중 흔들림이 출혈을 키울 수 있다고 소견에 적었다",
     "stance_support", True, PRO, "의무", r"흔들림"),
    (8, "기지 의무관은 외과 수련을 받은 적이 없다",
     "counter_evidence", True, CON, "의무", r"수련"),
    (9, "기지에서 겨울을 나는 대원은 모두 열넷이다",
     "condition", False, None, "보급", r"열넷"),
    (10, "환자는 이번이 세 번째 월동이다",
     "condition", False, None, "보급", r"세\s*번째"),
    (11, "이백 킬로 떨어진 이웃 기지에 외과의가 있으나 오갈 수단은 설상차뿐이다",
     "exception", True, "both", "보급", r"설상차"),
    (12, "본부는 결정을 기지장에게 일임했고 어느 쪽도 지시하지 않았다",
     "exception", False, "both", "비행", r"일임"),
]

QUESTION = "환자를 항공편으로 후송해야 할까요?"

# 본문 — 상황만. 팩트 원문은 싣지 않는다(설계 §5).
BODY = (
    "하르뫼 기지는 대륙 안쪽 고원에 있고 지금은 월동 기간이다. 바깥과 오갈 길은 활주로 "
    "하나뿐이며, 겨울에는 그마저 날씨가 허락할 때만 열린다. 어제 저녁 대원 한 사람이 "
    "복통을 호소하며 쓰러졌고, 밤사이 상태가 나빠졌다. 기지장은 항공편으로 그를 바깥 "
    "병원까지 후송할지, 아니면 기지에 두고 버틸지를 오늘 안에 정해야 한다. 어느 쪽도 "
    "안전하지 않다는 것만 분명하다. 기지장은 네 사람을 불렀다. 조종사, 의무관, 보급 "
    "담당, 통신 담당이다. 저마다 아는 것이 다르다."
)

STUB = (
    "월동 중인 하르뫼 기지에서 대원 한 사람이 밤사이 위중해졌다. 기지장은 항공편으로 "
    "바깥 병원까지 후송할지, 기지에 두고 버틸지를 오늘 안에 정해야 한다. 어느 쪽도 "
    "안전하지 않다."
)

# 입장 문면 — 이 한 줄만 바꿔 같은 재료를 두 번 돌린다(설계 §4).
STANCE_TEXT = {
    PRO: "너의 입장은 '환자를 항공편으로 후송해야 한다'이다. 이 입장은 끝까지 유지한다.",
    CON: "너의 입장은 '후송하지 말고 기지에서 버텨야 한다'이다. 이 입장은 끝까지 유지한다.",
}

# 최종 폴링 — 정답이 없으므로 정오 판정용이 아니라 **어느 쪽으로 기울었나**의 기록이다.
FINAL_POLL_INSTR = ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                    "'후송한다' 또는 '후송하지 않는다' 중 하나만 출력하라.")

# 단독 러너가 쓰는 묶음 — 프롬프트 문면의 단일 출처(래퍼가 이것만 읽는다).
SOLO_PROMPTS = {"issue_id": IID, "stub": STUB,
                "stances": {PRO: STANCE_TEXT[PRO], CON: STANCE_TEXT[CON]},
                "final_poll": FINAL_POLL_INSTR}

# 앵커 사전 — 팩트 하나당 검색 패턴 하나. 채점기(anchor_scan)가 이것만 읽는다.
ANCHORS = {f"fact_polar_{n:02d}": a for (n, *_rest, a) in FACTS}

# 토론용 배분 — 에이전트마다 [자기 불리 1 + 상대 불리 1 + 중립·양쪽 1]. 전 팩트 고립.
ASSIGN = {
    "agent_1": ("비행", PRO, [1, 2, 9]),     # 자기 불리 01 · 상대 불리 02 · 중립 09
    "agent_2": ("의무", PRO, [7, 4, 11]),    # 자기 불리 07 · 상대 불리 04 · 양쪽 11
    "agent_3": ("비행", CON, [6, 3, 10]),    # 자기 불리 06 · 상대 불리 03 · 중립 10
    "agent_4": ("보급", CON, [8, 5, 12]),    # 자기 불리 08 · 상대 불리 05 · 양쪽 12
}


def _guard_prior(path: Path) -> None:
    """이미 prior 가 채워진 facts 파일을 덮어쓰지 않는다 (적대적 리뷰 중대 3).
    프로브는 실호출이다. 앵커 한 줄 고치려고 재빌드했다가 36콜 결과가 조용히 지워지면 안 된다."""
    if not path.exists():
        return
    try:
        cur = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if any((f.get("prior") or {}).get("score") is not None for f in cur.get("facts", [])):
        raise SystemExit(
            f"[build] {path.name} 에 prior 프로브 결과가 있다 — 덮어쓰면 실호출 결과가 사라진다. "
            f"정말 다시 만들려면 그 파일을 먼저 옮기고 프로브를 다시 돌려라.")


def fid(n: int) -> str:
    return f"fact_polar_{n:02d}"


def build_docs() -> dict:
    facts = [{
        "fact_id": fid(n), "text": t, "tags": [tag], "critical": crit,
        "prior": {"score": None, "probe_model": None,
                  "probe_prompt_ver": None, "probed_at": None},
        "_unfavorable_to": unf, "_perspective": persp,
    } for (n, t, tag, crit, unf, persp, _a) in FACTS]

    common = {"schema_ver": "0.2", "created_by": CREATED_BY,
              "created_at": CREATED_AT, "issue_id": IID}
    return {
        "issue": {
            **common, "source": "synthetic",
            "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
            "title": "하르뫼 기지 — 월동 중 환자 후송 여부",
            "question": QUESTION, "body": BODY,
            "_note": (f"입장 대립형. pro={PRO}(후송 강행) / con={CON}(기지 대기). "
                      "**정답 없음** — 가치 판단이라 요건 충족 개수로 안 풀린다. "
                      "camp 계열과 골격이 다르다: 정답 대신 입장을 변수로 올려, 같은 재료를 "
                      "두 입장으로 각각 돌리고 죽는 사실이 뒤집히는지를 본다. "
                      "본문에는 팩트 원문을 싣지 않는다(배분층 보호 — camp 에서 계승)."),
        },
        "facts": {
            **common,
            "_note": (f"후보 초안(팀 검수 전). 불리 대칭 {PRO} 4 : {CON} 4, 중립 2, 양쪽 2. "
                      "불리한 사실을 목록 앞뒤로 교대 배치해 camp 의 순서 교락을 뺐다. "
                      "requirement·share 없음 — split_pairs 가 아니라 손배분이다. "
                      "prior 는 probe_prior_new.py 가 채운다 — 값이 null 이면 아직 안 돈 것이다."),
            "extractor": {"name": "manual", "ver": "1"},
            "facts": facts,
        },
        "assignment": {
            **common, "seed": 42, "overlap_k": 1,
            "_note": ("4에이전트(관점 × 입장), 에이전트당 3팩트, 밀도 1.0(전 팩트 고립). "
                      "제약: 모든 에이전트가 자기 입장 불리 1 + 상대 입장 불리 1 을 대칭으로 "
                      "보유한다. ⚠ stance 가 none 이 아니라 현행 콘솔은 재현 트랙으로 "
                      "판정해 수첩 조건을 막는다 — 토론에 쓰려면 그 경로부터 정리 필요."),
            "agents": [{"agent_id": a, "perspective": p, "stance": s,
                        "assigned_fact_ids": [fid(n) for n in ns]}
                       for a, (p, s, ns) in ASSIGN.items()],
        },
    }


def check(docs: dict) -> int:
    anchors = {fid(f[0]): f[6] for f in FACTS}
    texts = {fid(f[0]): f[1] for f in FACTS}
    unfav = {fid(f[0]): f[4] for f in FACTS}
    bad = 0

    def line(name: str, ok: bool, detail: str = "") -> None:
        nonlocal bad
        bad += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}{('  ' + detail) if detail else ''}")

    print("── 앵커")
    miss = [k for k, rx in anchors.items() if not re.search(rx, texts[k])]
    line("자기 팩트 적중", not miss, f"미적중 {miss}" if miss else "12/12")
    cross = {k: [j for j, t in texts.items() if j != k and re.search(rx, t)]
             for k, rx in anchors.items()}
    cross = {k: v for k, v in cross.items() if v}
    line("교차 오검출 0", not cross, str(cross) if cross else "")
    for label, blob in (("본문", BODY), ("요약문", STUB),
                        ("입장문(pro)", STANCE_TEXT[PRO]), ("입장문(con)", STANCE_TEXT[CON])):
        leak = [k for k, rx in anchors.items() if re.search(rx, blob)]
        line(f"{label} 누출 0", not leak, str(leak) if leak else f"{len(blob)}자")

    print("── 구조 (입장 대립형)")
    c = Counter(unfav.values())
    line("불리 대칭 4:4", c[PRO] == 4 and c[CON] == 4, f"{PRO} {c[PRO]} : {CON} {c[CON]}")
    line("중립 2 · 양쪽 2", c[None] == 2 and c["both"] == 2, f"중립 {c[None]} · 양쪽 {c['both']}")
    order = [unfav[fid(n)] for n in range(1, 9)]
    alt = all(order[i] != order[i + 1] for i in range(len(order) - 1) if order[i] and order[i + 1])
    line("불리가 앞뒤로 교대", alt, " → ".join(str(o) for o in order))
    line("정답 필드 없음(요건 미사용)",
         all("requirement" not in f and "share" not in f for f in docs["facts"]["facts"]))

    print("── 배분 (자기 불리 1 + 상대 불리 1)")
    own = Counter(i for a in docs["assignment"]["agents"] for i in a["assigned_fact_ids"])
    for a in docs["assignment"]["agents"]:
        ids = a["assigned_fact_ids"]
        mine = [i[-2:] for i in ids if unfav[i] == a["stance"]]
        theirs = [i[-2:] for i in ids if unfav[i] not in (a["stance"], None, "both")]
        line(f"{a['agent_id']} ({a['stance']})", len(mine) >= 1 and len(theirs) >= 1,
             f"자기불리 {mine} · 상대불리 {theirs}")
    line("전 팩트 고립(밀도 1.0)", set(own.values()) == {1} and len(own) == 12,
         f"보유자 분포 {dict(sorted(Counter(own.values()).items()))} · 배분 {len(own)}개")
    return bad


def main() -> None:
    docs = build_docs()
    out = {HERE / f"{IID}.json": docs["issue"],
           HERE / f"facts_{IID}.json": docs["facts"],
           HERE / f"assignment_{IID}.json": docs["assignment"]}
    _guard_prior(HERE / f"facts_{IID}.json")
    for p, d in out.items():
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[생성] {', '.join(p.name for p in out)}\n")
    bad = check(docs)
    print(f"\n{'전부 통과' if not bad else f'실패 {bad}건'}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
