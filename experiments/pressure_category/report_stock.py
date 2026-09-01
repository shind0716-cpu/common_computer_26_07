"""[공용 코어 · 압박×카테고리] 보고서 재료 — 인용할 수치를 한자리에 찍는다 (콜 0).

## 왜 있나

보고서를 쓰는 사람이 수치를 찾으러 문서 열 편을 열어야 했다. 게다가 어떤 수치는
세션 대화에만 있다가 사라졌다. 이 파일은 **보고서가 인용할 만한 수치를 전부, 한 번에,
같은 기준으로** 찍는다. 글은 안 쓴다 — 재료만 만든다.

## 기준 (섞지 않는다)

  뜻 기준   코더 둘이 수첩을 읽어 매긴 `보존/부분/변형/탈락`. **주 지표.**
            쓸 수 있는 것은 판독과 재료가 맞는 **22벌 44판**뿐이다(`ALIGNMENT` §②).
  글자 기준  표식을 수첩에서 글자로 찾은 것. **보조·탐색 등급.** 판 수가 많다.

표마다 머리에 어느 기준인지 적는다. 두 기준의 수를 한 표에 같이 놓지 않는다.

## 무엇을 찍나

  A 범위        무엇을 몇 판 쟀나 · 22벌 명단
  B 주 결과     H0 두 층 × 코더 둘 (짝 단위 격차, 부호검정)
  C 총량        준 가치 셋 중 몇 개가 남았나 · 안 준 셋은 몇 개
  D 어떤 가치   카테고리 이름별 생존 — 줬을 때 대 안 줬을 때
  E 관문        최종 선택이 갈린 쌍과 안 갈린 쌍
  F 잣대        표식과 판독을 맞대 본 표
  G 주는 방식   올세트 · 신념 (글자 기준)
  H 모델        세 모델 공통 재료 (글자 기준)
  I 수첩 원문   A판·B판 짝으로 인용할 수 있게 그대로
  J 한계        수치에 붙는 단서

사용: PYTHONUTF8=1 python experiments/pressure_category/report_stock.py
산출: STOCK_2026-09-01.md
"""
from __future__ import annotations

import collections
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aggregate_all11 as A  # noqa: E402
import analyze_stage1 as S  # noqa: E402

OUT = HERE / "STOCK_2026-09-01.md"
ALIVE = S.ALIVE
# 앞의 둘은 정렬된 22벌(뜻 기준 수치에 든다), 뒤의 넷은 재료가 개정된 벌이라
# 원자료는 현행이지만 판독이 없다 — 인용할 때 그 차이를 표시한다.
CASES = ["issue_restaurant_date", "issue_recycling_room",
         "issue_childcare", "issue_workmind", "issue_eol", "issue_elderdrive"]
NICE = {"issue_restaurant_date": "식당·데이트", "issue_recycling_room": "재활용실",
        "issue_childcare": "육아", "issue_workmind": "직장상담",
        "issue_eol": "임종돌봄", "issue_elderdrive": "고령운전"}


def load_aligned():
    """판독과 재료가 맞는 벌만. 어긋난 여덟 벌은 뜻 기준 수치를 낼 수 없다."""
    key = json.loads((HERE / "READ60_key.json").read_text(encoding="utf-8"))
    conc = json.loads((HERE / "CONCRETE_LIST_2026-08-27.json").read_text(encoding="utf-8"))["materials"]
    stem = {}
    for p in (HERE / "materials").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("issue_id") and p.stem in conc:
            stem[d["issue_id"]] = p.stem
    mats, drift = {}, []
    for iid in key:
        d = json.loads((HERE / "materials" / f"{stem[iid]}.json").read_text(encoding="utf-8"))
        order = list(conc[stem[iid]].keys())
        if order != [f["id"] for f in d["facts"]]:
            drift.append(iid)
            continue
        mats[iid] = {"facts": {f["id"]: f for f in d["facts"]}, "order": order,
                     "cats": d["categories"], "options": d["options"],
                     "sets": {s: set(v["categories"]) for s, v in d["value_sets"].items()},
                     "aligned": {s: v["aligned"] for s, v in d["value_sets"].items()}}
    runs = {(i, s): json.loads((HERE / "runs/gpt" / i / f"run_C0_{s}_rep1.json").read_text(encoding="utf-8"))
            for i in mats for s in "AB"}
    return key, mats, drift, runs


def sign_p(pos, neg):
    n = pos + neg
    if n == 0:
        return 1.0
    lo = min(pos, neg)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(lo + 1)) / 2 ** n)


def kappa(cod, key, ids):
    """코더 둘의 Cohen κ. **범위를 준 ids 로만 잰다** — 22벌 표에 30벌 값을 앉히지 않는다."""
    a, b = [], []
    for iid in ids:
        slot = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
        for s in "AB":
            for tag in ("r0", "last"):
                a += cod["코더 A"][(iid, slot[s])][tag]
                b += cod["헤르메스"][(iid, slot[s])][tag]
    n = len(a)
    cats = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return n, (po - pe) / (1 - pe)


def side_of(M, s, fid):
    return "안" if M["facts"][fid]["category"] in M["sets"][s] else "밖"


def main() -> int:
    key, mats, drift, runs = load_aligned()
    cod = {n: S.load_coding(p) for n, p in (("코더 A", "READ60_coderA"), ("헤르메스", "READ60_hermes"))}
    gate = {i for i in mats if runs[(i, "A")]["final_poll"] != runs[(i, "B")]["final_poll"]}
    nk, kap = kappa(cod, key, sorted(mats))

    L = [f"# 보고서 재료 — 인용할 수치 (2026-09-01, 기계 생성물)", "",
         "> `report_stock.py` 가 찍는다. **글이 아니라 재료다.** 표마다 머리에 어느 기준인지 적혀 있고,",
         "> 뜻 기준(판독)과 글자 기준(표식)의 수를 한 표에 같이 놓지 않았다.",
         "> 무엇을 인용해도 되는지는 `ALIGNMENT_2026-09-01.md` 가 정한다.", ""]

    # ── A 범위
    L += ["## A. 범위", "",
          f"뜻 기준으로 쓸 수 있는 것은 **{len(mats)}벌 {2*len(mats)}판**이다. "
          f"1차는 30벌이었으나 {len(drift)}벌은 판정 뒤에 재료가 개정되어 판독이 옛 재료 기준이라 뺐다.", "",
          "| | |", "|---|---|",
          f"| 모델 | `gpt-5.4-mini` · 온도 0.7 |",
          f"| 조건 | 압박 없음(C0) × 가치 세트 A·B × 반복 1 |",
          f"| 판 | {2*len(mats)} (재료 {len(mats)}벌 × 2) |",
          f"| 판독 칸 | {len(mats)*2*12*2:,} (사실 12 × 판 {2*len(mats)} × 첫·마지막 수첩) |",
          f"| 코더 | 2인 독립 · **이 22벌 1,056칸 일치도 κ {kap:.3f}** |",
          f"| 뺀 벌 | {', '.join(x.replace('issue_','') for x in sorted(drift))} |", "",
          "**쓴 22벌**: " + ", ".join(sorted(x.replace("issue_", "") for x in mats)), "",
          f"> κ 주의 — 위 값은 **이 22벌 {nk:,}칸**으로 다시 잰 것이다. 1차 전체 30벌 1,424칸은 κ 0.817 이다.",
          "> 범위가 다른 두 값이라 섞어 쓰지 않는다 (2026-09-01 피어 감사 지적).", ""]

    # ── B 주 결과
    rows = []
    for cn, cd in cod.items():
        lay = {"r0": [], "sv": []}
        for iid in sorted(mats):
            M = mats[iid]
            slot = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
            obs = {"안": {"r0": [], "sv": []}, "밖": {"r0": [], "sv": []}}
            for s in "AB":
                j0, jl = cd[(iid, slot[s])]["r0"], cd[(iid, slot[s])]["last"]
                for i, fid in enumerate(M["order"]):
                    sd = side_of(M, s, fid)
                    up = j0[i] in ALIVE
                    obs[sd]["r0"].append(up)
                    if up:
                        obs[sd]["sv"].append(jl[i] in ALIVE)
            r = lambda L_: (sum(L_) / len(L_)) if L_ else None
            lay["r0"].append(r(obs["안"]["r0"]) - r(obs["밖"]["r0"]))
            a, b = r(obs["안"]["sv"]), r(obs["밖"]["sv"])
            lay["sv"].append(None if a is None or b is None else a - b)
        for k, nm in (("r0", "(i) 첫 수첩에 올랐나"), ("sv", "(ii) 오른 것이 끝까지 살았나")):
            v = [x for x in lay[k] if x is not None]
            pos = sum(1 for x in v if x > 0)
            neg = sum(1 for x in v if x < 0)
            rows.append((cn, nm, len(v), pos, neg, len(v) - pos - neg,
                         statistics.median(v), sign_p(pos, neg)))
    L += ["## B. 주 결과 — 가치가 사실의 운명을 가르나", "",
          "**뜻 기준.** 짝 단위로 「가치 안이었을 때 생존율 − 가치 밖이었을 때 생존율」을 낸다.",
          "같은 사실을 A판에서 한 번, B판에서 한 번 보므로 사실 자체의 살아남기 쉬움과 재료 기울기가 상쇄된다.", "",
          "| 코더 | 층 | 쌍 | 양수 | 음수 | 동점 | 중앙 | 부호검정 p |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for cn, nm, n, pos, neg, tie, med, p in rows:
        L.append(f"| {cn} | {nm} | {n} | **{pos}** | {neg} | {tie} | {med:+.3f} | {p:.2g} |")

    # 보조 비율
    L += ["", "### B-1. 같은 것을 비율로", "",
          "| 코더 | 첫 수첩 진입 안 | 밖 | 진입분 생존 안 | 밖 | 첫 수첩 탈락 안 | 밖 |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    aux = {}
    for cn, cd in cod.items():
        C = collections.Counter()
        for iid in sorted(mats):
            M = mats[iid]
            slot = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
            for s in "AB":
                j0, jl = cd[(iid, slot[s])]["r0"], cd[(iid, slot[s])]["last"]
                for i, fid in enumerate(M["order"]):
                    sd = side_of(M, s, fid)
                    C[(sd, "전체")] += 1
                    up = j0[i] in ALIVE
                    C[(sd, "진입")] += up
                    if up:
                        C[(sd, "생존")] += jl[i] in ALIVE
                    C[(sd, "마지막")] += jl[i] in ALIVE
                    if j0[i] == "부":
                        C[(sd, "부분")] += 1
        f = lambda a, b: 100 * C[a] / C[b]
        aux[cn] = C
        L.append(f"| {cn} | {f(('안','진입'),('안','전체')):.1f}% | {f(('밖','진입'),('밖','전체')):.1f}% | "
                 f"{100*C[('안','생존')]/C[('안','진입')]:.1f}% | {100*C[('밖','생존')]/C[('밖','진입')]:.1f}% | "
                 f"{100-f(('안','진입'),('안','전체')):.1f}% | {100-f(('밖','진입'),('밖','전체')):.1f}% |")
    L += ["", "| 코더 | 첫 수첩 격차 | 마지막 격차 | 첫 수첩 몫 | 「부분」 밖:안 |", "|---|---:|---:|---:|---:|"]
    for cn, C in aux.items():
        f = lambda a, b: 100 * C[a] / C[b]
        g0 = f(("안", "진입"), ("안", "전체")) - f(("밖", "진입"), ("밖", "전체"))
        gl = f(("안", "마지막"), ("안", "전체")) - f(("밖", "마지막"), ("밖", "전체"))
        L.append(f"| {cn} | {g0:+.1f}%p | {gl:+.1f}%p | **{100*g0/gl:.0f}%** | "
                 f"{C[('밖','부분')]}:{C[('안','부분')]} = {C[('밖','부분')]/max(C[('안','부분')],1):.2f}:1 |")

    # ── C 총량
    L += ["", "## C. 총량 — 준 가치 셋 중 몇 개가 남았나", "",
          "**뜻 기준 · 마지막 수첩.** 카테고리가 살아남았다 = 그 카테고리의 사실 둘 중 하나 이상이 남았다.", "",
          "| 코더 | 무엇을 세나 | 셋 다 | 둘 | 하나 | 없음 | 평균 |", "|---|---|---:|---:|---:|---:|---:|"]
    for cn, cd in cod.items():
        din, dout = collections.Counter(), collections.Counter()
        for iid in sorted(mats):
            M = mats[iid]
            slot = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
            for s in "AB":
                jl = cd[(iid, slot[s])]["last"]
                by = collections.defaultdict(list)
                for i, fid in enumerate(M["order"]):
                    by[M["facts"][fid]["category"]].append(jl[i] in ALIVE)
                din[sum(1 for c in M["sets"][s] if any(by[c]))] += 1
                dout[sum(1 for c in M["cats"] if c not in M["sets"][s] and any(by[c]))] += 1
        for nm, d in (("준 가치 셋", din), ("안 준 가치 셋", dout)):
            n = sum(d.values())
            L.append(f"| {cn} | {nm} | {d[3]} | {d[2]} | {d[1]} | {d[0]} | "
                     f"**{sum(k*v for k, v in d.items())/n:.2f} / 3** |")

    # ── D 어떤 가치
    catf = collections.defaultdict(lambda: [0, 0, 0, 0])
    where = collections.defaultdict(set)
    cd = cod["코더 A"]
    for iid in sorted(mats):
        M = mats[iid]
        slot = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
        for s in "AB":
            jl = cd[(iid, slot[s])]["last"]
            for i, fid in enumerate(M["order"]):
                c = M["facts"][fid]["category"]
                where[c].add(iid)
                a = jl[i] in ALIVE
                if c in M["sets"][s]:
                    catf[c][0] += a; catf[c][1] += 1
                else:
                    catf[c][2] += a; catf[c][3] += 1
    big = sorted(((c, v) for c, v in catf.items() if len(where[c]) >= 3),
                 key=lambda x: -(x[1][2] / max(x[1][3], 1)))
    L += ["", "## D. 어떤 가치가 살아남나", "",
          "**뜻 기준 · 마지막 수첩 · 사실 단위 · 코더 A.** 이름이 같은 카테고리를 재료를 가로질러 모았다.",
          "재료 셋 이상에 나오는 이름만 싣는다 — 하나에만 나오는 이름은 분모가 2~4라 못 읽는다.", "",
          "| 가치 | 재료 | 줬을 때 | 안 줬을 때 | 차이 | 나오는 재료 |",
          "|---|---:|---:|---:|---:|---|"]
    for c, v in big:
        pi, po = 100 * v[0] / v[1], 100 * v[2] / v[3]
        ms = ", ".join(sorted(x.replace("issue_", "").replace("restaurant_", "r_") for x in where[c]))
        L.append(f"| **{c}** | {len(where[c])} | {pi:.0f}% ({v[0]}/{v[1]}) | {po:.0f}% ({v[2]}/{v[3]}) | "
                 f"**{pi-po:+.0f}%p** | {ms} |")
    L += ["",
          "⚠ **교락**: 차이가 큰 쪽(가격·프라이버시·메뉴다양성·신속함)은 식당 재료, 작은 쪽(위생·평온·안전·이동권)은",
          "공동체 재료에 몰려 있다. 저자와 계열이 섞였다. 다만 **접근성은 두 계열에 다 나오고**(재료 11벌) 차이가 크다."]

    # ── E 관문
    L += ["", "## E. 관문 — 최종 선택이 갈렸나", "",
          "**뜻 기준 · 첫 수첩 층 · 코더 A.** 관문 = 같은 재료에서 A와 B가 다른 답을 골랐나.", "",
          "| | 쌍 | 중앙 격차 | 양수 |", "|---|---:|---:|---:|"]
    dvals = {}
    for iid in sorted(mats):
        M = mats[iid]
        slot = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
        ins, outs = [], []
        for s in "AB":
            j0 = cd[(iid, slot[s])]["r0"]
            for i, fid in enumerate(M["order"]):
                (ins if side_of(M, s, fid) == "안" else outs).append(j0[i] in ALIVE)
        dvals[iid] = sum(ins) / len(ins) - sum(outs) / len(outs)
    for nm, sel in (("통과 — 답이 갈림", gate), ("탈락 — 답이 같음", set(mats) - gate)):
        v = [dvals[i] for i in sel]
        L.append(f"| {nm} | {len(v)} | {statistics.median(v):+.3f} | {sum(1 for x in v if x > 0)}/{len(v)} |")
    L.append("")
    L.append("**답이 같아진 쌍에서도 기억은 갈린다** — 격차는 작지만 방향이 전부 선다.")

    # ── F 잣대
    T = collections.Counter()
    for iid in sorted(mats):
        M = mats[iid]
        slot = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
        for s in "AB":
            note = (runs[(iid, s)].get("notes") or [""])[0]
            j0 = cd[(iid, slot[s])]["r0"]
            for i, fid in enumerate(M["order"]):
                hit = 0 < A.probe(M["facts"][fid]["anchor"], note)[0] <= 2
                T[("有" if hit else "無", j0[i])] += 1
    have = sum(v for k, v in T.items() if k[0] == "有")
    alive = sum(v for k, v in T.items() if k[1] in ALIVE)
    miss = sum(v for k, v in T.items() if k[0] == "無" and k[1] in ALIVE)
    false = T[("有", "-")]
    L += ["", "## F. 잣대 — 표식과 판독을 맞대면", "",
          f"**첫 수첩 {sum(T.values())}칸 · 코더 A 판독과 대조.** 표식은 글자로 찾고 판독은 뜻으로 읽는다.", "",
          "| | 보존 | 부분 | 변형 | 탈락 | 계 |", "|---|---:|---:|---:|---:|---:|"]
    for h in ("有", "無"):
        r = [T[(h, k)] for k in ("보", "부", "변", "-")]
        L.append(f"| 표식 {h} | {r[0]} | {r[1]} | {r[2]} | {r[3]} | {sum(r)} |")
    L += ["",
          f"- **놓침 {miss}/{alive} = {100*miss/alive:.0f}%** — 살아 있는데 표식이 못 잡은 칸",
          f"- **헛짚음 {false}/{have} = {100*false/have:.0f}%** — 표식은 잡혔는데 판독은 탈락",
          f"- 놓친 {miss}칸 가운데 「부분」이 {T[('無','부')]}칸 = **{100*T[('無','부')]/miss:.0f}%** — "
          "글자로 재면 「이름은 남고 근거만 빠진」 자리가 통째로 안 보인다",
          "",
          "헛짚는 일이 거의 없으므로 **표식이 잡힌 칸은 살아 있다고 보아도 된다.** "
          "표식이 없는 칸만 눈으로 읽으면 판독량이 크게 준다."]

    # ── G 주는 방식 (글자 기준)
    snap = json.loads((HERE / "AGG_all11_2026-09-01.json").read_text(encoding="utf-8"))["조건별"]
    def cell(k, lane):
        v = snap[k]["카테고리생존율_②"].get(lane)
        return f"{v[2]:.1f}%" if v else "–"
    L += ["", "## G. 주는 방식 — 올세트와 신념", "",
          "**글자 기준(표식) · 탐색 등급.** 이 판들은 판독을 안 거쳤다. 위 B~F 와 같은 표에 놓지 않는다.",
          "올세트는 gpt 11재료 33판, 신념은 하이쿠 11재료 33+33판이다.", "",
          "| 모델 | 주는 방식 | 판 | 마지막 수첩 표식 (12개 중) | 카테고리 격차 |",
          "|---|---|---:|---:|---|"]
    for k, nm, lane in (("gpt | 가치·C0", "가치 셋 A·B", ("안", "밖")),
                        ("gpt | 올세트·C0", "여섯 다 (올세트)", ("축ㄱ", "축ㄴ")),
                        ("claude-haiku | 가치·C0", "가치 셋 A·B", ("안", "밖")),
                        ("claude-haiku | 신념·C0", "신념 명제 여섯", ("축ㄱ", "축ㄴ")),
                        ("claude-haiku | 신념·압박", "신념 + 반대 압박", ("축ㄱ", "축ㄴ"))):
        v = snap[k]
        a, b = snap[k]["카테고리생존율_②"].get(lane[0]), snap[k]["카테고리생존율_②"].get(lane[1])
        gap = f"{lane[0]} {a[2]:.1f}% 대 {lane[1]} {b[2]:.1f}% = **{a[2]-b[2]:+.1f}%p**" if a and b else "–"
        L.append(f"| {k.split(' | ')[0]} | {nm} | {v['판']} | {v['마지막수첩_표식평균']['②접어서']:.2f} | {gap} |")
    L += ["",
          "- 올세트는 **총량이 A·B 와 거의 같은데 격차만 사라진다.** 같은 모델·같은 11재료다.",
          "- 신념은 **격차가 지목의 절반**이고 **총량이 3분의 1**로 준다. 수첩이 사실 대신 신념으로 찬다",
          "  (신념 어휘 8.6 대 1.0 · 숫자 사실 1.2 대 2.7 · 길이는 400 대 416자 — `READOUT_belief1` §3).",
          "- 신념 판은 하이쿠에만 있어 **주는 방식의 몫과 모델의 몫이 안 갈린다.**"]

    # ── H 모델 (글자 기준)
    cur = {}
    for p in sorted((HERE / "materials").glob("*.json")):
        if p.name == "MATERIALS_TEMPLATE.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            cur[d["issue_id"]] = d
    cov = collections.defaultdict(set)
    pool = []
    for p in (HERE / "runs").rglob("run_*.json"):
        top = p.relative_to(HERE / "runs").parts[0]
        if top.startswith("_") or top == "glm":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if str(d.get("script")) != "C0" or str(d.get("value_set")) not in ("A", "B"):
            continue
        if d.get("issue_id") not in cur:
            continue
        cov[d["issue_id"]].add(top)
        pool.append((top, d))
    common = {i for i, v in cov.items() if len(v) >= 3}
    st = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    npan = collections.Counter()
    for top, d in pool:
        if d["issue_id"] not in common:
            continue
        M = cur[d["issue_id"]]
        notes = d.get("notes") or []
        if not notes:
            continue
        npan[top] += 1
        given = set(d.get("value_categories") or [])
        by = collections.defaultdict(list)
        for f in M["facts"]:
            by[f["category"]].append(f)
        for c, fs in by.items():
            hit = any(0 < A.probe(f["anchor"], notes[-1])[0] <= 2 for f in fs)
            lane = "안" if c in given else "밖"
            st[top][lane][1] += 1
            st[top][lane][0] += hit
    L += ["", "## H. 모델 — 세 모델이 다 돈 재료만", "",
          f"**글자 기준 · 탐색 등급.** 세 모델 공통 재료 **{len(common)}벌**, 압박 없는 판 × 가치 A·B.",
          "읽기 판정이 끝난 것은 gpt 판뿐이라 B~F 와 같은 표에 놓지 않는다.", "",
          "| 모델 | 판 | 가치 안 | 가치 밖 | 안 − 밖 |", "|---|---:|---:|---:|---:|"]
    for m in ("gpt", "gemini-flash", "claude-haiku"):
        a, b = st[m]["안"], st[m]["밖"]
        pa, pb = 100 * a[0] / a[1], 100 * b[0] / b[1]
        L.append(f"| {m} | {npan[m]} | {pa:.1f}% ({a[0]}/{a[1]}) | {pb:.1f}% ({b[0]}/{b[1]}) | **{pa-pb:+.1f}%p** |")
    L.append("")
    L.append("**방향은 세 모델에서 전부 같다.** 크기는 두 배 차이 나고, 생존율 자체도 모델마다 크게 다르다.")

    # ── I 수첩 원문
    L += ["", "## I. 수첩 원문 — 인용할 짝", "",
          "**gpt 1차 판 · 마지막 수첩 그대로.** 요약하지 않았다. 원자료는 "
          "`runs/gpt/<재료>/run_C0_A_rep1.json` · `run_C0_B_rep1.json`.", ""]
    for iid in CASES:
        if iid not in mats:
            L += [f"### {NICE.get(iid, iid)} — *판독이 어긋난 벌이라 뜻 기준 수치에는 안 들어간다*", ""]
            M, get = cur[iid], lambda s: json.loads(
                (HERE / "runs/gpt" / iid / f"run_C0_{s}_rep1.json").read_text(encoding="utf-8"))
            sets = {s: v for s, v in M["value_sets"].items()}
            opts = M["options"]
        else:
            M2 = mats[iid]
            get = lambda s: runs[(iid, s)]
            sets = {s: {"categories": sorted(M2["sets"][s]), "aligned": M2["aligned"][s]} for s in "AB"}
            opts = M2["options"]
            L += [f"### {NICE.get(iid, iid)}", ""]
        L.append(f"선택지 — {opts[0]} · {opts[1]}")
        L.append("")
        for s in "AB":
            r = get(s)
            g = sets[s]
            L += [f"**{s}판** · 준 가치 {' · '.join(sorted(g['categories']))} · "
                  f"정렬 답 {g['aligned']} · 최종 선택 **{r['final_poll']}**", "",
                  "> " + r["notes"][-1].replace("\n", "<br>"), ""]

    # ── J 한계
    L += ["## J. 수치에 붙는 단서", "",
          "1. **주 결과는 모델 하나다** — `gpt-5.4-mini` · 압박 없음 · 온도 0.7 · 수첩 500자 · 보존 명령 없음.",
          "2. **(ii) 층은 천장에 붙어 있다** — 첫 수첩을 통과한 사실의 생존이 안·밖 모두 90% 안팎이라 잴 자리가 10%p 미만이다. 라운드 셋 · 반복 하나의 결과다.",
          "3. **격차는 방향이지 크기가 아니다** — 중앙값을 효과 크기로 인용하지 않는다. 신뢰구간은 안 붙였다.",
          "4. **여덟 벌은 아직 못 읽었다** — 재료 개정 뒤 다시 돈 판의 수첩을 읽으면 30벌 전부로 말할 수 있다.",
          "5. **D 표에는 교락이 있다** — 저자와 재료 계열이 섞여 있다.",
          "6. **G·H 는 글자 기준이다** — 뜻 기준 수치와 나란히 인용하지 않는다.",
          "7. **판독자와 실행자가 같다** — 두 번째 코더가 유일한 독립성이다.", "",
          "---", "",
          "재현: `PYTHONUTF8=1 python experiments/pressure_category/report_stock.py`  ·  "
          "무엇을 인용해도 되는지는 `ALIGNMENT_2026-09-01.md`."]

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"찍었다: {OUT.name}  (A~J · 뜻 기준 {len(mats)}벌 {2*len(mats)}판 · "
          f"모델 표 공통 {len(common)}벌)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
