from __future__ import annotations
import hashlib,json,os,shutil,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import claude_adapter,launch,sol_adapter
PACK=HERE.parent/'PACK_M_meaning_2026-09-02.md';SCHEMA=HERE/'coding_output_v2.schema.json';LEDGER=HERE/'CALL_LEDGER.json'
RUNS=[('A_CLAUDE_MEANING_02',claude_adapter(),HERE/'PROMPT_CLAUDE_V2.txt'),('B_SOL_MEANING_02',sol_adapter(),HERE/'PROMPT_SOL_V2.txt')]
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def now()->str:return datetime.now(timezone.utc).isoformat()
def main()->None:
 if sha(PACK)!='dd29b2af54a6886b6d8fe12cfd613c405bc071132bdad91dc28095361e4280b9':raise RuntimeError('pack drift')
 if any((HERE/f'{c}_RAW.json').exists() or (HERE/f'{c}_LAUNCH_RECEIPT.json').exists() for c,_,_ in RUNS):raise RuntimeError('refusing overwrite')
 ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
 if ledger.get('cap')!=2 or len(ledger.get('entries',[]))!=2:raise RuntimeError('unexpected prior ledger')
 ledger['cap']=4;ledger['cap_revision']={'from':2,'to':4,'reason':'user-approved two single-output replacements after reset','approved_replacements':2,'at':now()};atomic(LEDGER,ledger)
 base=Path(tempfile.mkdtemp(prefix='coder-meaning-v2-20260902-'));results=[];errors=[]
 for cid,adapter,prompt in RUNS:
  if len(ledger['entries'])>=ledger['cap']:raise RuntimeError('call cap exhausted')
  bundle=base/cid;bundle.mkdir();pd=bundle/PACK.name;pt=bundle/'prompt.txt';sd=bundle/SCHEMA.name
  for src,dst in [(PACK,pd),(prompt,pt),(SCHEMA,sd)]:shutil.copyfile(src,dst)
  atomic(bundle/'BUNDLE_MANIFEST.json',{'coder_id':cid,'files':{p.name:sha(p) for p in (pd,pt,sd)}})
  e={'coder_id':cid,'status':'RESERVED','replacement_for':cid.replace('_02','_01'),'reserved_at':now(),'bundle':str(bundle),'pack_sha256':sha(pd),'prompt_sha256':sha(pt),'schema_sha256':sha(sd)};ledger['entries'].append(e);atomic(LEDGER,ledger)
  try:
   r=launch(adapter,pd,pt,HERE/f'{cid}_RAW.json',HERE/f'{cid}_LAUNCH_RECEIPT.json');e.update(status='RAW_COMPLETE',completed_at=now(),family=r['provider_resolved_identity']['family'],output_sha256=sha(HERE/f'{cid}_RAW.json'));results.append(r)
  except Exception as x:e.update(status='FAILED',completed_at=now(),error=f'{type(x).__name__}: {x}');errors.append({'coder_id':cid,'error':e['error']})
  atomic(LEDGER,ledger)
 state={'status':'REPLACEMENT_RAW_COMPLETE' if not errors else 'HARD_STOP','transport_cap':4,'attempted_launches':len(ledger['entries']),'replacement_launches':2,'bundle_root':str(base),'pack_sha256':sha(PACK),'families':[r['provider_resolved_identity']['family'] for r in results],'outputs':{e['coder_id']:e.get('output_sha256') for e in ledger['entries'] if e['status']=='RAW_COMPLETE'},'errors':errors};atomic(HERE/'REPLACEMENT_RUN_STATE.json',state);print(json.dumps(state,ensure_ascii=False))
 if errors:raise SystemExit(1)
 if len(set(state['families']))!=2:raise RuntimeError(f"distinct-family gate: {state['families']}")
if __name__=='__main__':main()
