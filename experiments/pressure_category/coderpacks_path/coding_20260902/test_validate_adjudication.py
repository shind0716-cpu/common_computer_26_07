from __future__ import annotations
import copy,unittest
import compare_path as C
import test_validate_path as TV
import validate_adjudication as A

class AdjudicationTests(unittest.TestCase):
 def fixture(self):
  one=TV.PathContractTests().valid();one['coder_id']='A';two=copy.deepcopy(one);two['coder_id']='B'
  two['items'][1]['rounds'][1][1]='㉯';two['items'][1]['change_rounds']=[2,3];two['items'][1]['first_flip_round']=2;two['items'][1]['trajectory']='진동'
  dis=C.compare(one,two,'ha','hb');item=copy.deepcopy(one['items'][1])
  out={'pack':'PACK_P','adjudicator_id':'J','instruction_version':'20260902-path-adj-v1','independent':True,'key_access':False,'source_disagreement_sha256':'hash','items':[item]}
  return dis,out
 def test_valid(self):d,o=self.fixture();A.validate(o,d,'hash','J')
 def test_rejects_coordinate_drift(self):
  d,o=self.fixture();o['items']=[]
  with self.assertRaises(ValueError):A.validate(o,d,'hash')
 def test_rejects_nonlocal_and_derived_drift(self):
  d,o=self.fixture();o['items'][0]['rounds'][0][2]='foreign'
  with self.assertRaises(ValueError):A.validate(o,d,'hash')
  d,o=self.fixture();o['items'][0]['trajectory']='진동'
  with self.assertRaises(ValueError):A.validate(o,d,'hash')

if __name__=='__main__':unittest.main()
