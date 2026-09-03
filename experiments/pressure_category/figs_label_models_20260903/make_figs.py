import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
fm.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':11,'axes.edgecolor':'#c9c8c1','axes.labelcolor':'#52514e','xtick.color':'#52514e','ytick.color':'#52514e','axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#fcfcfb','axes.facecolor':'#fcfcfb','axes.unicode_minus':False})
C={'haiku':'#2a78d6','gpt':'#eb6834','gemini':'#1baf7a'}; NAME={'haiku':'claude-haiku','gpt':'gpt','gemini':'gemini-flash'}
def finish(fig,name,title,sub):
    fig.suptitle(title,x=0.02,y=0.995,ha='left',fontsize=14,fontweight='bold',color='#0b0b0b')
    fig.text(0.02,0.925,sub,ha='left',fontsize=10,color='#52514e')
    fig.subplots_adjust(top=0.82)
    fig.savefig(name,dpi=160,bbox_inches='tight',pad_inches=0.3); plt.close(fig)
lab={'haiku':([7.58,5.65,4.67],[8.11,2.98,2.43]),'gpt':([8.86,8.38,8.08],[8.5,7.77,7.42]),'gemini':([7.09,5.74,5.15],[5.77,4.77,4.27])}
val={'haiku':([8.9,7.1,6.2],[9.0,4.4,3.2]),'gpt':([9.38,9.0,8.83],[9.39,8.89,8.68]),'gemini':([8.0,7.24,6.85],[8.11,7.08,6.55])}
fig,axs=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
for ax,i,t in zip(axs,(0,1),('압박 없음','반대편 압박')):
    for m in C:
        ax.plot([0,1,2],lab[m][i],'-o',color=C[m],lw=2,ms=6,label=f'{NAME[m]} · 라벨')
        ax.plot([0,1,2],val[m][i],'--',color=C[m],lw=1.6,alpha=0.55,label=f'{NAME[m]} · 가치 문장')
        ax.text(2.07,lab[m][i][2],f'{lab[m][i][2]:.1f}',color=C[m],va='center',fontsize=10)
    ax.set_xticks([0,1,2]); ax.set_xticklabels(['수첩 r0','수첩 r1','수첩 r2']); ax.set_ylim(0,12); ax.set_title(t,loc='left',fontsize=12,color='#0b0b0b'); ax.grid(axis='y',color='#ecebe6'); ax.set_xlim(-0.2,2.4)
axs[0].set_ylabel('판당 "있음" 사실 (12개 중)')
axs[0].legend(frameon=False,fontsize=9,loc='lower left')
finish(fig,'fig1_facts.png','그림 1. 수첩에 남은 사실 — 라벨 판(실선) vs 가치 문장 판(점선), 세 모델','정독 채점, 11시나리오. 세 모델 모두 라벨 판이 가치 문장 판보다 적게 남긴다. 보존 순서 gpt > gemini > haiku는 그대로.')
fig,ax=plt.subplots(figsize=(8.5,4.6))
ms=['haiku','gpt','gemini']; lb=[0.00,1.17,1.27]; vb=[1.13,1.50,2.79]; x=np.arange(3); w=0.34
ax.bar(x-w/2,lb,w,color=[C[m] for m in ms],label='라벨 한 문장')
ax.bar(x+w/2,vb,w,color=[C[m] for m in ms],alpha=0.4,hatch='///',edgecolor='#fcfcfb',label='가치 문장(항목 3개)')
for xi,v in zip(x-w/2,lb): ax.text(xi,v+0.06,f'{v:+.2f}',ha='center',fontsize=10,color='#0b0b0b')
for xi,v in zip(x+w/2,vb): ax.text(xi,v+0.06,f'{v:+.2f}',ha='center',fontsize=10,color='#52514e')
ax.set_xticks(x); ax.set_xticklabels([NAME[m] for m in ms]); ax.set_ylim(0,3.3); ax.axhline(0,color='#c9c8c1',lw=1); ax.grid(axis='y',color='#ecebe6')
ax.set_ylabel('편식 격차 = 문장 편 사실 − 반대편 사실 (각 6개 중)')
ax.legend(frameon=False,fontsize=10,loc='upper left')
finish(fig,'fig2_bias.png','그림 2. 라벨만 줘도 사실을 편식하나 — 마지막 수첩, 압박 없음','하이쿠는 0.00(9/2). gpt·gemini는 라벨만으로 +1.2. 항목 낱말(빗금)은 편식을 키우지만 만드는 것은 아니다.')
rows=[('haiku · 라벨 (54)',[20,11,11,1,11]),('gpt · 라벨 (48)',[3,4,1,26,14]),('gemini · 라벨 (30)',[3,2,5,17,3]),('gpt · 가치 문장 (66)',[0,4,6,46,10]),('gemini · 가치 문장 (66)',[5,10,15,32,2])]
cls=['결정까지 바뀜','말만 바뀜','왔다갔다','안 바뀜','처음부터 같은 편(시험 안 됨)']
cc=['#2a78d6','#eb6834','#1baf7a','#eda100','#c9c8c1']
fig,ax=plt.subplots(figsize=(10,4.8))
for j,(name,v) in enumerate(rows):
    tot=sum(v); left=0
    for k,(n,col) in enumerate(zip(v,cc)):
        p=n/tot*100
        ax.barh(j,p,left=left,color=col,edgecolor='#fcfcfb',lw=2,height=0.62)
        if p>5: ax.text(left+p/2,j,str(n),ha='center',va='center',fontsize=10,color='#fff' if k in(0,1) else '#0b0b0b')
        left+=p
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows]); ax.invert_yaxis(); ax.set_xlim(0,100); ax.set_xlabel('판 비율 (%)'); ax.grid(axis='x',color='#ecebe6')
ax.legend([Patch(color=c) for c in cc],cls,frameon=False,fontsize=9,ncol=5,loc='upper center',bbox_to_anchor=(0.5,-0.18))
finish(fig,'fig3_5class.png','그림 3. 반대편 압박의 끝 — 5분류','결정까지 바뀜: 하이쿠 20/54 · gpt 3/48 · gemini 3/30. 라벨 판은 같은 모델 가치 문장 판보다 조금 더 넘어간다.')
fig,axs=plt.subplots(1,2,figsize=(11,4.4))
ax=axs[0]; ax.bar([0,1,2],[9,8,5],color=[C[m] for m in ms],width=0.55)
for i,v in enumerate([9,8,5]): ax.text(i,v+0.2,f'{v}/11',ha='center',fontsize=11)
ax.set_xticks([0,1,2]); ax.set_xticklabels([NAME[m] for m in ms]); ax.set_ylim(0,11.5); ax.set_title('관문 — 라벨이 답을 가른 시나리오 (11 중)',loc='left',fontsize=12); ax.grid(axis='y',color='#ecebe6')
ax=axs[1]; names=['haiku\n라벨','gpt\n라벨','gemini\n라벨','gpt\n가치','gemini\n가치']; eff=[46,17,17,0,11]; cols=[C['haiku'],C['gpt'],C['gemini'],C['gpt'],C['gemini']]; al=[1,1,1,0.4,0.4]
for i,(v,c,a) in enumerate(zip(eff,cols,al)):
    ax.bar(i,v,color=c,alpha=a,width=0.55,hatch='' if a==1 else '///',edgecolor='#fcfcfb'); ax.text(i,v+1.2,f'{v:+d}%p',ha='center',fontsize=11)
ax.set_xticks(range(5)); ax.set_xticklabels(names); ax.set_ylim(0,55); ax.set_title('압박 효과 — 압박 쪽 답 비율의 증가',loc='left',fontsize=12); ax.grid(axis='y',color='#ecebe6')
finish(fig,'fig4_gate_effect.png','그림 4. 라벨은 답을 가르나, 압박에 얼마나 넘어가나','gemini는 라벨보다 원래 선호가 세다(5/11). 압박 효과는 라벨 > 가치 문장이 세 모델 공통 방향이나 gpt·gemini의 구간은 0 근처를 포함.')
# fig5 정성 기계 집계: 라벨 낱말 출현 + 수첩 동결 + 항복 문형
fig,ax=plt.subplots(figsize=(9,4.2))
cats=['글에 라벨 낱말\n(보수/진보)','수첩에 라벨 낱말','수첩 r1=r2\n글자까지 동일','글에 항복 문형\n("말씀이 맞다" 등)','반복 대본\n알아챔·메타 발언']
g=[94/114*100,91/114*100,28/114*100,0,0]; m=[91/96*100,95/96*100,25/96*100,0,0]
x=np.arange(5); w=0.36
ax.bar(x-w/2,g,w,color=C['gpt'],label='gpt (114판)'); ax.bar(x+w/2,m,w,color=C['gemini'],label='gemini-flash (96판)')
for xi,v in zip(x-w/2,g): ax.text(xi,v+1.5,f'{v:.0f}%',ha='center',fontsize=10)
for xi,v in zip(x+w/2,m): ax.text(xi,v+1.5,f'{v:.0f}%',ha='center',fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(cats,fontsize=9.5); ax.set_ylim(0,112); ax.set_ylabel('판 비율 (%)'); ax.grid(axis='y',color='#ecebe6'); ax.legend(frameon=False,loc='upper right')
finish(fig,'fig5_qual_machine.png','그림 5. 라벨 판 원문에서 기계로 센 것 (210판 전수)','라벨은 글·수첩에 거의 늘 실려 다음 라운드로 넘어간다. 항복 문장·메타 발언은 0.')
print('ok')
