from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PACK=HERE.parent/'PACK_M_meaning_2026-09-02.md'
IDS=[f'M-{i:03d}' for i in range(1,100)];GRADES={'살아있다','부분만','없다'}
TOP={'pack','coder_id','instruction_version','independent','key_access','source_path','source_sha256','items'};ITEM={'id','cells'};CELL={'category','grade','evidence','missing_detail'}
def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def sections(text:str)->dict[str,str]:
 ms=list(re.finditer(r'^## (M-\d{3})\s*$',text,re.M));return {m.group(1):text[m.start():ms[i+1].start() if i+1<len(ms) else len(text)] for i,m in enumerate(ms)}
def parse_section(s:str)->tuple[list[str],str]:
 line=next(x for x in s.splitlines() if x.startswith('**따질 만한 여섯 갈래** — '));cats=line.split(' — ',1)[1].split(' · ');note=s.split('**수첩**',1)[1];return cats,note
def validate(o:dict,expected_coder:str|None=None)->None:
 if set(o)!=TOP or o['pack']!='PACK_M' or o['instruction_version']!='20260902-meaning-v1':raise ValueError('top contract')
 if o['independent'] is not True or o['key_access'] is not False or o['source_path']!=PACK.name or o['source_sha256']!=digest(PACK):raise ValueError('binding/blinding')
 if expected_coder and o['coder_id']!=expected_coder:raise ValueError('coder mismatch')
 ss=sections(PACK.read_text(encoding='utf-8'))
 if list(ss)!=IDS or [x.get('id') for x in o.get('items',[])]!=IDS:raise ValueError('ID closure/order')
 for x in o['items']:
  if set(x)!=ITEM:raise ValueError(f"{x.get('id')}: item fields")
  cats,note=parse_section(ss[x['id']])
  if [c.get('category') for c in x.get('cells',[])]!=cats:raise ValueError(f"{x['id']}: category closure/order")
  for c in x['cells']:
   if set(c)!=CELL or c['grade'] not in GRADES:raise ValueError(f"{x['id']}/{c.get('category')}: cell contract")
   g,e,m=c['grade'],c['evidence'],c['missing_detail']
   if g=='없다':
    if e is not None or m is not None:raise ValueError(f"{x['id']}/{c['category']}: absent null rule")
   else:
    if not isinstance(e,str) or not e.strip() or len(e)>180 or e not in note:raise ValueError(f"{x['id']}/{c['category']}: non-local evidence")
    if g=='부분만':
     if not isinstance(m,str) or not m.strip() or len(m)>240:raise ValueError(f"{x['id']}/{c['category']}: partial missing detail")
    elif m is not None:raise ValueError(f"{x['id']}/{c['category']}: alive null rule")
def main()->None:
 p=Path(sys.argv[1]);o=json.loads(p.read_text(encoding='utf-8'));validate(o,sys.argv[2] if len(sys.argv)>2 else None);print(f"PACK_M_VALID coder={o['coder_id']} items=99 cells=594 sha256={digest(p)}")
if __name__=='__main__':main()
