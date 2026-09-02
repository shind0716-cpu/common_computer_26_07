from __future__ import annotations
import re
from pathlib import Path
HERE=Path(__file__).resolve().parent;PACK=HERE.parent/'PACK_P_path_2026-09-02.md'
def ids_in(text:str)->list[str]:return re.findall(r'^## (P-\d{2})\s*$',text,re.M)
def build_texts()->tuple[str,str]:
 text=PACK.read_text(encoding='utf-8');matches=list(re.finditer(r'^## P-\d{2}\s*$',text,re.M));prefix=text[:matches[0].start()];sections=[]
 for i,m in enumerate(matches):sections.append(text[m.start():matches[i+1].start() if i+1<len(matches) else len(text)])
 return prefix+''.join(sections[:21]),prefix+''.join(sections[21:42])
def main()->None:
 a,b=build_texts();targets=[(HERE/'PACK_P_PREFIX_P01_P21.md',a),(HERE/'PACK_P_PREFIX_P22_P42.md',b)]
 for p,t in targets:
  if p.exists():raise RuntimeError(f'refusing overwrite: {p.name}')
  p.write_text(t,encoding='utf-8')
 print(f'PACK_P_RECOVERY_INPUTS first={len(ids_in(a))} second={len(ids_in(b))}')
if __name__=='__main__':main()
