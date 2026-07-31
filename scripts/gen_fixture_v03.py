"""스키마 v0.3 픽스처 생성기 — prompt_assembly · injected_text 가 실제로 든 로그 한 벌.

왜 필요한가: 리포·파일럿의 debate 로그 4개는 전부 v0.2 시절 산출물이라 입력 쪽 기록이
`prompt_hash` 하나뿐이다(해시는 위조 검증만 되고 복원은 안 된다). v0.3 이벤트는
2026-07-28 15:02(0dd86ac)에 엔진에 들어갔고 파일럿은 그날 11:51에 돌았다 — 3시간 차이로
데이터가 없다. 입력 전문 뷰는 그 데이터 위에서만 검증할 수 있으므로, **API 호출 0회**로
같은 엔진을 돌려 픽스처를 발행한다.

gen_dryrun2 전례를 따른다(엔진 무수정 + 주입 슬롯 사용):
- utterance_fn = 결정론적 모의 발화 (dryrun2 와 같은 규칙: 라운드마다 근거 1개 탈락)
- judge_vote_fn = judge._offline_vote (루프 내 판정도 원문 부분일치 — 장부 v0 가 요구)
→ 라운드가 지나며 실제로 팩트가 사라지고, r>=2 에서 재주입이 걸려 injected_text 가 생긴다.

dryrun2 를 덮지 않는다(별도 run_id). dryrun2 는 장부가 꺼진 정본 픽스처이고 테스트·문서가
그 수치를 인용한다 — 이 파일은 장부를 켠 v0.3 예시라는 다른 자리를 채운다.

**지위: 픽스처.** 발화가 모의이므로 이 run 의 수치는 실험 결과가 아니고 인용하지 않는다.

사용: python -m scripts.gen_fixture_v03
산출: data/debates/debate_issue_esa_fixture_v03.jsonl
      data/judgments/judgment_issue_esa_fixture_v03.json
      (둘 다 validate 자기검사 + debate 는 --deep 재조립 해시 검증까지 통과해야 끝난다)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# python scripts/gen_fixture_v03.py 직접 실행 대비 (권장: python -m scripts.gen_fixture_v03)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules import debate_engine, judge, paths, validate  # noqa: E402

ISSUE = "issue_esa"
RUN = "fixture_v03"
CONFIG = Path(__file__).resolve().parent.parent / "configs" / "fixture_v03.yaml"

SEP = " | "
PREFIX = "근거: "


def mock_utterance(inputs: str, model=None, temperature=None) -> str:
    """저자 프롬프트를 파싱해 결정론적 발화를 만든다 (LLM 대역, gen_dryrun2 와 같은 규칙).

    continue 프롬프트의 맨 끝은 'Your previous view:' 섹션이라, 그 뒤만 보면 이웃 발화나
    재주입 블록에 섞인 팩트 원문과 혼동하지 않는다 — 즉 **재주입이 곧 부활로 이어지지
    않는다**. 재주입 효과가 자동으로 성공하는 픽스처는 장부 화면 검증에 쓸모가 없다.
    """
    if "Your previous view:" in inputs:
        prev = inputs.split("Your previous view:")[-1]
        m = re.search(rf"{PREFIX}(.*)", prev)
        facts = [f.strip() for f in (m.group(1).split(SEP) if m else []) if f.strip()]
        if len(facts) > 1:
            facts = facts[:-1]          # 라운드마다 근거 1개 소실
        return "여전히 제 입장을 유지합니다. " + PREFIX + SEP.join(facts)

    ans = re.search(r'your answer is "([^"]+)"', inputs)
    stance = "찬성" if (ans and ans.group(1) == "yes") else "반대"
    facts_block = inputs.split("Facts:")[-1]
    facts = [ln.strip() for ln in facts_block.splitlines() if ln.strip()]
    return f"저는 {stance} 입장입니다. " + PREFIX + SEP.join(facts)


def offline_vote(fact: dict, stage_utterances: list[dict]) -> dict:
    """루프 내 판정 대역 — judge 의 오프라인 스텁을 그대로 쓴다(뷰어·픽스처 모두 재구현 금지)."""
    return judge._offline_vote(fact, stage_utterances)


def main() -> None:
    debate_path = debate_engine.run(ISSUE, RUN, CONFIG,
                                    utterance_fn=mock_utterance,
                                    judge_vote_fn=offline_vote)

    cfg = judge._load_config(CONFIG)
    result = judge.judge_debate(ISSUE, RUN, cfg, offline=True)
    out_path = paths.judgment(ISSUE, RUN)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # 자기검사 (CLAUDE.md 규칙 3). --deep 은 prompt_assembly 명세대로 재조립한 sha256 이
    # utterance.prompt_hash 와 같은지까지 본다 — 이 픽스처의 존재 이유가 그 이벤트이므로
    # 얕은 검사만 통과해서는 발행하지 않는다.
    validate.validate(debate_path)
    validate.validate(out_path)
    validate.validate(debate_path, deep=True)

    events = [json.loads(ln) for ln in
              debate_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    n_pa = sum(1 for e in events if e.get("event") == "prompt_assembly")
    injects = [e for e in events if e.get("event") == "ledger_inject"]
    n_text = sum(1 for e in injects if e.get("injected_text"))

    print(f"[fixture_v03] debate   = {debate_path}")
    print(f"[fixture_v03] judgment = {out_path}")
    print(f"[fixture_v03] prompt_assembly {n_pa}건 · ledger_inject {len(injects)}건"
          f"(injected_text 원문 {n_text}건)")
    print(f"[fixture_v03] far_system={result['summary']['far_system']} "
          f"far_critical={result['summary']['far_critical']} — 모의 발화이므로 인용 금지")
    if n_pa == 0 or n_text == 0:
        raise SystemExit("[fixture_v03] v0.3 이벤트가 안 생겼다 — 픽스처의 목적 미달, 발행 중단")


if __name__ == "__main__":
    main()
