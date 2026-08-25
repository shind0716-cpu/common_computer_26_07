"""12팩트 재조정용 공용 — 배분 자동 생성 + 골격 자체 검사.

골격 규격(v5-12, 기존 12팩트 눈금에 맞춤):
  팩트 12 · 8에이전트(관점4 x 입장2) · 에이전트당 3팩트 · 밀도 2.0
  관점 4분할(관점당 3팩트) · 자기 관점 2 + 타 관점 1 · 각 에이전트 자기입장 불리 1+ 보유
  고립(1인 보유) 목표 2 · 미배분 0 · 최대 보유 3 · 불리 pro:con 대칭 · 본문 팩트 노출 0
  태그: condition1 / counter_evidence7 / stance_support2 / exception2 (ESA 눈금 참고, 유연)
"""
import json, random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CREATED_BY = "manual(session-claude-draft, 팀 검수 전 후보 지위)"


def gen_assignment(facts, iso_target=2, seed=42, tries=800000):
    by_persp = {}
    for f in facts:
        by_persp.setdefault(f['_perspective'], []).append(f['fact_id'])
    fu = {f['fact_id']: f['_unfavorable_to'] for f in facts}
    persps = list(by_persp.keys())
    agents = [(p, st) for p in persps for st in ('pro', 'con')]
    allf = [f['fact_id'] for f in facts]
    rng = random.Random(seed)
    for _ in range(tries):
        holders = Counter(); assign = {}; ok = True
        for i, (p, st) in enumerate(agents):
            if len(by_persp[p]) < 2:
                ok = False; break
            self2 = rng.sample(by_persp[p], 2)
            others = [fid for q in persps if q != p for fid in by_persp[q]]
            other1 = rng.sample(others, 1)
            picks = self2 + other1
            if st not in [fu[x] for x in picks]:
                ok = False; break
            assign[f"agent_{i+1}"] = (p, st, picks)
            for x in picks:
                holders[x] += 1
        if not ok:
            continue
        if any(holders.get(x, 0) == 0 for x in allf):
            continue
        if sum(1 for x in allf if holders[x] == 1) != iso_target:
            continue
        if max(holders.values()) > 3:
            continue
        return [{"agent_id": aid, "perspective": p, "stance": st, "assigned_fact_ids": picks}
                for aid, (p, st, picks) in assign.items()]
    return None


def check(issue, facts, assign, expect_self=2, expect_other=1, iso_target=2):
    F = facts['facts']
    fmap = {f['fact_id']: f['_perspective'] for f in F}
    fu = {f['fact_id']: f['_unfavorable_to'] for f in F}
    tags = Counter(f['tags'][0] for f in F)
    unfav = Counter(f['_unfavorable_to'] for f in F)
    holders = Counter(); viol = []; noself = []
    for a in assign['agents']:
        op = [fmap[x] for x in a['assigned_fact_ids']]
        s = sum(1 for p in op if p == a['perspective'])
        if not (s == expect_self and len(op) - s == expect_other):
            viol.append(f"{a['agent_id']}({s}/{len(op)-s})")
        if a['stance'] not in [fu[x] for x in a['assigned_fact_ids']]:
            noself.append(a['agent_id'])
        for x in a['assigned_fact_ids']:
            holders[x] += 1
    allf = [f['fact_id'] for f in F]
    iso = [x for x in allf if holders[x] == 1]
    un = [x for x in allf if holders.get(x, 0) == 0]
    slots = sum(len(a['assigned_fact_ids']) for a in assign['agents'])
    id_dup = len(allf) != len(set(allf))
    bad_ref = [x for a in assign['agents'] for x in a['assigned_fact_ids'] if x not in set(allf)]
    expose = sum(1 for f in F if f['text'][:8] in issue['body'])
    rpt = {
        "n_facts": len(F), "tags": dict(tags), "unfav": dict(unfav),
        "unfav_sym": unfav.get('pro') == unfav.get('con'),
        "critical": sum(f['critical'] for f in F),
        "density": round(slots/len(F), 2), "holder_dist": dict(sorted(Counter(holders.values()).items())),
        "isolated": len(iso), "unassigned": len(un), "rule_viol": viol, "no_self_unfav": noself,
        "id_dup": id_dup, "bad_ref": bad_ref, "body_expose": expose,
    }
    ok = (not viol and not noself and len(iso) == iso_target and not un
          and rpt["unfav_sym"] and not id_dup and not bad_ref and expose == 0
          and set(tags) == {"condition", "counter_evidence", "stance_support", "exception"})
    return ok, rpt


def write_docs(base, iid, title, body, note_issue, note_facts, facts, agents, prompt_ver="scenario-cand-v5-12"):
    base = Path(base)
    created_at = datetime.now(timezone.utc).astimezone().isoformat()
    common = {"schema_ver": "0.2", "created_by": CREATED_BY, "created_at": created_at, "issue_id": iid}
    docs = {
        base/"issues"/f"{iid}.json": {**common, "source": "synthetic",
            "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
            "title": title, "body": body, "_note": note_issue},
        base/"facts"/f"facts_{iid}.json": {**common, "_note": note_facts,
            "extractor": {"model": "manual", "temperature": 0, "prompt_ver": prompt_ver},
            "facts": facts},
        base/"assignments"/f"assignment_{iid}.json": {**common,
            "_note": "8에이전트(관점 4 x 입장 2), 에이전트당 3팩트, 밀도 2.0, 자기2/타1, 각 자기입장 불리 1+.",
            "seed": 42, "agents": agents},
    }
    for path, doc in docs.items():
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return list(docs.keys())
