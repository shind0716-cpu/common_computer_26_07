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


def _note_ref_text(note_evs: dict, ref, where: str) -> str | None:
    """prompt_assembly.note 슬롯 참조 → 저장된 note_update.note_text.

    계약 §3: "참조 대상 note_update 가 없으면 --deep 은 실패로 처리한다(조용한 통과
    금지)." null 이면 엔진이 빈 문자열을 치환했으므로 None 을 돌려준다 — 우리 템플릿은
    {{note}} 치환을 항상 수행하므로 "슬롯 블록 생략"과는 다른 경로다(§3의 생략 규칙은
    슬롯이 블록 단위인 템플릿에 적용된다)."""
    if not ref:
        return None
    key = (ref.get("agent_id"), ref.get("source_round"))
    ev = note_evs.get(key)
    if ev is None:
        fail(f"{where}: note 참조 대상 note_update 없음 "
             f"(agent={key[0]}, source_round={key[1]})")
    return ev.get("note_text")


def _assemble_incoming(utts: dict, slots: dict, injects: dict, where: str) -> str:
    """수첩 조건 발화의 incoming 조립 — 엔진의 window 분기를 참조 목록으로 재현한다.

    엔진은 누적이면 과거 라운드를 `[라운드 N] 참석자K: …` 로 붙이고 마지막 라운드를
    `[라운드 N · 방금] …` 로 붙인다. 어느 조립이었는지는 **슬롯의 window 값을 읽어서**
    안다 — 참조 목록의 round 다양성으로 추론하지 않는다. 라운드 1에서는 누적과 직전만이
    똑같이 "라운드 0 하나"라서 추론이 조용히 틀린다(실측으로 잡은 드리프트, 7/30).
    window 슬롯이 없는 로그는 rolling 으로 읽는다(구 로그 호환 — v0.2·v0.3 초기 로그)."""
    refs = slots.get("others", [])
    incoming = ""
    if slots.get("window") == "cumulative":
        n_per = len(refs) // max(1, len({r.get("round") for r in refs}))
        past, tail = (refs[:-n_per], refs[-n_per:]) if n_per and len(refs) > n_per \
            else ([], refs)
        for idx, ref in enumerate(past):
            incoming += (f"[라운드 {ref.get('round')}] 참석자{idx % n_per + 1}: "
                         f"{_assembly_ref_text(utts, ref, where)}\n")
        for k, ref in enumerate(tail):
            incoming += (f"[라운드 {ref.get('round')} · 방금] 참석자{k + 1}: "
                         f"{_assembly_ref_text(utts, ref, where)}\n")
    else:
        for k, ref in enumerate(refs):
            incoming += f"참석자{k + 1}: {_assembly_ref_text(utts, ref, where)}\n"
    if slots.get("inject"):
        iev = injects.get(slots["inject"].get("round"))
        if iev is None or "injected_text" not in iev:
            fail(f"{where}: inject 참조 대상 ledger_inject.injected_text 없음")
        incoming += iev["injected_text"]
    return incoming


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
    # 수첩 판본 색인 — (agent_id, round) 로 note_update 를 찾는다. 계약 §3의
    # source_round 참조가 이 색인을 때린다. origin=intervention 도 함께 색인한다
    # (사람이 고쳐 넣은 수첩으로 재실행한 run 도 재조립이 성립해야 한다 — 개입 run 을
    #  집계에서 빼는 것과 재조립 검증을 통과시키는 것은 별개다).
    note_evs = {(e.get("agent_id"), e.get("round")): e
                for e in events if e.get("event") == "note_update"}

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
            # 누적 창이면 참조 목록에 과거 라운드가 들어있고 라운드 표시가 붙는다 —
            # 수첩 조건과 같은 조립기를 쓴다(엔진도 같은 분기 하나로 만든다).
            incoming = _assemble_incoming(utts, slots, injects, where)
            fact_text = ""
            for fid in slots.get("assigned_fact_ids", []):
                if fid not in fact_by_id:
                    fail(f"{where}: 미지의 fact_id {fid}")
                fact_text += f"{fact_by_id[fid]}\n"
            ptxt = _assembly_ref_text(utts, slots["previous"], where)
            inputs = debate_engine.assemble_coop_continue(question, body, fact_text,
                                                          ptxt or "", incoming)
        elif pa["template"] in ("coop_continue_note", "coop_continue_note_say"):
            # 수첩 조건 발화. 슬롯이 coop_continue 와 다르다 — my_facts·previous 없음,
            # note 있음(스키마 v0.3 §3). others 목록 순서가 곧 조립 순서다: 누적 창이면
            # 과거 라운드가 목록에 그대로 들어와 있고, 라운드 표시 문자열까지 계약이다.
            incoming = _assemble_incoming(utts, slots, injects, where)
            note_text = _note_ref_text(note_evs, slots.get("note"), where)
            inputs = debate_engine.assemble_coop_continue_note(
                question, body, note_text or "", incoming, template=pa["template"])
        elif pa["template"] == "coop_note_update":
            # 별도 호출(note_call=dedicated)의 수첩 갱신 입력. 이 호출도 prompt_assembly
            # 로 기록된다("입력이 기록되지 않은 LLM 호출"을 만들지 않는다 — §5).
            incoming = ""
            for k, ref in enumerate(slots.get("others", [])):
                incoming += f"참석자{k + 1}: {_assembly_ref_text(utts, ref, where)}\n"
            my_ref = slots.get("my_say")
            my_say = _assembly_ref_text(utts, my_ref, where) if my_ref else ""
            note_text = _note_ref_text(note_evs, slots.get("note"), where)
            nb = slots.get("note_budget")
            if nb is None:
                fail(f"{where}: coop_note_update 슬롯에 note_budget 없음")
            inputs = debate_engine.assemble_coop_note_update(
                question, note_text or "", my_say or "", incoming, nb)
        elif pa["template"] == "coop_final":
            # 최종 폴링. final_context 는 조건에 따라 수첩 또는 마지막 라운드 발언들 —
            # 어느 것이었는지가 슬롯에 적혀 있고, 재조립은 그 슬롯대로 되짚는다.
            if slots.get("note") is not None:
                note_text = _note_ref_text(note_evs, slots["note"], where)
                final_context = f"[당신의 수첩]\n{note_text or ''}\n"
            else:
                pref = slots.get("previous")
                ptxt = _assembly_ref_text(utts, pref, where) if pref else ""
                fc = f"[당신의 마지막 발언]\n{ptxt or ''}\n\n[참석자들의 마지막 발언]\n"
                for k, ref in enumerate(slots.get("others", [])):
                    fc += f"참석자{k + 1}: {_assembly_ref_text(utts, ref, where)}\n"
                final_context = fc
            inputs = debate_engine.assemble_coop_final(question, body, final_context)
        else:
            # template 등록제(v0.3 경계 조항 A-3): 검증기는 등록된 template 만 재조립한다.
            fail(f"{where}: 미등록 template {pa['template']} — 재조립 불가")
        digest = hashlib.sha256(inputs.encode("utf-8")).hexdigest()
        if digest != pa["prompt_hash"]:
            fail(f"{where}: 재조립 hash 불일치 — 로그 오염 또는 조립 규칙 드리프트")
        # 결합 키 검사: 발화 템플릿은 utterance 와, 발화가 아닌 호출(수첩 갱신·최종
        # 폴링)은 각자의 이벤트와 prompt_hash 로 결합한다. 발화가 아닌 호출을
        # utterance 에서 찾으면 당연히 없으므로, 여기서 갈라야 한다.
        if pa["template"] == "coop_note_update":
            nev = note_evs.get((pa["agent_id"], pa["round"]))
            # 파싱 실패로 미갱신된 라운드는 note_update 가 아예 없다(§2) — 그때는
            # 입력만 기록되고 결과가 없는 것이 정상이므로 결합 검사를 건너뛴다.
            if nev is not None and nev.get("source") != "dedicated":
                fail(f"{where}: coop_note_update 인데 note_update.source={nev.get('source')}")
        elif pa["template"] == "coop_final":
            fp = {(e.get("agent_id"), e.get("round")): e
                  for e in events if e.get("event") == "final_poll"}
            fev = fp.get((pa["agent_id"], pa["round"]))
            if fev is None or fev.get("prompt_hash") != pa["prompt_hash"]:
                fail(f"{where}: final_poll 결합 키(prompt_hash) 불일치")
        else:
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
            if ev["event"] == "run_meta":
                # v0.3 §4‴ — 있으면 구조를 검사하고, 없으면 통과(구 로그 호환).
                # 값의 의미(config와 실제 실행의 일치)는 검사하지 않는다 — 얕은 계약 검사.
                where = f"{path.name} line {i + 1} run_meta"
                check_keys(ev, ["issue_id", "condition", "config_ref", "settings"], where)
                check_keys(ev["config_ref"], ["name", "sha256"], f"{where}.config_ref")
                check_keys(ev["settings"],
                           ["window", "memory", "rounds", "structure", "stance",
                            "overlap_k", "ledger_mode", "seed"], f"{where}.settings")
                if events:  # 빈 줄은 세지 않는다 — '첫 이벤트'가 기준
                    fail(f"{where}: run_meta 는 첫 이벤트여야 한다 (앞에 {len(events)}건 있음)")
            if ev["event"] == "note_update":
                # 스키마 v0.3 §2 (SCHEMA_v0.3_NOTE_SLOT.md). note_text 는 A-1 대상 —
                # 복원 불가 텍스트라 전문 저장이 계약이고, 여기서 존재만 강제한다.
                where = f"{path.name} line {i + 1} note_update"
                check_keys(ev, ["agent_id", "round", "note_text", "origin", "source"],
                           where)
                if ev["origin"] not in ("model", "intervention"):
                    fail(f"{where}: origin 은 model|intervention (받은 값: {ev['origin']})")
                if ev["source"] not in ("utterance", "dedicated"):
                    fail(f"{where}: source 는 utterance|dedicated (받은 값: {ev['source']})")
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
