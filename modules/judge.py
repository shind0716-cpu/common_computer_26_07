"""[패키지 A · 신동범 · 마감 수 20시] 채점기(judge) — 순수 함수로 구현.

계약: 입력 debate 로그 + facts 목록 → 출력 paths.judgment(issue, run) (스키마 5번)
사양(확정): Sonnet 단일, temperature 0, n_votes=3 다수결, votes 원본 보존.
순수 함수 원칙: 입력→출력만. 대조군에선 사후 오프라인, 실험군에선 루프 안에서 동일 함수 호출.

저자 코드에서 계승한 것:
- evaluate_fact 프롬프트 원문 (authors_prompts로 원본에서 직접 읽음)
- 팩트 나열 포맷: "{index}: {text}\\n"
- JSON 응답 파싱 방식 (```json 껍데기 제거)

우리가 추가한 것 (스키마 v0.2 / 7-16 파일럿 교훈):
- n_votes=3 다수결 + votes[] 원본 보존 — 불일치율이 judge 신뢰도 지표
- status 5종 매핑. 단, 저자 프롬프트는 mentioned/unmentioned 2종만 판별하므로
  v0 단계에서는 mentioned/unmentioned만 산출한다.
  accepted/refuted/ignored 세분화는 v1(상태 추적) 몫 — 스키마는 자리를 미리 갖고 있다.
- far_by_stage 요약 (System/Agent × 전체/critical 4분할)

실행: python -m modules.judge --issue issue_esa --run run001 --config configs/sprint_mini.yaml
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from modules import authors_prompts, llm, paths


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_json_block(text: str):
    """저자 obtain_json() 계승 — 코드펜스 벗기고 파싱, 실패 시 None."""
    try:
        cleaned = text.replace("```json", "").replace("```", "").replace("\\n", "")
        return json.loads(cleaned)
    except Exception:  # noqa: BLE001
        return None


def judge_fact_ids(utterance: str, facts: list[dict], model: str, n_votes: int) -> list[list[str]]:
    """발화 하나에 어떤 팩트가 표현돼 있는지 n_votes회 독립 판정.

    반환: 표(vote)마다 매칭된 fact_id 목록. 원본 표를 전부 보존한다.
    순수 함수: 같은 입력이면 같은 프롬프트 — 비결정성은 LLM 몫이고 그걸 votes로 계측한다.
    """
    prompt = authors_prompts.load("evaluate_fact")
    fact_text = ""
    for index, f in enumerate(facts):
        fact_text += f"{index}: {f['text']}\n"
    inputs = prompt.replace("<===facts===>", fact_text)
    inputs = inputs.replace("<===text===>", utterance)

    votes = []
    for _ in range(n_votes):
        resp = llm.obtain_response(inputs, model=model, temperature=0.0)
        parsed = parse_json_block(resp)
        matched = []
        if isinstance(parsed, dict):
            for idx in parsed.get("matched_fact_ids", []):
                if isinstance(idx, int) and 0 <= idx < len(facts):
                    matched.append(facts[idx]["fact_id"])
        votes.append(sorted(matched))
    return votes


def majority(votes: list[list[str]], fact_id: str) -> bool:
    """다수결: 과반 표에 등장하면 mentioned."""
    hit = sum(1 for v in votes if fact_id in v)
    return hit * 2 > len(votes)


def load_utterances(issue_id: str, run_id: str) -> dict[int, list[dict]]:
    """debate 로그에서 라운드별 발화 이벤트만 모은다."""
    by_round: dict[int, list[dict]] = {}
    log_path = paths.debate(issue_id, run_id)
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("event") != "utterance":
            continue
        by_round.setdefault(int(ev["round"]), []).append(ev)
    return by_round


def far_summary(stages: list[dict], facts: list[dict]) -> dict:
    """4분할 요약. FAR = 1 − retention.
    System = 어느 에이전트든 언급했으면 생존 / Agent = 자기 배분 팩트 기준이 아니라
    '전체 팩트 대비 개인 언급률 평균' — 스키마 v0.2의 far_agent_mean 정의를 따른다."""
    all_ids = [f["fact_id"] for f in facts]
    crit_ids = [f["fact_id"] for f in facts if f.get("critical")]
    out_stages = []
    for st in stages:
        mentioned_by = {}  # fact_id -> set(agent)
        agents = set()
        for frec in st["facts"]:
            for a in frec["agents_mentioning"]:
                agents.add(a)
                mentioned_by.setdefault(frec["fact_id"], set()).add(a)
        # 발화는 했지만 아무 팩트도 언급 안 한 에이전트도 분모에 포함해야 한다
        agents |= set(st.get("_all_agents", []))

        def system_ret(ids):
            if not ids:
                return None
            alive = sum(1 for fid in ids if mentioned_by.get(fid))
            return alive / len(ids)

        def agent_ret(ids):
            if not ids or not agents:
                return None
            per = []
            for a in agents:
                said = sum(1 for fid in ids if a in mentioned_by.get(fid, set()))
                per.append(said / len(ids))
            return sum(per) / len(per)

        sys_all, sys_crit = system_ret(all_ids), system_ret(crit_ids)
        ag_all, ag_crit = agent_ret(all_ids), agent_ret(crit_ids)
        out_stages.append({
            "stage": st["stage"],
            "far_system": None if sys_all is None else round(1 - sys_all, 4),
            "far_system_critical": None if sys_crit is None else round(1 - sys_crit, 4),
            "far_agent_mean": None if ag_all is None else round(1 - ag_all, 4),
            "far_agent_mean_critical": None if ag_crit is None else round(1 - ag_crit, 4),
        })
    return {
        "far_by_stage": out_stages,
        "far_system": out_stages[-1]["far_system"] if out_stages else None,
        "far_agent_mean": out_stages[-1]["far_agent_mean"] if out_stages else None,
        "far_critical": out_stages[-1]["far_system_critical"] if out_stages else None,
    }


def run(issue_id: str, run_id: str, config_path: Path) -> Path:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model = cfg["judge_model"]
    n_votes = int(cfg.get("judge_n_votes", 3))

    facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    facts = facts_doc["facts"]
    by_round = load_utterances(issue_id, run_id)

    stages = []
    for r in sorted(by_round):
        utterances = by_round[r]
        fact_records = {f["fact_id"]: {"fact_id": f["fact_id"],
                                       "status": "unmentioned",
                                       "votes": [],
                                       "agents_mentioning": []} for f in facts}
        for ev in utterances:
            votes = judge_fact_ids(ev["response_text"], facts, model, n_votes)
            for f in facts:
                fid = f["fact_id"]
                rec = fact_records[fid]
                rec["votes"].append({"agent_id": ev["agent_id"], "votes": votes and [fid in v for v in votes]})
                if majority(votes, fid):
                    rec["status"] = "mentioned"
                    rec["agents_mentioning"].append(ev["agent_id"])
        stages.append({
            "stage": r,
            "facts": list(fact_records.values()),
            "_all_agents": [ev["agent_id"] for ev in utterances],
        })

    summary = far_summary(stages, facts)
    for st in stages:  # 내부 계산용 필드 제거
        st.pop("_all_agents", None)

    out = {
        "schema_ver": "0.2",
        "created_by": "modules.judge",
        "created_at": now(),
        "issue_id": issue_id,
        "run_id": run_id,
        "judge": {
            "model": llm.resolve_model(model),
            "temperature": 0,
            "n_votes": n_votes,
            "aggregation": "majority",
            "prompt_ver": authors_prompts.version_tag(),
        },
        "stage_type": "round",
        "stages": stages,
        "summary": summary,
    }
    out_path = paths.judgment(issue_id, run_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {out_path.name} — 라운드 {len(stages)}개, summary: {summary['far_by_stage']}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="채점기 (DelibTrace evaluate_fact 포팅)")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--config", required=True, type=Path)
    args = ap.parse_args()
    run(args.issue, args.run, args.config)


if __name__ == "__main__":
    main()
