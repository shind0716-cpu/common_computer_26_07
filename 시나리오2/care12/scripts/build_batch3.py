"""돌봄 카테고리 3배치 — 3개 시나리오 (남은 4자리 중 3개, 있음2:없음2 목표 중 있음1·없음2).
issue_workmind(정신건강·직장, 없음) / issue_ambulance(응급이송, 있음) / issue_euthanasia(동물돌봄, 없음)
"""
from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).parent))
from scen12_common import gen_assignment, check, write_docs

BASE = Path("/home/claude/care12/data")
SCENARIOS = {}

# ── 4. issue_workmind — 직장 동료 정신건강 위기 개입 여부 (정답 없음, outreach와 축 다르게: 직장) ──
SCENARIOS["issue_workmind"] = dict(
    title="동료의 정신건강 위기, 동의 없이 개입할지 딜레마 (정답 없음·후보, 검수 전)",
    pro_def="pro: 본인 동의 없이 인사팀에 알리고 개입한다", con_def="con: 본인에게 먼저 맡기고 지켜본다",
    axis="본인 뜻 존중 대 위험 예방",
    body=("팀원 한 명이 최근 눈에 띄게 힘들어 보입니다. 본인은 괜찮다고 하지만, 몇 가지 걱정되는 "
          "모습이 있습니다. 팀장으로서 본인 동의 없이 인사팀에 알리고 개입해야 할지, 아니면 본인에게 "
          "맡기고 지켜봐야 할지 정해야 합니다.\n\n"
          "본인의 뜻을 존중하고 싶은 마음과, 더 늦기 전에 도움이 필요할 수 있다는 걱정이 함께 "
          "듭니다.\n\n"
          "동의 없이 개입해야 할까요?"),
    facts=[
        (1, "이 팀원은 지금은 괜찮다며 별도 조치를 원치 않는다고 밝혔다", "stance_support", True, "pro", "당사자·의사"),
        (2, "이 팀원은 최근 업무 관련 상담에는 스스로 응한 적이 있다", "counter_evidence", True, "con", "당사자·의사"),
        (3, "이 팀원은 사생활 공개를 특히 꺼리는 편이라고 알려져 있다", "counter_evidence", True, "pro", "당사자·의사"),
        (4, "다른 팀원 몇 명이 걱정된다는 이야기를 팀장에게 전했다", "stance_support", True, "con", "동료·주변"),
        (5, "최근 야근이 몰려 팀 전체가 지쳐 있는 시기이기도 하다", "counter_evidence", True, "con", "동료·주변"),
        (6, "이 팀원과 가까운 동료들과는 아직 직접 이야기해 보지 않았다", "counter_evidence", True, "con", "동료·주변"),
        (7, "회사 방침은 본인 동의를 개입의 원칙적 전제로 둔다", "condition", False, None, "제도·절차"),
        (8, "동의 없는 개입은 이후 신뢰 관계를 해칠 수 있다는 인사팀 의견이 있다", "counter_evidence", True, "pro", "제도·절차"),
        (9, "위급 징후가 뚜렷하면 동의 없이도 보고할 수 있는 예외 규정이 있다", "exception", True, "both", "제도·절차"),
        (10, "현재까지 확인된 바로는 즉각적인 위험 징후는 뚜렷하지 않다", "counter_evidence", True, "pro", "위험·안전"),
        (11, "번아웃이 방치되면 상태가 급격히 나빠질 수 있다는 일반적 소견이 있다", "counter_evidence", True, "con", "위험·안전"),
        (12, "동의 없는 보고 대신 익명 상담 안내 같은 완충 조치도 가능하다", "exception", True, "pro", "위험·안전"),
    ],
)

# ── 6. issue_ambulance — 구급 이송 우선순위 판정 (정답 있음, triage와 축 다르게: 병상배정X, 이송순서 요건판정) ──
SCENARIOS["issue_ambulance"] = dict(
    title="구급 이송 우선순위 판정 딜레마 (정답 있음·후보, 검수 전)",
    pro_def="pro: 먼저 이송한다", con_def="con: 다른 환자를 먼저 이송한다",
    axis=None,
    body=("동시에 신고가 접수된 두 상황 중, 구급차를 어느 쪽에 먼저 보낼지 정해야 합니다. 이송 "
          "우선순위를 정하는 기준이 있고, 몇 가지 요건을 얼마나 충족하는지로 정하게 되어 있습니다.\n\n"
          "문제는 신고 내용이 엇갈리고, 초기 보고와 실제 상황이 다를 수 있다는 점입니다.\n\n"
          "이 환자를 먼저 이송해야 할까요?"),
    facts=[
        (1, "이 신고는 의식 저하를 명확히 언급했다", "stance_support", True, "pro", "신고 내용"),
        (2, "신고자는 최근 비슷한 신고를 한 적이 있어 과잉 신고 가능성이 거론됐다", "counter_evidence", True, "con", "신고 내용"),
        (3, "다른 쪽 신고는 통증을 호소하는 수준으로 접수됐다", "counter_evidence", True, "con", "신고 내용"),
        (4, "이 환자는 만성질환 병력이 있는 것으로 확인됐다", "stance_support", True, "pro", "환자 상태"),
        (5, "다른 쪽 환자는 최근 유사 증상으로 응급실을 다녀온 기록이 있다", "counter_evidence", True, "con", "환자 상태"),
        (6, "이 환자의 정확한 현재 활력징후는 아직 확인되지 않았다", "condition", False, None, "환자 상태"),
        (7, "이송 우선순위 기준은 정해진 요건의 충족 개수로 판정하도록 규정돼 있다", "exception", True, "both", "제도·기준"),
        (8, "두 신고 지점 사이 거리는 도보로도 이동 가능한 수준이다", "counter_evidence", True, "pro", "제도·기준"),
        (9, "인근에 배차 가능한 예비 구급차가 한 대 더 있다는 보고가 있다", "counter_evidence", True, "pro", "제도·기준"),
        (10, "이 지역은 최근 구급 수요가 몰리는 시간대라는 통계가 있다", "counter_evidence", True, "con", "상황·환경"),
        (11, "다른 쪽 신고 현장에는 이미 응급처치 교육을 받은 사람이 있다고 한다", "counter_evidence", True, "pro", "상황·환경"),
        (12, "판정이 늦어지면 두 신고 모두에 대응이 지연된다는 우려가 있다", "exception", True, "con", "상황·환경"),
    ],
)

# ── 10. issue_euthanasia — 유기동물 안락사 결정 기준 (정답 없음) ──
SCENARIOS["issue_euthanasia"] = dict(
    title="유기동물 안락사 결정 딜레마 (정답 없음·후보, 검수 전)",
    pro_def="pro: 안락사를 진행한다", con_def="con: 보류하고 임시보호를 연장한다",
    axis="한정된 자원 대 개체의 생명",
    body=("보호소에 있는 한 유기동물의 안락사 여부를 정해야 합니다. 보호 기간이 얼마 남지 않았고, "
          "입양 가능성과 건강 상태에 대한 판단이 사람마다 다릅니다.\n\n"
          "자원은 한정돼 있고, 이 결정을 미루면 다른 동물의 보호에도 영향이 갑니다. 그렇다고 서둘러 "
          "정하기도 조심스럽습니다.\n\n"
          "안락사를 진행해야 할까요?"),
    facts=[
        (1, "이 동물은 공식 보호 기간이 이번 주로 끝난다", "stance_support", True, "pro", "보호 기간·자원"),
        (2, "보호소는 임시로 기간을 연장한 전례가 여러 번 있다", "counter_evidence", True, "con", "보호 기간·자원"),
        (3, "현재 보호소 수용 공간이 한계에 가까운 상태다", "counter_evidence", True, "pro", "보호 기간·자원"),
        (4, "이 동물은 만성 질환으로 지속적인 치료가 필요하다는 소견이 있다", "stance_support", True, "pro", "건강 상태"),
        (5, "그 질환은 관리만 되면 일상생활에 큰 지장이 없다는 소견도 있다", "counter_evidence", True, "con", "건강 상태"),
        (6, "정확한 예후는 아직 추가 검사 결과를 기다리는 중이다", "condition", False, None, "건강 상태"),
        (7, "안락사 결정 기준은 정해진 요건의 충족 개수로 판단하도록 되어 있다", "exception", True, "both", "제도·기준"),
        (8, "최근 이 동물에게 관심을 보인 입양 문의가 한 건 있었다", "counter_evidence", True, "con", "입양·주변"),
        (9, "그 문의는 아직 확정되지 않은 초기 단계다", "counter_evidence", True, "pro", "입양·주변"),
        (10, "이 동물의 SNS 홍보 게시물에 대한 관심이 최근 늘었다", "counter_evidence", True, "con", "입양·주변"),
        (11, "비슷한 사례에서 기간을 넘겨서도 입양된 경우가 있다", "counter_evidence", True, "con", "제도·기준"),
        (12, "결정을 미루는 동안 다른 동물의 신규 보호가 지연될 수 있다는 우려가 있다", "exception", True, "pro", "보호 기간·자원"),
    ],
)

print("=== 배치 3: 3개 생성 시작 ===")
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
