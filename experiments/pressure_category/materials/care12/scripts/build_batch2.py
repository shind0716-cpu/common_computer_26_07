"""돌봄 카테고리 2배치 — 4개 시나리오 일괄 생성·검사.
issue_examaccom(장애, 있음) / issue_carebalance(부양분담, 있음) / issue_shelter(노숙인, 없음) / issue_remotewatch(원격돌봄, 있음)
"""
from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).parent))
from scen12_common import gen_assignment, check, write_docs

BASE = Path("/home/claude/care12/data")
SCENARIOS = {}

# ── 5. issue_examaccom — 장애학생 시험시간 연장 심사 (정답 있음) ──
SCENARIOS["issue_examaccom"] = dict(
    title="장애학생 시험시간 연장 심사 딜레마 (정답 있음·후보, 검수 전)",
    pro_def="pro: 시간 연장을 승인한다", con_def="con: 승인하지 않는다",
    axis=None,
    body=("한 학생의 시험시간 연장 신청을 승인할지 정해야 합니다. 학교에는 연장을 승인하는 기준이 "
          "있고, 몇 가지 요건을 얼마나 충족하는지로 정하게 되어 있습니다.\n\n"
          "문제는 이 학생에 대해 위원마다 아는 사실이 다르고, 서류상 인상과 실제 사정이 어긋난다는 "
          "점입니다.\n\n"
          "이 학생의 연장 신청을 승인해야 할까요?"),
    facts=[
        (1, "이 학생은 관련 진단서를 제출 기한 내에 제출했다", "stance_support", True, "pro", "서류·절차"),
        (2, "진단서 발급일이 신청 기준일보다 다소 오래됐다", "counter_evidence", True, "con", "서류·절차"),
        (3, "학교는 갱신 진단서를 요구할 수 있는 별도 절차를 두고 있다", "exception", True, "pro", "서류·절차"),
        (4, "이 학생은 이전 학기 시험에서도 동일한 연장을 받은 적이 있다", "counter_evidence", True, "pro", "학업 기록"),
        (5, "최근 성적 추이는 연장 없이도 큰 변화가 없었다는 기록이 있다", "counter_evidence", True, "con", "학업 기록"),
        (6, "담당 교사는 이번 학기 들어 학생의 어려움이 커졌다고 본다", "condition", False, None, "학업 기록"),
        (7, "심사 기준은 정해진 요건의 충족 개수로 승인 여부를 정하도록 규정돼 있다", "exception", True, "both", "제도·기준"),
        (8, "요건 중 하나인 전문가 소견서가 이번엔 조금 늦게 도착했다", "counter_evidence", True, "con", "제도·기준"),
        (9, "지각 제출에 대한 예외 인정 여부는 위원회 재량으로 되어 있다", "counter_evidence", True, "pro", "제도·기준"),
        (10, "다른 학생들 사이에서 형평성 문제가 제기된 적이 있다", "counter_evidence", True, "con", "형평성·환경"),
        (11, "비슷한 사례에서 서류가 조금 늦어도 승인된 전례가 있다", "counter_evidence", True, "pro", "형평성·환경"),
        (12, "이 학생은 연장이 반려되면 이의 신청을 할 뜻을 밝혔다", "stance_support", True, "con", "형평성·환경"),
    ],
)

# ── 7. issue_carebalance — 부모 부양 의무 형제 분담 심사 (정답 있음) ──
SCENARIOS["issue_carebalance"] = dict(
    title="부모 부양 분담 조정 심사 딜레마 (정답 있음·후보, 검수 전)",
    pro_def="pro: 분담 비율을 재조정한다", con_def="con: 현재 비율을 유지한다",
    axis=None,
    body=("형제자매 사이에서 부모님 부양 분담을 다시 정할지 논의 중입니다. 정해둔 원칙이 있어서, "
          "몇 가지 조건이 얼마나 맞는지로 조정 여부를 가리기로 했습니다.\n\n"
          "문제는 형제마다 아는 사정이 다르고, 겉으로 보이는 것과 실제 형편이 다르다는 점입니다.\n\n"
          "분담 비율을 재조정해야 할까요?"),
    facts=[
        (1, "첫째는 최근 소득이 눈에 띄게 늘었다", "stance_support", True, "pro", "첫째·둘째"),
        (2, "첫째의 소득 증가는 일시적인 상여금 때문이라는 설명이 있다", "counter_evidence", True, "con", "첫째·둘째"),
        (3, "둘째는 최근 육아 부담이 늘어 시간 여력이 줄었다", "counter_evidence", True, "pro", "첫째·둘째"),
        (4, "막내는 부모님과 가장 가까운 곳에 거주하고 있다", "stance_support", True, "con", "막내·거주"),
        (5, "막내는 최근 이직으로 근무 시간이 불규칙해졌다", "counter_evidence", True, "pro", "막내·거주"),
        (6, "가족들은 아직 이 문제로 다 함께 모여 이야기하지 못했다", "condition", False, None, "막내·거주"),
        (7, "부양 분담 원칙은 정해진 조건의 충족 개수로 비율을 정하도록 합의돼 있다", "exception", True, "both", "합의·기준"),
        (8, "합의문에는 소득 변화가 있으면 재논의한다는 조항이 있다", "counter_evidence", True, "pro", "합의·기준"),
        (9, "합의문에는 최소 6개월 유지 후 재논의한다는 조항도 있다", "counter_evidence", True, "con", "합의·기준"),
        (10, "부모님은 지금 분담 방식에 큰 불만이 없다고 말씀하신다", "counter_evidence", True, "con", "부모·환경"),
        (11, "부모님의 최근 통원 빈도가 늘어난 기록이 있다", "counter_evidence", True, "pro", "부모·환경"),
        (12, "재조정 논의 자체가 형제 사이 갈등을 키울 수 있다는 우려가 있다", "exception", True, "con", "부모·환경"),
    ],
)

# ── 9. issue_shelter — 노숙인 쉼터 강제 입소 여부 (정답 없음) ──
SCENARIOS["issue_shelter"] = dict(
    title="노숙인 쉼터 강제 입소 여부 딜레마 (정답 없음·후보, 검수 전)",
    pro_def="pro: 동의 없이 입소를 강행한다", con_def="con: 강행하지 않고 설득을 이어간다",
    axis="자기결정 존중 대 위험 예방",
    body=("한파 기간 동안 거리에서 지내는 한 사람을 두고, 담당자들이 결정을 내려야 합니다. 본인은 "
          "쉼터 입소를 원치 않는다고 밝혔습니다.\n\n"
          "본인의 뜻을 존중해 설득을 이어갈지, 위험을 막기 위해 동의 없이 입소시킬지 의견이 갈립니다. "
          "지침에도 원칙과 예외가 함께 있어 어느 쪽도 자동으로 답이 되지 않습니다.\n\n"
          "동의 없이 입소시켜야 할까요?"),
    facts=[
        (1, "이 사람은 담당자에게 쉼터 입소를 원치 않는다고 직접 밝혔다", "stance_support", True, "pro", "당사자·자기결정"),
        (2, "이 사람은 예전에 짧게 쉼터를 이용한 적이 있다", "counter_evidence", True, "con", "당사자·자기결정"),
        (3, "이 사람은 스스로 판단할 능력에 제한이 없어 보인다", "counter_evidence", True, "pro", "당사자·자기결정"),
        (4, "주변 상인들이 안전을 걱정하는 목소리를 전해 왔다", "stance_support", True, "con", "주변·환경"),
        (5, "인근에서 저체온증 사례가 최근 보고된 적이 있다", "counter_evidence", True, "con", "주변·환경"),
        (6, "이 사람과 담당자의 접촉은 최근 며칠 뜸해진 상태다", "counter_evidence", True, "con", "주변·환경"),
        (7, "지원 지침은 본인 동의를 입소의 원칙적 전제로 둔다", "condition", False, None, "지원·행정"),
        (8, "동의 없는 입소는 이후 신뢰 형성을 어렵게 한다는 현장 의견이 있다", "counter_evidence", True, "pro", "지원·행정"),
        (9, "한파 특보 기간에는 예외적으로 동의 없는 보호가 가능한 조항이 있다", "exception", True, "both", "지원·행정"),
        (10, "현재까지 확인된 정보로는 즉각적인 생명 위험 징후는 없다", "counter_evidence", True, "pro", "위험·안전"),
        (11, "장기간 노숙이 이어지면 건강 위험이 커진다는 일반적 소견이 있다", "counter_evidence", True, "con", "위험·안전"),
        (12, "당장의 입소 대신 방한용품 지원 같은 완충 조치도 가능하다", "exception", True, "pro", "위험·안전"),
    ],
)

# ── 11. issue_remotewatch — 독거노인 원격 모니터링 동의 없는 설치 (정답 있음) ──
SCENARIOS["issue_remotewatch"] = dict(
    title="독거노인 원격 모니터링 설치 심사 딜레마 (정답 있음·후보, 검수 전)",
    pro_def="pro: 설치를 승인한다", con_def="con: 승인하지 않는다",
    axis=None,
    body=("독거노인 가정에 원격 모니터링 기기를 설치할지 심사해야 합니다. 지원 프로그램에는 승인 "
          "기준이 있고, 몇 가지 요건의 충족 개수로 정하게 되어 있습니다.\n\n"
          "문제는 이 어르신에 대해 담당자마다 아는 사정이 다르고, 서류상 정보와 실제 상황이 "
          "어긋난다는 점입니다.\n\n"
          "이 가정에 설치를 승인해야 할까요?"),
    facts=[
        (1, "이 어르신은 최근 낙상으로 병원 진료를 받은 기록이 있다", "stance_support", True, "pro", "건강·상태"),
        (2, "그 낙상은 경미했고 이후 특별한 증상은 없었다는 진료 소견이 있다", "counter_evidence", True, "con", "건강·상태"),
        (3, "이 어르신은 정기적으로 이웃과 왕래하고 있다", "counter_evidence", True, "con", "건강·상태"),
        (4, "동거 가족은 없고 가장 가까운 친척은 차로 한 시간 거리에 산다", "stance_support", True, "pro", "가족·환경"),
        (5, "이웃 중 한 명이 매일 안부를 확인해 주고 있다", "counter_evidence", True, "con", "가족·환경"),
        (6, "이 가정은 아직 신청서를 정식으로 제출하지 않은 상태다", "condition", False, None, "가족·환경"),
        (7, "설치 승인 기준은 정해진 요건의 충족 개수로 정하도록 규정돼 있다", "exception", True, "both", "제도·기준"),
        (8, "본인 동의 없는 설치는 원칙적으로 금지되어 있다", "counter_evidence", True, "con", "제도·기준"),
        (9, "이 어르신은 설치에 대한 의사를 아직 명확히 밝히지 않았다", "counter_evidence", True, "pro", "제도·기준"),
        (10, "비슷한 사례에서 설치 후 만족도가 높았다는 조사 결과가 있다", "counter_evidence", True, "pro", "사례·프라이버시"),
        (11, "일부 이용자는 감시받는 느낌 때문에 불편을 호소한 적이 있다", "counter_evidence", True, "con", "사례·프라이버시"),
        (12, "동의 확인 전이라도 임시로 시범 운영할 수 있는 예외 규정이 있다", "exception", True, "pro", "사례·프라이버시"),
    ],
)

print("=== 배치 2: 4개 생성 시작 ===")
for iid, spec in SCENARIOS.items():
    facts = [{
        "fact_id": f"fact_{iid.replace('issue_','')}_{n:02d}", "text": t, "tags": [tag], "critical": c,
        "prior": {"score": None, "probe_model": None, "probe_prompt_ver": None, "probed_at": None},
        "_unfavorable_to": u, "_perspective": p,
    } for (n, t, tag, c, u, p) in spec["facts"]]

    issue = {"body": spec["body"]}
    agents = gen_assignment(facts, iso_target=2, seed=42)
    if agents is None:
        print(f"{iid}: 배분 탐색 실패"); continue
    ok, rpt = check(issue, {"facts": facts}, {"agents": agents})
    print(f"\n{iid}: {'통과' if ok else '실패'}")
    for k, v in rpt.items():
        print(f"  {k}: {v}")
    if ok:
        note_issue = f"입장 정의 — {spec['pro_def']} / {spec['con_def']}."
        if spec["axis"]:
            note_issue += f" 정답 없음({spec['axis']}). 입장 변수 — 프롬프트 한 줄만 바꿔 두 번 실행."
        else:
            note_issue += " 정답 있음(요건 충족 개수 판정)."
        note_issue += " 불리 대칭·교대 배치. 팩트 12 · 관점 4x3 · 본문 팩트 미포함. 전부 허구."
        note_facts = "12팩트. 관점 4분할(관점당 3). 불리 pro:con 대칭. _unfavorable_to/_perspective는 스키마 밖 보조 필드."
        paths = write_docs(BASE, iid, spec["title"], spec["body"], note_issue, note_facts, facts, agents)
        print(f"  생성: {[p.name for p in paths]}")
