from __future__ import annotations
import unittest
from pathlib import Path
import validate_turn as V
class Tests(unittest.TestCase):
 def valid(self):
  ss=V.sections(V.PACK.read_text(encoding='utf-8'));items=[]
  for i,s in ss.items():
   b,a=V.regions(s);qb=next(x for x in b.splitlines() if x.strip()).strip()[:80];qa=next(x for x in a.splitlines() if x.strip()).strip()[:80]
   items.append({'id':i,'same_principle':'같다','principle_evidence_before':qb,'principle_evidence_after':qa,'answer_relation':'같은 답','answer_evidence_before':qb,'answer_evidence_after':qa,'change_basis':None,'rationale':'같은 방향','confidence':.8})
  return {'pack':'PACK_T','coder_id':'TEST','instruction_version':'20260902-turn-v1','independent':True,'key_access':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'items':items}
 def test_valid(self):V.validate(self.valid())
 def test_missing(self):
  o=self.valid();o['items'].pop()
  with self.assertRaises(ValueError):V.validate(o)
 def test_cross_region_quote(self):
  o=self.valid();o['items'][0]['answer_evidence_before']=o['items'][0]['answer_evidence_after']
  with self.assertRaises(ValueError):V.validate(o)
 def test_basis_null_rule(self):
  o=self.valid();o['items'][0]['change_basis']='버렸다'
  with self.assertRaises(ValueError):V.validate(o)
if __name__=='__main__':unittest.main()
