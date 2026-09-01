"""[공용 코어 · 압박×카테고리] 신념 문장 탐침 — 18칸 세 갈래 블라인드 판독.

## 탐침은 관문이 아니다

방향이 거꾸로 읽히는 문장을 걸러내는 장치다(`PROBE_belief1_2026-08-31.md` 머리말).
떨어졌다고 그 세트를 버리는 것이 아니라, **판정 때 그 문장에 단서를 단다.**

## 왜 다시 하나 — 세 가지가 안 물어졌다

1. **합리주의(hapri)가 탐침을 안 거쳤다.** `TRACTION_belief2` §1 제목이 「초안, 탐침 전」
   이고 §끝 파이프라인도 탐침을 첫 칸에 두는데, 세트 파일 11개는 이미 지어져 있다.
2. **모델별로 안 물어봤다.** `PROBE_belief1` 은 요한 세션의 클로드가 읽은 것이다.
   문장을 **실제로 받는** 모델(하이쿠·gpt·제미니)이 같은 방향으로 읽는지는 안 쟀다.
   모델 축 실험에서 이건 전제다 — 모델이 문장을 다르게 읽으면 같은 처치가 아니다.
3. **원칙주의와 합리주의가 갈리는지 안 물었다.** 둘 다 「규칙·따짐」 쪽이라 섞일 수 있다.
   섞이면 두 기획이 같은 것을 재고 있다는 뜻이다.

## 어떻게 묻나

18문장(원칙주의 6 · 인본주의 6 · 합리주의 6)을 **씨앗 고정으로 섞어** 갈래를 가리고,
세 세계관 이름만 준 뒤 하나씩 고르게 한다. 한 모델당 콜 1회.

  갈래를 가린다      어느 세트에서 왔는지, 몇 개씩인지, 카드 이름
  가리지 않는다      세계관 셋의 이름과 한 줄 뜻 — 가리면 물음이 성립하지 않는다

「모르겠다」를 허용한다. 억지로 고르게 하면 탐침이 아니라 시험이 된다.

## 규율

호출 상한(모델 수 × 1) · 응답 **원문 그대로 보존**(요약 저장 금지) ·
`--dry` 0콜 리허설 · encoding utf-8.

사용:
  PYTHONUTF8=1 python probe_beliefs.py --dry
  PYTHONUTF8=1 python probe_beliefs.py --models claude-haiku gpt gemini-flash --allow-live
산출: PROBE_belief_models_<날짜>.json (원문 포함) · PROBE_belief_models_<날짜>.md
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from modules import llm  # noqa: E402

HERE = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
SEED = 20260901
TEMPERATURE = 0.0          # 탐침은 판독이지 생성이 아니다 — 재현 가능해야 한다

FAMILIES = {
    "wonchik": ("기준", "규칙·형평·절차를 우선한다"),
    "inbon":   ("사정", "사람의 처지와 마음을 우선한다"),
    "hapri":   ("따짐", "근거·검증·비교를 우선한다"),
}
REF = "childcare"          # 문장은 재료와 무관하다 — 아무 한 벌에서 가져온다


def load() -> list:
    items = []
    for fam in FAMILIES:
        p = HERE / "values" / f"{fam}_{REF}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        for it in d["items"]:
            items.append({"family": fam, "card": it["category"], "text": it["content"]})
    return items


def build_prompt(items: list) -> str:
    names = " · ".join(f"「{v[0]}」({v[1]})" for v in FAMILIES.values())
    lines = [
        "아래에 문장 18개가 있습니다. 각 문장이 어느 세계관에서 나온 말인지 골라 주세요.",
        "",
        f"세계관 셋: {names}",
        "",
        "규칙:",
        "- 문장 하나에 하나만 고릅니다.",
        "- 셋 중 어느 쪽인지 모르겠으면 「모르겠다」라고 적어도 됩니다. 억지로 고르지 마세요.",
        "- 세 세계관의 문장 수는 알려 주지 않았습니다. 같은 수라고 가정하지 마세요.",
        "- 앞뒤 문장과 비교하지 말고 하나씩 따로 읽어 주세요.",
        "",
        "다른 말 없이 아래 형식으로만 18줄을 적어 주세요.",
        "번호. 고른 것 | 그렇게 읽은 근거 한 줄",
        "",
    ]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it['text']}")
    return "\n".join(lines)


PICK = {"기준": "wonchik", "사정": "inbon", "따짐": "hapri"}


def parse(text: str, n: int) -> list:
    """응답에서 번호별 선택을 뽑는다. 원문은 따로 통째로 보존한다."""
    got = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d{1,2})\s*[.)]\s*(.+)", line.strip())
        if not m:
            continue
        idx, rest = int(m.group(1)), m.group(2)
        head = rest.split("|")[0]
        choice = None
        for label, fam in PICK.items():
            if label in head:
                choice = fam
                break
        if choice is None and ("모르" in head or "모름" in head):
            choice = "모르겠다"
        if 1 <= idx <= n and idx not in got:
            got[idx] = {"choice": choice, "line": rest.strip()}
    return [got.get(i, {"choice": None, "line": None}) for i in range(1, n + 1)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=["claude-haiku", "gpt", "gemini-flash"])
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--allow-live", action="store_true")
    ap.add_argument("--max-calls", type=int, default=6)
    a = ap.parse_args()
    if not a.dry and not a.allow_live:
        print("[즉사] 실호출에는 --allow-live 가 필요하다 (--dry 로 0콜 리허설)")
        return 2

    items = load()
    rng = random.Random(SEED)
    rng.shuffle(items)
    prompt = build_prompt(items)
    today = datetime.now(KST).strftime("%Y-%m-%d")

    print(f"문장 {len(items)}개 · 갈래 {len(FAMILIES)} · 씨앗 {SEED} · 모델 {len(a.models)}")
    if len(a.models) > a.max_calls:
        print(f"[즉사] 콜 상한 {a.max_calls} 초과")
        return 2

    out = {"schema": "pressure_belief_probe_v1", "status": "근거 자료 (탐침 — 관문 아님)",
           "created_at": datetime.now(KST).isoformat(timespec="seconds"),
           "seed": SEED, "temperature": TEMPERATURE, "reference_set": REF,
           "prompt": prompt,
           "key": [{"n": i + 1, "family": it["family"], "card": it["card"], "text": it["text"]}
                   for i, it in enumerate(items)],
           "readings": {}}

    if not a.dry:
        for m in a.models:
            llm.preflight(m, temperature=TEMPERATURE)
    for m in a.models:
        if a.dry:
            raw = "\n".join(f"{i}. 기준 | (0콜 리허설)" for i in range(1, len(items) + 1))
        else:
            raw = llm.obtain_response(prompt, model=m, temperature=TEMPERATURE)
        rows = parse(raw, len(items))
        hit = sum(1 for r, it in zip(rows, items) if r["choice"] == it["family"])
        unk = sum(1 for r in rows if r["choice"] == "모르겠다")
        miss = sum(1 for r in rows if r["choice"] is None)
        out["readings"][m] = {"model_id": llm.resolve_model(m), "raw": raw,   # 원문 그대로
                              "rows": rows, "correct": hit, "unknown": unk, "unparsed": miss}
        print(f"  {m:14s} 맞음 {hit}/{len(items)} · 모르겠다 {unk} · 못 읽음 {miss}")

    # ── 표
    L = [f"# 탐침 — 신념 18문장 세 갈래, 모델 셋이 읽다 ({today})", "",
         "> 지위: **근거 자료** (탐침 — 관문이 아니다). 갈래를 가리고 씨앗 고정으로 섞어",
         f"> 물었다. 온도 {TEMPERATURE} · 모델당 1콜 · 응답 원문은 json 에 그대로 있다.", "",
         "## 1. 모델별 성적", "",
         "| 모델 | 맞음 | 모르겠다 | 못 읽음 |", "|---|---:|---:|---:|"]
    for m in a.models:
        r = out["readings"][m]
        L.append(f"| {m} | {r['correct']}/{len(items)} | {r['unknown']} | {r['unparsed']} |")

    L += ["", "## 2. 갈래별 — 어느 갈래가 흐린가", "",
          "| 갈래 | " + " | ".join(a.models) + " |", "|---|" + "---:|" * len(a.models)]
    for fam, (label, _) in FAMILIES.items():
        cells = []
        for m in a.models:
            rows = out["readings"][m]["rows"]
            idx = [i for i, it in enumerate(items) if it["family"] == fam]
            cells.append(f"{sum(1 for i in idx if rows[i]['choice'] == fam)}/{len(idx)}")
        L.append(f"| {fam} 「{label}」 | " + " | ".join(cells) + " |")

    L += ["", "## 3. 섞이는 짝 — 무엇이 무엇으로 읽히나", ""]
    for m in a.models:
        rows = out["readings"][m]["rows"]
        conf = {}
        for it, r in zip(items, rows):
            if r["choice"] and r["choice"] != it["family"]:
                conf[(it["family"], r["choice"])] = conf.get((it["family"], r["choice"]), 0) + 1
        if conf:
            L.append(f"- **{m}** — " + " · ".join(
                f"{k[0]}→{k[1]} {v}" for k, v in sorted(conf.items(), key=lambda x: -x[1])))
        else:
            L.append(f"- **{m}** — 어긋난 것 없음")

    L += ["", "## 4. 문장별", "",
          "| # | 갈래 | 카드 | 문장 | " + " | ".join(a.models) + " |",
          "|---|---|---|---|" + "---|" * len(a.models)]
    for i, it in enumerate(items):
        cells = []
        for m in a.models:
            c = out["readings"][m]["rows"][i]["choice"]
            cells.append("O" if c == it["family"] else (c or "—"))
        L.append(f"| {i+1} | {it['family']} | {it['card']} | {it['text']} | "
                 + " | ".join(cells) + " |")

    L += ["", "## 5. 이 탐침이 못 말하는 것", "",
          "- 갈래를 맞히는 것과 **처치로서 작동하는 것**은 다른 물음이다. 모델이 문장을 "
          "옳게 분류해도 그 세계관대로 행동한다는 보장은 없다.",
          "- 모델당 한 번 물었다. 온도 0이라 재현은 되지만 **문항 순서 효과**는 안 쟀다.",
          "- 세 갈래를 한 번에 물었으므로 두 갈래만 줬을 때보다 어렵다 — 성적을 "
          f"`PROBE_belief1`(두 갈래 12칸)과 직접 견주지 않는다.", ""]

    tag = "_dry" if a.dry else ""
    (HERE / f"PROBE_belief_models_{today}{tag}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / f"PROBE_belief_models_{today}{tag}.md").write_text("\n".join(L), encoding="utf-8")
    print(f"→ PROBE_belief_models_{today}{tag}.json · .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
