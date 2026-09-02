from __future__ import annotations
import copy,json,tempfile,unittest
from pathlib import Path
import build_recovery_inputs as B
import test_validate_path as TV
import validate_recovery as R

class RecoveryTests(unittest.TestCase):
 def test_partial_pack_closure(self):
  a,b=B.build_texts();self.assertEqual(B.ids_in(a),[f'P-{i:02d}' for i in range(1,22)]);self.assertEqual(B.ids_in(b),[f'P-{i:02d}' for i in range(22,43)])
  self.assertNotIn('_KEY_',a+b)
 def test_subset_validation(self):
  full=TV.PathContractTests().valid();ids=[f'P-{i:02d}' for i in range(1,22)];o={'pack':'PACK_P_RECOVERY','coder_id':'A1','instruction_version':'20260902-path-recovery-v1','independent':True,'key_access':False,'source_path':'partial.md','source_sha256':'h','items':copy.deepcopy(full['items'][:21])};R.validate_subset(o,ids,'partial.md','h','A1')
  o['items'].pop()
  with self.assertRaises(ValueError):R.validate_subset(o,ids,'partial.md','h')
 def test_sol_fix_scope(self):
  o={'pack':'PACK_P_QUOTE_FIX','coder_id':'B_FIX','instruction_version':'20260902-path-quote-fix-v1','independent':True,'key_access':False,'source_path':'PACK_P_path_2026-09-02.md','source_sha256':R.V.digest(R.V.PACK),'corrections':[{'id':'P-45','round':1,'support':'㉮','evidence':'x'}]}
  R.validate_sol_fix_shape(o,'B_FIX',locality=False);o['corrections'][0]['round']=2
  with self.assertRaises(ValueError):R.validate_sol_fix_shape(o,locality=False)

if __name__=='__main__':unittest.main()
