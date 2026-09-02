from __future__ import annotations
import json,sys
from pathlib import Path
import validate_path as V
SUB_TOP={'pack','coder_id','instruction_version','independent','key_access','source_path','source_sha256','items'}
FIX_TOP={'pack','coder_id','instruction_version','independent','key_access','source_path','source_sha256','corrections'}
def validate_subset(o:object,ids:list[str],source_path:str,source_hash:str,expected_coder:str|None=None)->None:
 if not isinstance(o,dict) or set(o)!=SUB_TOP or o['pack']!='PACK_P_RECOVERY' or o['instruction_version']!='20260902-path-recovery-v1':raise ValueError('subset top contract')
 if o['independent'] is not True or o['key_access'] is not False or o['source_path']!=source_path or o['source_sha256']!=source_hash:raise ValueError('subset binding')
 if expected_coder and o['coder_id']!=expected_coder:raise ValueError('subset coder')
 if not isinstance(o['items'],list) or [x.get('id') for x in o['items']]!=ids:raise ValueError('subset ID closure')
 sections=V.sections(V.PACK.read_text(encoding='utf-8'))
 for x in o['items']:V.validate_item(x,x['id'],sections[x['id']])
def validate_sol_fix_shape(o:object,expected_coder:str|None=None,locality:bool=True)->None:
 if not isinstance(o,dict) or set(o)!=FIX_TOP or o['pack']!='PACK_P_QUOTE_FIX' or o['instruction_version']!='20260902-path-quote-fix-v1':raise ValueError('fix top contract')
 if o['independent'] is not True or o['key_access'] is not False or o['source_path']!=V.PACK.name or o['source_sha256']!=V.digest(V.PACK):raise ValueError('fix binding')
 if expected_coder and o['coder_id']!=expected_coder:raise ValueError('fix coder')
 if not isinstance(o['corrections'],list) or len(o['corrections'])!=1 or not isinstance(o['corrections'][0],dict) or set(o['corrections'][0])!={'id','round','support','evidence'}:raise ValueError('fix shape')
 x=o['corrections'][0]
 if (x['id'],x['round'],x['support'])!=('P-45',1,'㉮'):raise ValueError('fix scope')
 if locality:
  sec=V.sections(V.PACK.read_text(encoding='utf-8'))['P-45'];region=V.round_regions(sec)[1]
  if not isinstance(x['evidence'],str) or not x['evidence'] or len(x['evidence'])>300 or x['evidence'] not in region:raise ValueError('fix evidence locality')
