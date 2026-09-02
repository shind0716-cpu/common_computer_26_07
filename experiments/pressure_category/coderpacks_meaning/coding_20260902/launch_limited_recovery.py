from __future__ import annotations
import hashlib,json,os,shutil,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import claude_adapter,launch,sol_adapter
LEDGER=HERE/'CALL_LEDGER.json'
RUNS=[('A_CLAUDE_MEANING_PREFIX_03',claude_adapter(),HERE/'PROMPT_CLAUDE_PREFIX.txt',HERE/'PACK_M_PREFIX_M001_M014.md'),('B_SOL_MEANING_02_QUOTE_FIX',sol_adapter(),HERE/'PROMPT_SOL_QUOTE_FIX.txt',HERE/'PACK_M_ITEM_M080.md')]
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def now()->str:return datetime.now(timezone.utc).isoformat()
def main()->None:
 if any((HERE/f'{c}_RAW.json').exists() or (HERE/f'{c}_LAUNCH_RECEIPT.json').exists() for c,_,_,_ in RUNS):raise RuntimeError('refusing overwrite')
 ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
 if ledger.get('cap')!=4 or len(ledger.get('entries',[]))!=4:raise RuntimeError('unexpected prior ledger')
 prior=ledger.get('cap_revisions',[]);old=ledger.pop('cap_revision',None)
 if old:prior.append(old)
 prior.append({'from':4,'to':6,'reason':'timeout-fallback best-judgement: Claude missing-prefix supplement plus Sol two-quote correction','approved_replacements':2,'at':now()});ledger['cap_revisions']=prior;ledger['cap']=6;atomic(LEDGER,ledger)
 base=Path(tempfile.mkdtemp(prefix='coder-meaning-recovery-20260902-'));results=[];errors=[]
 for cid,adapter,prompt,source in RUNS:
  if len(ledger['entries'])>=ledger['cap']:raise RuntimeError('call cap exhausted')
  bundle=base/cid;bundle.mkdir();pd=bundle/source.name;pt=bundle/'prompt.txt';shutil.copyfile(source,pd);shutil.copyfile(prompt,pt)
  atomic(bundle/'BUNDLE_MANIFEST.json',{'coder_id':cid,'files':{pd.name:sha(pd),pt.name:sha(pt)}})
  e={'coder_id':cid,'status':'RESERVED','reserved_at':now(),'bundle':str(bundle),'source_path':source.name,'source_sha256':sha(pd),'prompt_sha256':sha(pt)};ledger['entries'].append(e);atomic(LEDGER,ledger)
  try:
   r=launch(adapter,pd,pt,HERE/f'{cid}_RAW.json',HERE/f'{cid}_LAUNCH_RECEIPT.json');e.update(status='RAW_COMPLETE',completed_at=now(),family=r['provider_resolved_identity']['family'],output_sha256=sha(HERE/f'{cid}_RAW.json'));results.append(r)
  except Exception as x:e.update(status='FAILED',completed_at=now(),error=f'{type(x).__name__}: {x}');errors.append({'coder_id':cid,'error':e['error']})
  atomic(LEDGER,ledger)
 state={'status':'RECOVERY_RAW_COMPLETE' if not errors else 'HARD_STOP','transport_cap':6,'attempted_launches':len(ledger['entries']),'recovery_launches':2,'bundle_root':str(base),'families':[r['provider_resolved_identity']['family'] for r in results],'outputs':{e['coder_id']:e.get('output_sha256') for e in ledger['entries'] if e['status']=='RAW_COMPLETE'},'errors':errors};atomic(HERE/'RECOVERY_RUN_STATE.json',state);print(json.dumps(state,ensure_ascii=False))
 if errors:raise SystemExit(1)
 if len(set(state['families']))!=2:raise RuntimeError(f"distinct-family gate: {state['families']}")
if __name__=='__main__':main()
