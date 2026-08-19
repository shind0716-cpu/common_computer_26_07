"""[수첩 예산 트랙 · 김요한] 수첩에 채워진 것 — 실물 사례 수집 (LLM 호출 0)

`note_fill.py` 가 센 "사실 아닌 글자"가 실제로 무엇인지 원문으로 보여준다. 세는 자가 아니라
**보여주는 자**다.

## 지위 — 사전 지정 지표가 아니다

여기 쓰인 낱말 목록 셋(`TITLE_GROUND`·`TITLE_DIRECTIVE`·`OUT_OF_INPUT`)은 **수첩을 읽고 나서
고른 것**이다. 사전등록에 없고, 가설을 검정하지 않는다. 사례를 같은 방식으로 다시 뽑을 수
있게 만드는 것이 목적이고, 여기서 나온 숫자는 **"내가 본 것이 몇 건이더라"** 이상이 아니다.
가설로 쓰려면 다음 실험에서 목록을 먼저 고정하고 새 재료에 걸어야 한다.

`OUT_OF_INPUT` 만은 사후 선정의 영향을 덜 받는다 — 후보 낱말이 이슈 원문과 팩트 12개 안에
실제로 있는지를 **파일로 대조**해서 없는 것만 남기기 때문이다(그 판정은 사람 취향이 아니다).
그래도 후보를 고른 것이 사람이라는 점은 그대로다.

## 무엇을 뽑나

1. **수첩 첫 줄(제목)의 r0 → r2 변화** — 수첩이 무엇이라고 자칭하는지.
2. **입력에 없는 말이 든 문장** — 이슈 원문·팩트 12개 어디에도 없는 낱말이 수첩에 나타난 곳.
3. **모델 대조** — 같은 잣대를 두 모델에 똑같이 건다.

실행: `python experiments/note_budget_curve/note_cases.py`
산출: 같은 폴더에 `note_cases_<날짜>.md`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "memory_structure"))
sys.path.insert(0, str(HERE))

from modules import paths  # noqa: E402
from note_fill import RUN_ID_V1, split_sentences  # noqa: E402

ISSUE_ID = "issue_camp"
SOLO_RUNS = ROOT / "experiments" / "memory_structure" / "runs"
MODELS = ("gemini-flash", "gpt")

# --- 사후 선정 목록 (독스트링 「지위」 참조) --------------------------------
TITLE_GROUND = ("당위성", "근거", "논거", "요약", "사유")          # 근거를 모아둔 문서라는 표시
TITLE_DIRECTIVE = ("지침", "전략", "고수", "사수", "유지",
                   "관철", "공격", "설득", "명심")                  # 행동을 지시하는 문서라는 표시
OUT_OF_INPUT_CANDIDATES = (
    "배임", "직무유기", "법적", "민주", "명분", "설득", "보상", "공격",
    "관철", "리스크", "존립", "안전망", "정당성", "치명", "신뢰", "책임",
)


def input_text() -> str:
    """이슈 원문 + 팩트 12개 — '입력에 있었나'의 대조 기준."""
    facts = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))
    issue = paths.issue(ISSUE_ID).read_text(encoding="utf-8")
    return " ".join(f["text"] for f in facts["facts"]) + " " + issue


def note_runs(model: str) -> list[dict]:
    out = []
    for p in sorted((SOLO_RUNS / model).glob("run_*.json")):
        run = json.loads(p.read_text(encoding="utf-8"))
        if run.get("memory") == "note" and RUN_ID_V1.match(run.get("run_id", "")):
            out.append(run)
    return out


def title_of(note: str) -> str:
    sents = split_sentences(note)
    return sents[0] if sents else ""


def main() -> None:
    inp = input_text()
    absent = [w for w in OUT_OF_INPUT_CANDIDATES if w not in inp]
    present = [w for w in OUT_OF_INPUT_CANDIDATES if w in inp]

    md = ["# 수첩에 채워진 것 — 실물 사례 (v1 수첩, 실호출 0)\n",
          "> 지위: **사례 수집**. 낱말 목록은 수첩을 읽고 나서 골랐다(사후 선정). "
          "가설 검정이 아니라 다음 실험에서 무엇을 사전 지정할지 정하기 위한 재료다.\n",
          f"\n대조 기준 = `{ISSUE_ID}` 이슈 원문 + 팩트 12개.\n",
          f"\n후보 낱말 중 **입력에 실제로 있던 것**(제외): {' · '.join(present) or '없음'}\n",
          f"\n입력에 없어서 사례 수집 대상이 된 낱말: {' · '.join(absent)}\n"]

    md.append("\n## 1. 수첩이 자칭하는 바 — 첫 줄의 r0 → r2\n")
    for model in MODELS:
        md.append(f"\n### {model}\n\n| 런 | r0 첫 줄 | r2 첫 줄 |\n|---|---|---|\n")
        g0 = g2 = d0 = d2 = 0
        for run in note_runs(model):
            t0, t2 = title_of(run["notes"][0]), title_of(run["notes"][2])
            g0 += any(k in t0 for k in TITLE_GROUND)
            g2 += any(k in t2 for k in TITLE_GROUND)
            d0 += any(k in t0 for k in TITLE_DIRECTIVE)
            d2 += any(k in t2 for k in TITLE_DIRECTIVE)
            md.append(f"| {run['run_id']} | {t0} | {t2} |\n")
        n = len(note_runs(model))
        md.append(f"\n- 근거말({' · '.join(TITLE_GROUND)}) 든 제목: r0 {g0}/{n} → r2 {g2}/{n}\n")
        md.append(f"- 지시말({' · '.join(TITLE_DIRECTIVE)}) 든 제목: r0 {d0}/{n} → r2 {d2}/{n}\n")

    md.append("\n## 2. 입력에 없던 말이 든 마지막 수첩(r2) 문장\n")
    for model in MODELS:
        rows = []
        for run in note_runs(model):
            for s in split_sentences(run["notes"][2]):
                hit = [w for w in absent if w in s]
                if hit:
                    rows.append((run["run_id"], hit, s))
        n_runs = len({r[0] for r in rows})
        md.append(f"\n### {model} — {len(rows)}건 / {n_runs}런\n\n")
        if not rows:
            md.append("해당 없음.\n")
            continue
        md.append("| 런 | 걸린 말 | 문장 |\n|---|---|---|\n")
        for rid, hit, s in rows:
            md.append(f"| {rid} | {' · '.join(hit)} | {s} |\n")

    md.append("""
## 읽을 때 주의

- 「입력에 없던 말」이 곧 **작화**는 아니다. 사실을 그대로 두고 함의를 덧붙인 것과, 없는 사실을
  지어낸 것은 다르다. 이 자는 둘을 못 가른다 — 가르려면 문장 단위 판독이 필요하고, 그건 사람 일이다.
- 제목 낱말 세기는 **9런 규모**다. 방향을 보는 것이지 비율을 주장하는 것이 아니다.
- 두 모델의 차이는 재료·프롬프트가 같은 조건에서 나온 것이지만, 모델 기본 성향(문체·길이)과
  섞여 있다. 분리는 안 됐다.
""")
    stamp = "2026-08-19"
    (HERE / f"note_cases_{stamp}.md").write_text("".join(md), encoding="utf-8")
    print(f"[done] note_cases_{stamp}.md")


if __name__ == "__main__":
    main()
