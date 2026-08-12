const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const out = path.join(__dirname, 'figures');
const font = "'Malgun Gothic','Noto Sans KR',sans-serif";

function box(x,y,w,h,lines,stroke='#c5c3ba',fill='#fbfbfa') {
  const start = y + h/2 - (lines.length-1)*14;
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="16" fill="${fill}" stroke="${stroke}" stroke-width="3"/>`+
    lines.map((t,i)=>`<text x="${x+w/2}" y="${start+i*28}" text-anchor="middle" dominant-baseline="middle" font-size="21" fill="#202020">${t}</text>`).join('');
}

function design() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="560" viewBox="0 0 1500 560">
  <rect width="1500" height="560" fill="white"/><defs><marker id="a" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3z" fill="#898882"/></marker></defs>
  <g font-family="${font}"><text x="50" y="62" font-size="32" font-weight="700" fill="#202020">같은 조건에서 토론 실행기만 바꿔 비교</text>
  <text x="50" y="100" font-size="19" fill="#77756f">3개 이슈 · 동일 팩트와 배분 · 동일 모델 설정</text>
  ${box(55,190,220,210,['같은 입력','이슈 3개','팩트 · 배분 고정'],'#c5c3ba','#f3f2ef')}
  ${box(460,145,280,120,['저자 판','DelibTrace'],'#2a78d6')}${box(460,335,280,120,['우리 판','debate_engine'],'#eb6834')}
  ${box(925,190,220,210,['같은 판정','팩트 언급 여부','gpt-5'],'#c5c3ba','#f3f2ef')}
  ${box(1270,215,165,160,['비교','FAR','셀 그리드'],'#c5c3ba','#f8f7f3')}
  <g stroke="#898882" stroke-width="4" fill="none" marker-end="url(#a)"><path d="M275 295 L445 210"/><path d="M275 295 L445 390"/><path d="M740 205 L910 275"/><path d="M740 395 L910 320"/><path d="M1145 295 L1255 295"/></g>
  <text x="600" y="510" text-anchor="middle" font-size="20" fill="#77756f">바뀌는 것은 실행기 하나뿐</text></g></svg>`;
}

function chart() {
  const sets=[['0543',15,[0,.6,11/15,13/15],[1/15,11/15,12/15,13/15]],['0248',14,[0,.5,11/14,10/14],[0,.5,8/14,8/14]],['0262',11,[0,6/11,7/11,9/11],[0,8/11,9/11,8/11]]];
  const W=1500,H=560, top=170,bottom=475, panelW=410, gaps=[70,545,1020];
  let body=`<rect width="${W}" height="${H}" fill="white"/><g font-family="${font}"><text x="750" y="48" text-anchor="middle" font-size="30" font-weight="700" fill="#202020">토론이 시작되자 양쪽 모두 팩트 언급이 급감</text>`;
  body+=`<g font-size="18" fill="#202020"><line x1="470" y1="90" x2="520" y2="90" stroke="#2a78d6" stroke-width="5"/><circle cx="495" cy="90" r="7" fill="#2a78d6"/><text x="530" y="96">저자 판</text><line x1="650" y1="90" x2="700" y2="90" stroke="#eb6834" stroke-width="5"/><rect x="687" y="83" width="14" height="14" fill="#eb6834"/><text x="710" y="96">우리 판</text><rect x="830" y="80" width="48" height="20" fill="#2a78d6" opacity=".12"/><text x="888" y="96">±1팩트 범위</text><text x="1080" y="97" fill="#555">◆ 범위 밖 차이</text></g>`;
  const y=v=>bottom-v*(bottom-top); const labels=['초기','R1','R2','R3'];
  sets.forEach(([id,n,a,o],pi)=>{const left=gaps[pi], xs=[0,1,2,3].map(i=>left+35+i*110), band=1/n;
    body+=`<text x="${left+200}" y="145" text-anchor="middle" font-size="21" fill="#202020">이슈 ${id} · 팩트 ${n}</text>`;
    [0,.2,.4,.6,.8,1].forEach(v=>{body+=`<line x1="${left}" y1="${y(v)}" x2="${left+panelW}" y2="${y(v)}" stroke="#deddd8"/><text x="${left-12}" y="${y(v)+6}" text-anchor="end" font-size="16" fill="#77756f">${v.toFixed(1)}</text>`});
    const upper=a.map((v,i)=>`${xs[i]},${y(Math.min(1,v+band))}`).join(' '), lower=a.map((v,i)=>`${xs[3-i]},${y(Math.max(0,a[3-i]-band))}`).join(' '); body+=`<polygon points="${upper} ${lower}" fill="#2a78d6" opacity=".10"/>`;
    body+=`<polyline points="${a.map((v,i)=>`${xs[i]},${y(v)}`).join(' ')}" fill="none" stroke="#2a78d6" stroke-width="5"/><polyline points="${o.map((v,i)=>`${xs[i]},${y(v)}`).join(' ')}" fill="none" stroke="#eb6834" stroke-width="5"/>`;
    a.forEach((v,i)=>{body+=`<circle cx="${xs[i]}" cy="${y(v)}" r="7" fill="#2a78d6"/><rect x="${xs[i]-7}" y="${y(o[i])-7}" width="14" height="14" fill="#eb6834"/>`; if(Math.abs(v-o[i])>band+1e-6) body+=`<text x="${xs[i]}" y="${y(Math.max(v,o[i]))-25}" text-anchor="middle" font-size="22" fill="#555">◆</text>`; body+=`<text x="${xs[i]}" y="510" text-anchor="middle" font-size="18" fill="#77756f">${labels[i]}</text>`});
  });
  body+=`<text x="25" y="330" transform="rotate(-90 25 330)" text-anchor="middle" font-size="19" fill="#202020">FAR (높을수록 팩트 소실이 큼)</text></g></svg>`; return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">${body}`;
}

async function write(name, svg) { fs.writeFileSync(path.join(out,name+'.svg'),svg); await sharp(Buffer.from(svg)).png().toFile(path.join(out,name+'.png')); }
(async()=>{await write('F1_design',design()); await write('F2_far_by_stage',chart());})();
