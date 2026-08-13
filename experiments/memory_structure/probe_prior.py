"""[민옥 트랙 · 기억 구조 1단(담화전진)] prior 프로브 — issue_camp 팩트 12개 사전지식 질의.

PREREG(기억 구조와 정보 집합, 초안 v0) 성립 조건 "prior 관문"의 실행기.
방식: 민옥 확정 v0(transmission_pilot tp-prior-v0.1) 계승 — 맥락 문서 없이 팩트 진술만 주고
"이 특정 사실을 아는가"를 JSON으로 질의. 판정 규칙: known=true가 1건이라도 나오면 해당 팩트 교체.

tp-prior-v0.1과의 차이(그래서 prompt_ver를 올림):
- 호출 경로가 run_pilot.py 자체 chat()이 아니라 정본 modules.llm.obtain_response()다.
  obtain_response는 system 채널이 없어 system 문구를 user 프롬프트 앞에 합친다 — 전송 문자열이
  달라지므로 camp-prior-v0.2로 기록한다. 질의 본문 문구는 tp-prior-v0.1과 글자 단위 동일.

규율(CLAUDE.md): 호출 상한 MAX_CALLS · 팩트 단위 체크포인트(.partial, 재실행 시 이어감) ·
결과는 이 폴더 data/에 저장 즉시 커밋 대상 · 경로는 paths.py · encoding utf-8 · 원문 전량 보존(raw).
실행: PYTHONUTF8=1 python experiments/memory_structure/probe_prior.py   (12콜, gpt-mini)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules.llm import obtain_response, preflight  # noqa: E402

ISSUE_ID = "issue_camp"
RUN_ID = "ms1"                      # memory_structure 트랙 1차
PROBE_MODEL = "gpt-mini"            # .env OPENAI_MODEL — Anthropic 키 자리표시자(7/30 실측) 편차는 보고서에 명기
PROBE_PROMPT_VER = "camp-prior-v0.2"
MAX_CALLS = 15                      # 상한(팩트 12 + 여유). 초과 시 즉사 — 폭주 방지
TEMPERATURE = 0.0

OUT_DIR = Path(__file__).resolve().parent / "data"
DST = OUT_DIR / f"prior_{ISSUE_ID}_{RUN_ID}.json"
PARTIAL = OUT_DIR / f"prior_{ISSUE_ID}_{RUN_ID}.partial.jsonl"

PROBE_SYSTEM = ("당신은 자신의 사전 지식을 정직하게 보고합니다. 지어내지 마세요. "
                "반드시 JSON 하나만 출력하세요.")


def probe_prompt(fact_text: str) -> str:
    # 질의 본문은 tp-prior-v0.1과 글자 단위 동일. system은 채널이 없어 앞에 합친다(모듈 독스트링 참조).
    user = (f"다음 진술을 보세요:\n\"{fact_text}\"\n\n"
            "맥락 문서 없이, 당신의 사전 지식만으로 이 진술이 가리키는 구체 사건·"
            "인물·수치를 이미 알고 있습니까? 일반 상식으로 그럴듯한지가 아니라, "
            "이 특정 사실을 아는지를 답하세요.\n"
            'JSON: {"known": true/false, "reason": "한 문장"}')
    return PROBE_SYSTEM + "\n\n" + user


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    if DST.exists():
        print(f"[probe] {DST.name} 존재 — 스킵 (재실행하려면 파일을 옮기고 다시)")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    facts_doc = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))
    facts = facts_doc["facts"]

    done: dict[str, dict] = {}
    if PARTIAL.exists():  # 체크포인트 재개
        for line in PARTIAL.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            done[row["fact_id"]] = row
        print(f"[probe] 체크포인트 재개 — 완료 {len(done)}/{len(facts)}")

    preflight(PROBE_MODEL, temperature=TEMPERATURE)

    n_calls = 0
    with PARTIAL.open("a", encoding="utf-8") as fp:
        for f in facts:
            if f["fact_id"] in done:
                continue
            if n_calls >= MAX_CALLS:
                raise RuntimeError(f"호출 상한 {MAX_CALLS} 도달 — 중단 (체크포인트 보존)")
            raw = obtain_response(probe_prompt(f["text"]), model=PROBE_MODEL,
                                  temperature=TEMPERATURE)
            n_calls += 1
            try:
                s = raw[raw.index("{"): raw.rindex("}") + 1]
                known = bool(json.loads(s).get("known"))
                parse_fail = False
            except Exception:
                known, parse_fail = True, True  # 파싱 실패는 보수적으로 known 취급(사람 확인 대상)
            row = {"fact_id": f["fact_id"], "score": 1.0 if known else 0.0,
                   "parse_fail": parse_fail, "raw": raw}
            done[f["fact_id"]] = row
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
            fp.flush()
            print(f"[probe] {f['fact_id']} → known={known}"
                  f"{' (파싱실패→보수판정)' if parse_fail else ''} · 호출 {n_calls}")

    out = {"issue_id": ISSUE_ID, "run_id": RUN_ID, "probe_model": PROBE_MODEL,
           "probe_prompt_ver": PROBE_PROMPT_VER, "probed_at": now(),
           "facts": [done[f["fact_id"]] for f in facts]}
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n_known = sum(1 for r in out["facts"] if r["score"] > 0)
    print(f"[probe] 완료 → {DST.name} · known {n_known}/{len(facts)}"
          f" · {'⚠ 교체 필요 팩트 있음' if n_known else '전 팩트 통과(허구성 확인)'}")


if __name__ == "__main__":
    main()
