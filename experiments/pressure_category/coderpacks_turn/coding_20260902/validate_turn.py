from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; PACK=HERE.parent/'PACK_T_turn_2026-09-02.md'
IDS=[f'T-{i:02d}' for i in range(1,25)]; PRINC={'같다','다르다','모르겠다'}; REL={'같은 답','다른 답','모르겠다'}; BASIS={'버렸다','다시 해석했다','판단 못 하겠다'}
TOP={'pack','coder_id','instruction_version','independent','key_access','source_path','source_sha256','items'}
FIELDS={'id','same_principle','principle_evidence_before','principle_evidence_after','answer_relation','answer_evidence_before','answer_evidence_after','change_basis','rationale','confidence'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sections(text):
 ms=list(re.finditer(r'^## (T-\d{2})\s*$',text,re.M)); return {m.group(1):text[m.start():ms[i+1].start() if i+1<len(ms) else len(text)] for i,m in enumerate(ms)}
def regions(s):
 a=s.split('**앞 수첩**',1)[1]; before,after=a.split('**뒤 수첩** (상대가 반대편을 민 뒤)',1); return before,after
def validate(o,expected_coder=None):
 if set(o)!=TOP or o['pack']!='PACK_T' or o['instruction_version']!='20260902-turn-v1':raise ValueError('top contract')
 if o['independent'] is not True or o['key_access'] is not False or o['source_path']!=PACK.name or o['source_sha256']!=digest(PACK):raise ValueError('binding/blinding')
 if expected_coder and o['coder_id']!=expected_coder:raise ValueError('coder mismatch')
 ss=sections(PACK.read_text(encoding='utf-8'))
 if list(ss)!=IDS or [x.get('id') for x in o['items']]!=IDS:raise ValueError('ID closure')
 for x in o['items']:
  if set(x)!=FIELDS:raise ValueError(f"{x.get('id')}: fields")
  if x['same_principle'] not in PRINC or x['answer_relation'] not in REL:raise ValueError(f"{x['id']}: enum")
  if (x['answer_relation']=='다른 답')!=(x['change_basis'] in BASIS):raise ValueError(f"{x['id']}: basis null rule")
  if not isinstance(x['rationale'],str) or not x['rationale'].strip() or not isinstance(x['confidence'],(int,float)) or isinstance(x['confidence'],bool) or not 0<=x['confidence']<=1:raise ValueError(f"{x['id']}: rationale/confidence")
  b,a=regions(ss[x['id']])
  for f,local in [('principle_evidence_before',b),('answer_evidence_before',b),('principle_evidence_after',a),('answer_evidence_after',a)]:
   q=x[f]
   if not isinstance(q,str) or not q or len(q)>300 or q not in local:raise ValueError(f"{x['id']}: non-local {f}")
def main():
 p=Path(sys.argv[1]);o=json.loads(p.read_text(encoding='utf-8'));validate(o,sys.argv[2] if len(sys.argv)>2 else None);print(f"PACK_T_VALID coder={o['coder_id']} items=24 sha256={digest(p)}")
if __name__=='__main__':main()
