"""[패키지 A · 신동범 · 마감 수 20시] 토론 엔진 — DelibTrace 저자 코드(discussion.py) 포팅.

계약: 입력 paths.facts(issue), paths.assignment(issue), config
      → 출력 paths.debate(issue, run)  (스키마 4번, 이벤트 jsonl)
완료 기준: 바닐라(ledger_mode=off) 1회 완주 + validate 통과 + 응답 원문 전량 기록.

저자 코드에서 글자 단위로 계승한 것:
- 프롬프트 원문 (authors_prompts로 원본에서 직접 읽음)
- initial: 관점별 yes/no 2개씩 생성, temp 1.2
- 위치 셔플: seed 고정 후 8개 인덱스를 섞어 토폴로지 위치에 배정
- edges 구성: full(자기 제외 전원) / tree(이진트리 부모·좌·우) / line(좌우 이웃)
- others 포맷: "View {n}: {text}\\n"
- 응답 None이면 공백으로 대체

우리가 추가한 것 (스키마 v0.2 요구):
- 발화마다 이벤트 jsonl 기록 (원문 전량, 요약 금지)
- prompt_hash(sha256) — 재현·재생 검증용 (7/16 파일럿 방식)

실행: python -m modules.debate_engine --issue issue_esa --run run001 --config configs/sprint_mini.yaml
"""
import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import yaml

from modules import authors_prompts, llm, paths

DEBATE_ROUNDS = 3  # 논문 상수. config에서 덮어쓸 수 있게 아래에서 읽는다.


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_edges(structure: str, length: int) -> list[list[int]]:
    """토폴로지별 이웃 목록. 저자 discussion.py의 분기를 그대로 옮김."""
    if structure == "full":
        return [[j for j in range(length) if i != j] for i in range(length)]
    if structure == "line":
        edges = []
        for i in range(length):
            if i == 0:
                edges.append([i + 1])
            elif i == length - 1:
                edges.append([i - 1])
            else:
                edges.append([i - 1, i + 1])
        return edges
    if structure == "tree":
        edges = []
        for i in range(length):
            edge = []
            father = (i + 1) // 2 - 1
            left = (i + 1) * 2 - 1
            right = (i + 1) * 2 + 1 - 1
            if i != father and 0 <= father < length:
                edge.append(father)
            if i != left and 0 <= left < length:
                edge.append(left)
            if i != right and 0 <= right < length:
                edge.append(right)
            edges.append(edge)
        return edges
    raise KeyError(f"알 수 없는 토폴로지: {structure} (full|tree|line)")


def initial_utterance(question: str, fact_text: str, answer: str, model: str, temp: float):
    """저자 obtain_discussion_initial_each() 계승."""
    prompt = authors_prompts.load("discussion_initial")
    inputs = prompt.replace("<===facts===>", fact_text)
    inputs = inputs.replace("<===answer===>", answer)
    inputs = inputs.replace("<===question===>", question)
    return inputs, llm.obtain_response(inputs, model=model, temperature=temp)


def continue_utterance(question: str, previous: str, others: str, setting: str,
                       model: str, temp: float):
    """저자 discussion_continue() 내부 조립 계승."""
    prompt = authors_prompts.load("discussion_continue")
    inputs = prompt.replace("<===others===>", others)
    inputs = inputs.replace("<===previous===>", previous)
    inputs = inputs.replace("<===setting===>", setting)
    inputs = inputs.replace("<===question===>", question)
    return inputs, llm.obtain_response(inputs, model=model, temperature=temp)


def run(issue_id: str, run_id: str, config_path: Path) -> Path:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model = cfg["debate_model"]
    temp = float(cfg["debate_temperature"])
    rounds = int(cfg.get("rounds", DEBATE_ROUNDS))
    structure = cfg.get("structure", "full")
    ledger_mode = cfg.get("ledger_mode", "off")
    seed = int(cfg["seed"])

    facts_doc = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))
    assign_doc = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    issue_doc = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))

    question = issue_doc.get("question") or issue_doc["title"]
    fact_by_id = {f["fact_id"]: f["text"] for f in facts_doc["facts"]}
    agents = assign_doc["agents"]
    length = len(agents)

    prompt_ver = authors_prompts.version_tag()
    settings = authors_prompts.load_settings()
    setting_key = cfg.get("persona", "default")  # 논문 기본값은 default
    setting_text = settings[setting_key]

    out_path = paths.debate(issue_id, run_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    events = []

    def emit(event: str, **fields):
        rec = {"event": event, "run_id": run_id, "ts": now(), **fields}
        events.append(rec)

    # --- round 0: initial ---------------------------------------------------
    # 저자는 관점별로 yes/no 2개를 만든다. 우리 배분표는 이미 agent마다 stance가 있으므로
    # stance(pro/con) → answer(yes/no)로 바로 대응시킨다.
    current = []
    for ag in agents:
        fact_text = ""
        for fid in ag["assigned_fact_ids"]:
            fact_text += f"{fact_by_id[fid]}\n"
        answer = "yes" if ag["stance"] == "pro" else "no"
        inputs, resp = initial_utterance(question, fact_text, answer, model, temp)
        current.append(resp)
        emit(
            "utterance",
            ledger_mode=ledger_mode, round=0, agent_id=ag["agent_id"],
            position=None, stance=ag["stance"], perspective=ag["perspective"],
            model=llm.resolve_model(model), temperature=temp,
            prompt_ver=prompt_ver, prompt_hash=sha256(inputs),
            response_text=resp,
        )

    # --- 위치 셔플 ----------------------------------------------------------
    # 저자: random.seed(...) 후 8개 인덱스를 섞어 initial을 재배열한다.
    # 위치 i에 원래 order[i]번 에이전트가 앉는다 — 관점·입장이 토폴로지에 쏠리지 않게.
    order = list(range(length))
    random.Random(seed).shuffle(order)
    seated = [agents[order[i]] for i in range(length)]
    previous = [current[order[i]] for i in range(length)]
    previous = [p if p is not None else " " for p in previous]

    emit("seating", seed=seed, structure=structure,
         order=[agents[order[i]]["agent_id"] for i in range(length)])

    edges = build_edges(structure, length)

    # --- rounds 1..N --------------------------------------------------------
    for r in range(1, rounds + 1):
        nxt = []
        for i in range(length):
            others = ""
            for k, j in enumerate(edges[i]):
                others += f"View {k + 1}: {previous[j]}\n"
            inputs, resp = continue_utterance(
                question, previous[i] or "", others, setting_text, model, temp
            )
            nxt.append(resp)
            emit(
                "utterance",
                ledger_mode=ledger_mode, round=r, agent_id=seated[i]["agent_id"],
                position=i, stance=seated[i]["stance"], perspective=seated[i]["perspective"],
                model=llm.resolve_model(model), temperature=temp,
                prompt_ver=prompt_ver, prompt_hash=sha256(inputs),
                response_text=resp,
            )
        previous = nxt

    with out_path.open("w", encoding="utf-8") as f:
        for rec in events:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[OK] {out_path.name} — 이벤트 {len(events)}건 "
          f"(에이전트 {length} x 라운드 {rounds}+초기)")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="토론 엔진 (DelibTrace 포팅)")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--config", required=True, type=Path)
    args = ap.parse_args()
    run(args.issue, args.run, args.config)


if __name__ == "__main__":
    main()
