"""경로 유도 규칙의 단일 소스. 어떤 모듈도 경로를 하드코딩하지 않는다 — 반드시 이 모듈을 거친다.

왜 이 모듈이 필요한가(리뷰어용): 파이프라인 7모듈은 파일로 대화한다(파일 계약). 각 모듈이
경로 문자열을 제각기 하드코딩하면 폴더명·파일명을 한 곳만 바꿔도 전부 어긋난다. 여기 함수만
쓰면 파일 위치·이름 규칙이 한 곳에 모여, 바꿀 때 이 파일만 고치면 된다. (CLAUDE.md 규칙 2)

이름 규칙: 산출물은 종류별 폴더(issues/·facts/…)에 담고, 같은 이슈의 여러 실행을 구분해야 하는
debate·judgment 만 파일명에 run_id 를 붙인다. debate 만 .jsonl(이벤트를 한 줄씩 append),
나머지는 .json(문서 한 덩어리)."""
from pathlib import Path

# ROOT = 이 파일(modules/paths.py)의 두 단계 위 = 리포 루트. DATA = 그 아래 data/.
# __file__ 기준이라 어느 작업 디렉터리에서 실행해도 항상 같은 곳을 가리킨다.
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def issue(issue_id: str) -> Path:
    """이슈 원문 파일. loader 산출물이자 extractor 입력. 예: data/issues/issue_esa.json"""
    return DATA / "issues" / f"{issue_id}.json"


def facts(issue_id: str) -> Path:
    """원자 팩트 목록. extractor 산출물, assigner·judge 입력. facts_ 접두사로 이슈 파일과 구분."""
    return DATA / "facts" / f"facts_{issue_id}.json"


def assignment(issue_id: str) -> Path:
    """에이전트별 팩트 배분표. assigner 산출물, debate 입력."""
    return DATA / "assignments" / f"assignment_{issue_id}.json"


def debate(issue_id: str, run_id: str) -> Path:
    """토론 이벤트 로그(.jsonl — 발화·주입 이벤트가 한 줄씩). debate_engine 산출물, judge 입력.
    run_id 로 같은 이슈의 여러 실행(대조군/실험군·seed)을 구분한다."""
    return DATA / "debates" / f"debate_{issue_id}_{run_id}.jsonl"


def judgment(issue_id: str, run_id: str) -> Path:
    """팩트별 생존 판정 결과. judge 산출물, analysis·ledger 입력. debate 와 같은 run_id 로 짝짓는다."""
    return DATA / "judgments" / f"judgment_{issue_id}_{run_id}.json"


def raw_calls(filename: str) -> Path:
    """호출 단위 원문 체크포인트. 파일명은 러너가 정하고 위치는 이 모듈이 유도한다."""
    if Path(filename).name != filename:
        raise ValueError(f"raw_calls filename은 basename이어야 함: {filename}")
    return DATA / "raw_calls" / filename


def recall_probe_pre_mapping(issue_id: str, run_id: str) -> Path:
    """팩트 매핑 승인 전 recall 자기보고 파생물. 계약 judgment와 분리해 둔다."""
    return DATA / "recall_probe" / f"recall_probe_pre_mapping_{issue_id}_{run_id}.json"


def detection_spec(issue_id: str) -> Path:
    """시나리오별 의미 판독 명세. 재료가 소유하고 analyzer 는 소비만 한다.

    2026-08-20 추가. camp 식 「대표 문자열 하나 = 팩트 생존」 계약이 throne 에 안 맞는다는
    감사 결과에서 나왔다 — 시나리오마다 의미 골격이 달라 판독 규칙을 공통 analyzer 가
    소유하면 시나리오 차이를 재는 게 아니라 지운다. 공통 층은 로딩·검증·기록만 맡는다."""
    return DATA / "detection_specs" / f"{issue_id}.json"


def calibration_set(issue_id: str) -> Path:
    """판독 명세의 독립 교정 사례. 관측 출력과 계보를 갈라 두려고 파일을 나눈다 —
    같은 출력으로 규칙을 만들고 같은 출력에서 성능을 주장하는 것을 막는다."""
    return DATA / "detection_specs" / f"calibration_{issue_id}.json"


def detection_manifest(issue_id: str) -> Path:
    """재료 3종·DetectionSpec·calibration 바이트 지문 manifest."""
    return DATA / "detection_specs" / f"manifest_{issue_id}.json"


def scenario_registry() -> Path:
    """콘솔 승격 승인 원장. 파일 존재가 아니라 이 원장의 명시 항목이 입구가 된다."""
    return DATA / "scenario_registry.json"


def scenario_registry_schema() -> Path:
    """승격 원장 JSON Schema. 운영자와 테스트가 같은 계약 파일을 가리킨다."""
    return DATA / "scenario_registry.schema.json"
