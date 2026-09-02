from __future__ import annotations
import copy,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import validate_receipt
import compare_path as C
import merge_path as M
import validate_adjudication as ADJ
import validate_path as V
FILES=['A_CLAUDE_PATH_01_RAW.json','A_CLAUDE_PATH_01_LAUNCH_RECEIPT.json','B_SOL_PATH_01_RAW.json','B_SOL_PATH_01_LAUNCH_RECEIPT.json','A_CLAUDE_PATH_RECOVERY_02_RAW.json','A_CLAUDE_PATH_RECOVERY_02_LAUNCH_RECEIPT.json','A_CLAUDE_PATH_RECOVERY_03_RAW.json','A_CLAUDE_PATH_RECOVERY_03_LAUNCH_RECEIPT.json','B_SOL_PATH_QUOTE_FIX_02_RAW.json','B_SOL_PATH_QUOTE_FIX_02_LAUNCH_RECEIPT.json','A_CLAUDE_PATH_COMPOSITE_01_03.json','B_SOL_PATH_CORRECTED_01_02.json','CALL_LEDGER.json','RUN_STATE.json','RECOVERY_RUN_STATE.json','RECOVERY_ACCEPTANCE_STATUS.json','PACK_P_DISAGREEMENTS.json','COMPARISON_SUMMARY.json','ADJUDICATION_RAW.json','ADJUDICATION_LAUNCH_RECEIPT.json','ADJUDICATION_LEDGER.json','ADJUDICATION_RUN_STATE.json','PACK_P_CONSENSUS.json']
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n:str):return json.loads((HERE/n).read_text(encoding='utf-8'))
def verify()->dict:
 if sha(V.PACK)!='a91725d6cfc537d052e5c0a21dae3d604d25052dcf265ee85f7228b6cac04c61':raise ValueError('pack drift')
 if any(HERE.glob('*.tmp')):raise ValueError('stale tmp')
 if any(not (HERE/n).exists() for n in FILES):raise ValueError('prekey closure missing')
 ledger=load('CALL_LEDGER.json');statuses=[e['status'] for e in ledger['entries']]
 if ledger['cap']!=5 or len(ledger['entries'])!=5 or statuses!=['FAILED_OR_REJECTED','FAILED_OR_REJECTED','ACCEPTED','ACCEPTED','ACCEPTED']:raise ValueError('coder ledger')
 if load('RECOVERY_RUN_STATE.json')['status']!='RECOVERY_RAW_ACCEPTED':raise ValueError('recovery state')
 receipts=[('A_CLAUDE_PATH_01','Claude'),('B_SOL_PATH_01','Hermes-Sol'),('A_CLAUDE_PATH_RECOVERY_02','Claude'),('A_CLAUDE_PATH_RECOVERY_03','Claude'),('B_SOL_PATH_QUOTE_FIX_02','Hermes-Sol')]
 for cid,fam in receipts:
  r=load(cid+'_LAUNCH_RECEIPT.json');validate_receipt(r,expected_nonce=r['launch_nonce'],expected_family=fam)
  if r['output_sha256']!=sha(HERE/(cid+'_RAW.json')):raise ValueError(f'{cid}: receipt output drift')
 adj_receipt=load('ADJUDICATION_LAUNCH_RECEIPT.json');validate_receipt(adj_receipt,expected_nonce=adj_receipt['launch_nonce'],expected_family='Claude')
 if adj_receipt['output_sha256']!=sha(HERE/'ADJUDICATION_RAW.json'):raise ValueError('adj receipt drift')
 al=load('ADJUDICATION_LEDGER.json')
 if al['cap']!=1 or len(al['entries'])!=1 or al['entries'][0]['status']!='ACCEPTED':raise ValueError('adj ledger')
 a=load('A_CLAUDE_PATH_COMPOSITE_01_03.json');b=load('B_SOL_PATH_CORRECTED_01_02.json');V.validate(a,'A_CLAUDE_PATH_COMPOSITE_01_03');V.validate(b,'B_SOL_PATH_01')
 # Sol correction changed exactly one evidence field.
 raw=load('B_SOL_PATH_01_RAW.json');x=copy.deepcopy(raw);y=copy.deepcopy(b);x['items'][44]['rounds'][0][2]=None;y['items'][44]['rounds'][0][2]=None
 if x!=y:raise ValueError('Sol correction scope')
 dis=load('PACK_P_DISAGREEMENTS.json');expected=C.compare(a,b,sha(HERE/'A_CLAUDE_PATH_COMPOSITE_01_03.json'),sha(HERE/'B_SOL_PATH_CORRECTED_01_02.json'))
 if dis!=expected or dis['agreement_count']!=47 or dis['round_agreement_count']!=191 or [z['id'] for z in dis['disagreements']]!=['P-15']:raise ValueError('comparison drift')
 adj=load('ADJUDICATION_RAW.json');ADJ.validate(adj,dis,sha(HERE/'PACK_P_DISAGREEMENTS.json'),'CLAUDE_ADJ_PATH_01')
 con=load('PACK_P_CONSENSUS.json');expected_con=M.merge(a,b,dis,adj,sha(HERE/'A_CLAUDE_PATH_COMPOSITE_01_03.json'),sha(HERE/'B_SOL_PATH_CORRECTED_01_02.json'),sha(HERE/'ADJUDICATION_RAW.json'))
 if con!=expected_con:raise ValueError('consensus drift')
 if len(con['items'])!=48 or sum(len(x['rounds']) for x in con['items'])!=192:raise ValueError('consensus closure')
 return {'files':{n:sha(HERE/n) for n in FILES},'consensus_sha256':sha(HERE/'PACK_P_CONSENSUS.json'),'items':48,'rounds':192,'agreement_items':47,'adjudicated_items':1,'coder_calls':5,'adjudication_calls':1}
def main()->None:
 r=verify();print(f"PACK_P_PREKEY_OK files={len(r['files'])} items=48 rounds=192 agreement=47 adjudicated=1 calls=5+1 consensus_sha256={r['consensus_sha256']}")
if __name__=='__main__':main()
