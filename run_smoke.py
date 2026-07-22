"""팀 퀵스타트용 스모크 검증 — API 키 없이 파이프라인이 도는지 한 방에 확인.

무엇을 하나(전부 API 불필요):
  1) 파일 계약(validate) — 정본 픽스처 4종이 스키마 v0.2를 지키는가
  2) 단위 테스트 — tests/ 전체 자동 발견(ledger·survival·통합, 개수는 실측 출력)
  3) Ledger 점검 — 동범 드라이런 judgment에서 소실 팩트를 뽑고 재주입 블록을 생성
각 단계를 [n/3]으로 안내하고, 끝에 통과/실패를 한눈에 요약한다.

직접 실행: python run_smoke.py   (리포 루트에서)
보통은 quickstart.bat 더블클릭이 이 스크립트를 부른다.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def _run(cmd: list[str]) -> tuple[bool, str]:
    """서브프로세스 실행 -> (성공여부, 출력). 실패해도 예외 안 내고 잡는다."""
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode == 0, out
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def hr(title: str) -> None:
    print("\n" + "=" * 58)
    print(f"  {title}")
    print("=" * 58)


def main() -> int:
    print("커먼컴퓨터 · fact-ledger-pipeline 스모크 검증 (API 키 불필요)")
    results: list[tuple[str, bool]] = []

    # --- [1/3] 파일 계약 검사 ------------------------------------------------
    hr("[1/3] 파일 계약(validate) — 정본 픽스처가 스키마 v0.2를 지키는가")
    files = [
        "data/issues/issue_esa.json",
        "data/facts/facts_issue_esa.json",
        "data/assignments/assignment_issue_esa.json",
        "data/debates/debate_issue_esa_dryrun.jsonl",
    ]
    ok, out = _run([PY, "-m", "modules.validate", *files])
    print(out.strip() or "(출력 없음)")
    print("  ->", "통과 [v]" if ok else "실패 [x]")
    results.append(("파일 계약 검사", ok))

    # --- [2/3] 단위 테스트 ---------------------------------------------------
    hr("[2/3] 단위 테스트 — tests/ 전체 자동 발견 (API 없이 결정론적)")
    ok, out = _run([PY, "-m", "unittest", "discover", "-s", "tests"])
    tail = "\n".join(out.strip().splitlines()[-4:])
    print(tail or "(출력 없음)")
    print("  ->", "통과 [v]" if ok else "실패 [x]")
    # 개수는 실측 출력에서 읽는다 — 고정 숫자 하드코딩 금지(개수가 늘 때마다 낡는다).
    import re
    m = re.search(r"Ran (\d+) tests", out)
    n_tests = m.group(1) if m else "?"
    results.append((f"단위 테스트 {n_tests}종", ok))

    # --- [3/3] Ledger 점검 ---------------------------------------------------
    hr("[3/3] Ledger 점검 — 드라이런 judgment에서 소실 팩트 추출·재주입")
    ok, out = _run([PY, "-m", "modules.ledger",
                    "--issue", "issue_esa", "--run", "dryrun", "--stage", "3"])
    # 핵심 줄만 보여준다(장부 재고지 블록은 길어서 앞부분만)
    lines = out.strip().splitlines()
    for ln in lines:
        if "소실 팩트" in ln or "issue=" in ln:
            print(ln)
    print("  (재주입 블록·ledger_inject 이벤트도 정상 생성됨 — 자세히 보려면 아래 명령 직접 실행)")
    print("   python -m modules.ledger --issue issue_esa --run dryrun --stage 3")
    print("  ->", "통과 [v]" if ok else "실패 [x]")
    results.append(("Ledger 소실팩트 점검", ok))

    # --- 최종 요약 -----------------------------------------------------------
    hr("결과 요약")
    all_ok = all(v for _, v in results)
    for name, v in results:
        print(f"  {'[v]' if v else '[x]'}  {name}")
    print()
    if all_ok:
        print("  [OK] 모든 검사 통과 — 파이프라인이 이 컴퓨터에서 정상 작동합니다.")
        print("     실제 토론(API 호출)까지 보려면 run_debate.bat 을 실행하세요(.env 키 필요).")
    else:
        print("  [FAIL] 일부 검사 실패 — 위 로그를 확인하세요.")
        print("     흔한 원인: (1) 리포 루트가 아닌 곳에서 실행 (data/·modules/ 폴더가 보이는 자리에서)")
        print("               (2) pyyaml 미설치 -> pip install pyyaml")
        print("               (3) Python 3.10 미만 -> python --version 확인")
    print()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
