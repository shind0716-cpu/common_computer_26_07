from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PACK=HERE.parent/'PACK_P_path_2026-09-02.md'
IDS=[f'P-{i:02d}' for i in range(1,49)]
SUPPORT={'㉮','㉯','판독 불가'};TRAJECTORY={'일관','전향유지','진동','판독 불가'}
TOP={'pack','coder_id','instruction_version','independent','key_access','source_path','source_sha256','items'}
FIELDS={'id','rounds','change_rounds','first_flip_round','trajectory','rationale','confidence'}
def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def sections(text:str)->dict[str,str]:
 ms=list(re.finditer(r'^## (P-\d{2})\s*$',text,re.M))
 return {m.group(1):text[m.start():ms[i+1].start() if i+1<len(ms) else len(text)] for i,m in enumerate(ms)}
def round_regions(section:str)->dict[int,str]:
 ms=list(re.finditer(r'^\*\*([1-4])번째 글\*\*\s*$',section,re.M))
 return {int(m.group(1)):section[m.end():ms[i+1].start() if i+1<len(ms) else len(section)] for i,m in enumerate(ms)}
def derive(states)->tuple[list[int],int|None,str]:
 if len(states)!=4 or any(x not in SUPPORT for x in states):raise ValueError('support states')
 if states[0]=='판독 불가' or states[-1]=='판독 불가':return [],None,'판독 불가'
 known=[(i+1,x) for i,x in enumerate(states) if x!='판독 불가'];changes=[]
 for (prev_i,prev),(cur_i,cur) in zip(known,known[1:]):
  if cur!=prev:changes.append(cur_i)
 trajectory='일관' if not changes else ('전향유지' if len(changes)==1 else '진동')
 return changes,(changes[0] if changes else None),trajectory
def validate_item(x:dict,iid:str,section:str)->None:
 if set(x)!=FIELDS or x.get('id')!=iid or not isinstance(x['rounds'],list) or len(x['rounds'])!=4:raise ValueError(f'{iid}: fields/round count')
 rr=round_regions(section);states=[]
 if list(rr)!=[1,2,3,4]:raise ValueError(f'{iid}: pack round regions')
 for expected,row in enumerate(x['rounds'],1):
  if not isinstance(row,list) or len(row)!=3 or row[0]!=expected or row[1] not in SUPPORT:raise ValueError(f'{iid}: round {expected} contract')
  q=row[2]
  if not isinstance(q,str) or not q.strip() or len(q)>300 or q not in rr[expected]:raise ValueError(f'{iid}: round {expected} non-local evidence')
  states.append(row[1])
 changes,flip,traj=derive(states)
 if x['change_rounds']!=changes or x['first_flip_round']!=flip or x['trajectory']!=traj:raise ValueError(f'{iid}: derived trajectory mismatch')
 if not isinstance(x['rationale'],str) or not x['rationale'].strip() or len(x['rationale'])>500:raise ValueError(f'{iid}: rationale')
 c=x['confidence']
 if not isinstance(c,(int,float)) or isinstance(c,bool) or not 0<=c<=1:raise ValueError(f'{iid}: confidence')
def validate(o:object,expected_coder:str|None=None)->None:
 if not isinstance(o,dict) or set(o)!=TOP or o['pack']!='PACK_P' or o['instruction_version']!='20260902-path-v1':raise ValueError('top contract')
 if o['independent'] is not True or o['key_access'] is not False or o['source_path']!=PACK.name or o['source_sha256']!=digest(PACK):raise ValueError('binding/blinding')
 if expected_coder and o['coder_id']!=expected_coder:raise ValueError('coder mismatch')
 ss=sections(PACK.read_text(encoding='utf-8'))
 if list(ss)!=IDS or not isinstance(o['items'],list) or [x.get('id') for x in o['items']]!=IDS:raise ValueError('ID closure')
 for x in o['items']:
  validate_item(x,x['id'],ss[x['id']])
def main()->None:
 p=Path(sys.argv[1]);o=json.loads(p.read_text(encoding='utf-8'));validate(o,sys.argv[2] if len(sys.argv)>2 else None);print(f"PACK_P_VALID coder={o['coder_id']} items=48 rounds=192 sha256={digest(p)}")
if __name__=='__main__':main()
