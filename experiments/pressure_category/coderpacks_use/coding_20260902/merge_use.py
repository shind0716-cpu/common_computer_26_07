from __future__ import annotations

import json
import os
from pathlib import Path

import validate_use as V

HERE = Path(__file__).resolve().parent
PACK = HERE.parent / "PACK_U_use_2026-09-02.md"
A = HERE / "A_CLAUDE_USE_01_RAW.json"; B = HERE / "B_SOL_USE_01_CORRECTED.json"
DIS = HERE / "PACK_U_DISAGREEMENTS.json"; ADJ = HERE / "PACK_U_ADJUDICATION.json"
OUT = HERE / "PACK_U_CONSENSUS.json"


def atomic(path, obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); os.replace(tmp,path)


def main():
    if OUT.exists(): raise RuntimeError('refusing to overwrite consensus')
    a=json.loads(A.read_text(encoding='utf-8')); b=json.loads(B.read_text(encoding='utf-8'))
    V.validate(a, expected_coder='A_CLAUDE_USE_01'); V.validate(b, expected_coder='B_SOL_USE_01')
    dis=json.loads(DIS.read_text(encoding='utf-8')); adj=json.loads(ADJ.read_text(encoding='utf-8'))
    if adj.get('schema')!='pack_u_adjudication_v1' or adj.get('source_disagreements_sha256')!=V.digest(DIS) or adj.get('key_access') is not False:
        raise ValueError('adjudication binding/blinding invalid')
    dids=[x['id'] for x in dis['items']]; res=adj.get('resolutions') or []
    if [x.get('id') for x in res]!=dids or len(set(dids))!=len(dids): raise ValueError('resolution ID closure mismatch')
    rmap={x['id']:x for x in res}; sections=V.source_sections(PACK.read_text(encoding='utf-8'))
    items=[]
    for x,y in zip(a['items'],b['items']):
        if x['id']!=y['id']: raise ValueError('coder item alignment mismatch')
        if x['rebuildability']==y['rebuildability']:
            value=x['rebuildability']; evidence=x['rebuildability_evidence']; rationale='두 코더 등급 일치'; status='agreement'
        else:
            r=rmap[x['id']]
            if set(r)!={'id','value','evidence','rationale','confidence'} or r['value'] not in V.ENUM or not 0<=r['confidence']<=1:
                raise ValueError(f"{x['id']}: invalid resolution")
            if r['evidence'] not in V.notebook_text(sections[x['id']]): raise ValueError(f"{x['id']}: non-local adjudication evidence")
            value,evidence,rationale,status=r['value'],r['evidence'],r['rationale'],'adjudicated'
        items.append({'id':x['id'],'coder_A':x,'coder_B':y,'consensus_rebuildability':value,
                      'consensus_evidence':evidence,'consensus_rationale':rationale,'status':status})
    obj={'schema':'pack_u_consensus_v1','source_path':PACK.name,'source_sha256':V.digest(PACK),
         'coder_artifact_sha256':[V.digest(A),V.digest(B)],'disagreements_sha256':V.digest(DIS),
         'adjudication_sha256':V.digest(ADJ),'key_access':False,'items':items}
    atomic(OUT,obj); print(f"PACK_U_CONSENSUS items={len(items)} adjudicated={len(res)} sha256={V.digest(OUT)}")

if __name__=='__main__': main()
