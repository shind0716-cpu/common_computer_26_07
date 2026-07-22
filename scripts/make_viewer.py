"""[민옥 · 관측 레이어 트랙] 뷰어 생성기 — 실행 한 판을 자기완결 HTML 하나로 굽는다.

무엇: modules.viewmodel 이 만든 뷰모델(JSON)을 scripts/viewer_template.html 에 내장해
viewers/viewer_{issue}_{run}.html 을 생성한다. 결과 파일은 더블클릭으로 열리고(서버·설치·
네트워크 불필요), 팀원에게 파일 하나로 공유 가능하며, "그때 그 실험"의 스냅샷으로 보존된다.

구조 원칙(보드 7/22 설계 제안 + 협의): **뷰모델 = 계약, 서빙 = 어댑터.**
이 스크립트는 정적 생성 어댑터다 — FastAPI 등 서버 어댑터가 와도 같은
modules.viewmodel.build_viewmodel() 을 소비하면 화면 자산이 그대로 이식된다.

사용: python scripts/make_viewer.py --issue issue_esa --run dryrun2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules.viewmodel import build_viewmodel  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent / "viewer_template.html"
PLACEHOLDER = "/*__DATA__*/null"


def make_viewer(issue_id: str, run_id: str, out: Path | None = None) -> Path:
    vm = build_viewmodel(issue_id, run_id)
    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise RuntimeError(f"템플릿에 데이터 자리({PLACEHOLDER}) 없음: {TEMPLATE}")
    # </script> 조기 종료 방지 이스케이프 — 발화 원문에 태그가 있어도 안전.
    payload = json.dumps(vm, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace(PLACEHOLDER, payload)

    if out is None:
        out = paths.DATA.parent / "viewers" / f"viewer_{issue_id}_{run_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[viewer] 작성: {out} — 더블클릭으로 열면 됩니다 "
          f"(팩트 {vm['meta']['n_facts']} x 스테이지 {len(vm['stages'])}, "
          f"재주입 {len(vm['injects'])}건)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="팩트 생존 뷰어 생성 (자기완결 HTML)")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    make_viewer(args.issue, args.run, args.out)


if __name__ == "__main__":
    main()
