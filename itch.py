"""itch.io 세일 중인 게임 에셋 수집기."""
from __future__ import annotations

import re

from ..models import Offer, SourceResult
from ..util import money_values, discount_pct, guess_category

# itch.io 목록 카드(.game_cell)에서 필요한 값만 뽑는다. 클래스가 없으면 링크 기준으로 대체.
CELLS_JS = r"""
() => [...document.querySelectorAll('.game_cell')].map(c => ({
  gid: c.getAttribute('data-game_id') || '',
  href: (c.querySelector('a.title, .game_title a, a.thumb_link') || {}).href || '',
  title: ((c.querySelector('a.title') || c.querySelector('.game_title') || {}).innerText || '').trim(),
  author: ((c.querySelector('.game_author') || {}).innerText || '').trim(),
  price: ((c.querySelector('.price_value') || {}).innerText || '').trim(),
  sale: ((c.querySelector('.sale_tag') || {}).innerText || '').trim(),
  genre: ((c.querySelector('.game_genre') || {}).innerText || '').trim(),
  text: (c.innerText || '').slice(0, 400)
}))
"""


def parse_cells(cells: list[dict]) -> dict[str, Offer]:
    out: dict[str, Offer] = {}
    for c in cells:
        if not c.get("href"):
            continue
        vals = money_values(c.get("price") or c.get("text", ""))
        pct = discount_pct(c.get("sale") or c.get("text", ""))
        if not vals:
            continue
        price = vals[0]
        regular = round(price / (1 - pct / 100), 2) if pct and 0 < pct < 100 else None
        gid = c.get("gid") or re.sub(r"\W+", "-", c["href"].split("//")[-1]).strip("-")
        oid = "i-" + gid
        out[oid] = Offer(id=oid, store="itch.io", name=c.get("title") or c["href"], url=c["href"].split("?")[0],
                         price=price, regular=regular, publisher=c.get("author", ""),
                         category=guess_category(c.get("title", ""), c.get("genre", ""), c.get("text", "")))
    return out


def collect(new_page, cfg: dict) -> SourceResult:
    res = SourceResult(store="itch.io")
    page = new_page()
    offers: dict[str, Offer] = {}
    try:
        for n in range(1, cfg.get("max_pages", 4) + 1):
            url = cfg["url"] + (f"?page={n}" if n > 1 else "")
            page.goto(url, wait_selector=".game_cell", scrolls=1)
            got = parse_cells(page.eval(CELLS_JS))
            new = {k: v for k, v in got.items() if k not in offers}
            print(f"[itch.io] page {n}: 새 상품 {len(new)}개")
            if not new:
                break
            offers.update(new)
        res.offers = list(offers.values())[: cfg.get("max_items", 200)]
        if len(res.offers) < cfg.get("min_expected", 1):
            page.snapshot("itch")
    except Exception as e:
        res.ok, res.error = False, f"{type(e).__name__}: {e}"
        page.snapshot("itch")
    return res
