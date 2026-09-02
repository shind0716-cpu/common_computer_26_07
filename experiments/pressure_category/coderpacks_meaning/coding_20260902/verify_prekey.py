from __future__ import annotations
import copy,json
from pathlib import Path
import validate_meaning as V
HERE=Path(__file__).resolve().parent
def load(n:str):return json.loads((HERE/n).read_text(encoding='utf-8'))
def verify()->dict:
 a=load('A_CLAUDE_MEANING_COMPOSITE_01_03.json');b=load('B_SOL_MEANING_02_EXPANDED.json');V.validate(a);V.validate(b)
 assembly=load('ASSEMBLY_MANIFEST.json');assert assembly['status']=='ASSEMBLED_VALID' and assembly['key_access'] is False and assembly['claude']['assembled_sha256']==V.digest(HERE/'A_CLAUDE_MEANING_COMPOSITE_01_03.json') and assembly['sol']['expanded_sha256']==V.digest(HERE/'B_SOL_MEANING_02_EXPANDED.json')
 dis=load('PACK_M_DISAGREEMENTS.json');adj=load('PACK_M_ADJUDICATION.json');con=load('PACK_M_CONSENSUS.json');assert dis['n_cells']==594 and dis['n_agreements']==429 and dis['n_disagreements']==165 and len(dis['items'])==165
 dcoords=[(x['id'],x['category']) for x in dis['items']];acoords=[(x['id'],x['category']) for x in adj['resolutions']];assert dcoords==acoords and len(set(dcoords))==165 and adj['source_disagreements_sha256']==V.digest(HERE/'PACK_M_DISAGREEMENTS.json') and adj['key_access'] is False
 assert con['n_items']==99 and con['n_cells']==594 and con['n_agreements']==429 and con['n_adjudicated']==165 and con['adjudication_sha256']==V.digest(HERE/'PACK_M_ADJUDICATION.json') and con['key_access'] is False
 ss=V.sections(V.PACK.read_text(encoding='utf-8'));counts={'agreement':0,'adjudicated':0}
 for x in con['items']:
  cats,note=V.parse_section(ss[x['id']]);assert [c['category'] for c in x['cells']]==cats
  for c in x['cells']:
   counts[c['status']]+=1
   if c['grade']=='없다':assert c['evidence'] is None and c['missing_detail'] is None
   else:
    assert c['evidence'] in note
    if c['grade']=='부분만':assert isinstance(c['missing_detail'],str) and c['missing_detail'].strip()
    else:assert c['missing_detail'] is None
 assert counts=={'agreement':429,'adjudicated':165}
 # Restore each approved correction and prove all non-approved values are identical.
 solraw=load('B_SOL_MEANING_02_RAW.json');solcor=load('B_SOL_MEANING_02_CORRECTED.json');rest=copy.deepcopy(solcor);rm={x[0]:x for x in solraw['items']};cm={x[0]:x for x in rest['items']}
 for cat in ('비용','접근성'):{c[0]:c for c in cm['M-080'][1]}[cat][2]={c[0]:c for c in rm['M-080'][1]}[cat][2]
 assert rest==solraw
 coding=load('CALL_LEDGER.json');adjl=load('ADJUDICATION_CALL_LEDGER.json');fixl=load('ADJUDICATION_CORRECTION_CALL_LEDGER.json');assert coding['cap']==6 and len(coding['entries'])==6 and adjl['cap']==3 and len(adjl['entries'])==3 and fixl['cap']==1 and len(fixl['entries'])==1
 for receipt,output in [('A_CLAUDE_MEANING_01_LAUNCH_RECEIPT.json','A_CLAUDE_MEANING_01_RAW.json'),('B_SOL_MEANING_02_LAUNCH_RECEIPT.json','B_SOL_MEANING_02_RAW.json'),('A_CLAUDE_MEANING_PREFIX_03_LAUNCH_RECEIPT.json','A_CLAUDE_MEANING_PREFIX_03_RAW.json'),('B_SOL_MEANING_02_QUOTE_FIX_LAUNCH_RECEIPT.json','B_SOL_MEANING_02_QUOTE_FIX_RAW.json'),('SOL_ADJ_NULL_FIX_01_RECEIPT.json','SOL_ADJ_NULL_FIX_01_RAW.json')]:assert load(receipt)['output_sha256']==V.digest(HERE/output)
 for n in (1,2,3):assert load(f'ADJUDICATION_CHUNK_{n}_RECEIPT.json')['output_sha256']==V.digest(HERE/f'ADJUDICATION_CHUNK_{n}_RAW.json')
 assert not list(HERE.glob('*.tmp'))
 return {'items':99,'cells':594,'agreement':429,'adjudicated':165,'coding_launches':6,'adjudication_launches':3,'correction_launches':1}
def main():print('PACK_M_PREKEY_OK '+json.dumps(verify(),sort_keys=True))
if __name__=='__main__':main()
