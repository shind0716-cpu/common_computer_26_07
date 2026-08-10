"""판정 축 대조 프로브 — 저자 축(발화 x 팩트목록, n=1) vs 우리 축(팩트 x 라운드, n=3).

목적: 같은 debate 로그를 두 판정 축으로 채점해 격자를 비교한다. 판정 **모델은 고정**하고
축만 바꾼다(모델 효과와 축 효과를 섞지 않기 위해).

저자 축 = DelibTrace evaluation.evaluate_facts:
  발화 1건 x 전체 팩트 목록 -> {"matched_fact_ids": [...]}, temperature 0, n=1.
  프롬프트는 저자 저장소 원문을 그대로 읽는다(복사 금지 — authors_prompts 계승 원칙).

우리 축 = 기존 judgment 산출물(재판정 없음, 파일에서 읽기만).

안전장치(CLAUDE.md 비용 주의):
  --max-calls 상한 · 발화 1건마다 체크포인트 append · 재시작 시 이어감 · --offline 0콜 검증.
LLM 응답은 원문 그대로 저장한다(규약 5) — 파싱 결과와 원문을 함께 남긴다.
"""
import argparse
import json
import re
from pathlib import Path

from modules import authors_prompts, llm, paths


# --- 저자 축 -----------------------------------------------------------------
def build_author_prompt(facts: list[dict], text: str) -> str:
    """저자 evaluate_facts 의 조립을 글자 단위로 계승 (evaluation.py:22-29)."""
    prompt = authors_prompts.load("evaluate_fact")
    fact_text = ""
    for index, item in enumerate(facts):
        fact_text += f"{index}: {item['text']}\n"
    inputs = prompt.replace("<===facts===>", fact_text)
    inputs = inputs.replace("<===text===>", text)
    return inputs


def obtain_json(data: str):
    """저자 utils.obtain_json 계승 — 실패하면 원문을 그대로 돌려준다."""
    try:
        d = data.replace("```json", "").replace("```", "").replace("\\n", "")
        return json.loads(d)
    except Exception:  # noqa: BLE001 — 저자 코드와 같은 관대한 처리
        return data


def parse_matched(raw, n_facts: int) -> tuple[list[int] | None, str]:
    """matched_fact_ids 를 뽑는다. (인덱스 목록, 파싱 상태)."""
    obj = obtain_json(raw)
    if isinstance(obj, dict) and isinstance(obj.get("matched_fact_ids"), list):
        ids = [i for i in obj["matched_fact_ids"] if isinstance(i, int) and 0 <= i < n_facts]
        return sorted(set(ids)), "json"
    # 폴백: 숫자 배열만 긁는다. 성공/실패를 반드시 구분해 기록한다(조용한 0 금지).
    m = re.search(r"matched_fact_ids\"?\s*:\s*\[([0-9,\s]*)\]", str(raw))
    if m:
        ids = [int(x) for x in re.findall(r"\d+", m.group(1)) if int(x) < n_facts]
        return sorted(set(ids)), "regex"
    return None, "parse_fail"


def offline_matched(facts: list[dict], text: str) -> list[int]:
    """0콜 검증용 결정론적 스텁 — 팩트 텍스트의 어절 겹침으로 흉내만 낸다.
    수치 인용 금지(모의 판정). 하네스 배관 확인 전용."""
    out = []
    for i, f in enumerate(facts):
        toks = [t for t in re.split(r"[\s,.·|]+", f["text"]) if len(t) >= 2]
        hit = sum(1 for t in toks if t in text)
        if toks and hit / len(toks) >= 0.5:
            out.append(i)
    return out


# --- 실행 --------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="판정 축 대조 프로브")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--model", default=None, help="생략 시 기존 judgment 의 judge.model")
    ap.add_argument("--max-calls", type=int, default=40, help="실호출 상한(초과 시 중단)")
    ap.add_argument("--offline", action="store_true", help="LLM 호출 0 — 하네스 검증용")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = out_dir / f"author_axis_{args.issue}_{args.run}.jsonl"

    facts_doc = json.loads(paths.facts(args.issue).read_text(encoding="utf-8"))
    facts = facts_doc["facts"]
    judgment = json.loads(paths.judgment(args.issue, args.run).read_text(encoding="utf-8"))
    model = args.model or judgment["judge"]["model"]

    utts = []
    for line in paths.debate(args.issue, args.run).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("event") == "utterance":
            utts.append(ev)

    done = set()
    if ckpt.exists():
        for line in ckpt.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["round"], r["agent_id"]))
    print(f"[axis] 발화 {len(utts)}건 · 팩트 {len(facts)}개 · 모델 {model} · "
          f"이미 완료 {len(done)}건 · 상한 {args.max_calls}")

    calls = 0
    with ckpt.open("a", encoding="utf-8") as fh:
        for u in utts:
            key = (u["round"], u["agent_id"])
            if key in done:
                continue
            if not args.offline and calls >= args.max_calls:
                print(f"[axis] 호출 상한 {args.max_calls} 도달 — 중단(체크포인트 저장됨). "
                      f"같은 명령으로 재시작하면 이어서 돕니다.")
                break
            text = u.get("response_text", "")
            inputs = build_author_prompt(facts, text)
            if args.offline:
                idx = offline_matched(facts, text)
                raw = json.dumps({"matched_fact_ids": idx})
                status = "offline_stub"
            else:
                raw = llm.obtain_response(inputs, model=model, temperature=0.0)
                calls += 1
                idx, status = parse_matched(raw, len(facts))
            rec = {
                "round": u["round"], "agent_id": u["agent_id"],
                "model": model, "temperature": 0.0, "n": 1,
                "axis": "author_evaluate_fact",
                "prompt_ver": authors_prompts.version_tag(),
                "matched_fact_ids": idx,
                "parse": status,
                "raw_response": raw,          # 규약 5 — 원문 그대로
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[axis] r{u['round']} {u['agent_id']} -> {idx} ({status}) "
                  f"· 호출 {calls}/{args.max_calls}")
    print(f"[axis] 체크포인트: {ckpt}")


if __name__ == "__main__":
    main()
