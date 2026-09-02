from __future__ import annotations
import json,os
from pathlib import Path
import validate_turn as V
HERE=Path(__file__).resolve().parent;A=HERE/'A_CLAUDE_TURN_01_RAW.json';B=HERE/'B_SOL_TURN_01_CORRECTED.json';DIS=HERE/'PACK_T_DISAGREEMENTS.json';ADJ=HERE/'PACK_T_ADJUDICATION.json';OUT=HERE/'PACK_T_CONSENSUS.json';FIELDS=('same_principle','answer_relation','change_basis')
def atomic(p,o):t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main():
 if OUT.exists():raise RuntimeError('refusing overwrite')
 a=json.loads(A.read_text(encoding='utf-8'));b=json.loads(B.read_text(encoding='utf-8'));V.validate(a,'A_CLAUDE_TURN_01');V.validate(b,'B_SOL_TURN_01');dis=json.loads(DIS.read_text(encoding='utf-8'));adj=json.loads(ADJ.read_text(encoding='utf-8'))
 if adj.get('schema')!='pack_t_adjudication_v1' or adj.get('source_disagreements_sha256')!=V.digest(DIS) or adj.get('key_access') is not False:raise ValueError('adjudication binding')
 did=[x['id'] for x in dis['items']];res=adj.get('resolutions') or []
 if [x.get('id') for x in res]!=did:raise ValueError('resolution closure')
 rmap={x['id']:x for x in res};dmap={x['id']:x for x in dis['items']};ss=V.sections(V.PACK.read_text(encoding='utf-8'));items=[]
 for x,y in zip(a['items'],b['items']):
  if x['id'] not in rmap:
   if any(x[f]!=y[f] for f in FIELDS):raise ValueError('missing disagreement')
   val={f:x[f] for f in FIELDS};ev={k:x[k] for k in ('principle_evidence_before','principle_evidence_after','answer_evidence_before','answer_evidence_after')};rat='두 코더 정형 필드 일치';status='agreement'
  else:
   r=rmap[x['id']];req={'id',*FIELDS,'principle_evidence_before','principle_evidence_after','answer_evidence_before','answer_evidence_after','rationale','confidence'}
   if set(r)!=req or r['same_principle'] not in V.PRINC or r['answer_relation'] not in V.REL or ((r['answer_relation']=='다른 답')!=(r['change_basis'] in V.BASIS)) or not 0<=r['confidence']<=1:raise ValueError(f"{x['id']}: resolution shape")
   for f in FIELDS:
    if f not in dmap[x['id']]['disputed_fields'] and r[f]!=x[f]:raise ValueError(f"{x['id']}: changed agreed field {f}")
   before,after=V.regions(ss[x['id']])
   for f,local in [('principle_evidence_before',before),('answer_evidence_before',before),('principle_evidence_after',after),('answer_evidence_after',after)]:
    if r[f] not in local:raise ValueError(f"{x['id']}: non-local {f}")
   val={f:r[f] for f in FIELDS};ev={k:r[k] for k in ('principle_evidence_before','principle_evidence_after','answer_evidence_before','answer_evidence_after')};rat=r['rationale'];status='adjudicated'
  items.append({'id':x['id'],'coder_A':x,'coder_B':y,**val,**ev,'rationale':rat,'status':status})
 obj={'schema':'pack_t_consensus_v1','source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'coder_artifact_sha256':[V.digest(A),V.digest(B)],'disagreements_sha256':V.digest(DIS),'adjudication_sha256':V.digest(ADJ),'key_access':False,'items':items};atomic(OUT,obj);print(f'PACK_T_CONSENSUS items=24 adjudicated={len(res)} sha256={V.digest(OUT)}')
if __name__=='__main__':main()
