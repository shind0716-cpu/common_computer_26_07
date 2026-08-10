# -*- coding: utf-8 -*-
"""논문 재현 트랙 — 저자 facts.py 3단계 계승 extractor.

범위: experiments/paper_repro/data/issues → data/facts + raw_calls JSONL.
고정 조건: gpt-5, temperature=0, n=1, 저자 프롬프트 원본 직독.
안전장치: 전역 호출 상한, 호출 단위 체크포인트, --dry 0콜 완주, 원문 전량 보존.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from modules import authors_prompts, llm, paths  # noqa: E402
from modules import validate as validate_mod  # noqa: E402

SCHEMA_VER = "0.3"
CREATED_BY = "paper_repro_extractor"
MODEL = "gpt-5"
TEMPERATURE = 0.0
N = 1
MAX_TOKENS = 8192
MIN_REFINED = 5
llm.MAX_TOKENS = MAX_TOKENS  # 편차 P-1: 러너 안에서만 완화, modules/llm.py 무수정


def obtain_json(data: str):
    """저자 utils.obtain_json 계승 — 실패하면 원문 문자열을 돌려준다."""
    try:
        return json.loads(data.replace("```json", "").replace("```", "").replace("\\n", ""))
    except Exception:  # noqa: BLE001
        return data


class CallCheckpoint:
    """tag 단위 원문 체크포인트와 이번 실행의 전역 신규 호출 상한."""

    def __init__(self, path: Path, max_calls: int,
                 responder: Callable[[str], str] | None = None,
                 prompt_ver: str | None = None):
        self.path = Path(path)
        self.max_calls = max_calls
        self.responder = responder or (
            lambda prompt: llm.obtain_response(prompt, model=MODEL, temperature=TEMPERATURE))
        self.prompt_ver = prompt_ver or authors_prompts.version_tag()
        self.calls_this_run = 0
        self.records: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self.records[rec["tag"]] = rec

    def call(self, prompt: str, tag: str) -> str:
        if tag in self.records:
            return self.records[tag]["raw"]
        if self.calls_this_run >= self.max_calls:
            raise RuntimeError(
                f"전역 호출 상한 {self.max_calls} 도달 — 중단(호출 원문 체크포인트 보존됨)")
        raw = self.responder(prompt)
        self.calls_this_run += 1
        rec = {"tag": tag, "model": MODEL, "temperature": TEMPERATURE, "n": N,
               "prompt_ver": self.prompt_ver, "raw": raw}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.records[tag] = rec
        return raw


class ParseFailure(ValueError):
    """원문은 보존됐지만 저자 JSON 배열로 파싱할 수 없는 호출."""

    def __init__(self, tag: str):
        self.tag = tag
        self.stage = tag.rsplit("|", 1)[-1]
        super().__init__(f"{tag}: JSON 배열 파싱 실패 — 원문은 raw_calls JSONL에 보존됨")


def _require_list(raw: str, tag: str) -> list:
    parsed = obtain_json(raw)
    if not isinstance(parsed, list):
        raise ParseFailure(tag)
    return parsed


def _fact_prefix(issue_id: str) -> str:
    if not issue_id.startswith("issue_"):
        raise ValueError(f"지원하지 않는 issue_id: {issue_id}")
    return f"fact_{issue_id[len('issue_'):]}"


def build_facts_doc(issue_id: str, refined: list, important: list,
                    created_at: str, prompt_ver: str) -> dict:
    """저자 위치 인덱스를 보존해 facts 픽스처와 같은 구조로 변환."""
    if len(refined) != len(important):
        raise ValueError(
            f"{issue_id}: refined({len(refined)})와 important({len(important)}) 길이 불일치")
    if not all(isinstance(x, str) for x in refined):
        raise ValueError(f"{issue_id}: refined_facts에 문자열 아닌 항목 존재")
    if not all(isinstance(x, bool) or
               (isinstance(x, int) and not isinstance(x, bool) and x in (0, 1))
               for x in important):
        raise ValueError(f"{issue_id}: important_facts에 bool 또는 0/1 int 아닌 항목 존재")
    important_bools = [bool(x) for x in important]
    prefix = _fact_prefix(issue_id)
    prior = {"score": None, "probe_model": None, "probe_prompt_ver": None,
             "probed_at": None}
    return {
        "schema_ver": SCHEMA_VER,
        "created_by": CREATED_BY,
        "created_at": created_at,
        "issue_id": issue_id,
        "extractor": {"model": MODEL, "temperature": TEMPERATURE,
                      "prompt_ver": prompt_ver},
        "_note": ("facts[] 배열 순서가 저자 위치 인덱스이며 origin_index가 그 대응을 보존한다. "
                  "raw/refine/select 응답 원문은 형제 raw_calls JSONL에 전량 보존한다."),
        "facts": [
            {"fact_id": f"{prefix}_{i + 1:02d}", "origin_index": i, "text": text,
             "tags": [], "critical": important_bools[i], "prior": dict(prior)}
            for i, text in enumerate(refined)
        ],
    }


def _validate_dry_output(path: Path) -> None:
    """dry validate 성공 출력은 숨기되 실패 원인은 stderr에 보존한다."""
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            validate_mod.validate(path)
    except SystemExit:
        output = captured.getvalue()
        if output:
            print(output, file=sys.stderr, end="")
        raise


def _issue_ids(data_root: Path) -> list[str]:
    manifest = json.loads((data_root / "sample_manifest.json").read_text(encoding="utf-8"))
    ids = [x["issue_id"] for x in manifest["sample"]["ids"]]
    if len(ids) != manifest["sample"]["n"] or len(ids) != len(set(ids)):
        raise ValueError("sample_manifest의 표본 수 또는 issue_id 유일성 불일치")
    return ids


def _dry_outputs(issue_ids: list[str], created_at: str, prompt_ver: str,
                 target_root: Path) -> tuple[int, list[str]]:
    old_data = paths.DATA
    paths.DATA = target_root
    excluded = []
    try:
        for issue_id in issue_ids:
            # 세 단계의 프롬프트 조립과 파싱/매핑을 모두 거치되 네트워크 호출은 0이다.
            issue = json.loads((old_data / "issues" / f"{issue_id}.json").read_text(
                encoding="utf-8"))
            raw_facts = [f"DRY raw fact {i + 1} for {issue_id}" for i in range(6)]
            p1 = authors_prompts.load("facts_initial").replace("<===text===>", issue["body"])
            parsed_raw = _require_list(json.dumps(raw_facts), f"{issue_id}|initial")
            fact_text = "".join(f"{x}\n" for x in parsed_raw)
            p2 = (authors_prompts.load("facts_refine").replace("<===text===>", issue["body"])
                  .replace("<===facts===>", fact_text))
            refined = _require_list(json.dumps(raw_facts), f"{issue_id}|refine")
            refined_text = "".join(f"{x}\n" for x in refined)
            p3 = (authors_prompts.load("facts_select")
                  .replace("<===question===>", issue["question"])
                  .replace("<===facts===>", refined_text))
            important = _require_list(json.dumps([True, False, False, False, False, False]),
                                      f"{issue_id}|select")
            if any(token in p1 + p2 + p3 for token in
                   ("<===text===>", "<===question===>", "<===facts===>")):
                raise ValueError(f"{issue_id}: dry 프롬프트 슬롯 미치환")
            doc = build_facts_doc(issue_id, refined, important, created_at, prompt_ver)
            out = paths.facts(issue_id)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
            _validate_dry_output(out)
            if len(refined) < MIN_REFINED:
                excluded.append(issue_id)
    finally:
        paths.DATA = old_data
    return len(issue_ids), excluded


def run(data_root: Path, max_calls: int, dry: bool) -> dict:
    data_root = Path(data_root).resolve()
    old_data = paths.DATA
    paths.DATA = data_root
    try:
        issue_ids = _issue_ids(data_root)
        prompt_ver = authors_prompts.version_tag()
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if dry:
            planned = len(issue_ids) * 3
            if max_calls < planned:
                raise RuntimeError(f"dry 예산 점검 실패: 예정 {planned}콜 > --max-calls {max_calls}")
            with tempfile.TemporaryDirectory(prefix="paper_repro_extract_dry_") as td:
                n_valid, excluded = _dry_outputs(
                    issue_ids, created_at, prompt_ver, Path(td))
            return {"dry": True, "issues": len(issue_ids), "planned_calls": planned,
                    "actual_calls": 0, "validated": n_valid,
                    "excluded_refined_lt5": excluded, "prompt_ver": prompt_ver}

        llm.preflight(MODEL, temperature=TEMPERATURE, reasoning="default")
        checkpoint = CallCheckpoint(
            paths.DATA / "raw_calls" / "extract_facts_calls.jsonl", max_calls,
            prompt_ver=prompt_ver)
        excluded = []
        failed_parse = []
        written = 0
        for issue_id in issue_ids:
            try:
                issue = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
                p1 = authors_prompts.load("facts_initial").replace("<===text===>", issue["body"])
                raw_facts = _require_list(checkpoint.call(p1, f"{issue_id}|initial"),
                                          f"{issue_id}|initial")
                fact_text = "".join(f"{x}\n" for x in raw_facts)
                p2 = (authors_prompts.load("facts_refine").replace("<===text===>", issue["body"])
                      .replace("<===facts===>", fact_text))
                refined = _require_list(checkpoint.call(p2, f"{issue_id}|refine"),
                                        f"{issue_id}|refine")
                refined_text = "".join(f"{x}\n" for x in refined)
                p3 = (authors_prompts.load("facts_select")
                      .replace("<===question===>", issue["question"])
                      .replace("<===facts===>", refined_text))
                important = _require_list(checkpoint.call(p3, f"{issue_id}|select"),
                                          f"{issue_id}|select")
            except ParseFailure as exc:
                failed_parse.append(
                    {"issue_id": issue_id, "stage": exc.stage, "tag": exc.tag})
                continue
            doc = build_facts_doc(issue_id, refined, important, created_at, prompt_ver)
            out = paths.facts(issue_id)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
            validate_mod.validate(out)
            written += 1
            if len(refined) < MIN_REFINED:
                excluded.append(issue_id)

        manifest = {
            "schema_ver": SCHEMA_VER, "created_by": CREATED_BY, "created_at": created_at,
            "model": MODEL, "temperature": TEMPERATURE, "n": N,
            "prompt_ver": prompt_ver, "max_tokens": MAX_TOKENS,
            "n_issues": len(issue_ids), "n_written_and_validated": written,
            "excluded_refined_lt5": excluded,
            "failed_parse": failed_parse,
            "raw_calls": "raw_calls/extract_facts_calls.jsonl",
            "deviations": ["P-1 max_tokens=8192 (저자는 상한 미전송)"],
        }
        (paths.DATA / "facts_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {**manifest, "dry": False, "actual_calls": checkpoint.calls_this_run}
    finally:
        paths.DATA = old_data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=HERE / "data")
    ap.add_argument("--max-calls", type=int, default=600)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true", help="0콜 완주 리허설; 파일은 임시 경로에만 씀")
    mode.add_argument("--live", action="store_true", help="지시자 승인 후에만 사용할 실호출 모드")
    args = ap.parse_args()
    result = run(args.data_dir, args.max_calls, dry=args.dry)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
