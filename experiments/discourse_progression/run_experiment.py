# -*- coding: utf-8 -*-
"""
담화 전진 가설 — 정식 검증 러너 (v0.2)
사전고정: PREREG_v0.2.md (이 파일의 PROMPTS/파라미터 상수가 문면 정본 — 실행 중 변경 금지)

사용법:
  set OPENAI_API_KEY=...   (Windows)  /  export OPENAI_API_KEY=... (mac/linux)
  set GEMINI_API_KEY=...
  python run_experiment.py all                # 생성 → 채점 → 안정성 → 분석 전체
  python run_experiment.py gen                # 생성만
  python run_experiment.py judge              # 채점(+안정성 재채점)만
  python run_experiment.py analyze            # 분석만 (API 호출 0)

  모델 지정(선택): --models gpt,gemini  (기본: 둘 다)
  모델 ID는 환경변수로 덮어쓰기: OPENAI_MODEL / GEMINI_MODEL / JUDGE_MODEL

의존성: requests 뿐 (pip install requests)
판단 = LLM(생성·채점), 집계 = 순수 계산(analyze) — 경계 분리 원칙.
"""
import os, sys, json, time, re, itertools
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("pip install requests 먼저 실행하세요.")

HERE = Path(__file__).parent
RESULTS = HERE / "results"

# ── .env 지원: 리포 루트의 .env를 읽어 환경변수로 (파이프라인과 동일한 단일 파일).
#    이미 설정된 환경변수는 덮지 않음. 이 폴더에 .env가 따로 있으면 그쪽이 우선.
def _load_dotenv():
    for fp in (HERE / ".env", HERE.parent.parent / ".env"):
        if not fp.exists():
            continue
        for line in fp.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

_load_dotenv()

# ── 고정 파라미터 (사전고정 v0.2 §2 — 변경 금지) ────────────────────────────
GEN_TEMPERATURE = 0.7
JUDGE_TEMPERATURE = 0.0
MAX_TOKENS = 1024
RUNS_PER_COND = 3          # 조건당 독립 런
ROUNDS = 3                 # 초기 1 + 라운드 3 = 텍스트 4개/런
CONDITIONS = ["A", "P", "B"]   # A=반복 강화, P=전진 강화(A′), B=자기반론 숙의
STABILITY_REJUDGE = 3      # P3용 재채점 횟수

MODELS = {
    "gpt":    {"provider": "openai", "model": os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
               "key_env": "OPENAI_API_KEY"},
    "gemini": {"provider": "gemini", "model": os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview"),
               "key_env": "GEMINI_API_KEY"},
}
# judge는 전 조건·전 모델에 대해 단일 고정 (사전고정 §3).
# 계정에서 상위 모델(gpt-5.4 등) 사용 가능해지면 JUDGE_MODEL만 올릴 것 — P3가 mini judge 신뢰도를 감시한다.
JUDGE_PROVIDER = "openai"
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gpt-5.4-mini")

# ── 픽스처 ──────────────────────────────────────────────────────────────────
ISSUE = json.loads((HERE / "fixtures" / "issue_esa.json").read_text(encoding="utf-8"))
FACTS = json.loads((HERE / "fixtures" / "facts_issue_esa.json").read_text(encoding="utf-8"))["facts"]
FACT_IDS = [f["fact_id"] for f in FACTS]

FACTS_BLOCK = "\n".join(f"- ({f['fact_id']}) {f['text']}" for f in FACTS)

# ── 프롬프트 문면 정본 (사전고정 v0.2 §4 — 변경 금지) ───────────────────────
BASE = (
    "다음 사안을 검토하라.\n\n[사안]\n" + ISSUE["body"] +
    "\n\n[알고 있는 사실 전체]\n" + FACTS_BLOCK +
    "\n\n너의 입장은 '집주인에게 알려야 한다(신고)'이다. 이 입장은 끝까지 유지한다.\n"
)

PROMPT_R0 = BASE + "\n위 사안에 대한 너의 입장을 밝히는 글을 한 문단으로 써라."

ROUND_INSTR = {
    "A": "지금까지 쓴 글을 참고해, 같은 입장을 더 설득력 있게 강화하는 새 글을 한 문단으로 써라.",
    "P": ("지금까지 쓴 글을 참고하되, 같은 입장을 유지하면서 이전 글에서 사용한 논거를 반복하지 말고 "
          "매번 새로운 논거로 강화하는 새 글을 한 문단으로 써라."),
    "B": ("지금까지 쓴 글을 참고해, 너의 입장에 대해 가장 강한 반론을 스스로 제기하고 진지하게 검토한 뒤, "
          "그 검토를 반영해 견해를 갱신한 글을 한 문단으로 써라."),
}

JUDGE_PROMPT = (
    "당신은 판정자다. 아래 팩트 각각에 대해, 주어진 글에 그 팩트가 언급되었는지 판정하라.\n"
    "- 패러프레이즈(같은 내용의 다른 표현)도 '언급'으로 인정한다.\n"
    "- 글에 그 내용이 실제로 담겨 있어야 한다. 문맥상 유추만 가능한 것은 '미언급'이다.\n\n"
    "[팩트 목록]\n" + FACTS_BLOCK + "\n\n[판정할 글]\n{text}\n\n"
    "출력은 다음 형식의 JSON 오브젝트 하나만, 다른 말 없이:\n"
    '{{"fact_esa_01": "mentioned", "fact_esa_02": "unmentioned", ...}} (12개 전부 포함)'
)

# ── API 호출 (재시도 + 파라미터 폴백, 실제 사용 파라미터 기록) ───────────────
def _post(url, headers, payload, tries=4):
    for i in range(tries):
        r = requests.post(url, headers=headers, json=payload, timeout=180)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 529) and i < tries - 1:
            time.sleep(5 * (i + 1)); continue
        raise RuntimeError(f"API {r.status_code}: {r.text[:400]}")
    raise RuntimeError("unreachable")

_OPENAI_MAXTOK = "max_tokens"  # 한 번 폴백하면 이후 호출은 처음부터 새 이름 사용

def call_openai(model, prompt, temperature, seed=None):
    global _OPENAI_MAXTOK
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("OPENAI_API_KEY 없음")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": temperature, _OPENAI_MAXTOK: MAX_TOKENS}
    if seed is not None:
        payload["seed"] = seed
    used = dict(payload); used.pop("messages")
    for _ in range(3):  # 신형 모델 파라미터 명 변화 폴백
        try:
            data = _post(url, headers, payload)
            text = data["choices"][0]["message"]["content"].strip()
            used["deviations"] = used.get("deviations", [])
            return text, used
        except RuntimeError as e:
            msg = str(e)
            if "max_tokens" in msg and "max_tokens" in payload:
                payload["max_completion_tokens"] = payload.pop("max_tokens")
                _OPENAI_MAXTOK = "max_completion_tokens"
                used.setdefault("deviations", []).append("max_tokens→max_completion_tokens")
                continue
            if "temperature" in msg and "temperature" in payload:
                payload.pop("temperature")
                used.setdefault("deviations", []).append("temperature 미지원 — 제거됨(보고서에 명기할 것)")
                continue
            raise

def call_gemini(model, prompt, temperature, seed=None):
    key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY 없음")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": temperature, "maxOutputTokens": MAX_TOKENS}}
    data = _post(url, {}, payload)
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini 응답 파싱 실패: {json.dumps(data)[:400]}")
    used = {"model": model, "temperature": temperature, "max_tokens": MAX_TOKENS,
            "seed": None, "deviations": ["gemini는 seed 미지원"]}
    return text, used

def call_model(provider, model, prompt, temperature, seed=None):
    if provider == "openai":
        return call_openai(model, prompt, temperature, seed)
    return call_gemini(model, prompt, temperature, seed)

# ── 생성 ────────────────────────────────────────────────────────────────────
def build_prompt(cond, history):
    if not history:
        return PROMPT_R0
    hist = "\n\n".join(f"[라운드 {i} 글]\n{t}" for i, t in enumerate(history))
    return BASE + "\n[지금까지 쓴 글]\n" + hist + "\n\n" + ROUND_INSTR[cond]

def cmd_gen(model_keys):
    for mk in model_keys:
        cfg = MODELS[mk]
        out = RESULTS / mk
        out.mkdir(parents=True, exist_ok=True)
        meta = {"model_key": mk, **cfg, "gen_temperature": GEN_TEMPERATURE,
                "max_tokens": MAX_TOKENS, "runs": RUNS_PER_COND, "rounds": ROUNDS,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "calls": []}
        for cond in CONDITIONS:
            for run in range(1, RUNS_PER_COND + 1):
                history = []
                for r in range(ROUNDS + 1):
                    fp = out / f"{cond}{run}_r{r}.txt"
                    if fp.exists():
                        history.append(fp.read_text(encoding="utf-8"))
                        print(f"[skip] {mk}/{cond}{run}_r{r} (이미 존재)")
                        continue
                    prompt = build_prompt(cond, history)
                    seed = 1000 * run + r  # openai만 적용
                    text, used = call_model(cfg["provider"], cfg["model"], prompt,
                                            GEN_TEMPERATURE, seed)
                    fp.write_text(text, encoding="utf-8")
                    meta["calls"].append({"file": fp.name, "params_used": used,
                                          "at": time.strftime("%H:%M:%S")})
                    history.append(text)
                    print(f"[gen] {mk}/{cond}{run}_r{r} ({len(text)}자)")
        meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        (out / "gen_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                           encoding="utf-8")

# ── 채점 ────────────────────────────────────────────────────────────────────
def parse_judge_json(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("judge 출력에서 JSON 미발견")
    obj = json.loads(m.group(0))
    out = {}
    for fid in FACT_IDS:
        v = str(obj.get(fid, "unmentioned")).lower()
        out[fid] = "mentioned" if "unmention" not in v and "mention" in v else "unmentioned"
    return out

def judge_text(text):
    raw, used = call_model(JUDGE_PROVIDER, JUDGE_MODEL,
                           JUDGE_PROMPT.format(text=text), JUDGE_TEMPERATURE)
    return parse_judge_json(raw), used

def cmd_judge(model_keys):
    for mk in model_keys:
        out = RESULTS / mk
        judgments = {}
        jf = out / "judgments.json"
        if jf.exists():
            judgments = json.loads(jf.read_text(encoding="utf-8"))
        for cond in CONDITIONS:
            for run in range(1, RUNS_PER_COND + 1):
                key = f"{cond}{run}"
                stages = judgments.get(key, [None] * (ROUNDS + 1))
                for r in range(ROUNDS + 1):
                    if stages[r] is not None:
                        continue
                    text = (out / f"{key}_r{r}.txt").read_text(encoding="utf-8")
                    verdict, _ = judge_text(text)
                    stages[r] = verdict
                    print(f"[judge] {mk}/{key}_r{r}: 생존 "
                          f"{sum(1 for v in verdict.values() if v == 'mentioned')}/12")
                    judgments[key] = stages
                    jf.write_text(json.dumps(judgments, ensure_ascii=False), encoding="utf-8")
        # P3 안정성: 이 모델에서 낙폭 최대 전이의 B런 라운드를 3회 재채점
        surv = {k: [sum(1 for v in st.values() if v == "mentioned") for st in sts]
                for k, sts in judgments.items()}
        b_drops = [(surv[k][r - 1] - surv[k][r], k, r)
                   for k in surv if k.startswith("B") for r in range(1, ROUNDS + 1)]
        drop, key, r = max(b_drops)
        sf = out / "stability.json"
        if not sf.exists():
            text = (out / f"{key}_r{r}.txt").read_text(encoding="utf-8")
            rejudges = []
            for i in range(STABILITY_REJUDGE):
                v, _ = judge_text(text)
                rejudges.append(v)
                print(f"[stability] {mk}/{key}_r{r} 재채점 {i+1}/{STABILITY_REJUDGE}")
            sf.write_text(json.dumps({"target": f"{key}_r{r}", "drop": drop,
                                      "original": judgments[key][r], "rejudges": rejudges},
                                     ensure_ascii=False, indent=1), encoding="utf-8")

# ── 분석 (순수 계산 — LLM 0) ────────────────────────────────────────────────
def ngrams(text, n=2):
    s = re.sub(r"\s+", "", text)
    return set(s[i:i + n] for i in range(len(s) - n + 1))

def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0

def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        ranks = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        return ranks
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0

def analyze_model(mk):
    out = RESULTS / mk
    judgments = json.loads((out / "judgments.json").read_text(encoding="utf-8"))
    surv, transitions = {}, []
    for key, stages in judgments.items():
        surv[key] = [sum(1 for v in st.values() if v == "mentioned") for st in stages]
        for r in range(1, ROUNDS + 1):
            prev, cur = stages[r - 1], stages[r]
            deaths = sum(1 for fid in FACT_IDS
                         if prev[fid] == "mentioned" and cur[fid] == "unmentioned")
            t_prev = (out / f"{key}_r{r-1}.txt").read_text(encoding="utf-8")
            t_cur = (out / f"{key}_r{r}.txt").read_text(encoding="utf-8")
            prog = 1 - jaccard(ngrams(t_prev), ngrams(t_cur))
            transitions.append({"run": key, "r": r, "prog": round(prog, 4), "deaths": deaths})
    minA = [min(surv[k]) for k in surv if k.startswith("A")]
    minP = [min(surv[k]) for k in surv if k.startswith("P")]
    p1_gap = sum(minA) / len(minA) - sum(minP) / len(minP)
    p1 = p1_gap >= 1
    b_recover = sum(1 for k in surv if k.startswith("B") and min(surv[k]) < surv[k][-1])
    p2 = b_recover >= 2
    stab = json.loads((out / "stability.json").read_text(encoding="utf-8"))
    maj = {fid: max(("mentioned", "unmentioned"),
                    key=lambda s: sum(1 for rj in stab["rejudges"] if rj[fid] == s))
           for fid in FACT_IDS}
    agree = [sum(1 for fid in FACT_IDS if rj[fid] == maj[fid]) for rj in stab["rejudges"]]
    p3 = min(agree) >= 10
    progs = [t["prog"] for t in transitions]
    deaths = [t["deaths"] for t in transitions]
    rho = spearman(progs, deaths)
    med = sorted(progs)[len(progs) // 2]
    hi = [d for p, d in zip(progs, deaths) if p >= med]
    lo = [d for p, d in zip(progs, deaths) if p < med]
    p5 = rho > 0 and (sum(hi) / len(hi)) > (sum(lo) / len(lo))
    return {"model": mk, "surv": surv, "transitions": transitions,
            "P1": {"minA": minA, "minP": minP, "gap": round(p1_gap, 2), "pass": p1},
            "P2": {"recovered": b_recover, "pass": p2},
            "P3": {"target": stab["target"], "agree": agree, "pass": p3},
            "P5": {"rho": round(rho, 4), "hi_mean": round(sum(hi) / len(hi), 2),
                   "lo_mean": round(sum(lo) / len(lo), 2), "pass": p5}}

def cmd_analyze(model_keys):
    results = [analyze_model(mk) for mk in model_keys]
    n_p1 = sum(1 for r in results if r["P1"]["pass"])
    verdict = {2: "완전 복제 — 보고서 v1 승격 요건 충족",
               1: "부분 복제 — 전진 효과는 모델 의존적(그대로 보고, 침묵 금지)",
               0: "미재현 — 데모 결과를 소넷 한정으로 강등"}[n_p1] \
        if len(results) == 2 else f"P1 성립 {n_p1}/{len(results)} 모델"
    combined = {"models": results, "R1_replication": {"p1_pass_models": n_p1,
                "verdict": verdict}}
    (RESULTS / "analysis.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in results:
        print(f"\n== {r['model']} ==")
        for k in sorted(r["surv"]):
            print(f"  {k}: {r['surv'][k]}")
        for p in ("P1", "P2", "P3", "P5"):
            print(f"  {p}: {'성립' if r[p]['pass'] else '불성립'}  {r[p]}")
    print(f"\n[R1 복제 판정] {verdict}")
    print("→ results/analysis.json 저장 완료")

# ── 스모크: 키·모델ID·파라미터·judge 파싱만 확인 (모델당 호출 2회, 산출물 없음) ──
def cmd_smoke(model_keys):
    ok = True
    for mk in model_keys:
        cfg = MODELS[mk]
        if not os.environ.get(cfg["key_env"]):
            print(f"[smoke] {mk}: {cfg['key_env']} 없음 — 건너뜀"); ok = False; continue
        try:
            text, used = call_model(cfg["provider"], cfg["model"],
                                    "한 문장으로 자기소개를 해라.", GEN_TEMPERATURE, seed=1)
            print(f"[smoke] {mk} 생성 OK ({cfg['model']}): {text[:40]}...")
            if used.get("deviations"):
                print(f"        파라미터 조정: {used['deviations']}")
        except Exception as e:
            print(f"[smoke] {mk} 생성 실패: {e}"); ok = False
    try:
        v, _ = judge_text("임대차 계약에 반려동물 금지 조항이 있고, 위반 시 보증금 500달러가 몰수된다.")
        n = sum(1 for s in v.values() if s == "mentioned")
        print(f"[smoke] judge OK ({JUDGE_MODEL}): 12팩트 중 {n}개 언급 판정 (기대: 2 안팎)")
    except Exception as e:
        print(f"[smoke] judge 실패: {e}"); ok = False
    print("[smoke] 전부 통과 — 본 실행 준비 완료" if ok else "[smoke] 실패 항목 있음 — .env 확인")

# ── main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "all"
    mks = list(MODELS)
    if "--models" in args:
        mks = args[args.index("--models") + 1].split(",")
    for mk in mks:
        if mk not in MODELS:
            sys.exit(f"알 수 없는 모델 키: {mk} (가능: {list(MODELS)})")
    print(f"모델: {[(m, MODELS[m]['model']) for m in mks]} / judge: {JUDGE_MODEL}")
    if cmd == "smoke":
        cmd_smoke(mks); sys.exit(0)
    if cmd in ("gen", "all"):
        cmd_gen(mks)
    if cmd in ("judge", "all"):
        cmd_judge(mks)
    if cmd in ("analyze", "all"):
        cmd_analyze(mks)
