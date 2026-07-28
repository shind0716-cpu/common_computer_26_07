"""히든 프로필 시나리오 온전성 검사 (v0)
목적: 토론 러너를 만들기 전에 시나리오 자체가 작동하는지 확인.
  - ceiling : 12팩트 전부 -> 유지완이 나와야 함 (안 나오면 난이도 문제)
  - trap    : 공유 4팩트만 -> 한도영이 나와야 함 (안 나오면 함정 미작동)
  - blind   : 팩트 없음 -> 판단 불가/무작위여야 함 (모델 prior 확인)
비용: 3조건 x n회 x 모델수. 기본 3x3x2 = 18콜.
"""
import os, sys, json, io, re, time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

def load_env():
    p = os.path.join(ROOT, ".env")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env()
KEY = os.environ.get("OPENAI_API_KEY", "")
if not KEY:
    print("OPENAI_API_KEY 없음"); sys.exit(1)

FACTS_FILE = os.environ.get("HP_FACTS", "facts_issue_hire_v1.json")
issue = json.load(open(os.path.join(HERE, "data", "issue_hire.json"), encoding="utf-8"))
facts = json.load(open(os.path.join(HERE, "data", FACTS_FILE), encoding="utf-8"))["facts"]
SHARED = [f for f in facts if f["share"] == "shared"]
print("facts file:", FACTS_FILE, "| shared", len(SHARED), "| total", len(facts))

SYSTEM = (
    "당신은 소규모 회사의 채용 결정에 참여하는 실무자입니다. "
    "주어진 상황과 정보만으로 판단하세요. 추측으로 없는 정보를 만들지 마세요. "
    "반드시 아래 JSON 한 개만 출력하세요. 다른 말은 쓰지 마세요.\n"
    '{"choice": "한도영" 또는 "유지완" 또는 "판단불가", "reason": "한 문장"}'
)

FORCE = os.environ.get("HP_FORCE", "") == "1"
if FORCE:
    SYSTEM = (
        "당신은 소규모 회사의 채용 결정에 참여하는 실무자입니다. "
        "주어진 상황과 정보만으로 판단하세요. 추측으로 없는 정보를 만들지 마세요. "
        "정보가 충분치 않더라도 반드시 둘 중 한 명을 골라야 합니다. 기권은 허용되지 않습니다.\n"
        "반드시 아래 JSON 한 개만 출력하세요. 다른 말은 쓰지 마세요.\n"
        '{"choice": "한도영" 또는 "유지완", "reason": "한 문장"}'
    )

def build_user(fact_list):
    lines = [issue["body"], "", "질문: " + issue["question"], ""]
    if fact_list:
        lines.append("당신이 알고 있는 정보:")
        for f in fact_list:
            lines.append("- " + f["text"])
    else:
        lines.append("(후보 개인에 대해 당신이 아는 정보는 없습니다.)")
    return "\n".join(lines)

def call(model, user, temp=1.0):
    body = json.dumps({
        "model": model,
        "max_completion_tokens": 300,
        "temperature": temp,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=body,
        headers={"content-type": "application/json",
                 "authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    txt = d["choices"][0]["message"]["content"] or ""
    u = d.get("usage", {})
    return txt, {"input_tokens": u.get("prompt_tokens", 0),
                 "output_tokens": u.get("completion_tokens", 0)}

def parse(txt):
    m = re.search(r'\{.*\}', txt, re.S)
    if not m:
        return "파싱실패", txt[:80]
    try:
        o = json.loads(m.group(0))
        return o.get("choice", "?"), o.get("reason", "")
    except Exception:
        return "파싱실패", txt[:80]

CONDS = [
    ("ceiling", facts,  "유지완"),
    ("trap",    SHARED, "한도영"),
    ("blind",   [],     "판단불가"),
]
MODELS = [os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3

results = []
tot_in = tot_out = 0
for model in MODELS:
    for name, fl, expect in CONDS:
        user = build_user(fl)
        picks = []
        for i in range(N):
            try:
                txt, usage = call(model, user)
                tot_in += usage.get("input_tokens", 0)
                tot_out += usage.get("output_tokens", 0)
                choice, reason = parse(txt)
            except Exception as e:
                choice, reason = "에러", str(e)[:80]
            picks.append(choice)
            results.append({"model": model, "cond": name, "run": i + 1,
                            "choice": choice, "expect": expect, "reason": reason})
            time.sleep(0.4)
        hit = sum(1 for p in picks if p == expect)
        print("%-28s %-8s -> %s  (기대 %s, 일치 %d/%d)" % (model, name, picks, expect, hit, N))

out = os.path.join(HERE, "sanity_results.json")
json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n토큰: in %d / out %d" % (tot_in, tot_out))
print("저장:", out)
