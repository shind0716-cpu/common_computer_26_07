from __future__ import annotations
import copy,unittest
import validate_meaning as V
import validate_meaning_v2 as W
class Tests(unittest.TestCase):
 def valid(self):
  ss=V.sections(V.PACK.read_text(encoding='utf-8'));items=[]
  for iid in V.IDS:
   cats,note=V.parse_section(ss[iid]);q=next(x.strip() for x in note.splitlines() if x.strip())[:60];items.append([iid,[[c,'살아있다',q,None] for c in cats]])
  return {'pack':'PACK_M','coder_id':'TEST_V2','instruction_version':'20260902-meaning-v2-compact','independent':True,'key_access':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'items':items}
 def test_valid_and_expand(self):
  o=self.valid();W.validate(o,'TEST_V2');e=W.expand(o);V.validate(e,'TEST_V2');self.assertEqual(sum(len(x['cells']) for x in e['items']),594)
 def test_missing(self):
  o=self.valid();o['items'].pop()
  with self.assertRaisesRegex(ValueError,'ID closure'):W.validate(o)
 def test_order(self):
  o=self.valid();o['items'][0][1].reverse()
  with self.assertRaisesRegex(ValueError,'category closure'):W.validate(o)
 def test_quote_and_null(self):
  o=self.valid();o['items'][0][1][0][2]='FOREIGN'
  with self.assertRaisesRegex(ValueError,'non-local'):W.validate(o)
  o=self.valid();o['items'][0][1][0][1]='없다'
  with self.assertRaisesRegex(ValueError,'absent null'):W.validate(o)
if __name__=='__main__':unittest.main()
