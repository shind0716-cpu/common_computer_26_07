import unittest
from pathlib import Path

from validate_coding import validate_output


def make_a_output():
    return {
        "pack": "PACK_A",
        "coder_id": "TEST",
        "coder_family": "Hermes-Sol",
        "instruction_version": "20260831-v1",
        "independent": True,
        "key_access": False,
        "source_path": "PACK_A_final.md",
        "source_sha256": "0" * 64,
        "items": [
            {
                "id": f"A-{i:02d}",
                "q1_orientation": "모르겠다",
                "q2_politics": "모르겠다",
                "q3_beliefs": [],
                "evidence": {"q1": "근거", "q2": "근거", "q3": {}},
                "confidence": {"q1": 0.5, "q2": 0.5, "q3": 0.5},
                "ambiguity_note": None,
            }
            for i in range(1, 67)
        ],
    }


class ValidateCodingTests(unittest.TestCase):
    def test_rejects_duplicate_and_missing_pack_a_id(self):
        data = make_a_output()
        data["items"][-1]["id"] = "A-65"
        with self.assertRaisesRegex(ValueError, "exact ID set"):
            validate_output(data, Path("unused"), skip_schema=True)

    def test_accepts_exact_assigned_pack_b_audit_sample(self):
        ids = ["B-06", "B-25"]
        data = {
            "pack": "PACK_B",
            "assigned_ids": ids,
            "items": [{"id": item_id} for item_id in ids],
        }
        validate_output(data, Path("unused"), skip_schema=True)

    def test_schema_rejects_invalid_pack_a_label(self):
        data = make_a_output()
        data["items"][0]["q1_orientation"] = "애매"
        schema = Path(__file__).parents[1] / "coding_output.schema.json"
        with self.assertRaisesRegex(ValueError, "schema validation"):
            validate_output(data, schema)


if __name__ == "__main__":
    unittest.main()
