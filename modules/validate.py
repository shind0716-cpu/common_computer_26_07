"""산출물이 스키마 v0.2를 지키는지 검사하는 CLI. 모든 모듈의 완료 기준 판정기.
사용: python -m modules.validate data/facts/facts_issue_esa.json [파일 ...]
파일 종류는 파일명 접두사(issue/facts/assignment/debate/judgment)로 자동 판별."""
import json
import sys
from pathlib import Path

REQUIRED = {
    "issue": ["schema_ver", "issue_id", "source", "title", "body"],
    "facts": ["schema_ver", "issue_id", "extractor", "facts"],
    "assignment": ["schema_ver", "issue_id", "seed", "agents"],
    "judgment": ["schema_ver", "issue_id", "run_id", "judge", "stage_type", "stages", "summary"],
}
FACT_KEYS = ["fact_id", "text", "tags", "critical"]
STATUS = {"unmentioned", "mentioned", "accepted", "refuted", "ignored"}


def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def check_keys(obj, keys, where):
    for k in keys:
        if k not in obj:
            fail(f"{where}: 필수 필드 누락 '{k}'")


def validate(path: Path):
    kind = path.name.split("_")[0].replace(".json", "")
    if kind == "debate":
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            ev = json.loads(line)
            check_keys(ev, ["event", "run_id", "ts"], f"{path.name} line {i + 1}")
        print(f"[OK] {path.name} (debate jsonl)")
        return
    obj = json.loads(path.read_text(encoding="utf-8"))
    if kind not in REQUIRED:
        fail(f"알 수 없는 파일 종류: {kind} ({path.name})")
    check_keys(obj, REQUIRED[kind], path.name)
    if kind == "facts":
        for f in obj["facts"]:
            check_keys(f, FACT_KEYS, f.get("fact_id", "fact"))
    if kind == "judgment":
        for st in obj["stages"]:
            check_keys(st, ["stage", "facts"], f"stage {st.get('stage')}")
            for f in st["facts"]:
                if f.get("status") not in STATUS:
                    fail(f"잘못된 status: {f.get('status')} ({f.get('fact_id')})")
    print(f"[OK] {path.name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        fail("사용법: python -m modules.validate <파일경로> [파일경로 ...]")
    for p in sys.argv[1:]:
        validate(Path(p))
    print("모든 검사 통과")
