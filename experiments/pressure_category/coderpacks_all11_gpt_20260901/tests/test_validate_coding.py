import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def envelope(pack, path, items):
    return {
        "pack": pack, "coder_id": f"{pack}_TEST",
        "instruction_version": "20260901-all11-v2", "independent": True,
        "key_access": False, "source_path": path.name,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bundle_manifest_sha256": "0" * 64, "items": items,
    }


def valid_a(pack_path):
    from build_packs import parse_pack_bytes
    items = []
    for source in parse_pack_bytes(pack_path.read_bytes())["items"]:
        quote = source["final_text"][:1]
        items.append({"id": source["id"], "q1_orientation": "모르겠다", "q2_politics": "모르겠다", "q3_beliefs": [], "evidence": {"q1": quote, "q2": quote, "q3": {}}, "confidence": {"q1": 0.5, "q2": 0.5, "q3": 0.5}, "ambiguity_note": None})
    return envelope("PACK_A", pack_path, items)


def valid_b(pack_path):
    from build_packs import parse_pack_bytes
    items = []
    for source in parse_pack_bytes(pack_path.read_bytes())["items"]:
        facts = [{"fact_no": n, "retained": False, "evidence": None, "rationale": "not present", "confidence": 0.5} for n in range(1, 13)]
        items.append({"id": source["id"], "facts": facts, "ambiguity_note": None})
    return envelope("PACK_B", pack_path, items)


def valid_c(pack_path):
    from build_packs import parse_pack_bytes
    items = []
    for source in parse_pack_bytes(pack_path.read_bytes())["items"]:
        option = source["options"][0]
        items.append({"id": source["id"], "round_options": {f"r{i}": option for i in range(4)}, "conclusion_relation": "유지", "first_flip": None, "trajectory_type": None, "evidence": {f"r{i}": source["round_texts"][f"r{i}"][:1] for i in range(4)}, "confidence": 0.5, "ambiguity_note": None})
    return envelope("PACK_C", pack_path, items)


class ValidateCodingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from build_packs import build
        cls.temp = tempfile.TemporaryDirectory()
        cls.private_temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        build(cls.folder, key_output_dir=Path(cls.private_temp.name))
        cls.schema = ROOT / "coding_output.schema.json"

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        cls.private_temp.cleanup()

    def check(self, data, name):
        from validate_coding import validate_output
        validate_output(data, self.schema, self.folder / name)

    def test_valid_full_packs_pass(self):
        self.check(valid_a(self.folder / "PACK_A_final.md"), "PACK_A_final.md")
        self.check(valid_b(self.folder / "PACK_B_factcheck.md"), "PACK_B_factcheck.md")
        self.check(valid_c(self.folder / "PACK_C_trajectory.md"), "PACK_C_trajectory.md")

    def test_duplicate_or_missing_id_rejected(self):
        data = valid_a(self.folder / "PACK_A_final.md")
        data["items"][-1] = copy.deepcopy(data["items"][0])
        with self.assertRaisesRegex(ValueError, "exact ID set|schema validation"):
            self.check(data, "PACK_A_final.md")

    def test_invalid_enum_rejected(self):
        data = valid_a(self.folder / "PACK_A_final.md")
        data["items"][0]["q1_orientation"] = "invalid"
        with self.assertRaisesRegex(ValueError, "schema validation"):
            self.check(data, "PACK_A_final.md")

    def test_wrong_source_hash_and_foreign_pack_rejected(self):
        data = valid_a(self.folder / "PACK_A_final.md")
        data["source_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "wrong source hash"):
            self.check(data, "PACK_A_final.md")
        data = valid_a(self.folder / "PACK_A_final.md")
        with self.assertRaisesRegex(ValueError, "wrong pack source path"):
            self.check(data, "PACK_B_factcheck.md")

    def test_b_missing_fact_and_conditional_evidence_rejected(self):
        data = valid_b(self.folder / "PACK_B_factcheck.md")
        data["items"][0]["facts"].pop()
        with self.assertRaisesRegex(ValueError, "schema validation"):
            self.check(data, "PACK_B_factcheck.md")
        data = valid_b(self.folder / "PACK_B_factcheck.md")
        data["items"][0]["facts"][0]["evidence"] = "foreign"
        with self.assertRaisesRegex(ValueError, "non-retained"):
            self.check(data, "PACK_B_factcheck.md")

    def test_evidence_locality_mismatch_rejected(self):
        data = valid_a(self.folder / "PACK_A_final.md")
        data["items"][0]["evidence"]["q1"] = "definitely-not-local"
        with self.assertRaisesRegex(ValueError, "evidence-locality"):
            self.check(data, "PACK_A_final.md")

    def test_field_region_locality_rejects_b_fact_list_a_poll_and_wrong_c_round(self):
        from build_packs import parse_pack_bytes
        bpath = self.folder / "PACK_B_factcheck.md"
        b = valid_b(bpath); bsource = parse_pack_bytes(bpath.read_bytes())["items"][0]
        quote = bsource["facts"][0]["text"]
        if quote not in bsource["last_notes"]:
            b["items"][0]["facts"][0].update(retained=True, evidence=quote)
            with self.assertRaisesRegex(ValueError, "evidence-locality"):
                self.check(b, "PACK_B_factcheck.md")
        apath = self.folder / "PACK_A_final.md"; a = valid_a(apath); asource = parse_pack_bytes(apath.read_bytes())["items"][0]
        poll_quote = str(asource["final_poll"])
        if poll_quote in asource["final_text"]:
            poll_quote = "poll-only-sentinel"
        a["items"][0]["evidence"]["q1"] = poll_quote
        with self.assertRaisesRegex(ValueError, "evidence-locality"):
            self.check(a, "PACK_A_final.md")
        cpath = self.folder / "PACK_C_trajectory.md"; c = valid_c(cpath); csource = parse_pack_bytes(cpath.read_bytes())["items"][0]
        wrong = csource["round_texts"]["r2"]
        if wrong not in csource["round_texts"]["r1"]:
            c["items"][0]["evidence"]["r1"] = wrong
            with self.assertRaisesRegex(ValueError, "evidence-locality"):
                self.check(c, "PACK_C_trajectory.md")

    def test_trajectory_truth_table_is_deterministic_and_descriptive(self):
        from validate_coding import derive_trajectory
        A, B, U = "A", "B", "모르겠다"
        cases = {
            (A,A,A,A): ("유지", None, None),
            (A,A,B,B): ("바뀜", "r2", "단일 전환"),
            (A,U,B,B): ("바뀜", "r2", "단일 전환"),
            (A,B,A,B): ("바뀜", "r1", "오락가락"),
            (A,B,B,A): ("유지", None, "오락가락"),
            (A,U,A,A): ("유지", None, None),
            (U,A,B,B): (U, None, "판정 불가"),
            (A,B,B,U): (U, None, "판정 불가"),
        }
        for values, expected in cases.items():
            with self.subTest(values=values):
                self.assertEqual(expected, derive_trajectory(dict(zip(("r0","r1","r2","r3"), values))))

    def test_c_invalid_option_relation_first_flip_and_trajectory_rejected(self):
        base = valid_c(self.folder / "PACK_C_trajectory.md")
        cases = []
        bad = copy.deepcopy(base); bad["items"][0]["round_options"]["r1"] = "foreign"; cases.append((bad, "invalid C option"))
        bad = copy.deepcopy(base); bad["items"][0]["conclusion_relation"] = "바뀜"; cases.append((bad, "relation inconsistent"))
        bad = copy.deepcopy(base); bad["items"][0]["first_flip"] = "r1"; cases.append((bad, "first_flip inconsistent"))
        bad = copy.deepcopy(base); bad["items"][0]["trajectory_type"] = "단일 전환"; cases.append((bad, "trajectory_type inconsistent"))
        for data, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.check(data, "PACK_C_trajectory.md")


if __name__ == "__main__":
    unittest.main()
