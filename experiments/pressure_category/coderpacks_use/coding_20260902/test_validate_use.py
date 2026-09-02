from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import validate_use as V

HERE = Path(__file__).resolve().parent
PACK = HERE.parent / "PACK_U_use_2026-09-02.md"


class ValidateUseTests(unittest.TestCase):
    def valid(self):
        sections = V.source_sections(PACK.read_text(encoding="utf-8"))
        items = []
        for item_id, section in sections.items():
            note = V.notebook_text(section)
            quote = note.strip().splitlines()[0]
            items.append({"id": item_id, "purpose": "판단 근거 보존", "purpose_evidence": quote,
                          "missing_capability": "일부 비교 재구성", "missing_evidence": None,
                          "rebuildability": "부분만", "rebuildability_evidence": quote,
                          "rationale": "일부만 남음", "confidence": 0.8})
        return {"pack": "PACK_U", "coder_id": "TEST", "instruction_version": "20260902-use-v1",
                "independent": True, "key_access": False, "source_path": PACK.name,
                "source_sha256": V.digest(PACK), "items": items}

    def test_valid_full_output(self):
        V.validate(self.valid(), PACK)

    def test_missing_id_fails(self):
        obj = self.valid(); obj["items"].pop()
        with self.assertRaises(ValueError): V.validate(obj, PACK)

    def test_foreign_quote_fails(self):
        obj = self.valid(); obj["items"][0]["purpose_evidence"] = "다른 항목에서만 존재할 구절"
        with self.assertRaises(ValueError): V.validate(obj, PACK)

    def test_wrong_source_hash_fails(self):
        obj = self.valid(); obj["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError): V.validate(obj, PACK)


if __name__ == "__main__": unittest.main()
