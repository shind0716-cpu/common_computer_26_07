"""돌봄 카테고리 배치4 — 마지막 1개. issue_caregiverprotect(돌봄노동자보호, 있음)"""
from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).parent))
from scen12_common import gen_assignment, check, write_docs

BASE = Path("/home/claude/care12/data")
IID = "issue_caregiverprotect"

# 관점 4: 요양보호사 / 이용자·가족 / 기관·관리 / 제도·안전 — 각 3
# (번호, 텍스트, 태그, critical, 불리(pro=배치승인/con=거부인정), 관점)
FACTS = [
    (1,  "이 요양보호사는 해당 가정에서 위협적인 언행을 겪은 적이 있다고 보고했다", "stance_support", True, "con", "요양보호사"),
    (2,  "그 보고는 정식 사건 기록으로는 아직 남아 있지 않다", "counter_evidence", True, "pro", "요양보호사"),
    (3,  "이 요양보호사는 해당 가정 방문을 명시적으로 거부 의사를 밝혔다", "counter_evidence", True, "con", "요양보호사"),
    (4,  "이용자 가족은 그런 일이 없었다고 반박하고 있다", "stance_support", True, "pro", "이용자·가족"),
    (5,  "이용자는 이 요양보호사와의 관계가 좋았다는 다른 방문 기록이 있다", "counter_evidence", True, "pro", "이용자·가족"),
    (6,  "이용자 가족과 아직 직접 대면 확인은 이뤄지지 않았다", "condition", False, None, "이용자·가족"),
    (7,  "배치 변경 여부는 정해진 요건의 충족 개수로 판단하도록 규정돼 있다", "exception", True, "both", "기관·관리"),
    (8,  "해당 지역에는 대체 배치할 인력이 마땅치 않은 상황이다", "counter_evidence", True, "pro", "기관·관리"),
    (9,  "기관 지침은 노동자의 위험 상황 배치 거부권을 원칙적으로 인정한다", "counter_evidence", True, "con", "기관·관리"),
    (10, "비슷한 신고가 이 가정에서 이전에도 한 차례 있었다는 기록이 있다", "counter_evidence", True, "con", "제도·안전"),
    (11, "그 이전 신고는 조사 결과 사실무근으로 종결된 바 있다", "counter_evidence", True, "pro", "제도·안전"),
    (12, "위험 상황이 반복되면 관리 책임 문제가 제기될 수 있다는 우려가 있다", "exception", True, "con", "제도·안전"),
]

BODY = (
    "한 요양보호사가 특정 가정으로의 배치를 거부하고 싶다는 뜻을 밝혔습니다. 방문 중 위협적인 "
    "상황을 겪었다는 이유입니다. 기관은 이 배치를 그대로 유지할지, 다른 곳으로 재배치할지 "
    "정해야 합니다.\n\n"
    "기관에는 이런 결정을 내리는 기준이 있고, 몇 가지 요건을 얼마나 충족하는지로 정하게 되어 "
    "있습니다. 문제는 상황에 대해 사람마다 아는 내용이 다르고, 정식 기록과 실제 정황이 어긋난다는 "
    "점입니다.\n\n"
    "이 배치를 그대로 유지해야 할까요?"
)

facts = [{
    "fact_id": f"fact_caregiverprotect_{n:02d}", "text": t, "tags": [tag], "critical": c,
    "prior": {"score": None, "probe_model": None, "probe_prompt_ver": None, "probed_at": None},
    "_unfavorable_to": u, "_perspective": p,
} for (n, t, tag, c, u, p) in FACTS]

issue = {"body": BODY}
agents = gen_assignment(facts, iso_target=2, seed=42)
if agents is None:
    print("배분 탐색 실패"); sys.exit(1)
ok, rpt = check(issue, {"facts": facts}, {"agents": agents})
print("검사:", "통과" if ok else "실패")
for k, v in rpt.items():
    print(f"  {k}: {v}")
if ok:
    note_issue = ("입장 정의 — pro: 배치를 그대로 유지한다 / con: 재배치해 거부를 인정한다. "
                  "정답 있음(기관 요건 충족 개수 판정). 공식 기록은 pro로 기울지만 미공유 팩트를 합치면 뒤집힐 수 있음. "
                  "팩트 12 · 관점 4x3 · 불리 대칭 · 본문 팩트 미포함. 전부 허구.")
    note_facts = "12팩트. 관점 4분할(관점당 3). 불리 pro:con 대칭. _unfavorable_to/_perspective는 스키마 밖 보조 필드."
    paths = write_docs(BASE, IID, "요양보호사 위험 상황 배치 거부권 심사 딜레마 (정답 있음·후보, 검수 전)",
                       BODY, note_issue, note_facts, facts, agents)
    print("생성:", [p.name for p in paths])
