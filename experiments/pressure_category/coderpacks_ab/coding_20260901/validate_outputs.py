from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_sections(kind: str, source: str) -> dict[str, str]:
    ids = list(re.finditer(rf"^## ({kind}-\d{{2}}).*?$", source, re.MULTILINE))
    return {
        match.group(1): source[match.start() : ids[index + 1].start() if index + 1 < len(ids) else len(source)]
        for index, match in enumerate(ids)
    }


def validate_item(kind: str, item: dict, local: str) -> None:
    if kind in {"W", "F"} and not 0 <= item["confidence"] <= 1:
        raise ValueError(f"{item['id']}: confidence out of range")
    if kind == "W":
        listed_match = re.search(r"\*\*따질 만한 것 여섯\*\* — ([^\n]+)", local)
        listed = [value.strip() for value in listed_match.group(1).split("·")]
        if len(item["weights"]) != 3 or len(set(item["weights"])) != 3 or not set(item["weights"]) <= set(listed):
            raise ValueError(f"{item['id']}: invalid weights")
        if set(item["evidence"]) != set(item["weights"]) or not all(quote in local for quote in item["evidence"].values()):
            raise ValueError(f"{item['id']}: invalid weight evidence")
        allowed = {"안 나옴", "이름만", "기각", "감수"}
        if item["unchosen_handling"] not in allowed:
            raise ValueError(f"{item['id']}: invalid unchosen_handling")
        if (item["unchosen_evidence"] is None) != (item["unchosen_handling"] == "안 나옴"):
            raise ValueError(f"{item['id']}: invalid unchosen evidence null rule")
        if item["unchosen_evidence"] is not None and item["unchosen_evidence"] not in local:
            raise ValueError(f"{item['id']}: unchosen evidence not local")
    elif kind == "R":
        notebook = local.split("[수첩]", 1)[1].split("[사실]", 1)[0]
        if [fact["fact_no"] for fact in item["facts"]] != list(range(1, 13)):
            raise ValueError(f"{item['id']}: fact coordinates invalid")
        for fact in item["facts"]:
            if not 0 <= fact["confidence"] <= 1:
                raise ValueError(f"{item['id']} fact {fact['fact_no']}: confidence out of range")
            if fact["retained"] != (fact["quote"] is not None):
                raise ValueError(f"{item['id']} fact {fact['fact_no']}: quote/null rule")
            if fact["quote"] is not None and fact["quote"] not in notebook:
                raise ValueError(f"{item['id']} fact {fact['fact_no']}: quote not in notebook")
    else:
        option_match = re.search(r"선택지:\s*([^/\n]+)\s*/\s*([^\)\n]+)", local)
        options = [value.strip() for value in option_match.groups()]
        rounds = item["round_options"]
        if set(rounds) != {"r0", "r1", "r2", "r3"} or not all(value in options + ["모르겠다"] for value in rounds.values()):
            raise ValueError(f"{item['id']}: invalid round options")
        relation = "모르겠다" if "모르겠다" in (rounds["r0"], rounds["r3"]) else ("유지" if rounds["r0"] == rounds["r3"] else "바뀜")
        if item["conclusion_relation"] != relation:
            raise ValueError(f"{item['id']}: conclusion relation mismatch")
        if relation == "바뀜":
            first = next(name for name in ("r1", "r2", "r3") if rounds[name] != rounds["r0"])
            if item["first_flip"] != first or item["change_type"] not in {"설득", "오락가락", "모르겠다"}:
                raise ValueError(f"{item['id']}: flip fields invalid")
        elif item["first_flip"] is not None or item["change_type"] is not None:
            raise ValueError(f"{item['id']}: non-change fields must be null")
        round_parts = {
            name: text for name, text in re.findall(r"\[(r[0-3])\]\s*(.*?)(?=\n\s*\[r[0-3]\]|\n\s*\[최종 선택\])", local, re.DOTALL)
        }
        if "r0" not in item["evidence"] or len(item["evidence"]) < 2:
            raise ValueError(f"{item['id']}: insufficient evidence rounds")
        for round_name, quote in item["evidence"].items():
            if round_name not in round_parts or quote not in round_parts[round_name]:
                raise ValueError(f"{item['id']} {round_name}: evidence not round-local")


def validate_pack(kind: str, expected_disagreements: int) -> None:
    source_path = ROOT / f"PACK_{kind}_{'weight' if kind == 'W' else 'retain' if kind == 'R' else 'flip'}_2026-09-01.md"
    source = source_path.read_text(encoding="utf-8")
    sections = source_sections(kind, source)
    expected_ids = [f"{kind}-{number:02d}" for number in range(1, 61)]
    consensus_path = HERE / f"PACK_{kind}_CONSENSUS_01.json"
    consensus = load(consensus_path)
    if [item["id"] for item in consensus["items"]] != expected_ids or consensus["source_sha256"] != digest(source_path):
        raise ValueError(f"PACK_{kind}: consensus IDs/source hash invalid")
    for item in consensus["items"]:
        validate_item(kind, item, sections[item["id"]])

    disagreements_path = HERE / f"PACK_{kind}_DISAGREEMENTS.json"
    adjudication_path = HERE / f"PACK_{kind}_ADJUDICATION.json"
    disagreements = load(disagreements_path)
    adjudication = load(adjudication_path)
    if disagreements["n_disagreements"] != expected_disagreements or len(adjudication["resolutions"]) != expected_disagreements:
        raise ValueError(f"PACK_{kind}: disagreement/adjudication count invalid")
    if adjudication["source_disagreements_sha256"] != digest(disagreements_path) or adjudication["key_access"] is not False:
        raise ValueError(f"PACK_{kind}: adjudication binding/blinding invalid")

    freeze_path = HERE / f"PACK_{kind}_FREEZE.json"
    freeze = load(freeze_path)
    if freeze["key_opened"] is not False:
        raise ValueError(f"PACK_{kind}: pre-key freeze declaration invalid")
    for name, expected_hash in freeze["files"].items():
        candidates = [HERE / name, ROOT / name]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is None or digest(path) != expected_hash:
            raise ValueError(f"PACK_{kind}: freeze hash mismatch for {name}")

    keyed_path = HERE / f"PACK_{kind}_KEYED_01.json"
    keyed = load(keyed_path)
    key_path = ROOT / f"_KEY_{kind}_2026-09-01.json"
    key = load(key_path)
    key_items = {item["item"]: item for item in key["items"]}
    consensus_items = {item["id"]: item for item in consensus["items"]}
    if keyed["consensus_sha256"] != digest(consensus_path) or keyed["key_sha256"] != digest(key_path):
        raise ValueError(f"PACK_{kind}: keyed hash binding invalid")
    if [row["id"] for row in keyed["items"]] != expected_ids:
        raise ValueError(f"PACK_{kind}: keyed IDs invalid")
    for row in keyed["items"]:
        if row["coding"] != consensus_items[row["id"]] or row["key"] != key_items[row["id"]]:
            raise ValueError(f"PACK_{kind}: keyed content mismatch {row['id']}")


def main() -> int:
    for kind, count in {"W": 50, "R": 39, "F": 6}.items():
        validate_pack(kind, count)

    spec = importlib.util.spec_from_file_location("key_join", HERE / "key_join.py")
    key_join = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(key_join)
    summary = load(HERE / "KEYED_SUMMARY.json")
    keyed_w, keyed_r, keyed_f = (load(HERE / f"PACK_{kind}_KEYED_01.json") for kind in "WRF")
    key_r = load(ROOT / "_KEY_R_2026-09-01.json")
    recomputed = {
        "W": key_join.summarize_w(keyed_w),
        "R": key_join.summarize_r(keyed_r, key_r),
        "F": key_join.summarize_f(keyed_f),
    }
    if summary["packs"] != recomputed:
        raise ValueError("KEYED_SUMMARY metrics do not recompute")
    if summary["analysis_status"] != {
        "PACK_W": "preregistered_with_disclosed_prior_exposure_for_W1_W2",
        "PACK_R": "post_hoc_exploratory",
        "PACK_F": "post_hoc_exploratory",
    }:
        raise ValueError("analysis status mismatch")

    prereg = (ROOT.parent / "PREREG_packW_2026-09-01.md").read_text(encoding="utf-8")
    required_prereg_results = ("W1 적중", "W2 적중", "W3 적중", "W4 적중", "W5 기각", "2.683/3", "52/60", "1.065")
    if not all(value in prereg for value in required_prereg_results):
        raise ValueError("PACK_W prereg result appendix incomplete")
    report = (HERE / "FINAL_REPORT.md").read_text(encoding="utf-8")
    if not all(value in report for value in ("W1 **적중**", "W5 **기각**", "483건", "바뀜: **11/60**")):
        raise ValueError("final report does not reflect keyed summary")

    manifest = load(HERE / "FREEZE_MANIFEST.json")
    if manifest["status"] != "complete" or manifest["key_join_policy"]["all_packs_frozen_before_key_open"] is not True:
        raise ValueError("final manifest status/policy invalid")
    for name, expected_hash in manifest["sha256"].items():
        if digest(HERE / name) != expected_hash:
            raise ValueError(f"final manifest hash mismatch: {name}")
    if list(HERE.glob("*.tmp")) or list(HERE.glob(".*.tmp")):
        raise ValueError("temporary files remain")
    print("CODERPACK_AB_VALIDATE_OK W=60 R=60x12 F=60 disagreements=50/39/6 hashes=all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
