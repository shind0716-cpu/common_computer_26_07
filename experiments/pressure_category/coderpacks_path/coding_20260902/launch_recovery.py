from __future__ import annotations
import hashlib,json,os,shutil,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import claude_adapter,launch,sol_adapter
import validate_recovery as R
FULL=HERE.parent/'PACK_P_path_2026-09-02.md'
RUNS=[
 ('A_CLAUDE_PATH_RECOVERY_02',claude_adapter(),HERE/'PACK_P_PREFIX_P01_P21.md',HERE/'PROMPT_CLAUDE_RECOVERY_02.txt',HERE/'recovery_output.schema.json',[f'P-{i:02d}' for i in range(1,22)]),
 ('A_CLAUDE_PATH_RECOVERY_03',claude_adapter(),HERE/'PACK_P_PREFIX_P22_P42.md',HERE/'PROMPT_CLAUDE_RECOVERY_03.txt',HERE/'recovery_output.schema.json',[f'P-{i:02d}' for i in range(22,43)]),
 ('B_SOL_PATH_QUOTE_FIX_02',sol_adapter(),FULL,HERE/'PROMPT_SOL_QUOTE_FIX.txt',HERE/'quote_fix.schema.json',None),
]
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def now()->str:return datetime.now(timezone.utc).isoformat()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main()->None:
 lp=HERE/'CALL_LEDGER.json';ledger=json.loads(lp.read_text(encoding='utf-8'))
 if ledger.get('cap')!=2 or len(ledger.get('entries',[]))!=2:raise RuntimeError('unexpected pre-expansion ledger')
 if any((HERE/f'{cid}_RAW.json').exists() or (HERE/f'{cid}_LAUNCH_RECEIPT.json').exists() for cid,*_ in RUNS):raise RuntimeError('refusing overwrite')
 if sha(FULL)!='a91725d6cfc537d052e5c0a21dae3d604d25052dcf265ee85f7228b6cac04c61':raise RuntimeError('full pack drift')
 expected={'PACK_P_PREFIX_P01_P21.md':'135d1892187c681db5aed3e850bbe00aec30f250ab9278c77b641f281bba1797','PACK_P_PREFIX_P22_P42.md':'74fec2785a82df585c78ba750d2c9626b33c672f371ac0ee983b5d48a6e37454'}
 for n,h in expected.items():
  if sha(HERE/n)!=h:raise RuntimeError(f'{n} drift')
 ledger['cap']=5;ledger.setdefault('approved_expansions',[]).append({'approved_at':now(),'old_cap':2,'new_cap':5,'scope':'Claude P-01..P-21 + Claude P-22..P-42 + Sol P-45 round-1 quote only'});atomic(lp,ledger)
 base=Path(tempfile.mkdtemp(prefix='coder-path-recovery-20260902-'));errors=[]
 for cid,adapter,pack,prompt,schema,ids in RUNS:
  if len(ledger['entries'])>=ledger['cap']:raise RuntimeError('transport cap exhausted')
  bundle=base/cid;bundle.mkdir();pd=bundle/pack.name;pt=bundle/'prompt.txt';sd=bundle/schema.name
  for src,dst in ((pack,pd),(prompt,pt),(schema,sd)):shutil.copyfile(src,dst)
  atomic(bundle/'BUNDLE_MANIFEST.json',{'coder_id':cid,'key_access':False,'files':{p.name:sha(p) for p in (pd,pt,sd)}})
  e={'coder_id':cid,'status':'RESERVED','reserved_at':now(),'bundle':str(bundle),'pack_sha256':sha(pd),'prompt_sha256':sha(pt),'schema_sha256':sha(sd)};ledger['entries'].append(e);atomic(lp,ledger)
  try:
   receipt=launch(adapter,pd,pt,HERE/f'{cid}_RAW.json',HERE/f'{cid}_LAUNCH_RECEIPT.json');raw=HERE/f'{cid}_RAW.json';o=json.loads(raw.read_text(encoding='utf-8'))
   if ids:R.validate_subset(o,ids,pack.name,sha(pack),cid)
   else:R.validate_sol_fix_shape(o,cid)
   e.update(status='ACCEPTED',completed_at=now(),family=receipt['provider_resolved_identity']['family'],model=receipt['provider_resolved_identity']['model'],output_sha256=sha(raw))
  except Exception as exc:
   e.update(status='FAILED_OR_REJECTED',completed_at=now(),error=f'{type(exc).__name__}: {exc}');errors.append({'coder_id':cid,'error':e['error']})
   if (HERE/f'{cid}_RAW.json').exists():e['output_sha256']=sha(HERE/f'{cid}_RAW.json')
  atomic(lp,ledger)
 state={'status':'RECOVERY_RAW_ACCEPTED' if not errors else 'HARD_STOP','transport_cap':ledger['cap'],'attempted_launches':len(ledger['entries']),'recovery_launches':3,'accepted_recovery':sum(e['status']=='ACCEPTED' for e in ledger['entries'][2:]),'bundle_root':str(base),'outputs':{e['coder_id']:e.get('output_sha256') for e in ledger['entries'][2:]},'errors':errors};atomic(HERE/'RECOVERY_RUN_STATE.json',state);print(json.dumps(state,ensure_ascii=False))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
