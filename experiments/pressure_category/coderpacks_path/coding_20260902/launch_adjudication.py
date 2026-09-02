from __future__ import annotations
import argparse,hashlib,json,os,shutil,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import claude_adapter,launch
import validate_adjudication as V
PACK=HERE/'PACK_P_DISAGREEMENTS.json';PROMPT=HERE/'PROMPT_ADJUDICATION.txt';SCHEMA=HERE/'adjudication_output.schema.json';EXPECTED='c4747effd04fb988e21616c6aa9c77e27be1411ef9ae76bfc0f2d82f710a44da'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def now()->str:return datetime.now(timezone.utc).isoformat()
def preflight()->dict:
 if sha(PACK)!=EXPECTED:raise RuntimeError('disagreement drift')
 dis=json.loads(PACK.read_text(encoding='utf-8'))
 if [x['id'] for x in dis['disagreements']]!=['P-15']:raise RuntimeError('coordinate drift')
 if any((HERE/n).exists() for n in ('ADJUDICATION_LEDGER.json','ADJUDICATION_RAW.json','ADJUDICATION_LAUNCH_RECEIPT.json','ADJUDICATION_RUN_STATE.json')):raise RuntimeError('refusing overwrite')
 return {'status':'DRY_RUN_OK','external_calls':0,'cap':1,'coordinates':['P-15'],'source_sha256':sha(PACK)}
def main()->None:
 ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');a=ap.parse_args();pf=preflight()
 if a.dry_run:print(json.dumps(pf));return
 ledger={'schema':'pack_p_adjudication_ledger_v1','cap':1,'entries':[]};atomic(HERE/'ADJUDICATION_LEDGER.json',ledger);base=Path(tempfile.mkdtemp(prefix='coder-path-adj-20260902-'));bundle=base/'CLAUDE_ADJ_PATH_01';bundle.mkdir()
 pd=bundle/PACK.name;pt=bundle/'prompt.txt';sd=bundle/SCHEMA.name
 for src,dst in ((PACK,pd),(PROMPT,pt),(SCHEMA,sd)):shutil.copyfile(src,dst)
 atomic(bundle/'BUNDLE_MANIFEST.json',{'adjudicator_id':'CLAUDE_ADJ_PATH_01','key_access':False,'files':{p.name:sha(p) for p in (pd,pt,sd)}})
 e={'adjudicator_id':'CLAUDE_ADJ_PATH_01','status':'RESERVED','reserved_at':now(),'bundle':str(bundle),'source_sha256':sha(pd),'prompt_sha256':sha(pt),'schema_sha256':sha(sd)};ledger['entries'].append(e);atomic(HERE/'ADJUDICATION_LEDGER.json',ledger)
 errors=[]
 try:
  receipt=launch(claude_adapter(),pd,pt,HERE/'ADJUDICATION_RAW.json',HERE/'ADJUDICATION_LAUNCH_RECEIPT.json');o=json.loads((HERE/'ADJUDICATION_RAW.json').read_text(encoding='utf-8'));V.validate(o,json.loads(PACK.read_text(encoding='utf-8')),sha(PACK),'CLAUDE_ADJ_PATH_01');e.update(status='ACCEPTED',completed_at=now(),family=receipt['provider_resolved_identity']['family'],model=receipt['provider_resolved_identity']['model'],output_sha256=sha(HERE/'ADJUDICATION_RAW.json'))
 except Exception as exc:e.update(status='FAILED_OR_REJECTED',completed_at=now(),error=f'{type(exc).__name__}: {exc}');errors.append(e['error'])
 atomic(HERE/'ADJUDICATION_LEDGER.json',ledger);state={'status':'ADJUDICATION_ACCEPTED' if not errors else 'HARD_STOP','cap':1,'attempted':1,'accepted':0 if errors else 1,'bundle_root':str(base),'output_sha256':e.get('output_sha256'),'errors':errors};atomic(HERE/'ADJUDICATION_RUN_STATE.json',state);print(json.dumps(state,ensure_ascii=False))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
