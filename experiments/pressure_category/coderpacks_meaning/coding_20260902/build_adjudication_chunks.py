from __future__ import annotations
import hashlib,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;SRC=HERE/'PACK_M_DISAGREEMENTS.json'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,s:str)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(s,encoding='utf-8');os.replace(t,p)
def main()->None:
 d=json.loads(SRC.read_text(encoding='utf-8'));assert d['n_disagreements']==165 and len(d['items'])==165
 manifest={'schema':'pack_m_adjudication_chunks_v1','source_disagreements_sha256':sha(SRC),'chunks':[]}
 for n,start in enumerate(range(0,165,55),1):
  rows=d['items'][start:start+55];lines=[f'# 팩 「뜻」 익명 불일치 판정 {n}/3','', '> 모델 정체·조건·기계 키는 가렸다. 각 칸을 원문만으로 독립 판정한다.','']
  last=None
  for r in rows:
   if r['id']!=last:lines += [f"## {r['id']}",'',r['source'],''];last=r['id']
   lines += [f"### {r['id']} / {r['category']}",'',f"- CODER_1: `{json.dumps(r['coder_1'],ensure_ascii=False,separators=(',',':'))}`",f"- CODER_2: `{json.dumps(r['coder_2'],ensure_ascii=False,separators=(',',':'))}`",'']
  p=HERE/f'ADJUDICATION_CHUNK_{n}.md';atomic(p,'\n'.join(lines));manifest['chunks'].append({'chunk':n,'path':p.name,'sha256':sha(p),'n':len(rows),'coordinates':[[r['id'],r['category']] for r in rows]})
 atomic(HERE/'ADJUDICATION_CHUNKS_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({'status':'ADJUDICATION_CHUNKS_READY','sizes':[x['n'] for x in manifest['chunks']],'source_sha256':sha(SRC)}))
if __name__=='__main__':main()
