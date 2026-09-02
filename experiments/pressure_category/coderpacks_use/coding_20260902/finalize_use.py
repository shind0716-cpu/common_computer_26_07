from __future__ import annotations

import collections
import json
import os
from pathlib import Path

import validate_use as V

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
PACK=ROOT/'PACK_U_use_2026-09-02.md'; KEY=ROOT/'_KEY_U_2026-09-02.json'
CONS=HERE/'PACK_U_CONSENSUS.json'; FREEZE=HERE/'PACK_U_FREEZE.json'


def atomic(path,obj):
 tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); os.replace(tmp,path)

def main():
 if FREEZE.exists(): raise RuntimeError('refusing to overwrite freeze')
 c=json.loads(CONS.read_text(encoding='utf-8'))
 if c.get('schema')!='pack_u_consensus_v1' or c.get('key_access') is not False or c.get('source_sha256')!=V.digest(PACK): raise ValueError('consensus contract invalid')
 if [x.get('id') for x in c.get('items',[])]!=V.EXPECTED_IDS: raise ValueError('consensus ID closure invalid')
 files=['CODING_PROTOCOL.md','coding_output.schema.json','PROMPT_CLAUDE.txt','PROMPT_SOL.txt',
        'A_CLAUDE_USE_01_RAW.json','B_SOL_USE_01_RAW.json','B_SOL_USE_01_CORRECTED.json',
        'A_CLAUDE_USE_01_LAUNCH_RECEIPT.json','B_SOL_USE_01_LAUNCH_RECEIPT.json',
        'B_SOL_USE_01_CORRECTION_RECEIPT.json','HARD_STOP_STATUS.json',
        'PACK_U_DISAGREEMENTS.json','PACK_U_ADJUDICATION.json','PACK_U_CONSENSUS.json']
 frozen={'schema':'pack_u_freeze_v1','status':'FROZEN_PRE_KEY','analysis_status':'post_hoc_exploratory',
         'key_opened':False,'source_path':PACK.name,'source_sha256':V.digest(PACK),
         'files':{name:V.digest(HERE/name) for name in files}}
 atomic(FREEZE,frozen)
 # Re-open and verify the durable pre-key freeze before first key read.
 check=json.loads(FREEZE.read_text(encoding='utf-8'))
 if check!=frozen or any(V.digest(HERE/name)!=h for name,h in check['files'].items()): raise ValueError('freeze readback failed')
 key=json.loads(KEY.read_text(encoding='utf-8'))
 km={x['item']:x for x in key['items']}
 if set(km)!=set(V.EXPECTED_IDS): raise ValueError('key ID closure invalid')
 rows=[{'id':x['id'],'coding':x,'key':km[x['id']]} for x in c['items']]
 keyed={'schema':'pack_u_keyed_v1','freeze_sha256':V.digest(FREEZE),'consensus_sha256':V.digest(CONS),
        'key_sha256':V.digest(KEY),'items':rows}
 kp=HERE/'PACK_U_KEYED.json'; atomic(kp,keyed)
 counts=collections.Counter(x['coding']['consensus_rebuildability'] for x in rows)
 by_facts={}
 for band in ('0개','1~3개','4개+'):
  sub=[x for x in rows if x['key']['band']==band]
  by_facts[band]={'n':len(sub),'grades':dict(collections.Counter(x['coding']['consensus_rebuildability'] for x in sub))}
 by_model={}
 for model in sorted({x['key']['model'] for x in rows}):
  sub=[x for x in rows if x['key']['model']==model]
  by_model[model]={'n':len(sub),'grades':dict(collections.Counter(x['coding']['consensus_rebuildability'] for x in sub))}
 summary={'schema':'pack_u_keyed_summary_v1','analysis_status':'post_hoc_exploratory','n':len(rows),
          'agreement_n':sum(x['coding']['status']=='agreement' for x in rows),'grades':dict(counts),
          'by_fact_band':by_facts,'by_model':by_model,
          'warning':'AI coder agreement is model-to-model agreement, not human reliability.'}
 sp=HERE/'KEYED_SUMMARY.json'; atomic(sp,summary)
 final={'schema':'pack_u_final_manifest_v1','status':'complete','freeze_sha256':V.digest(FREEZE),
        'key_sha256':V.digest(KEY),'keyed_sha256':V.digest(kp),'summary_sha256':V.digest(sp),
        'all_blind_artifacts_frozen_before_key_open':True}
 atomic(HERE/'FINAL_MANIFEST.json',final)
 print(f"PACK_U_FINALIZED n={len(rows)} agreement={summary['agreement_n']} freeze={V.digest(FREEZE)}")

if __name__=='__main__': main()
