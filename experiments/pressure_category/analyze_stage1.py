"""[공용 코어 · 압박×카테고리] 1차 1단계 판정 — 열쇠를 열고 H0·H3′·H6 를 잰다.

`SELECTION_live30_2026-08-27.md` §22-5 의 ⑤ 단계다. 판독(③④)이 닫힌 뒤에만 돌린다.

**이 파일은 결과를 보기 전에 커밋한다.** 사전고정이 층을 둘로 나눠 놓고
(§18-6-3 r0 진입 / 생존) 중단선은 「d > 0 이 16쌍 미만」이라고만 적어(§19-2)
어느 층에 거는지가 안 적혀 있다. 결과를 본 뒤 고르면 그게 사후 선택이므로 여기 못 박는다.

    2단계로 넘어가려면 **두 층 중 적어도 하나**에서 d > 0 이 16쌍 이상이어야 한다.
    둘 다 16 미만이면 나머지 960콜을 안 태우고 보고한다.

느슨한 쪽을 고른 이유: §19-2 가 밝힌 중단선의 목적이 "방향이 아예 안 서면 그만둔다"이고,
§18-6-3 이 "(i)이 본체일 수 있다"며 두 층이 갈릴 것을 이미 예상해 뒀다.
층별 판정(지지/부분지지/기각)은 §18-6-4 대로 **각 층에 따로** 매긴다.

눈금 — §18-6-3·§18-6-7-4:
    살았다 = 보존 ∪ 부분 ∪ 변형 · 죽었다 = 탈락
    (i) r0 진입  : r0 수첩에 올랐나                       분모 = 그 벌의 사실 전부
    (ii) 생존    : r0 에 오른 것이 마지막 수첩까지 갔나   분모 = r0 에 오른 것

짝 단위(§18-6-2) — 한 사실은 A판에서 안이면 B판에서 반드시 밖이다.
    d = p안 − p밖   (쌍 = 한 재료 × 한 모델, 사실마다 안 관측 1 · 밖 관측 1)

코더가 둘이라 **두 코더 각각으로 따로 낸다**(`READ60_kappa_all.md` 에 미리 적어 둔 절차).
방향이 같으면 보고하고 갈리면 「코더 의존」으로 적는다.

    python analyze_stage1.py
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
ALIVE = {"보", "부", "변"}
GARAE2 = {          # 갈래 둘 = 가치를 당사자에게 붙인 벌 (§2)
    "issue_cat_feeding_party", "issue_childcare_party", "issue_recycling_room_party",
    "issue_smoking_area_party", "issue_community_room", "issue_floor_noise",
    "issue_garden_plot",
}
HYUNSU = {"issue_ambulance", "issue_caregiverprotect", "issue_childcare", "issue_elderdrive",
          "issue_eol", "issue_euthanasia", "issue_remotewatch", "issue_workmind"}


def author(iid):
    if iid.startswith("issue_restaurant_"):
        return "그루"
    return "현수" if iid in HYUNSU else "요한"


def load_all():
    key = json.loads((ROOT / "READ60_key.json").read_text(encoding="utf-8"))
    conc = json.loads((ROOT / "CONCRETE_LIST_2026-08-27.json").read_text(encoding="utf-8"))["materials"]
    mats, runs = {}, {}
    for iid in key:
        d = json.loads((ROOT / "materials" / f"{iid}.json").read_text(encoding="utf-8"))
        order = list(conc[iid].keys())
        assert order == [f["id"] for f in d["facts"]], f"{iid} 사실 순서 어긋남"
        mats[iid] = {
            "facts": {f["id"]: f for f in d["facts"]},
            "order": order,
            "sets": {s: set(v["categories"]) for s, v in d["value_sets"].items()},
            "aligned": {s: v["aligned"] for s, v in d["value_sets"].items()},
            "options": d["options"],
        }
        for s in ("A", "B"):
            p = ROOT / "runs" / "gpt" / iid / f"run_C0_{s}_rep1.json"
            runs[(iid, s)] = json.loads(p.read_text(encoding="utf-8"))
    return key, mats, runs


def load_coding(prefix):
    """판독 6팩을 (재료, 슬롯) → {r0: [...], last: [...]} 로 모은다."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("chk", ROOT / "check_read60_coder.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = collections.defaultdict(dict)
    for b in (1, 2, 3):
        for tag in ("r0", "last"):
            rows, bad = m.parse(ROOT / f"{prefix}_b{b}_{tag}.txt")
            assert not bad, f"{prefix}_b{b}_{tag}: {bad}"
            for (mat, slot), (judg, label) in rows.items():
                iid = mat if mat.startswith("issue_") else f"issue_{mat}"
                out[(iid, slot)][tag] = judg
                out[(iid, slot)][tag + "_label"] = label
    return out


def pair_d(mats, coding, key, iid):
    """한 쌍의 d 를 두 층으로 낸다. 반환: (d_r0, d_surv, 진단)"""
    M = mats[iid]
    slot_of = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
    obs = {"in": {"r0": [], "surv": []}, "out": {"r0": [], "surv": []}}
    for s in ("A", "B"):
        j0 = coding[(iid, slot_of[s])]["r0"]
        jl = coding[(iid, slot_of[s])]["last"]
        for i, fid in enumerate(M["order"]):
            side = "in" if M["facts"][fid]["category"] in M["sets"][s] else "out"
            a0 = j0[i] in ALIVE
            obs[side]["r0"].append(a0)
            if a0:
                obs[side]["surv"].append(jl[i] in ALIVE)

    def p(side, layer):
        v = obs[side][layer]
        return (sum(v) / len(v)) if v else None

    d0 = None if None in (p("in", "r0"), p("out", "r0")) else p("in", "r0") - p("out", "r0")
    ds = None if None in (p("in", "surv"), p("out", "surv")) else p("in", "surv") - p("out", "surv")
    diag = {"p": {k: {l: p(k, l) for l in ("r0", "surv")} for k in ("in", "out")},
            "n": {k: {l: len(obs[k][l]) for l in ("r0", "surv")} for k in ("in", "out")}}
    return d0, ds, diag


def verdict(npos, n):
    if npos >= (2 * n) / 3:
        return "지지"
    if npos > n / 2:
        return "부분 지지"
    return "기각"


def main():
    key, mats, runs = load_all()
    iids = sorted(key)
    out = []
    W = out.append

    # ── 관문 (§15-4) ────────────────────────────────────────────────
    W("=" * 78)
    W("① 관문 — 같은 (재료·gpt) 에서 A 와 B 가 다른 옵션을 고르면 통과 (§15-4)")
    W("=" * 78)
    gate = {}
    for iid in iids:
        fa, fb = runs[(iid, "A")]["final_poll"], runs[(iid, "B")]["final_poll"]
        gate[iid] = fa != fb
        al = mats[iid]["aligned"]
        ta = "정렬" if fa == al["A"] else "역"
        tb = "정렬" if fb == al["B"] else "역"
        mark = "O" if gate[iid] else "X"
        W(f"  {mark} {iid:34s} A->{ta}  B->{tb}   {'다름' if fa != fb else '같음'}")
    W(f"\n  통과 {sum(gate.values())}/30 · 탈락 {30 - sum(gate.values())}")
    W("  ※ §18-6-7-1 대로 탈락 쌍도 H0 에 넣는다. 통과/탈락을 나눠 보고하되 판정은 전체로.")

    # ── 코더별 H0 ───────────────────────────────────────────────────
    res = {}
    for cname, prefix in (("코더 A", "READ60_coderA"), ("헤르메스", "READ60_hermes")):
        coding = load_coding(prefix)
        rows = {iid: pair_d(mats, coding, key, iid) for iid in iids}
        res[cname] = (coding, rows)
        W("")
        W("=" * 78)
        W(f"② H0 — {cname}. 쌍마다 d = p안 − p밖 (§18-6)")
        W("=" * 78)
        W(f"  {'재료':32s} {'r0 안':>6s} {'r0 밖':>6s} {'d':>7s} | {'생존 안':>7s} {'생존 밖':>7s} {'d':>7s}")
        for iid in iids:
            d0, ds, dg = rows[iid]
            pi, po = dg["p"]["in"], dg["p"]["out"]

            def f(x):
                return "   –  " if x is None else f"{x:6.2f}"

            def g(x):
                return "   –  " if x is None else f"{x:+6.2f}"
            W(f"  {iid:32s} {f(pi['r0'])} {f(po['r0'])} {g(d0)} |"
              f" {f(pi['surv'])} {f(po['surv'])} {g(ds)}")
        for idx, nm in ((0, "(i) r0 진입"), (1, "(ii) 생존")):
            vals = [rows[i][idx] for i in iids if rows[i][idx] is not None]
            pos = sum(1 for v in vals if v > 0)
            neg = sum(1 for v in vals if v < 0)
            zer = sum(1 for v in vals if v == 0)
            sv = sorted(vals)
            med = (sv[len(sv) // 2] if len(sv) % 2 else (sv[len(sv) // 2 - 1] + sv[len(sv) // 2]) / 2)
            W(f"\n  {nm}: 쌍 {len(vals)} · d>0 {pos} · d=0 {zer} · d<0 {neg} · 중앙 d {med:+.3f}")
            W(f"     판정 {verdict(pos, len(vals))}   (지지선 {-(-2 * len(vals) // 3)}쌍 · 과반 {len(vals) // 2 + 1}쌍)"
              f"{'   ⚠ 역전 1/4 이상 — 따로 보고' if neg >= len(vals) / 4 else ''}")
        p0 = sum(1 for i in iids if rows[i][0] is not None and rows[i][0] > 0)
        p1 = sum(1 for i in iids if rows[i][1] is not None and rows[i][1] > 0)
        W(f"\n  ▶ 2단계 진행 여부(머리말 규칙): max({p0}, {p1}) ≥ 16 → "
          f"{'진행' if max(p0, p1) >= 16 else '중단 — 나머지 960콜 안 태운다'}")

    # ── 딸림 ────────────────────────────────────────────────────────
    for cname in res:
        coding, rows = res[cname]
        W("")
        W("=" * 78)
        W(f"③ 딸림 — {cname}")
        W("=" * 78)
        for nm, sel in (("갈래 둘(7)", lambda i: i in GARAE2),
                        ("갈래 하나(5)", lambda i: author(i) == "요한" and i not in GARAE2),
                        ("요한(12)", lambda i: author(i) == "요한"),
                        ("현수(8)", lambda i: author(i) == "현수"),
                        ("그루(10)", lambda i: author(i) == "그루")):
            v0 = sorted(rows[i][0] for i in iids if sel(i) and rows[i][0] is not None)
            v1 = sorted(rows[i][1] for i in iids if sel(i) and rows[i][1] is not None)
            m0 = v0[len(v0) // 2] if len(v0) % 2 else (v0[len(v0) // 2 - 1] + v0[len(v0) // 2]) / 2
            m1 = v1[len(v1) // 2] if len(v1) % 2 else (v1[len(v1) // 2 - 1] + v1[len(v1) // 2]) / 2
            W(f"  {nm:14s} n={len(v0):2d}  r0 중앙 d {m0:+.3f} (d>0 {sum(1 for x in v0 if x > 0)})"
              f"   생존 중앙 d {m1:+.3f} (d>0 {sum(1 for x in v1 if x > 0)})")
        W("  ※ 현수는 만장이 아니라 §5 규칙상 다른 저자와 같은 표에 더하지 않는다 — 나란히만.")
        trio = ["issue_community_cat_feeding", "issue_cat_feeding_plainvalue", "issue_cat_feeding_party"]
        W("\n  캣맘 세 판본 (형태 효과와 갈래 효과를 가르는 자리, §15-3 H6):")
        for iid in trio:
            d0, ds, _ = rows[iid]
            W(f"    {iid:34s} r0 d {d0:+.3f} · 생존 d {ds:+.3f}")

        cnt = collections.defaultdict(collections.Counter)
        for iid in iids:
            M = mats[iid]
            slot_of = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
            for s in ("A", "B"):
                for tag in ("r0", "last"):
                    j = coding[(iid, slot_of[s])][tag]
                    for i, fid in enumerate(M["order"]):
                        side = "안" if M["facts"][fid]["category"] in M["sets"][s] else "밖"
                        cnt[(tag, side)][j[i]] += 1
        W("\n  H3′ — 「부분」이 가치 밖에 몰리나 (예상: 밖:안 ≥ 2:1)")
        for tag in ("r0", "last"):
            a, b = cnt[(tag, "안")], cnt[(tag, "밖")]
            r = (b["부"] / a["부"]) if a["부"] else float("inf")
            W(f"    {tag:5s} 부분 안 {a['부']:3d} · 밖 {b['부']:3d} → 밖:안 = {r:.2f}:1"
              f"   {'2:1 이상 O' if r >= 2 else '2:1 미만 X'}")
            W(f"          안 보{a['보']:3d}/부{a['부']:3d}/변{a['변']:3d}/탈{a['-']:3d}"
              f"  ·  밖 보{b['보']:3d}/부{b['부']:3d}/변{b['변']:3d}/탈{b['-']:3d}")

    # ── 기계값 대조 (§18-7) ────────────────────────────────────────
    W("")
    W("=" * 78)
    W("④ 기계값 대조 — 표식 문자열 검색 대 사람 판독 (코더 A 기준, §8-2)")
    W("=" * 78)
    tab = collections.Counter()
    for iid in iids:
        M = mats[iid]
        slot_of = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
        for s in ("A", "B"):
            note = runs[(iid, s)]["notes"][0]
            j = res["코더 A"][0][(iid, slot_of[s])]["r0"]
            for i, fid in enumerate(M["order"]):
                anc = M["facts"][fid].get("anchor")
                if not anc:
                    continue
                tab[(anc in note, j[i])] += 1
    hit = sum(v for (h, _), v in tab.items() if h)
    W(f"  표식 있음 {hit}칸 · 없음 {sum(tab.values()) - hit}칸 (표식 붙은 사실만)")
    for h in (True, False):
        row = {k[1]: v for k, v in tab.items() if k[0] == h}
        W(f"  표식 {'有' if h else '無'}: " + " · ".join(f"{x} {row.get(x, 0)}" for x in ("보", "부", "변", "-")))
    miss = sum(v for (h, x), v in tab.items() if not h and x in ALIVE)
    fp = sum(v for (h, x), v in tab.items() if h and x == "-")
    alive = sum(v for (_, x), v in tab.items() if x in ALIVE)
    W(f"  → 놓침 {miss}/{alive} = {miss / alive:.0%} · 오탐 {fp}/{hit} = {fp / hit:.0%}")

    # ── 분모 진단 (§15-4) ──────────────────────────────────────────
    W("")
    W("=" * 78)
    W("⑤ 분모 진단 — r0 수첩에 오른 사실이 3개 이하인 판 (§15-4)")
    W("=" * 78)
    thin = []
    for cname, (coding, rows) in res.items():
        for iid in iids:
            for slot in ("①", "②"):
                n = sum(1 for x in coding[(iid, slot)]["r0"] if x in ALIVE)
                if n <= 3:
                    thin.append((cname, iid, slot, n))
    W(f"  걸린 판 {len(thin)}" + ("" if thin else " — 없다"))
    for t in thin:
        W(f"    {t[0]} {t[1]} {t[2]} → r0 진입 {t[3]}")

    txt = "\n".join(out)
    (ROOT / "STAGE1_RESULT_2026-08-27.txt").write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
