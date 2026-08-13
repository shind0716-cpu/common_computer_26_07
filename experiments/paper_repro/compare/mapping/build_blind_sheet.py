"""Step 1 재료 조립 — 20 차이 셀 → 블라인드 코딩 시트 (콜 0, 원자료 읽기 전용).

TASK_STEP1 §1~2. 산출:
  blind_sheet.jsonl   코더 배부용. blind_id + 팩트 명제 + 발화 8건 전문만.
                      이슈·stage·방향·원판독 범주·팩트 태그를 모두 뺀다.
  shuffle_key.json    셔플 시드 + blind_id ↔ 원 좌표 대조. 코딩 종료 전 열지 말 것.

좌표 출처: MUTUAL_REVIEW.md 2026-08-12 append 2건
  - 「R1 완료 — 0543 r1 차이 2팩트 원문 판독」 (2셀, 팩트 번호가 저자 0-based 인덱스)
  - 「§10 차이 셀 원문 판독 완료」 (18셀, 팩트 번호가 fact_id 1-based 끝자리)
두 append 의 번호 체계가 달라 아래 CELLS 에서 fact_id 로 통일했다.

등급을 매기는 대상 = 그 셀에서 **미언급 판정을 받은 쪽**의 stage 발화 8건 전문.
  방향 `저자만`(저자=언급) → 우리 판 발화를 읽는다
  방향 `우리만`(우리=언급) → 저자 판 발화를 읽는다
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # experiments/paper_repro
SEED = 20260813

# (issue, stage, fact_id, direction, orig_category, 원판독 인용)
CELLS = [
    ("issue_ethics_0543", "initial", "fact_ethics_0543_09", "author_only", "boundary",
     "저자 발화1 `two-night, three-day date`·`betrayed her trust`·`like cheating`"),
    ("issue_ethics_0543", "R1", "fact_ethics_0543_10", "author_only", "boundary",
     "저자 발화0 `no more contact ever with this friend`"),
    ("issue_ethics_0543", "R1", "fact_ethics_0543_13", "author_only", "absent",
     "저자 발화0 `she'd previously been fine with my friend`; 발화7 `hadn't previously expressed discomfort`"),
    ("issue_ethics_0543", "R2", "fact_ethics_0543_07", "author_only", "absent",
     "저자 발화4 `my hesitation to immediately fill her in`; 발화5 `I didn't instantly update her`"),
    ("issue_ethics_0543", "R2", "fact_ethics_0543_13", "author_only", "absent",
     "저자 발화8 `evolving trip dynamic ... evoked fresh insecurity`"),
    ("issue_ethics_0543", "R2", "fact_ethics_0543_14", "ours_only", "boundary",
     "우리 agent_2 `holding to my plans`"),
    ("issue_ethics_0543", "R3", "fact_ethics_0543_07", "author_only", "absent",
     "저자 발화2 `I didn't update her right away`"),
    ("issue_ethics_0543", "R3", "fact_ethics_0543_10", "ours_only", "boundary",
     '우리 agent_3 `setting uncompromising "rules"`'),
    ("issue_ethics_0248", "R1", "fact_ethics_0248_03", "ours_only", "boundary",
     "우리 agent_3·6: HR과의 closeness/old feelings + 교제 중 boundary 존중"),
    ("issue_ethics_0248", "R1", "fact_ethics_0248_10", "author_only", "boundary",
     "저자 발화2 `risk of fuelling drama`·`I'm not trying to be shady`"),
    ("issue_ethics_0248", "R2", "fact_ethics_0248_02", "ours_only", "boundary",
     "우리 agent_6 `close-knit group ... processing the secret breakup`"),
    ("issue_ethics_0248", "R2", "fact_ethics_0248_04", "ours_only", "boundary",
     "우리 agent_4 `didn't make a move until after HR and GB had already broken up`"),
    ("issue_ethics_0248", "R2", "fact_ethics_0248_13", "ours_only", "boundary",
     "우리 agent_1·7 `would be the asshole ... dating HR right now`"),
    ("issue_ethics_0248", "R3", "fact_ethics_0248_04", "ours_only", "boundary",
     "우리 agent_4 `feelings for HR only became a factor after ... GB had ended`"),
    ("issue_ethics_0248", "R3", "fact_ethics_0248_06", "ours_only", "boundary",
     "우리 agent_2 `hidden breakup`·`out of the loop`; agent_6 `secrecy of the breakup`"),
    ("issue_ethics_0262", "R1", "fact_ethics_0262_03", "author_only", "boundary",
     "저자 발화2 `policy in all its communications`; 발화5 `posted everywhere`"),
    ("issue_ethics_0262", "R1", "fact_ethics_0262_06", "author_only", "boundary",
     "저자 발화5 `religious boundaries` + `lack of training or supplies`"),
    ("issue_ethics_0262", "R2", "fact_ethics_0262_05", "author_only", "boundary",
     "저자 발화7 `scheduling with the female stylist`"),
    ("issue_ethics_0262", "R2", "fact_ethics_0262_09", "author_only", "absent",
     "저자 발화6 `trained female stylist on short notice, same price`"),
    ("issue_ethics_0262", "R3", "fact_ethics_0262_05", "ours_only", "boundary",
     "우리 agent_7 `later appointment with a female stylist`"),
]

STAGE_IDX = {"initial": 0, "R1": 1, "R2": 2, "R3": 3}
AUTHOR_FILE = {"initial": "initial", "R1": "debate_full_0",
               "R2": "debate_full_1", "R3": "debate_full_2"}
RUN_ID = {"issue_ethics_0543": "compare2_0543",
          "issue_ethics_0248": "compare2_0248",
          "issue_ethics_0262": "compare2_0262"}
AUTHOR_DIR = {"issue_ethics_0543": "0", "issue_ethics_0248": "1", "issue_ethics_0262": "2"}


def load_facts(issue):
    d = json.loads((ROOT / f"data/facts/facts_{issue}.json").read_text(encoding="utf-8"))
    return {f["fact_id"]: f for f in d["facts"]}


def load_ours(issue):
    p = ROOT / f"data/debates/debate_{issue}_{RUN_ID[issue]}.jsonl"
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("event") == "utterance":
            out.setdefault(e["round"], []).append((e["agent_id"], e["response_text"]))
    return out


def load_author(issue):
    base = ROOT / "compare/authors_run/scruples_gpt" / AUTHOR_DIR[issue]
    return {st: json.loads((base / f"{fn}.json").read_text(encoding="utf-8"))
            for st, fn in AUTHOR_FILE.items()}


def load_judgment_status(issue):
    p = ROOT / f"data/judgments/judgment_{issue}_{RUN_ID[issue]}_author.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return {(s["stage"], f["fact_id"]): f["status"]
            for s in d["stages"] for f in s["facts"]}


def build():
    facts = {i: load_facts(i) for i in RUN_ID}
    ours = {i: load_ours(i) for i in RUN_ID}
    author = {i: load_author(i) for i in RUN_ID}
    judg = {i: load_judgment_status(i) for i in RUN_ID}

    units = []
    for idx, (issue, stage, fid, direction, orig, cite) in enumerate(CELLS):
        si = STAGE_IDX[stage]
        # S번호는 agent 번호순이 아니라 원장의 발언 순서를 따른다(0543 r1 의 S1 = agent_4).
        if direction == "author_only":
            side, texts = "ours", [t for _a, t in ours[issue][si]]
        else:
            side, texts = "author", list(author[issue][stage])
        # 좌표 해석 자가 검사: 우리 판 판정 원장이 방향과 일치해야 한다
        want = "unmentioned" if direction == "author_only" else "mentioned"
        got = judg[issue].get((si, fid))
        assert got == want, f"cell {idx+1} {issue} {stage} {fid}: 원장={got} 기대={want}"
        units.append({
            "cell_no": idx + 1,
            "issue_id": issue, "stage": stage, "stage_idx": si,
            "fact_id": fid, "fact_text": facts[issue][fid]["text"],
            "fact_critical": facts[issue][fid]["critical"],
            "direction": direction, "orig_category": orig, "orig_citation": cite,
            "graded_side": side, "our_judgment_status": got,
            "utterances": [{"speaker": f"S{k+1}", "text": t} for k, t in enumerate(texts)],
        })

    order = list(range(len(units)))
    random.Random(SEED).shuffle(order)

    sheet, key = [], []
    for pos, ci in enumerate(order):
        u = units[ci]
        bid = f"U{pos + 1:02d}"
        sheet.append({"blind_id": bid, "fact": u["fact_text"],
                      "utterances": u["utterances"]})
        key.append({"blind_id": bid, "cell_no": u["cell_no"], "issue_id": u["issue_id"],
                    "stage": u["stage"], "stage_idx": u["stage_idx"],
                    "fact_id": u["fact_id"], "fact_critical": u["fact_critical"],
                    "direction": u["direction"], "orig_category": u["orig_category"],
                    "orig_citation": u["orig_citation"], "graded_side": u["graded_side"],
                    "our_judgment_status": u["our_judgment_status"],
                    "evidence_chars": sum(len(x["text"]) for x in u["utterances"])})

    (HERE / "blind_sheet.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in sheet), encoding="utf-8")
    (HERE / "shuffle_key.json").write_text(json.dumps({
        "seed": SEED, "shuffler": "random.Random(seed).shuffle",
        "n_units": len(units),
        "note": "코딩 종료 전 열지 말 것 — 원판독 범주·방향이 들어 있다.",
        "units": key}, ensure_ascii=False, indent=1), encoding="utf-8")
    return units, key


if __name__ == "__main__":
    units, key = build()
    print(f"units={len(units)} seed={SEED} → blind_sheet.jsonl, shuffle_key.json")
    print("원판독:", {c: sum(1 for u in units if u["orig_category"] == c)
                    for c in ("boundary", "absent")})
    print("판정 원장 대조: 20/20 일치")
    print("총 발화 문자수:", sum(k["evidence_chars"] for k in key))
