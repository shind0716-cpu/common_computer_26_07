from __future__ import annotations
import copy,json,unittest
import validate_meaning as V
import validate_recovery as R
class Tests(unittest.TestCase):
 def prefix(self):
  ss=V.sections(R.PREFIX.read_text(encoding='utf-8'));items=[]
  for iid in V.IDS[:14]:
   cats,note=V.parse_section(ss[iid]);q=next(x.strip() for x in note.splitlines() if x.strip())[:60];items.append([iid,[[c,'살아있다',q,None] for c in cats]])
  return {'pack':'PACK_M','coder_id':'A_CLAUDE_MEANING_PREFIX_03','instruction_version':'20260902-meaning-prefix-v1','independent':True,'key_access':False,'parent_source_path':V.PACK.name,'parent_source_sha256':V.digest(V.PACK),'slice_path':R.PREFIX.name,'slice_sha256':V.digest(R.PREFIX),'items':items}
 def fix(self):
  note=V.parse_section(V.sections(R.M80.read_text(encoding='utf-8'))['M-080'])[1];q=next(x.strip() for x in note.splitlines() if x.strip())[:60]
  return {'pack':'PACK_M','coder_id':'B_SOL_MEANING_02_QUOTE_FIX','instruction_version':'20260902-meaning-sol-quote-fix-v1','independent':True,'key_access':False,'source_raw_sha256':V.digest(R.SOL),'item_source_path':R.M80.name,'item_source_sha256':V.digest(R.M80),'corrections':[['M-080','비용',q],['M-080','접근성',q]]}
 def test_prefix_valid(self):R.validate_prefix(self.prefix())
 def test_prefix_missing(self):
  o=self.prefix();o['items'].pop()
  with self.assertRaisesRegex(ValueError,'ID closure'):R.validate_prefix(o)
 def test_fix_scope_and_non_scope(self):
  out=R.validate_sol_fix(self.fix());self.assertEqual(len(out['items']),99)
  o=self.fix();o['corrections'].reverse()
  with self.assertRaisesRegex(ValueError,'scope'):R.validate_sol_fix(o)
 def test_fix_foreign_quote(self):
  o=self.fix();o['corrections'][0][2]='FOREIGN'
  with self.assertRaisesRegex(ValueError,'quote'):R.validate_sol_fix(o)
if __name__=='__main__':unittest.main()
