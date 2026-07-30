# -*- coding: utf-8 -*-
"""판 간 대조 계층의 순수 함수 계약."""
import unittest

from modules.crossrun import (
    CrossRunError, dependencies, divergences, fact_rows,
    report, timeline,
)


def record(run_id, *, final_2=True, final_10=True, inject=False, meta=True,
           judge_votes=3, far_final="0.0830", structure="full"):
    cells = [
        {"fact_id": "f02", "stage": 1, "status": "mentioned", "surviving": True,
         "counted": ["a1"], "flags": [], "max_prox": 0.4,
         "max_prox_agent": "a1", "votes": {"split": "3/3"},
         "access_agents": ["a1", "a2"]},
        {"fact_id": "f02", "stage": 3,
         "status": "mentioned" if final_2 else "unmentioned", "surviving": final_2,
         "counted": ["a1", "a2"] if final_2 else [],
         "flags": [] if final_2 else ["split"], "max_prox": 0.875 if final_2 else 0.2,
         "max_prox_agent": "a2", "votes": {"split": "2/3"},
         "access_agents": ["a1", "a2"] if final_2 else ["a1"]},
        {"fact_id": "f10", "stage": 2,
         "status": "mentioned" if final_10 else "unmentioned", "surviving": final_10,
         "counted": ["a3"] if final_10 else [],
         "flags": [] if final_10 else ["uncounted_high", "split"],
         "max_prox": 0.1 if final_10 else 0.533,
         "max_prox_agent": "a3", "votes": {"split": "2/3"},
         "access_agents": ["a3"]},
        {"fact_id": "f10", "stage": 3,
         "status": "mentioned" if final_10 else "unmentioned", "surviving": final_10,
         "counted": ["a3"] if final_10 else [], "flags": [], "max_prox": 0.2,
         "max_prox_agent": "a3", "votes": {"split": "3/3"},
         "access_agents": ["a2", "a3"]},
    ]
    run_meta = None
    if meta:
        run_meta = {
            "condition": "ledger-on" if inject else "ledger-off",
            "config_ref": {"name": "x.yaml", "sha256": "samehash"},
            "settings": {"window": "rolling", "memory": "none", "rounds": 3,
                         "structure": "all", "stance": "mixed", "persona": "none",
                         "overlap_k": 2, "assignment_mode": "split",
                         "ledger_mode": "v0" if inject else "off"},
        }
    return {
        "run_id": run_id,
        "judge": {"model": "sonnet", "temperature": 0, "n_votes": judge_votes,
                  "aggregation": "majority", "prompt_ver": "v1"},
        "far": {"by_stage": [{"stage": 1, "far_system": "0.2500"},
                              {"stage": 3, "far_system": far_final}],
                "final": far_final, "final_critical": "0.1110"},
        "cells": cells,
        "injections": ([{"round": 3, "fact_ids": ["f02"], "reason": "missing",
                         "block_text": "[f02] 원문", "block_text_source": "rebuilt"}]
                       if inject else []),
        "evidence": {"evidence_mix": {"literal": 0, "judged": 4},
                     "judged_share": 1.0, "resurgence_rate": 0.0, "status": "ok"},
        "run_meta": run_meta,
        "topology": {
            "structure": structure, "order": ["a1", "a2", "a3"],
            "edges": {"a1": ["a2"], "a2": ["a1", "a3"], "a3": ["a2"]},
            "assumed_full": False,
        },
        "analysis": {"transitions": [{"to_stage": 3, "cond_attrition": 0.25}]},
        "utterances": {"3": [{"agent_id": "a1", "text": "전문"}]},
    }


class TestCrossRunReport(unittest.TestCase):
    def setUp(self):
        self.a = record("off", final_2=False, final_10=False, far_final="0.3330")
        self.b = record("v0", final_2=True, final_10=True, inject=True,
                        far_final="0.0830")

    def test_divergent_cells_are_symmetric_and_keep_cell_evidence(self):
        ds = divergences([self.a, self.b])
        reverse = divergences([self.b, self.a])
        self.assertEqual([(d["fact_id"], d["stage"]) for d in ds],
                         [("f02", 3), ("f10", 2), ("f10", 3)])
        self.assertEqual(
            {(d["fact_id"], d["stage"]): d["runs"] for d in ds},
            {(d["fact_id"], d["stage"]): d["runs"] for d in reverse},
        )
        self.assertEqual(set(ds[0]["runs"]), {"off", "v0"})
        self.assertEqual(ds[0]["runs"]["v0"]["n_counted"], 2)
        self.assertEqual(ds[0]["runs"]["v0"]["n_access"], 2)
        self.assertEqual(ds[0]["runs"]["v0"]["access_agents"], ["a1", "a2"])
        self.assertEqual(ds[1]["runs"]["off"]["max_prox"], 0.533)

    def test_fact_rows_are_symmetric_coordinates_without_winner_keys(self):
        rows = {r["fact_id"]: r for r in fact_rows([self.a, self.b])}
        reverse = {r["fact_id"]: r for r in fact_rows([self.b, self.a])}
        self.assertEqual(rows, reverse)
        self.assertEqual(rows["f02"]["first_divergence_stage"], 3)
        self.assertEqual(rows["f10"]["divergent_stages"], [2, 3])
        self.assertEqual(rows["f02"]["runs"]["off"]["intervention_rounds"], [])
        self.assertEqual(rows["f02"]["runs"]["v0"]["intervention_rounds"], [3])
        self.assertEqual(rows["f10"]["runs"]["off"]["first_divergence"]["n_access"], 1)
        forbidden = {"losing" + "_run", "winning" + "_run",
                     "diverged_before" + "_injection", "losing" + "_cell" + "_flags"}
        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(v) for v in value)) if value else set()
            return set()
        self.assertTrue(forbidden.isdisjoint(keys(list(rows.values()))))

    def test_fact_rows_include_middle_only_divergence(self):
        a = record("a")
        b = record("b")
        next(c for c in a["cells"] if c["fact_id"] == "f10" and c["stage"] == 2).update(
            status="unmentioned", surviving=False, counted=[])
        rows = fact_rows([a, b])
        self.assertEqual([r["fact_id"] for r in rows], ["f10"])
        self.assertEqual(rows[0]["divergent_stages"], [2])
        self.assertTrue(rows[0]["runs"]["a"]["final"]["surviving"])
        self.assertTrue(rows[0]["runs"]["b"]["final"]["surviving"])

    def test_no_intervention_and_no_divergence_is_empty(self):
        self.assertEqual(fact_rows([record("a"), record("b")]), [])
        self.assertEqual(divergences([record("a"), record("b")]), [])

    def test_far_values_pass_through_without_recalculation(self):
        rows = timeline([self.a, self.b])
        self.assertEqual(rows[-1]["runs"]["off"]["far"], "0.3330")
        self.assertEqual(rows[-1]["runs"]["v0"]["far"], "0.0830")
        out = report([self.a, self.b])
        self.assertIs(out["scope"]["runs"][0]["far"], self.a["far"])

    def test_shape_and_topology_are_passed_through(self):
        for structure in ("full", "line", "tree"):
            a, b = record("a", structure=structure), record("b", structure=structure)
            out = report([a, b])
            self.assertEqual(out["scope"]["runs"][0]["topology"], a["topology"])
            self.assertEqual(out["shape"], {
                "stages": [1, 2, 3], "n_facts": 2,
                "n_agents": {"a": 3, "b": 3}, "n_rounds": 3,
            })

    def test_invalid_topology_raises(self):
        missing = record("missing")
        del missing["topology"]
        with self.assertRaises(CrossRunError):
            report([missing, record("ok")])
        bad_edges = record("bad")
        bad_edges["topology"]["edges"]["a1"] = {"a2"}
        with self.assertRaises(CrossRunError):
            report([bad_edges, record("ok")])

    def test_dependencies_keep_evidence_and_count_split_cells(self):
        dep = dependencies([self.a, self.b])
        self.assertEqual(dep["runs"]["off"]["evidence_mix"], {"literal": 0, "judged": 4})
        self.assertEqual(dep["runs"]["off"]["split_cells"], 2)

    def test_shape_drift_raises_instead_of_silent_zero(self):
        broken = record("broken")
        del broken["cells"][0]["surviving"]
        with self.assertRaises(CrossRunError):
            report([broken, record("ok")])

    def test_requires_exactly_two_distinct_runs(self):
        with self.assertRaises(CrossRunError):
            report([self.a])
        with self.assertRaises(CrossRunError):
            report([self.a, {**self.b, "run_id": "off"}])


if __name__ == "__main__":
    unittest.main()
