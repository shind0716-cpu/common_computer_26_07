from __future__ import annotations
import hashlib,json,os,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;PACK=HERE.parent/'PACK_M_meaning_2026-09-02.md'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic_text(p:Path,s:str)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(s,encoding='utf-8');os.replace(t,p)
def main()->None:
 text=PACK.read_text(encoding='utf-8');ms=list(re.finditer(r'^## (M-\d{3})\s*$',text,re.M));assert len(ms)==99
 header=text[:ms[0].start()];slice_text=header+text[ms[0].start():ms[14].start()]
 sp=HERE/'PACK_M_PREFIX_M001_M014.md';atomic_text(sp,slice_text)
 assert re.findall(r'^## (M-\d{3})\s*$',slice_text,re.M)==[f'M-{i:03d}' for i in range(1,15)]
 m80=header+text[ms[79].start():ms[80].start()]
 m80p=HERE/'PACK_M_ITEM_M080.md';atomic_text(m80p,m80)
 assert re.findall(r'^## (M-\d{3})\s*$',m80,re.M)==['M-080']
 raw=(HERE/'A_CLAUDE_MEANING_01_RAW.json').read_text(encoding='utf-8');start=raw.find('{"id":"M-015"');assert start>=0
 parsed=json.loads('{"items":['+raw[start:]);items=parsed['items'];assert [x['id'] for x in items]==[f'M-{i:03d}' for i in range(15,100)] and sum(len(x['cells']) for x in items)==510
 salvage={'schema':'pack_m_claude_salvage_v1','status':'DERIVED_VERBATIM_FROM_REJECTED_RAW','source_raw':'A_CLAUDE_MEANING_01_RAW.json','source_raw_sha256':sha(HERE/'A_CLAUDE_MEANING_01_RAW.json'),'start_marker':'M-015','items':items}
 atomic_text(HERE/'A_CLAUDE_MEANING_01_SALVAGED_M015_M099.json',json.dumps(salvage,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'status':'RECOVERY_INPUTS_READY','parent_sha256':sha(PACK),'slice_sha256':sha(sp),'slice_items':14,'m80_sha256':sha(m80p),'salvage_sha256':sha(HERE/'A_CLAUDE_MEANING_01_SALVAGED_M015_M099.json'),'salvage_items':85,'salvage_cells':510}))
if __name__=='__main__':main()
