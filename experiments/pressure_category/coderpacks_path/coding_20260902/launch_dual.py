from __future__ import annotations
import argparse,hashlib,json,os,shutil,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import claude_adapter,launch,sol_adapter
import validate_path as V
PACK=HERE.parent/'PACK_P_path_2026-09-02.md';SCHEMA=HERE/'coding_output.schema.json'
EXPECTED_PACK='a91725d6cfc537d052e5c0a21dae3d604d25052dcf265ee85f7228b6cac04c61'
RUNS=[('A_CLAUDE_PATH_01',claude_adapter(),HERE/'PROMPT_CLAUDE.txt'),('B_SOL_PATH_01',sol_adapter(),HERE/'PROMPT_SOL.txt')]
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def now()->str:return datetime.now(timezone.utc).isoformat()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def preflight()->dict:
 if sha(PACK)!=EXPECTED_PACK:raise RuntimeError('pack drift')
 if any((HERE/f'{cid}_RAW.json').exists() or (HERE/f'{cid}_LAUNCH_RECEIPT.json').exists() for cid,_,_ in RUNS):raise RuntimeError('refusing overwrite')
 if (HERE/'CALL_LEDGER.json').exists() or (HERE/'RUN_STATE.json').exists():raise RuntimeError('durable run state exists; refuse implicit retry')
 text=PACK.read_text(encoding='utf-8')
 if list(V.sections(text))!=V.IDS or sum(len(V.round_regions(s)) for s in V.sections(text).values())!=192:raise RuntimeError('pack closure')
 return {'status':'DRY_RUN_OK','external_calls':0,'planned_launches':2,'transport_cap':2,'pack_sha256':sha(PACK),'schema_sha256':sha(SCHEMA),'input_bytes':len(PACK.read_bytes()),'worst_case_output_bytes_estimate':90000}
def main()->None:
 ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');a=ap.parse_args();pf=preflight()
 if a.dry_run:print(json.dumps(pf,ensure_ascii=False));return
 base=Path(tempfile.mkdtemp(prefix='coder-path-20260902-'));ledger={'schema':'pack_p_call_ledger_v1','cap':2,'entries':[]};atomic(HERE/'CALL_LEDGER.json',ledger)
 receipts=[];errors=[]
 for cid,adapter,prompt in RUNS:
  if len(ledger['entries'])>=ledger['cap']:raise RuntimeError('transport call cap exhausted')
  bundle=base/cid;bundle.mkdir();pd=bundle/PACK.name;pt=bundle/'prompt.txt';sd=bundle/SCHEMA.name
  for src,dst in ((PACK,pd),(prompt,pt),(SCHEMA,sd)):shutil.copyfile(src,dst)
  atomic(bundle/'BUNDLE_MANIFEST.json',{'coder_id':cid,'key_access':False,'files':{p.name:sha(p) for p in (pd,pt,sd)}})
  entry={'coder_id':cid,'status':'RESERVED','reserved_at':now(),'bundle':str(bundle),'pack_sha256':sha(pd),'prompt_sha256':sha(pt),'schema_sha256':sha(sd)};ledger['entries'].append(entry);atomic(HERE/'CALL_LEDGER.json',ledger)
  try:
   receipt=launch(adapter,pd,pt,HERE/f'{cid}_RAW.json',HERE/f'{cid}_LAUNCH_RECEIPT.json')
   raw=HERE/f'{cid}_RAW.json';obj=json.loads(raw.read_text(encoding='utf-8'));V.validate(obj,cid)
   entry.update(status='ACCEPTED',completed_at=now(),family=receipt['provider_resolved_identity']['family'],model=receipt['provider_resolved_identity']['model'],output_sha256=sha(raw));receipts.append(receipt)
  except Exception as exc:
   entry.update(status='FAILED_OR_REJECTED',completed_at=now(),error=f'{type(exc).__name__}: {exc}')
   if (HERE/f'{cid}_RAW.json').exists():entry['output_sha256']=sha(HERE/f'{cid}_RAW.json')
   errors.append({'coder_id':cid,'error':entry['error']})
  atomic(HERE/'CALL_LEDGER.json',ledger)
 families=[r['provider_resolved_identity']['family'] for r in receipts]
 if not errors and len(set(families))!=2:errors.append({'gate':'distinct_family','families':families})
 state={'status':'CODER_OUTPUTS_ACCEPTED' if not errors else 'HARD_STOP','planned_launches':2,'attempted_launches':len(ledger['entries']),'accepted_outputs':sum(e['status']=='ACCEPTED' for e in ledger['entries']),'bundle_root':str(base),'pack_sha256':sha(PACK),'families':families,'outputs':{e['coder_id']:e.get('output_sha256') for e in ledger['entries'] if e.get('output_sha256')},'errors':errors};atomic(HERE/'RUN_STATE.json',state);print(json.dumps(state,ensure_ascii=False))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
