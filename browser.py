"""예의 바른 헤드리스 브라우저 세션.

- robots.txt를 먼저 확인하고 금지된 경로는 열지 않는다.
- 요청 사이에 쉬는 시간을 둔다.
- 페이지가 받아오는 JSON 응답을 모아 둔다(스토어 내부 데이터 파싱용).
- 실패하면 debug/ 폴더에 HTML과 스크린샷을 남겨 수집기 수정을 돕는다.
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.robotparser
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

UA = os.environ.get(
    "ASSETRADAR_UA",
    "Mozilla/5.0 (compatible; AssetRadarBot/0.1; +https://github.com/YOUR_ID/assetradar)",
)
DEBUG_DIR = Path(os.environ.get("ASSETRADAR_DEBUG", "debug"))
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}


def allowed(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    rp = _robots.get(base)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser(base + "/robots.txt")
        try:
            rp.read()
        except Exception:  # robots.txt를 못 읽으면 보수적으로 진행하되 기록만 남긴다
            print(f"[robots] {base}/robots.txt 를 읽지 못했어요. 계속 진행합니다.")
        _robots[base] = rp
    try:
        return rp.can_fetch(UA, url)
    except Exception:
        return True


class Page:
    def __init__(self, page):
        self.page = page
        self.json_responses: list[tuple[str, object]] = []
        page.on("response", self._on_response)

    def _on_response(self, resp):
        try:
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype and resp.status == 200:
                self.json_responses.append((resp.url, resp.json()))
        except Exception:
            pass

    def goto(self, url: str, wait_selector: str | None = None, scrolls: int = 4):
        if not allowed(url):
            raise PermissionError(f"robots.txt가 이 주소를 막고 있어요: {url}")
        self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        try:
            self.page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            pass
        if wait_selector:
            try:
                self.page.wait_for_selector(wait_selector, timeout=15_000)
            except Exception:
                pass
        for _ in range(scrolls):  # 지연 로딩되는 카드를 불러오기 위해 천천히 스크롤
            self.page.mouse.wheel(0, 2400)
            time.sleep(0.8)
        time.sleep(random.uniform(2.5, 4.5))  # 요청 간 간격

    def eval(self, js: str):
        return self.page.evaluate(js)

    def snapshot(self, name: str):
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            (DEBUG_DIR / f"{name}.html").write_text(self.page.content(), encoding="utf-8")
            self.page.screenshot(path=str(DEBUG_DIR / f"{name}.png"), full_page=False)
            (DEBUG_DIR / f"{name}.json-urls.txt").write_text(
                "\n".join(u for u, _ in self.json_responses), encoding="utf-8"
            )
        except Exception as e:
            print(f"[debug] 스냅샷 저장 실패: {e}")


@contextmanager
def session():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(user_agent=UA, locale="en-US", viewport={"width": 1366, "height": 900})
        try:
            yield lambda: Page(ctx.new_page())
        finally:
            ctx.close()
            browser.close()


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
