from __future__ import annotations
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
import validate_path as V
import verify_prekey
HERE=Path(__file__).resolve().parent
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,o:object)->None:
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def main()->None:
 out=HERE/'PACK_P_FREEZE.json'
 if out.exists():raise RuntimeError('refusing overwrite')
 if any((HERE/n).exists() for n in ('PACK_P_KEYED.json','KEYED_SUMMARY.json','FINAL_MANIFEST.json')):raise RuntimeError('key-derived artifact exists before freeze')
 r=verify_prekey.verify();freeze={'schema':'pack_p_prekey_freeze_v1','created_at':datetime.now(timezone.utc).isoformat(),'pack_sha256':V.digest(V.PACK),'consensus_sha256':r['consensus_sha256'],'closure':r['files'],'closure_count':len(r['files']),'key_opened':False,'key_artifact_included':False,'key_join_status':'NOT_STARTED'};atomic(out,freeze);print(f'PACK_P_FROZEN closure={len(r["files"])} freeze_sha256={sha(out)}')
if __name__=='__main__':main()
