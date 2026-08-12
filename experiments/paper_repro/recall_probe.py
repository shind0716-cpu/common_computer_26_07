# -*- coding: utf-8 -*-
"""논문 재현 §12 — 토론 후 이원 recall probe (시계열 회고 + 500자 저장소).

범위: 완주 debate를 읽기만 하고 각 에이전트의 rolling 입력을 시점별로 재조립한다.
probe_full은 전 시점, probe_note는 마지막 시점만 호출하며 어떤 출력도 토론에 되돌리지 않는다.
저자 코드·debate_engine.py는 수정하지 않는다.

실호출 전제:
- CallCheckpoint 좌표(model·temperature·n·prompt_ver·prompt_sha256) 대조
- 기존 debate의 config 지문 일치 및 8명×4라운드 완주 확인
- 한 호출 성공마다 raw JSONL append+flush
- 현재 단계는 팩트 매핑을 하지 않는다. 파싱 산출은 pre_mapping sidecar에 보존하고,
  judgment.recall_probe[] 등재는 별도 승인된 매핑 판정 이후 수행한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from modules import llm, note_slot, paths  # noqa: E402
from modules import validate as validate_mod  # noqa: E402
from extract_facts import (  # noqa: E402 — 트랙 공용 좌표 체크포인트 계승
    CallCheckpoint,
    CheckpointMismatch,
)
from rehearse_splice import check_debate_provenance  # noqa: E402

MODEL = "gpt-5"
TEMPERATURE = 0.0
N = 1
NOTE_BUDGET = 500
ARMS = ("probe_full", "probe_note")

# §11 산출 기대: 팔별 문안 2안 이상. 결과를 보기 전에 A안을 활성 문안으로 고정한다.
# 두 팔 모두 <===shared_input===> 자리에 같은 문자열을 글자 그대로 한 번 삽입한다.
PROMPT_OPTIONS = {
    "probe_full": {
        "A": """당신은 한 토론에 참여 중인 참가자입니다. 아래에는 해당 시점 발언 직전에 당신이 실제로 본 입력이 그대로 있습니다. 다른 자료를 보거나 다른 참가자와 다시 대화하지 마세요.\n\n이 시점에 당신이 알고 있다고 생각하는 사실을 빠짐없이 적으세요. 요약문이나 결론을 쓰지 말고, 사실 하나를 statement 하나로 분리하세요. 각 사실이 처음 배정받은 정보면 assigned, 다른 참가자에게서 들었으면 heard, 입력을 바탕으로 스스로 추론했으면 inferred로 표시하세요. heard일 때만 heard_from에 발화자 agent_id를 쓰고, 나머지는 null을 쓰세요. 확실하지 않은 것을 새 사실로 만들지 마세요.\n\n다음 JSON 배열만 출력하세요:\n[{\"statement\": \"...\", \"source\": \"assigned|heard|inferred\", \"heard_from\": \"agent_id 또는 null\"}]\n\n[해당 시점 입력]\n<===shared_input===>""",
        "B": """지금부터의 답은 토론에 전달되지 않습니다. 아래 해당 시점 입력만 근거로, 이 시점에 당신의 머릿속에 남아 있는 사실 원장을 작성하세요. 결론·권고·설명문이 아니라 독립적인 사실 문장들을 모두 적으세요. 출처는 처음 배정=assigned, 타인의 발언=heard, 스스로 도출=inferred 중 하나입니다. heard만 heard_from에 agent_id를 쓰고 다른 경우 null로 두세요.\n\nJSON 배열 외에는 쓰지 마세요:\n[{\"statement\": \"...\", \"source\": \"assigned|heard|inferred\", \"heard_from\": null}]\n\n[해당 시점 입력]\n<===shared_input===>""",
    },
    "probe_note": {
        "A": """당신은 방금 한 토론을 마친 참가자입니다. 아래에는 마지막 발언 직전에 당신이 실제로 본 입력이 그대로 있습니다. 다른 자료를 보거나 다른 참가자와 다시 대화하지 마세요.\n\n이 입력을 다시 볼 수 없고, 이후의 당신에게 남는 것은 지금 쓰는 저장소뿐입니다. 다음에 꼭 기억해야 한다고 판단하는 내용을 500자 이내로 적으세요. 무엇을 남길지는 전적으로 당신의 판단입니다. 출처 표기는 요구하지 않습니다.\n\n다음 JSON 형식으로만 답하세요:\n{\"note\": \"저장소 내용\"}\n\n[마지막 시점 입력]\n<===shared_input===>""",
        "B": """토론이 끝났습니다. 아래 마지막 시점 입력은 곧 사라집니다. 이후 판단에 필요하다고 생각하는 것만 500자 저장소에 남기세요. 요약 방식과 우선순위는 당신이 정하며, 누가 말했는지는 적지 않아도 됩니다.\n\nJSON 하나만 출력하세요: {\"note\": \"...\"}\n\n[마지막 시점 입력]\n<===shared_input===>""",
    },
}
ACTIVE_WORDING = {"probe_full": "A", "probe_note": "A"}


def _prompt_version() -> str:
    h = hashlib.sha256()
    for arm in ARMS:
        h.update(arm.encode("utf-8"))
        h.update(ACTIVE_WORDING[arm].encode("utf-8"))
        h.update(PROMPT_OPTIONS[arm][ACTIVE_WORDING[arm]].encode("utf-8"))
    return f"paper_repro_recall_v1@{h.hexdigest()[:12]}"


PROMPT_VER = _prompt_version()


class ProbeParseError(ValueError):
    """raw는 보존됐지만 probe 응답 계약으로 파싱할 수 없음."""


@dataclass(frozen=True)
class Target:
    issue_id: str
    run_id: str


def _json_value(raw: str):
    text = raw.strip()
    if text.startswith("```json"):
        text = text[len("```json"):]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        return json.loads(text.strip())
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProbeParseError("JSON 파싱 실패 — raw checkpoint는 보존됨") from exc


def parse_full(raw: str, agent_ids: set[str]) -> list[dict]:
    """probe_full 배열을 엄격 파싱. source 귀속은 자기보고 관찰값일 뿐 판정값이 아니다."""
    obj = _json_value(raw)
    if not isinstance(obj, list):
        raise ProbeParseError("probe_full 최상위는 JSON 배열이어야 함")
    out = []
    for idx, row in enumerate(obj):
        if not isinstance(row, dict) or set(row) != {"statement", "source", "heard_from"}:
            raise ProbeParseError(f"probe_full[{idx}] 필드 불일치")
        statement, source, heard_from = row["statement"], row["source"], row["heard_from"]
        if not isinstance(statement, str) or not statement.strip():
            raise ProbeParseError(f"probe_full[{idx}].statement 빈 문자열/비문자열")
        if source not in {"assigned", "heard", "inferred"}:
            raise ProbeParseError(f"probe_full[{idx}].source 미지원: {source}")
        if source == "heard":
            if not isinstance(heard_from, str) or heard_from not in agent_ids:
                raise ProbeParseError(f"probe_full[{idx}] heard_from 미지/부재: {heard_from}")
        elif heard_from is not None:
            raise ProbeParseError(f"probe_full[{idx}] {source}는 heard_from=null이어야 함")
        out.append({"statement": statement, "source": source, "heard_from": heard_from})
    return out


def parse_note(raw: str, budget: int = NOTE_BUDGET) -> tuple[str, bool]:
    """기존 수첩 파서·예산 집행을 그대로 재사용한다(§11 팔 2)."""
    text = note_slot.parse_note_only(raw)
    if text is None:
        raise ProbeParseError("probe_note 빈 응답/파싱 실패")
    return note_slot.apply_budget(text, budget)


def parse_payload(raw: str, arm: str, agent_ids: set[str]) -> dict:
    """한 raw를 제3상태로 파싱한다. 실패 raw도 호출 좌표 행을 막지 않는다."""
    try:
        if arm == "probe_full":
            return {"parse_status": "ok", "statements": parse_full(raw, agent_ids)}
        if arm == "probe_note":
            note_text, truncated = parse_note(raw)
            return {"parse_status": "ok", "note_text": note_text, "truncated": truncated}
        raise KeyError(f"미지원 recall arm: {arm}")
    except ProbeParseError as exc:
        return {"parse_status": "parse_fail", "parse_error": str(exc)}


def build_prompt(arm: str, shared_input: str) -> str:
    if arm not in ARMS:
        raise KeyError(f"미지원 recall arm: {arm}")
    template = PROMPT_OPTIONS[arm][ACTIVE_WORDING[arm]]
    marker = "<===shared_input===>"
    if template.count(marker) != 1:
        raise RuntimeError(f"{arm} 활성 문안의 shared_input 슬롯은 정확히 1개여야 함")
    return template.replace(marker, shared_input)


def _read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def load_shared_inputs(data_root: Path, target: Target,
                       config_path: Path) -> tuple[dict[str, dict[int, str]], int]:
    """완주 토론의 모든 rolling prompt를 에이전트×시점으로 재조립한다."""
    old_data = paths.DATA
    paths.DATA = Path(data_root).resolve()
    try:
        debate_path = paths.debate(target.issue_id, target.run_id)
        check_debate_provenance(debate_path, config_path)
        events = _read_events(debate_path)
        utterances = [e for e in events if e.get("event") == "utterance"]
        agent_ids = {e["agent_id"] for e in utterances}
        rounds = sorted({e["round"] for e in utterances})
        if len(agent_ids) != 8 or not rounds:
            raise SystemExit(f"{target.issue_id}/{target.run_id}: 8명 완주 토론 아님")
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        expected_rounds = list(range(int(cfg.get("rounds", 3)) + 1))
        if rounds != expected_rounds:
            raise SystemExit(
                f"{target.issue_id}/{target.run_id}: 연속 라운드 "
                f"r0..r{expected_rounds[-1]} 필요 — 실제 {rounds}")
        final_round = rounds[-1]
        expected = len(agent_ids) * len(rounds)
        if len(utterances) != expected:
            raise SystemExit(
                f"{target.issue_id}/{target.run_id}: 부분 debate {len(utterances)}/{expected}발화")
        issue_doc = json.loads(paths.issue(target.issue_id).read_text(encoding="utf-8"))
        facts_doc = json.loads(paths.facts(target.issue_id).read_text(encoding="utf-8"))
        ctx = validate_mod.replay_context(events, issue_doc=issue_doc, facts_doc=facts_doc)
        pas = {(e.get("round"), e.get("agent_id")): e for e in events
               if e.get("event") == "prompt_assembly"}
        shared = {agent_id: {} for agent_id in sorted(agent_ids)}
        for agent_id in sorted(agent_ids):
            for probe_round in rounds:
                pa = pas.get((probe_round, agent_id))
                if pa is None:
                    raise SystemExit(
                        f"{target.issue_id}/{target.run_id}: prompt_assembly 부재"
                        f"({agent_id}, r{probe_round})")
                if pa.get("slots", {}).get("window", "rolling") != "rolling":
                    raise SystemExit(f"{target.issue_id}/{target.run_id}: §12는 rolling 입력만 허용")
                exact = validate_mod.reassemble_prompt(
                    pa, ctx,
                    where=f"recall {target.issue_id}/{target.run_id}/{agent_id}/r{probe_round}")
                digest = hashlib.sha256(exact.encode("utf-8")).hexdigest()
                if digest != pa["prompt_hash"]:
                    raise SystemExit(
                        f"{target.issue_id}/{target.run_id}/{agent_id}/r{probe_round}: "
                        "재조립 hash 불일치")
                refs = pa.get("slots", {}).get("others", [])
                source_map = "\n".join(
                    f"View {idx + 1} = {ref['agent_id']}" for idx, ref in enumerate(refs))
                shared[agent_id][probe_round] = (
                    f"[발화자 ID 대응 — 출처 귀속용]\n{source_map or '(이웃 없음)'}\n\n"
                    f"[재조립 검증된 r{probe_round} 입력 · sha256={digest}]\n{exact}"
                )
        return shared, final_round
    finally:
        paths.DATA = old_data


def make_checkpoint(path: Path, max_calls: int,
                    responder: Callable[[str], str] | None = None) -> CallCheckpoint:
    return CallCheckpoint(path, max_calls=max_calls, responder=responder,
                          prompt_ver=PROMPT_VER, model=MODEL,
                          temperature=TEMPERATURE, n=N)


def _pre_mapping_path(target: Target) -> Path:
    """계약 judgment 폴더와 분리하고, 별도 승인 전 judgment 자체는 수정하지 않는다."""
    return paths.recall_probe_pre_mapping(target.issue_id, target.run_id)


def _write_pre_mapping(target: Target, final_round: int, rows: list[dict]) -> Path:
    path = _pre_mapping_path(target)
    doc = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "created_by": "paper_repro_recall_probe",
        "issue_id": target.issue_id,
        "run_id": target.run_id,
        "source_round": final_round,
        "prompt_ver": PROMPT_VER,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "note_budget": NOTE_BUDGET,
        "mapping_status": "pending_separate_approval",
        "_note": ("자기보고 관찰값. 팩트 매핑 전 pre-mapping 산출이며 결과 변수가 아니다. "
                  "별도 승인 전 judgment.recall_probe에 등재하지 않는다."),
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run(data_root: Path, targets: list[Target], config_path: Path, *, dry: bool,
        max_calls: int, responder: Callable[[str], str] | None = None) -> dict:
    if not targets:
        raise ValueError("target이 하나 이상 필요")
    old_data = paths.DATA
    paths.DATA = Path(data_root).resolve()
    parsed_total = 0
    parse_failed = 0
    written = []
    try:
        loaded = []
        planned = 0
        for target in targets:
            shared_by_agent, final_round = load_shared_inputs(paths.DATA, target, config_path)
            loaded.append((target, shared_by_agent, final_round))
            planned += sum(len(by_round) + 1 for by_round in shared_by_agent.values())
        if not dry:
            if max_calls <= 0:
                raise SystemExit("live는 --max-calls 필수")
            hard_ceiling = math.ceil(planned * 1.2)
            if max_calls > hard_ceiling:
                raise SystemExit(f"G1 상한 초과: --max-calls {max_calls} > {hard_ceiling}")
            llm.preflight(MODEL, temperature=TEMPERATURE, reasoning="default")
            # 편차 P-1 계열(2026-08-12 실측 2회): gpt-5 사고 토큰이 기본 상한 2048을 잠식해
            # 3번째 콜 절단 → 8192 완화 후에도 12번째 콜 절단(후반 라운드 입력이 큼).
            # 상한은 천장이라 미도달 콜 비용에 무영향 — 반복 절단 낭비를 피해 24576.
            # llm.py 무수정 원칙 유지(러너 한정), 절단 검출은 그대로 살아 있다.
            llm.MAX_TOKENS = 24576

        checkpoint_path = paths.raw_calls("recall_probe_calls.jsonl")
        checkpoint = None if dry else make_checkpoint(checkpoint_path, max_calls, responder=responder)
        for target, shared_by_agent, final_round in loaded:
            agent_ids = set(shared_by_agent)
            rows = []
            for agent_id in sorted(shared_by_agent):
                coordinates = [
                    ("probe_full", probe_round, shared_by_agent[agent_id][probe_round])
                    for probe_round in sorted(shared_by_agent[agent_id])
                ]
                coordinates.append(("probe_note", final_round,
                                    shared_by_agent[agent_id][final_round]))
                for arm, probe_round, shared in coordinates:
                    input_sha = hashlib.sha256(shared.encode("utf-8")).hexdigest()
                    prompt = build_prompt(arm, shared)
                    tag = (f"{target.issue_id}|{target.run_id}|{agent_id}|"
                           f"r{probe_round}|{arm}")
                    if dry:
                        raw = (json.dumps([{"statement": "DRY fact", "source": "inferred",
                                           "heard_from": None}]) if arm == "probe_full"
                               else json.dumps({"note": "DRY note"}))
                    else:
                        raw = checkpoint.call(prompt, tag)
                    base = {"agent_id": agent_id, "arm": arm, "probe_round": probe_round,
                            "input_sha256": input_sha, "checkpoint_tag": tag,
                            "raw_checkpoint": str(checkpoint_path),
                            "self_report_status": "observational_unmapped"}
                    base.update(parse_payload(raw, arm, agent_ids))
                    rows.append(base)
                    if base["parse_status"] == "ok":
                        parsed_total += 1
                    else:
                        parse_failed += 1
            if not dry:
                written.append(str(_write_pre_mapping(target, final_round, rows)))
        return {"dry": dry, "targets": len(targets), "planned_calls": planned,
                "actual_calls": 0 if dry else checkpoint.calls_this_run,
                "parsed_rows": parsed_total, "parse_failed_rows": parse_failed,
                "written": written,
                "prompt_ver": PROMPT_VER}
    finally:
        paths.DATA = old_data


def _target(value: str) -> Target:
    try:
        issue_id, run_id = value.split(":", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("target 형식은 ISSUE_ID:RUN_ID") from exc
    if not issue_id or not run_id:
        raise argparse.ArgumentTypeError("target 형식은 ISSUE_ID:RUN_ID")
    return Target(issue_id, run_id)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=HERE / "data")
    ap.add_argument("--target", type=_target, action="append", required=True,
                    help="반복 가능: issue_ethics_0543:compare_0543")
    ap.add_argument("--config", type=Path, required=True)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true")
    mode.add_argument("--live", action="store_true")
    ap.add_argument("--max-calls", type=int, default=0)
    args = ap.parse_args()
    result = run(args.data_root, args.target, args.config, dry=args.dry,
                 max_calls=args.max_calls)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
