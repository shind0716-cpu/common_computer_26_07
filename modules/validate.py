"""산출물이 스키마 v0.2를 지키는지 검사하는 CLI. 모든 모듈의 완료 기준 판정기.
사용: python -m modules.validate data/facts/facts_issue_esa.json [파일 ...]
파일 종류는 파일명 접두사(issue/facts/assignment/debate/judgment)로 자동 판별.

왜 필요한가(리뷰어용): 우리 모듈은 파일로 대화한다(파일 계약). "완료했다"의 객관적 기준이
곧 "산출 파일이 스키마를 지킨다"이다(CLAUDE.md 규칙 3) — 통과 전엔 완료가 아니다. 검사는
'필수 필드가 있는가' 수준의 얕은 계약 검사이지, 값의 의미까지 보지는 않는다."""
import json
import sys
from pathlib import Path

# 파일 종류별 최상위 필수 필드. 여기 없는 종류(예: debate)는 validate() 안에서 따로 처리.
REQUIRED = {
    "issue": ["schema_ver", "issue_id", "source", "title", "body"],
    "facts": ["schema_ver", "issue_id", "extractor", "facts"],
    "assignment": ["schema_ver", "issue_id", "seed", "agents"],
    "judgment": ["schema_ver", "issue_id", "run_id", "judge", "stage_type", "stages", "summary"],
}
FACT_KEYS = ["fact_id", "text", "tags", "critical"]  # facts 파일 안 각 팩트의 필수 키
STATUS = {"unmentioned", "mentioned", "accepted", "refuted", "ignored"}  # judgment status 허용 5종


def fail(msg: str):
    """검사 실패를 출력하고 즉시 종료(exit 1). CLI 스크립트라 예외 대신 종료 코드로 실패를 알린다."""
    print(f"[FAIL] {msg}")
    sys.exit(1)


def check_keys(obj, keys, where):
    """obj(dict)에 keys 가 모두 있는지 확인. 하나라도 없으면 fail. where 는 오류 메시지용 위치 표시."""
    for k in keys:
        if k not in obj:
            fail(f"{where}: 필수 필드 누락 '{k}'")


def validate(path: Path):
    """파일 하나를 스키마 검사. 통과하면 [OK] 출력, 실패하면 fail 로 종료.

    파일 종류는 파일명 접두사로 판별한다(예: judgment_issue_esa_run001.json → 'judgment').
    debate 만 .jsonl(줄 단위 이벤트)이라 별도 경로로, 나머지는 .json 문서로 검사한다."""
    # 파일명 첫 토큰이 종류. facts_issue_esa.json → 'facts'. debate 아닌 파일 대비 .json 접미사 제거.
    kind = path.name.split("_")[0].replace(".json", "")
    if kind == "debate":
        # debate 는 이벤트 jsonl — 한 줄이 한 이벤트. 줄마다 최소 계약(event·run_id·ts)만 확인.
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue  # 빈 줄은 건너뜀
            ev = json.loads(line)
            check_keys(ev, ["event", "run_id", "ts"], f"{path.name} line {i + 1}")
        print(f"[OK] {path.name} (debate jsonl)")
        return
    obj = json.loads(path.read_text(encoding="utf-8"))
    if kind not in REQUIRED:
        fail(f"알 수 없는 파일 종류: {kind} ({path.name})")
    check_keys(obj, REQUIRED[kind], path.name)
    if kind == "facts":
        # facts 는 최상위뿐 아니라 각 팩트 항목도 계약을 지켜야 한다.
        for f in obj["facts"]:
            check_keys(f, FACT_KEYS, f.get("fact_id", "fact"))
    if kind == "judgment":
        # judgment 는 stage마다 facts 배열이 있고, 각 판정 status 가 허용 5종인지까지 확인.
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
