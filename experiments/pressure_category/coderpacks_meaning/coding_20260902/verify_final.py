from __future__ import annotations
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def h(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n:str):return json.loads((HERE/n).read_text(encoding='utf-8'))
def main():
 f=load('PACK_M_FREEZE.json');assert f['status']=='FROZEN_PRE_KEY' and f['key_opened'] is False and f['source_sha256']==h(HERE.parent/'PACK_M_meaning_2026-09-02.md')
 assert all(h(HERE/n)==v for n,v in f['files'].items())
 m=load('FINAL_MANIFEST.json');assert m['status']=='complete' and m['all_blind_artifacts_frozen_before_key_open'] is True and m['freeze_sha256']==h(HERE/'PACK_M_FREEZE.json') and m['consensus_sha256']==h(HERE/'PACK_M_CONSENSUS.json') and m['keyed_sha256']==h(HERE/'PACK_M_KEYED.json') and m['summary_sha256']==h(HERE/'KEYED_SUMMARY.json')
 k=load('PACK_M_KEYED.json');flat=[c for x in k['items'] for c in x['cells']];assert len(k['items'])==99 and len(flat)==594
 assert collections.Counter(x['human_grade'] for x in flat)=={'살아있다':338,'부분만':165,'없다':91};assert sum(x['machine'] for x in flat)==150;assert sum(not x['machine'] and x['human_grade']!='없다' for x in flat)==353;assert sum(x['machine'] and x['human_grade']=='없다' for x in flat)==0
 s=load('KEYED_SUMMARY.json');assert s['overall']['human_present']==503 and s['overall']['machine_missed_human_present']==353 and s['overall']['machine_alive']==150
 assert s['by_arm']['가치 A']['machine_missed_human_present']==109 and s['by_arm']['신념 C0']['machine_missed_human_present']==121 and s['by_arm']['신념 압박']['machine_missed_human_present']==123
 assert not list(HERE.glob('*.tmp'))
 print('PACK_M_REPO_VERIFY_OK items=99 cells=594 agreement=429 adjudicated=165 human=338/165/91 machine=150 missed=353/503 false_positive=0 hashes=all tmp=0')
if __name__=='__main__':main()
