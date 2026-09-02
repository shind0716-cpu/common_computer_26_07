"""[민옥] 콘솔 탭 스크린샷 도구 — WORKORDER_CONSOLE_FINAL §7 이 허용한 유일한 새 코드 파일.

하는 일: 서버가 떠 있는지 확인 → Playwright(chromium, 1280x900)로 nav 의 탭 버튼을 차례로 눌러
전체 페이지 스크린샷 → _review/<before|after>/<탭id>.png 저장 → 브라우저 콘솔 에러 수를 출력하고
같은 폴더의 errors.txt 에 남긴다. 발표 모드(/present, 새 창 링크)는 present.png 로 따로 찍는다.

사용 (worktree 루트에서, 서버는 미리 띄워 둘 것):
    PYTHONUTF8=1 python tools/console/_review/shots.py --phase before [--port 8021]

접힌 그룹(2단계 이후 「보관」) 안의 탭 버튼은 보이지 않으므로, 버튼이 안 보이면
[data-toggle] 요소를 눌러 펼친 뒤 다시 시도한다. 탭 목록은 페이지의 nav button[data-t] 에서
읽어 오므로 탭이 늘거나 순서가 바뀌어도 이 파일을 고칠 필요가 없다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def wait_quiet(page, inflight: dict, quiet_ms: int = 700, timeout_ms: int = 60000) -> bool:
    """진행 중 요청이 0 인 상태가 quiet_ms 동안 이어지면 True. timeout_ms 를 넘기면 False."""
    t0 = time.time()
    quiet_since = None
    while (time.time() - t0) * 1000 < timeout_ms:
        if inflight["n"] == 0:
            if quiet_since is None:
                quiet_since = time.time()
            elif (time.time() - quiet_since) * 1000 >= quiet_ms:
                return True
        else:
            quiet_since = None
        page.wait_for_timeout(100)  # 이벤트 루프를 돌려 request 핸들러가 실행되게
    return False


def server_up(base: str) -> bool:
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["before", "after"], required=True)
    ap.add_argument("--port", type=int, default=8021)
    ap.add_argument("--settle", type=int, default=1200, help="탭 전환 후 기다리는 ms (데이터 불러오기)")
    args = ap.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    if not server_up(base):
        print(f"[shots] server not up at {base} -- start it first:")
        print("        python -m uvicorn tools.console.app:app --port", args.port)
        return 2

    from playwright.sync_api import sync_playwright  # 늦은 import: 미설치 시 안내가 먼저 나오게

    out = HERE / args.phase
    out.mkdir(parents=True, exist_ok=True)

    errors: list[dict] = []  # {"tab":..., "kind": console|page|http, "text":...}
    current = {"tab": "(load)"}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("console", lambda m: errors.append({"tab": current["tab"], "kind": "console", "text": m.text})
                if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append({"tab": current["tab"], "kind": "page", "text": str(e)}))
        page.on("response", lambda r: errors.append({"tab": current["tab"], "kind": "http", "text": f"{r.status} {r.url}"})
                if r.status >= 400 else None)
        inflight = {"n": 0}
        page.on("request", lambda r: inflight.__setitem__("n", inflight["n"] + 1))
        page.on("requestfinished", lambda r: inflight.__setitem__("n", max(0, inflight["n"] - 1)))
        page.on("requestfailed", lambda r: inflight.__setitem__("n", max(0, inflight["n"] - 1)))

        page.goto(base + "/", wait_until="networkidle")
        page.wait_for_timeout(args.settle)
        page.screenshot(path=str(out / "_landing.png"), full_page=True)

        tab_ids = page.eval_on_selector_all("nav button[data-t]", "els => els.map(e => e.dataset.t)")
        print(f"[shots] tabs found: {len(tab_ids)} -> {' '.join(tab_ids)}")

        for tid in tab_ids:
            current["tab"] = tid
            btn = page.locator(f"nav button[data-t='{tid}']")
            if not btn.is_visible():
                toggles = page.locator("nav [data-toggle]")
                if toggles.count():
                    toggles.first.click()
                    page.wait_for_timeout(200)
            btn.click()
            # wait_for_load_state("networkidle") 는 이미 도달한 상태면 즉시 돌아와서 탭 클릭이 일으킨
            # fetch 를 기다려 주지 않는다(실측: 압박 집계 탭이 "불러오는 중" 으로 찍힘). 그래서 진행 중
            # 요청 수를 직접 세어 0 이 700ms 이상 유지될 때까지 기다린다(최대 60초).
            if not wait_quiet(page, inflight):
                print(f"[shots] {tid}: network still busy after 60s -- screenshot may show loading state")
            page.wait_for_timeout(args.settle)
            page.screenshot(path=str(out / f"{tid}.png"), full_page=True)
            print(f"[shots] {tid}.png")

        # 발표 모드 — 새 창 링크. 같은 서버의 /present 를 직접 연다.
        current["tab"] = "present"
        pres = browser.new_page(viewport={"width": 1280, "height": 900})
        pres.on("console", lambda m: errors.append({"tab": "present", "kind": "console", "text": m.text})
                if m.type == "error" else None)
        pres.on("pageerror", lambda e: errors.append({"tab": "present", "kind": "page", "text": str(e)}))
        pres.goto(base + "/present", wait_until="load")
        pres.wait_for_timeout(args.settle)
        pres.screenshot(path=str(out / "present.png"), full_page=False)  # 자족 페이지가 큼(4.8MB) — 첫 화면만
        print("[shots] present.png (viewport only)")
        browser.close()

    console_n = sum(1 for e in errors if e["kind"] in ("console", "page"))
    http_n = sum(1 for e in errors if e["kind"] == "http")
    (out / "errors.txt").write_text(
        "\n".join(f"[{e['tab']}] {e['kind']}: {e['text']}" for e in errors) + "\n", encoding="utf-8")
    (out / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[shots] console errors (console+pageerror): {console_n} ; http >=400 responses: {http_n}")
    print(f"[shots] saved to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
