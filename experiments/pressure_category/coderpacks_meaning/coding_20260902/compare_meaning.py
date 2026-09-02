from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import validate_meaning as V
HERE=Path(__file__).resolve().parent;A=HERE/'A_CLAUDE_MEANING_COMPOSITE_01_03.json';B=HERE/'B_SOL_MEANING_02_EXPANDED.json'
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main()->None:
 a=json.loads(A.read_text(encoding='utf-8'));b=json.loads(B.read_text(encoding='utf-8'));V.validate(a);V.validate(b);ss=V.sections(V.PACK.read_text(encoding='utf-8'));out=[];agree=0
 for xa,xb in zip(a['items'],b['items']):
  assert xa['id']==xb['id']
  for ca,cb in zip(xa['cells'],xb['cells']):
   assert ca['category']==cb['category']
   if ca['grade']==cb['grade']:agree+=1;continue
   coord=f"{xa['id']}/{ca['category']}";swap=int(hashlib.sha256(coord.encode()).hexdigest(),16)%2==1;v1,v2=(cb,ca) if swap else (ca,cb)
   out.append({'id':xa['id'],'category':ca['category'],'source':ss[xa['id']],'coder_1':v1,'coder_2':v2})
 obj={'schema':'pack_m_disagreements_v1','source_sha256':V.digest(V.PACK),'coder_mapping_hidden':True,'compared_field':'grade','n_cells':594,'n_agreements':agree,'n_disagreements':len(out),'items':out};p=HERE/'PACK_M_DISAGREEMENTS.json';atomic(p,obj);print(f"PACK_M_COMPARE agreement={agree}/594 disagreements={len(out)} sha256={V.digest(p)}")
if __name__=='__main__':main()
