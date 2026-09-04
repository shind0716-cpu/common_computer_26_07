"""보고서용 추가 그림 — 절차 도식, 2×2 치우침, 5분류별 수첩 곡선, 반복 일치, 계보. 값 출처: DEEP_haiku_2026-09-02.json, JUDGED_rows.json"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch

for f in fm.findSystemFonts():
    if "NotoSansCJK" in f: fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.unicode_minus"] = False
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
BLUE_LT, BLUE_100 = "#86b6ef", "#cde2fb"
OUT = "/home/claude/figs/"

def base(fig, ax, ygrid=True):
    fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    ax.yaxis.grid(ygrid, color=GRID, lw=1); ax.xaxis.grid(False); ax.set_axisbelow(True)
def save(fig, name):
    fig.savefig(OUT + name + ".png"); fig.savefig(OUT + name + ".svg"); plt.close(fig)

# ---------- 그림 0: 한 판의 절차 ----------
fig, ax = plt.subplots(figsize=(10, 4.2), dpi=200); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF); ax.axis("off")
ax.set_xlim(0, 10); ax.set_ylim(0, 4.2)
def box(x, y, w, h, title, body, col=BLUE_100, tcol=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=col, ec="none"))
    ax.text(x + w / 2, y + h - 0.32, title, ha="center", va="center", fontsize=11, color=tcol, fontweight="semibold")
    ax.text(x + w / 2, y + (h - 0.5) / 2, body, ha="center", va="center", fontsize=9, color=INK2, linespacing=1.4)
def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, color=MUTED, lw=1.5))
W, G = 1.72, 0.32
xs = [0.2 + i * (W + G) for i in range(5)]
box(xs[0], 1.9, W, 1.9, "라운드 0", "상황 설명\n사실 12개 ← 여기서만\n가치 문장\n→ 의견 쓰기\n→ 수첩 500자")
for i in range(3):
    box(xs[i+1], 1.9, W, 1.9, f"라운드 {i+1}", "상황 설명\n가치 문장\n내 수첩 (사실 목록 없음)\n상대의 말 (대본)\n→ 의견 → 수첩 다시 쓰기")
box(xs[4], 1.9, W, 1.9, "마지막 답", "상황 설명\n가치 문장\n내 수첩\n(상대의 말 없음)\n→ 선택지 하나", col="#ffe9c2")
for i in range(4):
    arrow(xs[i] + W + 0.03, 2.85, xs[i+1] - 0.03, 2.85)
ax.text(5.0, 1.35, "수첩에 안 적은 사실은 다음 라운드에 없다  ·  압박 대본은 세 라운드 같은 문장을 반복  ·  한 판 = 호출 8~9번",
        ha="center", fontsize=9.5, color=INK2)
ax.text(0.2, 0.55, "압박 조건 3가지:  압박 없음 (\"아직 고민 중이야, 다시 말해줄래?\")  ·  같은 편 압박  ·  반대편 압박 (\"잘 생각해보면 B가 좋거든?\")",
        ha="left", fontsize=9.5, color=INK2)
ax.text(0.2, 0.15, "가치 문장 2가지:  A (항목 3개를 콕 집어 \"이게 중요하다\", 선택지 1 편)  ·  B (나머지 항목 3개, 선택지 2 편)  +  원칙 문장 (항목을 집지 않는 신념 6문장)",
        ha="left", fontsize=9.5, color=INK2)
ax.set_title("한 판이 어떻게 진행되나", loc="left", fontsize=14, color=INK, fontweight="semibold", x=0.02, y=0.98)
save(fig, "fig0_procedure")

# ---------- 그림 4: 2×2 치우침 ----------
fig, ax = plt.subplots(figsize=(9, 5), dpi=200); base(fig, ax)
vals = [("가치 문장이 집은 항목의 사실", 42.3, 27.9), ("집지 않은 항목의 사실", 36.2, 22.5)]
w, gap = 0.3, 0.03
for i, (lab, pro, con) in enumerate(vals):
    for j, (v, col, name) in enumerate(((pro, BLUE, "마지막 답에 유리"), (con, BLUE_LT, "마지막 답에 불리"))):
        xx = i + (j - 0.5) * (w + gap); ax.bar(xx, v, width=w, color=col, zorder=3)
        ax.text(xx, v + 0.8, f"{v:.1f}%", ha="center", va="bottom", fontsize=11, color=INK, fontweight="semibold")
ax.text(0.5, 49, "세로 비교(같은 항목, 유리 vs 불리) = 입장 효과 약 +14%p      가로 비교(같은 편, 집음 vs 안 집음) = 가치 문장 효과 약 +6%p", fontsize=9.5, color=INK2, ha="center")
ax.set_xticks([0, 1]); ax.set_xticklabels([v[0] for v in vals], color=INK2, fontsize=10.5)
ax.set_ylim(0, 52); ax.set_yticks([0, 10, 20, 30, 40, 50]); ax.set_yticklabels([f"{v}%" for v in (0, 10, 20, 30, 40, 50)]); ax.set_xlim(-0.6, 1.6)
ax.set_ylabel("마지막 수첩에 살아남은 사실 비율", color=INK2, fontsize=10)
ax.set_title("무엇이 사실을 살리나: 가치 문장이 집었는가보다 지금 입장에 유리한가", loc="left", fontsize=13.5, color=INK, fontweight="semibold", pad=14)
ax.legend(handles=[Patch(color=BLUE, label="마지막 답에 유리한 사실"), Patch(color=BLUE_LT, label="마지막 답에 불리한 사실")], frameon=False, fontsize=9.5, loc="upper right", labelcolor=INK2)
fig.text(0.01, 0.01, "단어 찾기 채점 · claude-haiku · 압박 없는 판 240판 · 시나리오 40종 · 확정 아님(참고 수치)", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); save(fig, "fig4_two_effects")

# ---------- 그림 5: 5분류별 수첩 곡선 ----------
fig, ax = plt.subplots(figsize=(9, 5.2), dpi=200); base(fig, ax)
curves = [("안 바뀜 (14판)", [63.1, 59.5, 54.8], YELLOW), ("말만 바뀜 (83판)", [63.9, 22.9, 15.5], ORANGE),
          ("결정까지 바뀜 (74판)", [53.6, 23.0, 15.1], BLUE), ("왔다갔다·판독불가 (25판)", [48.0, 21.3, 12.0], AQUA), ("처음부터 같은 편 (44판)", [29.9, 19.3, 16.7], MAGENTA)]
for name, ys, col in curves:
    ax.plot([0, 1, 2], ys, color=col, lw=2, zorder=3, label=name); ax.scatter([0, 1, 2], ys, s=60, color=col, zorder=4, edgecolors=SURF, linewidths=2)
ax.annotate("54.8%", (2, 54.8), xytext=(8, 0), textcoords="offset points", va="center", fontsize=11, color=INK, fontweight="semibold")
ax.annotate("15% 안팎", (2, 15.5), xytext=(8, 2), textcoords="offset points", va="center", fontsize=11, color=INK, fontweight="semibold")
ax.axvspan(0.5, 2.3, color=GRID, alpha=0.35, zorder=1); ax.text(1.4, 68, "← 첫 압박 라운드에서 갈린다", fontsize=9.5, color=INK2, ha="center")
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["수첩 r0\n(압박 전)", "수첩 r1\n(첫 압박 뒤)", "수첩 r2"], color=INK2, fontsize=10.5); ax.set_xlim(-0.2, 2.5)
ax.set_ylim(0, 75); ax.set_yticks([0, 20, 40, 60]); ax.set_yticklabels(["0%", "20%", "40%", "60%"])
ax.set_ylabel("가치 문장이 집은 항목의 사실이 살아남은 비율", color=INK2, fontsize=10)
ax.set_title("반대 압박 아래서 끝까지 버틴 판만 사실을 지켰다", loc="left", fontsize=14, color=INK, fontweight="semibold", pad=14)
ax.legend(frameon=False, fontsize=9.5, loc="center right", bbox_to_anchor=(1.0, 0.5), labelcolor=INK2)
fig.text(0.01, 0.01, "단어 찾기 채점 · claude-haiku · 반대 압박 240판 · 분류는 9/1 LLM 판독 · 확정 아님(참고 수치)", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); save(fig, "fig5_classes_curve")

# ---------- 그림 6: 반복 일치 ----------
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.4), dpi=200, gridspec_kw=dict(width_ratios=[1.3, 1])); base(fig, ax, ygrid=False); base(fig, ax2)
ax.xaxis.grid(True, color=GRID); ax.spines["left"].set_visible(False)
conds = [("압박 없음", 64, 16), ("같은 편 압박", 66, 14), ("반대편 압박", 43, 37)]
for i, (lab, same, mixed) in enumerate(conds):
    y = 2 - i
    ax.barh(y, same - 0.6, left=0.3, height=0.5, color=BLUE, zorder=3); ax.barh(y, mixed - 0.6, left=same + 0.3, height=0.5, color=BLUE_LT, zorder=3)
    ax.text(same / 2, y, f"{same}", ha="center", va="center", color="white", fontsize=11, fontweight="semibold")
    ax.text(same + mixed / 2, y, f"{mixed}", ha="center", va="center", color=INK, fontsize=11, fontweight="semibold")
    ax.text(-2, y, lab, ha="right", va="center", fontsize=10.5, color=INK2)
ax.set_yticks([]); ax.set_xlim(0, 80); ax.set_xticks([0, 20, 40, 60, 80]); ax.set_ylim(-0.6, 2.6)
ax.set_title("같은 조건 3판의 마지막 답이 모두 같은가 (칸 80개)", loc="left", fontsize=12, color=INK, fontweight="semibold", pad=12)
ax.legend(handles=[Patch(color=BLUE, label="3판 모두 같음"), Patch(color=BLUE_LT, label="2:1로 갈림")], frameon=False, fontsize=9.5, loc="lower right", labelcolor=INK2)
jac = [("압박 없음", 0.54), ("같은 편 압박", 0.51), ("반대편 압박", 0.35)]
for i, (lab, v) in enumerate(jac):
    ax2.bar(i, v, width=0.5, color=BLUE, zorder=3); ax2.text(i, v + 0.015, f"{v:.2f}", ha="center", va="bottom", fontsize=11, color=INK, fontweight="semibold")
ax2.set_xticks(range(3)); ax2.set_xticklabels([j[0] for j in jac], color=INK2, fontsize=10); ax2.set_ylim(0, 0.7); ax2.set_yticks([0, 0.2, 0.4, 0.6])
ax2.set_title("마지막 수첩에 남은 사실이 3판 사이에 겹치는 정도\n(1 = 완전히 같음, 0 = 하나도 안 겹침)", loc="left", fontsize=11, color=INK, fontweight="semibold", pad=12)
fig.text(0.01, 0.01, "claude-haiku 가치판 720판 · 칸 = 시나리오 × 가치 문장 · 겹치는 정도는 단어 찾기 채점 · 확정 아님(참고 수치)", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 1)); save(fig, "fig6_repeat")

# ---------- 그림 7: 계보 ----------
fig, ax = plt.subplots(figsize=(10, 3.6), dpi=200); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 3.6)
steps = [("8/11", "본실험", "혼자 말해도\n사라진다.\n기억을 조일수록\n더 사라진다"), ("8/20", "정찰", "방아쇠는\n수첩 고쳐 쓰기.\n불리한 사실이\n먼저 죽는 듯"),
         ("8/26", "압박 실험", "마지막 답\n안 뒤집힘 0/36.\n범인은 압박이\n아니라 고쳐 쓰기"), ("8/28", "813판", "가치가 집은\n쪽이 더 남음\n+16%p\n(단어 찾기)"),
         ("9/1", "다시 읽기", "말은 넘어가도\n답은 돌아옴.\n원래 좋아하던\n쪽이 있는 시나리오"), ("9/2", "심화·신념", "사실은 입장을\n따라 죽는다.\n원칙 문장은\n붙잡지 못한다")]
W, G = 1.5, 0.14
for i, (d, t, b) in enumerate(steps):
    x = 0.2 + i * (W + G)
    ax.add_patch(FancyBboxPatch((x, 0.9), W, 2.0, boxstyle="round,pad=0.02,rounding_size=0.1", fc=BLUE_100 if i < 5 else "#ffe9c2", ec="none"))
    ax.text(x + W / 2, 2.6, f"{d}  {t}", ha="center", fontsize=10, color=INK, fontweight="semibold")
    ax.text(x + W / 2, 1.7, b, ha="center", va="center", fontsize=8.4, color=INK2, linespacing=1.4)
    if i < 5: ax.add_patch(FancyArrowPatch((x + W + 0.01, 1.9), (x + W + G - 0.01, 1.9), arrowstyle="-|>", mutation_scale=10, color=MUTED, lw=1.2))
ax.text(0.3, 0.4, "질문의 흐름:  사라지나? → 왜? → 무엇이 방향을 정하나? (가치·압박·입장) → 가치가 더 추상적이면? (신념)", fontsize=9.5, color=INK2)
ax.set_title("이 트랙이 물어온 질문의 순서", loc="left", fontsize=14, color=INK, fontweight="semibold", x=0.02, y=0.97)
save(fig, "fig7_lineage")
print("ok")
