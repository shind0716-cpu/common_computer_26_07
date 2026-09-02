from __future__ import annotations
import json,sys
from pathlib import Path
import validate_path as V
TOP={'pack','adjudicator_id','instruction_version','independent','key_access','source_disagreement_sha256','items'}
def validate(o:object,dis:dict,source_hash:str,expected_adjudicator:str|None=None)->None:
 if not isinstance(o,dict) or set(o)!=TOP or o['pack']!='PACK_P' or o['instruction_version']!='20260902-path-adj-v1':raise ValueError('top contract')
 if o['independent'] is not True or o['key_access'] is not False or o['source_disagreement_sha256']!=source_hash:raise ValueError('binding/blinding')
 if expected_adjudicator and o['adjudicator_id']!=expected_adjudicator:raise ValueError('adjudicator mismatch')
 expected=[x['id'] for x in dis['disagreements']]
 if not isinstance(o['items'],list) or [x.get('id') for x in o['items']]!=expected:raise ValueError('adjudication coordinate closure')
 sections={x['id']:x['public_section'] for x in dis['disagreements']}
 for x in o['items']:V.validate_item(x,x['id'],sections[x['id']])
def main()->None:
 here=Path(__file__).resolve().parent;raw=Path(sys.argv[1]);dis_path=here/'PACK_P_DISAGREEMENTS.json';dis=json.loads(dis_path.read_text(encoding='utf-8'));o=json.loads(raw.read_text(encoding='utf-8'));validate(o,dis,V.digest(dis_path),sys.argv[2] if len(sys.argv)>2 else None);print(f"PACK_P_ADJ_VALID items={len(o['items'])} sha256={V.digest(raw)}")
if __name__=='__main__':main()
