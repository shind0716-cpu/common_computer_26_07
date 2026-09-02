from __future__ import annotations
import collections,copy,json,os
from pathlib import Path
import validate_turn as V
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;KEY=ROOT/'_KEY_T_2026-09-02.json';CONS=HERE/'PACK_T_CONSENSUS.json';FREEZE=HERE/'PACK_T_FREEZE.json'
def atomic(p,o):t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main():
 if FREEZE.exists():raise RuntimeError('refusing overwrite')
 c=json.loads(CONS.read_text(encoding='utf-8'))
 if c.get('schema')!='pack_t_consensus_v1' or c.get('key_access') is not False or [x.get('id') for x in c.get('items',[])]!=V.IDS:raise ValueError('consensus contract')
 ss=V.sections(V.PACK.read_text(encoding='utf-8'))
 for x in c['items']:
  b,a=V.regions(ss[x['id']])
  for f,l in [('principle_evidence_before',b),('answer_evidence_before',b),('principle_evidence_after',a),('answer_evidence_after',a)]:
   if x[f] not in l:raise ValueError(f"{x['id']}: consensus quote")
  if (x['answer_relation']=='다른 답')!=(x['change_basis'] in V.BASIS):raise ValueError(f"{x['id']}: null rule")
 files=['CODING_PROTOCOL.md','coding_output.schema.json','PROMPT_CLAUDE.txt','PROMPT_SOL.txt','A_CLAUDE_TURN_01_RAW.json','B_SOL_TURN_01_RAW.json','B_SOL_TURN_01_CORRECTED.json','A_CLAUDE_TURN_01_LAUNCH_RECEIPT.json','B_SOL_TURN_01_LAUNCH_RECEIPT.json','B_SOL_TURN_01_CORRECTION_RECEIPT.json','HARD_STOP_STATUS.json','PACK_T_DISAGREEMENTS.json','PACK_T_ADJUDICATION.json','PACK_T_CONSENSUS.json']
 f={'schema':'pack_t_freeze_v1','status':'FROZEN_PRE_KEY','analysis_status':'post_hoc_exploratory','key_opened':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'files':{n:V.digest(HERE/n) for n in files}};atomic(FREEZE,f)
 chk=json.loads(FREEZE.read_text(encoding='utf-8'))
 if chk!=f or any(V.digest(HERE/n)!=h for n,h in chk['files'].items()):raise ValueError('freeze readback')
 key=json.loads(KEY.read_text(encoding='utf-8'));km={x['item']:x for x in key['items']}
 if set(km)!=set(V.IDS):raise ValueError('key closure')
 rows=[{'id':x['id'],'coding':x,'key':km[x['id']]} for x in c['items']];kp=HERE/'PACK_T_KEYED.json';atomic(kp,{'schema':'pack_t_keyed_v1','freeze_sha256':V.digest(FREEZE),'consensus_sha256':V.digest(CONS),'key_sha256':V.digest(KEY),'items':rows})
 def expected(r):return '다른 답' if r['key']['flipped'] else '같은 답'
 correct=[r for r in rows if r['coding']['answer_relation']==expected(r)]
 easy=[r for r in rows if r['key']['after_states_conclusion']];hard=[r for r in rows if not r['key']['after_states_conclusion']];flips=[r for r in rows if r['key']['flipped']]
 def acc(xs):return {'n':len(xs),'correct':sum(r['coding']['answer_relation']==expected(r) for r in xs)}
 summary={'schema':'pack_t_keyed_summary_v1','analysis_status':'post_hoc_exploratory','n':24,'coder_structured_agreement_n':24,'answer_relation':dict(collections.Counter(r['coding']['answer_relation'] for r in rows)),'truth':dict(collections.Counter(expected(r) for r in rows)),'accuracy':acc(rows),'easy_after_states_conclusion':acc(easy),'hard_no_stated_conclusion':acc(hard),'true_flips':{'n':len(flips),'same_principle':dict(collections.Counter(r['coding']['same_principle'] for r in flips)),'change_basis':dict(collections.Counter(r['coding']['change_basis'] for r in flips))},'warning':'AI coder agreement is model-to-model agreement, not human reliability.'}
 sp=HERE/'KEYED_SUMMARY.json';atomic(sp,summary);fm={'schema':'pack_t_final_manifest_v1','status':'complete','freeze_sha256':V.digest(FREEZE),'key_sha256':V.digest(KEY),'keyed_sha256':V.digest(kp),'summary_sha256':V.digest(sp),'all_blind_artifacts_frozen_before_key_open':True};atomic(HERE/'FINAL_MANIFEST.json',fm);print(f"PACK_T_FINALIZED accuracy={summary['accuracy']['correct']}/24 easy={summary['easy_after_states_conclusion']['correct']}/{summary['easy_after_states_conclusion']['n']} hard={summary['hard_no_stated_conclusion']['correct']}/{summary['hard_no_stated_conclusion']['n']} freeze={V.digest(FREEZE)}")
if __name__=='__main__':main()
