from __future__ import annotations
import copy,unittest
import assemble_recovery as A
import test_validate_path as TV

class AssembleTests(unittest.TestCase):
 def test_claude_exact_partition(self):
  full=TV.PathContractTests().valid();r2={'items':copy.deepcopy(full['items'][:21])};r3={'items':copy.deepcopy(full['items'][21:42])};out=A.assemble_claude(r2,r3,copy.deepcopy(full['items'][42:]));self.assertEqual([x['id'] for x in out['items']],A.V.IDS);A.V.validate(out,'A_CLAUDE_PATH_COMPOSITE_01_03')
 def test_sol_only_quote_changes(self):
  sol=TV.PathContractTests().valid();sol['coder_id']='B_SOL_PATH_01';fix={'corrections':[{'id':'P-45','round':1,'support':'㉮','evidence':'replacement'}]};new=A.correct_sol(sol,fix);self.assertEqual(new['items'][44]['rounds'][0][2],'replacement')
  old=copy.deepcopy(sol);new2=copy.deepcopy(new);old['items'][44]['rounds'][0][2]=None;new2['items'][44]['rounds'][0][2]=None;self.assertEqual(old,new2)

if __name__=='__main__':unittest.main()
