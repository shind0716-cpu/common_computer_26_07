from __future__ import annotations
import hashlib,json,os,shutil,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import launch,sol_adapter
PACK=HERE/'ADJUDICATION_NULL_FIX_PACK.md';PROMPT=HERE/'PROMPT_ADJ_NULL_FIX.txt';LEDGER=HERE/'ADJUDICATION_CORRECTION_CALL_LEDGER.json';CID='SOL_ADJ_NULL_FIX_01'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main()->None:
 if LEDGER.exists() or (HERE/f'{CID}_RAW.json').exists():raise RuntimeError('refusing retry/overwrite')
 base=Path(tempfile.mkdtemp(prefix='coder-meaning-adj-fix-20260902-'));bundle=base/CID;bundle.mkdir();pd=bundle/PACK.name;pt=bundle/'prompt.txt';shutil.copyfile(PACK,pd);shutil.copyfile(PROMPT,pt);atomic(bundle/'BUNDLE_MANIFEST.json',{'coder_id':CID,'files':{pd.name:sha(pd),pt.name:sha(pt)}})
 ledger={'schema':'pack_m_adjudication_correction_ledger_v1','cap':1,'entries':[{'corrector_id':CID,'status':'RESERVED','reserved_at':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(pd),'prompt_sha256':sha(pt)}]};atomic(LEDGER,ledger);e=ledger['entries'][0]
 try:
  r=launch(sol_adapter(),pd,pt,HERE/f'{CID}_RAW.json',HERE/f'{CID}_RECEIPT.json');e.update(status='RAW_COMPLETE',completed_at=datetime.now(timezone.utc).isoformat(),family=r['provider_resolved_identity']['family'],output_sha256=sha(HERE/f'{CID}_RAW.json'));status='RAW_COMPLETE'
 except Exception as x:e.update(status='FAILED',completed_at=datetime.now(timezone.utc).isoformat(),error=f'{type(x).__name__}: {x}');status='HARD_STOP'
 atomic(LEDGER,ledger);state={'status':status,'cap':1,'attempted_launches':1,'entry':e};atomic(HERE/'ADJUDICATION_CORRECTION_RUN_STATE.json',state);print(json.dumps(state,ensure_ascii=False))
 if status!='RAW_COMPLETE':raise SystemExit(1)
if __name__=='__main__':main()
