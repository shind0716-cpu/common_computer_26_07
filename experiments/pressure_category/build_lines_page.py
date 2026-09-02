"""[공용 코어 · 압박×카테고리] 선 그래프 한 장 — 집계 JSON 을 그대로 그린다 (콜 0).

## 무엇을 만드나

`FACTS_<날짜>.json`(사실 보존율)과 `CHOICE_<날짜>.json`(최종 선택)을 읽어
선 그래프 다섯을 담은 낱장 HTML 을 찍는다.

  하나  라운드별 사실 보존율 — 안/밖 × 세 모델 (분모 1440칸)
  둘    세트 축 압박 — A·B 마다 C0·C1·C2 격차 (쪽마다 720칸)
  셋    올세트 대 A/B — 판당 사실 수 (두 갈래를 다 돈 34벌)
  넷    최종 선택 뒤집힘 — 압박 방향 축 (표식 안 씀)
  다섯  관문 — 재료별 (표식 안 씀)

## 왜 집계 JSON 에서만 읽나

**손으로 옮긴 숫자가 한 개도 없어야 한다.** 앞서 보고서 수치를 손으로 옮기다가
틀린 적이 있다. 이 생성기는 집계기 산출물만 읽고, 표에 적힌 값을 다시 타이핑하지
않는다. 집계기를 다시 돌리면 그림도 따라 바뀐다.

## 색

`dataviz` 검사기(`validate_palette.js`)를 통과한 값만 쓴다 — 밝은 화면·어두운 화면
각각 밝기대·채도 바닥·색각 분리·대비를 전부 통과했다. 눈으로 고르지 않았다.

사용: PYTHONUTF8=1 python build_lines_page.py
산출: LINES_<날짜>.html
"""
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

HERE = pathlib.Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
MODELS = ["claude-haiku", "gemini-flash", "gpt"]
# 캣맘 무대의 판본들 — 서로 다른 시나리오가 아니라 같은 무대를 고쳐 가며 만든 것이다
CAT = ["issue_community_cat_feeding", "issue_cat_feeding_evenweight",
       "issue_cat_feeding_shared", "issue_cat_feeding_plainvalue",
       "issue_cat_feeding_party", "issue_cat_feeding_days_list",
       "issue_cat_feeding_entry_list", "issue_cat_feeding_harm"]


def 최신(prefix: str) -> pathlib.Path:
    xs = sorted(HERE.glob(f"{prefix}_*.json"))
    if not xs:
        sys.exit(f"{prefix}_*.json 이 없다 — 집계기를 먼저 돌려라")
    return xs[-1]


def 재료() -> dict:
    F = json.loads(최신("FACTS").read_text(encoding="utf-8"))
    C = json.loads(최신("CHOICE").read_text(encoding="utf-8"))
    out = {"모델": MODELS, "라운드": ["원문", "r0", "r1", "r2"], "캣맘": CAT}

    합 = {}
    for m in MODELS:
        s = F["series"][m]
        for sd in ("안", "밖"):
            a, b = s[f"A|C0|{sd}"], s[f"B|C0|{sd}"]
            합.setdefault(m, {})[sd] = [[a[r][0] + b[r][0], a[r][1] + b[r][1]]
                                       for r in range(3)]
    out["보존"] = 합

    축 = {}
    for m in MODELS:
        s = F["series"][m]
        for st in ("A", "B"):
            for cond in ("C0", "C1", "C2"):
                축.setdefault(m, {}).setdefault(st, {})[cond] = {
                    sd: s[f"{st}|{cond}|{sd}"] for sd in ("안", "밖")}
    out["세트축"] = 축

    AB, 올 = F["올세트대AB"], {}
    for m in MODELS:
        for 갈래 in ("올세트", "A/B"):
            n = AB.get(f"{m}|{갈래}|C0|판")
            if n:
                올.setdefault(m, {})[갈래] = {
                    "판": n, "값": [round(AB[f"{m}|{갈래}|C0|{r}"] / n, 3) for r in range(3)]}
    out["올세트"] = 올
    out["올세트재료"] = len(F["올세트공통재료"])

    뒤, flip = C["뒤집힘"], {}
    for m in MODELS:
        for st in ("A", "B"):
            flip.setdefault(m, {})[st] = [
                [뒤.get(f"{m}|{st}|{c}|뒤집힘", 0), 뒤.get(f"{m}|{st}|{c}|판", 0)]
                for c in ("C1", "C0", "C2")]          # 편들어 → 없음 → 반대로
    out["뒤집힘"] = flip

    g = {}
    for key, v in C["관문"].items():
        q = key.split("|")
        if len(q) == 2 and q[1] in ("C0짝", "C0통과"):
            g.setdefault(q[0], {})["짝" if q[1] == "C0짝" else "통과"] = v
    out["관문"] = {k: v for k, v in g.items() if v.get("짝")}
    out["판"] = C["판"]
    out["재료수"] = len({k for k in out["관문"]})
    return out


D = 재료()

CSS = r"""
:root{
  --paper:#fbfcfd; --sunk:#f2f5f8; --card:#ffffff;
  --ink-1:#12181f; --ink-2:#43505e; --ink-3:#77828f; --ink-4:#9aa5b1;
  --rule:#dde4ea; --rule-2:#eaeff4;
  --m1:#1C7ED6; --m2:#C2410C; --m3:#7C3AED;
  --push-for:#1D4ED8; --push-none:#8a93a0; --push-against:#DC2626;
  --warn-bg:#fdf6ec; --warn-ink:#8a5a17; --warn-rule:#e8d5b0;
  --grid:#e9eef3;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#0e1318; --sunk:#141b22; --card:#151d25;
    --ink-1:#eef3f7; --ink-2:#b3bfcb; --ink-3:#818d99; --ink-4:#606c78;
    --rule:#27313b; --rule-2:#1e2730;
    --m1:#3591D6; --m2:#D07C3E; --m3:#9478E0;
    --push-for:#4D8FE8; --push-none:#7b8794; --push-against:#E8595F;
    --warn-bg:#241d10; --warn-ink:#d9b579; --warn-rule:#463a22;
    --grid:#212b34;
  }
}
:root[data-theme="dark"]{
  --paper:#0e1318; --sunk:#141b22; --card:#151d25;
  --ink-1:#eef3f7; --ink-2:#b3bfcb; --ink-3:#818d99; --ink-4:#606c78;
  --rule:#27313b; --rule-2:#1e2730;
  --m1:#3591D6; --m2:#D07C3E; --m3:#9478E0;
  --push-for:#4D8FE8; --push-none:#7b8794; --push-against:#E8595F;
  --warn-bg:#241d10; --warn-ink:#d9b579; --warn-rule:#463a22;
  --grid:#212b34;
}

*{box-sizing:border-box}
body{
  background:var(--paper); color:var(--ink-1); margin:0;
  font-family:"IBM Plex Sans KR",system-ui,-apple-system,"Malgun Gothic",sans-serif;
  font-size:16px; line-height:1.75;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1000px;margin:0 auto;padding:56px 24px 96px}
h1{
  font-family:"Gowun Batang",Batang,serif; font-weight:700;
  font-size:clamp(30px,4.6vw,46px); line-height:1.25; letter-spacing:-.02em;
  margin:0 0 14px; text-wrap:balance;
}
h2{
  font-family:"Gowun Batang",Batang,serif; font-weight:700;
  font-size:clamp(21px,2.7vw,27px); line-height:1.35; letter-spacing:-.01em;
  margin:0 0 6px; text-wrap:balance;
}
.eyebrow{
  font-size:11.5px; font-weight:600; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ink-4); margin:0 0 10px;
}
.lede{font-size:18px;color:var(--ink-2);margin:0 0 26px;max-width:62ch}
.strip{
  display:flex;flex-wrap:wrap;gap:8px 20px;padding:13px 16px;margin:0 0 44px;
  background:var(--sunk);border:1px solid var(--rule);border-radius:9px;
  font-size:13px;color:var(--ink-2);
}
.strip b{color:var(--ink-1);font-weight:600}
.num{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}

figure{margin:0 0 60px;padding:0}
.fhead{margin:0 0 16px}
.fnote{font-size:14.5px;color:var(--ink-2);margin:6px 0 0;max-width:66ch}
.plot{
  background:var(--card);border:1px solid var(--rule);border-radius:11px;
  padding:18px 16px 12px;position:relative;overflow-x:auto;
}
.grid2{display:grid;gap:12px;grid-template-columns:repeat(3,1fr)}
.grid2.two{grid-template-columns:repeat(2,1fr)}
@media(max-width:1000px){.grid2{grid-template-columns:repeat(2,1fr)}}
@media(max-width:620px){.grid2,.grid2.two{grid-template-columns:1fr}}
.panel{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:12px 10px 6px}
.ptitle{font-size:12.5px;font-weight:600;color:var(--ink-2);margin:0 0 2px;padding-left:6px}
.psub{font-size:11px;color:var(--ink-4);margin:0 0 4px;padding-left:6px}

svg{display:block;width:100%;height:auto;overflow:visible}
.gl{stroke:var(--grid);stroke-width:1}
.ax{stroke:var(--rule);stroke-width:1}
.axlab{fill:var(--ink-4);font-size:11px;font-family:"IBM Plex Mono",monospace}
.ttl{fill:var(--ink-3);font-size:11px}
.dl{font-size:11.5px;font-weight:600;font-family:"IBM Plex Sans KR",sans-serif}
.hit{fill:transparent;cursor:crosshair}

.legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin:12px 0 0;padding:0 6px;font-size:12.5px;color:var(--ink-2)}
.key{display:inline-flex;align-items:center;gap:7px}
.swatch{width:22px;height:0;border-top-width:2.5px;border-top-style:solid;display:inline-block}
.denom{font-size:12px;color:var(--ink-4);margin:10px 0 0;padding:0 6px}

.tip{
  position:absolute;pointer-events:none;opacity:0;transition:opacity .09s;
  background:var(--ink-1);color:var(--paper);border-radius:7px;padding:8px 11px;
  font-size:12.5px;line-height:1.55;white-space:nowrap;z-index:9;
  box-shadow:0 6px 18px rgba(0,0,0,.18);
}
.tip .k{color:var(--ink-4);}
.tip b{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}

.toggle{display:inline-flex;border:1px solid var(--rule);border-radius:7px;overflow:hidden;margin:0 0 12px}
.toggle button{
  font:inherit;font-size:12.5px;padding:5px 13px;border:0;cursor:pointer;
  background:var(--card);color:var(--ink-3);
}
.toggle button[aria-pressed="true"]{background:var(--ink-1);color:var(--paper);font-weight:600}
.toggle button:focus-visible{outline:2px solid var(--m1);outline-offset:-2px}

details{margin:12px 0 0;border-top:1px solid var(--rule-2);padding-top:10px}
summary{cursor:pointer;font-size:12.5px;color:var(--ink-3);list-style:none}
summary::-webkit-details-marker{display:none}
summary:before{content:"▸ ";color:var(--ink-4)}
details[open] summary:before{content:"▾ "}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin-top:10px}
th,td{border-bottom:1px solid var(--rule-2);padding:5px 9px;text-align:right}
th:first-child,td:first-child{text-align:left}
thead th{color:var(--ink-3);font-weight:600;border-bottom-color:var(--rule)}
td.n{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
.tw{overflow-x:auto}

.warn{
  background:var(--warn-bg);border:1px solid var(--warn-rule);border-left-width:3px;
  border-radius:0 8px 8px 0;padding:13px 16px;margin:16px 0 0;
  font-size:13.5px;color:var(--warn-ink);line-height:1.65;
}
.warn b{color:var(--warn-ink)}
.band-key{width:22px;height:11px;display:inline-block;border-radius:2px;
  background:var(--m3);opacity:.3}
.cmp{margin:22px 0 0;padding:16px 18px;background:var(--sunk);
  border:1px solid var(--rule);border-radius:10px}
.cmplab{font-size:13px;font-weight:600;color:var(--ink-1);margin:0 0 6px}
.cmpnote{font-size:13px;color:var(--ink-2);margin:0;max-width:64ch}
.rail{border-left:2px solid var(--rule);padding-left:16px;margin:18px 0 0;color:var(--ink-2);font-size:14.5px}
footer{margin-top:72px;padding-top:22px;border-top:1px solid var(--rule);font-size:13px;color:var(--ink-3)}
footer code{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink-2)}
h3{font-family:"Gowun Batang",Batang,serif;font-size:19px;margin:0 0 10px}
"""

JS = r"""
const D = __DATA__;
const M = D["모델"];
const MC = {"claude-haiku":"--m1","gemini-flash":"--m2","gpt":"--m3"};
const ORD = ["gpt","gemini-flash","claude-haiku"];   // 주 실험이 앞에 온다
const MN = {"claude-haiku":"클로드 하이쿠","gemini-flash":"제미나이 플래시","gpt":"GPT"};
const cv = n => getComputedStyle(document.body).getPropertyValue(n).trim();
const pc = a => a[1] ? 100*a[0]/a[1] : 0;
const f1 = v => (Math.round(v*10)/10).toFixed(1);

function mkTip(host){
  const t=document.createElement("div"); t.className="tip"; host.appendChild(t); return t;
}

/* 범용 선 그래프 — series:[{name,color,dash,pts:[{x,y,lab}]}] */
function draw(host, series, o){
  o = Object.assign({w:820,h:300,pl:52,pr:98,pt:14,pb:34,ylab:v=>v,
                     ymin:null,ymax:null,ticks:5,xlabs:[],zero:false,dl:true,edgeLabs:false,band:null}, o);
  const vals = series.flatMap(s=>s.pts.map(p=>p.y));
  let lo = o.ymin!==null?o.ymin:Math.min(...vals), hi = o.ymax!==null?o.ymax:Math.max(...vals);
  if(hi===lo){hi=lo+1;}
  const pad=(hi-lo)*0.12; if(o.ymin===null) lo-=pad; if(o.ymax===null) hi+=pad;
  const n = series[0].pts.length;
  const X = i => o.pl + i*(o.w-o.pl-o.pr)/(n-1);
  const Y = v => o.pt + (hi-v)/(hi-lo)*(o.h-o.pt-o.pb);
  const NS="http://www.w3.org/2000/svg";
  const svg=document.createElementNS(NS,"svg");
  svg.setAttribute("viewBox",`0 0 ${o.w} ${o.h}`);
  svg.setAttribute("role","img");
  const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e;};

  for(let i=0;i<=o.ticks;i++){
    const v=lo+(hi-lo)*i/o.ticks, y=Y(v);
    svg.appendChild(el("line",{x1:o.pl,x2:o.w-o.pr,y1:y,y2:y,class:"gl"}));
    const tx=el("text",{x:o.pl-9,y:y+4,class:"axlab","text-anchor":"end"});
    tx.textContent=o.ylab(v); svg.appendChild(tx);
  }
  if(o.zero && lo<0 && hi>0){
    svg.appendChild(el("line",{x1:o.pl,x2:o.w-o.pr,y1:Y(0),y2:Y(0),class:"ax"}));
  }
  o.xlabs.forEach((lb,i)=>{
    const an = o.edgeLabs && i===0 ? "start"
             : o.edgeLabs && i===o.xlabs.length-1 ? "end" : "middle";
    const tx=el("text",{x:X(i),y:o.h-o.pb+19,class:"axlab","text-anchor":an});
    tx.textContent=lb; svg.appendChild(tx);
  });

  if(o.band){
    const A=series[o.band.a].pts, B=series[o.band.b].pts;
    const d = A.map((p,i)=>`${i?"L":"M"}${X(i)},${Y(p.y)}`).join(" ")
      + " " + B.map((p,i)=>`L${X(B.length-1-i)},${Y(B[B.length-1-i].y)}`).join(" ") + " Z";
    svg.appendChild(el("path",{d,fill:cv(o.band.color),opacity:.13,stroke:"none"}));
  }
  series.forEach(s=>{
    const c=cv(s.color);
    const d=s.pts.map((p,i)=>`${i?"L":"M"}${X(i)},${Y(p.y)}`).join(" ");
    svg.appendChild(el("path",{d,fill:"none",stroke:c,"stroke-width":2,
      "stroke-linejoin":"round","stroke-linecap":"round",
      ...(s.dash?{"stroke-dasharray":"5 4"}:{})}));
    s.pts.forEach((p,i)=>{
      svg.appendChild(el("circle",{cx:X(i),cy:Y(p.y),r:4.5,fill:cv("--card"),
        stroke:c,"stroke-width":2}));
    });
    if(o.dl){
      const last=s.pts[s.pts.length-1];
      const tx=el("text",{x:X(n-1)+11,y:Y(last.y)+4,class:"dl",fill:c});
      tx.textContent=s.name; svg.appendChild(tx);
    }
  });

  /* 겹치는 직접 이름표 밀어내기 */
  if(o.dl){
    const labs=[...svg.querySelectorAll("text.dl")];
    const ys=labs.map(t=>+t.getAttribute("y")).map((y,i)=>({y,i}));
    ys.sort((a,b)=>a.y-b.y);
    for(let k=1;k<ys.length;k++) if(ys[k].y-ys[k-1].y<14) ys[k].y=ys[k-1].y+14;
    ys.forEach(({y,i})=>labs[i].setAttribute("y",y));
  }

  const tip=mkTip(host);
  const cross=el("line",{x1:0,x2:0,y1:o.pt,y2:o.h-o.pb,class:"ax",opacity:0});
  svg.appendChild(cross);
  const hit=el("rect",{x:o.pl-14,y:0,width:o.w-o.pl-o.pr+28,height:o.h,class:"hit"});
  svg.appendChild(hit);
  hit.addEventListener("mousemove",e=>{
    const r=svg.getBoundingClientRect();
    const px=(e.clientX-r.left)/r.width*o.w;
    let i=0,best=1e9;
    for(let k=0;k<n;k++){const dd=Math.abs(X(k)-px); if(dd<best){best=dd;i=k;}}
    cross.setAttribute("opacity",.7);
    cross.setAttribute("x1",X(i)); cross.setAttribute("x2",X(i));
    tip.innerHTML = `<span class="k">${o.xlabs[i]||""}</span><br>` +
      series.map(s=>`${s.name} <b>${s.pts[i].lab}</b>`).join("<br>");
    tip.style.opacity=1;
    const hr=host.getBoundingClientRect();
    let L=e.clientX-hr.left+14;
    if(L+tip.offsetWidth>hr.width-6) L=e.clientX-hr.left-tip.offsetWidth-14;
    tip.style.left=L+"px";
    tip.style.top=Math.max(6,e.clientY-hr.top-tip.offsetHeight-12)+"px";
  });
  hit.addEventListener("mouseleave",()=>{tip.style.opacity=0;cross.setAttribute("opacity",0);});
  host.appendChild(svg);
  return svg;
}

/* ───── 그림 1 — 라운드별 사실 보존율 ───── */
const XL1=["원문","r0","r1","r2"];
function fig1(mode){
  const wrap=document.getElementById("p1"); wrap.innerHTML="";
  ORD.forEach(m=>{
    const raw={}, N=D["보존"][m]["안"][0][1];
    ["안","밖"].forEach(sd=>raw[sd]=[[N,N],...D["보존"][m][sd]]);
    const g2=pc(D["보존"][m]["안"][2])-pc(D["보존"][m]["밖"][2]);
    const d=document.createElement("div"); d.className="panel";
    d.innerHTML=`<p class="ptitle">${MN[m]}</p>
      <p class="psub">마지막 수첩 격차 <b style="color:var(${MC[m]})">${g2>=0?"+":""}${f1(g2)}%p</b>
        · 점마다 ${N.toLocaleString()}칸</p>`;
    const h=document.createElement("div"); h.style.position="relative"; d.appendChild(h);
    const S=["안","밖"].map(sd=>({
      name:sd, color: sd==="안"?MC[m]:"--push-none", dash: sd==="밖",
      pts:raw[sd].map(c=>({y: mode==="개수"?c[0]:pc(c),
        lab: mode==="개수" ? `${c[0]}칸 / ${c[1]}` : `${f1(pc(c))}%  (${c[0]}/${c[1]})`}))}));
    draw(h,S,{w:400,h:230,pl:46,pr:44,pb:30,xlabs:XL1,
      band:{a:0,b:1,color:MC[m]},
      ylab: mode==="개수" ? (v=>Math.round(v)) : (v=>Math.round(v)+"%"),
      ymin:0, ymax: mode==="개수"?1500:100, ticks:5});
    wrap.appendChild(d);
  });
}
document.querySelectorAll("#t1 button").forEach(b=>{
  b.addEventListener("click",()=>{
    document.querySelectorAll("#t1 button").forEach(x=>x.setAttribute("aria-pressed","false"));
    b.setAttribute("aria-pressed","true"); fig1(b.dataset.mode);
  });
});

/* ───── 그림 2 — 세트 축 격차, 작은 그림 여섯 ───── */
const PUSH={C1:["--push-for","편들어 미는 압박"],C0:["--push-none","압박 없음"],
            C2:["--push-against","반대로 미는 압박"]};
function fig2(){
  const wrap=document.getElementById("p2"); wrap.innerHTML="";
  ORD.forEach(m=>["A","B"].forEach(st=>{
    const d=document.createElement("div"); d.className="panel";
    d.innerHTML=`<p class="ptitle">${MN[m]} · ${st}세트</p>
                 <p class="psub">안 − 밖, 쪽마다 720칸</p>`;
    const h=document.createElement("div"); h.style.position="relative"; d.appendChild(h);
    const S=["C1","C0","C2"].map(c=>{
      const o=D["세트축"][m][st][c];
      return {name:c, color:PUSH[c][0], dash:false,
        pts:[0,1,2].map(r=>{
          const g=pc(o["안"][r])-pc(o["밖"][r]);
          return {y:g, lab:`${g>=0?"+":""}${f1(g)}%p  (안 ${o["안"][r][0]} · 밖 ${o["밖"][r][0]})`};
        })};
    });
    draw(h,S,{w:400,h:220,pl:44,pr:46,pb:30,xlabs:["r0","r1","r2"],
      ylab:v=>(v>0?"+":"")+Math.round(v), zero:true, ymin:-10, ymax:40, ticks:5});
    wrap.appendChild(d);
  }));
}

/* ───── 그림 3 — 올세트 대 A/B ───── */
function fig3(){
  const wrap=document.getElementById("p3"); wrap.innerHTML="";
  ORD.forEach(m=>{
    const o=D["올세트"][m]; if(!o||!o["올세트"]) return;
    const d=document.createElement("div"); d.className="panel";
    d.innerHTML=`<p class="ptitle">${MN[m]}</p>
      <p class="psub">올세트 ${o["올세트"]["판"]}판 · A/B ${o["A/B"]["판"]}판</p>`;
    const h=document.createElement("div"); h.style.position="relative"; d.appendChild(h);
    const S=[["올세트","--m3",false],["A/B","--push-none",true]].map(([k,c,dash])=>({
      name:k, color:c, dash,
      pts:o[k]["값"].map(v=>({y:v, lab:`${v.toFixed(2)}개 / 12`}))}));
    draw(h,S,{w:400,h:220,pl:44,pr:74,pb:30,xlabs:["r0","r1","r2"],
      ylab:v=>v.toFixed(0), ymin:3, ymax:7, ticks:4});
    wrap.appendChild(d);
  });
}

/* ───── 그림 4 — 최종 선택 뒤집힘 ───── */
function fig4(){
  const host=document.getElementById("p4"); host.innerHTML="";
  const S=[];
  ORD.forEach(m=>["A","B"].forEach(st=>{
    const row=D["뒤집힘"][m][st];
    S.push({name:MN[m]+" "+st, color:MC[m], dash:st==="B",
      pts:row.map(c=>({y:pc(c), lab:`${f1(pc(c))}%  (${c[0]}/${c[1]}판)`}))});
  }));
  draw(host,S,{h:320,pr:150,xlabs:["편들어 미는 압박","압박 없음","반대로 미는 압박"],
    ylab:v=>Math.round(v)+"%", ymin:0, ymax:60, ticks:6, edgeLabs:true});
}

/* ───── 그림 5 — 관문 ───── */
function fig5(){
  const host=document.getElementById("p5"); host.innerHTML="";
  const cat=new Set(D["캣맘"]);
  const rows=Object.entries(D["관문"]).map(([k,v])=>({k,v,r:v["통과"]/v["짝"]}))
    .sort((a,b)=>a.r-b.r||a.k.localeCompare(b.k));
  const NS="http://www.w3.org/2000/svg";
  const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const q in a)e.setAttribute(q,a[q]);return e;};
  const W=820,RH=19,PL=250,PR=54,H=rows.length*RH+30;
  const svg=document.createElementNS(NS,"svg");
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
  const X=r=>PL+r*(W-PL-PR);
  [0,.25,.5,.75,1].forEach(t=>{
    svg.appendChild(el("line",{x1:X(t),x2:X(t),y1:16,y2:H-8,class:"gl"}));
    const tx=el("text",{x:X(t),y:11,class:"axlab","text-anchor":"middle"});
    tx.textContent=Math.round(t*100)+"%"; svg.appendChild(tx);
  });
  const tip=mkTip(host);
  rows.forEach((o,i)=>{
    const y=28+i*RH;
    const isCat=cat.has(o.k);
    const c=cv(o.r<0.5?"--push-against":"--m1");
    svg.appendChild(el("line",{x1:PL,x2:X(o.r),y1:y,y2:y,
      stroke:cv("--rule"),"stroke-width":1}));
    if(isCat) svg.appendChild(el("circle",{cx:X(o.r),cy:y,r:8.5,fill:"none",
      stroke:cv("--ink-3"),"stroke-width":1}));
    svg.appendChild(el("circle",{cx:X(o.r),cy:y,r:4.5,fill:c}));
    const tx=el("text",{x:PL-11,y:y+4,class:"axlab","text-anchor":"end"});
    tx.textContent=(isCat?"◇ ":"")+o.k.replace("issue_","");
    tx.setAttribute("fill",cv(isCat?"--ink-2":"--ink-3"));
    svg.appendChild(tx);
    const g=el("rect",{x:PL-250,y:y-9,width:W-PR-PL+250,height:RH,class:"hit"});
    g.addEventListener("mousemove",e=>{
      tip.innerHTML=`${o.k.replace("issue_","")}<br>통과 <b>${o.v["통과"]}/${o.v["짝"]}</b> 짝`
        + (isCat?`<br><span class="k">캣맘 무대 판본</span>`:"");
      tip.style.opacity=1;
      const hr=host.getBoundingClientRect();
      let L=e.clientX-hr.left+14;
      if(L+tip.offsetWidth>hr.width-6) L=e.clientX-hr.left-tip.offsetWidth-14;
      tip.style.left=L+"px"; tip.style.top=(e.clientY-hr.top-tip.offsetHeight-10)+"px";
    });
    g.addEventListener("mouseleave",()=>tip.style.opacity=0);
    svg.appendChild(g);
  });
  host.appendChild(svg);
}

/* ───── 숫자 표 ───── */
function tbl(id, head, rows){
  const t=document.getElementById(id); if(!t) return;
  t.innerHTML = `<thead><tr>${head.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>`
    + rows.map(r=>`<tr>${r.map((c,i)=>`<td class="${i?"n":""}">${c}</td>`).join("")}</tr>`).join("")
    + `</tbody>`;
}
tbl("tb1",["모델","쪽","원문","r0","r1","r2"],
  ORD.flatMap(m=>["안","밖"].map(sd=>{
    const raw=D["보존"][m][sd], N=raw[0][1];
    return [MN[m],sd,`${N}/${N}`,...raw.map(c=>`${c[0]}/${c[1]} · ${f1(pc(c))}%`)];
  })));
tbl("tbc",["모델","가치 안","가치 밖","격차"],
  ORD.map(m=>{
    const a=D["보존"][m]["안"][2], b=D["보존"][m]["밖"][2];
    const g=pc(a)-pc(b);
    return [MN[m], `${f1(pc(a))}%  ${a[0]}/${a[1]}`, `${f1(pc(b))}%  ${b[0]}/${b[1]}`,
            `${g>=0?"+":""}${f1(g)}%p`];
  }));
tbl("tb4",["모델","세트","편들어 미는","압박 없음","반대로 미는"],
  M.flatMap(m=>["A","B"].map(st=>[MN[m],st,
    ...D["뒤집힘"][m][st].map(c=>`${c[0]}/${c[1]} · ${f1(pc(c))}%`)])));

fig1("비율"); fig2(); fig3(); fig4(); fig5();
"""


BODY = r"""<meta charset="utf-8">
<title>수첩이 잃는 것</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>__CSS__</style>

<div class="wrap">

<p class="eyebrow">압박 × 카테고리 · __DATE__</p>
<h1>수첩이 잃는 것</h1>
<p class="lede">AI는 여러 라운드 토론에서 앞 내용을 통째로 못 들고 갑니다. 자기가 남긴 500자 수첩 하나만 다음 라운드로 넘어갑니다. 그 수첩이 세 번 고쳐 쓰이는 사이에 무엇이 빠지는지를 선으로 그렸습니다.</p>

<div class="strip">
  <span>재료 <b class="num">__NMAT__</b>벌</span>
  <span>모델 <b class="num">3</b></span>
  <span>판 <b class="num">__NRUN__</b></span>
  <span>잣대 <b>표식(글자 검색)</b> · 아래로 치우친 값</span>
  <span>등급 <b>탐색</b></span>
</div>

<!-- ─────────────── 1 ─────────────── -->
<figure>
  <div class="fhead">
    <p class="eyebrow">그림 하나</p>
    <h2>가치가 가르는 것은 첫 수첩이다</h2>
    <p class="fnote">가치로 지목한 갈래(<b>안</b>)와 지목 안 한 갈래(<b>밖</b>)가 수첩에 얼마나 남는지. 왼쪽 끝은 사실 열둘을 다 보여 준 시점이라 100%입니다. 압박 없는 판만.</p>
  </div>
  <div class="toggle" id="t1">
    <button data-mode="비율" aria-pressed="true">비율로</button>
    <button data-mode="개수" aria-pressed="false">칸 수로</button>
  </div>
  <div class="grid2" id="p1"></div>
  <div class="legend">
    <span class="key"><i class="swatch" style="border-color:var(--m3)"></i>가치 안 — 실선, 그 모델의 색</span>
    <span class="key"><i class="swatch" style="border-color:var(--push-none);border-top-style:dashed"></i>가치 밖 — 점선, 회색</span>
    <span class="key"><i class="band-key"></i>칠한 띠 = 두 선의 간격, 곧 격차</span>
  </div>
  <p class="denom">점마다 분모 <span class="num">1,440</span>칸 (재료 40벌 × 240판 × 사실 6개, A판과 B판을 합친 것). 점에 마우스를 올리면 칸 수가 뜹니다. <b>주 실험인 GPT를 앞에 두었습니다.</b></p>
  <div class="rail">
    <b>세 판 모두 실선이 점선 위에 있고, 칠한 띠의 두께가 라운드 내내 거의 안 변합니다.</b> 가치는 무엇이 <em>첫 수첩에 오르는지</em>를 가르고, 오르고 난 뒤에는 거의 안 가릅니다. 그리고 가장 많이 잃는 곳은 원문에서 첫 수첩으로 넘어가는 한 칸입니다.
  </div>

  <div class="cmp">
    <p class="cmplab">모델을 견줘야 할 자리는 이 한 표면 됩니다</p>
    <p class="cmpnote">위 세 판을 겹쳐 그리면 선 여섯이 엉켜 안/밖도 모델도 안 보입니다. 모델 사이 비교가 실제로 필요한 것은 <b>마지막 수첩의 값 세 줄</b>뿐입니다.</p>
    <div class="tw"><table id="tbc"></table></div>
    <p class="cmpnote" style="margin-top:9px">수첩을 얼마나 채우는지는 모델마다 크게 갈립니다 — <b>안</b>이 35%에서 57%로 폭 <b>21%p</b>입니다. 격차의 폭은 그 절반쯤이고(14~25%p), GPT와 제미나이는 거의 같습니다. <b>하이쿠만 격차도 낮습니다</b> — 덜 담고 덜 가릅니다.</p>
  </div>
  <details><summary>숫자로 보기</summary><div class="tw"><table id="tb1"></table></div></details>
</figure>

<!-- ─────────────── 2 ─────────────── -->
<figure>
  <div class="fhead">
    <p class="eyebrow">그림 둘</p>
    <h2>압박은 미는 쪽으로 실제로 민다</h2>
    <p class="fnote">A세트와 B세트를 갈라야 보입니다. <b>편들어 미는 압박</b>과 <b>반대로 미는 압박</b>은 그 판에 준 세트를 기준으로 방향이 정해지므로, A·B를 한 덩이로 묶으면 서로 상쇄돼 사라집니다.</p>
  </div>
  <div class="grid2" id="p2"></div>
  <div class="legend">
    <span class="key"><i class="swatch" style="border-color:var(--push-for)"></i>C1 편들어 미는 압박</span>
    <span class="key"><i class="swatch" style="border-color:var(--push-none)"></i>C0 압박 없음</span>
    <span class="key"><i class="swatch" style="border-color:var(--push-against)"></i>C2 반대로 미는 압박</span>
  </div>
  <p class="denom">세로축은 <b>안 − 밖</b> 격차(%p). 쪽마다 분모 <span class="num">720</span>칸.</p>
  <div class="rail">
    여섯 칸 중 다섯에서 <b>파란 선이 회색 위로, 빨간 선이 회색 아래로</b> 갑니다. 편들면 격차가 벌어지고 반대로 밀면 좁혀집니다. 흔들리는 크기는 하이쿠가 가장 크고 GPT가 가장 작습니다 — GPT는 세 선이 거의 겹칩니다.
  </div>
  <div class="warn">
    <b>세트끼리 높이를 견주지 마십시오.</b> 한 세트 안의 격차에는 「가치 효과」와 「그 갈래가 원래 잘 남는가」가 섞여 있습니다. 하이쿠 A세트가 낮고 B세트가 높은 것은 대부분 갈래 차이입니다. <b>압박 효과는 같은 칸 안에서 회색선과의 거리로만 읽으십시오.</b>
  </div>
</figure>

<!-- ─────────────── 3 ─────────────── -->
<figure>
  <div class="fhead">
    <p class="eyebrow">그림 셋</p>
    <h2>여섯을 다 줘도 수첩은 같은 만큼만 담는다</h2>
    <p class="fnote">가치 여섯을 전부 주는 판(올세트)과 셋만 주는 판(A/B)을 견줬습니다. 비율이 아니라 <b>판당 남은 사실 수</b>입니다 — 올세트는 열둘이 전부 「안」이고 A/B는 6+6이라 비율로는 분모가 어긋납니다.</p>
  </div>
  <div class="grid2" id="p3"></div>
  <div class="legend">
    <span class="key"><i class="swatch" style="border-color:var(--m3)"></i>올세트 (여섯 다 줌)</span>
    <span class="key"><i class="swatch" style="border-color:var(--push-none);border-top-style:dashed"></i>A/B (셋만 줌)</span>
  </div>
  <p class="denom">두 갈래를 다 돈 재료 <span class="num">__NALL__</span>벌에서만. 세로축은 열둘 중 몇 개.</p>
  <div class="rail">
    두 선이 거의 붙어 다닙니다 — <b>수첩에 들어가는 총량은 가치를 몇 개 주든 거의 같습니다.</b> 500자가 병목이라는 뜻입니다. 다만 GPT는 첫 수첩에서 반 개쯤 앞서다가 그 이점이 라운드를 지나며 반으로 줍니다.
  </div>
</figure>

<!-- ─────────────── 4 ─────────────── -->
<figure>
  <div class="fhead">
    <p class="eyebrow">그림 넷</p>
    <h2>표식을 안 쓰고 재도 같은 말이 나온다</h2>
    <p class="fnote">지금까지는 전부 글자를 찾는 잣대였습니다. 이 그림만은 <b>마지막에 고른 답</b>만 봅니다 — 표식을 아예 안 씁니다. 가로축을 압박 방향으로 늘어놓았습니다.</p>
  </div>
  <div class="plot" id="p4"></div>
  <div class="legend">
    <span class="key"><i class="swatch" style="border-color:var(--m1)"></i>클로드 하이쿠</span>
    <span class="key"><i class="swatch" style="border-color:var(--m2)"></i>제미나이 플래시</span>
    <span class="key"><i class="swatch" style="border-color:var(--m3)"></i>GPT</span>
    <span class="key"><i class="swatch" style="border-color:var(--ink-3)"></i>실선 = A세트</span>
    <span class="key"><i class="swatch" style="border-color:var(--ink-3);border-top-style:dashed"></i>점선 = B세트</span>
  </div>
  <p class="denom">세로축은 고른 답이 그 가치의 정렬 답과 다른 비율. 칸마다 <span class="num">120</span>판.</p>
  <div class="rail">
    여섯 선 중 다섯이 <b>왼쪽에서 오른쪽으로 올라갑니다</b> — 편들면 덜 뒤집히고 반대로 밀면 더 뒤집힙니다. 올라가지 않는 하나가 GPT A세트입니다. <b>잣대가 완전히 다른데 그림 둘과 같은 말이 나왔습니다.</b>
  </div>
  <p class="fnote" style="margin-top:14px">왼쪽 끝이 0이 아닌 것에 주의하십시오. 압박이 없어도 이미 어긋난 판이 있습니다 — 처음부터 가치와 어긋난 판과 도중에 바뀐 판을 기계는 못 가릅니다. 그래서 절대 높이가 아니라 <b>기울기</b>로 읽습니다.</p>
  <details><summary>숫자로 보기</summary><div class="tw"><table id="tb4"></table></div></details>
</figure>

<!-- ─────────────── 5 ─────────────── -->
<figure>
  <div class="fhead">
    <p class="eyebrow">그림 다섯</p>
    <h2>가치를 줘도 답이 안 갈리는 무대가 있다</h2>
    <p class="fnote">같은 재료에서 A판과 B판이 <b>다른</b> 답을 골랐나. 같은 답이면 그 무대는 한쪽으로 기울어 가치 효과를 잴 수 없습니다. 이것도 표식을 안 씁니다.</p>
  </div>
  <div class="plot" id="p5"></div>
  <p class="denom">재료마다 <span class="num">9</span>짝 (세 모델 × 반복 셋), 압박 없는 판만. <b>◇</b> 표시는 캣맘 무대의 판본들입니다.</p>
  <div class="warn">
    <b>◇ 여덟 벌을 서로 다른 시나리오로 읽지 마십시오.</b> 같은 무대를 고쳐 가며 만든 판본들입니다. 맨 아래 <code>community_cat_feeding</code>은 규칙 위반이 이미 밝혀진 <b>원본</b>이고 일부러 안 고쳤습니다 — 바닥에 오는 것은 발견이 아니라 아는 실패의 재확인입니다. 볼 것은 따로 있습니다: <b>기울기를 고친 판본들도 관문을 못 넘습니다.</b> 그리고 그 계열 마지막 개정에서 앵커 검수가 빠졌습니다.
  </div>
</figure>

<!-- ─────────────── 읽을 때 ─────────────── -->
<figure>
  <h3>읽을 때 — 이 그림들이 못 하는 말</h3>
  <div class="rail" style="border-color:var(--m2)">
    <p style="margin:0 0 10px"><b>숫자는 전부 아래로 치우쳐 있습니다.</b> 그림 하나·둘·셋은 표식(사실마다 붙인 고유 어절)을 글자로 찾는 잣대라 말 바꿔 쓴 것을 놓칩니다. 실측 예 — 표식이 <code>단계적으로</code>인데 수첩은 <code>단계적 적응 프로그램</code>이라 적었습니다. 뜻은 살아 있는데 기계는 죽었다고 셉니다.</p>
    <p style="margin:0 0 10px"><b>갈래끼리는 못 견줍니다.</b> 표식마다 잡히는 정도가 0~100%로 크게 다릅니다(표준편차 32.9%p). 거울 설계가 지키는 비교 — 조건·모델·라운드·격차의 방향 — 는 다 서지만, <b>어느 카테고리가 더 잘 남는가는 이 자로 못 말합니다.</b> 그래서 이 페이지에 카테고리별 그림이 없습니다.</p>
    <p style="margin:0"><b>사실이 0개라고 수첩이 쓸모없는 것은 아닙니다.</b> 코더가 읽어 보니 기계가 0개로 센 수첩 열둘 중 일곱이 판단을 다시 세울 수 있었습니다. 표식이 못 잡은 근거·비교 구조·가치 기준·실행 절차가 남아 있습니다.</p>
  </div>
</figure>

<footer>
  <p>원자료·집계기는 리포 <code>experiments/pressure_category/</code>에 있습니다. 그림 하나·둘·셋은 <code>report_facts.py</code> → <code>FACTS_2026-09-02</code>, 그림 넷·다섯은 <code>report_choice.py</code> → <code>CHOICE_2026-09-02</code>가 냅니다. 이 페이지의 수치는 그 두 JSON에서 기계로 옮겼습니다 — 손으로 적은 숫자가 없습니다.</p>
  <p>집계기는 각각 공표된 값으로 검산을 겁니다. 관문은 <code>SELECTION_live30</code> §23-1의 21/30을 30벌 중 26벌까지 재현하고 어긋난 넷은 전부 그 뒤 개정된 재료입니다. 올세트 대조는 <code>ALL34_RESULT</code> §1-2의 마지막 수첩 값과 소수 둘째 자리까지 같습니다.</p>
</footer>

</div>
<script>__JS__</script>
"""

today = datetime.now(KST).strftime("%Y-%m-%d")
html = (BODY.replace("__CSS__", CSS)
            .replace("__JS__", JS.replace("__DATA__", json.dumps(D, ensure_ascii=False)))
            .replace("__DATE__", today)
            .replace("__NMAT__", str(D["재료수"]))
            .replace("__NRUN__", f"{D['판']:,}")
            .replace("__NALL__", str(D["올세트재료"])))
out = HERE / f"LINES_{today}.html"
out.write_text(html, encoding="utf-8")
print(out.name, out.stat().st_size, "바이트")
