from __future__ import annotations
import json,sys
from pathlib import Path
import validate_meaning as V
HERE=Path(__file__).resolve().parent
TOP={'pack','coder_id','instruction_version','independent','key_access','source_path','source_sha256','items'}
def validate(o:dict,expected_coder:str|None=None)->None:
 if set(o)!=TOP or o['pack']!='PACK_M' or o['instruction_version']!='20260902-meaning-v2-compact':raise ValueError('top contract')
 if o['independent'] is not True or o['key_access'] is not False or o['source_path']!=V.PACK.name or o['source_sha256']!=V.digest(V.PACK):raise ValueError('binding/blinding')
 if expected_coder and o['coder_id']!=expected_coder:raise ValueError('coder mismatch')
 ss=V.sections(V.PACK.read_text(encoding='utf-8'))
 if [x[0] if isinstance(x,list) and x else None for x in o.get('items',[])]!=V.IDS:raise ValueError('ID closure/order')
 for item in o['items']:
  if not isinstance(item,list) or len(item)!=2 or not isinstance(item[1],list):raise ValueError('item tuple')
  iid,cells=item;cats,note=V.parse_section(ss[iid])
  if [c[0] if isinstance(c,list) and c else None for c in cells]!=cats:raise ValueError(f'{iid}: category closure/order')
  for c in cells:
   if not isinstance(c,list) or len(c)!=4:raise ValueError(f'{iid}: cell tuple')
   cat,g,e,m=c
   if g not in V.GRADES:raise ValueError(f'{iid}/{cat}: grade')
   if g=='없다':
    if e is not None or m is not None:raise ValueError(f'{iid}/{cat}: absent null rule')
   else:
    if not isinstance(e,str) or not e.strip() or len(e)>120 or e not in note:raise ValueError(f'{iid}/{cat}: non-local evidence')
    if g=='부분만':
     if not isinstance(m,str) or not m.strip() or len(m)>160:raise ValueError(f'{iid}/{cat}: partial missing detail')
    elif m is not None:raise ValueError(f'{iid}/{cat}: alive null rule')
def expand(o:dict)->dict:
 return {'pack':'PACK_M','coder_id':o['coder_id'],'instruction_version':'20260902-meaning-v1','independent':True,'key_access':False,'source_path':o['source_path'],'source_sha256':o['source_sha256'],'items':[{'id':iid,'cells':[{'category':c,'grade':g,'evidence':e,'missing_detail':m} for c,g,e,m in cells]} for iid,cells in o['items']]}
def main()->None:
 p=Path(sys.argv[1]);o=json.loads(p.read_text(encoding='utf-8'));validate(o,sys.argv[2] if len(sys.argv)>2 else None);print(f"PACK_M_V2_VALID coder={o['coder_id']} items=99 cells=594 sha256={V.digest(p)}")
if __name__=='__main__':main()
