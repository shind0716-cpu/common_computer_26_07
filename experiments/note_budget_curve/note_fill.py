"""[수첩 예산 트랙 · 김요한] 수첩에 무엇이 채워졌나 — 글자 회계 (LLM 호출 0)

계기: 2026-08-19 중간보고서 v5 리뷰 댓글 — *"버리는 값 대신에 어떤 값이 채워지는가를
보셔야 합니다."* 지금 우리 지표는 "사실 12개 중 몇 개가 남았나"뿐이라, 사실이 빠진 자리에
무엇이 들어찼는지를 세지 않는다. 이 스크립트가 그 빈칸을 센다.

읽기 전용이다. `experiments/memory_structure/`(민옥 소유)의 v1 산출물을 읽기만 하고
한 글자도 쓰지 않는다. 앵커 정규식은 `analyze_solo.ANCHORS`를 그대로 가져다 쓴다
(다시 적으면 두 벌이 되고 언젠가 어긋난다).

## 세는 규칙 (숫자를 보기 전에 고정한다)

1. **대상** — v1 수첩 런만. `run_<A|P|B>_note_rep<1-3>.json` 형태의 run_id 만 받는다
   (예산 스윕 접미사 `_b250` 등이 붙은 런은 제외). 2모델 × 진행 3 × 반복 3 = 18런,
   런마다 수첩 3개(r0·r1·r2) = 54수첩.

2. **글자 수 단위** — 파이썬 `len`, 공백·문장부호 포함. 러너의 예산 계산과 같은 단위다.

3. **문장 쪼개기** — 줄바꿈으로 먼저 자르고, 각 줄을 `(?<=[.!?])\\s+` 로 다시 자른다.
   빈 조각은 버린다. 조각이 하나도 안 나오면 수첩 전체를 문장 하나로 본다.

4. **문장 라벨 — `has_fact`** — 앵커 12개 정규식 중 하나라도 걸리면 사실 문장.
   정규식이 정하므로 사람 판단이 안 들어간다(8/13 보존 등급 코드북이 애매 30%로 무너진
   지점을 피한다).

5. **문장 라벨 — `has_marker`** — 아래 표지어 중 하나라도 들어 있으면 표지어 문장.
   목록은 **프롬프트 문면에서** 뽑았다(수첩 원문을 보고 고른 게 아니다):
   프롬프트의 "너의 입장은 … 끝까지 유지한다" 와 수첩 지시문의 "다음 라운드의 너는 …
   수첩만 보게 된다" 에서 온 말들이다.

   두 라벨은 **배타가 아니다.** 한 문장이 사실도 담고 표지어도 담을 수 있다. 그래서
   집계는 `has_fact` 를 1차 분모로 쓰고, 표지어는 **사실 없는 문장 안에서만** 따로 센다
   (이중 계상을 만들지 않기 위해서다).

6. **누락 심문** — 문장 글자 수의 합은 수첩 총 글자 수보다 작다(잘라낸 공백·줄바꿈이
   빠진다). 그 차이를 `sep_chars` 로 같이 내놓는다. 합이 총계와 안 맞는 것을 숨기지 않는다.

## 지위

**탐색**이다. 사전등록에 없던 지표이고, 기존 산출물을 사후에 다시 센 것이다. 방향을 보는
단서로만 쓴다. 표지어 목록은 이 파일에 박혀 있으니, 다른 목록으로 다시 세고 싶으면
`MARKERS` 만 바꿔 다시 돌리면 된다.

실행: `python experiments/note_budget_curve/note_fill.py`
산출: 같은 폴더에 `note_fill_<날짜>.json`(원자료) + `note_fill_<날짜>.md`(요약표)
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "memory_structure"))

from analyze_solo import ANCHORS  # noqa: E402  (앵커 정본 — 다시 적지 않는다)

SOLO_RUNS = ROOT / "experiments" / "memory_structure" / "runs"
NOTE_BUDGET_V1 = 500
RUN_ID_V1 = re.compile(r"^[APB]_note_rep[123]$")

# 프롬프트 문면에서 뽑은 표지어 (수첩 원문을 보고 고른 것이 아니다 — 규칙 §5)
MARKERS = ("입장", "유지", "끝까지", "다음 라운드", "수첩", "기억", "잊지", "명심", "반드시", "강조")

ARM_NAME = {"A": "반복", "P": "강제 전진", "B": "숙의"}


def split_sentences(text: str) -> list[str]:
    """규칙 §3 — 줄바꿈 → 문장부호 순으로 자른다."""
    out: list[str] = []
    for line in text.split("\n"):
        for part in re.split(r"(?<=[.!?])\s+", line):
            part = part.strip()
            if part:
                out.append(part)
    return out or ([text.strip()] if text.strip() else [])


def label(sent: str) -> tuple[bool, bool]:
    """규칙 §4·§5 — (사실 있음, 표지어 있음)."""
    has_fact = any(re.search(rx, sent) for rx in ANCHORS.values())
    has_marker = any(m in sent for m in MARKERS)
    return has_fact, has_marker


def account(note: str) -> dict:
    """수첩 하나의 글자 회계."""
    sents = split_sentences(note)
    fact_chars = nofact_chars = marker_chars = 0
    n_fact = n_nofact = n_marker = 0
    for s in sents:
        has_fact, has_marker = label(s)
        if has_fact:
            fact_chars += len(s)
            n_fact += 1
        else:
            nofact_chars += len(s)
            n_nofact += 1
            if has_marker:                 # 규칙 §5 — 사실 없는 문장 안에서만 센다
                marker_chars += len(s)
                n_marker += 1
    total = len(note)
    return {
        "total_chars": total,
        "slack_chars": NOTE_BUDGET_V1 - total,
        "n_sentences": len(sents),
        "fact_chars": fact_chars, "n_fact_sentences": n_fact,
        "nofact_chars": nofact_chars, "n_nofact_sentences": n_nofact,
        "marker_chars": marker_chars, "n_marker_sentences": n_marker,
        "sep_chars": total - (fact_chars + nofact_chars),   # 규칙 §6
        "facts_hit": sorted(fid for fid, rx in ANCHORS.items() if re.search(rx, note)),
    }


def collect() -> list[dict]:
    rows: list[dict] = []
    for model_dir in sorted(p for p in SOLO_RUNS.iterdir() if p.is_dir() and p.name != "_dry"):
        for rp in sorted(model_dir.glob("run_*.json")):
            run = json.loads(rp.read_text(encoding="utf-8"))
            if run.get("memory") != "note" or not RUN_ID_V1.match(run.get("run_id", "")):
                continue
            budget = (run.get("meta") or {}).get("note_budget", NOTE_BUDGET_V1)
            if budget != NOTE_BUDGET_V1:
                continue
            for i, note in enumerate(run.get("notes") or []):
                rows.append({
                    "model": model_dir.name, "run_id": run["run_id"],
                    "arm": run["arm"], "arm_name": ARM_NAME.get(run["arm"], run["arm"]),
                    "rep": run["rep"], "note_index": i, "round": f"r{i}",
                    **account(note),
                })
    return rows


def mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def group_table(rows: list[dict], key) -> list[tuple]:
    buckets: dict = defaultdict(list)
    for r in rows:
        buckets[key(r)].append(r)
    out = []
    for k in sorted(buckets):
        g = buckets[k]
        out.append((
            k, len(g),
            mean([r["total_chars"] for r in g]),
            mean([r["slack_chars"] for r in g]),
            mean([r["fact_chars"] for r in g]),
            mean([r["nofact_chars"] for r in g]),
            mean([r["marker_chars"] for r in g]),
            mean([len(r["facts_hit"]) for r in g]),
        ))
    return out


HEAD = ("| {} | 수첩 수 | 총 글자 | 여백 | 사실 글자 | 사실없음 글자 | └표지어 글자 | 앵커 사실 수 |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n")
ROW = "| {} | {} | {:.0f} | {:.0f} | {:.0f} | {:.0f} | {:.0f} | {:.1f} |\n"


def render(rows: list[dict]) -> str:
    md = ["# 수첩에 무엇이 채워졌나 — 글자 회계 (v1 54수첩, 실호출 0)\n",
          "> 지위: **탐색**. 사전등록에 없던 지표를 기존 산출물에 사후 적용했다. 방향의 단서로만 쓴다.\n",
          f"\n대상 {len(rows)}수첩 · 예산 {NOTE_BUDGET_V1}자 · 세는 규칙은 `note_fill.py` 독스트링에 고정.\n",
          f"\n표지어 목록: {' · '.join(MARKERS)}\n"]

    for title, key, label_col in [
        ("모델별", lambda r: r["model"], "모델"),
        ("라운드별", lambda r: r["round"], "라운드"),
        ("모델 × 라운드", lambda r: f'{r["model"]} {r["round"]}', "모델·라운드"),
        ("모델 × 진행", lambda r: f'{r["model"]} {r["arm"]}({r["arm_name"]})', "모델·진행"),
    ]:
        md.append(f"\n## {title}\n\n")
        md.append(HEAD.format(label_col))
        for k, n, tot, slack, fc, nfc, mc, nf in group_table(rows, key):
            md.append(ROW.format(k, n, tot, slack, fc, nfc, mc, nf))

    # 런 안에서 짝지어 본 r0 → r2 변화 (조건 간 비교가 아니라 같은 런 안의 이동)
    paired: dict = defaultdict(dict)
    for r in rows:
        paired[(r["model"], r["run_id"])][r["round"]] = r
    md.append("\n## 런 안에서 짝지은 r0 → r2 변화\n\n"
              "조건끼리 비교한 게 아니라 **같은 런의 첫 수첩과 마지막 수첩**을 뺀 값이다.\n\n"
              "| 모델 | 런 | 사실 글자 | 사실없음 글자 | 총 글자 |\n|---|---|---:|---:|---:|\n")
    n_dec = n_pair = 0
    for k in sorted(paired):
        g = paired[k]
        if "r0" not in g or "r2" not in g:
            continue
        n_pair += 1
        df = g["r2"]["fact_chars"] - g["r0"]["fact_chars"]
        dn = g["r2"]["nofact_chars"] - g["r0"]["nofact_chars"]
        dt = g["r2"]["total_chars"] - g["r0"]["total_chars"]
        n_dec += df < 0
        md.append(f"| {k[0]} | {k[1]} | {df:+d} | {dn:+d} | {dt:+d} |\n")
    md.append(f"\n사실 글자가 줄어든 런 {n_dec}/{n_pair}. "
              "총 글자가 거의 안 움직이는데 안의 구성이 바뀌는 런에 주목 — 그게 자리를 비우지 않고 "
              "바꿔 넣었다는 뜻이다.\n")

    sep = [r["sep_chars"] for r in rows]
    md.append(f"\n## 누락 심문 (규칙 §6)\n\n문장 글자 수 합과 수첩 총 글자 수의 차이"
              f"(잘라낸 공백·줄바꿈): 평균 {mean(sep):.1f}자 · 최대 {max(sep)}자.\n"
              "표의 `사실 글자 + 사실없음 글자`가 `총 글자`보다 이만큼 작다.\n")

    md.append("""
## 이 자가 못 재는 것 (읽기 전에)

**「사실없음」은 사실이 없다는 뜻이 아니라 앵커가 안 걸렸다는 뜻이다.** 수첩 문장을 눈으로
대조하면 「사실없음」에 최소 세 가지가 섞여 있다.

1. **앵커가 놓친 사실** — 예: `- 안전: 배상책임보험 가입(필수 요건 충족)`.
   12번 사실(무레온이 보험 증서를 첨부)인데 앵커가 `증서`라서 「가입」으로 쓰면 안 걸린다.
   `- 시설: 공사로 실내 이용 불가` 도 7번 사실이지만 앵커 `배관`이 없어 놓친다.
2. **자기 지시·전략** — 예: `다림재의 '안전 미확보'를 강력 비판할 것.` 이건 진짜로 사실이 아니다.
3. **구조 부호** — `1.` `2.` `최종 입장` 같은 제목·번호.

그래서 이 표에서 **사실 글자는 하한, 사실없음 글자는 상한**이다.

주의: 본실험 보고서가 말한 "앵커 스캔은 관대해서 도달률이 상한"과 **방향이 반대다.**
거기는 발화에서 표식 하나만 걸려도 전달로 세는 관대함이고, 여기는 문장 단위라 의역을
놓치는 엄격함이다. 두 한정을 같은 것으로 묶어 인용하면 안 된다.

따라서 아래 라운드별 감소(`사실 글자`가 r0→r2 로 줄고 `사실없음`이 느는 것)에는
**설명이 둘 있고 이 자로는 못 가른다**: ⓐ 사실이 실제로 빠졌다 ⓑ 사실이 남아 있는데
표현이 원문에서 멀어져 앵커가 덜 걸린다. ⓑ를 가르려면 보존 등급(원문/의역/방향만) 같은
분류 단위가 있어야 한다 — 8/13 에 만들었다 폐기한 그 자리다.
""")
    return "".join(md)


def main() -> None:
    rows = collect()
    if not rows:
        raise SystemExit("v1 수첩 런을 못 찾았다 — runs/<model>/run_*_note_rep*.json 확인")
    stamp = "2026-08-19"
    (HERE / f"note_fill_{stamp}.json").write_text(
        json.dumps({"schema": "note_fill_v1", "budget": NOTE_BUDGET_V1,
                    "markers": list(MARKERS), "rows": rows},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / f"note_fill_{stamp}.md").write_text(render(rows), encoding="utf-8")
    print(f"[done] {len(rows)}수첩 · note_fill_{stamp}.json / .md")


if __name__ == "__main__":
    main()
