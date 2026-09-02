from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda n:json.loads((HERE/n).read_text(encoding='utf-8'))

f=load('PACK_U_FREEZE.json')
assert f['status']=='FROZEN_PRE_KEY' and f['key_opened'] is False
for name,h in f['files'].items(): assert sha(HERE/name)==h
m=load('FINAL_MANIFEST.json')
assert m['status']=='complete' and m['all_blind_artifacts_frozen_before_key_open'] is True
assert sha(HERE/'PACK_U_FREEZE.json')==m['freeze_sha256']
assert sha(HERE/'PACK_U_KEYED.json')==m['keyed_sha256']
assert sha(HERE/'KEYED_SUMMARY.json')==m['summary_sha256']
k=load('PACK_U_KEYED.json'); s=load('KEYED_SUMMARY.json')
assert len(k['items'])==34 and len({x['id'] for x in k['items']})==34
counts=collections.Counter(x['coding']['consensus_rebuildability'] for x in k['items'])
assert dict(counts)==s['grades']=={'세울 수 있다':24,'부분만':10}
assert s['agreement_n']==25
zero=[x for x in k['items'] if x['key']['band']=='0개']
high=[x for x in k['items'] if x['key']['band']=='4개+']
assert len(zero)==12 and sum(x['coding']['consensus_rebuildability']=='세울 수 있다' for x in zero)==7
assert len(high)==10 and all(x['coding']['consensus_rebuildability']=='세울 수 있다' for x in high)
assert not list(HERE.glob('*.tmp'))
print('PACK_U_REPO_VERIFY_OK n=34 agreement=25 grades=24/10 zero-can=7/12 high-can=10/10 hashes=all tmp=0')
