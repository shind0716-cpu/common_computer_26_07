"""콘솔 「단독 실험」 탭 API 테스트 — WORKORDER_SOLO_TAB 2026-08-18.

LLM 실호출 0. 러너(run_solo.py)는 실행하지 않는다 — subprocess.Popen 을 가짜로 갈아
끼우고 **콘솔이 러너에게 무슨 명령을 만들어 주는가**를 본다. 콘솔의 계약(워크오더 §2):
  · 파일 스캔: runs/·runs/_dry/ 를 읽기만 하고, v1 산출물의 메타 부재를 기본값과 뭉치지 않는다
  · 견적 산식: 런 수 × (full/prev 5콜, note 8콜) + final_poll 런당 1콜
  · 사전등록 관문: v2 조건 실호출은 확인 체크 없이 400 — --allow-v2 는 확인 시에만,
    v1 조건엔 확인 여부와 무관하게 절대 붙지 않는다
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from modules import llm, paths
from tests.test_note_slot import _write_fixture


def _run_doc(run_id, mem="note", ver="solo-v1", issue_id="issue_note", **meta_over):
    """runs/<model>/run_<id>.json 모형. ver="solo-v1" 이면 v2 손잡이 메타 키 자체를
    넣지 않는다 — 실제 v1 산출물(2026-08-11 본실험 54런)과 같은 모양."""
    meta = {"model_key": "gpt", "provider": "api", "model_id": "gpt-x",
            "temperature": 0.7, "rounds": 4, "note_budget": 500,
            "note_truncated": False, "dry": False,
            "finished_at": "2026-08-18T00:00:00+00:00"}
    if ver != "solo-v1":
        meta.update({"facts_order": "original", "stance": True, "final_poll": False})
    meta.update(meta_over)
    doc = {"schema": "solo_run_v1", "issue_id": issue_id, "prompts_ver": ver,
           "run_id": run_id, "arm": run_id.split("_")[0], "arm_name": "repeat",
           "memory": mem, "rep": int(run_id.rsplit("rep", 1)[-1]),
           "meta": meta,
           "essays": ["글0", "글1", "글2", "글3"],
           "notes": (["가나다라마"] * 3 if mem == "note" else []),
           "recall": "- 회상 목록"}
    if meta.get("final_poll"):
        doc["final_poll"] = "무레온 캠프"
    return doc


def _judge_doc(run_id, issue_id, fact_ids, mentioned_at=("essay_r0", "carrier"),
               split_cell=None):
    """judgments/<model>/judge_<id>.json 모형 — 실물(solo_judgment_v1) 축소판."""
    def rec(stage):
        rows = []
        for f in fact_ids:
            st = "mentioned" if stage in mentioned_at else "unmentioned"
            votes = [{"status": st, "agents_mentioning": [], "reason": "r"}] * 3
            if split_cell == (f, stage):     # 표 분열 셀 하나 심기
                votes = [{"status": "mentioned", "agents_mentioning": [], "reason": "r"},
                         {"status": "mentioned", "agents_mentioning": [], "reason": "r"},
                         {"status": "unmentioned", "agents_mentioning": [], "reason": "r"}]
                st = "mentioned"
            rows.append({"fact_id": f, "status": st, "votes": votes,
                         "agents_mentioning": []})
        return rows
    return {"schema": "solo_judgment_v1", "issue_id": issue_id, "run_id": run_id,
            "run_model": "gpt",
            "judge": {"model": "gpt-mini", "temperature": 0, "n_votes": 3,
                      "prompt_ver": "judge-v0.2-binary+merged_system"},
            "records": {s: rec(s) for s in
                        ("essay_r0", "essay_r1", "essay_r2", "essay_r3", "carrier")}}


class SoloBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig_data = paths.DATA
        paths.DATA = self.tmp / "data"
        self.issue_id = _write_fixture(paths.DATA)     # 팩트 f0~f5 — 격자 행 라벨용
        from tools.console import app as console_app
        self.mod = console_app
        self._orig_solo = console_app.SOLO_DIR
        console_app.SOLO_DIR = self.tmp / "memory_structure"
        # 실행 슬롯 초기화 — 다른 테스트가 남긴 가짜 _proc 이 409 를 만들면 안 된다
        self._orig_proc = console_app._proc
        console_app._proc = None
        self.c = TestClient(console_app.app)

    def tearDown(self):
        paths.DATA = self._orig_data
        self.mod.SOLO_DIR = self._orig_solo
        self.mod._proc = self._orig_proc
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_run(self, model, doc, dry=False):
        d = (self.mod.SOLO_DIR / "runs" / "_dry" / model) if dry \
            else (self.mod.SOLO_DIR / "runs" / model)
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"run_{doc['run_id']}.json"
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return p

    def _write_judge(self, model, doc):
        d = self.mod.SOLO_DIR / "judgments" / model
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"judge_{doc['run_id']}.json"
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return p


class TestScan(SoloBase):
    def test_lists_runs_with_meta_and_judged_flag(self):
        self._write_run("gpt", _run_doc("A_note_rep1"))
        self._write_run("gpt", _run_doc("A_full_rep1", mem="full"))
        self._write_judge("gpt", _judge_doc("A_note_rep1", self.issue_id,
                                            [f"f{i}" for i in range(6)]))
        runs = self.c.get("/api/solo/runs").json()["runs"]
        self.assertEqual(len(runs), 2)
        note = next(r for r in runs if r["run_id"] == "A_note_rep1")
        self.assertEqual(note["model"], "gpt")
        self.assertEqual(note["version"], "v1")
        self.assertTrue(note["judged"])
        full = next(r for r in runs if r["run_id"] == "A_full_rep1")
        self.assertFalse(full["judged"])

    def test_v1_meta_absence_is_none_not_default(self):
        # v1 산출물엔 facts_order·stance·final_poll 이 없다 — None 으로 나가야 화면이
        # "v1"로 적을 수 있다. 기본값(original/True/False)으로 채우면 부재와 지정이 뭉친다.
        self._write_run("gpt", _run_doc("A_note_rep1", ver="solo-v1"))
        r = self.c.get("/api/solo/runs").json()["runs"][0]
        self.assertIsNone(r["facts_order"])
        self.assertIsNone(r["stance"])
        self.assertIsNone(r["final_poll"])

    def test_v2_meta_present(self):
        self._write_run("gpt", _run_doc("A_note_b250_rep1", ver="solo-v2-draft",
                                        note_budget=250))
        r = self.c.get("/api/solo/runs").json()["runs"][0]
        self.assertEqual(r["version"], "v2")
        self.assertEqual(r["note_budget"], 250)
        self.assertEqual(r["facts_order"], "original")

    def test_dry_runs_marked_separately(self):
        self._write_run("gpt", _run_doc("A_note_rep1"))
        self._write_run("gpt", _run_doc("A_note_rep1", dry=True), dry=True)
        runs = self.c.get("/api/solo/runs").json()["runs"]
        self.assertEqual(sorted(r["dry"] for r in runs), [False, True])
        # dry 런은 채점 대상이 아니다
        self.assertTrue(all(not r["judged"] for r in runs if r["dry"]))

    def test_partial_only_run_is_visible(self):
        d = self.mod.SOLO_DIR / "runs" / "gpt"
        d.mkdir(parents=True)
        (d / "run_B_prev_rep2.partial.jsonl").write_text("{}\n", encoding="utf-8")
        runs = self.c.get("/api/solo/runs").json()["runs"]
        self.assertEqual(len(runs), 1)
        self.assertTrue(runs[0]["partial"])
        self.assertEqual(runs[0]["run_id"], "B_prev_rep2")

    def test_completed_run_hides_its_own_partial(self):
        p = self._write_run("gpt", _run_doc("A_note_rep1"))
        (p.parent / "run_A_note_rep1.partial.jsonl").write_text("{}\n", encoding="utf-8")
        runs = self.c.get("/api/solo/runs").json()["runs"]
        self.assertEqual(len(runs), 1)
        self.assertFalse(runs[0]["partial"])

    def test_empty_dirs_ok(self):
        self.assertEqual(self.c.get("/api/solo/runs").json()["runs"], [])

    def test_broken_json_listed_as_broken_not_500(self):
        # 리뷰 ④·⑩: 깨진 결과 파일을 조용히 빼면 잔존 .partial 이 "체크포인트만"으로
        # 위장되고, 내용이 null 인 유효 JSON 은 종전 코드에서 목록 전체를 500 으로 죽였다.
        d = self.mod.SOLO_DIR / "runs" / "gpt"
        d.mkdir(parents=True)
        (d / "run_A_note_rep1.json").write_text("null", encoding="utf-8")
        (d / "run_A_note_rep1.partial.jsonl").write_text("{}\n", encoding="utf-8")
        (d / "run_B_full_rep2.json").write_text("{절반만 쓰다 만", encoding="utf-8")
        r = self.c.get("/api/solo/runs")
        self.assertEqual(r.status_code, 200)
        runs = r.json()["runs"]
        self.assertEqual(len(runs), 2)                       # partial 위장 행 없음
        self.assertTrue(all(x["broken"] for x in runs))
        self.assertFalse(any(x["partial"] for x in runs))


class TestEstimate(SoloBase):
    def _est(self, **over):
        body = {"model": "gpt", "arms": ["A"], "memories": ["full"], "reps": [1]}
        body.update(over)
        return self.c.post("/api/solo/estimate", json=body)

    def test_formula_full_prev_5_note_8(self):
        # 워크오더 §1 산식 그대로: 런 수 × (full/prev 5콜, note 8콜)
        self.assertEqual(self._est().json()["calls"], 5)
        self.assertEqual(self._est(memories=["prev"]).json()["calls"], 5)
        self.assertEqual(self._est(memories=["note"]).json()["calls"], 8)
        d = self._est(arms=["A", "P", "B"], memories=["full", "note", "prev"],
                      reps=[1, 2, 3]).json()
        self.assertEqual(d["runs"], 27)
        self.assertEqual(d["calls"], 3 * 3 * (5 + 8 + 5))    # 162

    def test_final_poll_adds_one_per_run(self):
        base = self._est(arms=["A"], memories=["full", "note"], reps=[1, 2]).json()
        d = self._est(arms=["A"], memories=["full", "note"], reps=[1, 2],
                      ns_final_poll=True).json()
        self.assertEqual(d["calls"], base["calls"] + d["runs"])
        self.assertEqual(d["runs"], 4)

    def test_v2_detection_and_suffix(self):
        self.assertFalse(self._est().json()["is_v2"])
        d = self._est(note_budget=250, facts_reverse=True, ns_final_poll=True).json()
        self.assertTrue(d["is_v2"])
        self.assertEqual(d["suffix"], "_b250_rev_ns")     # run_solo._variant_suffix 와 동일
        self.assertEqual(len(d["v2_reasons"]), 3)

    def test_rejects_unknown_condition(self):
        self.assertEqual(self._est(arms=["Z"]).status_code, 400)
        self.assertEqual(self._est(memories=["nope"]).status_code, 400)

    def test_rejects_off_menu_budget(self):
        # 리뷰 ⑨: UI 는 select 라 안전하지만 API 오타(250→50, 2500)가 사전등록에 없는
        # 예산의 v2 산출물을 과금과 함께 만든다 — 콘솔이 유일한 방어선.
        self.assertEqual(self._est(note_budget=2500).status_code, 400)
        self.assertEqual(self._est(note_budget=50).status_code, 400)
        self.assertEqual(self._est(note_budget=250).status_code, 200)

    def test_calls_max_covers_note_retry_ceiling(self):
        # 리뷰 ⑤: note 런은 수첩 반려 재호출로 8→최대 11콜. 상한이 함께 나가야
        # 과금이 견적을 넘는 방향이 화면에 보인다.
        d = self._est(memories=["note"]).json()
        self.assertEqual(d["calls"], 8)
        self.assertEqual(d["calls_max"], 11)
        self.assertEqual(d["note_retry_max"], 3)
        d2 = self._est(memories=["full", "prev"]).json()
        self.assertEqual(d2["calls_max"], d2["calls"])       # note 없으면 상한 = 견적
        self.assertEqual(d2["note_retry_max"], 0)

    def test_existing_runs_reported_for_skip_preview(self):
        # 이미 결과가 있는 런은 러너가 [skip] — 견적의 과대 방향도 미리 보인다.
        self._write_run("gpt", _run_doc("A_full_rep1", mem="full"))
        d = self._est(memories=["full"], reps=[1, 2]).json()
        self.assertEqual(d["existing"], ["A_full_rep1"])


class TestRunGate(SoloBase):
    """사전등록 관문 — 콘솔이 러너의 --allow-v2 관문을 무력화하지 않는가(§2-3)."""

    def _run(self, **over):
        body = {"model": "gpt", "arms": ["A"], "memories": ["note"], "reps": [1],
                "dry": False, "prereg_confirmed": False}
        body.update(over)
        # 러너 파일 존재 검사 통과용 빈 파일
        (self.mod.SOLO_DIR).mkdir(parents=True, exist_ok=True)
        (self.mod.SOLO_DIR / "run_solo.py").write_text("# stub", encoding="utf-8")
        with mock.patch.object(llm, "preflight",
                               lambda model, temperature=None, reasoning=None: {}), \
             mock.patch("subprocess.Popen") as popen:
            popen.return_value.stdout.readline.return_value = ""   # _tail_reader 즉시 종료
            popen.return_value.poll.return_value = 0
            r = self.c.post("/api/solo/run", json=body)
        self.mod._proc = None      # 가짜 _proc 잔존물 정리
        return r, popen

    def test_v2_without_confirm_is_rejected(self):
        r, popen = self._run(note_budget=250)
        self.assertEqual(r.status_code, 400)
        self.assertIn("PROMPTS_v2", r.json()["detail"])
        popen.assert_not_called()      # 러너가 뜨기 전에 막혀야 한다

    def test_v2_confirmed_appends_allow_v2(self):
        r, popen = self._run(note_budget=250, prereg_confirmed=True)
        self.assertEqual(r.status_code, 200, r.text)
        cmd = popen.call_args[0][0]
        self.assertIn("--allow-v2", cmd)
        self.assertIn("--note-budget", cmd)

    def test_v1_never_gets_allow_v2_even_if_confirmed(self):
        # 확인을 눌러놨어도 v1 조건이면 --allow-v2 를 붙일 이유가 없다 — 붙이면
        # "관문 플래그가 습관적으로 붙는" 길이 열린다.
        r, popen = self._run(prereg_confirmed=True)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotIn("--allow-v2", popen.call_args[0][0])

    def test_dry_needs_no_confirm_and_no_allow_v2(self):
        # 러너와 같은 규칙: --dry 는 관문 밖(0콜). --allow-v2 도 안 붙는다.
        r, popen = self._run(note_budget=250, dry=True)
        self.assertEqual(r.status_code, 200, r.text)
        cmd = popen.call_args[0][0]
        self.assertIn("--dry", cmd)
        self.assertNotIn("--allow-v2", cmd)

    def test_ns_final_poll_maps_to_both_flags(self):
        # 러너가 final_poll 단독을 즉사시키므로 콘솔은 묶음 한 칸 — 항상 쌍으로 나가야 한다.
        r, popen = self._run(ns_final_poll=True, prereg_confirmed=True)
        self.assertEqual(r.status_code, 200, r.text)
        cmd = popen.call_args[0][0]
        self.assertIn("--no-stance", cmd)
        self.assertIn("--final-poll", cmd)

    def test_rejects_empty_selection(self):
        r, popen = self._run(arms=[])
        self.assertEqual(r.status_code, 400)
        popen.assert_not_called()

    def test_ns_collision_with_existing_no_poll_run_is_blocked(self):
        # 리뷰 ⑦ 완화: 러너의 _ns 접미사는 final_poll 을 인코딩하지 않는다(러너 소관 —
        # 보고 대상). CLI --no-stance 단독 런이 이미 있으면 러너가 [skip] 해 "최종 판단"
        # 실행이 조용히 무효가 된다 — 콘솔이 실행 전에 시끄럽게 막아야 한다.
        self._write_run("gpt", _run_doc("A_note_ns_rep1", ver="solo-v2-draft"))
        r, popen = self._run(ns_final_poll=True, prereg_confirmed=True)
        self.assertEqual(r.status_code, 409)
        self.assertIn("final_poll", r.json()["detail"])
        popen.assert_not_called()

    def test_ns_no_collision_when_existing_has_final_poll(self):
        # 기존 산출물이 이미 final_poll 을 가진 같은 조건이면 [skip] 이 정당하다 — 통과.
        self._write_run("gpt", _run_doc("A_note_ns_rep1", ver="solo-v2-draft",
                                        stance=False, final_poll=True))
        r, popen = self._run(ns_final_poll=True, prereg_confirmed=True)
        self.assertEqual(r.status_code, 200, r.text)

    def test_ns_collision_not_checked_on_dry(self):
        # 드라이런은 runs/_dry 로 가므로 실런과 충돌하지 않는다 — 막으면 리허설을 못 한다.
        self._write_run("gpt", _run_doc("A_note_ns_rep1", ver="solo-v2-draft"))
        r, popen = self._run(ns_final_poll=True, dry=True)
        self.assertEqual(r.status_code, 200, r.text)


class TestDetail(SoloBase):
    def test_note_margin_is_budget_minus_len(self):
        # 발견 ④(자리가 남는데 버림)의 화면 재료 — 여백 = 예산 − 글자 수.
        self._write_run("gpt", _run_doc("A_note_rep1"))     # 수첩 "가나다라마" = 5자
        d = self.c.get("/api/solo/detail?model=gpt&run_id=A_note_rep1").json()
        self.assertEqual(d["note_budget"], 500)
        for n in d["notes"]:
            self.assertEqual(n["len"], 5)
            self.assertEqual(n["margin"], 495)

    def test_v1_has_no_final_poll_field(self):
        self._write_run("gpt", _run_doc("A_note_rep1"))
        d = self.c.get("/api/solo/detail?model=gpt&run_id=A_note_rep1").json()
        self.assertIsNone(d["final_poll"])

    def test_v2_final_poll_returned_verbatim(self):
        self._write_run("gpt", _run_doc("A_note_ns_rep1", ver="solo-v2-draft",
                                        stance=False, final_poll=True))
        d = self.c.get("/api/solo/detail?model=gpt&run_id=A_note_ns_rep1").json()
        self.assertEqual(d["final_poll"], "무레온 캠프")

    def test_missing_run_404(self):
        r = self.c.get("/api/solo/detail?model=gpt&run_id=nope")
        self.assertEqual(r.status_code, 404)

    def test_path_traversal_rejected(self):
        # 리뷰 ⑧: run_id/model 은 경로에 결합된다 — '..' 로 runs/ 밖(정답 누설 필드가
        # 있는 data/ 등)을 읽을 수 있으면 안 된다.
        r = self.c.get("/api/solo/detail",
                       params={"model": "gpt", "run_id": "x/../../../data/facts/facts_issue_note"})
        self.assertEqual(r.status_code, 400)
        r2 = self.c.get("/api/solo/detail", params={"model": "..", "run_id": "x"})
        self.assertEqual(r2.status_code, 400)

    def test_broken_run_file_is_422_not_500(self):
        d = self.mod.SOLO_DIR / "runs" / "gpt"
        d.mkdir(parents=True)
        (d / "run_A_note_rep1.json").write_text("null", encoding="utf-8")
        r = self.c.get("/api/solo/detail?model=gpt&run_id=A_note_rep1")
        self.assertEqual(r.status_code, 422)
        self.assertIn("깨진", r.json()["detail"])


class TestGrid(SoloBase):
    def test_grid_shape_and_statuses(self):
        fids = [f"f{i}" for i in range(6)]
        self._write_run("gpt", _run_doc("A_note_rep1"))
        self._write_judge("gpt", _judge_doc("A_note_rep1", self.issue_id, fids,
                                            mentioned_at=("essay_r0", "carrier"),
                                            split_cell=("f2", "essay_r1")))
        d = self.c.get("/api/solo/grid?model=gpt&run_id=A_note_rep1").json()
        self.assertEqual(d["stages"],
                         ["essay_r0", "essay_r1", "essay_r2", "essay_r3", "carrier"])
        self.assertEqual(len(d["rows"]), 6)
        row0 = d["rows"][0]
        self.assertEqual(row0["fact_id"], "f0")
        self.assertEqual(row0["text"], "사실 0")           # 행 라벨 = 팩트 원문
        self.assertEqual(row0["cells"][0]["status"], "mentioned")
        self.assertEqual(row0["cells"][1]["status"], "unmentioned")
        self.assertEqual(row0["cells"][4]["status"], "mentioned")
        # 표 분열 셀 — 3표가 갈린 곳은 split 로 드러난다(judge 신뢰도의 직접 관측)
        f2 = next(r for r in d["rows"] if r["fact_id"] == "f2")
        self.assertTrue(f2["cells"][1]["split"])
        self.assertFalse(row0["cells"][0]["split"])

    def test_aggregate_across_reps(self):
        fids = [f"f{i}" for i in range(6)]
        for rep in (1, 2, 3):
            self._write_run("gpt", _run_doc(f"A_note_rep{rep}"))
            at = ("essay_r0", "carrier") if rep < 3 else ("essay_r0",)
            self._write_judge("gpt", _judge_doc(f"A_note_rep{rep}", self.issue_id,
                                                fids, mentioned_at=at))
        d = self.c.get("/api/solo/grid?model=gpt&run_id=A_note_rep1").json()
        self.assertIsNotNone(d["agg"])
        self.assertEqual(d["agg"]["n_runs"], 3)
        self.assertEqual(d["agg"]["condition"], "A_note")
        row0 = d["agg"]["rows"][0]
        self.assertEqual(row0["cells"][0], 3)     # essay_r0: 3런 전부 mentioned
        self.assertEqual(row0["cells"][4], 2)     # carrier: rep1·2 만
        self.assertEqual(row0["cells"][1], 0)

    def test_aggregate_keeps_v2_suffix_conditions_apart(self):
        # 조건 키 = run_id 에서 _rep 만 뗀 것 — b250 런이 v1 런과 섞이면 안 된다.
        fids = [f"f{i}" for i in range(6)]
        self._write_run("gpt", _run_doc("A_note_rep1"))
        self._write_run("gpt", _run_doc("A_note_b250_rep1", ver="solo-v2-draft",
                                        note_budget=250))
        self._write_judge("gpt", _judge_doc("A_note_rep1", self.issue_id, fids))
        self._write_judge("gpt", _judge_doc("A_note_b250_rep1", self.issue_id, fids))
        d = self.c.get("/api/solo/grid?model=gpt&run_id=A_note_rep1").json()
        self.assertIsNone(d["agg"])     # 형제 없음 — b250 은 다른 조건

    def test_unjudged_404(self):
        self._write_run("gpt", _run_doc("A_note_rep1"))
        r = self.c.get("/api/solo/grid?model=gpt&run_id=A_note_rep1")
        self.assertEqual(r.status_code, 404)

    def test_path_traversal_rejected(self):
        r = self.c.get("/api/solo/grid",
                       params={"model": "gpt", "run_id": "x/../../secret"})
        self.assertEqual(r.status_code, 400)

    def test_broken_judgment_is_422_not_500(self):
        # judge_solo.py CLI 와 병행 사용은 콘솔 자신이 안내하는 패턴 — 쓰다 만 판정
        # 파일을 만나면 500 이 아니라 무엇이 왜 안 열리는지 말해야 한다(리뷰 ⑩).
        d = self.mod.SOLO_DIR / "judgments" / "gpt"
        d.mkdir(parents=True)
        (d / "judge_A_note_rep1.json").write_text('{"records": {', encoding="utf-8")
        r = self.c.get("/api/solo/grid?model=gpt&run_id=A_note_rep1")
        self.assertEqual(r.status_code, 422)

    def test_broken_sibling_skipped_in_aggregate(self):
        # 형제 하나가 쓰다 만 파일이어도 멀쩡한 격자·농도는 나와야 하고,
        # 빠진 형제는 skipped 로 드러나야 한다(농도 분모가 줄어든 이유).
        fids = [f"f{i}" for i in range(6)]
        for rep in (1, 2):
            self._write_judge("gpt", _judge_doc(f"A_note_rep{rep}", self.issue_id, fids))
        jd = self.mod.SOLO_DIR / "judgments" / "gpt"
        (jd / "judge_A_note_rep3.json").write_text('{"쓰다 만', encoding="utf-8")
        r = self.c.get("/api/solo/grid?model=gpt&run_id=A_note_rep1")
        self.assertEqual(r.status_code, 200)
        agg = r.json()["agg"]
        self.assertEqual(agg["n_runs"], 2)
        self.assertEqual(agg["skipped_run_ids"], ["A_note_rep3"])
        self.assertEqual(agg["rows"][0]["cells"][0], 2)


if __name__ == "__main__":
    unittest.main()
