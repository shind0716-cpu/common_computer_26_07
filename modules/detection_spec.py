"""[측정 계약] 시나리오별 의미 판독 명세 — 로더·검증기 (LLM 0콜).

## 왜 있는가

2026-08-20 Hermes 독립 감사가 throne 파일럿에서 이것을 실측했다: 앵커 미적중 68건 중
36건만 실제 미발화였고 **28건은 앵커가 놓친 것**이었다. 반대로 적중 40건 중 온전한 보존은
24건뿐이다. 「대표 문자열 하나가 있으면 팩트가 살아 있다」는 camp 계약이 throne 의 의미
골격과 안 맞는다.

그래서 판독 규칙의 소유권을 **시나리오로 옮긴다.** 공통 층(이 모듈)은 로딩·검증·기록만
맡고, 무엇이 팩트 보존인지는 각 시나리오의 명세가 정한다.

## 이 모듈이 하지 않는 것

**자동 의미 판정을 하지 않는다.** 정규식을 늘려서 semantic detector 라고 부르지 않는다
(브리프 §4.4). 여기 있는 것은 명세 로딩, 어휘 검증, 판정 레코드 검증, 교정셋 검증뿐이다.
자동 판정기는 독립 교정셋에서 입증된 뒤에 별도로 붙인다.

## fail-closed

모르는 것을 0점이나 `absent` 로 조용히 바꾸지 않는다. 아래 중 하나면 `SpecError` 로 죽는다.

- 등록되지 않은 issue / spec_version / fact_id
- 재료 해시 불일치
- 닫힌 어휘 밖의 preservation_status · mention_mode · distortion_flag
- `blocked` 인데 사유가 없음
- `judge_kind` 가 lexical 인 레코드에 semantic 판정이 실림
- provenance_class 누락

## 세 축을 한 칸으로 합치지 않는다

`preservation_status`(명제 보존) · `mention_mode`(발화 양태) · `relation_engaged`(관계 관여)
는 따로 기록한다. `absent + relation_engaged=true` 가 성립해야 한다 — 원 사실을 말하지
않고 **더 강한 사실을 지어내 말한 경우**가 "아예 말 안 함"과 같은 칸에 들어가면 안 된다.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from modules import paths


class SpecError(Exception):
    """판독 계약 위반. 조용히 넘기지 않고 여기서 멈춘다."""


# ── 닫힌 어휘 ────────────────────────────────────────────────────────────────
# 값을 늘리려면 명세 문서와 교정셋을 함께 고친다. 코드에서만 늘리지 않는다.
PRESERVATION_STATUSES = ("exact", "faithful", "partial", "absent", "contradicted", "blocked")
#: 주지표 집계에 들어가는 상태. partial 은 별도 보고, blocked 는 분모에서 뺀다.
PRIMARY_STATUSES = ("exact", "faithful")
#: 조건 충족 근거로 쓸 수 있는 상태. 나머지는 undetermined 를 만든다.
EVIDENTIAL_STATUSES = ("exact", "faithful")

MENTION_MODES = ("asserted", "attributed", "hypothetical", "counterargument", "none")

DISTORTION_FLAGS = (
    "wrong_subject", "wrong_object", "wrong_value", "polarity_flip",
    "modality_strengthening", "modality_weakening",
    "unsupported_causal_link", "unsupported_concrete_extension",
    "condition_relabeling", "source_dropped", "canonical_ambiguity",
)

#: semantic 판정을 실을 수 있는 판정자. lexical 은 보조지표라 여기 없다.
SEMANTIC_JUDGE_KINDS = ("human", "independent-judge", "adjudicated")

REQUIRED_RECORD_FIELDS = (
    "issue_id", "spec_version", "fact_id", "preservation_status", "mention_mode",
    "relation_engaged", "provenance_class",
)


@dataclass
class FactSpec:
    fact_id: str
    proposition: str
    slots: dict
    required_slots: list
    accepted_paraphrase: list = field(default_factory=list)
    contradiction_policy: list = field(default_factory=list)
    lexical_probes: list = field(default_factory=list)
    atomicity: str = "simple"
    note: str = ""


@dataclass
class DetectionSpec:
    issue_id: str
    spec_id: str
    spec_version: str
    material_sha256: str
    calibration_version: str
    facts: dict
    requirements: dict
    candidates: list
    lexical_is_primary: bool = False

    def verify_material(self) -> None:
        """명세가 가리키는 재료가 그대로인지 본다. 다르면 집계하지 않는다."""
        actual = sha256_of(paths.facts(self.issue_id))
        if actual != self.material_sha256:
            raise SpecError(
                f"재료 해시 불일치 [{self.issue_id}] — 명세 {self.material_sha256[:12]}… / "
                f"실제 {actual[:12]}…. 재료가 바뀌었으면 명세와 교정셋을 함께 올려라.")


@dataclass
class CalibrationSet:
    issue_id: str
    version: str
    cases: list


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── 로딩 ─────────────────────────────────────────────────────────────────────

def load(issue_id: str) -> DetectionSpec:
    p = paths.detection_spec(issue_id)
    if not p.exists():
        raise SpecError(
            f"판독 명세 없음: {issue_id} ({p}). 등록되지 않은 이슈로는 의미 집계를 하지 않는다.")
    doc = json.loads(p.read_text(encoding="utf-8"))
    facts = {}
    for fid, raw in doc["facts"].items():
        missing = [k for k in ("proposition", "slots", "required_slots") if k not in raw]
        if missing:
            raise SpecError(f"{issue_id}/{fid}: 명세 필수 항목 없음 {missing}")
        if not raw["required_slots"]:
            raise SpecError(f"{issue_id}/{fid}: required_slots 가 비었다")
        facts[fid] = FactSpec(fact_id=fid, **raw)
    return DetectionSpec(
        issue_id=doc["issue_id"], spec_id=doc["spec_id"],
        spec_version=doc["spec_version"], material_sha256=doc["material_sha256"],
        calibration_version=doc.get("calibration_version", ""),
        facts=facts, requirements=doc.get("requirements", {}),
        candidates=doc.get("candidates", []),
        lexical_is_primary=doc.get("lexical_is_primary", False))


def load_calibration(issue_id: str) -> CalibrationSet:
    p = paths.calibration_set(issue_id)
    if not p.exists():
        raise SpecError(f"교정셋 없음: {issue_id} ({p})")
    doc = json.loads(p.read_text(encoding="utf-8"))
    return CalibrationSet(issue_id=doc["issue_id"], version=doc["version"],
                          cases=doc["cases"])


def read_coding_csv(path, *, issue_id: str, spec_version: str) -> list:
    """구조화된 사람/독립판정 코딩 기록을 읽는다. 검증은 validate_record 가 따로 한다.

    `issue_id`·`spec_version` 은 **키워드 필수**다. 기본값을 두지 않는 이유가 있다.

    첫 실물(2026-08-20 r0 코딩 CSV)에는 두 칸이 아예 없다. 사람이 v1 재료를 보고 손으로
    적은 표이고 그때는 명세가 없었다. 그 파일을 읽히게 하려고 검증을 느슨하게 하면
    **판본 표시 없는 레코드가 아무 명세로나 통과한다** — 처음에 그렇게 짰다가 되돌렸다.

    그래서 읽는 쪽이 "이 표는 어느 재료·어느 명세의 것인가"를 선언하게 한다. 추측하지
    않는다. 명세가 없던 시절 자료라면 `spec_version="pre-spec"` 처럼 그 사실을 적으면 되고,
    그러면 어떤 명세로 검증해도 버전 불일치로 막힌다. 그것이 맞는 동작이다.

    파일에 이미 값이 있는데 인자와 다르면 죽는다 — 조용히 덮어쓰지 않는다.
    """
    p = Path(path)
    if not p.exists():
        raise SpecError(f"코딩 기록 없음: {p}")
    with p.open(encoding="utf-8", newline="") as fp:
        rows = list(csv.DictReader(fp))
    if not rows:
        raise SpecError(f"코딩 기록이 비었다: {p}")
    for i, r in enumerate(rows, 1):
        for key, declared in (("issue_id", issue_id), ("spec_version", spec_version)):
            have = (r.get(key) or "").strip()
            if have and have != declared:
                raise SpecError(
                    f"{p.name}:{i} {key} 충돌 — 파일 {have!r} / 선언 {declared!r}. "
                    f"덮어쓰지 않는다.")
            r[key] = declared
        r["relation_engaged"] = _as_bool(r.get("relation_engaged"))
        r["lexical_hit"] = _as_bool(r.get("lexical_hit"))
        flags = (r.get("distortion_flags") or "").strip()
        r["distortion_flags"] = [f for f in flags.replace(",", ";").split(";") if f]
    return rows


def _as_bool(v):
    if isinstance(v, bool) or v is None:
        return bool(v)
    return str(v).strip().lower() in ("true", "1", "yes", "y")


# ── 검증 ─────────────────────────────────────────────────────────────────────

def validate_record(spec: DetectionSpec, record: dict) -> None:
    """판정 레코드 하나를 명세에 비추어 본다. 위반은 예외지 경고가 아니다."""
    missing = [k for k in REQUIRED_RECORD_FIELDS if k not in record]
    if missing:
        raise SpecError(f"판정 레코드 필수 항목 없음: {missing}")

    if record["issue_id"] != spec.issue_id:
        raise SpecError(f"이슈 불일치: 레코드 {record['issue_id']} / 명세 {spec.issue_id}")

    # 버전은 필수다. 「없으면 통과」로 두면 판본 표시 없는 레코드가 아무 명세로나 통과한다.
    ver = record["spec_version"]
    if ver != spec.spec_version:
        raise SpecError(f"명세 버전 불일치: 레코드 {ver!r} / 명세 {spec.spec_version!r}")

    if record["fact_id"] not in spec.facts:
        raise SpecError(
            f"명세에 없는 fact_id: {record['fact_id']} — 판본이 섞였을 수 있다 "
            f"(명세 {spec.issue_id}). fact_id 만으로 합치지 말고 (issue_id, fact_id) 를 키로 써라.")

    status = record["preservation_status"]
    if status not in PRESERVATION_STATUSES:
        raise SpecError(f"등록되지 않은 preservation_status: {status!r}")

    mode = record["mention_mode"]
    if mode not in MENTION_MODES:
        raise SpecError(f"등록되지 않은 mention_mode: {mode!r}")

    for f in record.get("distortion_flags") or []:
        if f not in DISTORTION_FLAGS:
            raise SpecError(f"등록되지 않은 distortion_flag: {f!r}")

    if status == "blocked" and not (record.get("reason") or "").strip():
        raise SpecError(f"{record['fact_id']}: blocked 는 사유가 필수다 — 근거 없는 차단은 은폐다")

    jk = record.get("judge_kind")
    if jk is not None and jk not in SEMANTIC_JUDGE_KINDS:
        raise SpecError(
            f"judge_kind={jk!r} 로는 semantic 판정을 실을 수 없다 — lexical 은 보조지표다. "
            f"허용: {', '.join(SEMANTIC_JUDGE_KINDS)}")

    if not (record.get("provenance_class") or "").strip():
        raise SpecError("provenance_class 가 비었다 — 관측 출력과 독립 사례를 섞지 않는다")


def validate_calibration_case(spec: DetectionSpec, case: dict) -> None:
    """교정 사례 하나. 기대 상태가 닫힌 어휘 안이어야 하고 계보가 독립이어야 한다."""
    for k in ("fact_id", "text", "expected_status", "provenance_class"):
        if k not in case:
            raise SpecError(f"교정 사례 필수 항목 없음: {k}")
    if case["fact_id"] not in spec.facts:
        raise SpecError(f"명세에 없는 fact_id: {case['fact_id']}")
    if case["expected_status"] not in PRESERVATION_STATUSES:
        raise SpecError(f"등록되지 않은 expected_status: {case['expected_status']!r}")
    for f in case.get("expected_flags") or []:
        if f not in DISTORTION_FLAGS:
            raise SpecError(f"등록되지 않은 expected_flag: {f!r}")
    if case["provenance_class"] != "independent-from-observed-output":
        raise SpecError(
            f"{case['fact_id']}: 교정 사례의 계보가 독립이 아니다 ({case['provenance_class']}). "
            f"관측 출력으로 만든 규칙을 같은 출력에서 평가하면 성능 주장이 성립하지 않는다.")
