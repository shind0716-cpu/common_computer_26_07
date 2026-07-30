# -*- coding: utf-8 -*-
"""두 판 API 조립 계층과 화면 배선 검증."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import access_window as aw
from modules import paths
from modules import transmission as tr

try:
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from tools.viewer import app as viewer_app
    HAVE_APP = True
except Exception:
    HAVE_APP = False

ISSUE = "issue_esa"
A = "dryrun2"
B = "fixture_v03"


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestPairApi(unittest.TestCase):
    def setUp(self):
        if not paths.judgment(ISSUE, A).exists() or not paths.judgment(ISSUE, B).exists():
            self.skipTest("dryrun2/fixture_v03 픽스처 없음")

    def test_both_runs_and_utterance_originals_are_present(self):
        d = viewer_app.api_pair(ISSUE, A, B)
        self.assertEqual([r["run_id"] for r in d["records"]], [A, B])
        self.assertTrue(d["records"][0]["utterances"])
        self.assertTrue(d["records"][1]["utterances"])
        self.assertEqual(d["data_root"], str(paths.DATA))

    def test_far_is_judgment_summary_value_not_recalculated(self):
        d = viewer_app.api_pair(ISSUE, A, B)
        for run in (A, B):
            jd = json.loads(paths.judgment(ISSUE, run).read_text(encoding="utf-8"))
            rec = next(r for r in d["records"] if r["run_id"] == run)
            self.assertEqual(rec["far"]["by_stage"], jd["summary"]["far_by_stage"])
            self.assertEqual(rec["far"]["final"], jd["summary"]["far_system"])
            self.assertEqual(rec["far"]["final_critical"], jd["summary"]["far_critical"])

    def test_divergence_is_symmetric_under_run_order(self):
        ab = viewer_app.api_pair(ISSUE, A, B)["divergences"]
        ba = viewer_app.api_pair(ISSUE, B, A)["divergences"]
        coords = lambda rows: {(r["fact_id"], r["stage"]) for r in rows}
        self.assertEqual(coords(ab), coords(ba))

    def test_access_agents_match_access_window_output(self):
        judgment = json.loads(paths.judgment(ISSUE, A).read_text(encoding="utf-8"))
        assignment = json.loads(paths.assignment(ISSUE).read_text(encoding="utf-8"))
        events = [json.loads(line) for line in
                  paths.debate(ISSUE, A).read_text(encoding="utf-8").splitlines()
                  if line.strip()]
        rounds, mentions = tr.mention_map(judgment)
        acc, _lit, _meta = aw.access_sets(rounds, mentions, assignment, events)
        agent_ids = [a["agent_id"] for a in assignment["agents"]]
        expected = {
            (fact_id, rounds[idx]): [a for a in agent_ids if fact_id in by_agent.get(a, set())]
            for idx, by_agent in acc.items()
            for fact_id in {f["fact_id"] for f in judgment["stages"][idx]["facts"]}
        }
        audit = viewer_app.api_audit(ISSUE, A)
        actual = {(f["fact_id"], c["stage"]): c["access_agents"]
                  for f in audit["facts"] for c in f["cells"]}
        self.assertEqual(actual, expected)

    def test_shape_agent_count_and_logged_topology_are_data_driven(self):
        out = viewer_app.api_pair(ISSUE, A, B)
        assignment = json.loads(paths.assignment(ISSUE).read_text(encoding="utf-8"))
        self.assertEqual(out["shape"]["n_agents"], {A: len(assignment["agents"]),
                                                       B: len(assignment["agents"])})
        events = [json.loads(line) for line in
                  paths.debate(ISSUE, A).read_text(encoding="utf-8").splitlines()
                  if line.strip()]
        seating = next(e for e in events if e.get("event") == "seating")
        topo = next(r for r in out["scope"]["runs"] if r["run_id"] == A)["topology"]
        self.assertEqual(topo["structure"], seating["structure"])
        self.assertEqual(topo["order"], seating["order"])
        self.assertFalse(topo["assumed_full"])

    def test_missing_seating_uses_assignment_order_and_assumed_full(self):
        assignment = {"agents": [{"agent_id": "a2"}, {"agent_id": "a1"}]}
        audit = {
            "judge": {}, "far": {}, "facts": [], "access": {},
            "utterances": {"0": [{"agent_id": "a2", "text": ""}]},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            debate = root / "debate.jsonl"
            debate.write_text(json.dumps({"event": "utterance", "round": 0}, ensure_ascii=False),
                              encoding="utf-8")
            assignment_path = root / "assignment.json"
            assignment_path.write_text(json.dumps(assignment, ensure_ascii=False), encoding="utf-8")
            with (patch.object(viewer_app, "api_audit", return_value=audit),
                  patch.object(viewer_app, "api_ledger",
                               return_value={"ledger_mode": "off", "injections": []}),
                  patch.object(viewer_app, "api_analysis", return_value={"report": {}}),
                  patch.object(viewer_app, "_run_meta", return_value=None),
                  patch.object(paths, "debate", return_value=debate),
                  patch.object(paths, "assignment", return_value=assignment_path)):
                topo = viewer_app._pair_record(ISSUE, "no_seating")["topology"]
        self.assertEqual(topo, {
            "structure": "full", "order": ["a2", "a1"],
            "edges": {"a2": ["a1"], "a1": ["a2"]}, "assumed_full": True,
        })

    def test_pairs_with_and_without_intervention_return_200(self):
        client = TestClient(viewer_app.app)
        self.assertEqual(client.get(f"/api/pair/{ISSUE}/{B}/{A}").status_code, 200)
        self.assertEqual(client.get(f"/api/pair/{ISSUE}/dryrun/{A}").status_code, 200)

    def test_decomposition_uses_coordinate_only_fact_rows_copy(self):
        html = (Path(viewer_app.__file__).with_name("pair.html")).read_text(encoding="utf-8")
        self.assertIn("D.fact_rows", html)
        self.assertIn("처음 갈린 라운드", html)
        self.assertIn("갈린 칸이 없다 — 이 두 판은 모든 칸에서 같은 판정을 받았다.", html)
        self.assertIn("이 절은 좌표만 적는다 — 왜 갈렸는지는 ④의 발화 전문을 사람이 읽고 정한다.", html)
        self.assertNotIn("D." + "gap_facts", html)

    def test_diffusion_map_uses_data_driven_agent_seats_and_evidence_source(self):
        out = viewer_app.api_pair(ISSUE, A, B)
        for rec in out["records"]:
            self.assertIn("window_source", rec["evidence"])
        html = (Path(viewer_app.__file__).with_name("pair.html")).read_text(encoding="utf-8")
        self.assertIn('D.shape.n_agents[r.run_id]', html)
        self.assertIn("topology.order", html)
        self.assertIn("access_agents", html)
        self.assertIn("window_source", html)
        self.assertNotIn("counted.length/8", html)
        self.assertNotIn("/8*100", html)
        self.assertNotIn("/8}", html)

    def test_404_when_either_run_is_missing(self):
        with self.assertRaises(HTTPException) as cm:
            viewer_app.api_pair(ISSUE, A, "no_such_run")
        self.assertEqual(cm.exception.status_code, 404)

    def test_root_is_pair_and_removed_routes_are_404(self):
        client = TestClient(viewer_app.app)
        root = client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertIn("<title>두 판", root.text)
        self.assertIn(">두 판<", root.text)
        self.assertEqual(client.get("/ledger").status_code, 404)
        self.assertEqual(client.get("/transmission").status_code, 404)
        self.assertEqual(client.get(f"/api/transmission/{ISSUE}/{A}").status_code, 404)
        self.assertEqual(client.get("/gap").status_code, 404)
        old_api = "/api/" + "gap" + f"/{ISSUE}/{A}/{B}"
        self.assertEqual(client.get(old_api).status_code, 404)

    def test_run_catalog_uses_runs_and_provenance_without_rewriting_health(self):
        d = viewer_app.api_provenance(ISSUE, A)
        self.assertIn("baseline_eligible", d["health"])
        self.assertIn("issues", d["health"])
        html = (Path(viewer_app.__file__).with_name("pair.html")).read_text(encoding="utf-8")
        self.assertIn("/api/runs", html)
        self.assertIn("/api/provenance/", html)
        self.assertIn("판이 하나뿐이라 나란히 놓을 수 없다. 대조·전기에서 이 판을 볼 수 있다.", html)
        self.assertIn("자격 있음", html)
        self.assertIn("자격 없음", html)

if __name__ == "__main__":
    unittest.main()
