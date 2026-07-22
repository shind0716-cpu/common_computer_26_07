"""[민옥 · 관측 레이어 트랙] viewmodel + 뷰어 생성기 테스트 — API 불필요.

검증: ① 매트릭스 완전성(전 팩트 × 전 스테이지, 레코드 부재=absent) ② status·surviving 이
judge 잣대와 일치 ③ 발화 원문 전량 보존(요약 금지) ④ 재주입 추출 ⑤ 생성 HTML 이
자기완결(데이터 내장·외부 리소스 0)이고 원본 파일을 건드리지 않음.
"""
import json
import unittest
from pathlib import Path

from modules import paths, viewmodel
from modules.judge import SURVIVING

from tests.test_integration_ledger import IntegrationBase, N_AGENTS, ROUNDS, vote_all_unmentioned

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "make_viewer", Path(__file__).resolve().parent.parent / "scripts" / "make_viewer.py")
make_viewer_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_viewer_mod)


class ViewmodelBase(IntegrationBase):
    def build(self, ledger_mode="off", vote_fn=None):
        self.run_engine(self.write_config(ledger_mode=ledger_mode), vote_fn=vote_fn)
        # 오프라인 judge 로 judgment 생성 (파일 기반 사후 채점 — 실제 소비 흐름 그대로)
        from modules import judge
        result = judge.judge_debate("issue_esa", "t1",
                                    {"judge_n_votes": 1}, offline=True)
        out = paths.judgment("issue_esa", "t1")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return viewmodel.build_viewmodel("issue_esa", "t1")


class TestViewmodel(ViewmodelBase):
    def test_matrix_complete_and_yardstick_consistent(self):
        vm = self.build()
        self.assertEqual(len(vm["facts"]), 12)
        self.assertEqual(vm["stages"], list(range(0, ROUNDS + 1)))
        for f in vm["facts"]:
            row = vm["matrix"][f["fact_id"]]
            self.assertEqual(set(row.keys()), {str(n) for n in vm["stages"]})
            for cell in row.values():
                self.assertIn(cell["status"], viewmodel.STATUS_ORDER)
                self.assertEqual(cell["surviving"], cell["status"] in SURVIVING)

    def test_utterances_full_text_no_summary(self):
        vm = self.build()
        total = sum(len(v) for v in vm["utterances"].values())
        self.assertEqual(total, N_AGENTS * (ROUNDS + 1))
        # 원문 전량 보존 — debate 로그의 발화가 그대로 있어야
        events = [json.loads(l) for l in
                  paths.debate("issue_esa", "t1").read_text(encoding="utf-8").splitlines()]
        sample = next(e for e in events if e.get("event") == "utterance" and e["round"] == 1)
        texts = [u["text"] for u in vm["utterances"]["1"]]
        self.assertIn(sample["response_text"], texts)

    def test_injects_extracted_in_v0(self):
        vm = self.build(ledger_mode="v0", vote_fn=vote_all_unmentioned)
        self.assertEqual([i["round"] for i in vm["injects"]], [2, 3])
        self.assertEqual(len(vm["injects"][0]["fact_ids"]), 12)

    def test_absent_when_record_missing(self):
        vm = self.build()
        # judgment 에서 팩트 하나를 지운 조작본으로 absent 규칙 확인
        jp = paths.judgment("issue_esa", "t1")
        doc = json.loads(jp.read_text(encoding="utf-8"))
        removed = doc["stages"][0]["facts"].pop()["fact_id"]
        jp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        vm2 = viewmodel.build_viewmodel("issue_esa", "t1")
        self.assertEqual(vm2["matrix"][removed]["0"]["status"], "absent")
        self.assertFalse(vm2["matrix"][removed]["0"]["surviving"])


class TestMakeViewer(ViewmodelBase):
    def test_html_self_contained_and_sources_untouched(self):
        self.build(ledger_mode="v0", vote_fn=vote_all_unmentioned)
        dbg = paths.debate("issue_esa", "t1").read_text(encoding="utf-8")
        out = self.tmp / "viewer.html"
        make_viewer_mod.make_viewer("issue_esa", "t1", out=out)
        html = out.read_text(encoding="utf-8")

        self.assertIn('"issue_esa"', html)              # 데이터 내장
        self.assertNotIn("/*__DATA__*/null", html)      # 자리표 치환 완료
        self.assertNotIn("http://", html)               # 외부 리소스 0 (자기완결)
        self.assertNotIn("https://", html)
        self.assertIn("팩트 생존 뷰어", html)
        # 읽기 전용 — 원본 debate 불변
        self.assertEqual(paths.debate("issue_esa", "t1").read_text(encoding="utf-8"), dbg)

    def test_script_not_broken_by_utterance_content(self):
        """발화에 </script> 가 들어 있어도 HTML 이 깨지지 않아야(이스케이프 검증)."""
        self.build()
        jp = paths.debate("issue_esa", "t1")
        lines = jp.read_text(encoding="utf-8").splitlines()
        ev = json.loads(lines[0])
        ev["response_text"] = "악의적 발화 </script><script>alert(1)</script>"
        lines[0] = json.dumps(ev, ensure_ascii=False)
        jp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out = self.tmp / "viewer2.html"
        make_viewer_mod.make_viewer("issue_esa", "t1", out=out)
        html = out.read_text(encoding="utf-8")
        self.assertNotIn("</script><script>alert", html)  # 조기 종료 없음


if __name__ == "__main__":
    unittest.main()
