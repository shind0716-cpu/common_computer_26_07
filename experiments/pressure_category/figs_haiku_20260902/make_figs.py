"""하이쿠 정독 잣대 198판 — 발표용 정적 그림 3장. 원값: JUDGED_rows.json (combine.py 집계)."""
import json, collections, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in fm.findSystemFonts():
    if "NotoSansCJK" in f: fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
BLUE_LT = "#86b6ef"
FOOT = "사람처럼 읽어 채점(소넷, 어느 조건인지 모르고 판정) · claude-haiku · 시나리오 11종 · 198판 · 확정 아님(참고 수치) · 두 채점자 일치 κ 0.85"

rows = json.load(open("/home/claude/judged/JUDGED_rows.json"))
def g(cond, press): return [r for r in rows if r["cond"] == cond and r["press"] == press]
def mean(xs): return statistics.mean(xs)

def base(fig, ax):
    fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(AXIS); ax.spines[s].set_linewidth(1)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True)
    ax.xaxis.grid(False)

# ---------- 그림 1: 사실 곡선 ----------
fig, ax = plt.subplots(figsize=(9, 5.4), dpi=200); base(fig, ax)
x = [0, 1, 2, 3]; xt = ["원문\n(사실 12개)", "수첩 r0", "수첩 r1", "수첩 r2"]
series = [("가치 문장 · 압박 없음", "AB", False, BLUE, "-"), ("가치 문장 · 반대 압박", "AB", True, BLUE, (0, (4, 2))),
          ("원칙 문장 · 압박 없음", "belief", False, ORANGE, "-"), ("원칙 문장 · 반대 압박", "belief", True, ORANGE, (0, (4, 2)))]
for name, cond, press, col, ls in series:
    ys = [12] + [mean([r["n_alive"][i] for r in g(cond, press)]) for i in range(3)]
    ax.plot(x, ys, color=col, lw=2, ls=ls, solid_capstyle="round", zorder=3, label=f"{name} (n={len(g(cond, press))})")
    ax.scatter(x[1:], ys[1:], s=64, color=col, zorder=4, edgecolors=SURF, linewidths=2)
    dy = {"가치 문장 · 반대 압박": -7, "원칙 문장 · 압박 없음": 7}.get(name, 0)
    ax.annotate(f"{ys[-1]:.1f}", (3, ys[-1]), xytext=(8, dy), textcoords="offset points", va="center", fontsize=11, color=INK, fontweight="semibold")
ax.set_xticks(x); ax.set_xticklabels(xt, color=INK2, fontsize=10.5)
ax.set_ylim(0, 12.6); ax.set_yticks([0, 3, 6, 9, 12]); ax.set_xlim(-0.15, 3.45)
ax.set_ylabel("판당 남은 사실 (12개 중, 내용을 알아볼 수 있게 남은 것)", color=INK2, fontsize=10)
ax.set_title("수첩을 세 번 고쳐 쓰는 동안 사실은 얼마나 남나", loc="left", fontsize=14, color=INK, fontweight="semibold", pad=14)
ax.legend(frameon=False, fontsize=9.5, loc="lower left", labelcolor=INK2)
fig.text(0.01, 0.01, FOOT, fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("/home/claude/figs/fig1_fact_curve.png"); fig.savefig("/home/claude/figs/fig1_fact_curve.svg"); plt.close(fig)

# ---------- 그림 2: 편 / 반대 ----------
fig, ax = plt.subplots(figsize=(9, 5.0), dpi=200); base(fig, ax)
groups = [("가치 문장\n압박 없음", "AB", False), ("가치 문장\n반대 압박", "AB", True), ("원칙 문장\n압박 없음", "belief", False), ("원칙 문장\n반대 압박", "belief", True)]
w = 0.32; gap = 0.02
for i, (lab, cond, press) in enumerate(groups):
    gg = [r for r in g(cond, press) if r["pro_final"]]
    pro = mean([r["pro_final"][2] for r in gg]); con = mean([r["con_final"][2] for r in gg])
    for j, (v, col) in enumerate(((pro, BLUE), (con, BLUE_LT))):
        xx = i + (j - 0.5) * (w + gap)
        ax.bar(xx, v, width=w, color=col, zorder=3)
        ax.text(xx, v + 0.08, f"{v:.2f}", ha="center", va="bottom", fontsize=10.5, color=INK, fontweight="semibold")
    ax.text(i, -0.55, f"n={len(gg)}", ha="center", fontsize=8.5, color=MUTED)
ax.set_xticks(range(4)); ax.set_xticklabels([q[0] for q in groups], color=INK2, fontsize=10.5)
ax.set_ylim(0, 4.4); ax.set_yticks([0, 1, 2, 3, 4]); ax.set_xlim(-0.6, 3.6)
ax.set_ylabel("마지막 수첩에 남은 사실 (각 6개 중)", color=INK2, fontsize=10)
ax.set_title("남는 사실은 마지막 답에 유리한 쪽: 압박 없는 가치 문장 판에서만 뚜렷", loc="left", fontsize=14, color=INK, fontweight="semibold", pad=14)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=BLUE, label="마지막 답에 유리한 사실"), Patch(color=BLUE_LT, label="마지막 답에 불리한 사실")], frameon=False, fontsize=9.5, loc="upper right", labelcolor=INK2)
fig.text(0.01, 0.01, FOOT + " · 최종 답이 읽히는 판만", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("/home/claude/figs/fig2_pro_con.png"); fig.savefig("/home/claude/figs/fig2_pro_con.svg"); plt.close(fig)

# ---------- 그림 3: 5분류 ----------
fig, ax = plt.subplots(figsize=(9, 3.9), dpi=200); base(fig, ax); ax.yaxis.grid(False); ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
cats = [("결정까지 바뀜", BLUE), ("말만 바뀜", ORANGE), ("왔다갔다", AQUA), ("안 바뀜", YELLOW), ("처음부터 같은 편", MAGENTA)]
bars = [("가치 문장 반대 압박", "AB"), ("원칙 문장 반대 압박", "belief")]
for bi, (lab, cond) in enumerate(bars):
    gg = [r for r in rows if r["cond"] == cond and r["press"]]; n = len(gg)
    c = collections.Counter(r["cls"] for r in gg); left = 0
    y = 1 - bi
    for name, col in cats:
        v = c.get(name, 0) / n * 100
        if v == 0: continue
        ax.barh(y, v - 0.6, left=left + 0.3, height=0.5, color=col, zorder=3)
        if v >= 7: ax.text(left + v / 2, y, f"{c[name]}", ha="center", va="center", fontsize=10.5, color="white" if col in (BLUE, ORANGE) else INK, fontweight="semibold")
        left += v
    ax.text(-1.5, y, f"{lab}\n(n={n})", ha="right", va="center", fontsize=10.5, color=INK2)
ax.set_yticks([]); ax.set_ylim(-0.6, 1.6); ax.set_xlim(0, 100)
ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.spines["left"].set_visible(False)
ax.set_title("반대 압박을 받은 판은 어떻게 끝났나 (판 수)", loc="left", fontsize=14, color=INK, fontweight="semibold", pad=14)
ax.legend(handles=[Patch(color=col, label=name) for name, col in cats], frameon=False, fontsize=9.5, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=5, labelcolor=INK2)
fig.text(0.01, 0.01, FOOT, fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig("/home/claude/figs/fig3_five_classes.png"); fig.savefig("/home/claude/figs/fig3_five_classes.svg"); plt.close(fig)
print("ok")
