from __future__ import annotations
import copy,unittest
import validate_meaning as V
class Tests(unittest.TestCase):
 def valid(self):
  ss=V.sections(V.PACK.read_text(encoding='utf-8'));items=[]
  for iid in V.IDS:
   cats,note=V.parse_section(ss[iid]);q=next(x.strip() for x in note.splitlines() if x.strip())[:80]
   items.append({'id':iid,'cells':[{'category':c,'grade':'살아있다','evidence':q,'missing_detail':None} for c in cats]})
  return {'pack':'PACK_M','coder_id':'TEST','instruction_version':'20260902-meaning-v1','independent':True,'key_access':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'items':items}
 def test_valid(self):V.validate(self.valid(),'TEST')
 def test_missing_item(self):
  o=self.valid();o['items'].pop()
  with self.assertRaisesRegex(ValueError,'ID closure'):V.validate(o)
 def test_category_order(self):
  o=self.valid();o['items'][0]['cells'].reverse()
  with self.assertRaisesRegex(ValueError,'category closure'):V.validate(o)
 def test_foreign_quote(self):
  o=self.valid();o['items'][0]['cells'][0]['evidence']='NOT IN NOTE'
  with self.assertRaisesRegex(ValueError,'non-local evidence'):V.validate(o)
 def test_conditional_fields(self):
  o=self.valid();c=o['items'][0]['cells'][0];c.update(grade='부분만',missing_detail=None)
  with self.assertRaisesRegex(ValueError,'partial missing'):V.validate(o)
  o=self.valid();c=o['items'][0]['cells'][0];c.update(grade='없다',evidence='x')
  with self.assertRaisesRegex(ValueError,'absent null'):V.validate(o)
if __name__=='__main__':unittest.main()
