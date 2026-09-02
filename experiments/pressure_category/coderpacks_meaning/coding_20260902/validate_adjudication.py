from __future__ import annotations
import json,sys
from pathlib import Path
import validate_meaning as V
HERE=Path(__file__).resolve().parent;DIS=HERE/'PACK_M_DISAGREEMENTS.json';MAN=HERE/'ADJUDICATION_CHUNKS_MANIFEST.json'
def validate(o:dict,chunk:int)->None:
 top={'schema','adjudicator_id','instruction_version','independent','key_access','source_disagreements_sha256','chunk','chunk_sha256','resolutions'}
 if set(o)!=top or o['schema']!='pack_m_adjudication_chunk_v1' or o['instruction_version']!='20260902-meaning-adjudication-v1' or o['chunk']!=chunk:raise ValueError('top contract')
 if o['adjudicator_id']!=f'CLAUDE_ADJ_M_CHUNK_{chunk}' or o['independent'] is not True or o['key_access'] is not False or o['source_disagreements_sha256']!=V.digest(DIS):raise ValueError('binding/blinding')
 man=json.loads(MAN.read_text(encoding='utf-8'));meta=man['chunks'][chunk-1]
 if o['chunk_sha256']!=meta['sha256'] or [(x[0],x[1]) for x in o.get('resolutions',[])]!=[tuple(x) for x in meta['coordinates']]:raise ValueError('coordinate closure/order')
 rows={(x['id'],x['category']):x for x in json.loads(DIS.read_text(encoding='utf-8'))['items']}
 for iid,cat,g,e,m,why in o['resolutions']:
  if g not in V.GRADES or not isinstance(why,str) or not why.strip():raise ValueError(f'{iid}/{cat}: grade/rationale')
  source=rows[(iid,cat)]['source']
  if g=='없다':
   if e is not None or m is not None:raise ValueError(f'{iid}/{cat}: absent null')
  else:
   if not isinstance(e,str) or not e.strip() or len(e)>180 or e not in source:raise ValueError(f'{iid}/{cat}: quote')
   if g=='부분만' and (not isinstance(m,str) or not m.strip() or len(m)>200):raise ValueError(f'{iid}/{cat}: partial missing')
   if g=='살아있다' and m is not None:raise ValueError(f'{iid}/{cat}: alive null')
def main()->None:
 p=Path(sys.argv[1]);n=int(sys.argv[2]);o=json.loads(p.read_text(encoding='utf-8'));validate(o,n);print(f'PACK_M_ADJ_VALID chunk={n} resolutions=55 sha256={V.digest(p)}')
if __name__=='__main__':main()
