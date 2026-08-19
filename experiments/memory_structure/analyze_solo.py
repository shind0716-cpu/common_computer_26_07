"""[민옥 트랙 · 기억 구조 1단] 분석 — PREREG_v1 §6~§8 지표 산출 (LLM 0콜).

입력: runs/<model>/run_*.json + judgments/<model>/judge_*.json
출력: analysis/analysis_solo.json + analysis/analysis_solo.md (사람용 표)

산출 지표 (전부 PREREG §6 사전 지정 — 순서·정의 변경 금지):
  주 지표   ② 조건부 사망률 = r0 발화 진입(judge mentioned) 팩트 중 최종 캐리어 부재 비율
  분리      부호화 실패 = r0 발화 미진입 팩트 수
  보조      라운드별 발화 생존(judge) · 생존 AUC · r1 신규 소실률(③ 바닥 대비)
  조작 점검 전진 점수 = 1 − 문자 2그램 자카드(직전 라운드 대비) · A′>A 확인
  관계식    조건 내 전진 점수 × 신규 소실 스피어만 ρ
  회상      앵커 일치 정답 수 + 캐리어 밖 초과 항목 수(작화 후보 — 3요건 LLM 판정은 별도)
  공변량    favors 태그별 생존 분해
  측정 방어 판정기 vs 앵커 스캔 불일치율 · votes 불일치율(3표 만장일치 아님 비율)

실행: PYTHONUTF8=1 python experiments/memory_structure/analyze_solo.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules.judge import SURVIVING  # noqa: E402

ISSUE_ID = "issue_camp"
HERE = Path(__file__).resolve().parent
# ── 앵커 사전 (2026-08-19 이슈별 분리) ──────────────────────────────────────
# camp 문면은 정본이라 한 글자도 바꾸지 않았다 — 아래 issue_camp 항목은 종전 ANCHORS 를
# 그대로 옮긴 것이고, 모듈 끝의 `ANCHORS` 별칭이 종전 참조를 계속 가리킨다.
#
# camp 밖의 앵커는 **요한 측이 만든 정의를 그대로 가져온 것**이다. 임의로 새로 만들지 않는다.
#   출처: experiments/scenario_generalization/build_issue_throne.py 의 ANCHORS
#         experiments/scenario_generalization/build_issue_polar.py  의 ANCHORS
#         experiments/scenario_generalization/build_issue_exile.py  의 ANCHORS
#   (그 파일들이 정본 — 앵커를 고치려면 거기부터 고치고 자체 검사를 다시 돌린다)
ANCHORS_BY_ISSUE = {
    "issue_camp": {  # 드라이런 정본 계승 (dryrun_all_arms_seed1.json anchors)
        "fact_camp_01": r"38[,.]?000", "fact_camp_02": r"60\s*명|60명",
        "fact_camp_03": r"사흘|회신에.*걸", "fact_camp_04": r"10월\s*2일|마감일.*견적",
        "fact_camp_05": r"51[,.]?000", "fact_camp_06": r"39[,.]?500",
        "fact_camp_07": r"배관", "fact_camp_08": r"40\s*인|40인", "fact_camp_09": r"확인서",
        "fact_camp_10": r"24\s*[~\-]\s*25|24~25", "fact_camp_11": r"명단에\s*없|미가입",
        "fact_camp_12": r"증서",
    },
    "issue_throne": {
        "fact_throne_01": r"친딸", "fact_throne_02": r"열여섯", "fact_throne_03": r"회신",
        "fact_throne_04": r"거부를\s*통보", "fact_throne_05": r"서약서",
        "fact_throne_06": r"적자", "fact_throne_07": r"스물하나", "fact_throne_08": r"파종제",
        "fact_throne_09": r"봉인", "fact_throne_10": r"넷뿐", "fact_throne_11": r"이단",
        "fact_throne_12": r"파문\s*명부",
    },
    "issue_polar": {
        "fact_polar_01": r"영하\s*52", "fact_polar_02": r"혈색소",
        "fact_polar_03": r"여섯\s*시간", "fact_polar_04": r"두\s*팩",
        "fact_polar_05": r"이륙\s*직후", "fact_polar_06": r"백열흘",
        "fact_polar_07": r"흔들림", "fact_polar_08": r"수련", "fact_polar_09": r"열넷",
        "fact_polar_10": r"세\s*번째", "fact_polar_11": r"설상차", "fact_polar_12": r"일임",
    },
    "issue_exile": {
        "fact_exile_01": r"서른한", "fact_exile_02": r"아홉\s*배", "fact_exile_03": r"우두머리",
        "fact_exile_04": r"삼분의\s*일", "fact_exile_05": r"통행이\s*막",
        "fact_exile_06": r"진입을\s*거부", "fact_exile_07": r"구호\s*조약",
        "fact_exile_08": r"예순둘", "fact_exile_09": r"세\s*해\s*전",
        "fact_exile_10": r"열한\s*자리", "fact_exile_11": r"넉\s*달",
        "fact_exile_12": r"따로\s*송환",
    },
}

# 하위 호환 — 종전 `from analyze_solo import ANCHORS` 는 camp 사전을 계속 가리킨다.
ANCHORS = ANCHORS_BY_ISSUE["issue_camp"]


def anchors_for(issue_id: str) -> dict[str, str]:
    """이슈의 앵커 사전. 없는 이슈면 즉사한다 — 빈 사전으로 조용히 0점을 주지 않는다."""
    if issue_id not in ANCHORS_BY_ISSUE:
        raise SystemExit(f"[analyze_solo] 앵커 사전이 없는 이슈: {issue_id} — "
                         f"등록된 것: {', '.join(ANCHORS_BY_ISSUE)}")
    return ANCHORS_BY_ISSUE[issue_id]


def bigrams(s: str) -> set[str]:
    s = re.sub(r"\s+", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def spearman(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = (sum((x - mx) ** 2 for x in rx) * sum((y - my) ** 2 for y in ry)) ** 0.5
    return num / den if den else None


def main() -> None:
    facts = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))["facts"]
    favors = {f["fact_id"]: (f.get("favors") or "중립") for f in facts}
    out_rows = []
    for md in sorted((HERE / "runs").iterdir()):
        if not md.is_dir() or md.name.startswith("_"):
            continue
        for rp in sorted(md.glob("run_*.json")):
            run = json.loads(rp.read_text(encoding="utf-8"))
            jp = HERE / "judgments" / md.name / f"judge_{run['run_id']}.json"  # 실판정만 (_offline 제외)
            if not jp.exists():
                print(f"[warn] 판정 없음 — {md.name}/{run['run_id']} 건너뜀")
                continue
            jd = json.loads(jp.read_text(encoding="utf-8"))
            rec = jd["records"]
            surv = {}   # tag -> set(fact_id 생존)
            votes_total = votes_split = 0
            for tag, rows in rec.items():
                s = set()
                for r in rows:
                    votes_total += 1
                    sts = [v["status"] for v in r["votes"]]
                    if len(set(sts)) > 1:
                        votes_split += 1
                    if r["status"] in SURVIVING:
                        s.add(r["fact_id"])
                surv[tag] = s
            r0 = surv["essay_r0"]
            rounds = [surv[f"essay_r{i}"] for i in range(4)]
            # 캐리어 생존: ①은 설계상 전 팩트 보존
            carrier = set(f["fact_id"] for f in facts) if run["memory"] == "full" else surv.get("carrier", set())
            cond_death = (len(r0 - carrier) / len(r0)) if r0 else None   # 주 지표(②에서 주, 전 조건 산출)
            encode_fail = 12 - len(r0)
            auc = sum(len(s) for s in rounds) / 4
            new_loss_r1 = len(rounds[0] - rounds[1])
            # 전진 점수
            prog = [1 - jaccard(bigrams(run["essays"][i]), bigrams(run["essays"][i - 1]))
                    for i in range(1, 4)]
            new_loss = [len(rounds[i - 1] - rounds[i]) for i in range(1, 4)]
            # 회상 (앵커 일치 필수)
            recall_hits = {fid for fid, pat in ANCHORS.items() if re.search(pat, run["recall"])}
            recall_correct = len(recall_hits & carrier) if run["memory"] != "full" else len(recall_hits)
            recall_excess = len(recall_hits - carrier) if run["memory"] != "full" else 0
            # 앵커 스캔 vs 판정 불일치 (발화 4편 × 12팩트)
            mismatch = 0
            for i in range(4):
                for fid, pat in ANCHORS.items():
                    a = bool(re.search(pat, run["essays"][i]))
                    j = fid in rounds[i]
                    if a != j:
                        mismatch += 1
            # favors 분해 (최종 캐리어 기준 생존)
            fav = {}
            for side in ("무레온", "다림재", "중립"):
                ids = {fid for fid, s in favors.items() if s == side}
                fav[side] = {"n": len(ids), "carrier_surv": len(ids & carrier)}
            out_rows.append({
                "model": md.name, "run_id": run["run_id"], "arm": run["arm"],
                "memory": run["memory"], "rep": run["rep"],
                "r0_entered": len(r0), "encode_fail": encode_fail,
                "round_surv": [len(s) for s in rounds], "auc": auc,
                "carrier_surv": len(carrier & set(f["fact_id"] for f in facts)),
                "cond_death_rate": cond_death, "new_loss_r1": new_loss_r1,
                "progress_scores": prog, "new_loss": new_loss,
                "spearman_prog_loss": spearman(prog, [float(x) for x in new_loss]),
                "recall_correct": recall_correct, "recall_excess_anchor": recall_excess,
                "judge_anchor_mismatch": mismatch, "votes_split_rate": votes_split / votes_total,
                "favors": fav,
            })
    dst_dir = HERE / "analysis"
    dst_dir.mkdir(exist_ok=True)
    (dst_dir / "analysis_solo.json").write_text(
        json.dumps(out_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 사람용 표 (조건 평균) ──
    from collections import defaultdict
    agg = defaultdict(list)
    for r in out_rows:
        agg[(r["model"], r["arm"], r["memory"])].append(r)
    lines = ["# 분석 결과 (조건 평균, 반복 3) — PREREG_v1 지표", ""]
    arm_ko = {"A": "A반복", "P": "A′전진", "B": "B숙의"}
    mem_ko = {"full": "①전체", "note": "②수첩", "prev": "③직전"}
    for model in sorted({r["model"] for r in out_rows}):
        lines += [f"## {model}", "",
                  "| 조건 | r0진입 | 발화생존 r0→r3 | AUC | 캐리어 | 조건부사망률 | 전진(평균) | ρ(전진,소실) |",
                  "|---|---|---|---|---|---|---|---|"]
        for arm in ("A", "P", "B"):
            for mem in ("full", "note", "prev"):
                rows = agg.get((model, arm, mem), [])
                if not rows:
                    continue
                def m(f):
                    vals = [f(r) for r in rows if f(r) is not None]
                    return sum(vals) / len(vals) if vals else None
                rs = [m(lambda r, i=i: r["round_surv"][i]) for i in range(4)]
                cd = m(lambda r: r["cond_death_rate"])
                pg = m(lambda r: sum(r["progress_scores"]) / 3)
                sp = m(lambda r: r["spearman_prog_loss"])
                lines.append(
                    f"| {arm_ko[arm]}×{mem_ko[mem]} | {m(lambda r: r['r0_entered']):.1f} "
                    f"| {rs[0]:.1f}→{rs[1]:.1f}→{rs[2]:.1f}→{rs[3]:.1f} | {m(lambda r: r['auc']):.1f} "
                    f"| {m(lambda r: r['carrier_surv']):.1f} | {('%.2f' % cd) if cd is not None else '—'} "
                    f"| {pg:.2f} | {('%.2f' % sp) if sp is not None else '—'} |")
        lines.append("")
    (dst_dir / "analysis_solo.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[analyze] {len(out_rows)}런 → analysis/analysis_solo.json · analysis_solo.md")


if __name__ == "__main__":
    main()
