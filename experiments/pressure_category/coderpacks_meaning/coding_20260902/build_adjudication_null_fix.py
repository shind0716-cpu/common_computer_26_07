from __future__ import annotations
import json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;STATUS=HERE/'ADJUDICATION_HARD_STOP_STATUS.json';DIS=HERE/'PACK_M_DISAGREEMENTS.json'
def atomic(p:Path,s:str)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(s,encoding='utf-8');os.replace(t,p)
def main()->None:
 coords=[tuple(x) for x in json.loads(STATUS.read_text(encoding='utf-8'))['failure_coordinates']];rows={(x['id'],x['category']):x for x in json.loads(DIS.read_text(encoding='utf-8'))['items']};raw=[]
 for n in (1,2,3):raw.extend(json.loads((HERE/f'ADJUDICATION_CHUNK_{n}_RAW.json').read_text(encoding='utf-8'))['resolutions'])
 rm={(x[0],x[1]):x for x in raw};lines=['# 팩 「뜻」 익명 판정 enum 교정 12칸','', '> 아래 좌표는 최초 판정에서 grade를 JSON null로 냈다. 원문과 최초 이유를 읽고 `없다`인지 확인한다.','']
 last=None
 for coord in coords:
  r=rows[coord];x=rm[coord]
  if coord[0]!=last:lines += [f'## {coord[0]}','',r['source'],''];last=coord[0]
  lines += [f'### {coord[0]} / {coord[1]}','',f'- 최초 grade: `null`',f'- 최초 evidence/missing: `{x[3]}` / `{x[4]}`',f'- 최초 이유: {x[5]}','']
 p=HERE/'ADJUDICATION_NULL_FIX_PACK.md';atomic(p,'\n'.join(lines));print(f'NULL_FIX_PACK_READY coords={len(coords)}')
if __name__=='__main__':main()
