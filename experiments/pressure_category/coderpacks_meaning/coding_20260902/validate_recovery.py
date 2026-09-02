from __future__ import annotations
import copy,json
from pathlib import Path
import validate_meaning as V
import validate_meaning_v2 as W
HERE=Path(__file__).resolve().parent;PREFIX=HERE/'PACK_M_PREFIX_M001_M014.md';M80=HERE/'PACK_M_ITEM_M080.md';SOL=HERE/'B_SOL_MEANING_02_RAW.json'
def validate_prefix(o:dict)->None:
 top={'pack','coder_id','instruction_version','independent','key_access','parent_source_path','parent_source_sha256','slice_path','slice_sha256','items'}
 if set(o)!=top or o['pack']!='PACK_M' or o['coder_id']!='A_CLAUDE_MEANING_PREFIX_03' or o['instruction_version']!='20260902-meaning-prefix-v1':raise ValueError('prefix top')
 if o['independent'] is not True or o['key_access'] is not False or o['parent_source_path']!=V.PACK.name or o['parent_source_sha256']!=V.digest(V.PACK) or o['slice_path']!=PREFIX.name or o['slice_sha256']!=V.digest(PREFIX):raise ValueError('prefix binding')
 ss=V.sections(PREFIX.read_text(encoding='utf-8'));ids=V.IDS[:14]
 if [x[0] if isinstance(x,list) and x else None for x in o.get('items',[])]!=ids:raise ValueError('prefix ID closure')
 surrogate={'pack':'PACK_M','coder_id':o['coder_id'],'instruction_version':'20260902-meaning-v2-compact','independent':True,'key_access':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'items':o['items']}
 # Local subset validation mirrors v2 without requiring all 99 IDs.
 for iid,cells in surrogate['items']:
  cats,note=V.parse_section(ss[iid])
  if [c[0] for c in cells]!=cats:raise ValueError(f'{iid}: category closure')
  for cat,g,e,m in cells:
   if g not in V.GRADES:raise ValueError('grade')
   if g=='없다':
    if e is not None or m is not None:raise ValueError('absent null')
   else:
    if not isinstance(e,str) or not e.strip() or len(e)>120 or e not in note:raise ValueError(f'{iid}/{cat}: quote')
    if g=='부분만' and (not isinstance(m,str) or not m.strip() or len(m)>160):raise ValueError('partial missing')
    if g=='살아있다' and m is not None:raise ValueError('alive null')
def validate_sol_fix(fix:dict)->dict:
 top={'pack','coder_id','instruction_version','independent','key_access','source_raw_sha256','item_source_path','item_source_sha256','corrections'}
 if set(fix)!=top or fix['pack']!='PACK_M' or fix['coder_id']!='B_SOL_MEANING_02_QUOTE_FIX' or fix['instruction_version']!='20260902-meaning-sol-quote-fix-v1':raise ValueError('fix top')
 if fix['independent'] is not True or fix['key_access'] is not False or fix['source_raw_sha256']!=V.digest(SOL) or fix['item_source_path']!=M80.name or fix['item_source_sha256']!=V.digest(M80):raise ValueError('fix binding')
 coords=[('M-080','비용'),('M-080','접근성')]
 if [(x[0],x[1]) for x in fix.get('corrections',[])]!=coords:raise ValueError('fix scope')
 note=V.parse_section(V.sections(M80.read_text(encoding='utf-8'))['M-080'])[1]
 for _,_,q in fix['corrections']:
  if not isinstance(q,str) or not q.strip() or len(q)>120 or q not in note:raise ValueError('fix quote')
 raw=json.loads(SOL.read_text(encoding='utf-8'));corrected=copy.deepcopy(raw);item={x[0]:x for x in corrected['items']}['M-080'];cells={c[0]:c for c in item[1]}
 for _,cat,q in fix['corrections']:cells[cat][2]=q
 restored=copy.deepcopy(corrected);rcells={c[0]:c for c in {x[0]:x for x in restored['items']}['M-080'][1]};orig={c[0]:c for c in {x[0]:x for x in raw['items']}['M-080'][1]}
 for _,cat,_ in fix['corrections']:rcells[cat][2]=orig[cat][2]
 if restored!=raw:raise ValueError('fix changed non-approved coordinates')
 W.validate(corrected,'B_SOL_MEANING_02');return corrected
