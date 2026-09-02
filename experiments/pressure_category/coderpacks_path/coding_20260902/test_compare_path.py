from __future__ import annotations
import copy,unittest
import compare_path as C
import test_validate_path as TV

class CompareTests(unittest.TestCase):
 def test_agreement_and_item_disagreement(self):
  a=TV.PathContractTests().valid();a['coder_id']='A';b=copy.deepcopy(a);b['coder_id']='B'
  b['items'][1]['rounds'][1][1]='㉯';b['items'][1]['change_rounds']=[2,3];b['items'][1]['first_flip_round']=2;b['items'][1]['trajectory']='진동'
  out=C.compare(a,b,'ha','hb')
  self.assertEqual(out['agreement_count'],47);self.assertEqual(out['disagreement_count'],1);self.assertEqual(out['disagreements'][0]['id'],'P-02')
  self.assertNotIn('coder_id',str(out['disagreements'][0]));self.assertEqual({x['label'] for x in out['disagreements'][0]['candidates']},{'X','Y'})
 def test_rejects_same_artifact_hash(self):
  a=TV.PathContractTests().valid();b=copy.deepcopy(a);b['coder_id']='B'
  with self.assertRaises(ValueError):C.compare(a,b,'same','same')

if __name__=='__main__':unittest.main()
