from __future__ import annotations
import copy,json,os,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];INFRA=ROOT/'experiments/pressure_category/coderpacks_all11_gpt_20260901';sys.path.insert(0,str(INFRA))
from isolated_launcher import launch,sol_adapter
import validate_turn as V
RAW=HERE/'B_SOL_TURN_01_RAW.json';OUT=HERE/'B_SOL_TURN_01_CORRECTED.json';RECEIPT=HERE/'B_SOL_TURN_01_CORRECTION_RECEIPT.json'
COORDS=[('T-15','answer_evidence_after'),('T-16','answer_evidence_before'),('T-16','principle_evidence_after'),('T-17','answer_evidence_before'),('T-17','principle_evidence_after'),('T-17','answer_evidence_after'),('T-18','principle_evidence_before'),('T-18','answer_evidence_before'),('T-18','principle_evidence_after')]
def main():
 if OUT.exists() or RECEIPT.exists():raise RuntimeError('refusing overwrite')
 raw=json.loads(RAW.read_text(encoding='utf-8'));ss=V.sections(V.PACK.read_text(encoding='utf-8'));base=Path(tempfile.mkdtemp(prefix='coder-turn-quote-correction-'))
 src=base/'FAILED_SOURCE.txt';prompt=base/'prompt.txt';src.write_text('\n\n'.join(ss[x] for x in ('T-15','T-16','T-17','T-18')),encoding='utf-8')
 prompt.write_text('''당신은 B_SOL_TURN_01의 구조 교정 전용 세션입니다. ORIGINAL_JSON의 의미 판정과 모든 값은 보존하고, 아래 9개 evidence 값만 각 항목의 지정된 앞/뒤 수첩에 실제 존재하는 300자 이하 exact substring으로 바꾸십시오. 다른 값은 하나도 바꾸지 마십시오. 완전한 JSON 객체 하나만 반환하고 설명과 Markdown fence는 금지합니다.\n승인 좌표: '''+json.dumps(COORDS,ensure_ascii=False)+'\nORIGINAL_JSON\n'+json.dumps(raw,ensure_ascii=False),encoding='utf-8')
 launch(sol_adapter(),src,prompt,OUT,RECEIPT)
 cor=json.loads(OUT.read_text(encoding='utf-8'));rest=copy.deepcopy(cor);rmap={x['id']:x for x in raw['items']};cmap={x['id']:x for x in rest['items']};changed=[]
 for iid,f in COORDS:
  if cmap[iid][f]!=rmap[iid][f]:changed.append((iid,f))
  cmap[iid][f]=rmap[iid][f]
 if rest!=raw:raise ValueError('correction changed fields outside approved coordinates')
 if set(changed)!=set(COORDS):raise ValueError(f'not all approved failed quotes changed: {changed}')
 V.validate(cor,'B_SOL_TURN_01')
 st=json.loads((HERE/'HARD_STOP_STATUS.json').read_text(encoding='utf-8'));st.update(status='CORRECTED_ACCEPTED',attempted_semantic_launches=3,accepted_first_pass_outputs=2,private_key_released=False,correction={'scope':[f'{i}/{f}' for i,f in COORDS],'corrected_output_sha256':V.digest(OUT),'receipt_sha256':V.digest(RECEIPT)},next_gate='Compare validated outputs; keep key sealed.')
 tmp=HERE/'HARD_STOP_STATUS.json.tmp';tmp.write_text(json.dumps(st,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,HERE/'HARD_STOP_STATUS.json')
 print(f'TURN_SOL_CORRECTION_VALID sha256={V.digest(OUT)} bundle={base}')
if __name__=='__main__':main()
