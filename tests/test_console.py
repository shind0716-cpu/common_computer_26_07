"""콘솔 v0 API 테스트 — 실행·수첩 매트릭스·개입 창.

LLM 실호출은 하지 않는다(개입 창은 llm.obtain_response 를 몽키패치). 콘솔의 계약은
"UI 가 예쁘다"가 아니라 **계약을 UI 가 집행하는가**이므로, 테스트도 그것을 본다:
  · append-only: 기존 run 을 덮어쓰려 하면 409
  · 개입 run 은 새 파일 + origin=intervention + condition 표시 (§6)
  · 호출 수 추정이 엔진의 상한 계산과 같은 식인가 (돌리기 전에 비용을 안다)
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from modules import debate_engine, llm, paths
from tests.test_note_slot import FakeLLM, _cfg, _write_fixture


class ConsoleBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig = paths.DATA
        paths.DATA = self.tmp / "data"
        self.issue_id = _write_fixture(paths.DATA)
        from tools.console import app as console_app
        self.mod = console_app
        self.c = TestClient(console_app.app)

    def tearDown(self):
        paths.DATA = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_run(self, run_id, **over):
        fake = FakeLLM()
        cfg = _cfg(self.tmp, **over)
        return debate_engine.run(self.issue_id, run_id, cfg, utterance_fn=fake)


class TestMeta(ConsoleBase):
    def test_axes_cover_settings_dictionary(self):
        d = self.c.get("/api/meta").json()
        keys = {a["key"] for a in d["axes"]}
        # 설정 사전의 조정 가능한 축이 폼에 다 있는가(⑤⑦은 배분표 소관이라 static).
        for k in ("window", "memory", "note_budget", "note_call", "rounds",
                  "structure", "ledger_mode", "final_poll"):
            self.assertIn(k, keys)
        self.assertTrue(d["note_parse_ver"].startswith("note_parse_"))

    def test_index_html_serves(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("실험 콘솔", r.text)

    def test_runs_list_reports_note_count(self):
        self._make_run("r_note", memory="note", note_call="utterance")
        runs = self.c.get("/api/meta").json()["runs"]
        row = next(r for r in runs if r["run_id"] == "r_note")
        self.assertEqual(row["memory"], "note")
        self.assertGreater(row["n_notes"], 0)


class TestEstimate(ConsoleBase):
    def _est(self, **over):
        body = {"issue_id": self.issue_id, "run_id": "x", "rounds": 3}
        body.update(over)
        return self.c.post("/api/estimate", json=body).json()

    def test_plain_run(self):
        d = self._est()
        self.assertEqual(d["total"], 3 * 4)          # 에이전트 3 x (라운드 3 + 초기)

    def test_note_dedicated_adds_calls(self):
        base = self._est()["total"]
        d = self._est(memory="note", note_call="dedicated")
        # 라운드0 수첩 3 + 갱신 3*(3-1)=6
        self.assertEqual(d["total"], base + 3 + 6)

    def test_note_ride_along_only_round0(self):
        base = self._est()["total"]
        d = self._est(memory="note", note_call="utterance")
        self.assertEqual(d["total"], base + 3)

    def test_final_poll_adds_one_per_agent(self):
        base = self._est()["total"]
        self.assertEqual(self._est(final_poll=True)["total"], base + 3)

    def test_matches_engine_budget(self):
        # 콘솔 추정과 엔진 상한이 같은 식이어야 한다 — 다르면 콘솔이 거짓말을 한다.
        est = self._est(memory="note", note_call="dedicated", final_poll=True)["total"]
        fake = FakeLLM()
        cfg = _cfg(self.tmp, memory="note", note_call="dedicated", final_poll=True)
        # max_llm_calls 를 추정치로 주면 딱 맞아야 한다(초과 시 SystemExit).
        import yaml
        doc = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        doc["max_llm_calls"] = est
        cfg.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
        debate_engine.run(self.issue_id, "budget", cfg, utterance_fn=fake)  # 안 죽어야 함

    def _make_repro_track(self):
        """배분표를 pro/con 으로 바꿔 재현 트랙으로 만든다."""
        aj = paths.assignment(self.issue_id)
        doc = json.loads(aj.read_text(encoding="utf-8"))
        for i, ag in enumerate(doc["agents"]):
            ag["stance"] = "pro" if i % 2 else "con"
        aj.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def test_blocks_note_without_coop(self):
        # 경고가 아니라 차단이어야 한다 — 경고만이면 사람이 지나쳐 누르고,
        # 엔진이 도중에 죽으며 스택트레이스를 읽어야 한다.
        self._make_repro_track()
        d = self._est(memory="note")
        self.assertTrue(d["blocking"], "협력 조건 아닌데 수첩을 켜면 차단해야 한다")
        self.assertFalse(d["coop"])

    def test_blocks_cumulative_without_coop(self):
        self._make_repro_track()
        d = self._est(window="cumulative")
        self.assertTrue(d["blocking"])

    def test_repro_track_flags_missing_author_repo(self):
        # 2026-07-30 실측: issue_esa(pro/con)를 골라 실행하니 authors_prompts 가
        # RuntimeError — 저자 저장소 클론이 없어서였다. 누르기 전에 알려야 한다.
        self._make_repro_track()
        with mock.patch.object(self.mod, "_author_repo_present", lambda: False):
            d = self._est()
        self.assertTrue(any("저자 저장소" in b for b in d["blocking"]))

    def test_coop_issue_has_no_blocking(self):
        d = self._est(memory="note", final_poll=True)
        self.assertTrue(d["coop"])
        self.assertEqual(d["blocking"], [])


class TestScenario(ConsoleBase):
    """시나리오 열람 — 돌리기 전에 "무엇을 묻고 누가 무엇을 아는가"를 본다."""

    def test_returns_origin_facts_and_assignment(self):
        d = self.c.get(f"/api/scenario?issue_id={self.issue_id}").json()
        self.assertEqual(d["issue_id"], self.issue_id)
        self.assertTrue(d["body"])
        self.assertEqual(d["n_facts"], 6)
        self.assertEqual(len(d["agents"]), 3)
        self.assertTrue(d["coop"])
        for a in d["agents"]:
            self.assertIn("n_facts", a)
            self.assertIn("assigned_fact_ids", a)

    def test_answer_key_fields_hidden_by_default(self):
        # 정답 누설 필드는 기본 접힘 — 사람이 실험 전에 읽으면 조건 설정이
        # 정답 쪽으로 기울 수 있다(관측자 오염).
        fp = paths.facts(self.issue_id)
        doc = json.loads(fp.read_text(encoding="utf-8"))
        for f in doc["facts"]:
            f["favors"] = "후보A"
        fp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

        d = self.c.get(f"/api/scenario?issue_id={self.issue_id}").json()
        self.assertIn("favors", d["hidden_fields"])
        self.assertFalse(d["revealed"])
        self.assertTrue(all("favors" not in f for f in d["facts"]))

        # 검수할 땐 볼 수 있어야 한다 — 숨김이 아니라 접힘이다.
        d2 = self.c.get(f"/api/scenario?issue_id={self.issue_id}&reveal=true").json()
        self.assertTrue(d2["revealed"])
        self.assertTrue(all("favors" in f for f in d2["facts"]))

    def test_detects_orphan_facts(self):
        # 아무에게도 배정되지 않은 팩트는 배분 결함이므로 드러내야 한다.
        aj = paths.assignment(self.issue_id)
        doc = json.loads(aj.read_text(encoding="utf-8"))
        doc["agents"][0]["assigned_fact_ids"] = []
        aj.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        d = self.c.get(f"/api/scenario?issue_id={self.issue_id}").json()
        self.assertTrue(d["orphan_fact_ids"])

    def test_missing_issue_404(self):
        r = self.c.get("/api/scenario?issue_id=issue_nope")
        self.assertEqual(r.status_code, 404)

    def test_survives_missing_assignment(self):
        # 배분표가 없어도 원문·팩트는 볼 수 있어야 한다(죽지 않는다).
        paths.assignment(self.issue_id).unlink()
        d = self.c.get(f"/api/scenario?issue_id={self.issue_id}").json()
        self.assertEqual(d["agents"], [])
        self.assertEqual(d["n_facts"], 6)


class TestRunBlocking(ConsoleBase):
    """실행 요청 자체를 막나 — 경고를 지나쳐 눌러도 엔진에 도달하지 않아야 한다."""

    def _make_repro_track(self):
        aj = paths.assignment(self.issue_id)
        doc = json.loads(aj.read_text(encoding="utf-8"))
        for i, ag in enumerate(doc["agents"]):
            ag["stance"] = "pro" if i % 2 else "con"
        aj.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def test_run_rejects_note_on_repro_track(self):
        self._make_repro_track()
        r = self.c.post("/api/run", json={"issue_id": self.issue_id,
                                          "run_id": "blk1", "memory": "note"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(paths.debate(self.issue_id, "blk1").exists())

    def test_run_rejects_repro_track_without_author_repo(self):
        self._make_repro_track()
        with mock.patch.object(self.mod, "_author_repo_present", lambda: False):
            r = self.c.post("/api/run", json={"issue_id": self.issue_id,
                                              "run_id": "blk2"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("저자 저장소", r.json()["detail"])
        self.assertFalse(paths.debate(self.issue_id, "blk2").exists())


class TestRunGuard(ConsoleBase):
    def test_refuses_to_overwrite_existing_run(self):
        self._make_run("dup")
        r = self.c.post("/api/run", json={"issue_id": self.issue_id, "run_id": "dup"})
        self.assertEqual(r.status_code, 409)   # append-only (규칙 1)

    def test_writes_config_file_with_coords(self):
        import yaml
        req = self.mod.RunReq(issue_id=self.issue_id, run_id="cfgtest",
                              memory="note", note_budget=250, window="cumulative",
                              condition="talk-note")
        p = self.mod._write_config(req)
        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        self.assertEqual(doc["memory"], "note")
        self.assertEqual(doc["note_budget"], 250)
        self.assertEqual(doc["window"], "cumulative")
        self.assertEqual(doc["condition"], "talk-note")
        p.unlink()


class TestNotesMatrix(ConsoleBase):
    def test_matrix_shape(self):
        self._make_run("m1", memory="note", note_call="utterance", final_poll=True)
        d = self.c.get(f"/api/notes?issue_id={self.issue_id}&run_id=m1").json()
        self.assertEqual(len(d["agents"]), 3)
        self.assertTrue(d["cells"])
        for c in d["cells"]:
            self.assertIn("origin", c)
            self.assertIn("source", c)
            self.assertEqual(c["len"], len(c["text"]))
        self.assertEqual(len(d["polls"]), 3)

    def test_no_notes_run_is_empty_not_error(self):
        self._make_run("m2")
        d = self.c.get(f"/api/notes?issue_id={self.issue_id}&run_id=m2").json()
        self.assertEqual(d["cells"], [])
        self.assertTrue(d["says"])       # 발화는 있다

    def test_missing_run_404(self):
        r = self.c.get(f"/api/notes?issue_id={self.issue_id}&run_id=nope")
        self.assertEqual(r.status_code, 404)


class TestIntervene(ConsoleBase):
    def setUp(self):
        super().setUp()
        self._orig_llm = llm.obtain_response
        # 개입 폴링만 가짜로 — 수첩 내용에 따라 다른 답을 주게 해서 "결론이 바뀌나"를 본다.
        def fake_resp(inputs, model=None, temperature=None):
            if "핵심사실" in inputs:
                return json.dumps({"recommend": "채용"}, ensure_ascii=False)
            return json.dumps({"recommend": "불채용"}, ensure_ascii=False)
        llm.obtain_response = fake_resp

    def tearDown(self):
        llm.obtain_response = self._orig_llm
        super().tearDown()

    def test_intervention_writes_new_run_and_marks_origin(self):
        self._make_run("iv_src", memory="note", note_call="utterance", final_poll=True)
        d0 = self.c.get(f"/api/notes?issue_id={self.issue_id}&run_id=iv_src").json()
        notes = {a: "핵심사실 있음" for a in d0["agents"]}
        r = self.c.post("/api/intervene", json={
            "issue_id": self.issue_id, "run_id": "iv_src",
            "new_run_id": "iv_src_iv1", "notes": notes})
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        # 원본은 그대로 (append-only)
        src = paths.debate(self.issue_id, "iv_src").read_text(encoding="utf-8")
        self.assertNotIn("intervention", src)
        # 개입 run 은 별도 파일 + origin=intervention + condition 표시
        ev = [json.loads(l) for l in
              paths.debate(self.issue_id, "iv_src_iv1").read_text(encoding="utf-8")
              .splitlines() if l.strip()]
        nus = [e for e in ev if e["event"] == "note_update"]
        self.assertTrue(nus)
        self.assertTrue(all(e["origin"] == "intervention" for e in nus))
        meta = ev[0]
        self.assertIn("intervention", meta["condition"])
        self.assertEqual(meta["settings"]["intervention_of"], "iv_src")
        # 결론이 바뀌었는지 대조가 돌아온다
        self.assertTrue(d["changed_agents"])
        self.assertTrue(all("채용" in v for v in d["after"].values()))

    def test_refuses_run_without_notes(self):
        self._make_run("nonote")
        r = self.c.post("/api/intervene", json={
            "issue_id": self.issue_id, "run_id": "nonote",
            "new_run_id": "nonote_iv", "notes": {}})
        self.assertEqual(r.status_code, 400)

    def test_refuses_to_clobber(self):
        self._make_run("iv2", memory="note", note_call="utterance")
        r = self.c.post("/api/intervene", json={
            "issue_id": self.issue_id, "run_id": "iv2",
            "new_run_id": "iv2", "notes": {}})
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
