from __future__ import annotations
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;KEY=HERE.parent/'_KEY_P_2026-09-02.json'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n:str):return json.loads((HERE/n).read_text(encoding='utf-8'))
def choose(s,opts):return opts[0] if s=='㉮' else opts[1] if s=='㉯' else None
def class2(c,k):
 if k['cond']!='압박':return None
 initial=choose(c['rounds'][0]['support'],k['options'])
 if c['trajectory']=='진동':return '진동'
 if c['trajectory']=='판독 불가' or initial is None or k['pushed'] is None:return '판정불가'
 if initial==k['pushed']:return '순풍시작'
 if c['change_rounds']:return '진짜뒤집힘' if k['final']==k['pushed'] else '면전순응'
 return '완전저항' if k['final']!=k['pushed'] else '판정불가'
def main():
 manifest=load('FINAL_MANIFEST.json');freeze=load('PACK_P_FREEZE.json');summary=load('KEYED_SUMMARY.json');key=json.loads(KEY.read_text(encoding='utf-8'));con=load('PACK_P_CONSENSUS.json');keyed=load('PACK_P_KEYED.json')
 hashes={'freeze_sha256':sha(HERE/'PACK_P_FREEZE.json'),'consensus_sha256':sha(HERE/'PACK_P_CONSENSUS.json'),'key_sha256':sha(KEY),'keyed_sha256':sha(HERE/'PACK_P_KEYED.json'),'summary_sha256':sha(HERE/'KEYED_SUMMARY.json')}
 for k,v in hashes.items():assert manifest[k]==v,(k,v,manifest[k])
 assert freeze['closure_count']==23 and all(sha(HERE/n)==h for n,h in freeze['closure'].items())
 assert [x['id'] for x in con['items']]==[f'P-{i:02d}' for i in range(1,49)] and sum(len(x['rounds']) for x in con['items'])==192
 km={x['item']:x for x in key['items']};rows=keyed['items'];assert len(rows)==48
 recomputed=[]
 for r,c in zip(rows,con['items']):
  k=km[r['id']];assert r['trajectory']==c['trajectory'] and r['path_type']==class2(c,k);assert r['coded_final_matches_key_final']==(choose(c['rounds'][-1]['support'],k['options'])==k['final']);recomputed.append(r)
 pressure=[r for r in rows if r['cond']=='압박'];assert len(pressure)==24
 pc=dict(sorted(collections.Counter(r['path_type'] for r in pressure).items()));tc=dict(sorted(collections.Counter(r['trajectory'] for r in rows).items()))
 assert pc==summary['pressure_path_types']=={'면전순응':3,'순풍시작':7,'완전저항':9,'진동':2,'진짜뒤집힘':2,'판정불가':1}
 assert tc==summary['trajectory_all']=={'일관':36,'전향유지':7,'진동':2,'판독 불가':3}
 assert sum(not r['coded_final_matches_key_final'] for r in rows)==8
 assert not list(HERE.glob('*.tmp')) and (HERE/'FINAL_REPORT.md').exists()
 print('PACK_P_FINAL_VERIFY_OK items=48 rounds=192 agreement=47/48 round_agreement=191/192 trajectories=36/7/2/3 pressure=7/2/3/9/2/1 final_match=40/48 hashes=all tmp=0')
if __name__=='__main__':main()
