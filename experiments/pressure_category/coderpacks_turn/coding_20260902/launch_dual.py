from __future__ import annotations
import concurrent.futures,hashlib,json,shutil,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import claude_adapter,launch,sol_adapter
PACK=HERE.parent/'PACK_T_turn_2026-09-02.md'
RUNS=[('A_CLAUDE_TURN_01',claude_adapter(),HERE/'PROMPT_CLAUDE.txt'),('B_SOL_TURN_01',sol_adapter(),HERE/'PROMPT_SOL.txt')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def one(cid,adapter,prompt,bundle):
 pd=bundle/PACK.name;pt=bundle/'prompt.txt';shutil.copyfile(PACK,pd);shutil.copyfile(prompt,pt)
 (bundle/'BUNDLE_MANIFEST.json').write_text(json.dumps({'coder_id':cid,'files':{pd.name:sha(pd),pt.name:sha(pt)}},sort_keys=True,indent=2)+'\n',encoding='utf-8')
 return launch(adapter,pd,pt,HERE/f'{cid}_RAW.json',HERE/f'{cid}_LAUNCH_RECEIPT.json')
def main():
 if any((HERE/f'{c}_RAW.json').exists() for c,_,_ in RUNS):raise RuntimeError('refusing overwrite')
 base=Path(tempfile.mkdtemp(prefix='coder-turn-20260902-'));bundles=[]
 for cid,_,_ in RUNS:p=base/cid;p.mkdir();bundles.append(p)
 (HERE/'RUN_STATE.json').write_text(json.dumps({'status':'LAUNCHED','planned_launches':2,'bundle_root':str(base),'pack_sha256':sha(PACK)},indent=2)+'\n',encoding='utf-8')
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:rs=[f.result() for f in [ex.submit(one,*spec,b) for spec,b in zip(RUNS,bundles)]]
 fam=[r['provider_resolved_identity']['family'] for r in rs]
 if len(set(fam))!=2:raise RuntimeError(f'distinct-family gate: {fam}')
 state={'status':'RAW_COMPLETE','planned_launches':2,'attempted_launches':2,'bundle_root':str(base),'pack_sha256':sha(PACK),'families':fam,'outputs':{c:sha(HERE/f'{c}_RAW.json') for c,_,_ in RUNS}}
 (HERE/'RUN_STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(state,ensure_ascii=False))
if __name__=='__main__':main()
