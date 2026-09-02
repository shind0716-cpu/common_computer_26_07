from __future__ import annotations
import copy,json,unittest
import validate_adjudication_null_fix as F
import validate_meaning as V
class Tests(unittest.TestCase):
 def valid(self):
  coords=json.loads(F.STATUS.read_text(encoding='utf-8'))['failure_coordinates'];return {'schema':'pack_m_adjudication_null_fix_v1','corrector_id':'SOL_ADJ_NULL_FIX_01','instruction_version':'20260902-adj-null-fix-v1','independent':True,'key_access':False,'source_pack_sha256':V.digest(F.PACK),'confirmations':[[a,b,'없다'] for a,b in coords]}
 def test_valid_and_apply(self):self.assertEqual(sum(len(x['resolutions']) for x in F.apply(self.valid())),165)
 def test_refusal(self):
  o=self.valid();o['confirmations'][0][2]='교정 거부'
  with self.assertRaisesRegex(ValueError,'scope'):F.validate_fix(o)
 def test_missing(self):
  o=self.valid();o['confirmations'].pop()
  with self.assertRaisesRegex(ValueError,'scope'):F.validate_fix(o)
if __name__=='__main__':unittest.main()
