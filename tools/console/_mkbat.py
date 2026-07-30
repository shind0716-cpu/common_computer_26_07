"""run_console.bat 생성기 — 인코딩·줄바꿈·파서 함정을 한 곳에서 통제한다.

왜 .bat 을 직접 편집하지 않고 이 스크립트로 떨어뜨리나 (실측 사고 2건, 2026-07-30):

1. **인코딩**: .bat 파서는 `chcp 65001` 이 실행되기 *전에* 파일을 OS 코드페이지로
   읽는다. UTF-8 로 저장하면 한글 줄이 깨져 명령으로 오인된다
   ('ython' is not recognized). → cp949 로 기록해야 한다.
2. **줄바꿈**: .gitattributes 의 `* text=auto eol=lf` 가 체크아웃에서 CRLF→LF 로
   바꾼다. cmd.exe 는 LF 만으로도 대개 돌지만, 괄호 블록 `if ... (` ... `)` 안에서
   한글·caret 이스케이프가 섞이면 블록이 조기 종료돼 안쪽 echo 줄이 명령으로
   튀어나온다('걍?설치'은(는) 내부 또는 외부 명령...). → CRLF 로 기록 +
   .gitattributes 에 `*.bat text eol=crlf` 를 못 박는다.

그래서 이 파일이 지키는 규칙 3개:
- 괄호 블록(`if ( ... )`)을 쓰지 않는다 → `if not exist X goto :label` 로 우회
- caret 이스케이프(`^(`)를 쓰지 않는다 → 괄호를 문장에서 뺀다
- 한글은 echo 한 줄에 하나씩, 특수문자 없이

실행: python tools/console/_mkbat.py   (리포 루트에서)
"""
from pathlib import Path

LINES = [
    "@echo off",
    "chcp 65001 >nul",
    "setlocal",
    'cd /d "%~dp0"',
    "",
    "echo ============================================================",
    "echo   실험 콘솔 v0 - 로컬 웹앱 실행기",
    "echo   시나리오 / 설정+실행 / 수첩 매트릭스 / 개입 모드",
    "echo ============================================================",
    "echo.",
    "",
    "set \"PYCMD=\"",
    "where py >nul 2>nul && set \"PYCMD=py\"",
    "if not defined PYCMD where python >nul 2>nul && set \"PYCMD=python\"",
    "if not defined PYCMD goto :nopython",
    "",
    "echo [1/3] 콘솔 패키지 설치 - fastapi, uvicorn, requests",
    "%PYCMD% -m pip install --quiet -r tools\\console\\requirements.txt",
    "if errorlevel 1 echo     경고: 설치에 문제가 있었지만 계속 시도합니다",
    "echo     완료",
    "echo.",
    "",
    "REM 키 점검 - 엔진은 호출 실패를 5회 재시도 후 공백 발화로 넘긴다.",
    "REM 키가 죽어 있으면 전 발화가 빈 로그가 조용히 완주하고, 호출을 다 태운",
    "REM 뒤에야 폴백 카운터로 알게 된다. 그래서 돌리기 전에 사람에게 알린다.",
    "echo [2/3] API 키 점검 - 어떤 모델을 실제로 쓸 수 있는지",
    "if not exist \".env\" goto :nodotenv",
    "%PYCMD% -X utf8 -m tools.console.keycheck",
    "goto :serve",
    "",
    ":nodotenv",
    "echo     경고: .env 파일이 없습니다",
    "echo     실호출은 안 되고 화면만 볼 수 있습니다",
    "echo     .env.example 을 .env 로 복사한 뒤 키를 넣으세요",
    "",
    ":serve",
    "echo.",
    "echo [3/3] 서버 시작 - 브라우저가 곧 열립니다",
    "echo     이 창을 닫으면 서버가 꺼집니다",
    "echo.",
    "echo   [!] 이 콘솔은 인증이 없습니다. 내 컴퓨터 전용입니다.",
    "echo   [!] 코드를 수정하면 이 창을 닫고 다시 실행해야 반영됩니다.",
    "echo.",
    'start "" "http://127.0.0.1:8021"',
    "%PYCMD% -m uvicorn tools.console.app:app --port 8021",
    "goto :done",
    "",
    ":nopython",
    "echo [X] 파이썬을 찾지 못했습니다",
    "echo     quickstart.bat 을 먼저 실행해 보세요",
    "pause",
    "",
    ":done",
    "endlocal",
]


def main() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    out = root / "run_console.bat"
    # CRLF + cp949 — 위 독스트링의 함정 2개를 둘 다 피한다.
    out.write_bytes(("\r\n".join(LINES) + "\r\n").encode("cp949"))
    print(f"WROTE {out} ({out.stat().st_size} bytes, cp949, CRLF)")


if __name__ == "__main__":
    main()
