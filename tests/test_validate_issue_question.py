# -*- coding: utf-8 -*-
"""validate 의 §1′ issue.question 타입 검사 (2026-08-10 계약 등재분, PR#34 리뷰 반영).

계약(SCHEMA.md §1′ 검증 계약): question 은 필수 키가 아니다(구 문서 호환) —
있으면 문자열인지만 본다. 얕은 계약 검사 원칙 유지(질문 형태 여부는 안 본다).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules import validate as validate_mod  # noqa: E402

BASE_ISSUE = {
    "schema_ver": "0.3",
    "created_by": "test",
    "created_at": "2026-08-10T00:00:00+00:00",
    "issue_id": "issue_q_test",
    "source": "synthetic",
    "title": "제목",
    "body": "본문",
}


class IssueQuestionTypeTests(unittest.TestCase):
    def _validate(self, doc: dict):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "issue_q_test.json"
            p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            validate_mod.validate(p)  # 실패 시 SystemExit

    def test_string_question_passes(self):
        self._validate({**BASE_ISSUE, "question": "Is the author in the wrong?"})

    def test_absent_question_passes_for_legacy_docs(self):
        self._validate(dict(BASE_ISSUE))  # 부재 = 구 문서 호환 (§1′: 부재는 '모름')

    def test_non_string_question_fails(self):
        # PR#34 리뷰 재현: question: 123 인 issue 가 [OK] 로 통과했었다
        for bad in (123, None, ["q"], {"q": 1}):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                self._validate({**BASE_ISSUE, "question": bad})


if __name__ == "__main__":
    unittest.main()
