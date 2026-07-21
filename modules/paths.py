"""경로 유도 규칙의 단일 소스. 어떤 모듈도 경로를 하드코딩하지 않는다 — 반드시 이 모듈을 거친다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def issue(issue_id: str) -> Path:
    return DATA / "issues" / f"{issue_id}.json"


def facts(issue_id: str) -> Path:
    return DATA / "facts" / f"facts_{issue_id}.json"


def assignment(issue_id: str) -> Path:
    return DATA / "assignments" / f"assignment_{issue_id}.json"


def debate(issue_id: str, run_id: str) -> Path:
    return DATA / "debates" / f"debate_{issue_id}_{run_id}.jsonl"


def judgment(issue_id: str, run_id: str) -> Path:
    return DATA / "judgments" / f"judgment_{issue_id}_{run_id}.json"
