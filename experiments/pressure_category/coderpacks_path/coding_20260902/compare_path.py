from __future__ import annotations
import copy,hashlib,json,os
from pathlib import Path
import validate_path as V
HERE=Path(__file__).resolve().parent
A=HERE/'A_CLAUDE_PATH_COMPOSITE_01_03.json';B=HERE/'B_SOL_PATH_CORRECTED_01_02.json';OUT=HERE/'PACK_P_DISAGREEMENTS.json'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def candidate(x:dict,label:str)->dict:
 return {'label':label,**{k:copy.deepcopy(x[k]) for k in ('rounds','change_rounds','first_flip_round','trajectory','rationale')}}
def compare(a:dict,b:dict,ha:str,hb:str)->dict:
 V.validate(a);V.validate(b)
 if ha==hb:raise ValueError('coder artifacts must differ')
 if a['coder_id']==b['coder_id']:raise ValueError('coder IDs must differ')
 aa={x['id']:x for x in a['items']};bb={x['id']:x for x in b['items']};agreements=[];dis=[];round_agree=0
 sections=V.sections(V.PACK.read_text(encoding='utf-8'))
 for iid in V.IDS:
  xa,xb=aa[iid],bb[iid];sa=[r[1] for r in xa['rounds']];sb=[r[1] for r in xb['rounds']];round_agree+=sum(x==y for x,y in zip(sa,sb))
  if sa==sb:agreements.append(iid);continue
  swap=int(hashlib.sha256(f'{ha}:{hb}:{iid}'.encode()).hexdigest(),16)%2
  pairs=[candidate(xa,'X'),candidate(xb,'Y')]
  if swap:pairs=[candidate(xb,'X'),candidate(xa,'Y')]
  dis.append({'id':iid,'public_section':sections[iid],'candidates':pairs})
 return {'schema':'pack_p_disagreement_v1','pack':'PACK_P','source_sha256':V.digest(V.PACK),'coder_artifact_sha256':[ha,hb],'compared_field':'round_support','item_count':48,'round_count':192,'agreement_count':len(agreements),'disagreement_count':len(dis),'round_agreement_count':round_agree,'agreement_ids':agreements,'disagreements':dis}
def main()->None:
 if OUT.exists():raise RuntimeError('refusing overwrite')
 a=json.loads(A.read_text(encoding='utf-8'));b=json.loads(B.read_text(encoding='utf-8'));V.validate(a,'A_CLAUDE_PATH_COMPOSITE_01_03');V.validate(b,'B_SOL_PATH_01');o=compare(a,b,sha(A),sha(B));atomic(OUT,o);atomic(HERE/'COMPARISON_SUMMARY.json',{k:v for k,v in o.items() if k not in {'agreement_ids','disagreements'}}|{'disagreement_sha256':sha(OUT)});print(f"PACK_P_COMPARE item_agreement={o['agreement_count']}/48 round_agreement={o['round_agreement_count']}/192 disagreements={o['disagreement_count']} sha256={sha(OUT)}")
if __name__=='__main__':main()
