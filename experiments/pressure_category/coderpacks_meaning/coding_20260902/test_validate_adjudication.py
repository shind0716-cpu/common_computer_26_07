from __future__ import annotations
import copy,json,unittest
import validate_adjudication as A
import validate_meaning as V
class Tests(unittest.TestCase):
 def valid(self,n=1):
  man=json.loads(A.MAN.read_text(encoding='utf-8'));meta=man['chunks'][n-1];rows={(x['id'],x['category']):x for x in json.loads(A.DIS.read_text(encoding='utf-8'))['items']};res=[]
  for iid,cat in meta['coordinates']:
   src=rows[(iid,cat)]['source'];q=next(x.strip() for x in src.splitlines() if x.strip() and not x.startswith('#'))[:80];res.append([iid,cat,'살아있다',q,None,'근거가 구체적으로 남아 있다'])
  return {'schema':'pack_m_adjudication_chunk_v1','adjudicator_id':f'CLAUDE_ADJ_M_CHUNK_{n}','instruction_version':'20260902-meaning-adjudication-v1','independent':True,'key_access':False,'source_disagreements_sha256':V.digest(A.DIS),'chunk':n,'chunk_sha256':meta['sha256'],'resolutions':res}
 def test_all_chunks(self):
  for n in (1,2,3):A.validate(self.valid(n),n)
 def test_missing(self):
  o=self.valid();o['resolutions'].pop()
  with self.assertRaisesRegex(ValueError,'coordinate closure'):A.validate(o,1)
 def test_quote(self):
  o=self.valid();o['resolutions'][0][3]='FOREIGN'
  with self.assertRaisesRegex(ValueError,'quote'):A.validate(o,1)
 def test_null(self):
  o=self.valid();o['resolutions'][0][2]='없다'
  with self.assertRaisesRegex(ValueError,'absent null'):A.validate(o,1)
if __name__=='__main__':unittest.main()
