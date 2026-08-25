"""돌봄 카테고리 1배치 — 4개 시나리오 일괄 생성·검사.
issue_childcare(아동, 없음) / issue_eol(임종기, 없음) / issue_elderdrive(노년자립, 없음) / issue_parentalreturn(직장내돌봄, 있음)
"""
from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).parent))
from scen12_common import gen_assignment, check, write_docs

BASE = Path("/home/claude/care12/data")

SCENARIOS = {}

# ── 1. issue_childcare — 어린이집 등원 거부 아동 강제 등원 (정답 없음: 아동 자율 대 보호자 필요) ──
SCENARIOS["issue_childcare"] = dict(
    title="어린이집 등원 거부 아동, 강제로 등원시킬지 딜레마 (정답 없음·후보, 검수 전)",
    pro_def="pro: 아이를 달래서라도 등원시킨다", con_def="con: 등원을 미루고 기다린다",
    axis="아동 정서 존중 대 보호자·기관의 필요",
    body=("다섯 살 아이가 두 달째 어린이집 문 앞에서 울며 안 들어가려 합니다. 억지로 들여보내야 할지, "
          "며칠 더 기다려야 할지 정하지 못하고 있습니다.\n\n"
          "아이는 입구에서만 울고 들어가면 괜찮아진다고도 하고, 어떤 날은 하루 종일 힘들어한다고도 합니다. "
          "보호자의 사정도 있고, 기관의 방침도 있어 어느 쪽으로도 결정이 쉽지 않습니다.\n\n"
          "아이를 달래서라도 등원시켜야 할까요?"),
    facts=[
        (1, "아이는 입구를 지나면 대체로 안정된다는 교사 관찰이 있다", "stance_support", True, "con", "아동"),
        (2, "아이는 최근 낮잠 시간마다 힘들어한다는 기록이 있다", "counter_evidence", True, "con", "아동"),
        (3, "아이는 최근 동생이 태어나며 정서적으로 예민해진 시기다", "counter_evidence", True, "con", "아동"),
        (4, "보호자는 등원 요일이 정해져 있지 않으면 돌봄 공백이 생긴다", "stance_support", True, "pro", "보호자"),
        (5, "보호자는 최근 며칠 등원을 늦추자는 쪽으로 마음이 기울었다", "counter_evidence", True, "con", "보호자"),
        (6, "보호자는 아이의 등원 거부가 반복되면 상담을 받아볼 계획이다", "condition", False, None, "보호자"),
        (7, "기관은 정원 유지를 위해 규칙적인 등원을 권장한다", "counter_evidence", True, "pro", "기관"),
        (8, "기관 교사는 무리한 등원이 아이의 불안을 키울 수 있다고 본다", "counter_evidence", True, "con", "기관"),
        (9, "기관에는 적응 기간을 유연하게 두는 별도 절차가 있다", "exception", True, "pro", "기관"),
        (10, "또래 친구들은 아이가 오는 날을 반긴다는 이야기가 있다", "counter_evidence", True, "pro", "또래·환경"),
        (11, "비슷한 사례에서 며칠 쉬고 나니 저절로 나아졌다는 이야기도 있다", "counter_evidence", True, "both", "또래·환경"),
        (12, "무리한 등원이 이어지면 등원 자체를 더 거부하게 됐다는 사례도 있다", "exception", True, "pro", "또래·환경"),
    ],
)

# ── 2. issue_eol — 임종기 환자 연명치료 중단 결정 (정답 없음) ──
SCENARIOS["issue_eol"] = dict(
    title="임종기 환자 연명치료 중단 결정 딜레마 (정답 없음·후보, 검수 전)",
    pro_def="pro: 연명치료를 중단한다", con_def="con: 연명치료를 유지한다",
    axis="본인 뜻 존중 대 생명 유지",
    body=("말기 상태인 환자의 연명치료를 이어갈지 결정해야 합니다. 환자는 의식이 오락가락하고, 가족들의 "
          "생각도 갈립니다.\n\n"
          "본인이 예전에 남긴 뜻이 있긴 하지만 정식 서류로 남기진 않았고, 지금 상태에서 회복 여지가 "
          "얼마나 있는지도 의견이 갈립니다.\n\n"
          "연명치료를 중단해야 할까요?"),
    facts=[
        (1, "환자는 과거 지인들에게 연명치료를 원치 않는다고 여러 번 말했다", "stance_support", True, "pro", "환자"),
        (2, "환자는 정식 사전연명의료의향서를 작성해 두지는 않았다", "counter_evidence", True, "con", "환자"),
        (3, "환자는 최근 며칠 짧게나마 의식이 돌아오는 순간이 있었다", "counter_evidence", True, "con", "환자"),
        (4, "자녀 중 한 명은 조금이라도 더 시간을 갖길 원한다", "stance_support", True, "con", "가족"),
        (5, "배우자는 본인이 밝힌 뜻대로 해드리고 싶다는 입장이다", "counter_evidence", True, "pro", "가족"),
        (6, "가족들은 최종 결정을 두고 아직 합의에 이르지 못했다", "condition", False, None, "가족"),
        (7, "담당 의료진은 현재 상태에서 회복 가능성이 매우 낮다고 판단한다", "counter_evidence", True, "pro", "의료진"),
        (8, "담당 의료진은 며칠 더 지켜보자는 의견도 함께 냈다", "counter_evidence", True, "con", "의료진"),
        (9, "병원 지침은 본인 의사 확인이 어려우면 가족 합의를 거치도록 한다", "exception", True, "both", "의료진"),
        (10, "종교적 신념상 생명 유지를 중요하게 여기는 가족 구성원이 있다", "counter_evidence", True, "con", "윤리·사회"),
        (11, "비슷한 사례에서 뒤늦게 회복한 경우도 드물게 보고된다", "counter_evidence", True, "pro", "윤리·사회"),
        (12, "본인 뜻을 존중하지 않으면 이후 가족 간 갈등이 깊어질 수 있다는 우려가 있다", "exception", True, "pro", "윤리·사회"),
    ],
)

# ── 3. issue_elderdrive — 고령 부모 운전면허 반납 권고 (정답 없음) ──
SCENARIOS["issue_elderdrive"] = dict(
    title="고령 부모 운전면허 반납 권고 딜레마 (정답 없음·후보, 검수 전)",
    pro_def="pro: 면허 반납을 권한다", con_def="con: 당분간 계속 운전하게 둔다",
    axis="부모의 자율·이동권 대 보행자·본인 안전",
    body=("고령의 부모님께 운전면허를 반납하시라고 말씀드려야 할지 고민하고 있습니다. 최근 몇 가지 "
          "일이 있었지만, 아직은 괜찮으시다는 말씀도 하십니다.\n\n"
          "면허를 놓으시면 이동이 크게 불편해지실 텐데, 그대로 두자니 걱정도 됩니다. 가족들 생각도 "
          "갈립니다.\n\n"
          "면허 반납을 권해야 할까요?"),
    facts=[
        (1, "부모님은 최근 주차 중 가벼운 접촉 사고를 두 차례 냈다", "stance_support", True, "pro", "부모"),
        (2, "부모님은 최근 건강검진에서 시력과 반응속도가 정상 범위로 나왔다", "counter_evidence", True, "con", "부모"),
        (3, "부모님은 운전을 그만두면 활동 반경이 크게 줄 것을 걱정한다", "counter_evidence", True, "con", "부모"),
        (4, "부모님은 병원 통원에 운전이 꼭 필요하다고 말한다", "stance_support", True, "con", "가족"),
        (5, "자녀 중 한 명은 대신 운전해 드릴 여건이 된다", "counter_evidence", True, "pro", "가족"),
        (6, "가족들은 아직 이 문제를 부모님께 직접 여쭤보지 않았다", "condition", False, None, "가족"),
        (7, "거주 지역은 대중교통 접근성이 낮은 편이다", "counter_evidence", True, "con", "지역·안전"),
        (8, "최근 그 지역에서 고령 운전자 관련 사고가 몇 차례 보도됐다", "counter_evidence", True, "pro", "지역·안전"),
        (9, "지자체에는 고령자 이동 지원 서비스가 일부 운영되고 있다", "exception", True, "pro", "지역·안전"),
        (10, "비슷한 연세에도 문제없이 운전하는 이웃 사례가 있다", "counter_evidence", True, "con", "사회·제도"),
        (11, "면허 자진 반납 시 지자체 혜택이 있다는 안내를 받은 적이 있다", "counter_evidence", True, "pro", "사회·제도"),
        (12, "본인 의사에 반해 면허를 반납시키는 강제 절차는 없다", "exception", True, "both", "사회·제도"),
    ],
)

# ── 4. issue_parentalreturn — 육아휴직 복귀자 업무 재배치 (정답 있음) ──
SCENARIOS["issue_parentalreturn"] = dict(
    title="육아휴직 복귀자 업무 재배치 딜레마 (정답 있음·후보, 검수 전)",
    pro_def="pro: 원래 업무로 복귀시킨다", con_def="con: 다른 업무로 재배치한다",
    axis=None,
    body=("육아휴직에서 복귀하는 팀원을 원래 맡던 업무로 되돌릴지, 다른 업무로 재배치할지 정해야 "
          "합니다. 회사에는 복귀 배치를 정하는 기준이 있고, 몇 가지 요건을 얼마나 충족하는지로 "
          "정하게 되어 있습니다.\n\n"
          "문제는 이 팀원에 대해 사람마다 아는 사실이 다르고, 겉으로 드러난 인상과 실제 사정이 "
          "어긋난다는 점입니다.\n\n"
          "이 팀원을 원래 업무로 복귀시켜야 할까요?"),
    facts=[
        (1, "이 팀원은 휴직 전 담당 업무에서 높은 평가를 받았다", "stance_support", True, "pro", "업무·역량"),
        (2, "휴직 기간 중 관련 시스템이 크게 바뀌어 재적응이 필요하다", "counter_evidence", True, "con", "업무·역량"),
        (3, "이 팀원은 휴직 중에도 관련 교육을 일부 이수했다", "counter_evidence", True, "pro", "업무·역량"),
        (4, "원래 업무는 현재 다른 팀원이 임시로 맡아 안정적으로 돌아가고 있다", "counter_evidence", True, "con", "팀 상황"),
        (5, "그 팀원은 계속 그 업무를 맡고 싶다는 뜻을 밝혔다", "counter_evidence", True, "con", "팀 상황"),
        (6, "팀 내 다른 자리는 현재 마땅한 공백이 없다", "condition", False, None, "팀 상황"),
        (7, "회사 복귀 배치 기준은 정해진 요건의 충족 개수로 정하도록 규정돼 있다", "exception", True, "both", "회사·제도"),
        (8, "복귀자를 원래 업무가 아닌 곳에 배치하면 별도 사유 기록이 필요하다", "counter_evidence", True, "pro", "회사·제도"),
        (9, "본인 동의 없는 재배치는 추가 협의 절차를 거치게 되어 있다", "exception", True, "pro", "회사·제도"),
        (10, "이 팀원은 육아 시간 단축 근무를 함께 신청한 상태다", "counter_evidence", True, "pro", "당사자·사정"),
        (11, "이 팀원은 이전에 근무 조정 관련 문의를 여러 차례 남긴 적이 있다", "counter_evidence", True, "con", "당사자·사정"),
        (12, "이 팀원은 원래 업무 복귀가 이번 결정의 전제 조건이라 여기고 있다", "stance_support", True, "con", "당사자·사정"),
    ],
)

print("=== 배치 1: 4개 생성 시작 ===")
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
            note_issue += " 정답 있음(회사 요건 충족 개수 판정)."
        note_issue += " 불리 대칭·교대 배치. 팩트 12 · 관점 4x3 · 본문 팩트 미포함. 전부 허구."
        note_facts = "12팩트. 관점 4분할(관점당 3). 불리 pro:con 대칭. _unfavorable_to/_perspective는 스키마 밖 보조 필드."
        paths = write_docs(BASE, iid, spec["title"], spec["body"], note_issue, note_facts, facts, agents)
        print(f"  생성: {[p.name for p in paths]}")
