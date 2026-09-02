from __future__ import annotations
import json,os
from pathlib import Path
import validate_meaning as V
import validate_meaning_v2 as W
import validate_recovery as R
HERE=Path(__file__).resolve().parent
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main()->None:
 prefix=json.loads((HERE/'A_CLAUDE_MEANING_PREFIX_03_RAW.json').read_text(encoding='utf-8'));R.validate_prefix(prefix)
 salvage=json.loads((HERE/'A_CLAUDE_MEANING_01_SALVAGED_M015_M099.json').read_text(encoding='utf-8'));assert salvage['source_raw_sha256']==V.digest(HERE/'A_CLAUDE_MEANING_01_RAW.json')
 pitems=[{'id':iid,'cells':[{'category':c,'grade':g,'evidence':e,'missing_detail':m} for c,g,e,m in cells]} for iid,cells in prefix['items']]
 a={'pack':'PACK_M','coder_id':'A_CLAUDE_MEANING_COMPOSITE_01_03','instruction_version':'20260902-meaning-v1','independent':True,'key_access':False,'source_path':V.PACK.name,'source_sha256':V.digest(V.PACK),'items':pitems+salvage['items']};V.validate(a,'A_CLAUDE_MEANING_COMPOSITE_01_03');ap=HERE/'A_CLAUDE_MEANING_COMPOSITE_01_03.json';atomic(ap,a)
 fix=json.loads((HERE/'B_SOL_MEANING_02_QUOTE_FIX_RAW.json').read_text(encoding='utf-8'));corrected=R.validate_sol_fix(fix);bp=HERE/'B_SOL_MEANING_02_CORRECTED.json';atomic(bp,corrected)
 expanded=W.expand(corrected);expanded['coder_id']='B_SOL_MEANING_02_CORRECTED';V.validate(expanded,'B_SOL_MEANING_02_CORRECTED');be=HERE/'B_SOL_MEANING_02_EXPANDED.json';atomic(be,expanded)
 provenance={'schema':'pack_m_assembly_manifest_v1','status':'ASSEMBLED_VALID','key_access':False,'claude':{'method':'M001-M014 fresh prefix supplement + verbatim parsed M015-M099 suffix from rejected raw','prefix_raw_sha256':V.digest(HERE/'A_CLAUDE_MEANING_PREFIX_03_RAW.json'),'rejected_raw_sha256':V.digest(HERE/'A_CLAUDE_MEANING_01_RAW.json'),'salvage_sha256':V.digest(HERE/'A_CLAUDE_MEANING_01_SALVAGED_M015_M099.json'),'assembled_sha256':V.digest(ap),'items':99,'cells':594},'sol':{'method':'two approved evidence coordinates replaced; all other values deep-identical','raw_sha256':V.digest(HERE/'B_SOL_MEANING_02_RAW.json'),'fix_raw_sha256':V.digest(HERE/'B_SOL_MEANING_02_QUOTE_FIX_RAW.json'),'corrected_sha256':V.digest(bp),'expanded_sha256':V.digest(be),'items':99,'cells':594}}
 atomic(HERE/'ASSEMBLY_MANIFEST.json',provenance);print(f"PACK_M_ASSEMBLED claude={V.digest(ap)} sol={V.digest(be)} cells=594+594 key_access=false")
if __name__=='__main__':main()
