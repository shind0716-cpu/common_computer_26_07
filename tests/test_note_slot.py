"""수첩(개인 기억) 구현 테스트 — 계약 SCHEMA_v0.3_NOTE_SLOT.md 집행.

이 파일이 지키는 것은 "코드가 도나"가 아니라 **계약대로 도나**다. 그래서 테스트가
검사하는 항목은 전부 계약 문면에 대응한다:

  §2  note_update 이벤트 필드·미갱신 시 이벤트 부재
  §3  prompt_assembly.note.source_round = 실제 사용 판본 (계산 아님)
  §5  note_call 두 방식 · NOTE_PARSE_VER 존재 · 한 run 안에서 안 섞임
  §7  memory/note_budget 좌표 분리
  B판 배정 팩트는 라운드 0에만 (설정 사전 v0.1 변경 3)
  + validate --deep 재조립이 수첩 슬롯에서도 성립하는가

LLM 은 전부 가짜(utterance_fn 주입) — API 키 없이 돈다.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from modules import debate_engine, note_slot, paths, validate


# ─── 가짜 LLM ────────────────────────────────────────────────────────────────
class FakeLLM:
    """호출 순서대로 응답을 만든다. 프롬프트를 보고 무엇을 요구받았는지 판별해
    JSON 모양을 맞춘다 — 실제 모델이 지시를 따랐을 때의 형태를 재현한다."""

    def __init__(self, *, note_ok=True, say_prefix="발언"):
        self.calls = []
        self.note_ok = note_ok
        self.say_prefix = say_prefix

    def __call__(self, inputs, model=None, temperature=None):
        self.calls.append(inputs)
        n = len(self.calls)
        wants_note = '"note"' in inputs
        wants_say = '"say"' in inputs
        wants_rec = '"recommend"' in inputs
        if wants_rec:
            return json.dumps({"recommend": "채용"}, ensure_ascii=False)
        if wants_say and wants_note:
            if not self.note_ok:
                return "JSON 아님 — 파싱 실패 유도"
            return json.dumps({"say": f"{self.say_prefix}{n}",
                               "note": f"수첩{n}"}, ensure_ascii=False)
        if wants_note:
            if not self.note_ok:
                return "JSON 아님 — 파싱 실패 유도"
            return json.dumps({"note": f"수첩{n}"}, ensure_ascii=False)
        return f"{self.say_prefix}{n}"


# ─── 픽스처: 최소 이슈/팩트/배분 ─────────────────────────────────────────────
def _write_fixture(root: Path, issue_id="issue_note", n_agents=3, n_facts=6):
    (root / "issues").mkdir(parents=True, exist_ok=True)
    (root / "facts").mkdir(parents=True, exist_ok=True)
    (root / "assignments").mkdir(parents=True, exist_ok=True)
    (root / "debates").mkdir(parents=True, exist_ok=True)
    (root / "issues" / f"{issue_id}.json").write_text(json.dumps({
        "issue_id": issue_id, "title": "제목", "question": "이 사람을 채용해야 하나?",
        "body": "상황 설명 본문", "source": "테스트", "options": ["채용", "불채용"],
    }, ensure_ascii=False), encoding="utf-8")
    facts = [{"fact_id": f"f{i}", "text": f"사실 {i}", "requirement": f"R{i % 3}",
              "side": "A" if i % 2 else "B", "tags": []} for i in range(n_facts)]
    (root / "facts" / f"facts_{issue_id}.json").write_text(json.dumps(
        {"issue_id": issue_id, "facts": facts}, ensure_ascii=False), encoding="utf-8")
    per = n_facts // n_agents
    agents = [{"agent_id": f"a{i}", "stance": "none", "perspective": f"P{i}",
               "assigned_fact_ids": [f["fact_id"] for f in facts[i * per:(i + 1) * per]]}
              for i in range(n_agents)]
    (root / "assignments" / f"assignment_{issue_id}.json").write_text(json.dumps(
        {"issue_id": issue_id, "agents": agents, "overlap_k": 1,
         "created_by": "test"}, ensure_ascii=False), encoding="utf-8")
    return issue_id


def _cfg(tmp: Path, **over):
    base = {"experiment": "t", "condition": "test", "issue_id": "issue_note",
            "run_id": "r1", "seed": 42, "agents": 3, "rounds": 3,
            "debate_model": "claude-haiku", "debate_temperature": 1.0,
            "judge_model": "claude-sonnet-4-6", "judge_temperature": 0,
            "judge_n_votes": 1, "ledger_mode": "off"}
    base.update(over)
    p = tmp / "cfg.yaml"
    p.write_text(yaml.safe_dump(base, allow_unicode=True), encoding="utf-8")
    return p


class NoteRunBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig_data = paths.DATA
        paths.DATA = self.tmp / "data"
        self.issue_id = _write_fixture(paths.DATA)

    def tearDown(self):
        paths.DATA = self._orig_data
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, run_id, **cfg_over):
        fake = FakeLLM(**cfg_over.pop("_fake", {}))
        cfg = _cfg(self.tmp, **cfg_over)
        out = debate_engine.run(self.issue_id, run_id, cfg, utterance_fn=fake)
        events = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
        return out, events, fake


class TestParsing(unittest.TestCase):
    """§5 파싱 규칙 — NOTE_PARSE_VER 이 가리키는 규칙 R1~R5."""

    def test_parse_ver_exists(self):
        # 계약이 요구하는 것은 상수의 존재 자체다(규칙 변경 추적 지점).
        self.assertTrue(note_slot.NOTE_PARSE_VER.startswith("note_parse_"))

    def test_r1_clean_json(self):
        say, note = note_slot.parse_say_and_note('{"say": "발언", "note": "수첩"}')
        self.assertEqual((say, note), ("발언", "수첩"))

    def test_r2_json_with_prose_around(self):
        raw = '알겠습니다.\n{"say": "발언", "note": "수첩"}\n이상입니다.'
        say, note = note_slot.parse_say_and_note(raw)
        self.assertEqual(note, "수첩")

    def test_r3_regex_fallback(self):
        # 깨진 JSON 이지만 note 필드는 읽힌다.
        raw = '{"say": "발언", "note": "수첩", }}'
        say, note = note_slot.parse_say_and_note(raw)
        self.assertEqual(note, "수첩")

    def test_r4_failure_is_none_not_empty(self):
        # 실패는 None(미갱신)이어야 한다 — 빈 문자열이면 미갱신과 구별이 사라진다.
        say, note = note_slot.parse_say_and_note("그냥 산문입니다")
        self.assertIsNone(note)
        self.assertEqual(say, "그냥 산문입니다")

    def test_say_falls_back_to_raw(self):
        # 발화는 절대 비우지 않는다(소실 지표 오염 방지).
        say, note = note_slot.parse_say_and_note("파싱 안 되는 응답")
        self.assertEqual(say, "파싱 안 되는 응답")

    def test_r5_budget_truncates_and_reports(self):
        text, trunc = note_slot.apply_budget("가" * 600, 500)
        self.assertEqual(len(text), 500)
        self.assertTrue(trunc)
        text2, trunc2 = note_slot.apply_budget("가" * 10, 500)
        self.assertFalse(trunc2)

    def test_dedicated_prose_becomes_note(self):
        # 별도 호출은 산문 응답을 수첩으로 받는다(얹기와 규칙이 다름 — 의도된 비대칭).
        self.assertEqual(note_slot.parse_note_only("남길 것은 이것"), "남길 것은 이것")


class TestNoteRideAlong(NoteRunBase):
    """note_call=utterance (얹기)."""

    def test_emits_note_update_with_contract_fields(self):
        out, events, fake = self._run("ride", memory="note", note_budget=500,
                                      note_call="utterance")
        nus = [e for e in events if e["event"] == "note_update"]
        self.assertTrue(nus)
        for e in nus:
            # §2 필드 전부
            for k in ("run_id", "ts", "agent_id", "round", "note_text", "origin", "source"):
                self.assertIn(k, e)
            self.assertEqual(e["origin"], "model")
            self.assertIn(e["source"], ("utterance", "dedicated"))

    def test_round0_note_is_dedicated_call(self):
        # 라운드 0 발화 프롬프트는 두 조건에서 동일해야 하므로 첫 수첩만 별도 호출.
        out, events, fake = self._run("ride2", memory="note", note_call="utterance")
        r0 = [e for e in events if e["event"] == "note_update" and e["round"] == 0]
        self.assertTrue(r0)
        self.assertTrue(all(e["source"] == "dedicated" for e in r0))

    def test_no_facts_after_round0_bplan(self):
        # B판: 라운드 1+ 프롬프트에 배정 팩트가 없다.
        out, events, fake = self._run("ride3", memory="note", note_call="utterance")
        pas = [e for e in events if e["event"] == "prompt_assembly"
               and e["template"] == "coop_continue_note"]
        self.assertTrue(pas)
        for pa in pas:
            self.assertEqual(pa["slots"]["assigned_fact_ids"], [])
            self.assertIsNone(pa["slots"]["previous"])   # 직전 발언도 기억이다

    def test_source_round_points_at_real_version(self):
        # §3: source_round 는 계산값이 아니라 실제 사용 판본.
        out, events, fake = self._run("ride4", memory="note", note_call="utterance")
        nu_by = {(e["agent_id"], e["round"]) for e in events
                 if e["event"] == "note_update"}
        for pa in events:
            if pa.get("event") != "prompt_assembly":
                continue
            ref = (pa.get("slots") or {}).get("note")
            if ref:
                self.assertIn((ref["agent_id"], ref["source_round"]), nu_by,
                              "note 슬롯이 존재하지 않는 판본을 가리킨다")

    def test_run_meta_records_note_coords(self):
        # §7 좌표 분리 + 얹기 방식의 파싱 버전 기록.
        out, events, fake = self._run("ride5", memory="note", note_budget=250,
                                      note_call="utterance")
        st = events[0]["settings"]
        self.assertEqual(st["memory"], "note")
        self.assertEqual(st["note_budget"], 250)
        self.assertEqual(st["note_call"], "utterance")
        self.assertEqual(st["note_parse_ver"], note_slot.NOTE_PARSE_VER)

    def test_parse_failure_emits_no_event(self):
        # §2: 미갱신은 이벤트 부재로 표현한다(빈 이벤트를 만들지 않는다).
        out, events, fake = self._run("ridefail", memory="note", note_call="utterance",
                                      _fake={"note_ok": False})
        # 라운드 1+ 의 얹기 갱신은 전부 실패 → 이벤트 없음. 라운드 0 은 별도 호출인데
        # 그 응답도 산문이므로 parse_note_only 규칙에 따라 원문이 수첩이 된다(의도된
        # 비대칭 — 별도 호출엔 발화가 섞여 들어올 위험이 없다).
        nus = [e for e in events if e["event"] == "note_update"]
        self.assertTrue(all(e["round"] == 0 for e in nus),
                        f"라운드 1+ 에 갱신 이벤트가 생겼다: {[e['round'] for e in nus]}")
        # 그래도 발화는 다 있다 — 수첩 파싱 실패가 발화를 죽이지 않는다.
        utts = [e for e in events if e["event"] == "utterance"]
        self.assertEqual(len(utts), 3 * 4)

    def test_deep_reassembly_passes(self):
        out, events, fake = self._run("ridedeep", memory="note", note_call="utterance")
        validate.validate(out, deep=True)   # 실패하면 SystemExit


class TestNoteDedicated(NoteRunBase):
    """note_call=dedicated (별도 호출)."""

    def test_source_is_dedicated_and_inputs_recorded(self):
        out, events, fake = self._run("ded", memory="note", note_call="dedicated")
        nus = [e for e in events if e["event"] == "note_update"]
        self.assertTrue(nus)
        self.assertTrue(all(e["source"] == "dedicated" for e in nus))
        # §5: 별도 호출의 입력도 prompt_assembly 로 기록된다.
        nu_pas = [e for e in events if e["event"] == "prompt_assembly"
                  and e["template"] == "coop_note_update"]
        self.assertEqual(len(nu_pas), len(nus))

    def test_say_template_has_no_note_field(self):
        # 별도 호출 조건의 발화 프롬프트는 note 를 요구하지 않는다(선별과 발화 분리).
        out, events, fake = self._run("ded2", memory="note", note_call="dedicated")
        say_prompts = [c for c in fake.calls if "발언하세요" in c]
        self.assertTrue(say_prompts)
        self.assertTrue(all('"say"' not in c for c in say_prompts))

    def test_no_mixing_within_run(self):
        # §5: 두 방식이 한 run 안에 섞이는 것은 금지. 라운드 0 은 항상 dedicated 이고
        # 나머지도 dedicated 이어야 한다 — utterance 소스가 하나도 없어야 한다.
        out, events, fake = self._run("ded3", memory="note", note_call="dedicated")
        srcs = {e["source"] for e in events if e["event"] == "note_update"}
        self.assertEqual(srcs, {"dedicated"})

    def test_deep_reassembly_passes(self):
        out, events, fake = self._run("deddeep", memory="note", note_call="dedicated")
        validate.validate(out, deep=True)


class TestCumulativeWindow(NoteRunBase):
    """window=cumulative — ③ 온전 대화의 정정된 좌표."""

    def test_others_refs_grow_with_rounds(self):
        out, events, fake = self._run("cum", window="cumulative")
        pas = [e for e in events if e["event"] == "prompt_assembly"
               and e["template"] == "coop_continue"]
        by_round = {}
        for pa in pas:
            by_round.setdefault(pa["round"], []).append(len(pa["slots"]["others"]))
        # 라운드가 올라가면 참조 목록이 길어진다(회의록 전체 재독).
        self.assertLess(max(by_round[1]), max(by_round[3]))

    def test_rolling_stays_flat(self):
        out, events, fake = self._run("roll", window="rolling")
        pas = [e for e in events if e["event"] == "prompt_assembly"
               and e["template"] == "coop_continue"]
        sizes = {len(pa["slots"]["others"]) for pa in pas}
        self.assertEqual(len(sizes), 1)   # 항상 이웃 수만큼

    def test_run_meta_records_window(self):
        out, events, fake = self._run("cum2", window="cumulative")
        self.assertEqual(events[0]["settings"]["window"], "cumulative")

    def test_deep_reassembly_passes(self):
        out, events, fake = self._run("cumdeep", window="cumulative")
        validate.validate(out, deep=True)

    def test_note_plus_cumulative_deep(self):
        # 직교 슬롯(§7)이므로 조합이 성립해야 한다.
        out, events, fake = self._run("both", window="cumulative", memory="note",
                                      note_call="utterance")
        validate.validate(out, deep=True)


class TestFinalPoll(NoteRunBase):
    """최종 폴링 — 벌거벗은 판단 {"recommend"} 한 필드."""

    def test_emits_one_per_agent(self):
        out, events, fake = self._run("fp", final_poll=True)
        fps = [e for e in events if e["event"] == "final_poll"]
        self.assertEqual(len(fps), 3)
        for e in fps:
            self.assertIn("response_text", e)
            self.assertIn("recommend", e["response_text"])

    def test_prompt_has_no_reason_field(self):
        # 회고·이유 필드 없음(결과가 자명한 측정 배제 — 설정 사전 v0.1 변경 6).
        out, events, fake = self._run("fp2", final_poll=True)
        polls = [c for c in fake.calls if '"recommend"' in c]
        self.assertTrue(polls)
        for c in polls:
            self.assertNotIn('"reason"', c)
            self.assertNotIn('"retrospect"', c)

    def test_note_condition_polls_from_note_only(self):
        # 수첩 조건: 최종 판단의 근거는 수첩뿐 — 슬롯이 그것을 증언한다.
        out, events, fake = self._run("fp3", final_poll=True, memory="note",
                                      note_call="utterance")
        fpas = [e for e in events if e["event"] == "prompt_assembly"
                and e["template"] == "coop_final"]
        self.assertTrue(fpas)
        for pa in fpas:
            self.assertIsNotNone(pa["slots"]["note"])
            self.assertEqual(pa["slots"]["others"], [])

    def test_deep_reassembly_passes(self):
        out, events, fake = self._run("fpdeep", final_poll=True)
        validate.validate(out, deep=True)

    def test_deep_reassembly_passes_with_note(self):
        out, events, fake = self._run("fpdeep2", final_poll=True, memory="note",
                                      note_call="dedicated")
        validate.validate(out, deep=True)


class TestGuards(NoteRunBase):
    """미지 값·미정의 조합은 조용히 돌지 않고 즉사한다."""

    def test_unknown_window(self):
        with self.assertRaises(KeyError):
            self._run("g1", window="sliding")

    def test_unknown_memory(self):
        with self.assertRaises(KeyError):
            self._run("g2", memory="notebook")

    def test_unknown_note_call(self):
        with self.assertRaises(KeyError):
            self._run("g3", memory="note", note_call="both")

    def test_note_requires_coop(self):
        # 저자 템플릿엔 수첩 슬롯이 없다 — pro/con 배분표로 수첩을 켜면 즉사.
        aj = paths.assignment(self.issue_id)
        doc = json.loads(aj.read_text(encoding="utf-8"))
        for i, ag in enumerate(doc["agents"]):
            ag["stance"] = "pro" if i % 2 else "con"
        aj.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(KeyError):
            self._run("g4", memory="note")


class TestBackwardCompat(NoteRunBase):
    """기존 조건은 한 글자도 달라지지 않는다(append 호환)."""

    def test_default_run_has_no_note_events(self):
        out, events, fake = self._run("compat")
        self.assertEqual([e for e in events if e["event"] == "note_update"], [])
        self.assertEqual([e for e in events if e["event"] == "final_poll"], [])
        st = events[0]["settings"]
        self.assertEqual((st["window"], st["memory"]), ("rolling", "none"))
        self.assertIsNone(st["note_call"])

    def test_default_prompt_hashes_unchanged_by_new_code(self):
        # 같은 seed·같은 가짜 응답이면 프롬프트 해시가 재현된다(조립 규칙 불변 확인).
        _, ev1, _ = self._run("rep1")
        _, ev2, _ = self._run("rep2")
        h1 = [e["prompt_hash"] for e in ev1 if e["event"] == "utterance"]
        h2 = [e["prompt_hash"] for e in ev2 if e["event"] == "utterance"]
        self.assertEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()
