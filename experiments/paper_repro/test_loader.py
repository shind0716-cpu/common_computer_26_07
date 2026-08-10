# -*- coding: utf-8 -*-
"""loader(load_issues.py) 테스트 — 완성도 리뷰 L-1 반영 (2026-08-10, 접합 계층 · 요한).

층화 표본·매핑·멱등 쓰기·정본 sha 일관성. LLM 호출 0 · 원본 파일 불필요(합성 데이터)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import load_issues as li  # noqa: E402


def _mk_items(n_no: int, n_yes: int, n_tie: int) -> list[dict]:
    """합성 원본 — gold_label 별 개수와 동점 개수를 지정해 만든다."""
    items = []
    for i in range(n_no):
        items.append({"id": f"o-no-{i}", "question": "q", "background": f"body no {i}",
                      "title": f"AITA no {i}?", "gold_label": "NO",
                      "label_scores": {"RIGHT": 7, "WRONG": 3}})
    for i in range(n_yes):
        items.append({"id": f"o-yes-{i}", "question": "q", "background": f"body yes {i}",
                      "title": f"AITA yes {i}?", "gold_label": "YES",
                      "label_scores": {"RIGHT": 3, "WRONG": 7}})
    for i in range(n_tie):
        items.append({"id": f"o-tie-{i}", "question": "q", "background": f"body tie {i}",
                      "title": f"AITA tie {i}?", "gold_label": "YES",  # 동점의 YES 강제(실측)
                      "label_scores": {"RIGHT": 5, "WRONG": 5}})
    return items


class SampleItemsTests(unittest.TestCase):
    def test_tie_drop_and_stratification_sum(self):
        items = _mk_items(30, 20, 7)
        out, pool_n, share = li.sample_items(items, 10, seed=1)
        self.assertEqual(pool_n, 50)                       # 동점 7건 제외
        self.assertEqual(sum(share.values()), 10)          # 몫 보정 후 합계 정확
        self.assertEqual(len(out), 10)
        self.assertFalse(any(x["id"].startswith("o-tie") for x in out))
        # 층화 비율 근사: NO 30/50 → 6
        self.assertEqual(share["NO"], 6)

    def test_deterministic_and_prefix_subset(self):
        """같은 시드에서 n 이 커져도 작은 표본이 부분집합 — 트랜치 확장의 전제."""
        items = _mk_items(40, 30, 0)
        small, _, _ = li.sample_items(items, 8, seed=20260810)
        large, _, _ = li.sample_items(items, 20, seed=20260810)
        again, _, _ = li.sample_items(items, 8, seed=20260810)
        self.assertEqual([x["id"] for x in small], [x["id"] for x in again])  # 결정론
        self.assertTrue({x["id"] for x in small} <= {x["id"] for x in large})  # 접두 성질

    def test_pos_is_position_in_original_file(self):
        items = _mk_items(5, 5, 0)
        out, _, _ = li.sample_items(items, 4, seed=7)
        for x in out:
            self.assertEqual(items[x["_pos"] - 1]["id"], x["id"])  # 1-based 위치 보존


class ToIssueDocTests(unittest.TestCase):
    def test_mapping_preserves_all_source_fields(self):
        item = dict(_mk_items(1, 0, 0)[0], _pos=36)
        d = li.to_issue_doc(item, "2026-08-10T00:00:00+00:00")
        self.assertEqual(d["issue_id"], "issue_ethics_0036")
        self.assertEqual(d["body"], item["background"])
        self.assertEqual(d["title"], item["title"])
        self.assertEqual(d["question"], item["title"])            # Q3 판정 — 명시 주입
        self.assertEqual(d["source"], "paper")
        self.assertIsNone(d["source_meta"]["usage_approved"])     # 라이선스 미확인 유지
        self.assertEqual(d["source_meta"]["origin_id"], item["id"])
        self.assertEqual(d["source_meta"]["origin_question"], item["question"])  # 규약 8
        self.assertEqual(d["gold"], {"label": "NO", "scores": {"RIGHT": 7, "WRONG": 3}})


class WriteIfChangedTests(unittest.TestCase):
    def test_same_content_different_timestamp_not_rewritten(self):
        item = dict(_mk_items(1, 0, 0)[0], _pos=1)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "issue_ethics_0001.json"
            self.assertTrue(li.write_if_changed(p, li.to_issue_doc(item, "2026-08-10T01:00:00+00:00")))
            before = p.read_text(encoding="utf-8")
            self.assertFalse(li.write_if_changed(p, li.to_issue_doc(item, "2026-08-11T09:99:99+00:00")))
            self.assertEqual(p.read_text(encoding="utf-8"), before)  # 원본 유지

    def test_content_change_is_rewritten(self):
        item = dict(_mk_items(1, 0, 0)[0], _pos=1)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "issue_ethics_0001.json"
            li.write_if_changed(p, li.to_issue_doc(item, "t1"))
            changed = li.to_issue_doc(dict(item, background="edited body"), "t2")
            self.assertTrue(li.write_if_changed(p, changed))
            self.assertIn("edited body", p.read_text(encoding="utf-8"))


class CanonicalShaTests(unittest.TestCase):
    def test_manifest_sha_matches_canonical(self):
        """라이브 manifest 가 있으면 정본 sha 와 일치해야 한다 — R-4 관문의 일관성."""
        mp = HERE / "data" / "sample_manifest.json"
        if not mp.exists():
            self.skipTest("라이브 manifest 없음")
        m = json.loads(mp.read_text(encoding="utf-8"))
        self.assertEqual(m["source"]["sha256"], li.CANONICAL_SHA256)


if __name__ == "__main__":
    unittest.main()
