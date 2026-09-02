from __future__ import annotations
import hashlib,json,os,shutil,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import claude_adapter,launch
MAN=HERE/'ADJUDICATION_CHUNKS_MANIFEST.json';TEMPLATE=HERE/'ADJUDICATION_PROMPT_TEMPLATE.txt';LEDGER=HERE/'ADJUDICATION_CALL_LEDGER.json'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def atomic_text(p:Path,s:str)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(s,encoding='utf-8');os.replace(t,p)
def now()->str:return datetime.now(timezone.utc).isoformat()
def main()->None:
 if LEDGER.exists():raise RuntimeError('adjudication ledger exists; refuse retry')
 man=json.loads(MAN.read_text(encoding='utf-8'));base=Path(tempfile.mkdtemp(prefix='coder-meaning-adjudication-20260902-'));ledger={'schema':'pack_m_adjudication_call_ledger_v1','cap':3,'entries':[]};atomic(LEDGER,ledger);results=[];errors=[]
 for meta in man['chunks']:
  n=meta['chunk'];cid=f'CLAUDE_ADJ_M_CHUNK_{n}';source=HERE/meta['path'];out=HERE/f'ADJUDICATION_CHUNK_{n}_RAW.json';receipt=HERE/f'ADJUDICATION_CHUNK_{n}_RECEIPT.json'
  if out.exists() or receipt.exists():raise RuntimeError('refusing overwrite')
  prompt_text=TEMPLATE.read_text(encoding='utf-8').replace('CLAUDE_ADJ_M_CHUNK_N',cid).replace('"chunk":N',f'"chunk":{n}').replace('CHUNK_SHA',meta['sha256']);prompt=HERE/f'ADJUDICATION_PROMPT_{n}.txt';atomic_text(prompt,prompt_text)
  bundle=base/cid;bundle.mkdir();pd=bundle/source.name;pt=bundle/'prompt.txt';shutil.copyfile(source,pd);shutil.copyfile(prompt,pt);atomic(bundle/'BUNDLE_MANIFEST.json',{'coder_id':cid,'files':{pd.name:sha(pd),pt.name:sha(pt)}})
  e={'adjudicator_id':cid,'chunk':n,'status':'RESERVED','reserved_at':now(),'source_sha256':sha(pd),'prompt_sha256':sha(pt)};ledger['entries'].append(e);atomic(LEDGER,ledger)
  try:
   r=launch(claude_adapter(),pd,pt,out,receipt);e.update(status='RAW_COMPLETE',completed_at=now(),family=r['provider_resolved_identity']['family'],output_sha256=sha(out));results.append(r)
  except Exception as x:e.update(status='FAILED',completed_at=now(),error=f'{type(x).__name__}: {x}');errors.append({'chunk':n,'error':e['error']})
  atomic(LEDGER,ledger)
 state={'status':'ADJUDICATION_RAW_COMPLETE' if not errors else 'HARD_STOP','cap':3,'attempted_launches':len(ledger['entries']),'families':[r['provider_resolved_identity']['family'] for r in results],'outputs':{e['adjudicator_id']:e.get('output_sha256') for e in ledger['entries'] if e['status']=='RAW_COMPLETE'},'errors':errors};atomic(HERE/'ADJUDICATION_RUN_STATE.json',state);print(json.dumps(state,ensure_ascii=False))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
