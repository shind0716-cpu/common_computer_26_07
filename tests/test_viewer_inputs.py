# -*- coding: utf-8 -*-
"""입력 전문 뷰 API 회귀 테스트 (/api/inputs).

이 뷰가 지켜야 할 것 두 가지만 검사한다:
  ① **없는 기록을 지어내지 않는다** — v0.2 로그(조립 명세 없음)는 status="absent" 로
     비워 두고 재구성을 시도하지 않는다. 입력을 추측해 채우면 이 뷰가 메우려던 구멍이
     더 깊어진다.
  ② **되살린 전문이 그때 그것과 같음을 스스로 증명한다** — 재조립분의 sha256 이 로그의
     prompt_hash 와 일치(hash_match)해야 한다. 조립 규칙이 엔진과 어긋나면 여기서 깨진다.

문면은 검사하지 않는다(일상어로 다듬을 때마다 깨지므로 — test_viewer_terms 와 같은 방침).
저자 저장소(DelibTrace-main)가 없는 환경에서는 discussion_* 재조립이 불가하므로 스킵한다.
"""
import hashlib
import json
import unittest

from modules import paths

try:
    from fastapi import HTTPException
    from tools.viewer import app as viewer_app
    HAVE_APP = True
except Exception:
    HAVE_APP = False

ISSUE = "issue_esa"
FIXTURE = "fixture_v03"     # v0.3 픽스처 (scripts/gen_fixture_v03.py 발행)
OLD_RUN = "dryrun2"         # v0.2 구 로그 — 조립 명세 없음


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestInputsV03(unittest.TestCase):
    def setUp(self):
        if not paths.debate(ISSUE, FIXTURE).exists():
            self.skipTest("v0.3 픽스처 없음 — python -m scripts.gen_fixture_v03")
        self.d = viewer_app.api_inputs(ISSUE, FIXTURE)
        env_err = next((i["error"] for i in self.d.get("items", [])
                        if i.get("error") and "환경" in i["error"]), None)
        if env_err:
            self.skipTest(f"재조립 환경 미비 — {env_err}")

    def test_status_ok_and_one_item_per_utterance(self):
        self.assertEqual(self.d["status"], "ok")
        events = [json.loads(ln) for ln
                  in paths.debate(ISSUE, FIXTURE).read_text(encoding="utf-8").splitlines()
                  if ln.strip()]
        n_pa = sum(1 for e in events if e.get("event") == "prompt_assembly")
        self.assertEqual(len(self.d["items"]), n_pa)
        self.assertGreater(n_pa, 0)

    def test_every_item_hash_verified(self):
        """되살린 전문의 지문 == 로그의 prompt_hash. 하나라도 어긋나면 조립 규칙 드리프트다."""
        for it in self.d["items"]:
            where = f"round {it['round']} · {it['agent_id']}"
            self.assertIsNotNone(it["text"], f"{where}: 전문이 비었다 ({it.get('error')})")
            digest = hashlib.sha256(it["text"].encode("utf-8")).hexdigest()
            self.assertEqual(digest, it["prompt_hash"], f"{where}: 지문 불일치")
            self.assertTrue(it["hash_match"], f"{where}: hash_match 가 참이 아니다")
        self.assertEqual(self.d["n_mismatch"], 0)
        self.assertEqual(self.d["n_verified"], len(self.d["items"]))

    def test_injected_text_is_literal_and_inside_the_input(self):
        """장부가 넣은 문구는 재조립이 아니라 로그 원문이며, 입력 전문 안에 그대로 들어 있다."""
        with_inj = [i for i in self.d["items"] if i.get("inject_text")]
        self.assertTrue(with_inj, "픽스처인데 재주입이 든 입력이 없다 — 픽스처 목적 미달")
        for it in with_inj:
            self.assertIn(it["inject_text"], it["text"],
                          f"round {it['round']} · {it['agent_id']}: 재주입 원문이 입력 안에 없다")
            self.assertTrue(it["inject_fact_ids"])

    def test_slots_are_coordinates_not_text(self):
        """슬롯은 좌표(참조)여야 한다 — 발화 원문을 슬롯에 복사해 두면 원장이 부풀고 진본이 갈린다."""
        cont = [i for i in self.d["items"] if i["slots"]["others"]]
        self.assertTrue(cont)
        for ref in cont[0]["slots"]["others"]:
            self.assertEqual(set(ref), {"round", "agent_id"})


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestInputsOldLog(unittest.TestCase):
    def test_v02_log_reports_absent_without_fabricating(self):
        if not paths.debate(ISSUE, OLD_RUN).exists():
            self.skipTest("dryrun2 픽스처 없음")
        d = viewer_app.api_inputs(ISSUE, OLD_RUN)
        self.assertEqual(d["status"], "absent")
        self.assertEqual(d["items"], [])
        self.assertTrue(d["rounds"], "라운드 목록은 발화에서 알 수 있으므로 비어선 안 된다")
        self.assertTrue(d["note"])

    def test_404_without_debate_log(self):
        with self.assertRaises(HTTPException):
            viewer_app.api_inputs(ISSUE, "no_such_run")


if __name__ == "__main__":
    unittest.main()
