"""[재료 확장 · 김요한] prior 프로브 — 새 재료의 팩트가 모델의 사전지식에 있나 (실호출)

camp 은 팩트 12개를 확정한 뒤 "이 특정 사실을 이미 아는가"를 물어 known 0/12 를 확인하고서야
사연을 썼다(`probe_prior.py` 의 ms1). 그 관문을 새 재료에도 건다.

## 문면을 글자 단위로 계승한다

민옥 트랙 `experiments/memory_structure/probe_prior.py` 의 `PROBE_SYSTEM` 과 `probe_prompt()`
를 그대로 옮겼다. 문면이 달라지면 camp 의 known 0/12 와 나란히 못 놓는다. **복사한 이유가
그것이고, 두 벌이 된 것은 알고 있다** — 민옥 트랙 러너는 `ISSUE_ID = "issue_camp"` 상수라
다른 이슈를 못 받고, 우리 재료는 아직 `data/` 밖에 있다. 배관이 정리되면 이 파일은 버린다.

## 판정 규칙 (계승)

- `known=true` 가 하나라도 나오면 그 팩트는 **교체 대상**이다.
- 파싱 실패는 보수적으로 `known` 으로 친다(사람 확인 대상).
- 온도 0, 팩트 단위 체크포인트(`.partial.jsonl`), 호출 상한 초과 시 즉사.
- 응답 원문을 전량 보존한다.

`prior_<issue>.json` 이 이미 있는 이슈는 건너뛴다. 그래서 재료를 더해도 새 것만 돈다.
호출 상한은 그때그때 안 돈 이슈의 팩트 수로 정하고, 실행 첫 줄에 찍는다.

실행: `PYTHONUTF8=1 python 시나리오/probe_prior_new.py`
산출: 안 돈 이슈마다 `prior_<issue>.json` + facts 파일의 `prior` 칸 기입
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 리포 최상위. 이 파일이 시나리오/ 로 옮겨져 한 칸 얕아졌다(2026-08-19) —
# 종전 HERE.parent.parent 를 그대로 두면 리포 밖을 가리켜 modules 를 못 찾는다.
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from modules.llm import obtain_response, preflight  # noqa: E402

# issue_award 추가(2026-08-19). 앞선 셋은 prior_<이슈>.json 이 이미 있어 아래 루프가
# 건너뛴다 — 그래서 이번 실행은 award 12콜만 나간다. 재실행해도 같다.
ISSUES = ("issue_throne", "issue_polar", "issue_exile", "issue_award")
PROBE_MODEL = "gpt-mini"
PROBE_PROMPT_VER = "camp-prior-v0.2"      # 문면 계승 — 버전도 그대로 둔다
TEMPERATURE = 0.0


def call_budget() -> tuple[int, list[str]]:
    """이번 실행의 호출 상한과 실제로 돌 이슈 목록.

    상한을 고정값으로 두면 재료를 더하거나 `_guard_prior` 안내대로 재프로브할 때마다
    손으로 고쳐야 하고, 안 고치면 둘째 재료가 반쯤 채워진 채 죽는다(체크포인트라
    데이터는 안전하지만 원인을 못 찾는다). 그래서 **안 돈 이슈의 팩트 수**로 정한다.
    여유 3은 재시도 몫이다 — 상한이 사라지는 것이 아니라 필요한 만큼만 열린다.
    """
    todo = [i for i in ISSUES if not (HERE / f"prior_{i}.json").exists()]
    n = sum(len(json.loads((HERE / f"facts_{i}.json").read_text(encoding="utf-8"))["facts"])
            for i in todo)
    return n + 3, todo

# ── 아래 두 개는 memory_structure/probe_prior.py 에서 글자 단위로 옮긴 것 ──
PROBE_SYSTEM = ("당신은 자신의 사전 지식을 정직하게 보고합니다. 지어내지 마세요. "
                "반드시 JSON 하나만 출력하세요.")


def probe_prompt(fact_text: str) -> str:
    user = (f"다음 진술을 보세요:\n\"{fact_text}\"\n\n"
            "맥락 문서 없이, 당신의 사전 지식만으로 이 진술이 가리키는 구체 사건·"
            "인물·수치를 이미 알고 있습니까? 일반 상식으로 그럴듯한지가 아니라, "
            "이 특정 사실을 아는지를 답하세요.\n"
            'JSON: {"known": true/false, "reason": "한 문장"}')
    return PROBE_SYSTEM + "\n\n" + user
# ──────────────────────────────────────────────────────────────────────


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    preflight(PROBE_MODEL, temperature=TEMPERATURE)
    max_calls, todo = call_budget()
    # 돈이 나가기 전에 몇 콜인지 눈으로 보게 한다.
    print(f"[probe] 이번에 돌 이슈 {todo or '없음'} · 호출 상한 {max_calls}")
    n_calls = 0
    summary = []

    for issue in ISSUES:
        facts_path = HERE / f"facts_{issue}.json"
        dst = HERE / f"prior_{issue}.json"
        partial = HERE / f"prior_{issue}.partial.jsonl"
        if dst.exists():
            print(f"[probe] {dst.name} 존재 — 스킵")
            continue

        doc = json.loads(facts_path.read_text(encoding="utf-8"))
        facts = doc["facts"]
        done: dict[str, dict] = {}
        if partial.exists():
            for line in partial.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                done[row["fact_id"]] = row
            print(f"[probe] {issue} 체크포인트 재개 — 완료 {len(done)}/{len(facts)}")

        with partial.open("a", encoding="utf-8") as fp:
            for f in facts:
                if f["fact_id"] in done:
                    continue
                if n_calls >= max_calls:
                    raise RuntimeError(f"호출 상한 {max_calls} 도달 — 중단 (체크포인트 보존)")
                raw = obtain_response(probe_prompt(f["text"]), model=PROBE_MODEL,
                                      temperature=TEMPERATURE)
                n_calls += 1
                try:
                    s = raw[raw.index("{"): raw.rindex("}") + 1]
                    known = bool(json.loads(s).get("known"))
                    parse_fail = False
                except Exception:
                    known, parse_fail = True, True
                row = {"fact_id": f["fact_id"], "score": 1.0 if known else 0.0,
                       "parse_fail": parse_fail, "raw": raw}
                done[f["fact_id"]] = row
                fp.write(json.dumps(row, ensure_ascii=False) + "\n")
                fp.flush()
                mark = " ⚠" if known else ""
                print(f"[probe] {f['fact_id']} → known={known}{mark}"
                      f"{' (파싱실패→보수판정)' if parse_fail else ''} · 누적 {n_calls}")

        probed = now()
        out = {"issue_id": issue, "probe_model": PROBE_MODEL,
               "probe_prompt_ver": PROBE_PROMPT_VER, "probed_at": probed,
               "facts": [done[f["fact_id"]] for f in facts]}
        dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

        # facts 파일의 prior 칸 기입 — 나머지 필드는 건드리지 않는다
        for f in facts:
            r = done[f["fact_id"]]
            f["prior"] = {"score": r["score"], "probe_model": PROBE_MODEL,
                          "probe_prompt_ver": PROBE_PROMPT_VER, "probed_at": probed}
        facts_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

        n_known = sum(1 for r in out["facts"] if r["score"] > 0)
        summary.append((issue, n_known, len(facts)))
        print(f"[probe] {issue} 완료 — known {n_known}/{len(facts)}"
              f"{' ⚠ 교체 필요' if n_known else ' (허구성 통과)'}\n")

    print("── 요약")
    for issue, k, n in summary:
        print(f"  {issue:14s} known {k}/{n}{'  ⚠ 교체 필요' if k else '  통과'}")
    print(f"  실호출 {n_calls}회 · 모델 {PROBE_MODEL} · 온도 {TEMPERATURE}")


if __name__ == "__main__":
    main()
