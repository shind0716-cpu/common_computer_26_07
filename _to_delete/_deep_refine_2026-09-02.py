import json, sys, collections, statistics
from pathlib import Path
HERE=Path('.').resolve(); sys.path.insert(0,str(HERE))
from run_pressure import discover_materials, load_materials
from aggregate_all11 import probe
reg={iid:load_materials(p) for iid,p in discover_materials().items()}
lj=json.load(open('LABELS_c2_discourse_haiku_2026-09-01.json',encoding='utf-8'))
lrows=lj if isinstance(lj,list) else (lj.get('rows') or next(v for v in lj.values() if isinstance(v,list)))
labels={(r['issue_id'],r['run_id']):r for r in lrows}
runs=[]
for p in sorted(Path('runs/claude-haiku').glob('*/run_*.json')):
    if p.name.endswith('.final2.json'): continue
    d=json.loads(p.read_text(encoding='utf-8'))
    if d['meta'].get('dry') or d.get('value_set') not in ('A','B'): continue
    d['_mat']=reg[d['issue_id']]; runs.append(d)
def alive(a,t): return probe(a,t)[0]>=1
def choice_of(d):
    poll=(d.get('final_poll') or '').strip().strip("'\"*` \n"); o=d['_mat']['options']
    if poll in o: return poll
    pos={x:(d.get('final_poll') or '').rfind(x) for x in o}; hit=[x for x in o if pos[x]>=0]
    return max(hit,key=lambda x:pos[x]) if hit else None
def pct(v): return f"{100*v[0]/v[1]:.1f}% ({v[0]}/{v[1]})" if v[1] else '-'
# 1) 세트 안/밖 × 최종입장 편/반대 — C0 만, 마지막 수첩
T=collections.defaultdict(lambda:[0,0])
for d in runs:
    if d['script']!='C0': continue
    fin=choice_of(d); 
    if not fin: continue
    ln=d['notes'][-1]; incats=set(d.get('value_categories') or [])
    for f in d['_mat']['facts']:
        k=('안' if f['category'] in incats else '밖', 'pro' if f['favors']==fin else 'con', '정렬' if fin==d['aligned'] else '이탈')
        T[k][0]+=alive(f['anchor'],ln); T[k][1]+=1
print('== C0 마지막 수첩: 세트 안/밖 × 최종편/반대 × 판이 정렬/이탈')
for k in sorted(T): print('  ',k,pct(T[k]))
# 2) C2 라벨별 × 안/밖 × 수첩 k
U=collections.defaultdict(lambda:[0,0])
for d in runs:
    if d['script']!='C2': continue
    lb=labels.get((d['issue_id'],d['run_id'])); 
    if not lb: continue
    incats=set(d.get('value_categories') or [])
    for k,n in enumerate(d['notes'][:3]):
        for f in d['_mat']['facts']:
            kk=(lb['label'],'안' if f['category'] in incats else '밖',k)
            U[kk][0]+=alive(f['anchor'],n); U[kk][1]+=1
print('== C2 라벨 × 안/밖 × 수첩')
for k in sorted(U): print('  ',k,pct(U[k]))
# 3) 진짜뒤집힘: 전향 라운드 s 기준, 수첩 s-1 (전향 직전) 과 수첩 s (전향 직후) 에 새 입장 편 사실이 있었나
V=collections.Counter(); ex=[]
for d in runs:
    lb=labels.get((d['issue_id'],d['run_id']))
    if not lb or lb['label']!='진짜뒤집힘' or lb.get('shift_round') in (None,''): continue
    s=int(lb['shift_round']); new=lb[f'r{s}']
    prev=d['notes'][s-1] if s-1<len(d['notes']) else None
    if prev is None: continue
    newfacts=[f for f in d['_mat']['facts'] if f['favors']==new]
    n_alive=sum(alive(f['anchor'],prev) for f in newfacts)
    V[(s, 'new편 사실 있음' if n_alive>0 else 'new편 사실 0')]+=1
    if n_alive==0 and len(ex)<6: ex.append((d['issue_id'],d['run_id'],s))
print('== 진짜뒤집힘: 전향 직전 수첩에 새 입장 편 사실이 남아 있었나'); 
for k in sorted(V): print('  ',k,V[k])
print('  예:',ex)
# 4) 표식이 사안(stub)에 있는 사실 비율
st=collections.Counter()
for iid,m in reg.items():
    for f in m['facts']: st[f['anchor'] in m['stub']]+=1
print('== 표식이 stub 에 등장:',dict(st))
# 5) B 보강: C2 칸 3/3 일치 여부 × 라벨 조합
W=collections.Counter()
cells=collections.defaultdict(list)
for d in runs:
    if d['script']=='C2':
        lb=labels.get((d['issue_id'],d['run_id'])); cells[(d['issue_id'],d['value_set'])].append(lb['label'] if lb else '?')
for k,v in cells.items(): W[tuple(sorted(collections.Counter(v).items()))]+=1
print('== C2 칸(재료×세트) 라벨 조합')
for k,v in W.most_common(): print('  ',v,k)
