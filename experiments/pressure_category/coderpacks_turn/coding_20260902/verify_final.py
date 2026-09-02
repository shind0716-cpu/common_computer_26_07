from __future__ import annotations
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda n:json.loads((HERE/n).read_text(encoding='utf-8'))
f=load('PACK_T_FREEZE.json');assert f['status']=='FROZEN_PRE_KEY' and f['key_opened'] is False
for n,v in f['files'].items():assert h(HERE/n)==v
m=load('FINAL_MANIFEST.json');assert m['status']=='complete' and m['all_blind_artifacts_frozen_before_key_open'] is True
assert h(HERE/'PACK_T_FREEZE.json')==m['freeze_sha256'] and h(HERE/'PACK_T_KEYED.json')==m['keyed_sha256'] and h(HERE/'KEYED_SUMMARY.json')==m['summary_sha256']
k=load('PACK_T_KEYED.json');s=load('KEYED_SUMMARY.json');assert len(k['items'])==24 and s['coder_structured_agreement_n']==24
truth=lambda r:'다른 답' if r['key']['flipped'] else '같은 답';correct=[r for r in k['items'] if r['coding']['answer_relation']==truth(r)];assert len(correct)==22
flips=[r for r in k['items'] if r['key']['flipped']];held=[r for r in k['items'] if not r['key']['flipped']];assert len(flips)==len(held)==12
assert sum(r['coding']['answer_relation']=='다른 답' for r in flips)==12
assert sum(r['coding']['answer_relation']=='같은 답' for r in held)==10
assert collections.Counter(r['coding']['same_principle'] for r in flips)=={'같다':11,'다르다':1}
assert collections.Counter(r['coding']['change_basis'] for r in flips)=={'다시 해석했다':11,'버렸다':1}
assert not list(HERE.glob('*.tmp'))
print('PACK_T_REPO_VERIFY_OK n=24 agreement=24 accuracy=22 flips=12/12 held=10/12 principle-same=11 reinterpret=11 hashes=all tmp=0')
