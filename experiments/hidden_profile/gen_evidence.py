"""증거 HTML 생성기 — 히든 프로필 온전성 검사 v0
입력: sanity_results_v1_forced_n10.json, sanity_results_v1_optout.json, curve_results.json
출력: evidence_hidden_profile.html (자기완결·오프라인)
"""
import json, os, io, sys, html
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
H = os.path.dirname(os.path.abspath(__file__))

def L(name):
    return json.load(open(os.path.join(H, name), encoding="utf-8"))

forced = L("sanity_results_v1_forced_n10.json")
optout = L("sanity_results_v1_optout.json")
curve = L("curve_results.json")
facts = L(os.path.join("data", "facts_issue_hire_v1.json"))["facts"]
issue = L(os.path.join("data", "issue_hire.json"))

def rate(rows, cond, target="유지완"):
    g = [r for r in rows if r["cond"] == cond]
    return sum(1 for r in g if r["choice"] == target), len(g)

CONDS = [("ceiling", "12팩트 전부", "유지완"), ("trap", "공유 4개만", "한도영"),
         ("blind", "팩트 0", "—")]
CK = {}
for k in range(9):
    g = [r for r in curve if r["cond"] == "curve" and r["k"] == k]
    CK[k] = (sum(1 for r in g if r["choice"] == "유지완"), len(g))
PERSP = {}
for r in curve:
    if r["cond"] == "perspective":
        PERSP.setdefault(r["persp"], []).append(r["choice"])

CSS = """
body{font-family:'Malgun Gothic',system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:28px 20px;
background:#faf9f6;color:#26251f;line-height:1.65}
h1{font-size:24px;font-weight:500;margin:0 0 4px}h2{font-size:18px;font-weight:500;margin:34px 0 10px;
border-bottom:1px solid #ddd;padding-bottom:6px}h3{font-size:15px;font-weight:500;margin:20px 0 6px}
.sub{color:#6b6a63;font-size:13px;margin-bottom:22px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}
.card{flex:1;min-width:190px;border:1px solid #ddd;border-radius:10px;padding:14px;background:#fff}
.card .n{font-size:26px;font-weight:500}
.ok{color:#0f6e56}.bad{color:#a32d2d}.mid{color:#854f0b}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
th,td{border:1px solid #e2e0d8;padding:7px 9px;text-align:left;vertical-align:top}
th{background:#f1efe8;font-weight:500}
.q{font-size:12.5px;color:#3d3d3a}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;border:1px solid}
.t-y{color:#0f6e56;border-color:#9fe1cb;background:#e1f5ee}
.t-h{color:#a32d2d;border-color:#f7c1c1;background:#fcebeb}
.t-n{color:#5f5e5a;border-color:#d3d1c7;background:#f1efe8}
.note{background:#fff;border-left:3px solid #b4b2a9;padding:10px 14px;font-size:13px;margin:12px 0}
code{background:#f1efe8;padding:1px 5px;border-radius:3px;font-size:12px}
"""

def bar_svg():
    rows = []
    for i, (c, label, exp) in enumerate(CONDS):
        y_ok, y_n = rate(forced, c)
        pct = 100.0 * y_ok / y_n if y_n else 0
        yy = 40 + i * 62
        w = max(2, pct * 5.4)
        col = "#1D9E75" if c == "ceiling" else ("#E24B4A" if c == "trap" else "#888780")
        rows.append(
            '<text x="0" y="%d" font-size="13" fill="#26251f">%s</text>'
            '<rect x="150" y="%d" width="%.1f" height="20" fill="%s" rx="3"/>'
            '<text x="%.1f" y="%d" font-size="12" fill="#6b6a63">%d%% (유지완 %d/%d)</text>'
            % (yy + 15, label, yy, w, col, 156 + w, yy + 15, round(pct), y_ok, y_n))
    return ('<svg viewBox="0 0 720 230" width="100%%" style="max-width:720px">'
            '<text x="0" y="16" font-size="12" fill="#6b6a63">정답(유지완) 선택률 — 기권 금지 조건, n=10</text>'
            '%s<line x1="150" y1="30" x2="150" y2="220" stroke="#ddd"/></svg>' % "".join(rows))

def curve_svg():
    pts, bars = [], []
    for k in range(9):
        ok, n = CK[k]
        pct = 100.0 * ok / n if n else 0
        x = 60 + k * 72
        y = 190 - pct * 1.5
        pts.append("%d,%.1f" % (x, y))
        bars.append('<circle cx="%d" cy="%.1f" r="4" fill="#534AB7"/>'
                    '<text x="%d" y="%.1f" font-size="11" fill="#6b6a63" text-anchor="middle">%d%%</text>'
                    '<text x="%d" y="208" font-size="11" fill="#6b6a63" text-anchor="middle">%d</text>'
                    % (x, y, x, y - 10, round(pct), x, k))
    return ('<svg viewBox="0 0 700 240" width="100%%" style="max-width:700px">'
            '<text x="0" y="14" font-size="12" fill="#6b6a63">미공유 팩트 k개일 때 정답률 — k당 5조합 x 3회 (표본 부족, 해석 유보)</text>'
            '<line x1="50" y1="190" x2="660" y2="190" stroke="#ddd"/>'
            '<line x1="50" y1="40" x2="50" y2="190" stroke="#ddd"/>'
            '<polyline points="%s" fill="none" stroke="#534AB7" stroke-width="1.5"/>%s'
            '<text x="350" y="228" font-size="11" fill="#6b6a63" text-anchor="middle">보유한 미공유 팩트 수 k</text></svg>'
            % (" ".join(pts), "".join(bars)))

def tag(c):
    cls = "t-y" if c == "유지완" else ("t-h" if c == "한도영" else "t-n")
    return '<span class="tag %s">%s</span>' % (cls, html.escape(str(c)))

def log_table(rows, cond):
    out = ['<table><tr><th style="width:44px">#</th><th style="width:82px">선택</th><th>모델이 밝힌 이유</th></tr>']
    i = 0
    for r in rows:
        if r["cond"] != cond:
            continue
        i += 1
        out.append('<tr><td>%d</td><td>%s</td><td class="q">%s</td></tr>'
                   % (i, tag(r["choice"]), html.escape(r.get("reason", ""))))
    out.append("</table>")
    return "".join(out)

def facts_table():
    out = ['<table><tr><th>구분</th><th>ID</th><th>내용</th><th>요건</th><th>유리</th></tr>']
    for f in facts:
        sh = "공유" if f["share"] == "shared" else "미공유"
        out.append('<tr><td>%s</td><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>'
                   % (sh, f["fact_id"][-2:], html.escape(f["text"]),
                      f.get("requirement") or "—", f.get("favors") or "—"))
    out.append("</table>")
    return "".join(out)

c_ok, c_n = rate(forced, "ceiling")
t_h, t_n = rate(forced, "trap", "한도영")
b_h, b_n = rate(forced, "blind", "한도영")
p_ok = sum(1 for v in PERSP.values() for c in v if c == "유지완")
p_n = sum(len(v) for v in PERSP.values())

persp_rows = "".join(
    '<tr><td>%s</td><td>요건 %s 양쪽</td><td>%s</td><td>%s</td></tr>'
    % (n, {"개발": "①", "공장": "②", "인사": "③", "재무": "④"}[n],
       "".join(tag(c) for c in v),
       '<b class="%s">%d/%d</b>' % ("ok" if sum(1 for c in v if c == "유지완") else "bad",
                                    sum(1 for c in v if c == "유지완"), len(v)))
    for n, v in PERSP.items())

HTML = """<!doctype html><html lang="ko"><meta charset="utf-8">
<title>히든 프로필 온전성 검사 — 증거</title><style>%s</style>
<h1>히든 프로필 시나리오 온전성 검사 — 증거 자료</h1>
<div class="sub">2026-07-28 · 민옥·SilenceBreaker · 모델 gpt-5.4-mini · temperature 1.0 ·
<b>탐색적 지위</b>(사전고정 문서 없음) · 원자료 <code>sanity_results_*.json</code> <code>curve_results.json</code></div>

<div class="note"><b>한 줄:</b> 정보를 전부 가진 에이전트는 정답(유지완)을, 공유 정보만 가진 에이전트는
오답(한도영)을 <b>10/10으로</b> 고른다 — 단 기권을 금지했을 때만. 그러나 실제 배분에서는 4명 중 3명이
혼자서 이미 정답을 알아(기준선 75%%), 현 배분으로는 정보 취합의 몫을 측정할 수 없다.</div>

<div class="cards">
<div class="card"><div>전지식 (12팩트)</div><div class="n ok">%d/%d</div><div class="sub">정답 유지완</div></div>
<div class="card"><div>공유만 (4팩트)</div><div class="n bad">%d/%d</div><div class="sub">오답 한도영</div></div>
<div class="card"><div>정보 없음</div><div class="n mid">%d/%d</div><div class="sub">한도영 (임의 선택)</div></div>
<div class="card"><div>실제 배분 기준선</div><div class="n mid">%d/%d</div><div class="sub">정답 — 너무 높음</div></div>
</div>

<h2>1. 조건별 정답률</h2>%s
<h2>2. 기권 허용 vs 금지</h2>
<table><tr><th>조건</th><th>기권 허용 (n=3)</th><th>기권 금지 (n=10)</th></tr>
<tr><td>ceiling</td><td>유지완 3/3</td><td>유지완 10/10</td></tr>
<tr><td>trap</td><td><b>판단불가 3/3</b></td><td><b>한도영 10/10</b></td></tr>
<tr><td>blind</td><td>판단불가 3/3</td><td>한도영 7 / 유지완 3</td></tr></table>
<div class="note">모델은 기권이 가능하면 <b>정보 부족을 정확히 인지</b>하고 판단을 보류한다. 사람 대상
히든 프로필 실험에서는 보고되지 않는 행동이다. 기권을 금지하면 고전 효과가 그대로 재현된다.</div>

<h2>3. 실제 배분에서의 단독 기준선 (핵심)</h2>
<table><tr><th>관점</th><th>보유 미공유 팩트</th><th>5회 결과</th><th>정답률</th></tr>%s</table>
<div class="note">각 관점이 <b>한 요건의 양쪽</b>(한도영 측·유지완 측)을 통째로 쥐고 있어 그 하나만으로
비교가 완결된다 → 혼자 결론이 난다. 히든 프로필의 필수 조건 "아무도 혼자서는 못 맞힌다"가 깨졌다.
<b>배분은 편의 파라미터가 아니라 1급 설계 변수다.</b></div>

<h2>4. 용량-반응 곡선</h2>%s
<div class="note">비단조. 미공유 8개 중 6개가 유지완에 유리해 k=1에서 유리 팩트를 뽑을 확률이 높고,
k당 5조합만 추첨해 표본 오차가 크다. <b>현 표본으로는 해석하지 않는다.</b></div>

<h2>5. 응답 원문 — 전지식 조건 (정답)</h2>%s
<h2>6. 응답 원문 — 함정 조건 (오답)</h2>
<div class="note">모델이 <b>찍은 것이 아니라</b> 공유 팩트로 요건 3~4개를 조립해 확신을 세운다.
그 근거는 전부 미공유 팩트에 의해 뒤집히는 것들이다 — 이것이 히든 프로필이 작동한다는 증거다.</div>%s
<h2>7. 응답 원문 — 정보 없음 조건 (대조)</h2>
<div class="note">스스로 "임의 선택", "이름 순으로"라고 밝힌다. 함정 조건과 <b>질적으로 다른 상태</b>이며,
7:3 쏠림은 정보가 아니라 순서 편향이다(재실행 시 이름 순서 균형 필요).</div>%s
<h2>8. 시나리오 전문</h2>
<div class="note"><b>%s</b><br>%s<br><br><b>질문:</b> %s</div>%s
<div class="sub" style="margin-top:30px">생성: gen_evidence.py · 총 실호출 약 190콜(401 실패 18콜 포함)</div>
</html>""" % (CSS, c_ok, c_n, t_h, t_n, b_h, b_n, p_ok, p_n,
              bar_svg(), persp_rows, curve_svg(),
              log_table(forced, "ceiling"), log_table(forced, "trap"), log_table(forced, "blind"),
              html.escape(issue["title"]), html.escape(issue["body"]),
              html.escape(issue["question"]), facts_table())

out = os.path.join(H, "evidence_hidden_profile.html")
open(out, "w", encoding="utf-8").write(HTML)
print("저장:", out, "|", len(HTML), "bytes")
