from __future__ import annotations
import collections,json,os
from pathlib import Path
import validate_meaning as V
import verify_prekey
HERE=Path(__file__).resolve().parent;KEY=HERE.parent/'_KEY_M_2026-09-02.json';FREEZE=HERE/'PACK_M_FREEZE.json'
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main()->None:
 if FREEZE.exists():raise RuntimeError('refusing overwrite')
 pre=verify_prekey.verify();excluded={'PACK_M_FREEZE.json','PACK_M_KEYED.json','KEYED_SUMMARY.json','FINAL_MANIFEST.json','FINAL_REPORT.md','verify_final.py'}
 files=sorted(p for p in HERE.iterdir() if p.is_file() and p.name not in excluded and not p.name.endswith(('.tmp','.pyc')))
 freeze={'schema':'pack_m_freeze_v1','status':'FROZEN_PRE_KEY','analysis_status':'post_hoc_exploratory','key_opened':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'prekey_counts':pre,'files':{p.name:V.digest(p) for p in files}};atomic(FREEZE,freeze)
 chk=json.loads(FREEZE.read_text(encoding='utf-8'));assert chk==freeze and all(V.digest(HERE/n)==h for n,h in chk['files'].items())
 # Key access begins only below, after freeze readback.
 key=json.loads(KEY.read_text(encoding='utf-8'));cons=json.loads((HERE/'PACK_M_CONSENSUS.json').read_text(encoding='utf-8'));km={x['item']:x for x in key['items']};assert set(km)==set(V.IDS) and len(km)==99
 rows=[]
 for item in cons['items']:
  k=km[item['id']];assert [c['category'] for c in item['cells']]==k['cats_shown'] and set(k['machine'])==set(k['cats_shown'])
  rows.append({'id':item['id'],'arm':k['arm'],'cells':[{'category':c['category'],'human_grade':c['grade'],'machine':bool(k['machine'][c['category']]),'consensus_status':c['status']} for c in item['cells']]})
 flat=[{'arm':r['arm'],**c} for r in rows for c in r['cells']];assert len(flat)==594 and sum(x['machine'] for x in flat)==150
 def stats(xs):
  grades=collections.Counter(x['human_grade'] for x in xs);matrix=collections.Counter((str(x['machine']).lower(),x['human_grade']) for x in xs);present=sum(x['human_grade']!='없다' for x in xs);miss=sum(not x['machine'] and x['human_grade']!='없다' for x in xs)
  return {'n':len(xs),'human_grades':dict(grades),'machine_alive':sum(x['machine'] for x in xs),'matrix':{f'machine_{m}__human_{g}':v for (m,g),v in matrix.items()},'human_present':present,'machine_missed_human_present':miss,'machine_miss_rate_among_human_present':(miss/present if present else None),'machine_false_positive_vs_human_absent':sum(x['machine'] and x['human_grade']=='없다' for x in xs)}
 summary={'schema':'pack_m_keyed_summary_v1','analysis_status':'post_hoc_exploratory','question':'How much meaning does the lexical machine measure miss?','overall':stats(flat),'by_arm':{arm:stats([x for x in flat if x['arm']==arm]) for arm in ('가치 A','신념 C0','신념 압박')},'restrictions':['Do not use this pack for model rankings.','Do not publish category rankings because anchor detectability varies strongly by marker.'],'warning':'AI coder agreement is model-to-model agreement, not human reliability.'}
 keyed={'schema':'pack_m_keyed_v1','freeze_sha256':V.digest(FREEZE),'consensus_sha256':V.digest(HERE/'PACK_M_CONSENSUS.json'),'key_sha256':V.digest(KEY),'items':rows};atomic(HERE/'PACK_M_KEYED.json',keyed);atomic(HERE/'KEYED_SUMMARY.json',summary)
 manifest={'schema':'pack_m_final_manifest_v1','status':'complete','all_blind_artifacts_frozen_before_key_open':True,'freeze_sha256':V.digest(FREEZE),'key_sha256':V.digest(KEY),'consensus_sha256':V.digest(HERE/'PACK_M_CONSENSUS.json'),'keyed_sha256':V.digest(HERE/'PACK_M_KEYED.json'),'summary_sha256':V.digest(HERE/'KEYED_SUMMARY.json')};atomic(HERE/'FINAL_MANIFEST.json',manifest);print(f"PACK_M_FINALIZED human={summary['overall']['human_grades']} machine=150/594 missed={summary['overall']['machine_missed_human_present']}/{summary['overall']['human_present']} freeze={V.digest(FREEZE)}")
if __name__=='__main__':main()
