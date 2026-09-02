from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import validate_turn as V
HERE=Path(__file__).resolve().parent;A=HERE/'A_CLAUDE_TURN_01_RAW.json';B=HERE/'B_SOL_TURN_01_CORRECTED.json';OUT=HERE/'PACK_T_DISAGREEMENTS.json';FIELDS=('same_principle','answer_relation','change_basis')
def atomic(p,o):t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main():
 if OUT.exists():raise RuntimeError('refusing overwrite')
 a=json.loads(A.read_text(encoding='utf-8'));b=json.loads(B.read_text(encoding='utf-8'));V.validate(a,'A_CLAUDE_TURN_01');V.validate(b,'B_SOL_TURN_01');ah,bh=V.digest(A),V.digest(B);swap=int(hashlib.sha256((ah+bh).encode()).hexdigest(),16)&1;one,two=(b,a) if swap else (a,b);ss=V.sections(V.PACK.read_text(encoding='utf-8'));rows=[]
 for x,y in zip(one['items'],two['items']):
  diff=[f for f in FIELDS if x[f]!=y[f]]
  if diff:rows.append({'id':x['id'],'disputed_fields':diff,'source':ss[x['id']], 'CODER_1':x,'CODER_2':y})
 obj={'schema':'pack_t_disagreements_v1','source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'coder_artifact_sha256':sorted([ah,bh]),'n_disagreements':len(rows),'items':rows};atomic(OUT,obj);atomic(HERE/'ANONYMIZATION_MAP.json',{'swap':bool(swap),'CODER_1_sha256':V.digest(B if swap else A),'CODER_2_sha256':V.digest(A if swap else B)});print(f'PACK_T_DISAGREEMENTS n={len(rows)} fields={sum(len(x["disputed_fields"]) for x in rows)} sha256={V.digest(OUT)}')
if __name__=='__main__':main()
