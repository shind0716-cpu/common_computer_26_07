"""[공용 · 요한(Claude)] 줄바꿈에 흔들리지 않는 파일 지문.

왜 이 모듈이 필요한가 (2026-08-20 실측):

승격 관문·DetectionSpec·manifest 가 전부 `hashlib.sha256(path.read_bytes())` 로 재료의
지문을 찍고 registry 에 박아 두는데, **같은 커밋을 새로 체크아웃하면 그 지문이 안 맞았다.**

- `.gitattributes` 는 `*.json text eol=lf` — 저장소 정본 바이트는 LF 다.
- 그런데 빌드 스크립트가 Windows 에서 `Path.write_text()` 로 쓴다. 기본 `newline=None` 은
  `\n` 을 `os.linesep`(CRLF)로 바꿔 쓴다. 그래서 작업본은 CRLF, 저장소는 LF 가 된다.
- git 은 이 차이를 정규화해서 흡수하므로 `git status` 는 깨끗하다 — 아무도 눈치채지 못한다.
- 결과: registry 에 적힌 지문은 **이 PC 의 CRLF 사본** 지문이고, 팀원이 클론하면
  material·spec·calibration 이 전부 `hash mismatch` 로 차단된다. 실측으로 깨끗한
  worktree 에서 전체 테스트 19건이 실패했다(전부 지문 비교).

그래서 지문을 **줄바꿈 정규화 뒤에** 찍는다. CRLF 로 쓰인 파일과 LF 로 체크아웃된 같은
파일이 같은 지문을 갖는다. 어느 OS 에서 만들었든, 어떤 체크아웃이든 같은 값이 나온다.

무엇을 포기하는가: 내용이 같고 줄바꿈만 다른 두 파일을 구별하지 못한다. 텍스트 재료의
동일성 판정에서 그 구별은 의미가 없고, 오히려 그걸 구별해서 이 사고가 났다.

이 함수를 쓰지 않고 `read_bytes()` 로 직접 지문을 찍는 자리를 새로 만들지 마라 — 그 자리가
곧 같은 사고의 재발 지점이다.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def normalize(data: bytes) -> bytes:
    """CRLF·CR 을 LF 로 접는다. 저장소 정본(eol=lf) 과 같은 모양으로 만든다."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(normalize(data)).hexdigest()


def sha256_file(path: Path) -> str:
    """파일 지문. 줄바꿈 방식과 무관하게 같은 내용이면 같은 값."""
    return sha256_bytes(Path(path).read_bytes())
