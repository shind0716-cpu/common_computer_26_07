"""[상류 · 민옥] 개인 수첩 — 응답 파싱 + 예산 집행.

계약 근거: docs/proposals/SCHEMA_v0.3_NOTE_SLOT.md (요한 사전고정, PR #20 a5af1bb).
이 모듈이 지는 계약은 §5의 한 줄이다.

> 발화 호출에 필드로 얹으면 `note_text`를 응답에서 파싱해야 하므로 **파싱 규칙이 계약**이
> 된다. 규칙 변경 시 구 로그가 다르게 재파싱되어 과거 수치가 소리 없이 변한다
> → `NOTE_PARSE_VER` 필수(`JUDGE_PROMPT_VER`와 같은 이유).

그래서 이 파일의 핵심은 파싱 함수가 아니라 **NOTE_PARSE_VER 상수**다. 파싱 규칙을
한 글자라도 바꾸면 이 상수를 올려야 하고, 올리지 않으면 과거 run 의 수치가 조용히
달라진다. 규칙을 바꿀 때 이 모듈만 보면 되도록 규칙 전체를 여기 모아둔다.

왜 judge 를 쓰지 않는가: 수첩은 모델이 그 자리에 쓴 텍스트고, 우리는 그것을 **판정하지
않고 그대로 저장**한다(A-1). 이 모듈은 "응답에서 수첩 문자열을 꺼내는" 일만 한다 —
내용에 대한 어떤 판단도 하지 않는다.
"""
import json
import re

# ─────────────────────────────────────────────────────────────────────────────
# NOTE_PARSE_VER — 파싱 규칙의 버전. 아래 규칙 목록을 바꾸면 반드시 올린다.
#
# v1 규칙 (2026-07-30 최초 고정):
#   R1. 응답 전체를 json.loads 시도 → dict 이고 "note" 키가 str 이면 그 값.
#   R2. 실패 시 응답에서 첫 '{' 부터 마지막 '}' 까지를 잘라 json.loads 재시도(모델이
#       JSON 앞뒤에 산문을 붙이는 흔한 실패 모드). 같은 조건이면 그 값.
#   R3. 그래도 실패하면 정규식으로 "note"\s*:\s*"..." 한 건을 찾아 JSON 문자열
#       이스케이프만 되돌린다.
#   R4. 전부 실패하면 None — 파싱 실패는 폴백을 만들지 않고 **미갱신**으로 취급한다.
#       (계약 §2: "갱신이 없었던 라운드는 이벤트를 만들지 않는다 — 이벤트 부재가 곧
#        미갱신이다." 빈 문자열을 넣으면 미갱신과 구별이 사라진다.)
#   R5. 예산: 문자 수 기준 앞에서부터 note_budget 자까지만 남기고 뒤를 버린다.
#       절단이 일어났는지는 truncated 플래그로 보고한다(조용한 절단 금지).
#       문자 수 세는 단위는 파이썬 str 길이(코드포인트) — 한글 1자 = 1.
# ─────────────────────────────────────────────────────────────────────────────
NOTE_PARSE_VER = "note_parse_v1"

_NOTE_RE = re.compile(r'"note"\s*:\s*"((?:[^"\\]|\\.)*)"', re.DOTALL)


def _from_obj(obj):
    if isinstance(obj, dict):
        v = obj.get("note")
        if isinstance(v, str):
            return v
    return None


def parse_say_and_note(resp):
    """응답 1건에서 (발화, 수첩) 을 꺼낸다. 수첩이 없으면 (발화, None).

    발화 규칙: JSON 이 파싱되고 "say" 가 str 이면 그 값, 아니면 **응답 원문 전체**.
    (원문 전체로 폴백하는 이유: 발화는 지표의 원자료다. 파싱이 실패했다고 발화를
     비우면 그 라운드가 무음이 되어 소실 지표가 우리 파서 탓으로 오염된다.
     원문을 넣으면 최악의 경우 JSON 껍데기가 발화에 섞이지만, 그건 로그에서 눈에
     보이는 오염이다 — 조용한 손실보다 낫다.)
    """
    if resp is None or not isinstance(resp, str):
        return resp, None
    text = resp.strip()
    if not text:
        return resp, None

    # R1
    try:
        obj = json.loads(text)
    except Exception:
        obj = None
    if obj is None:
        # R2
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j > i:
            try:
                obj = json.loads(text[i:j + 1])
            except Exception:
                obj = None

    if obj is not None:
        note = _from_obj(obj)
        say = obj.get("say") if isinstance(obj, dict) else None
        return (say if isinstance(say, str) else resp), note

    # R3
    m = _NOTE_RE.search(text)
    if m:
        try:
            note = json.loads(f'"{m.group(1)}"')
        except Exception:
            note = m.group(1)
        return resp, note

    # R4
    return resp, None


def parse_note_only(resp):
    """별도 호출(dedicated) 응답에서 수첩만 꺼낸다.

    별도 호출은 `{"note": "..."}` 만 요구하지만, 모델이 그냥 산문으로 답하는 경우가
    있다. 그때는 **응답 원문 전체를 수첩으로 취급**한다 — 별도 호출은 수첩을 쓰라는
    지시밖에 없으므로 산문 응답은 형식 실패지 내용 실패가 아니다.
    (얹기 방식과 규칙이 다른 이유: 얹기에서 원문 폴백을 하면 발화가 수첩에 통째로
     들어가 "선별"이라는 측정 대상이 사라진다. 별도 호출엔 그 위험이 없다.)
    """
    if resp is None or not isinstance(resp, str) or not resp.strip():
        return None
    say, note = parse_say_and_note(resp)
    if note is not None:
        return note
    return resp.strip()


def apply_budget(note_text, note_budget):
    """예산 집행. (텍스트, 절단여부) 반환. note_budget<=0 이면 무제한."""
    if note_text is None:
        return None, False
    if not note_budget or note_budget <= 0:
        return note_text, False
    if len(note_text) <= note_budget:
        return note_text, False
    return note_text[:note_budget], True
