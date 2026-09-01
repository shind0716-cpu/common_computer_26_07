"""[공용 코어 · 압박×카테고리] 정렬 대장 — 지금 원자료로 무엇을 말할 수 있나 (콜 0).

## 왜 있나

이 트랙은 재료를 여러 번 고쳤다. 고칠 때마다 그 재료를 가리키던 판·판독·세트가 뒤에
남는데, 문서는 append-only 라 옛 수치가 그대로 서 있다. 그래서 **「이 숫자가 지금
원자료로 재현되나」를 물을 자리가 없었다.** 2026-09-01 에 실제로 걸렸다 — 사전고정
판정을 낸 `analyze_stage1.py` 가 더는 안 돈다. 1차 30벌 중 여덟 벌이 판정 뒤에
개정됐기 때문이다.

이 파일은 그 물음에 기계로 답한다.

## 기준

**지금 `runs/` 에 있는 판**이 기준이다. 재료·판독·세트가 그 판과 맞는지를 본다.
판을 기준에 맞추는 것이 아니라, 기준이 판이다.

## 무엇을 보나

  ① 원자료   판의 `materials_hash` 가 현행 재료 지문과 같은가
  ② 판독     READ60 이 붙은 재료가 현행 재료와 같은 사실을 가리키는가
             (`CONCRETE_LIST` 의 사실 id 와 재료의 사실 id 대조)
  ③ 가치 세트 `values/*.json` 의 카테고리가 현행 재료 카테고리와 같은가
  ④ 주 판정   판독이 맞는 쌍만으로 H0 두 층을 다시 낸다 — 눈금은 `analyze_stage1.py`
             머리말 그대로(살았다 = 보 ∪ 부 ∪ 변, 짝 단위 d = p안 − p밖)

밑줄 폴더(`_dry`·`_scout`·`_stale_hash`)는 ① 에서 뺀다 — 드라이런·정찰·의도적 격리라
어긋나는 것이 정상이다.

## 산출

  ALIGNMENT_2026-09-01.md — 층별 정렬표 + 22쌍 재판정

사용: PYTHONUTF8=1 python experiments/pressure_category/align_audit.py
"""
from __future__ import annotations

import collections
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import analyze_stage1 as S  # noqa: E402
from modules import content_hash  # noqa: E402

OUT = HERE / "ALIGNMENT_2026-09-01.md"
ALIVE = S.ALIVE
SKIP_DIRS = ("_dry", "_scout", "_stale_hash", "_collision")

# ── 보고서를 쓸 때 여는 문서 / 안 여는 문서 ──────────────────────────────────
# 잣대는 하나다: **1차 보고서가 인용할 근거인가.** 「닫음」은 폐기가 아니라
# "이번 보고서를 쓰는 동안 열지 않아도 된다"는 뜻이다. 남의 담당 문서도 그대로 둔다.
# 새 .md 가 생기면 아래 표에 없다고 경고가 뜬다 — 그때 한 줄 적으면 된다.
연다 = {
    "STOCK_2026-09-01.md": "**보고서 재료.** 인용할 수치가 전부 여기 있다 — 여기부터 연다",
    "ALIGNMENT_2026-09-01.md": "입구. 무엇을 쓸 수 있는지가 여기 있다",
    "SELECTION_live30_2026-08-27.md": "§23 주 판정. 156KB 중 이 절만 연다",
    "PREREG_v0.md": "1차 사전고정 — 예측과 판정선",
    "READ60_kappa_all.md": "판독 신뢰도 κ 0.817",
    "PREREG_belief1_2026-08-31.md": "신념 트랙 사전고정",
    "READOUT_belief1_2026-08-31.md": "신념 66판 판독 — 수첩이 신조문이 된다",
    "READOUT_all11_2026-09-01.md": "올세트·전수 741판 집계",
    "AGG_all11_TABLES_2026-09-01.md": "위 보고서의 표 원본",
    "USABLE_MATERIALS_2026-09-01.md": "재료 등급 — 표식 수치를 인용해도 되는 벌",
    "GUIDE_scenario_writing_2026-08-25.md": "§2 표식 한계 — 한계 절의 근거",
    "READPLAN_ab_2026-09-01.md": "A/B 를 belief1 방식으로 물을 문항 초안",
    "PREREG_packW_2026-09-01.md": "팩 가 사전고정 — 판독 전에 걸어 둔 예측과 판정선",
    "PREREG_all34_2026-09-01.md": "3모델 ALL 균형 사전고정 — 왜 34벌인지·세트가 두 벌로 갈린 내력",
    "BELIEF_MODEL_READY_2026-09-01.md": "**신념 다른 모델 사전 점검.** 있는 것·없는 것·실수 날 자리",
    "PROBE_belief_models_2026-09-01.md": "신념 18문장 탐침 — 세 모델이 같은 방향으로 읽나, hapri 첫 탐침",
    "PREREG_belief1_models_2026-09-01.md": "신념 모델 축 사전고정 — M1~M6, 기준선 표(하이쿠 공표값 재현 확인)",
    "ALL34_RESULT_2026-09-01.md": "**3모델 ALL 결과.** P1·P2 적중·P3 빗나감, 판당 총 적재량 표",
}
원장 = {   # 근거로는 살아 있으나 읽을 것은 아니다. 인용할 때만 연다
    "READ60_pack_b1_r0.md": None, "READ60_pack_b1_last.md": None,
    "READ60_pack_b2_r0.md": None, "READ60_pack_b2_last.md": None,
    "READ60_pack_b3_r0.md": None, "READ60_pack_b3_last.md": None,
    "READ60_judgments_b1_r0.md": None, "READ60_judgments_b1_last.md": None,
    "READ60_judgments_b2_r0.md": None, "READ60_judgments_b2_last.md": None,
    "READ60_judgments_b3.md": None, "READ60_adjudication_b1_r0.md": None,
    "READ60_PROMPT_coder.md": None, "READ20_judgments.md": None,
    "READ20_PROTOCOL.md": None, "MATERIALS_REGISTRY_2026-08-27.md": None,
    "REFERENCE_source_values_2026-08-25.md": None, "scan_table.md": None,
    "DIAG_numword_2026-09-01.md": None, "WORKLOG.md": None,
}
닫음 = {   # 이번 보고서와 무관 — 사유를 적는다
    "MATERIALS_JOHAN12_PLAN_2026-08-30.md": "신작 12벌 제작 계획. 1차 30벌과 다른 재료",
    "PLAN_restaurant_side_assignment_2026-08-26.md": "재료 제작 계획",
    "PLAN_value_once_2026-08-27.md": "실행자 미정, 안 돌았다",
    "PROBLEM_care12_2026-08-26.md": "현수 재료 검토 — 판독이 어긋난 여덟 벌 쪽",
    "REVIEW_care12_favors_2026-08-26.md": "같음",
    "GATE_FAIL_DIAGNOSIS_2026-08-27.md": "관문 탈락 진단 — 캣맘은 1차에서 전부 탈락해 보고서에 안 든다",
    "LIMITS_cat_feeding_2026-08-25.md": "같음",
    "HANDOFF_CAT_FEEDING_REVIEW_2026-08-25.md": "같음",
    "READOUT_track2_2026-08-25.md": "제안 — 사전고정 전이고 안 돌았다",
    "기획_신념세트_4안_2026-08-31.md": "기획 단계 문서. 확정본은 PREREG_belief1",
    "READOUT_gpt_haikuset_2026-08-31.md": "다른 배치 집계 — 1차 보고서 범위 밖",
    "RESEARCH_value_vs_belief_lit_2026-08-31.md": "문헌 메모. 인용은 노션 카드로",
    "TRACTION_belief2_2026-09-01.md": "기획 2(합리주의) — 아직 안 돌았다",
    "TRACTION_belief1_2026-08-31.md": "종이 채점 — 판정은 READOUT_belief1 이 한다",
    "TRACTION_rest6_2026-09-01.md": "기획 3(식당 서열) — 아직 안 돌았다",
    "PROBE_belief1_2026-08-31.md": "탐침 — 관문이 아니다",
    "PROBE_belief3_2026-09-01.md": "기획 3 탐침 — 아직 안 돌았다",
    "WORKORDER_신념트랙_템플릿_2026-09-01.md": "작업 지시서",
    "식당_시나리오_12가지.md": "그루 원문 — 기획 3 재료",
    "README_팀원용.md": "트랙 안내",
}


def current_materials() -> dict:
    """issue_id → (파일 이름, 현행 지문). 지문은 러너와 같은 방식(LF 정규화 sha256 앞 12자)."""
    out = {}
    for p in sorted((HERE / "materials").glob("*.json")):
        if p.name == "MATERIALS_TEMPLATE.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") == "pressure_materials_v0":
            out[d["issue_id"]] = (p.stem, content_hash.sha256_file(p)[:12])
    return out


def scan_runs(cur: dict):
    """① 원자료 — 폴더별 일치/어긋남/재료없음, 그리고 어긋난 판 목록."""
    tally = collections.defaultdict(lambda: collections.Counter())
    drift = []
    for p in sorted((HERE / "runs").rglob("run_*.json")):
        top = p.relative_to(HERE / "runs").parts[0]
        d = json.loads(p.read_text(encoding="utf-8"))
        iid, h = d.get("issue_id"), d.get("materials_hash")
        if iid not in cur:
            tally[top]["재료없음"] += 1
            continue
        if h == cur[iid][1]:
            tally[top]["일치"] += 1
        else:
            tally[top]["어긋남"] += 1
            if not top.startswith(SKIP_DIRS):
                drift.append((top, iid, str(d.get("script")), str(d.get("value_set")),
                              h, cur[iid][1], (d.get("meta", {}).get("finished_at") or "?")[:10]))
    return tally, drift


def scan_reading(cur: dict):
    """② 판독 — CONCRETE_LIST 의 사실 id 가 현행 재료의 사실 id 와 같은가."""
    conc = json.loads((HERE / "CONCRETE_LIST_2026-08-27.json").read_text(encoding="utf-8"))["materials"]
    key = json.loads((HERE / "READ60_key.json").read_text(encoding="utf-8"))
    stem = {}
    for p in (HERE / "materials").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("issue_id") and p.stem in conc:
            stem[d["issue_id"]] = p.stem
    aligned, drifted, mats = [], [], {}
    for iid in key:
        d = json.loads((HERE / "materials" / f"{stem[iid]}.json").read_text(encoding="utf-8"))
        order = list(conc[stem[iid]].keys())
        if order == [f["id"] for f in d["facts"]]:
            aligned.append(iid)
            mats[iid] = {"facts": {f["id"]: f for f in d["facts"]}, "order": order,
                         "sets": {s: set(v["categories"]) for s, v in d["value_sets"].items()}}
        else:
            drifted.append(iid)
    return key, mats, aligned, drifted


def scan_valuesets(cur: dict):
    """③ 가치 세트 — 세트의 카테고리가 그 재료의 현행 카테고리와 같은가."""
    catof = {}
    for iid, (st, _) in cur.items():
        catof[iid] = set(json.loads((HERE / "materials" / f"{st}.json").read_text(encoding="utf-8"))["categories"])
    ok, bad = [], []
    for p in sorted((HERE / "values").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        cats = set(d.get("categories") or [])
        if not cats:
            continue          # 신념 세트는 카테고리를 안 지목한다 — 대조 대상이 아니다
        iid = d.get("materials")
        (ok if iid in catof and cats == catof[iid] else bad).append(p.stem)
    return ok, bad


def scan_fingerprints(cur: dict):
    """③-2 지문 — 세트·각본이 적어 둔 `materials_hash` 가 현행 재료 지문과 같은가.

    카테고리 대조(③)는 **재료 카테고리를 지목하는 세트에만** 걸린다. 신념 세트와 서열 세트는
    카드 이름을 `items[].category` 에 두는데 그건 일부러 재료 밖 낱말이라 대조 상대가 아니다.
    그런 세트도 `materials_hash` 는 갖고 있으므로 **지문으로는 잴 수 있다.**
    2026-09-01 피어 감사 지적 — ③ 만으로는 세트 69개와 각본 49개가 통째로 안 보였다.
    """
    out = {}
    for kind, folder in (("가치 세트", "values"), ("압박 각본", "scripts")):
        ok = nohash = drift = 0
        bad = []
        for q in sorted((HERE / folder).glob("*.json")):
            d = json.loads(q.read_text(encoding="utf-8"))
            h, iid = d.get("materials_hash"), d.get("materials")
            if h is None:
                nohash += 1
            elif iid in cur and h == cur[iid][1]:
                ok += 1
            else:
                drift += 1
                bad.append((q.stem, iid, h, cur.get(iid, ("", "없음"))[1]))
        out[kind] = {"일치": ok, "지문 없음": nohash, "어긋남": drift, "목록": bad}
    return out


def locate_old_materials(drifted: list):
    """②-2 §23 을 돌려보려면 재료 판본이 어디 있나 — 지문에서 좌표를 역추적한다.

    §23 재현에는 세 겹이 8/27 판본이어야 한다: 판 · 판독 · **재료**. 앞의 둘은 트리에 있는데
    (판은 `_stale_hash/`, 판독은 `READ60_*`) **재료는 git 이력에만 있다.** 그래서 「유효하다」가
    「돌려볼 수 있다」가 되려면 좌표가 적혀 있어야 한다(2026-09-01 피어 지적).

    좌표를 손으로 적지 않고 **지문에서 찾는다** — `_stale_hash` 판이 적어 둔 `materials_hash`
    와 같은 지문을 내는 판본을 이력에서 고른다. 커밋 하나로 안 묶인다는 것이 실측으로 나왔다:
    `issue_euthanasia` 는 `a17936e` 에서 지워졌다가 `8d8fcaa` 에서 다시 생겨 `8d8fcaa^` 에 없다.
    """
    want = {}
    for q in (HERE / "runs/_stale_hash").rglob("run_*.json"):
        d = json.loads(q.read_text(encoding="utf-8"))
        if d.get("issue_id") in drifted and str(d.get("script")) == "C0"                 and str(d.get("value_set")) in ("A", "B"):
            want.setdefault(d["issue_id"], set()).add(d.get("materials_hash"))
    rows = []
    for iid in drifted:
        hs = sorted(want.get(iid, []))
        h = hs[0] if len(hs) == 1 else None
        rel = f"experiments/pressure_category/materials/{iid}.json"
        found = None
        if h:
            log = subprocess.run(["git", "log", "--format=%h %ad", "--date=short", "--all", "--", rel],
                                 capture_output=True, text=True, encoding="utf-8",
                                 cwd=HERE.parents[1])
            for line in (log.stdout or "").splitlines():
                rev = line.split()[0]
                blob = subprocess.run(["git", "show", f"{rev}:{rel}"], capture_output=True,
                                      cwd=HERE.parents[1]).stdout
                if blob and content_hash.sha256_bytes(blob)[:12] == h:
                    found = (rev, line.split()[1])
                    break
        rows.append((iid, h or "·".join(hs) or "없음", found))
    return rows


def sign_p(pos: int, neg: int) -> float:
    n = pos + neg
    if n == 0:
        return 1.0
    lo = min(pos, neg)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(lo + 1)) / 2 ** n)


def rejudge(key: dict, mats: dict, prefix: str):
    """④ 주 판정 재계산 — 판독이 맞는 쌍만. 눈금은 analyze_stage1 머리말 그대로."""
    cod = S.load_coding(prefix)
    layers = {"r0": [], "sv": []}
    for iid in sorted(mats):
        M = mats[iid]
        slot_of = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
        obs = {"in": {"r0": [], "sv": []}, "out": {"r0": [], "sv": []}}
        for s in ("A", "B"):
            j0, jl = cod[(iid, slot_of[s])]["r0"], cod[(iid, slot_of[s])]["last"]
            for i, fid in enumerate(M["order"]):
                side = "in" if M["facts"][fid]["category"] in M["sets"][s] else "out"
                up = j0[i] in ALIVE
                obs[side]["r0"].append(up)
                if up:
                    obs[side]["sv"].append(jl[i] in ALIVE)
        rate = lambda L: (sum(L) / len(L)) if L else None
        layers["r0"].append(rate(obs["in"]["r0"]) - rate(obs["out"]["r0"]))
        a, b = rate(obs["in"]["sv"]), rate(obs["out"]["sv"])
        layers["sv"].append(None if a is None or b is None else a - b)
    out = {}
    for k, v in layers.items():
        v = [x for x in v if x is not None]
        pos = sum(1 for x in v if x > 0)
        neg = sum(1 for x in v if x < 0)
        out[k] = {"쌍": len(v), "양수": pos, "음수": neg, "동점": len(v) - pos - neg,
                  "중앙": round(statistics.median(v), 3), "p": sign_p(pos, neg)}
    return out


def main() -> int:
    cur = current_materials()
    tally, drift = scan_runs(cur)
    key, mats, aligned, drifted = scan_reading(cur)
    vok, vbad = scan_valuesets(cur)
    fp = scan_fingerprints(cur)
    oldmat = locate_old_materials(sorted(drifted))
    judged = {n: rejudge(key, mats, p) for n, p in
              (("코더 A", "READ60_coderA"), ("헤르메스", "READ60_hermes"))}

    L = ["# 정렬 대장 — 지금 원자료로 무엇을 말할 수 있나 (2026-09-01, 기계 생성물)",
         "",
         "> `align_audit.py` 가 찍는다. **기준은 지금 `runs/` 에 있는 판**이고, 재료·판독·세트가",
         "> 그 판과 맞는지를 본다. 밑줄 폴더(드라이런·정찰·격리)는 원자료 대조에서 뺐다.",
         "", "## ① 원자료 — 판의 재료 지문이 현행 재료와 같은가", "",
         "| 폴더 | 일치 | 어긋남 | 재료 없음 |", "|---|---:|---:|---:|"]
    for k in sorted(tally):
        t = tally[k]
        L.append(f"| `{k}` | {t['일치']} | {t['어긋남']} | {t['재료없음']} |")
    L += ["", f"밑줄 폴더 밖에서 어긋난 판 **{len(drift)}개**:", ""]
    if drift:
        L += ["| 폴더 | 재료 | 조건 | 판의 지문 | 현행 지문 | 실행일 |", "|---|---|---|---|---|---|"]
        for t, iid, sc, vs, h, c, day in drift:
            L.append(f"| `{t}` | {iid.replace('issue_','')} | {sc}/{vs} | `{h}` | `{c}` | {day} |")
    else:
        L.append("없다.")

    L += ["", "## ② 판독 — READ60 이 현행 재료를 가리키는가", "",
          f"판독이 붙은 재료 **{len(key)}벌** 가운데 현행 재료와 정렬 **{len(aligned)}벌** · "
          f"어긋남 **{len(drifted)}벌**.", "",
          "어긋난 벌: " + ", ".join(x.replace("issue_", "") for x in sorted(drifted)), "",
          "이 여덟 벌은 판정 뒤에 재료가 개정되어 새 재료로 다시 돌았다. **원자료는 정렬돼 있고**",
          "판독만 옛 재료 기준이다. 다만 **옛 판이 통째로 남아 있다** — `runs/_stale_hash/` 에",
          "여덟 벌 × A·B = **16판이 전부 8/27 로 온전하다**(재료마다 지문 하나씩, 확인함).", "",
          "**그래서 쓸 수 있는 온전한 기준이 둘이다.**", "",
          "| 기준 | 판을 어디서 | 판독 | 벌 |", "|---|---|---|---:|",
          "| §23 그대로 | 8벌은 `runs/_stale_hash/` · 22벌은 `runs/gpt/` | READ60 그대로 | 30 |",
          "| 이 문서 §④ | 전부 `runs/gpt/` (현행 경로) | READ60 중 정렬분 | 22 |", "",
          "둘 다 **판독과 판이 같은 시점을 가리킨다.** 없는 것은 세 번째 — 「현행 판 + 새 판독」이고,",
          "그건 **여덟 벌을 다시 읽어야 존재한다.** §23 을 인용할 때는 여덟 벌의 판이 지금",
          "`runs/gpt/` 가 아니라 `_stale_hash/` 에 있다는 것만 적으면 된다.",
          "", "### ②-2. §23 을 돌려보려면 — 재료 판본이 어디 있나", "",
          "세 겹이 8/27 판본이어야 하는데 **재료만 트리에 없다.** 지문에서 역추적한 좌표다 —",
          "커밋을 믿지 말고 지문으로 확인하면 된다.", "",
          "| 재료 | `_stale_hash` 판이 적은 지문 | 그 판본이 있는 커밋 |", "|---|---|---|"] + [
          f"| {iid.replace('issue_','')} | `{h}` | " +
          (f"`{rev}` ({day})" if found else "**못 찾음**") + " |"
          for iid, h, found in ((a, b, c) for a, b, c in oldmat)
          for rev, day in [found or ("", "")]] + [
          "",
          "**커밋 하나로 안 묶인다.** `issue_euthanasia` 는 `a17936e` 에서 지워졌다가 `8d8fcaa` 에서",
          "다시 생겨 `8d8fcaa^` 에 없다 — 그 판본은 `abfb629` 에 있다. 나머지 일곱은 `8d8fcaa^` 다.",
          "",
          "판독은 `READ60_*` 그대로, 판은 `runs/_stale_hash/gpt/` 다. 셋을 맞추면 §23 이 돌아간다.",
          "", "## ③ 가치 세트 — 세트의 카테고리가 현행 재료와 같은가", "",
          f"카테고리를 지목하는 세트 **{len(vok)+len(vbad)}개** 중 정렬 **{len(vok)}** · 어긋남 **{len(vbad)}**.",
          "", "어긋남: " + ", ".join(f"`{x}`" for x in sorted(vbad)), "",
          "전부 재료 개정 전에 만든 옛 올세트다. 지우지 않고 두되 **기준선으로 쓰지 않는다** —",
          "지목하는 낱말이 현행 재료의 카테고리와 한 개도 안 겹친다.",
          "", "### ③-2. 지문 — 세트·각본이 적어 둔 재료 지문", "",
          "위 카테고리 대조는 **재료 카테고리를 지목하는 세트에만** 걸린다. 신념 세트와 서열 세트는",
          "카드 이름을 `items[].category` 에 두는데 그건 일부러 재료 밖 낱말이라 대조 상대가 아니다.",
          "그런 세트도 `materials_hash` 는 갖고 있으므로 지문으로 잰다. 각본도 같다.", "",
          "| 무엇 | 지문 일치 | 지문 없음 | 어긋남 |", "|---|---:|---:|---:|"] + [
          f"| {k} | {v['일치']} | {v['지문 없음']} | {v['어긋남']} |" for k, v in fp.items()] + [
          "",
          "지문 없는 것은 지문 칸이 생기기 전에 만든 옛 세트다(카테고리 대조로만 잰다).",
          "", "## ④ 주 판정 재계산 — 현행 경로의 22쌍", "",
          "눈금은 `analyze_stage1.py` 머리말 그대로다. 살았다 = 보 ∪ 부 ∪ 변, 짝 단위 `d = p안 − p밖`.",
          "**이건 §23 을 대체하는 값이 아니라 부분집합 값이다** — §23 의 30쌍도 (②의 표대로) 유효하다.", "",
          "| 코더 | 층 | 쌍 | 양수 | 음수 | 동점 | 중앙 d | 부호검정 p |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for cn, r in judged.items():
        for lk, ln in (("r0", "(i) 첫 수첩 진입"), ("sv", "(ii) 이후 생존")):
            v = r[lk]
            L.append(f"| {cn} | {ln} | {v['쌍']} | **{v['양수']}** | {v['음수']} | {v['동점']} | "
                     f"{v['중앙']:+.3f} | {v['p']:.2g} |")
    L += ["",
          "**§23 의 30쌍과 견주면 방향이 같고 부분집합이 더 선명하다** — 30쌍에서 (i) 25/30 · 중앙 +0.250 이던 것이",
          "22쌍에서 22/22 · 중앙 +0.333 이 된다. 빠진 여덟 벌은 §23-6 이 이미 「격차가 0에 가깝다」고",
          "적어 둔 현수 재료라, 선명해진 것은 새 발견이 아니라 **약한 무대를 뺀 결과**다.",
          "(ii) 는 두 기준 모두 기각이고 동점이 절반이라는 천장도 그대로다.",
          "",
          "⚠ **관문 수도 기준에 따라 다르다** (2026-09-01 피어 감사). 관문은 `run_C0_{A,B}_rep1.json` 의",
          "`final_poll` 둘만 보는데, 개정된 여덟 벌은 8/31 판으로 갈렸다. **8/27 판 기준 21/30 ·",
          "현행 판 기준 23/30** 이다(childcare 가 8/27 에는 같은 답이라 탈락, 8/31 에는 갈려 통과).",
          "판을 바꾼 커밋은 `8d8fcaa`(재료 재업로드) 뿐 아니라 **`6466eb3`**(8/31, 옛 판 18개를",
          "`_stale_hash` 로 옮기고 같은 경로를 새 판으로 채움)이다. §23 의 21/30 은 8/27 기준이고,",
          "위 22쌍 재판정은 **판독과 판이 둘 다 8/27 인 22벌**만 쓰므로 안이 맞는다(확인함).",
          "",
          "## 그래서 무엇을 쓸 수 있나", "",
          "| 산출물 | 근거 | 판정 |", "|---|---|---|",
          "| `SELECTION_live30` §23 (H0·H3′·H6 판정) | 8/27 60판 + 판독 1,424칸 | **유효** — 판독과 판이 같은 시점이다. 인용할 때 여덟 벌의 판이 `_stale_hash/` 에 있다고만 적는다 |",
          "| READ60 판독 원장 (30벌 κ 0.817 · 정렬 22벌 부분집합 κ 0.832) | 같음 | **유효** — 옛 판과 짝지으면 30벌, 현행 경로만 쓰면 22벌 |",
          "| `analyze_stage1.py` | 결과 보기 전 커밋 | **안 돈다** — 여덟 벌에서 사실 id 대조에 걸린다. 고치지 않고 둔다(사전고정 코드) |",
          "| `READOUT_belief1` (신념 66판) | 8/31 하이쿠 | **유효** — 지문 전건 일치 |",
          "| `ALL11_*` receipt·manifest (올세트 33판) | 9/1 gpt | **유효** |",
          "| `AGG_all11_*` · `READOUT_all11` · `USABLE_MATERIALS` | 9/1 전수 741판, 지문 대조 통과 | **유효** — 다만 표식 기준이라 탐색 등급 |",
          "| 옛 올세트 `values/all_*.json` 9개 | 재료 개정 전 | **못 쓴다** (③) |",
          "", "## 보고서를 쓸 때 여는 것 · 안 여는 것", "",
          "잣대는 하나다 — **1차 보고서가 인용할 근거인가.** 「닫음」은 폐기가 아니라",
          "*이번 보고서를 쓰는 동안 열지 않아도 된다*는 뜻이다. 파일은 그대로 둔다.", ""]
    here = {p.name for p in HERE.glob("*.md")}
    L += [f"트랙 문서 **{len(here)}편** — 연다 **{len(연다)}** · 원장이라 안 연다 **{len(원장)}** · "
          f"이번 보고서와 무관 **{len(닫음)}**.", "",
          "### 연다", "", "| 문서 | 왜 |", "|---|---|"]
    for n, why in 연다.items():
        L.append(f"| {'`'+n+'`' if n in here else '~~'+n+'~~ (없음)'} | {why} |")
    L += ["", "### 원장이라 안 연다 — 인용할 때만", "",
          " · ".join(f"`{n}`" for n in 원장), "",
          "### 이번 보고서와 무관", "", "| 문서 | 사유 |", "|---|---|"]
    for n, why in 닫음.items():
        L.append(f"| {'`'+n+'`' if n in here else '~~'+n+'~~ (없음)'} | {why} |")
    unclassified = sorted(here - set(연다) - set(원장) - set(닫음))
    if unclassified:
        L += ["", "> ⚠ **분류 안 된 문서가 있다.** `align_audit.py` 의 표에 한 줄 적어야 한다 — ",
              "> " + ", ".join(f"`{n}`" for n in unclassified)]
    L += ["", "## 다음에 이 사고를 안 내려면", "",
          "재료를 고칠 때 그 재료를 가리키는 것이 셋이다 — **판 · 판독 · 세트**. 지금까지 판은",
          "격리로 챙겼고(`_stale_hash`) 세트는 새로 지었지만 **판독은 챙기는 자리가 없었다.**",
          "재료 개정 절차에 「그 재료의 판독을 무효로 표시한다」를 넣을지가 결정 사항이다.",
          ]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"찍었다: {OUT.name}")
    print(f"원자료 — 밑줄 폴더 밖 어긋남 {len(drift)}판")
    print(f"판독  — 정렬 {len(aligned)} · 어긋남 {len(drifted)}")
    print(f"세트  — 카테고리 정렬 {len(vok)} · 어긋남 {len(vbad)}")
    for k, v in fp.items():
        print(f"지문  — {k}: 일치 {v['일치']} · 지문없음 {v['지문 없음']} · 어긋남 {v['어긋남']}")
    for cn, r in judged.items():
        v = r["r0"]
        print(f"재판정 {cn}: (i) {v['양수']}/{v['쌍']} · 중앙 {v['중앙']:+.3f} · p {v['p']:.2g}")
    here = {p.name for p in HERE.glob("*.md")}
    un = sorted(here - set(연다) - set(원장) - set(닫음))
    print(f"문서 {len(here)}편 — 연다 {len(연다)} · 원장 {len(원장)} · 닫음 {len(닫음)}"
          + (f" · ⚠ 분류 안 됨 {len(un)}: {', '.join(un)}" if un else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
