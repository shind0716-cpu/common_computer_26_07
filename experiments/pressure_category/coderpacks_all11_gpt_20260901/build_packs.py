#!/usr/bin/env python
"""Build deterministic blind packs exclusively from pinned Git blobs."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from typing import Any, Callable

COMMIT = "64ab4017ae76aa79d1ecc86cba994288085ffcc5"
SEED = "20260901"
RUNPLAN = "experiments/pressure_category/ALL11_GPT_RUNPLAN_2026-09-01.json"
RECEIPT = "experiments/pressure_category/ALL11_GPT_RUN_RECEIPT_2026-09-01.json"
ALL11 = "experiments/pressure_category/ALL11_MANIFEST_2026-09-01.json"
EXPECTED_CLOSURE = "b3551db787ff655816abe8c8d26c6cbb5c6612ffa1b7a331c9c86a7eccb82982"
PACK_FILES = {"PACK_A":"PACK_A_final.md","PACK_B":"PACK_B_factcheck.md","PACK_C":"PACK_C_trajectory.md"}

def _repo_root() -> Path: return Path(__file__).resolve().parents[3]
def git_blob(path: str, *, repo: Path | None=None) -> bytes:
    p=subprocess.run(["git","-C",str(repo or _repo_root()),"show",f"{COMMIT}:{path}"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: raise RuntimeError(p.stderr.decode("utf-8",errors="replace"))
    return p.stdout
def _json_blob(path: str, *, repo: Path|None=None) -> dict[str,Any]: return json.loads(git_blob(path,repo=repo).decode("utf-8"))
def _sha(raw: bytes)->str: return hashlib.sha256(raw).hexdigest()
def _canonical(value:Any)->bytes: return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()

def _expected_coordinates(repo:Path, blob_reader:Callable=git_blob)->list[dict[str,Any]]:
    plan=json.loads(blob_reader(RUNPLAN,repo=repo).decode("utf-8")); rows=[]; seen=set()
    if plan.get("totals",{}).get("runs") != 33: raise ValueError("run-plan count mismatch")
    for batch in plan["batches"]:
        for entry in batch["items"]:
            for rep in plan["condition"]["reps"]:
                issue,vset=entry["issue_id"],entry["vset_id"]
                key=(issue,vset,rep)
                if key in seen: raise ValueError("duplicate coordinate")
                seen.add(key)
                path=f"experiments/pressure_category/runs/gpt/{issue}/run_C0_{vset}_rep{rep}.json"
                raw=blob_reader(path,repo=repo); run=json.loads(raw.decode("utf-8"))
                if (run.get("issue_id"),run.get("value_set"),run.get("rep"),run.get("script")) != (issue,vset,rep,"C0"):
                    raise ValueError(f"source identity mismatch: {path}")
                rows.append({"issue_id":issue,"vset_id":vset,"rep":rep,"run_path":path,"source_blob_sha256":_sha(raw)})
    if len(rows)!=33: raise ValueError(f"expected 33 coordinates, got {len(rows)}")
    return rows

def collect_source_artifacts(repo:Path, *, artifact_paths:list[str]|None=None, blob_reader:Callable=git_blob)->dict[str,Any]:
    """Recompute the documented LF-normalized 66-artifact closure."""
    coordinates=_expected_coordinates(repo,blob_reader)
    expected=[]
    for row in coordinates:
        expected.extend([row["run_path"],row["run_path"].removesuffix(".json")+".partial.jsonl"])
    candidate=expected if artifact_paths is None else artifact_paths
    if len(candidate)!=66 or len(set(candidate))!=66 or set(candidate)!=set(expected):
        raise ValueError("artifact path set must be exact: 33 results + 33 checkpoints")
    receipt=json.loads(blob_reader(RECEIPT,repo=repo).decode("utf-8")); plan=json.loads(blob_reader(RUNPLAN,repo=repo).decode("utf-8"))
    pairs={(e["issue_id"],e["vset_id"]) for b in plan["batches"] for e in b["items"]}
    receipt_pairs={(e["issue_id"],e["vset_id"]) for e in receipt["items"]}
    if receipt.get("runplan")!=Path(RUNPLAN).name or pairs!=receipt_pairs: raise ValueError("receipt/run-plan identity mismatch")
    if tuple(receipt.get(k) for k in ("runs","result_files","checkpoint_files","artifact_files"))!=(33,33,33,66): raise ValueError("receipt artifact counts mismatch")
    closure=hashlib.sha256(); hashes={}; checkpoint_rows=0
    for path in sorted(candidate):
        raw=blob_reader(path,repo=repo); normalized=raw.replace(b"\r\n",b"\n").replace(b"\r",b"\n")
        digest=hashlib.sha256(normalized).digest(); closure.update(path.encode()+b"\0"+digest); hashes[path]=digest.hex()
        if path.endswith(".partial.jsonl"):
            rows=[json.loads(line) for line in normalized.decode("utf-8").splitlines() if line]
            checkpoint_rows+=len(rows)
            if len({row.get("tag") for row in rows})!=len(rows): raise ValueError(f"duplicate checkpoint tag: {path}")
    computed=closure.hexdigest()
    if computed!=EXPECTED_CLOSURE or computed!=receipt.get("artifact_closure_sha256"): raise ValueError(f"closure mismatch: {computed}")
    if checkpoint_rows!=receipt.get("checkpoint_rows"): raise ValueError("checkpoint row count mismatch")
    return {"coordinates":coordinates,"artifact_paths":expected,"artifact_hashes":hashes,"closure_sha256":computed}

def _ordered(pack:str,rows:list[dict[str,Any]])->list[dict[str,Any]]:
    return sorted(rows,key=lambda r:hashlib.sha256(f"{SEED}|{pack}|{r['issue_id']}|{r['vset_id']}|{r['rep']}".encode()).hexdigest())
def _pack_items(pack:str, coordinates:list[dict[str,Any]], materials:dict[str,dict[str,Any]], repo:Path):
    public=[]; keys=[]
    for number,row in enumerate(_ordered(pack,coordinates),1):
        blind=f"{pack[-1]}-{number:02d}"; run=_json_blob(row["run_path"],repo=repo); material=materials[row["issue_id"]]
        if pack=="PACK_A": item={"id":blind,"final_text":run["essays"][3],"final_poll":run["final_poll"]}
        elif pack=="PACK_B": item={"id":blind,"last_notes":run["notes"][2],"facts":[{"fact_no":n,"text":f["text"]} for n,f in enumerate(material["facts"],1)]}
        else: item={"id":blind,"round_texts":{f"r{i}":run["essays"][i] for i in range(4)},"options":material["options"]}
        public.append(item); keys.append({"id":blind,**row,"material_file":material["_source_path"],"material_blob_sha256":material["_blob_sha256"]})
    return public,keys
def _render(pack:str,items:list[dict[str,Any]])->bytes:
    title={"PACK_A":"Final text blind coding","PACK_B":"Last-notes fact retention","PACK_C":"Descriptive option trajectory"}[pack]
    payload=json.dumps({"pack":pack,"items":items},ensure_ascii=False,indent=2)
    return (f"# {pack} — {title}\n\nPost-hoc exploratory blind source pack. Code under CODING_PROTOCOL.md.\n\n<!-- PACK_PAYLOAD_BEGIN -->\n```json\n{payload}\n```\n<!-- PACK_PAYLOAD_END -->\n").encode()
def parse_pack_bytes(raw:bytes)->dict[str,Any]:
    text=raw.decode(); start=text.index("<!-- PACK_PAYLOAD_BEGIN -->"); fenced=text.index("```json",start)+7; end=text.index("```",fenced); return json.loads(text[fenced:end])

def build(output_dir:Path, *, repo:Path|None=None, key_output_dir:Path|None=None)->dict[str,Any]:
    root=(repo or _repo_root()).resolve(); output_dir.mkdir(parents=True,exist_ok=True)
    if key_output_dir is None:
        raise ValueError("key_output_dir is required and must be outside repository")
    private=key_output_dir.resolve()
    if private == root or root in private.parents:
        raise ValueError("key_output_dir must be outside repository")
    all11_raw=git_blob(ALL11,repo=root); all11=json.loads(all11_raw.decode()); materials={}; material_hashes={}
    for entry in all11["entries"]:
        path="experiments/pressure_category/"+entry["material_file"]; raw=git_blob(path,repo=root); material=json.loads(raw.decode())
        material["_source_path"]=path; material["_blob_sha256"]=_sha(raw); materials[entry["issue_id"]]=material; material_hashes[path]=_sha(raw)
    source=collect_source_artifacts(root); coordinates=source["coordinates"]; packs={}; key_packs={}; pack_hashes={}
    for pack,filename in PACK_FILES.items():
        items,key_rows=_pack_items(pack,coordinates,materials,root); raw=_render(pack,items); (output_dir/filename).write_bytes(raw)
        packs[filename]=items; key_packs[pack]=key_rows; pack_hashes[filename]=_sha(raw)
    receipt_raw=git_blob(RECEIPT,repo=root)
    source_core={"schema":"all11_gpt_source_manifest_v2","source_commit":COMMIT,"seed":SEED,"sort_key":"sha256(20260901|PACK_X|issue_id|vset_id|rep)","runplan":{"path":RUNPLAN,"sha256":_sha(git_blob(RUNPLAN,repo=root))},"receipt":{"path":RECEIPT,"sha256":_sha(receipt_raw)},"run_closure_sha256":source["closure_sha256"],"run_artifact_paths":source["artifact_paths"],"run_artifact_lf_sha256":source["artifact_hashes"],"all11_manifest":{"path":ALL11,"sha256":_sha(all11_raw)},"material_blobs":material_hashes,"coordinates":coordinates,"pack_sha256":pack_hashes,"private_reconstruction":{"fact_count":sum(len(materials[r["issue_id"]]["facts"]) for r in coordinates),"fact_texts_sha256":_sha(_canonical([[f["text"] for f in materials[r["issue_id"]]["facts"]] for r in coordinates]))}}
    payload_hash=_sha(_canonical(source_core)); key={"schema":"all11_gpt_blind_key_v2","source_commit":COMMIT,"source_manifest_payload_sha256":payload_hash,"packs":key_packs}
    key_raw=_canonical(key); private.mkdir(parents=True,exist_ok=True); key_path=private/"_KEY_all11_gpt.json"; key_path.write_bytes(key_raw)
    try: key_path.chmod(0o600)
    except OSError: pass
    manifest={**source_core,"integrity":{"manifest_payload_sha256":payload_hash,"key_sha256":_sha(key_raw)}}; (output_dir/"SOURCE_MANIFEST.json").write_bytes(_canonical(manifest))
    return {"packs":packs,"manifest":manifest,"pack_hashes":pack_hashes,"key_path":str(key_path)}
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parent); p.add_argument("--key-output-dir",type=Path,required=True); a=p.parse_args(); result=build(a.output_dir,key_output_dir=a.key_output_dir); print(f"WROTE deterministic A/B/C packs: {sum(len(v) for v in result['packs'].values())} items"); return 0
if __name__=="__main__": raise SystemExit(main())
