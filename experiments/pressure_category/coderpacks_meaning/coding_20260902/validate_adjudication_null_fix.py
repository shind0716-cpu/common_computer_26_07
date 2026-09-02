from __future__ import annotations
import copy,json
from pathlib import Path
import validate_adjudication as A
import validate_meaning as V
HERE=Path(__file__).resolve().parent;PACK=HERE/'ADJUDICATION_NULL_FIX_PACK.md';STATUS=HERE/'ADJUDICATION_HARD_STOP_STATUS.json'
def validate_fix(o:dict)->None:
 top={'schema','corrector_id','instruction_version','independent','key_access','source_pack_sha256','confirmations'}
 if set(o)!=top or o['schema']!='pack_m_adjudication_null_fix_v1' or o['corrector_id']!='SOL_ADJ_NULL_FIX_01' or o['instruction_version']!='20260902-adj-null-fix-v1':raise ValueError('top')
 if o['independent'] is not True or o['key_access'] is not False or o['source_pack_sha256']!=V.digest(PACK):raise ValueError('binding')
 coords=[tuple(x) for x in json.loads(STATUS.read_text(encoding='utf-8'))['failure_coordinates']]
 if [(x[0],x[1]) for x in o.get('confirmations',[]) ]!=coords or any(len(x)!=3 or x[2]!='없다' for x in o['confirmations']):raise ValueError('scope/confirmation')
def apply(o:dict)->list[dict]:
 validate_fix(o);coords={(x[0],x[1]) for x in o['confirmations']};out=[];changed=[]
 for n in (1,2,3):
  raw=json.loads((HERE/f'ADJUDICATION_CHUNK_{n}_RAW.json').read_text(encoding='utf-8'));cor=copy.deepcopy(raw)
  for r in cor['resolutions']:
   if (r[0],r[1]) in coords:
    if r[2] is not None or r[3] is not None or r[4] is not None:raise ValueError('unexpected raw null shape')
    r[2]='없다';changed.append((r[0],r[1]))
  restored=copy.deepcopy(cor)
  for r in restored['resolutions']:
   if (r[0],r[1]) in coords:r[2]=None
  if restored!=raw:raise ValueError('non-scope change')
  A.validate(cor,n);out.append(cor)
 if len(changed)!=len(coords) or set(changed)!=coords:raise ValueError('changed closure')
 return out
