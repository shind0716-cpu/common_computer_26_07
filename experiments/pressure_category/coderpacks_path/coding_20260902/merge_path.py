from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import compare_path as C
import validate_adjudication as ADJ
import validate_path as V
HERE=Path(__file__).resolve().parent
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def merge(a:dict,b:dict,dis:dict,adj:dict,ha:str,hb:str,hj:str)->dict:
 V.validate(a);V.validate(b)
 if C.compare(a,b,ha,hb)!=dis:raise ValueError('disagreement artifact drift')
 ADJ.validate(adj,dis,adj['source_disagreement_sha256'])
 aa={x['id']:x for x in a['items']};bb={x['id']:x for x in b['items']};jj={x['id']:x for x in adj['items']};dis_ids={x['id'] for x in dis['disagreements']};items=[]
 for iid in V.IDS:
  xa,xb=aa[iid],bb[iid];is_dis=iid in dis_ids;xj=jj.get(iid)
  if is_dis!=(xj is not None):raise ValueError(f'{iid}: adjudication closure')
  final=xj if is_dis else xa;rounds=[]
  for idx in range(4):
   ra,rb=xa['rounds'][idx],xb['rounds'][idx];rj=xj['rounds'][idx] if xj else None
   if not is_dis and ra[1]!=rb[1]:raise ValueError(f'{iid}: false agreement')
   rounds.append({'round':idx+1,'support':rj[1] if rj else ra[1],'evidence':rj[2] if rj else [ra[2],rb[2]],'coder_supports':[ra[1],rb[1]],'coder_evidence':[ra[2],rb[2]],'adjudicator_evidence':rj[2] if rj else None,'coding_status':'adjudicated' if is_dis else 'audited_agreement'})
  states=[r['support'] for r in rounds];changes,flip,traj=V.derive(states)
  if [changes,flip,traj]!=[final['change_rounds'],final['first_flip_round'],final['trajectory']]:raise ValueError(f'{iid}: final derivation')
  items.append({'id':iid,'rounds':rounds,'change_rounds':changes,'first_flip_round':flip,'trajectory':traj,'coding_status':'adjudicated' if is_dis else 'audited_agreement','coder_rationales':[xa['rationale'],xb['rationale']],'adjudicator_rationale':xj['rationale'] if xj else None})
 return {'schema':'pack_p_consensus_v1','pack':'PACK_P','source_sha256':V.digest(V.PACK),'coder_artifact_sha256':[ha,hb],'disagreement_artifact_sha256':adj['source_disagreement_sha256'],'adjudication_artifact_sha256':hj,'item_count':48,'round_count':192,'agreement_count':48-len(dis_ids),'adjudicated_count':len(dis_ids),'items':items}
def main()->None:
 paths={n:HERE/n for n in ('A_CLAUDE_PATH_COMPOSITE_01_03.json','B_SOL_PATH_CORRECTED_01_02.json','PACK_P_DISAGREEMENTS.json','ADJUDICATION_RAW.json')};out=HERE/'PACK_P_CONSENSUS.json'
 if out.exists():raise RuntimeError('refusing overwrite')
 a,b,dis,adj=(json.loads(paths[n].read_text(encoding='utf-8')) for n in paths);ADJ.validate(adj,dis,sha(paths['PACK_P_DISAGREEMENTS.json']),'CLAUDE_ADJ_PATH_01');o=merge(a,b,dis,adj,sha(paths['A_CLAUDE_PATH_COMPOSITE_01_03.json']),sha(paths['B_SOL_PATH_CORRECTED_01_02.json']),sha(paths['ADJUDICATION_RAW.json']));atomic(out,o);print(f"PACK_P_CONSENSUS items=48 agreement={o['agreement_count']} adjudicated={o['adjudicated_count']} sha256={sha(out)}")
if __name__=='__main__':main()
