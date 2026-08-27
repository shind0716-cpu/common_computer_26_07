"""[공용 코어 · 압박×카테고리] 1차 1단계 콘솔을 만든다 — 파일 하나, 서버 없음.

`tools/console`(민옥 · 실험 콘솔)과 `tools/viewer`(요한 · 팩트 생존 뷰어)는 둘 다
`data/debates` 의 스키마 v0.3 산출물을 읽는다. 이 트랙의 런은 형식이 다르므로
(`runs/<모델>/<재료>/run_C0_<세트>_rep1.json`) 그 둘을 고치지 않고 옆에 세운다 —
`tools/console/app.py` 머리말이 같은 이유로 뷰어 옆에 콘솔을 세운다고 적어 둔 그 원칙이다.

만드는 것: `CONSOLE_stage1_2026-08-27.html` — 열면 되는 파일 하나.
서버도 설치도 없다. 원문·판독·열쇠를 전부 품고 있어 리포만 받으면 그대로 열린다.

**원문을 그대로 싣는다**(규약 5). 수첩도 토론도 자르지 않는다.

    python make_console.py            # 만들고 경로를 찍는다
    python make_console.py --body     # 머리·몸통 태그 없이 (Artifact 게시용)
"""
import html
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze_stage1 as S  # noqa: E402

OUT = "CONSOLE_stage1_2026-08-27.html"
GARAE2 = S.GARAE2


def build_data():
    key, mats, runs = S.load_all()
    coders = {n: S.load_coding(p) for n, p in
              (("A", "READ60_coderA"), ("H", "READ60_hermes"))}
    out = {"materials": [], "meta": {}}
    for iid in sorted(key):
        M = mats[iid]
        slot_of = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
        d0, ds, _ = S.pair_d(mats, coders["A"], key, iid)
        d0h, dsh, _ = S.pair_d(mats, coders["H"], key, iid)
        fa = runs[(iid, "A")]["final_poll"]
        fb = runs[(iid, "B")]["final_poll"]
        rec = {
            "id": iid, "name": iid.replace("issue_", ""),
            "author": S.author(iid),
            "garae": "둘" if iid in GARAE2 else ("하나" if S.author(iid) == "요한" else "—"),
            "options": M["options"], "gate": fa != fb,
            "d0": d0, "ds": ds, "d0h": d0h, "dsh": dsh,
            "facts": [], "sides": {},
        }
        for s in ("A", "B"):
            r = runs[(iid, s)]
            rec["sides"][s] = {
                "slot": slot_of[s], "statement": r["value_statement"],
                "aligned": r["aligned"], "final": r["final_poll"],
                "ok": r["final_poll"] == r["aligned"],
                "cats": sorted(M["sets"][s]),
                "notes": r["notes"], "essays": r["essays"],
            }
        for i, fid in enumerate(M["order"]):
            f = M["facts"][fid]
            row = {"id": fid, "text": f["text"], "cat": f["category"],
                   "anchor": f.get("anchor", ""), "j": {}}
            for s in ("A", "B"):
                sl = slot_of[s]
                row["j"][s] = {
                    "side": "안" if f["category"] in M["sets"][s] else "밖",
                    "a0": coders["A"][(iid, sl)]["r0"][i],
                    "al": coders["A"][(iid, sl)]["last"][i],
                    "h0": coders["H"][(iid, sl)]["r0"][i],
                    "hl": coders["H"][(iid, sl)]["last"][i],
                    "hit": f.get("anchor", "") in runs[(iid, s)]["notes"][0] if f.get("anchor") else None,
                }
            rec["facts"].append(row)
        out["materials"].append(rec)
    pos0 = sum(1 for m in out["materials"] if m["d0"] is not None and m["d0"] > 0)
    out["meta"] = {"pairs": len(out["materials"]), "gate": sum(1 for m in out["materials"] if m["gate"]),
                   "pos0": pos0, "cells": 1424, "kappa": 0.817}
    return out


CSS = """
:root{
  --bg:#faf9f7; --panel:#fff; --ink:#1c1a17; --dim:#6c665e; --line:#e3ded6;
  --in:#8a4b1e; --in-bg:#fdf1e6; --out:#2a5f7a; --out-bg:#e9f2f6;
  --keep:#1f6b3a; --part:#a8730c; --morph:#7a3fa0; --drop:#a33; --accent:#1c1a17;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#15140f; --panel:#1d1b16; --ink:#eae5db; --dim:#9a9288; --line:#332f28;
  --in:#e0a06a; --in-bg:#2c2118; --out:#7fb8d4; --out-bg:#17262e;
  --keep:#6cc38c; --part:#e0b756; --morph:#c295e0; --drop:#e08a86; --accent:#eae5db;
}}
:root[data-theme="dark"]{
  --bg:#15140f; --panel:#1d1b16; --ink:#eae5db; --dim:#9a9288; --line:#332f28;
  --in:#e0a06a; --in-bg:#2c2118; --out:#7fb8d4; --out-bg:#17262e;
  --keep:#6cc38c; --part:#e0b756; --morph:#c295e0; --drop:#e08a86; --accent:#eae5db;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.65 -apple-system,"Segoe UI","Malgun Gothic",system-ui,sans-serif;}
.wrap{max-width:1520px;margin:0 auto;padding:0 20px 80px}
header{padding:34px 0 20px;border-bottom:1px solid var(--line);margin-bottom:22px}
h1{font-size:23px;margin:0 0 6px;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:14px;margin:0 0 18px}
.lead{font-size:17px;margin:0 0 20px;padding:14px 18px;background:var(--panel);
  border:1px solid var(--line);border-left:3px solid var(--in);border-radius:0 6px 6px 0}
.nums{display:flex;gap:28px;flex-wrap:wrap}
.num b{display:block;font-size:26px;font-variant-numeric:tabular-nums;line-height:1.1}
.num span{font-size:12px;color:var(--dim)}
.cols{display:grid;grid-template-columns:264px 1fr;gap:22px;align-items:start}
@media(max-width:1000px){.cols{grid-template-columns:1fr}}
.rail{position:sticky;top:14px;max-height:calc(100vh - 30px);overflow:auto;
  background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px}
.filt{display:flex;gap:5px;padding:4px 4px 8px;flex-wrap:wrap}
.filt button{font:inherit;font-size:12px;padding:3px 9px;border:1px solid var(--line);
  background:transparent;color:var(--dim);border-radius:99px;cursor:pointer}
.filt button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.item{display:block;width:100%;text-align:left;font:inherit;background:transparent;
  border:0;border-radius:6px;padding:7px 9px;cursor:pointer;color:var(--ink)}
.item:hover{background:var(--bg)}
.item.on{background:var(--in-bg);box-shadow:inset 2px 0 0 var(--in)}
.item .t{font-size:13px;display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.item .m{font-size:11px;color:var(--dim);font-variant-numeric:tabular-nums}
.bar{height:3px;background:var(--line);border-radius:2px;margin-top:4px;position:relative}
.bar i{position:absolute;top:0;bottom:0;background:var(--in);border-radius:2px}
.bar i.neg{background:var(--out)}
.pane{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:22px 24px}
.head2{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
h2{font-size:19px;margin:0 0 4px}
.tag{display:inline-block;font-size:11px;padding:2px 8px;border-radius:99px;
  border:1px solid var(--line);color:var(--dim);margin-right:5px}
.tag.pass{color:var(--keep);border-color:var(--keep)}
.tag.fail{color:var(--drop);border-color:var(--drop)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}
@media(max-width:820px){.two{grid-template-columns:1fr}}
.vs{padding:12px 14px;border-radius:6px;border:1px solid var(--line);font-size:13.5px}
.vs.a{background:var(--in-bg)} .vs.b{background:var(--out-bg)}
.vs h3{margin:0 0 6px;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--dim)}
.vs .st{margin:0 0 8px}
.vs .fin{font-size:13px}
.vs .fin b{font-weight:600}
.ok{color:var(--keep)} .no{color:var(--drop);font-weight:600}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin:6px 0 4px}
th{text-align:left;font-weight:500;font-size:11px;color:var(--dim);padding:4px 6px;
  border-bottom:1px solid var(--line);text-transform:uppercase;letter-spacing:.04em}
td{padding:6px;border-bottom:1px solid var(--line);vertical-align:top}
td.f{width:44%}
.side{display:inline-block;width:20px;font-weight:600;font-size:12px}
.side.in{color:var(--in)} .side.out{color:var(--out)}
.j{font-size:11.5px;font-variant-numeric:tabular-nums;white-space:nowrap}
.k{color:var(--keep)}.p{color:var(--part)}.m{color:var(--morph)}.d{color:var(--drop)}
.dis{color:var(--drop);font-weight:700}
.tabs{display:flex;gap:4px;margin:20px 0 10px;border-bottom:1px solid var(--line)}
.tabs button{font:inherit;font-size:13px;padding:7px 13px;border:0;background:transparent;
  color:var(--dim);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
.tabs button.on{color:var(--ink);border-bottom-color:var(--in);font-weight:500}
.note{white-space:pre-wrap;background:var(--bg);border:1px solid var(--line);
  border-radius:6px;padding:12px 14px;margin:0 0 12px;font-size:14px}
.note .cap{font-size:11px;color:var(--dim);margin-bottom:6px;letter-spacing:.03em}
.same{color:var(--part)}
.legend{font-size:12px;color:var(--dim);margin:10px 0 0}
.scroll{overflow-x:auto}
"""

JS = r"""
const D = __DATA__;
let cur = 0, filt = 'all', tab = 'facts';
const M = {'보':['k','보존'],'부':['p','부분'],'변':['m','변형'],'-':['d','탈락']};
const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const fd = v => v === null ? ' – ' : (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toFixed(2);

function rail(){
  const F = {all:()=>1, gate:m=>!m.gate, big:m=>m.d0>=0.33, zero:m=>m.d0<=0};
  const rows = D.materials.filter(F[filt]).map(m=>{
    const i = D.materials.indexOf(m), w = Math.abs(m.d0||0)*100;
    return `<button class="item ${i===cur?'on':''}" data-i="${i}">
      <span class="t"><span>${esc(m.name)}</span>
      <span class="m">${m.gate?'':'✕ '}${fd(m.d0)}</span></span>
      <span class="bar"><i class="${m.d0<0?'neg':''}" style="left:50%;width:${w/2}%;
        ${m.d0<0?`left:${50-w/2}%`:''}"></i></span></button>`;
  }).join('');
  document.getElementById('rail').innerHTML = rows || '<p class="legend">해당 없음</p>';
  document.querySelectorAll('.item').forEach(b =>
    b.onclick = () => { cur = +b.dataset.i; draw(); });
  document.querySelectorAll('.filt button').forEach(b =>
    b.classList.toggle('on', b.dataset.f === filt));
}

function facts(m){
  const rows = m.facts.map(f=>{
    const c = s => {
      const j = f.j[s], dis = (j.a0!==j.h0 || j.al!==j.hl);
      const g = x => `<span class="${M[x][0]}">${M[x][1]}</span>`;
      return `<td><span class="side ${j.side==='안'?'in':'out'}">${j.side}</span>
        <span class="j">${g(j.a0)}→${g(j.al)}${dis?' <span class="dis">≠</span> '+g(j.h0)+'→'+g(j.hl):''}</span></td>`;
    };
    return `<tr>${c('A')}<td class="f">${esc(f.text)}<br><span class="legend">${esc(f.cat)}</span></td>${c('B')}</tr>`;
  }).join('');
  return `<div class="scroll"><table>
    <tr><th>가치 A 에서</th><th>사실</th><th>가치 B 에서</th></tr>${rows}</table></div>
    <p class="legend">한 사실은 A벌에서 「안」이면 B벌에서 반드시 「밖」이다 — 거울 설계.
    판독은 r0 → 마지막 순이고, 두 코더가 갈린 자리에만 <span class="dis">≠</span> 뒤에
    헤르메스 판독을 함께 적었다.</p>`;
}

function notes(m, kind){
  return `<div class="two">` + ['A','B'].map(s=>{
    const S = m.sides[s], xs = kind==='notes' ? S.notes : S.essays;
    return `<div>${xs.map((t,i)=>{
      const same = kind==='notes' && i && t===xs[i-1];
      return `<div class="note"><div class="cap">가치 ${s} · ${kind==='notes'?'수첩':'토론'} r${i}
        · ${t.length}자${same?' <span class="same">※ 앞과 글자까지 같다</span>':''}</div>${esc(t)}</div>`;
    }).join('')}</div>`;
  }).join('') + `</div>`;
}

function draw(){
  const m = D.materials[cur];
  const vs = s => { const S = m.sides[s];
    return `<div class="vs ${s.toLowerCase()}"><h3>가치 ${s} · 판독 팩 ${S.slot}</h3>
      <p class="st">${esc(S.statement)}</p>
      <p class="fin">정렬 답 <b>${esc(S.aligned)}</b> · 고른 것 <b>${esc(S.final)}</b>
      <span class="${S.ok?'ok':'no'}">${S.ok?'정렬':'★ 역 — 가치를 안 따랐다'}</span></p>
      <p class="legend">카테고리 ${S.cats.map(esc).join(' · ')}</p></div>`; };
  document.getElementById('pane').innerHTML = `
    <div class="head2"><div><h2>${esc(m.name)}</h2>
      <p class="legend">${esc(m.options[0])} &nbsp;↔&nbsp; ${esc(m.options[1])}</p></div>
      <div><span class="tag ${m.gate?'pass':'fail'}">관문 ${m.gate?'통과':'탈락'}</span>
      <span class="tag">${esc(m.author)}</span><span class="tag">갈래 ${esc(m.garae)}</span>
      <span class="tag">r0 d ${fd(m.d0)}</span><span class="tag">생존 d ${fd(m.ds)}</span></div></div>
    <div class="two">${vs('A')}${vs('B')}</div>
    <div class="tabs">
      <button data-t="facts" class="${tab==='facts'?'on':''}">사실 ${m.facts.length}개와 판독</button>
      <button data-t="notes" class="${tab==='notes'?'on':''}">수첩 원문</button>
      <button data-t="essays" class="${tab==='essays'?'on':''}">토론 원문</button></div>
    ${tab==='facts' ? facts(m) : notes(m, tab)}`;
  document.querySelectorAll('.tabs button').forEach(b =>
    b.onclick = () => { tab = b.dataset.t; draw(); });
  rail();
}
document.querySelectorAll('.filt button').forEach(b =>
  b.onclick = () => { filt = b.dataset.f; cur = D.materials.indexOf(
    D.materials.filter({all:()=>1,gate:m=>!m.gate,big:m=>m.d0>=0.33,zero:m=>m.d0<=0}[filt])[0] || D.materials[0]); draw(); });
addEventListener('keydown', e => {
  if(e.key==='ArrowDown'||e.key==='j'){cur=Math.min(cur+1,D.materials.length-1);draw();}
  if(e.key==='ArrowUp'||e.key==='k'){cur=Math.max(cur-1,0);draw();}});
draw();
"""

BODY = """<title>압박×카테고리 1차 콘솔</title>
<style>__CSS__</style>
<div class="wrap">
<header>
  <h1>부여된 가치와 사실 생존 — 1차 1단계 콘솔</h1>
  <p class="sub">gpt-5.4-mini · 30벌 × 가치 A·B · C0 · 반복 1 · 온도 0.7 · 수첩 500자, 보존 명령 없음
    · 60판 496콜 (2026-08-27) · 사전고정 <code>SELECTION_live30_2026-08-27.md</code> §15·§18·§19·§21</p>
  <p class="lead">가치는 무엇이 <b>첫 수첩에 오르는지</b>를 가른다. 오르고 난 뒤에는 거의 안 가른다.</p>
  <div class="nums">
    <div class="num"><b>25<span style="font-size:15px">/30</span></b><span>r0 진입에서 d&gt;0 인 쌍 · 두 코더 같음</span></div>
    <div class="num"><b>9<span style="font-size:15px">/29</span></b><span>생존 층에서 d&gt;0 — 기각</span></div>
    <div class="num"><b>21<span style="font-size:15px">/30</span></b><span>관문 통과</span></div>
    <div class="num"><b>0.817</b><span>코더 간 κ · 1,424칸</span></div>
    <div class="num"><b>5.6e-06</b><span>부호검정 p (r0 층)</span></div>
  </div>
</header>
<div class="cols">
  <aside class="rail">
    <div class="filt">
      <button data-f="all" class="on">30벌</button>
      <button data-f="gate">관문 탈락</button>
      <button data-f="big">d ≥ .33</button>
      <button data-f="zero">d ≤ 0</button>
    </div>
    <div id="rail"></div>
  </aside>
  <main id="pane" class="pane"></main>
</div>
<p class="legend" style="margin-top:22px">↑↓ 또는 j/k 로 벌을 옮긴다. 수첩·토론은 <b>원문 그대로</b>이고 자르지 않았다(규약 5).
d = p안 − p밖, 짝 단위(§18-6-2). 판독은 코더 A(요한 측)와 헤르메스(다른 모델) 둘이 가린 채 따로 읽었다.</p>
</div>
<script>__JS__</script>
"""


def main(argv):
    root = pathlib.Path(__file__).resolve().parent
    data = build_data()
    body = (BODY.replace("__CSS__", CSS)
                .replace("__JS__", JS.replace("__DATA__", json.dumps(data, ensure_ascii=False))))
    if "--body" in argv:
        out = root / OUT.replace(".html", "_body.html")
        out.write_text(body, encoding="utf-8")
    else:
        out = root / OUT
        out.write_text('<!doctype html>\n<html lang="ko">\n<meta charset="utf-8">\n'
                       '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
                       + body + "\n</html>\n", encoding="utf-8")
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB · 벌 {len(data['materials'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
