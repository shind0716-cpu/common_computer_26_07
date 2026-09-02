from __future__ import annotations
import copy,hashlib,json,os
from pathlib import Path
import validate_path as V
import validate_recovery as R
HERE=Path(__file__).resolve().parent
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def assemble_claude(r2:dict,r3:dict,suffix:list[dict])->dict:
 items=copy.deepcopy(r2['items'])+copy.deepcopy(r3['items'])+copy.deepcopy(suffix)
 if [x['id'] for x in items]!=V.IDS:raise ValueError('Claude partition closure')
 return {'pack':'PACK_P','coder_id':'A_CLAUDE_PATH_COMPOSITE_01_03','instruction_version':'20260902-path-v1','independent':True,'key_access':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'items':items}
def correct_sol(sol:dict,fix:dict)->dict:
 c=fix['corrections']
 if not isinstance(c,list) or len(c)!=1 or (c[0].get('id'),c[0].get('round'),c[0].get('support'))!=('P-45',1,'㉮'):raise ValueError('Sol correction scope')
 out=copy.deepcopy(sol);item=next(x for x in out['items'] if x['id']=='P-45')
 if item['rounds'][0][1]!='㉮':raise ValueError('Sol support drift')
 item['rounds'][0][2]=c[0]['evidence'];return out
def salvage_suffix(raw:str)->list[dict]:
 sections=V.sections(V.PACK.read_text(encoding='utf-8'));dec=json.JSONDecoder();out=[]
 for iid in [f'P-{i:02d}' for i in range(43,49)]:
  marker='{"id":"'+iid+'"';start=raw.find(marker)
  if start<0:raise ValueError(f'missing salvage {iid}')
  x,_=dec.raw_decode(raw[start:]);V.validate_item(x,iid,sections[iid]);out.append(x)
 return out
def main()->None:
 names=['A_CLAUDE_PATH_RECOVERY_02_RAW.json','A_CLAUDE_PATH_RECOVERY_03_RAW.json','A_CLAUDE_PATH_01_RAW.json','B_SOL_PATH_01_RAW.json','B_SOL_PATH_QUOTE_FIX_02_RAW.json'];p={n:HERE/n for n in names}
 ao=HERE/'A_CLAUDE_PATH_COMPOSITE_01_03.json';bo=HERE/'B_SOL_PATH_CORRECTED_01_02.json'
 if ao.exists() or bo.exists():raise RuntimeError('refusing overwrite')
 r2=json.loads(p[names[0]].read_text(encoding='utf-8'));r3=json.loads(p[names[1]].read_text(encoding='utf-8'));R.validate_subset(r2,[f'P-{i:02d}' for i in range(1,22)],'PACK_P_PREFIX_P01_P21.md','135d1892187c681db5aed3e850bbe00aec30f250ab9278c77b641f281bba1797','A_CLAUDE_PATH_RECOVERY_02');R.validate_subset(r3,[f'P-{i:02d}' for i in range(22,43)],'PACK_P_PREFIX_P22_P42.md','74fec2785a82df585c78ba750d2c9626b33c672f371ac0ee983b5d48a6e37454','A_CLAUDE_PATH_RECOVERY_03')
 a=assemble_claude(r2,r3,salvage_suffix(p[names[2]].read_text(encoding='utf-8')));V.validate(a,'A_CLAUDE_PATH_COMPOSITE_01_03')
 sol=json.loads(p[names[3]].read_text(encoding='utf-8'));fix=json.loads(p[names[4]].read_text(encoding='utf-8'));R.validate_sol_fix_shape(fix,'B_SOL_PATH_QUOTE_FIX_02');b=correct_sol(sol,fix);V.validate(b,'B_SOL_PATH_01')
 # Deep identity outside exactly one evidence path.
 x=copy.deepcopy(sol);y=copy.deepcopy(b);x['items'][44]['rounds'][0][2]=None;y['items'][44]['rounds'][0][2]=None
 if x!=y:raise ValueError('Sol non-approved field drift')
 atomic(ao,a);atomic(bo,b);atomic(HERE/'RECOVERY_ACCEPTANCE_STATUS.json',{'status':'CODER_OUTPUTS_ACCEPTED_AWAITING_COMPARISON','transport_attempts':5,'claude_composite_parts':[{'artifact':names[0],'sha256':sha(p[names[0]]),'ids':'P-01..P-21'},{'artifact':names[1],'sha256':sha(p[names[1]]),'ids':'P-22..P-42'},{'artifact':names[2],'sha256':sha(p[names[2]]),'ids':'P-43..P-48 salvage'}],'sol_correction':{'raw_sha256':sha(p[names[3]]),'fix_sha256':sha(p[names[4]]),'allowed_coordinate':['P-45',1,'evidence']},'accepted':{ao.name:sha(ao),bo.name:sha(bo)},'key_access':False});print(f'PACK_P_RECOVERY_ACCEPTED claude={sha(ao)} sol={sha(bo)}')
if __name__=='__main__':main()
