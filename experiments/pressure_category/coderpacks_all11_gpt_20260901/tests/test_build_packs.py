import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
sys.path.insert(0, str(ROOT))
COMMIT = "64ab4017ae76aa79d1ecc86cba994288085ffcc5"


def show_json(path):
    raw = subprocess.run(["git", "-C", str(REPO), "show", f"{COMMIT}:{path}"], check=True, stdout=subprocess.PIPE).stdout
    return json.loads(raw.decode("utf-8")), raw


class BuildPacksTests(unittest.TestCase):
    def test_source_closure_is_recomputed_from_exact_66_commit_artifacts(self):
        from build_packs import collect_source_artifacts

        source = collect_source_artifacts(REPO)
        self.assertEqual(33, len(source["coordinates"]))
        self.assertEqual(66, len(source["artifact_paths"]))
        self.assertEqual(66, len(set(source["artifact_paths"])))
        self.assertEqual("b3551db787ff655816abe8c8d26c6cbb5c6612ffa1b7a331c9c86a7eccb82982", source["closure_sha256"])

    def test_source_closure_rejects_missing_duplicate_extra_and_mutation(self):
        from build_packs import collect_source_artifacts, git_blob

        baseline = collect_source_artifacts(REPO)
        paths = baseline["artifact_paths"]
        cases = [paths[:-1], paths + [paths[0]], paths + ["extra.json"]]
        for candidate in cases:
            with self.subTest(count=len(candidate)), self.assertRaisesRegex(ValueError, "artifact path set"):
                collect_source_artifacts(REPO, artifact_paths=candidate)
        mutation_target = next(path for path in paths if path.endswith(".partial.jsonl"))
        def mutated(path, *, repo=None):
            raw = git_blob(path, repo=repo)
            return raw + (b"\n" if path == mutation_target else b"")
        with self.assertRaisesRegex(ValueError, "closure mismatch"):
            collect_source_artifacts(REPO, blob_reader=mutated)

    def test_pack_b_public_facts_are_minimal_and_private_reconstruction_is_exact(self):
        from build_packs import build

        with tempfile.TemporaryDirectory() as public, tempfile.TemporaryDirectory() as private:
            result = build(Path(public), key_output_dir=Path(private))
            self.assertFalse((Path(public) / "_KEY_all11_gpt.json").exists())
            self.assertTrue((Path(private) / "_KEY_all11_gpt.json").exists())
            facts = [fact for item in result["packs"]["PACK_B_factcheck.md"] for fact in item["facts"]]
            self.assertEqual(396, len(facts))
            self.assertTrue(all(set(fact) == {"fact_no", "text"} for fact in facts))
            self.assertEqual(396, result["manifest"]["private_reconstruction"]["fact_count"])
            forbidden = ("issue_id", "vset_id", "run_id", "source_ref", "favors", "about_option", "category", "provenance_type", "material_file")
            public_text = "\n".join((Path(public) / name).read_text(encoding="utf-8") for name in ("PACK_A_final.md", "PACK_B_factcheck.md", "PACK_C_trajectory.md"))
            for token in forbidden:
                self.assertNotIn(f'"{token}"', public_text)
    def test_builder_creates_three_deterministic_33_item_packs(self):
        from build_packs import build

        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second, tempfile.TemporaryDirectory() as first_key, tempfile.TemporaryDirectory() as second_key:
            one = build(Path(first), key_output_dir=Path(first_key))
            two = build(Path(second), key_output_dir=Path(second_key))
            for name in ("PACK_A_final.md", "PACK_B_factcheck.md", "PACK_C_trajectory.md"):
                self.assertEqual(33, len(one["packs"][name]))
                self.assertEqual(hashlib.sha256((Path(first) / name).read_bytes()).hexdigest(), hashlib.sha256((Path(second) / name).read_bytes()).hexdigest())

    def test_pack_content_exactly_matches_commit_blobs(self):
        from build_packs import build

        plan, _ = show_json("experiments/pressure_category/ALL11_GPT_RUNPLAN_2026-09-01.json")
        all11, _ = show_json("experiments/pressure_category/ALL11_MANIFEST_2026-09-01.json")
        material_paths = {row["issue_id"]: "experiments/pressure_category/" + row["material_file"] for row in all11["entries"]}
        expected = {}
        for batch in plan["batches"]:
            for row in batch["items"]:
                material, _ = show_json(material_paths[row["issue_id"]])
                for rep in (1, 2, 3):
                    path = f"experiments/pressure_category/runs/gpt/{row['issue_id']}/run_C0_{row['vset_id']}_rep{rep}.json"
                    run, _ = show_json(path)
                    expected[(row["issue_id"], row["vset_id"], rep)] = (run, material)
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as private:
            result = build(Path(folder), key_output_dir=Path(private))
            manifest = result["manifest"]
            for pack, name in (("PACK_A", "PACK_A_final.md"), ("PACK_B", "PACK_B_factcheck.md"), ("PACK_C", "PACK_C_trajectory.md")):
                ordered = sorted(manifest["coordinates"], key=lambda row: hashlib.sha256(f"20260901|{pack}|{row['issue_id']}|{row['vset_id']}|{row['rep']}".encode()).hexdigest())
                for item, coordinate in zip(result["packs"][name], ordered):
                    run, material = expected[(coordinate["issue_id"], coordinate["vset_id"], coordinate["rep"])]
                    if pack == "PACK_A":
                        self.assertEqual((run["essays"][3], run["final_poll"]), (item["final_text"], item["final_poll"]))
                    elif pack == "PACK_B":
                        public_facts = [{"fact_no": n, "text": fact["text"]} for n, fact in enumerate(material["facts"], 1)]
                        self.assertEqual((run["notes"][2], public_facts), (item["last_notes"], item["facts"]))
                    else:
                        self.assertEqual(({f"r{i}": run["essays"][i] for i in range(4)}, material["options"]), (item["round_texts"], item["options"]))

    def test_manifest_hashes_and_blind_prose_are_closed(self):
        from build_packs import build

        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as private:
            out = Path(folder)
            result = build(out, key_output_dir=Path(private))
            manifest = json.loads((out / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual("05994087d15f330b6c15e4ec14a471095d49b2bd29169aaf5888ffeb340b55c4", manifest["receipt"]["sha256"])
            self.assertEqual("b3551db787ff655816abe8c8d26c6cbb5c6612ffa1b7a331c9c86a7eccb82982", manifest["run_closure_sha256"])
            orders = []
            for pack, name in (("PACK_A", "PACK_A_final.md"), ("PACK_B", "PACK_B_factcheck.md"), ("PACK_C", "PACK_C_trajectory.md")):
                orders.append([(row["issue_id"], row["rep"]) for row in sorted(manifest["coordinates"], key=lambda row: hashlib.sha256(f"20260901|{pack}|{row['issue_id']}|{row['vset_id']}|{row['rep']}".encode()).hexdigest())])
                prose = (out / name).read_text(encoding="utf-8")
                for row in manifest["coordinates"]:
                    self.assertNotIn(row["issue_id"], prose)
                    self.assertNotIn(row["vset_id"], prose)
                    self.assertNotIn(row["run_path"], prose)
                self.assertNotIn("gpt-5.4-mini", prose)
            self.assertEqual(3, len({tuple(order) for order in orders}))
            self.assertEqual(result["pack_hashes"], manifest["pack_sha256"])

    def test_protocol_and_six_prompts_enforce_isolation(self):
        protocol = (ROOT / "CODING_PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("20260901-all11-v2", protocol)
        self.assertIn("post-hoc exploratory", protocol)
        prompts = sorted((ROOT / "prompts").glob("PACK_*.txt"))
        self.assertEqual(6, len(prompts))
        for prompt in prompts:
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("tool-less", text)
            if "_SOL" in prompt.name:
                self.assertIn("BLOCKED CONFIGURATION", text)
            else:
                self.assertIn("_KEY_all11_gpt.json", text)
                self.assertIn("external web/search", text)
                self.assertIn("atomic rename", text)


if __name__ == "__main__":
    unittest.main()
