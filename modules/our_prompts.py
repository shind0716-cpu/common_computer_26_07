"""[상류 · 민옥] 우리 소유 템플릿 로더 — 본실험(협력·무입장) 전용.

저자 로더(authors_prompts)와 분리하는 이유: 저자 원본은 재현 트랙의 증거물(글자 단위
계승·무수정)이고, 이 파일이 읽는 prompts/ 는 본실험 소유물이다(저자 제약 해방 — 편차
D2 각주, 설정 사전 §2-3). 우리 소유라 라이선스 문제 없음.

등록제(스키마 v0.3 경계 조항 A-3): 새 템플릿은 TEMPLATES 등재 + debate_engine 의
assemble_coop_* 재조립 규칙과 쌍으로 추가한다 — validate --deep 이 이 쌍을 집행한다.

수첩(coop_continue_note)·최종(coop_final)은 파일만 등재 — 엔진 연결은 수첩 슬롯
스키마 안건(요한 소관) 확정 후.
"""
import hashlib
from pathlib import Path

from modules.paths import ROOT

DIR = ROOT / "prompts"
TEMPLATES = ("coop_initial", "coop_continue", "coop_continue_note", "coop_final")


def load(name: str) -> str:
    """prompts/{name}.txt 원문 반환. 미등록 이름은 즉사(등록제 집행)."""
    if name not in TEMPLATES:
        raise KeyError(f"미등록 우리 템플릿: {name} (등록: {TEMPLATES})")
    p = DIR / f"{name}.txt"
    if not p.exists():
        raise RuntimeError(f"템플릿 파일 없음: {p}")
    return p.read_text(encoding="utf-8")


def version_tag() -> str:
    """템플릿 전체 내용의 해시 — 프롬프트 버전 식별자(재현성 근거).
    저자 쪽 delibtrace@<커밋>과 대칭으로 ours@<내용해시8>."""
    h = hashlib.sha256()
    for name in TEMPLATES:
        h.update(load(name).encode("utf-8"))
    return f"ours@{h.hexdigest()[:8]}"
