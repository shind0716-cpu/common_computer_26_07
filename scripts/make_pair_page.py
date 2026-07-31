"""두 판 화면 한 장을 서버 없이 여는 자기완결 HTML로 굽는다.

라이브 /와 같은 tools/viewer/pair.html 자산에 /api/pair 페이로드를 넣는다.
화면 자산을 복제하지 않으며, 결과는 더블클릭·노션 첨부로 열 수 있다.

사용:
  python scripts/make_pair_page.py --issue issue_esa --a h2p_off --b h2p_v0
데이터 뿌리를 바꾸려면 VIEWER_DATA 환경변수를 함께 준다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from tools.viewer.app import api_pair, api_provenance, api_runs  # noqa: E402

TEMPLATE = ROOT / "tools" / "viewer" / "pair.html"
PLACEHOLDER = "/*__DATA__*/null"
RUNS_PLACEHOLDER = "/*__RUNS__*/null"


def make_pair_page(issue_id: str, run_a: str, run_b: str,
                   out: Path | None = None) -> Path:
    payload = api_pair(issue_id, run_a, run_b)
    runs = [r for r in api_runs()["runs"] if r["issue_id"] == issue_id]
    catalog = {
        "runs": runs,
        "provenance": {
            f"{r['issue_id']}/{r['run_id']}": api_provenance(r["issue_id"], r["run_id"])
            for r in runs
        },
    }
    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html or RUNS_PLACEHOLDER not in html:
        raise RuntimeError(f"템플릿에 데이터 자리 없음: {TEMPLATE}")
    baked = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    baked_catalog = json.dumps(catalog, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace(PLACEHOLDER, baked).replace(RUNS_PLACEHOLDER, baked_catalog)
    if out is None:
        out = paths.ROOT / "viewers" / f"pair_{issue_id}_{run_a}_vs_{run_b}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[pair] 작성: {out} — 서버 없이 더블클릭으로 열 수 있습니다 "
          f"(갈린 칸 {len(payload['divergences'])}개)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="두 판 자기완결 HTML 생성")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--a", required=True, help="첫째 run_id")
    ap.add_argument("--b", required=True, help="둘째 run_id")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    make_pair_page(args.issue, args.a, args.b, args.out)


if __name__ == "__main__":
    main()
