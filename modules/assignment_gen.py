"""[상류 · 민옥] 배분 생성기 — 팩트를 에이전트에게 나누는 순수 함수 (LLM 호출 0).

계약: 입력 facts 문서(dict) + 파라미터 → 출력 assignment 문서(dict, 스키마 0.2 호환).
파일 입출력은 호출자 몫 — 이 모듈은 dict만 받고 dict만 돌려준다(테스트가 API 없이 돈다).

배경 (7/28 히든 프로필 온전성 검사 §4-4): 관점별 배분 v1은 각 에이전트가 한 요건의
양쪽(두 후보의 사실)을 통째로 쥐어 혼자서 비교가 완결됐다 — 단독 기준선 75%.
"아무도 혼자서는 못 맞힌다"가 깨지면 취합 실험이 성립하지 않으므로, 배분은
편의 파라미터가 아니라 1급 설계 변수다 (EXPERIMENT_SETTINGS_v0 §2-4).

모드 2종:
- split_pairs(히든 프로필): 공유 팩트는 전원에게, 미공유 팩트는 **한 에이전트가
  같은 requirement의 팩트 2개를 쥐지 않도록** 나눈다. 목표: 단독 기준선 ≈ 우연 수준.
- k_overlap(일반): requirement 개념이 없는 이슈(ESA 등)용 라운드로빈 — 팩트마다
  겹침도 k명에게 배정.

결정론: 같은 (facts, 파라미터, seed) → 같은 출력. random.Random(seed)만 사용.
"""
import random


def _agent_ids(n: int) -> list[str]:
    return [f"agent_{i + 1}" for i in range(n)]


def _base_doc(facts_doc: dict, seed: int, mode: str, overlap_k: int) -> dict:
    return {
        "schema_ver": facts_doc.get("schema_ver", "0.2"),
        "created_by": f"assignment_gen v1 ({mode})",
        "issue_id": facts_doc["issue_id"],
        "seed": seed,
        "overlap_k": overlap_k,
        "agents": [],
    }


def generate_split_pairs(facts_doc: dict, *, n_agents: int = 4, seed: int = 42,
                         overlap_k: int = 1, stance: str = "none",
                         perspectives: list[str] | None = None) -> dict:
    """히든 프로필 배분 v2 — 요건 쌍 쪼개기.

    규칙:
      1) share == "shared" 팩트는 전원에게.
      2) share == "unshared" 팩트는 각각 overlap_k 명에게 — 단, 어떤 에이전트도
         같은 requirement의 미공유 팩트를 2개 이상 쥐지 않는다(비교 완결 차단).
      3) 부하 균형: 배정 가능한 에이전트 중 미공유 보유 수가 가장 적은 쪽부터.
    배정 불능(예: overlap_k가 너무 커서 규칙 2를 지킬 수 없음)이면 ValueError —
    조용히 규칙을 깨느니 시끄럽게 죽는다.
    """
    rng = random.Random(seed)
    facts = facts_doc["facts"]
    shared = [f for f in facts if f.get("share") == "shared"]
    unshared = [f for f in facts if f.get("share") == "unshared"]
    if not unshared:
        raise ValueError("split_pairs 모드는 share=unshared 팩트가 필요하다 "
                         "(없으면 k_overlap 모드를 쓸 것)")
    for f in unshared:
        if f.get("requirement") is None:
            raise ValueError(f"미공유 팩트에 requirement 없음: {f['fact_id']}")

    ids = _agent_ids(n_agents)
    holds: dict[str, list[str]] = {a: [] for a in ids}          # 미공유 fact_id
    reqs_of: dict[str, set] = {a: set() for a in ids}           # 보유 requirement

    order = list(unshared)
    rng.shuffle(order)
    for f in order:
        req = f["requirement"]
        for _ in range(overlap_k):
            pool = [a for a in ids
                    if req not in reqs_of[a] and f["fact_id"] not in holds[a]]
            if not pool:
                raise ValueError(
                    f"배정 불능: {f['fact_id']} (requirement {req}) — "
                    f"overlap_k={overlap_k}가 규칙(같은 요건 2개 금지)과 충돌. "
                    f"k를 낮추거나 에이전트 수를 늘릴 것")
            pool.sort(key=lambda a: (len(holds[a]), a))
            best = [a for a in pool if len(holds[a]) == len(holds[pool[0]])]
            pick = rng.choice(best)
            holds[pick].append(f["fact_id"])
            reqs_of[pick].add(req)

    persp = perspectives or [f"참석자{chr(ord('A') + i)}" for i in range(n_agents)]
    doc = _base_doc(facts_doc, seed, "split_pairs", overlap_k)
    shared_ids = [f["fact_id"] for f in shared]
    fact_by_id = {f["fact_id"]: f for f in facts}
    for i, a in enumerate(ids):
        mine = sorted(holds[a])
        doc["agents"].append({
            "agent_id": a,
            "perspective": persp[i],
            "stance": stance,
            "assigned_fact_ids": shared_ids + mine,
        })
    # 사람 검수용 요약 — 배분이 규칙을 지켰는지 눈으로 확인하는 자리.
    doc["_note"] = "; ".join(
        f"{a}: req={sorted(reqs_of[a])} favors=" +
        ",".join(str(fact_by_id[fid].get("favors")) for fid in sorted(holds[a]))
        for a in ids)
    _check_split_pairs(doc, facts_doc, overlap_k)
    return doc


def _check_split_pairs(doc: dict, facts_doc: dict, overlap_k: int) -> None:
    """출력 자기 검증 — 생성기가 자기 규칙을 어겼으면 여기서 죽는다."""
    fact_by_id = {f["fact_id"]: f for f in facts_doc["facts"]}
    counts: dict[str, int] = {}
    for ag in doc["agents"]:
        seen_reqs = []
        for fid in ag["assigned_fact_ids"]:
            f = fact_by_id[fid]
            if f.get("share") == "unshared":
                counts[fid] = counts.get(fid, 0) + 1
                seen_reqs.append(f["requirement"])
        assert len(seen_reqs) == len(set(seen_reqs)), \
            f"{ag['agent_id']}가 같은 requirement 미공유 팩트 2개 보유"
    for f in facts_doc["facts"]:
        if f.get("share") == "unshared":
            assert counts.get(f["fact_id"], 0) == overlap_k, \
                f"{f['fact_id']} 배정 횟수 {counts.get(f['fact_id'], 0)} != k={overlap_k}"


def generate_k_overlap(facts_doc: dict, *, n_agents: int = 8, seed: int = 42,
                       overlap_k: int = 2, stance_cycle: tuple = ("pro", "con"),
                       perspectives: list[str] | None = None) -> dict:
    """일반 배분 — requirement 개념 없는 이슈용. 팩트마다 k명에게, 부하 균형 라운드로빈."""
    rng = random.Random(seed)
    facts = list(facts_doc["facts"])
    rng.shuffle(facts)
    ids = _agent_ids(n_agents)
    holds: dict[str, list[str]] = {a: [] for a in ids}
    for f in facts:
        pool = sorted(ids, key=lambda a: (len(holds[a]), a))
        chosen = pool[:overlap_k]
        for a in chosen:
            holds[a].append(f["fact_id"])
    doc = _base_doc(facts_doc, seed, "k_overlap", overlap_k)
    persp = perspectives or [f"관점{i + 1}" for i in range(n_agents)]
    for i, a in enumerate(ids):
        doc["agents"].append({
            "agent_id": a,
            "perspective": persp[i],
            "stance": stance_cycle[i % len(stance_cycle)],
            "assigned_fact_ids": sorted(holds[a]),
        })
    return doc
