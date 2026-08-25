"""[공용 코어 · 8/21 요한 결정 (구 패키지 A · 신동범, 8/21 이적)] dryrun2 정본 픽스처 생성기 — 현 judge.py 구조의 canonical 예시.

배경(7/22): 리포에 커밋된 dryrun judgment 는 초안 judge(af4963f) 산출물이라 votes 구조가
현 judge.py 출력과 다르다(WORKLOG ⚠ 민옥 발견). 그러나 그 파일은
  1) test_ledger·test_survival 의 '구버전 votes 에서도 동작' 강건성 픽스처이고
  2) P2 입증 수치(naive FAR 0.8333 vs 조건부 0.0)의 원본이라
덮어쓰지 않는다(덮어쓰면 테스트 2클래스 + 문서 인용 수치의 재현성이 깨짐 — 7/22 검토).
대신 이 스크립트가 현 judge.py 구조의 정본 픽스처를 run_id=dryrun2 로 발행한다.
→ dryrun = 레거시 강건성 픽스처 / dryrun2 = 현행 구조 정본. 소비자는 dryrun2 를 참조할 것.

모의 규칙(결정론적, API 호출 0회):
- 초기 발화: 배분받은 팩트 원문을 전부 그대로 언급
- 이후 라운드: 자기 직전 발화의 근거 목록에서 마지막 1개를 떨군다(최소 1개는 유지)
→ 라운드가 지날수록 팩트가 실제로 소실되는, ledger·P2 가 물릴 수 있는 픽스처가 된다.
  (전부-unmentioned 인 퇴화 픽스처를 피하기 위한 설계 — 오프라인 judge 는 원문 부분일치라
   팩트 원문을 그대로 실은 발화만 mentioned 로 잡는다)

사용: python -m scripts.gen_dryrun2
산출: data/debates/debate_issue_esa_dryrun2.jsonl
      data/judgments/judgment_issue_esa_dryrun2.json  (둘 다 validate 자기검사 포함)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# python scripts/gen_dryrun2.py 직접 실행 대비 (모듈 실행 python -m scripts.gen_dryrun2 권장)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules import debate_engine, judge, paths, validate  # noqa: E402

ISSUE = "issue_esa"
RUN = "dryrun2"
CONFIG = Path(__file__).resolve().parent.parent / "configs" / "sprint_mini.yaml"

SEP = " | "
PREFIX = "근거: "


def mock_utterance(inputs: str, model=None, temperature=None) -> str:
    """저자 프롬프트 원문을 파싱해 결정론적 발화를 만든다 (LLM 대역).

    continue 프롬프트는 맨 끝이 'Your previous view:' 섹션이므로 그 뒤만 보면
    이웃 발화(others)에 섞인 근거와 혼동하지 않는다."""
    if "Your previous view:" in inputs:
        prev = inputs.split("Your previous view:")[-1]
        m = re.search(rf"{PREFIX}(.*)", prev)
        facts = [f.strip() for f in (m.group(1).split(SEP) if m else []) if f.strip()]
        if len(facts) > 1:
            facts = facts[:-1]  # 라운드마다 마지막 근거 1개 소실
        return "여전히 제 입장을 유지합니다. " + PREFIX + SEP.join(facts)

    ans = re.search(r'your answer is "([^"]+)"', inputs)
    stance = "찬성" if (ans and ans.group(1) == "yes") else "반대"
    facts_block = inputs.split("Facts:")[-1]
    facts = [ln.strip() for ln in facts_block.splitlines() if ln.strip()]
    return f"저는 {stance} 입장입니다. " + PREFIX + SEP.join(facts)


def main() -> None:
    debate_path = debate_engine.run(ISSUE, RUN, CONFIG, utterance_fn=mock_utterance)

    cfg = judge._load_config(CONFIG)
    result = judge.judge_debate(ISSUE, RUN, cfg, offline=True)
    out_path = paths.judgment(ISSUE, RUN)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # 자기검사 (CLAUDE.md 규칙 3) — 실패 시 validate 가 비정상 종료한다
    validate.validate(debate_path)
    validate.validate(out_path)

    print(f"[gen_dryrun2] debate   = {debate_path}")
    print(f"[gen_dryrun2] judgment = {out_path}")
    print(f"[gen_dryrun2] far_system={result['summary']['far_system']} "
          f"far_critical={result['summary']['far_critical']} (잠정 수식)")
    print("[gen_dryrun2] P2 확인: python -m modules.survival --issue issue_esa --run dryrun2")


if __name__ == "__main__":
    main()
