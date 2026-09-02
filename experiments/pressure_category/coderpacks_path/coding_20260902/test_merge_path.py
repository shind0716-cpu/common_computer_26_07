from __future__ import annotations
import copy,unittest
import compare_path as C
import merge_path as M
import test_validate_adjudication as TA

class MergeTests(unittest.TestCase):
 def test_merge_preserves_agreement_and_adjudication(self):
  dis,adj=TA.AdjudicationTests().fixture();base=TA.TV.PathContractTests().valid();base['coder_id']='A';other=copy.deepcopy(base);other['coder_id']='B'
  other['items'][1]['rounds'][1][1]='㉯';other['items'][1]['change_rounds']=[2,3];other['items'][1]['first_flip_round']=2;other['items'][1]['trajectory']='진동'
  out=M.merge(base,other,dis,adj,'ha','hb','hj')
  self.assertEqual(len(out['items']),48);self.assertEqual(out['items'][0]['coding_status'],'audited_agreement');self.assertEqual(out['items'][1]['coding_status'],'adjudicated')
  self.assertEqual(out['items'][1]['rounds'][1]['support'],'㉮');self.assertEqual(out['items'][1]['rounds'][1]['coder_supports'],['㉮','㉯'])
 def test_rejects_incomplete_adjudication(self):
  dis,adj=TA.AdjudicationTests().fixture();a=TA.TV.PathContractTests().valid();a['coder_id']='A';b=copy.deepcopy(a);b['coder_id']='B';b['items'][1]['rounds'][1][1]='㉯';b['items'][1]['change_rounds']=[2,3];b['items'][1]['first_flip_round']=2;b['items'][1]['trajectory']='진동';adj['items']=[]
  with self.assertRaises(ValueError):M.merge(a,b,dis,adj,'ha','hb','hj')

if __name__=='__main__':unittest.main()
