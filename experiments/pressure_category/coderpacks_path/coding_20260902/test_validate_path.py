from __future__ import annotations
import copy,unittest
import validate_path as V

class PathContractTests(unittest.TestCase):
 def test_truth_table(self):
  cases={
   ('㉮','㉮','㉮','㉮'):([],None,'일관'),
   ('㉮','㉮','㉯','㉯'):([3],3,'전향유지'),
   ('㉮','㉯','㉮','㉮'):([2,3],2,'진동'),
   ('㉮','판독 불가','㉯','㉯'):([3],3,'전향유지'),
   ('㉮','㉯','판독 불가','㉮'):([2,4],2,'진동'),
   ('판독 불가','㉮','㉮','㉮'):([],None,'판독 불가'),
   ('㉮','㉮','㉮','판독 불가'):([],None,'판독 불가'),
  }
  for states,want in cases.items():self.assertEqual(V.derive(states),want)
 def valid(self):
  sections=V.sections(V.PACK.read_text(encoding='utf-8'));items=[]
  for iid in V.IDS:
   rs=V.round_regions(sections[iid]);rounds=[]
   for n in range(1,5):
    quote=next(line.strip() for line in rs[n].splitlines() if line.strip())[:80]
    rounds.append([n,'㉮',quote])
   items.append({'id':iid,'rounds':rounds,'change_rounds':[],'first_flip_round':None,'trajectory':'일관','rationale':'네 글 모두 ㉮를 지지한다.','confidence':0.8})
  return {'pack':'PACK_P','coder_id':'CODER','instruction_version':'20260902-path-v1','independent':True,'key_access':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'items':items}
 def test_valid(self):V.validate(self.valid(),'CODER')
 def test_rejects_nonlocal_quote(self):
  o=self.valid();o['items'][0]['rounds'][0][2]='다른 글에만 있는 문장';
  with self.assertRaises(ValueError):V.validate(o)
 def test_rejects_inconsistent_derived_fields(self):
  o=self.valid();o['items'][0]['rounds'][1][1]='㉯'
  with self.assertRaises(ValueError):V.validate(o)
 def test_rejects_blinding_and_id_drift(self):
  for mutate in (lambda o:o.update(key_access=True),lambda o:o['items'].pop()):
   o=self.valid();mutate(o)
   with self.assertRaises(ValueError):V.validate(o)

if __name__=='__main__':unittest.main()
