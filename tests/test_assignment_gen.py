"""배분 생성기 테스트 — API 불필요, 순수 함수만 검사."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.assignment_gen import generate_split_pairs, generate_k_overlap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HIRE = ROOT / "experiments" / "hidden_profile" / "data" / "facts_issue_hire_v1.json"


def _hire_doc():
    return json.loads(HIRE.read_text(encoding="utf-8"))


def test_split_pairs_no_agent_completes_a_requirement():
    doc = generate_split_pairs(_hire_doc(), n_agents=4, seed=42)
    facts = {f["fact_id"]: f for f in _hire_doc()["facts"]}
    for ag in doc["agents"]:
        reqs = [facts[fid]["requirement"] for fid in ag["assigned_fact_ids"]
                if facts[fid].get("share") == "unshared"]
        assert len(reqs) == len(set(reqs)), f"{ag['agent_id']} 요건 중복: {reqs}"


def test_split_pairs_shared_to_everyone_unshared_exactly_k():
    doc = generate_split_pairs(_hire_doc(), n_agents=4, seed=42, overlap_k=1)
    facts = _hire_doc()["facts"]
    shared = {f["fact_id"] for f in facts if f.get("share") == "shared"}
    unshared = {f["fact_id"] for f in facts if f.get("share") == "unshared"}
    count = {}
    for ag in doc["agents"]:
        got = set(ag["assigned_fact_ids"])
        assert shared <= got, f"{ag['agent_id']}에 공유 팩트 누락"
        for fid in got & unshared:
            count[fid] = count.get(fid, 0) + 1
    assert all(count[fid] == 1 for fid in unshared), count


def test_split_pairs_balanced_load():
    doc = generate_split_pairs(_hire_doc(), n_agents=4, seed=42)
    facts = {f["fact_id"]: f for f in _hire_doc()["facts"]}
    sizes = [sum(1 for fid in ag["assigned_fact_ids"]
                 if facts[fid].get("share") == "unshared") for ag in doc["agents"]]
    assert max(sizes) - min(sizes) <= 1, sizes  # 8팩트/4명 → 전원 2개


def test_split_pairs_deterministic_and_seed_sensitive():
    a = generate_split_pairs(_hire_doc(), seed=42)
    b = generate_split_pairs(_hire_doc(), seed=42)
    assert a == b, "같은 seed인데 출력이 다름"
    diffs = [s for s in range(1, 30)
             if generate_split_pairs(_hire_doc(), seed=s) != a]
    assert diffs, "seed를 바꿔도 출력이 전혀 안 변함 — shuffle 미작동 의심"


def test_split_pairs_infeasible_k_raises():
    try:
        generate_split_pairs(_hire_doc(), n_agents=4, overlap_k=4)
    except ValueError:
        return
    raise AssertionError("k=4는 4에이전트에서 규칙과 충돌해야 함(요건당 팩트 2개)")


def test_split_pairs_stance_default_none():
    doc = generate_split_pairs(_hire_doc(), seed=42)
    assert all(ag["stance"] == "none" for ag in doc["agents"])


def test_k_overlap_counts():
    doc = generate_k_overlap(_hire_doc(), n_agents=8, seed=42, overlap_k=2)
    count = {}
    for ag in doc["agents"]:
        for fid in ag["assigned_fact_ids"]:
            count[fid] = count.get(fid, 0) + 1
    assert all(c == 2 for c in count.values()), count


def test_k_overlap_deterministic():
    assert generate_k_overlap(_hire_doc(), seed=7) == generate_k_overlap(_hire_doc(), seed=7)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)}종 전부 통과")
