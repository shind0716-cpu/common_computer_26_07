from __future__ import annotations
import json,os
from pathlib import Path
import validate_meaning as V
import validate_adjudication as ADJ
import validate_adjudication_null_fix as FIX
HERE=Path(__file__).resolve().parent;A=HERE/'A_CLAUDE_MEANING_COMPOSITE_01_03.json';B=HERE/'B_SOL_MEANING_02_EXPANDED.json'
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main()->None:
 fix=json.loads((HERE/'SOL_ADJ_NULL_FIX_01_RAW.json').read_text(encoding='utf-8'));chunks=FIX.apply(fix)
 for n,o in enumerate(chunks,1):atomic(HERE/f'ADJUDICATION_CHUNK_{n}_CORRECTED.json',o);ADJ.validate(o,n)
 resolutions=[r for o in chunks for r in o['resolutions']];rm={(r[0],r[1]):r for r in resolutions};assert len(rm)==165
 combined={'schema':'pack_m_adjudication_v1','source_disagreements_sha256':V.digest(HERE/'PACK_M_DISAGREEMENTS.json'),'raw_chunk_sha256':{str(n):V.digest(HERE/f'ADJUDICATION_CHUNK_{n}_RAW.json') for n in (1,2,3)},'null_fix_sha256':V.digest(HERE/'SOL_ADJ_NULL_FIX_01_RAW.json'),'correction_scope_n':12,'key_access':False,'resolutions':[{'id':i,'category':c,'grade':g,'evidence':e,'missing_detail':m,'rationale':why} for i,c,g,e,m,why in resolutions]};atomic(HERE/'PACK_M_ADJUDICATION.json',combined)
 a=json.loads(A.read_text(encoding='utf-8'));b=json.loads(B.read_text(encoding='utf-8'));V.validate(a);V.validate(b);items=[];agree=adjudicated=0
 for xa,xb in zip(a['items'],b['items']):
  cells=[]
  for ca,cb in zip(xa['cells'],xb['cells']):
   coord=(xa['id'],ca['category'])
   if ca['grade']==cb['grade']:
    grade=ca['grade'];final={'grade':grade,'evidence':ca['evidence'],'missing_detail':ca['missing_detail']};status='agreement';adj=None;agree+=1
   else:
    r=rm[coord];grade=r[2];final={'grade':grade,'evidence':r[3],'missing_detail':r[4]};status='adjudicated';adj={'grade':r[2],'evidence':r[3],'missing_detail':r[4],'rationale':r[5]};adjudicated+=1
   cells.append({'category':ca['category'],'grade':grade,'evidence':final['evidence'],'missing_detail':final['missing_detail'],'status':status,'coder_a':ca,'coder_b':cb,'adjudication':adj})
  items.append({'id':xa['id'],'cells':cells})
 if agree!=429 or adjudicated!=165 or len(rm)!=adjudicated:raise ValueError('merge counts')
 ss=V.sections(V.PACK.read_text(encoding='utf-8'))
 for x in items:
  cats,note=V.parse_section(ss[x['id']]);assert [c['category'] for c in x['cells']]==cats
  for c in x['cells']:
   if c['grade']=='없다':assert c['evidence'] is None and c['missing_detail'] is None
   else:
    assert isinstance(c['evidence'],str) and c['evidence'] in note
    if c['grade']=='부분만':assert isinstance(c['missing_detail'],str) and c['missing_detail'].strip()
    else:assert c['missing_detail'] is None
 consensus={'schema':'pack_m_consensus_v1','source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'key_access':False,'coder_a_sha256':V.digest(A),'coder_b_sha256':V.digest(B),'adjudication_sha256':V.digest(HERE/'PACK_M_ADJUDICATION.json'),'n_items':99,'n_cells':594,'n_agreements':agree,'n_adjudicated':adjudicated,'items':items};p=HERE/'PACK_M_CONSENSUS.json';atomic(p,consensus);print(f'PACK_M_CONSENSUS cells=594 agreement={agree} adjudicated={adjudicated} sha256={V.digest(p)}')
if __name__=='__main__':main()
