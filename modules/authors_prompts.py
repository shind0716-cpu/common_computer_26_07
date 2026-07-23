"""[패키지 A · 신동범] 저자 코드(DelibTrace)의 프롬프트 원문 로더.

프롬프트를 우리 리포에 복사하지 않고 **원본 저장소에서 직접 읽는다.**
이유 두 가지:
1. "프롬프트 조립 로직을 글자 단위로 계승"이 요구사항인데, 복사본은 원본과 어긋날 수 있다
2. 저자 저장소에 라이선스 표기가 없어 재배포 판단을 보류한다 (기업 확인 Q12 항목)

원본 위치: 기본 `<리포 부모>/DelibTrace-main`, 환경변수 DELIBTRACE_DIR로 재지정 가능.
받는 법: git clone https://github.com/whr000001/DelibTrace.git DelibTrace-main
"""
import json
import os
from pathlib import Path

from modules.paths import ROOT

DEFAULT_DIR = ROOT.parent / "DelibTrace-main"


def author_dir() -> Path:
    """저자 코드(DelibTrace) 루트 경로. 환경변수 DELIBTRACE_DIR 우선, 없으면 기본 위치.
    폴더가 없으면 clone 안내와 함께 즉시 에러 — 프롬프트를 원본에서 읽는 설계라 없으면 진행 불가."""
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


def version_tag() -> str:
    """프롬프트 버전 식별자. 저자 저장소의 현재 커밋 해시를 쓴다 — 재현성 근거."""
    head = author_dir() / ".git" / "HEAD"
    try:
        ref = head.read_text(encoding="utf-8").strip()
        if ref.startswith("ref: "):
            sha = (author_dir() / ".git" / ref[5:]).read_text(encoding="utf-8").strip()
        else:
            sha = ref
        return f"delibtrace@{sha[:8]}"
    except Exception:  # noqa: BLE001 — 버전 태그는 있으면 좋고 없어도 진행
        return "delibtrace@unknown"
