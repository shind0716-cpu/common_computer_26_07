from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901'; sys.path.insert(0,str(INFRA))
from isolated_launcher import launch, sol_adapter
import validate_use as V

RAW=HERE/'B_SOL_USE_01_RAW.json'; OUT=HERE/'B_SOL_USE_01_CORRECTED.json'; RECEIPT=HERE/'B_SOL_USE_01_CORRECTION_RECEIPT.json'
FIELDS=('purpose_evidence','rebuildability_evidence')

def main():
 if OUT.exists() or RECEIPT.exists(): raise RuntimeError('refusing to overwrite correction artifacts')
 original=json.loads(RAW.read_text(encoding='utf-8'))
 sections=V.source_sections(V.PACK.read_text(encoding='utf-8')); u20=sections['U-20']
 base=Path(tempfile.mkdtemp(prefix='coder-use-u20-correction-'))
 source=base/'U20_SOURCE.txt'; prompt=base/'prompt.txt'
 source.write_text(u20,encoding='utf-8')
 prompt.write_text('''당신은 B_SOL_USE_01의 구조 교정 전용 세션입니다. 아래 ORIGINAL_JSON은 보존된 당신의 첫 판독입니다. U-20의 purpose_evidence와 rebuildability_evidence 두 값만 item-local 수첩의 정확한 부분문자열로 바꾸십시오. 의미 등급, rationale, confidence, 다른 33개 항목과 U-20의 나머지 값은 하나도 바꾸지 마십시오. 완전한 JSON 객체 하나만 반환하고 Markdown fence나 설명은 금지합니다. 열쇠·다른 코더 출력은 제공되지 않았습니다.\n\nORIGINAL_JSON\n'''+json.dumps(original,ensure_ascii=False),encoding='utf-8')
 launch(sol_adapter(),source,prompt,OUT,RECEIPT)
 corrected=json.loads(OUT.read_text(encoding='utf-8'))
 # Only two coordinates may differ; reject any semantic or collateral change.
 restored=copy.deepcopy(corrected); oi=next(x for x in original['items'] if x['id']=='U-20'); ci=next(x for x in restored['items'] if x['id']=='U-20')
 for field in FIELDS: ci[field]=oi[field]
 if restored!=original: raise ValueError('correction changed fields outside the two approved coordinates')
 if all(next(x for x in corrected['items'] if x['id']=='U-20')[f]==oi[f] for f in FIELDS): raise ValueError('correction changed neither failed quote')
 V.validate(corrected, expected_coder='B_SOL_USE_01')
 status=json.loads((HERE/'HARD_STOP_STATUS.json').read_text(encoding='utf-8'))
 status.update(status='CORRECTED_ACCEPTED',attempted_semantic_launches=3,accepted_first_pass_outputs=2,rejected_first_pass_outputs=1,
               private_key_released=False,correction={'coder_id':'B_SOL_USE_01','scope':['U-20/purpose_evidence','U-20/rebuildability_evidence'],
               'corrected_output_sha256':V.digest(OUT),'receipt_sha256':V.digest(RECEIPT)},next_gate='Compare validated outputs; keep key sealed.')
 tmp=HERE/'HARD_STOP_STATUS.json.tmp'; tmp.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.replace(tmp,HERE/'HARD_STOP_STATUS.json')
 print(f'SOL_CORRECTION_VALID sha256={V.digest(OUT)} bundle={base}')
if __name__=='__main__': main()
