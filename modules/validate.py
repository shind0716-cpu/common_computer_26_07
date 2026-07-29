"""산출물이 스키마 v0.2를 지키는지 검사하는 CLI. 모든 모듈의 완료 기준 판정기.
사용: python -m modules.validate data/facts/facts_issue_esa.json [파일 ...]
파일 종류는 파일명 접두사(issue/facts/assignment/debate/judgment)로 자동 판별.

왜 필요한가(리뷰어용): 우리 모듈은 파일로 대화한다(파일 계약). "완료했다"의 객관적 기준이
곧 "산출 파일이 스키마를 지킨다"이다(CLAUDE.md 규칙 3) — 통과 전엔 완료가 아니다. 검사는
'필수 필드가 있는가' 수준의 얕은 계약 검사이지, 값의 의미까지 보지는 않는다.

[2026-07-28 · 요한 — 작업 이관분(민옥 승인 7/28 보드)] v0.3 `--deep` 옵션:
debate 파일의 `prompt_assembly` 명세대로 프롬프트를 재조립해 sha256 == prompt_hash 를
검사한다(스키마 v0.3 검증 계약 — 기본 검사는 종전대로 구조만, --deep 는 옵트인).
조립 코드는 debate_engine.assemble_* 재사용(단일 소스). 형제 산출물(issue·facts)은
파일 위치 기준(debates/../)으로 찾는다 — 파일럿처럼 data 루트가 다른 경우도 동작.
prompt_assembly 가 없는 v0.2 구 로그는 재검증을 생략하고 통과한다(append 호환)."""
import hashlib
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


def _assembly_ref_text(utts: dict, ref: dict, where: str) -> str | None:
    """prompt_assembly 슬롯 참조 → 저장된 발화 원문. 엔진의 정규화 규칙을 재현한다:
    round 0 발화가 null 이면 좌석 셔플 시 " " 로 치환됐다(debate_engine 참조)."""
    u = utts.get((ref.get("round"), ref.get("agent_id")))
    if u is None:
        fail(f"{where}: 참조 발화 없음 (round={ref.get('round')}, agent={ref.get('agent_id')})")
    txt = u.get("response_text")
    if ref.get("round") == 0 and txt is None:
        txt = " "
    return txt


def deep_check_debate(path: Path, events: list[dict]) -> None:
    """v0.3 검증 계약: prompt_assembly 명세 재조립 sha256 == prompt_hash.
    utterance 결합 키(같은 round·agent 의 prompt_hash 동일)도 함께 검사한다."""
    from modules import authors_prompts, debate_engine  # 지연 임포트 — 구조 검사는 무의존 유지

    pas = [e for e in events if e.get("event") == "prompt_assembly"]
    if not pas:
        print(f"[OK] {path.name} (--deep: prompt_assembly 없음 — v0.2 구 로그, 재검증 생략)")
        return

    utts = {(e.get("round"), e.get("agent_id")): e
            for e in events if e.get("event") == "utterance"}
    injects = {e.get("round"): e for e in events if e.get("event") == "ledger_inject"}

    # 형제 산출물 로딩 — 파일 위치 기준(debates/../ = data 루트). issue_id 는
    # 파일명에서 run_id(이벤트 기록값)를 벗겨 복원한다(둘 다 '_' 포함 가능).
    run_id = pas[0].get("run_id")
    stem = path.name[len("debate_"):].rsplit(".", 1)[0]
    if not (run_id and stem.endswith("_" + run_id)):
        fail(f"{path.name}: 파일명에서 issue_id 복원 실패 (run_id={run_id})")
    issue_id = stem[: -len(run_id) - 1]
    root = path.resolve().parent.parent
    try:
        issue = json.loads((root / "issues" / f"{issue_id}.json").read_text(encoding="utf-8"))
        facts_doc = json.loads(
            (root / "facts" / f"facts_{issue_id}.json").read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        fail(f"{path.name} --deep: 형제 산출물 없음 — {e}")
    question = issue.get("question") or issue["title"]
    fact_by_id = {f["fact_id"]: f["text"] for f in facts_doc["facts"]}
    body = issue.get("body", "")
    settings = None  # 지연 로딩 — discussion_* 템플릿을 만났을 때만 저자 저장소 접근

    for pa in pas:
        where = f"{path.name} prompt_assembly(round={pa.get('round')}, agent={pa.get('agent_id')})"
        check_keys(pa, ["round", "agent_id", "template", "prompt_ver", "slots", "prompt_hash"],
                   where)
        slots = pa["slots"]
        if pa["template"] == "discussion_initial":
            fact_text = ""
            for fid in slots.get("assigned_fact_ids", []):
                if fid not in fact_by_id:
                    fail(f"{where}: 미지의 fact_id {fid}")
                fact_text += f"{fact_by_id[fid]}\n"
            u = utts.get((pa["round"], pa["agent_id"]))
            if u is None:
                fail(f"{where}: 짝 utterance 없음")
            answer = "yes" if u.get("stance") == "pro" else "no"
            inputs = debate_engine.assemble_initial(question, fact_text, answer)
        elif pa["template"] == "discussion_continue":
            others = ""
            for k, ref in enumerate(slots.get("others", [])):
                others += f"View {k + 1}: {_assembly_ref_text(utts, ref, where)}\n"
            if slots.get("inject"):
                iev = injects.get(slots["inject"].get("round"))
                if iev is None or "injected_text" not in iev:
                    fail(f"{where}: inject 참조 대상 ledger_inject.injected_text 없음")
                others += iev["injected_text"]
            ptxt = _assembly_ref_text(utts, slots["previous"], where)
            if settings is None:
                settings = authors_prompts.load_settings()
            setting = settings.get(pa.get("setting_key"))
            if setting is None:
                fail(f"{where}: 미등록 setting_key {pa.get('setting_key')}")
            inputs = debate_engine.assemble_continue(question, ptxt or "", others, setting)
        elif pa["template"] == "coop_initial":
            fact_text = ""
            for fid in slots.get("assigned_fact_ids", []):
                if fid not in fact_by_id:
                    fail(f"{where}: 미지의 fact_id {fid}")
                fact_text += f"{fact_by_id[fid]}\n"
            inputs = debate_engine.assemble_coop_initial(question, body, fact_text)
        elif pa["template"] == "coop_continue":
            incoming = ""
            for k, ref in enumerate(slots.get("others", [])):
                incoming += f"참석자{k + 1}: {_assembly_ref_text(utts, ref, where)}\n"
            if slots.get("inject"):
                iev = injects.get(slots["inject"].get("round"))
                if iev is None or "injected_text" not in iev:
                    fail(f"{where}: inject 참조 대상 ledger_inject.injected_text 없음")
                incoming += iev["injected_text"]
            fact_text = ""
            for fid in slots.get("assigned_fact_ids", []):
                if fid not in fact_by_id:
                    fail(f"{where}: 미지의 fact_id {fid}")
                fact_text += f"{fact_by_id[fid]}\n"
            ptxt = _assembly_ref_text(utts, slots["previous"], where)
            inputs = debate_engine.assemble_coop_continue(question, body, fact_text,
                                                          ptxt or "", incoming)
        else:
            # template 등록제(v0.3 경계 조항 A-3): 검증기는 등록된 template 만 재조립한다.
            fail(f"{where}: 미등록 template {pa['template']} — 재조립 불가")
        digest = hashlib.sha256(inputs.encode("utf-8")).hexdigest()
        if digest != pa["prompt_hash"]:
            fail(f"{where}: 재조립 hash 불일치 — 로그 오염 또는 조립 규칙 드리프트")
        u = utts.get((pa["round"], pa["agent_id"]))
        if u is None or u.get("prompt_hash") != pa["prompt_hash"]:
            fail(f"{where}: utterance 결합 키(prompt_hash) 불일치")
    print(f"[OK] {path.name} (--deep: prompt_assembly {len(pas)}건 재조립 검증 통과)")


def validate(path: Path, deep: bool = False):
    """파일 하나를 스키마 검사. 통과하면 [OK] 출력, 실패하면 fail 로 종료.

    파일 종류는 파일명 접두사로 판별한다(예: judgment_issue_esa_run001.json → 'judgment').
    debate 만 .jsonl(줄 단위 이벤트)이라 별도 경로로, 나머지는 .json 문서로 검사한다.
    deep=True (debate 한정): prompt_assembly 재조립 hash 검증까지 수행(v0.3)."""
    # 파일명 첫 토큰이 종류. facts_issue_esa.json → 'facts'. debate 아닌 파일 대비 .json 접미사 제거.
    kind = path.name.split("_")[0].replace(".json", "")
    if kind == "debate":
        # debate 는 이벤트 jsonl — 한 줄이 한 이벤트. 줄마다 최소 계약(event·run_id·ts)만 확인.
        events = []
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue  # 빈 줄은 건너뜀
            ev = json.loads(line)
            check_keys(ev, ["event", "run_id", "ts"], f"{path.name} line {i + 1}")
            events.append(ev)
        print(f"[OK] {path.name} (debate jsonl)")
        if deep:
            deep_check_debate(path, events)
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
    argv = sys.argv[1:]
    deep = "--deep" in argv
    files = [a for a in argv if a != "--deep"]
    if not files:
        fail("사용법: python -m modules.validate [--deep] <파일경로> [파일경로 ...]")
    for p in files:
        validate(Path(p), deep=deep)
    print("모든 검사 통과")
