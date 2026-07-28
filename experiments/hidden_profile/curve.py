"""용량-반응 곡선 — 미공유 팩트 k개일 때 정답률 (히든 프로필 v1)
목적: 단독 에이전트가 몇 개를 알아야 답이 뒤집히는지. 토론 결과 해석의 눈금.
      k=2(실제 배분)의 정답률 = 단독 기준선. 토론이 이걸 넘으면 그 초과분이 취합의 몫.
비용: 약 130콜. 기권 금지 조건 고정.
"""
import os, sys, json, io, re, time, random, itertools
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

KEY = os.environ["OPENAI_API_KEY"]
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")

issue = json.load(open(os.path.join(HERE, "data", "issue_hire.json"), encoding="utf-8"))
FACTS = json.load(open(os.path.join(HERE, "data", "facts_issue_hire_v1.json"), encoding="utf-8"))["facts"]
SHARED = [f for f in FACTS if f["share"] == "shared"]
UNSHARED = [f for f in FACTS if f["share"] == "unshared"]

PERSPECTIVE = {
    "개발": ["fact_hire_05", "fact_hire_06"],
    "공장": ["fact_hire_07", "fact_hire_08"],
    "인사": ["fact_hire_09", "fact_hire_10"],
    "재무": ["fact_hire_11", "fact_hire_12"],
}

SYSTEM = (
    "당신은 소규모 회사의 채용 결정에 참여하는 실무자입니다. "
    "주어진 상황과 정보만으로 판단하세요. 추측으로 없는 정보를 만들지 마세요. "
    "정보가 충분치 않더라도 반드시 둘 중 한 명을 골라야 합니다. 기권은 허용되지 않습니다.\n"
    "반드시 아래 JSON 한 개만 출력하세요. 다른 말은 쓰지 마세요.\n"
    '{"choice": "한도영" 또는 "유지완", "reason": "한 문장"}'
)

def build_user(fl):
    lines = [issue["body"], "", "질문: " + issue["question"], "", "당신이 알고 있는 정보:"]
    for f in fl:
        lines.append("- " + f["text"])
    return "\n".join(lines)

def call(user, temp=1.0):
    body = json.dumps({
        "model": MODEL, "max_completion_tokens": 300, "temperature": temp,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=body,
        headers={"content-type": "application/json", "authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    txt = d["choices"][0]["message"]["content"] or ""
    u = d.get("usage", {})
    m = re.search(r'\{.*\}', txt, re.S)
    choice = "파싱실패"
    if m:
        try:
            choice = json.loads(m.group(0)).get("choice", "?")
        except Exception:
            pass
    return choice, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)

rnd = random.Random(20260728)
N_RUN = 3
MAX_COMBO = 5
rows = []
tin = tout = 0

print("=== 용량-반응 곡선 (공유 4 고정 + 미공유 k개) ===")
for k in range(0, 9):
    allc = list(itertools.combinations(range(8), k))
    combos = allc if len(allc) <= MAX_COMBO else rnd.sample(allc, MAX_COMBO)
    picks = []
    for combo in combos:
        fl = SHARED + [UNSHARED[i] for i in combo]
        user = build_user(fl)
        for r in range(N_RUN):
            try:
                c, a, b = call(user)
                tin += a; tout += b
            except Exception as e:
                c = "에러:" + str(e)[:40]
            picks.append(c)
            rows.append({"cond": "curve", "k": k, "combo": [UNSHARED[i]["fact_id"] for i in combo],
                         "run": r + 1, "choice": c})
            time.sleep(0.3)
    ok = sum(1 for p in picks if p == "유지완")
    bar = "#" * int(round(20 * ok / len(picks)))
    print("k=%d  정답(유지완) %2d/%2d  %-20s" % (k, ok, len(picks), bar))

print("\n=== 실제 배분(k=2, 관점별) — 단독 기준선 ===")
for name, ids in PERSPECTIVE.items():
    fl = SHARED + [f for f in UNSHARED if f["fact_id"] in ids]
    user = build_user(fl)
    picks = []
    for r in range(5):
        try:
            c, a, b = call(user)
            tin += a; tout += b
        except Exception as e:
            c = "에러:" + str(e)[:40]
        picks.append(c)
        rows.append({"cond": "perspective", "k": 2, "combo": ids, "persp": name,
                     "run": r + 1, "choice": c})
        time.sleep(0.3)
    ok = sum(1 for p in picks if p == "유지완")
    print("%-4s 정답 %d/5   %s" % (name, ok, picks))

json.dump(rows, open(os.path.join(HERE, "curve_results.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n총 %d콜 | 토큰 in %d / out %d" % (len(rows), tin, tout))
