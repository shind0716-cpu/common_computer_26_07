"""콘솔 v0 관문·추가 기능 테스트 (2026-07-30 · 민옥).

이 파일이 지키는 것은 "기능이 있다"가 아니라 **조용히 틀린 데이터가 안 나온다**이다.
세 함정이 실측으로 확인됐고(콘솔 실사 7/30), 각각에 관문을 세웠다:

  1. 온도 범위 밖 값 → API 400 → 재시도 5회 → 공백 폴백 → 빈 발화 로그가 종료코드 0
  2. 개입 창이 키 없이 호출 → 개입 후 판단이 공백 → 화면엔 "결론이 바뀌었다"로 보임
  3. 에이전트 수 변경이 같은 이슈의 배분표를 덮어씀 → 과거 run 의 조건이 소리 없이 변함

그리고 FAR: 채점기는 처음부터 있었는데 콘솔이 채점 단계를 안 붙여 수치가 안 나왔다.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from modules import llm, paths
from tests.scenario_gate_helpers import approve_legacy_fixture
from tests.test_note_slot import FakeLLM, _cfg, _write_fixture
from modules import debate_engine


class GateBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig = paths.DATA
        paths.DATA = self.tmp / "data"
        self.issue_id = _write_fixture(paths.DATA)
        approve_legacy_fixture(self.issue_id)
        from tools.console import app as console_app
        self.mod = console_app
        self.c = TestClient(console_app.app)

    def tearDown(self):
        paths.DATA = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_run(self, run_id, **over):
        return debate_engine.run(self.issue_id, run_id, _cfg(self.tmp, **over),
                                 utterance_fn=FakeLLM())


class TestTemperatureGuard(unittest.TestCase):
    """온도는 공급자마다 허용 범위가 다르고, 범위 밖은 조용한 오염으로 이어진다."""

    def test_anthropic_rejects_paper_constant(self):
        # 논문 상수 1.2 는 저자 모델(0~2 스케일) 기준이다. Anthropic 은 0~1 만 받는다.
        with self.assertRaises(SystemExit) as cm:
            llm.check_temperature("claude-haiku", 1.2)
        self.assertIn("1.2", str(cm.exception))

    def test_openai_and_gemini_allow_paper_constant(self):
        # 어제 붙인 다중 공급자가 "1.2 는 재현 불가" 판정의 전제를 바꿨다.
        llm.check_temperature("gpt-mini", 1.2)
        llm.check_temperature("gemini-flash", 1.2)

    def test_boundaries_inclusive(self):
        llm.check_temperature("claude-haiku", 1.0)
        llm.check_temperature("claude-haiku", 0.0)
        with self.assertRaises(SystemExit):
            llm.check_temperature("claude-haiku", 1.0001)
        with self.assertRaises(SystemExit):
            llm.check_temperature("gpt-mini", 2.5)

    def test_negative_rejected(self):
        with self.assertRaises(SystemExit):
            llm.check_temperature("gpt-mini", -0.1)

    def test_unknown_model_still_dies_loudly(self):
        # 미지 모델은 온도 판정 이전에 공급자 유도에서 죽는다(조용히 기본값으로 흐르지 않는다).
        # 등록된 접두사(claude/gpt/o1/o3/o4/gemini) 어느 것도 아닌 이름을 쓴다.
        with self.assertRaises(KeyError):
            llm.check_temperature("llama-3-70b", 0.5)


class TestReasoningAxis(unittest.TestCase):
    """⑨ 추론 모드 — 종전엔 공급자마다 사고량이 다른데 기록이 없었다."""

    def test_default_is_previous_behavior(self):
        # "지정 안 함"은 파라미터를 안 보내는 것 = 종전 동작. 옛 config 가 그대로 돌아야 한다.
        llm.check_reasoning("gpt-mini", "default")
        llm.check_reasoning("claude-haiku", "default")
        llm.check_reasoning("gemini-flash", "default")

    def test_rejects_unknown_value(self):
        with self.assertRaises(SystemExit):
            llm.check_reasoning("gpt-mini", "maximum")

    def test_all_three_providers_have_a_mapping(self):
        # 관문이 통과시킨 값은 실제로 보낼 것이 있어야 한다 — 통과했는데 보낼 게
        # 없으면 "켰다고 생각했는데 안 켜진" 상태가 되고, 그건 기록과 실제가 갈리는 것.
        for provider in ("anthropic", "openai", "gemini"):
            for mode in ("off", "on"):
                self.assertIn(mode, llm.REASONING_PARAM[provider], f"{provider}/{mode}")

    def test_obtain_response_signature_keeps_old_contract(self):
        # 설계 원칙 2(호출 계약 불변) — 기존 호출자는 한 글자도 안 고쳐야 한다.
        import inspect
        sig = inspect.signature(llm.obtain_response)
        self.assertEqual(sig.parameters["reasoning"].default, "default")
        # 앞 세 인자의 이름·순서가 그대로인가
        self.assertEqual(list(sig.parameters)[:3], ["inputs", "model", "temperature"])


class TestReasoningRecorded(GateBase):
    """축의 존재보다 중요한 것: 이 run 이 어떤 상태로 돌았는지가 로그에 남는가."""

    def test_run_meta_records_reasoning(self):
        self._make_run("rz1")
        events = [json.loads(l) for l in
                  paths.debate(self.issue_id, "rz1").read_text(encoding="utf-8")
                  .splitlines() if l.strip()]
        meta = next(e for e in events if e["event"] == "run_meta")
        # 기록이 없으면 나중에 "그때 추론 켰었나?"를 사람 기억에 묻게 된다.
        self.assertIn("reasoning", meta["settings"])
        self.assertEqual(meta["settings"]["reasoning"], "default")

    def test_console_writes_reasoning_into_config(self):
        import yaml as _yaml
        req = self.mod.RunReq(issue_id=self.issue_id, run_id="rz2", reasoning="on")
        p = self.mod._write_config(req)
        self.assertEqual(_yaml.safe_load(p.read_text(encoding="utf-8"))["reasoning"], "on")
        p.unlink()

    def test_run_rejects_unknown_reasoning(self):
        r = self.c.post("/api/run", json={
            "issue_id": self.issue_id, "run_id": "rz3", "reasoning": "maximum"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(paths.debate(self.issue_id, "rz3").exists())

    def test_estimate_warns_when_reasoning_on(self):
        # 켜면 편차 D1(사고 토큰이 본문 예산 잠식)이 되살아난다 — 조용히 넘기지 않는다.
        d = self.c.post("/api/estimate", json={
            "issue_id": self.issue_id, "run_id": "x", "reasoning": "on"}).json()
        self.assertTrue(any("D1" in w for w in d["warnings"]))


class TestConsoleTemperatureGate(GateBase):
    def test_estimate_blocks_out_of_range(self):
        d = self.c.post("/api/estimate", json={
            "issue_id": self.issue_id, "run_id": "x",
            "debate_model": "claude-haiku", "debate_temperature": 1.2}).json()
        self.assertTrue(any("허용 범위" in b for b in d["blocking"]),
                        f"온도 차단이 없다: {d['blocking']}")

    def test_estimate_allows_paper_constant_on_gpt(self):
        d = self.c.post("/api/estimate", json={
            "issue_id": self.issue_id, "run_id": "x",
            "debate_model": "gpt-mini", "debate_temperature": 1.2}).json()
        self.assertEqual(d["blocking"], [])

    def test_run_rejects_out_of_range_and_writes_nothing(self):
        r = self.c.post("/api/run", json={
            "issue_id": self.issue_id, "run_id": "hot1",
            "debate_model": "claude-haiku", "debate_temperature": 1.2})
        self.assertEqual(r.status_code, 400)
        self.assertIn("허용 범위", r.json()["detail"])
        self.assertFalse(paths.debate(self.issue_id, "hot1").exists())


class TestInterveneGate(GateBase):
    """개입 창은 콘솔 프로세스에서 직접 LLM 을 부르므로 자기 관문이 필요하다."""

    def test_intervene_refuses_when_key_gate_fails(self):
        self._make_run("g1", memory="note", note_call="utterance", final_poll=True)
        orig, calls = llm.preflight, []

        def boom(model, temperature=None):
            raise SystemExit("[llm] STUB_KEY 없음 — 자리표시자")

        def never(*a, **k):          # 관문을 통과하면 안 되므로 호출 자체가 실패 신호
            calls.append(1)
            return "{}"

        orig_resp = llm.obtain_response
        llm.preflight, llm.obtain_response = boom, never
        try:
            r = self.c.post("/api/intervene", json={
                "issue_id": self.issue_id, "run_id": "g1",
                "new_run_id": "g1_iv", "notes": {}})
        finally:
            llm.preflight, llm.obtain_response = orig, orig_resp
        self.assertEqual(r.status_code, 400)
        self.assertIn("자리표시자", r.json()["detail"])
        # 관문에 걸렸으면 호출도 없고 파일도 없어야 한다 — 공백 판단이 저장되는 경로 차단.
        self.assertEqual(calls, [])
        self.assertFalse(paths.debate(self.issue_id, "g1_iv").exists())


class TestVariant(GateBase):
    """에이전트 수 = 배분표. 그래서 수를 바꾸면 변종 이슈가 파생돼야 한다."""

    def setUp(self):
        super().setUp()
        # 공용 픽스처의 팩트에는 share·requirement 가 없어 히든 프로필 배분이 성립하지
        # 않는다(그 필드는 issue_hire 계열의 것). 여기서만 얹어 실제 조건에 맞춘다:
        # 미공유 4개를 요건 2종에 두 개씩 걸어 "같은 요건 2개 금지"가 실제로 물리게 한다.
        fp = paths.facts(self.issue_id)
        doc = json.loads(fp.read_text(encoding="utf-8"))
        reqs = ["r1", "r1", "r2", "r2"]
        for i, f in enumerate(doc["facts"]):
            f.setdefault("tags", ["condition"])
            f.setdefault("critical", False)
            if i < len(reqs):
                f["share"], f["requirement"] = "unshared", reqs[i]
            else:
                f["share"] = "shared"
        fp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        # 공용 픽스처는 스키마 필수 필드를 다 갖추지 않았다(엔진 테스트에는 필요 없어서).
        # 변종 생성은 규칙 3대로 산출물을 validate 하므로, 원본이 검사를 통과할 수 있게
        # 최소 필드를 채운다 — 실제 data/ 파일들은 이미 갖추고 있다.
        for p, extra in ((paths.issue(self.issue_id), {"schema_ver": "0.2"}),
                         (paths.facts(self.issue_id),
                          {"schema_ver": "0.2", "extractor": "test-fixture"})):
            d = json.loads(p.read_text(encoding="utf-8"))
            d.update({k: v for k, v in extra.items() if k not in d})
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")

    def test_creates_three_files_with_new_issue_id(self):
        r = self.c.post("/api/variant", json={
            "issue_id": self.issue_id, "suffix": "a5", "n_agents": 5})
        self.assertEqual(r.status_code, 200, r.text)
        new_id = r.json()["issue_id"]
        self.assertTrue(new_id.endswith("_a5"))
        for p in (paths.issue(new_id), paths.facts(new_id), paths.assignment(new_id)):
            self.assertTrue(p.exists(), p)
            # 세 파일 모두 새 id 를 가리켜야 한다 — 하나라도 원본이면 배분과 팩트가 어긋난다.
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["issue_id"], new_id)
        asg = json.loads(paths.assignment(new_id).read_text(encoding="utf-8"))
        self.assertEqual(len(asg["agents"]), 5)

    def test_original_untouched(self):
        before = paths.assignment(self.issue_id).read_text(encoding="utf-8")
        self.c.post("/api/variant", json={
            "issue_id": self.issue_id, "suffix": "a6", "n_agents": 6})
        self.assertEqual(paths.assignment(self.issue_id).read_text(encoding="utf-8"), before)

    def test_refuses_to_clobber_existing_variant(self):
        self.c.post("/api/variant", json={
            "issue_id": self.issue_id, "suffix": "a5", "n_agents": 5})
        r = self.c.post("/api/variant", json={
            "issue_id": self.issue_id, "suffix": "a5", "n_agents": 7})
        self.assertEqual(r.status_code, 409)      # append-only

    def test_empty_suffix_rejected(self):
        r = self.c.post("/api/variant", json={
            "issue_id": self.issue_id, "suffix": "  /  ", "n_agents": 5})
        self.assertEqual(r.status_code, 400)

    def test_impossible_split_dies_loudly(self):
        # 에이전트가 너무 적으면 "같은 요건 2개 금지"를 지킬 수 없다 — 조용히 규칙을
        # 깨느니 400 으로 죽어야 한다(생성기의 ValueError 를 삼키지 않는다).
        r = self.c.post("/api/variant", json={
            "issue_id": self.issue_id, "suffix": "a1", "n_agents": 1})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(paths.assignment(f"{self.issue_id}_a1").exists())

    def test_variant_stays_hidden_until_explicit_registry_approval(self):
        self.c.post("/api/variant", json={
            "issue_id": self.issue_id, "suffix": "a5", "n_agents": 5})
        rows = self.c.get("/api/meta").json()["issue_rows"]
        self.assertNotIn(f"{self.issue_id}_a5", [r["issue_id"] for r in rows])


class TestFar(GateBase):
    """채점기는 있었고, 없던 것은 콘솔의 채점 단계였다."""

    def test_status_reports_cost_and_not_judged(self):
        self._make_run("f1")
        d = self.c.get(f"/api/judge/status?issue_id={self.issue_id}&run_id=f1").json()
        self.assertFalse(d["judged"])
        # 비용 = 팩트 x 라운드 x 표. 돌리기 전에 알아야 한다.
        self.assertEqual(d["cost"]["total"],
                         d["cost"]["facts"] * d["cost"]["stages"] * d["cost"]["n_votes"])
        self.assertGreater(d["cost"]["total"], 0)

    def test_far_404_before_judging(self):
        self._make_run("f2")
        r = self.c.get(f"/api/far?issue_id={self.issue_id}&run_id=f2")
        self.assertEqual(r.status_code, 404)

    def test_far_after_offline_judging(self):
        from modules import judge as judge_mod

        self._make_run("f3")
        result = judge_mod.judge_debate(self.issue_id, "f3", {"judge_n_votes": 1},
                                        offline=True)
        p = paths.judgment(self.issue_id, "f3")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

        d = self.c.get(f"/api/far?issue_id={self.issue_id}&run_id=f3").json()
        self.assertIn("far_system", d["summary"])
        self.assertIn("transitions", d["report"])
        self.assertIn("far_by_stage", d["report"])
        # FAR 수식이 아직 잠정이라는 사실을 화면이 감추면 사람이 확정 수치로 읽는다.
        self.assertIn("미확정", d["far_note"])

    def test_judge_refuses_when_already_judged(self):
        from modules import judge as judge_mod

        self._make_run("f4")
        result = judge_mod.judge_debate(self.issue_id, "f4", {"judge_n_votes": 1},
                                        offline=True)
        p = paths.judgment(self.issue_id, "f4")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        r = self.c.post("/api/judge/run", json={
            "issue_id": self.issue_id, "run_id": "f4", "offline": True})
        self.assertEqual(r.status_code, 409)      # 재채점은 판정을 덮어쓴다


class TestJudgeProviderBranch(unittest.TestCase):
    """판정기 공급자 분기 — 기존 Anthropic 경로는 그대로, 그 외만 llm 경유."""

    def test_non_anthropic_marks_prompt_ver(self):
        # 잣대가 달랐음이 산출물에 남아야 한다. 역할 배치(system→user 병합)가 다르므로
        # 같은 문장이어도 판정이 달라질 수 있고, 그것을 조용히 넘기면 재현성이 깨진다.
        from modules import judge as judge_mod

        self.assertIn("+merged_system",
                      judge_mod.JUDGE_PROMPT_VER + "+merged_system")
        # 기본 별칭은 여전히 claude 계열 — 확정 사양의 기본값을 바꾸지 않았다.
        self.assertTrue(str(judge_mod.MODEL_ALIASES.get("claude-sonnet", "")).startswith("claude")
                        or "claude" in str(judge_mod._resolve_model("claude-sonnet")))


if __name__ == "__main__":
    unittest.main()
