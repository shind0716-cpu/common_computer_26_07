"""[패키지 A · 신동범] 저자 코드(DelibTrace)의 프롬프트 원문 로더.

프롬프트를 우리 리포에 복사하지 않고 **원본 저장소에서 직접 읽는다.**
이유 두 가지:
1. "프롬프트 조립 로직을 글자 단위로 계승"이 요구사항인데, 복사본은 원본과 어긋날 수 있다
2. 저자 저장소에 라이선스 표기가 없어 재배포 판단을 보류한다 (기업 확인 Q12 항목)

원본 위치: 기본 `<리포 부모>/DelibTrace-main`, 환경변수 DELIBTRACE_DIR로 재지정 가능.
받는 법: git clone https://github.com/whr000001/DelibTrace.git DelibTrace-main
"""
import hashlib
import json
import os
from pathlib import Path

from modules.paths import ROOT

DEFAULT_DIR = ROOT.parent / "DelibTrace-main"


def _load_env() -> None:
    """.env 를 올린다 (2026-07-30 · 민옥).

    종전엔 os.environ 만 읽어서, DELIBTRACE_DIR 을 .env 에 적어도 무시되고 기본 위치만
    봤다 — 저자 저장소를 다른 폴더에 둔 사람은 매번 셸 환경변수를 export 해야 했고,
    콘솔처럼 더블클릭으로 띄우는 경로에서는 그럴 자리가 없다. 키를 .env 에 두는 것과
    같은 규칙으로 통일한다. llm._load_env 를 import 하지 않는 이유: 이 모듈은 프롬프트
    로더이고 SDK·호출 계층에 의존하지 않는다(오프라인 테스트가 이 모듈을 그냥 import 한다)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def author_dir() -> Path:
    """저자 코드(DelibTrace) 루트 경로. 환경변수 DELIBTRACE_DIR 우선, 없으면 기본 위치.
    DELIBTRACE_DIR 은 셸 환경변수 또는 .env 어느 쪽에 있어도 된다.
    폴더가 없으면 clone 안내와 함께 즉시 에러 — 프롬프트를 원본에서 읽는 설계라 없으면 진행 불가."""
    _load_env()
    d = Path(os.environ.get("DELIBTRACE_DIR", DEFAULT_DIR))
    if not d.exists():
        raise RuntimeError(
            f"저자 코드를 찾을 수 없음: {d}\n"
            "  git clone https://github.com/whr000001/DelibTrace.git DelibTrace-main\n"
            "  (다른 위치에 두었다면 환경변수 DELIBTRACE_DIR 지정)"
        )
    return d


def load(name: str) -> str:
    """prompts/{name}.txt 원문을 그대로 반환."""
    p = author_dir() / "prompts" / f"{name}.txt"
    if not p.exists():
        raise RuntimeError(f"프롬프트 파일 없음: {p}")
    return p.read_text(encoding="utf-8")


def load_settings() -> dict:
    """discussion_setting.json — 페르소나 문구(open-minded/default/stubborn)."""
    p = author_dir() / "prompts" / "discussion_setting.json"
    return json.loads(p.read_text(encoding="utf-8"))


def prompts_digest() -> str:
    """prompts/ 안 파일 내용의 합성 해시 (2026-07-30 · 민옥).

    왜 필요한가: 저자 저장소를 zip 으로 받으면 .git 이 없어 커밋 해시가 안 잡히고,
    종전 version_tag() 는 그때 조용히 "delibtrace@unknown" 을 돌려줬다. 그 값이 로그의
    prompt_ver 로 그대로 들어가므로, **재현성 근거 칸에 '모름'이 조용히 적히는** 셈이었다
    (7/30 실측: Downloads 아래 DelibTrace-main 이 zip 사본이라 unknown). 커밋 해시가
    없으면 프롬프트 파일 자체를 지문 삼는다 — 파일이 바뀌면 지문이 바뀌므로 목적(같은
    프롬프트로 돌렸는지 나중에 대조)은 그대로 달성된다."""
    d = author_dir() / "prompts"
    h = hashlib.sha256()
    for p in sorted(d.glob("*")):
        if p.is_file():
            h.update(p.name.encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


def version_tag() -> str:
    """프롬프트 버전 식별자. 저자 저장소의 현재 커밋 해시를 쓴다 — 재현성 근거.

    .git 이 없으면(zip 사본) prompts/ 내용 해시로 대체하고, 무엇으로 잡았는지 접두사로
    구분한다: `delibtrace@<커밋8>` vs `delibtrace-files@<내용해시8>`. 둘 다 실패하면
    unknown 이지만, 그 경우가 진짜로 "식별 불가"인 경우다."""
    head = author_dir() / ".git" / "HEAD"
    try:
        ref = head.read_text(encoding="utf-8").strip()
        if ref.startswith("ref: "):
            sha = (author_dir() / ".git" / ref[5:]).read_text(encoding="utf-8").strip()
        else:
            sha = ref
        return f"delibtrace@{sha[:8]}"
    except Exception:  # noqa: BLE001 — 커밋 해시가 없으면 내용 해시로
        try:
            return f"delibtrace-files@{prompts_digest()}"
        except Exception:  # noqa: BLE001 — 버전 태그는 있으면 좋고 없어도 진행
            return "delibtrace@unknown"
