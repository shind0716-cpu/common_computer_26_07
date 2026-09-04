"""gpt·gemini 라벨 210판 정성 판독용 읽기 팩 (2026-09-03). qualpacks_20260903/build_packs.py 와 같은 형식, 라벨 판만."""
import json, glob, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); PC = os.path.dirname(HERE); os.chdir(PC)
M11 = json.load(open('coderpacks_haiku_llm_20260902/MATERIALS11.json', encoding='utf-8'))
GATE = json.load(open('LABEL_GATE_models_2026-09-03.json', encoding='utf-8'))
J = {}
for r in json.load(open('coderpacks_label_models_20260903/JUDGED_label_models_rows.json', encoding='utf-8')):
    J[(r['model'], r['issue'], r['run'])] = r
def cond_label(d):
    s = d['script']; vs = d.get('value_set')
    press = '압박 없음' if s == 'C0' else '반대편 압박(관문에서 이 라벨의 다수 답 반대쪽을 밈)'
    kind = '라벨 "나는 보수주의자다"' if vs.startswith('lcons') else '라벨 "나는 진보주의자다"'
    return press, kind
def run_block(m, d):
    press, kind = cond_label(d)
    j = J.get((m, d['issue_id'], d['run_id'])); jl = ''
    if j: jl = f"\n- 정량 채점(소넷, 참고): 분류={j.get('cls')} · 글 입장={j.get('stance')} · 마지막 답={j.get('final')} · 수첩 사실 수(있음) r0/r1/r2={j.get('n_alive')}"
    own = j.get('own') if j else None
    out = [f"\n\n## RUN {d['run_id']}  [{m} · {d['issue_id']}]",
           f"- 조건: {press} · {kind} · rep{d.get('rep')}",
           f"- 문장 원문: {d.get('value_statement')}",
           f"- 이 라벨이 관문(압박 없음 3반복)에서 낸 다수 답: {own or '(관문에서 두 라벨이 같은 답 — 갈리지 않음)'}",
           f"- 상대 대본(라운드 1~3 반복): {d.get('script_line')}" + jl]
    E = d.get('essays', []); N = d.get('notes', [])
    for i in range(4):
        if i < len(E): out.append(f"\n### 라운드 {i} 글\n{E[i].strip()}")
        if i < len(N): out.append(f"\n### 수첩 r{i} (다음 라운드로 넘어가는 유일한 기억, 500자)\n{N[i].strip()}")
    out.append(f"\n### 마지막 답 (압박 없이, 문장+수첩만 보고): {d.get('final_poll')}")
    return '\n'.join(out)
def issue_header(iid):
    mat = M11[iid]
    lines = [f"\n\n# 시나리오 {iid}", f"선택지: {mat['options'][0]} / {mat['options'][1]}", "사실 12개 (항목 · 내용 · 편드는 선택지):"]
    for f in mat['facts']: lines.append(f"  - [{f['id']}] {f['category']} · {f['text']} · → {f['favors']}")
    return '\n'.join(lines)
plan = {'gpt': [['issue_childcare','issue_euthanasia','issue_examaccom','issue_remotewatch'],['issue_workmind','issue_recycling_room','issue_smoking_area_party','issue_cat_feeding_days_list'],['issue_eol','issue_shelter','issue_parentalreturn']],
        'gemini-flash': [['issue_childcare','issue_euthanasia','issue_examaccom','issue_remotewatch'],['issue_workmind','issue_recycling_room','issue_smoking_area_party','issue_cat_feeding_days_list'],['issue_eol','issue_shelter','issue_parentalreturn']]}
for m, groups in plan.items():
    for gi, issues in enumerate(groups, 1):
        name = f"{HERE}/{m}_lpack{gi}.md"
        parts = [f"# 읽기 팩 {m} 라벨 #{gi} — 시나리오 {len(issues)}개", "이 팩의 판은 모두 라벨 한 문장(\"나는 보수주의자다\" / \"나는 진보주의자다\")을 받은 판이다. 가치 문장(항목 3개)은 없다.", "각 판(RUN)은 라운드 0~3 글 + 수첩 3장 + 마지막 답. 수첩에 안 적은 사실은 다음 라운드에 없다."]
        n = 0
        for iid in issues:
            parts.append(issue_header(iid))
            files = [f for f in sorted(glob.glob(f'runs/{m}/{iid}/run_*_l[cp]*_rep?.json')) if ('/run_C0_' in f or '/run_px' in f)]
            files.sort(key=lambda f: (0 if '_C0_' in f else 1, os.path.basename(f)))
            for f in files:
                d = json.load(open(f, encoding='utf-8')); parts.append(run_block(m, d)); n += 1
        txt = '\n'.join(parts); open(name, 'w', encoding='utf-8').write(txt)
        print(name.split('/')[-1], n, len(txt))
