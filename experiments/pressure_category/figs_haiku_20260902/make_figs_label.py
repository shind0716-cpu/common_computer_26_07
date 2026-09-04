"""라벨 한 문장 실험 그림 4장 — 세 조건(가치 문장 / 라벨 / 원칙 문장) 나란히. 값: JUDGED_rows.json + JUDGED_label_rows.json"""
import json, collections, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
for f in fm.findSystemFonts():
    if "NotoSansCJK" in f: fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.unicode_minus"] = False
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
BLUE_LT = "#86b6ef"
OUT = "/home/claude/figs/"
FOOT = "사람처럼 읽어 채점(소넷, 어느 조건인지 모르고 판정) · claude-haiku · 시나리오 11종 · 확정 아님(참고 수치)"
rows = json.load(open("/home/claude/judged/JUDGED_rows.json")) + json.load(open("/home/claude/judged_label/JUDGED_label_rows.json"))
COND = [("가치 문장 (항목 3개 집음)", "AB", BLUE), ("라벨 한 문장 (나는 ~이다)", "label", AQUA), ("원칙 문장 (격률 6개)", "belief", ORANGE)]
def g(cond, press): return [r for r in rows if r["cond"] == cond and r["press"] == press]
def mean(xs): return statistics.mean(xs)
def base(fig, ax, ygrid=True):
    fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    ax.yaxis.grid(ygrid, color=GRID, lw=1); ax.xaxis.grid(False); ax.set_axisbelow(True)
def save(fig, name): fig.savefig(OUT + name + ".png"); fig.savefig(OUT + name + ".svg"); plt.close(fig)

# ---- L1: 사실 곡선, 세 조건 × 압박 유무 (두 패널) ----
fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=200, sharey=True)
for ax, press, ttl in zip(axes, (False, True), ("압박 없음", "반대편 압박")):
    base(fig, ax)
    for name, cond, col in COND:
        gg = g(cond, press); ys = [12] + [mean([r["n_alive"][i] for r in gg]) for i in range(3)]
        ax.plot([0, 1, 2, 3], ys, color=col, lw=2, zorder=3, label=f"{name} (n={len(gg)})")
        ax.scatter([1, 2, 3], ys[1:], s=56, color=col, zorder=4, edgecolors=SURF, linewidths=2)
        ax.annotate(f"{ys[-1]:.1f}", (3, ys[-1]), xytext=(7, 0), textcoords="offset points", va="center", fontsize=10.5, color=INK, fontweight="semibold")
    ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["원문\n(12개)", "수첩 r0", "수첩 r1", "수첩 r2"], color=INK2, fontsize=10); ax.set_xlim(-0.15, 3.5)
    ax.set_ylim(0, 12.6); ax.set_yticks([0, 3, 6, 9, 12]); ax.set_title(ttl, loc="left", fontsize=12, color=INK, fontweight="semibold")
axes[0].set_ylabel("판당 남은 사실 (12개 중)", color=INK2, fontsize=10)
axes[0].legend(frameon=False, fontsize=9, loc="lower left", labelcolor=INK2)
fig.suptitle("문장을 주는 방식에 따라 수첩에 남는 사실", x=0.02, ha="left", fontsize=14, color=INK, fontweight="semibold")
fig.text(0.01, 0.01, FOOT, fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.95)); save(fig, "figL1_fact_curve_3cond")

# ---- L2: 편식 격차 (문장이 편드는 답 편 vs 반대), 압박 없음 ----
fig, ax = plt.subplots(figsize=(9, 4.8), dpi=200); base(fig, ax)
w, gap = 0.3, 0.03
for i, (name, cond, col) in enumerate(COND):
    gg = [r for r in g(cond, False) if r.get("in_alive")]
    a = mean([r["in_alive"][2] for r in gg]); b = mean([r["out_alive"][2] for r in gg])
    for j, (v, c2) in enumerate(((a, BLUE), (b, BLUE_LT))):
        xx = i + (j - 0.5) * (w + gap); ax.bar(xx, v, width=w, color=c2, zorder=3)
        ax.text(xx, v + 0.06, f"{v:.2f}", ha="center", va="bottom", fontsize=10.5, color=INK, fontweight="semibold")
    ax.text(i, 4.15, f"격차 {a-b:+.2f}", ha="center", fontsize=11, color=INK, fontweight="semibold")
    ax.text(i, -0.42, f"n={len(gg)}", ha="center", fontsize=8.5, color=MUTED)
ax.set_xticks(range(3)); ax.set_xticklabels([c[0] for c in COND], color=INK2, fontsize=10.5); ax.set_xlim(-0.6, 2.6)
ax.set_ylim(0, 4.6); ax.set_yticks([0, 1, 2, 3, 4]); ax.set_ylabel("마지막 수첩에 남은 사실 (각 6개 중)", color=INK2, fontsize=10)
ax.set_title("기억의 편식은 항목 낱말만 만든다 — 압박 없는 판", loc="left", fontsize=14, color=INK, fontweight="semibold", pad=14)
ax.legend(handles=[Patch(color=BLUE, label="문장이 편드는 답에 유리한 사실"), Patch(color=BLUE_LT, label="반대편 사실")], frameon=False, fontsize=9.5, loc="upper right", labelcolor=INK2)
fig.text(0.01, 0.01, FOOT + " · 원칙 문장의 '편드는 답'은 요한의 종이 예측(빗나간 것으로 판정됨) 기준", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); save(fig, "figL2_bias_3cond")

# ---- L3: 5분류, 시험 안 됨 분리 ----
fig, ax = plt.subplots(figsize=(10, 4.4), dpi=200); base(fig, ax, ygrid=False); ax.xaxis.grid(True, color=GRID); ax.spines["left"].set_visible(False)
cats = [("결정까지 바뀜", BLUE), ("말만 바뀜", ORANGE), ("왔다갔다", AQUA), ("안 바뀜", YELLOW)]
for bi, (name, cond, col) in enumerate(COND):
    gg = g(cond, True); room = [r for r in gg if r["stance"][0] not in ("모호", r["pushed"])]; n = len(room); c = collections.Counter(r["cls"] for r in room)
    y = 2 - bi; left = 0
    for cname, cc in cats:
        v = c.get(cname, 0) / n * 100
        if v == 0: continue
        ax.barh(y, v - 0.6, left=left + 0.3, height=0.5, color=cc, zorder=3)
        if v >= 6: ax.text(left + v / 2, y, f"{c[cname]}", ha="center", va="center", fontsize=10.5, color="white" if cc in (BLUE, ORANGE) else INK, fontweight="semibold")
        left += v
    ax.text(-1.5, y, f"{name}\n시험된 판 {n} (시험 안 됨 {len(gg)-n})", ha="right", va="center", fontsize=9.5, color=INK2)
ax.set_yticks([]); ax.set_ylim(-0.6, 2.6); ax.set_xlim(0, 100); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_title("반대편 압박을 받은 판은 어떻게 끝났나 — 처음부터 압박 쪽이던 판(시험 안 됨)은 뺌", loc="left", fontsize=13, color=INK, fontweight="semibold", pad=14)
ax.legend(handles=[Patch(color=cc, label=cn) for cn, cc in cats], frameon=False, fontsize=9.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, labelcolor=INK2)
fig.text(0.01, 0.01, FOOT, fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.05, 1, 1)); save(fig, "figL3_five_classes_3cond")

# ---- L4: 세 겹 요약 — 세 지표 × 세 조건 ----
fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), dpi=200)
gate_split = {"AB": 10 / 11, "label": 9 / 11, "belief": None}
def bias(cond):
    gg = [r for r in g(cond, False) if r.get("in_alive")]; return mean([r["in_alive"][2] for r in gg]) - mean([r["out_alive"][2] for r in gg])
def effect(cond):
    c0 = g(cond, False); pr = g(cond, True)
    if cond == "label": c0 = [r for r in c0 if r["own"]]; a = sum(r["final"] != r["own"] for r in c0)
    else: pmap = {(r["issue"], r["set"]): r["pushed"] for r in pr}; a = sum(r["final"] == pmap.get((r["issue"], r["set"])) for r in c0)
    b = sum(r["final"] == r["pushed"] for r in pr); return 100 * (b / len(pr) - a / len(c0))
panels = [("답을 가르나\n(11시나리오 중 갈린 수)", lambda c: gate_split[c] * 11 if gate_split[c] is not None else None, "{:.0f}", (0, 11.5)),
          ("기억을 편식시키나\n(편 − 반대, 마지막 수첩)", bias, "{:+.2f}", (-0.3, 1.4)),
          ("압박에 넘어가나\n(압박 효과, %p)", effect, "{:+.0f}", (0, 52))]
for ax, (ttl, fn, fmt, yl) in zip(axes, panels):
    base(fig, ax)
    for i, (name, cond, col) in enumerate(COND):
        v = fn(cond)
        if v is None:
            ax.text(i, yl[1] * 0.08, "관문\n없음", ha="center", fontsize=9, color=MUTED); continue
        ax.bar(i, v, width=0.55, color=col, zorder=3); ax.text(i, v + (yl[1] - yl[0]) * 0.02, fmt.format(v), ha="center", va="bottom", fontsize=11, color=INK, fontweight="semibold")
    ax.set_xticks(range(3)); ax.set_xticklabels(["가치 문장", "라벨", "원칙 문장"], color=INK2, fontsize=10); ax.set_ylim(*yl)
    ax.set_title(ttl, loc="left", fontsize=11, color=INK, fontweight="semibold")
    if yl[0] < 0: ax.axhline(0, color=AXIS, lw=1)
fig.suptitle("세 겹이 갈라진다: 답은 정체성이, 기억은 항목 낱말이, 버팀은 항목 낱말이", x=0.02, ha="left", fontsize=13.5, color=INK, fontweight="semibold")
fig.text(0.01, 0.01, FOOT + " · 원칙 문장은 갈림 관문을 안 거침", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 0.93)); save(fig, "figL4_three_layers")
print("ok")
