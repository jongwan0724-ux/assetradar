"""Unity Asset Store 세일 수집기."""
from __future__ import annotations

import re

from ..models import Offer, SourceResult
from ..util import sale_and_regular
from .. import jsonproducts
from . import CARDS_JS

LINK = r"assetstore\.unity\.com/packages/[^?#]*?-(\d+)(?:[/?#]|$)"
CAT = {"tools": "tool", "3d": "3d", "2d": "2d", "vfx": "vfx", "audio": "audio", "templates": "tmpl",
       "essentials": "tool", "add-ons": "tool", "ai-ml-integration": "tool", "decentralization": "tool"}


def category_from_url(url: str) -> str:
    m = re.search(r"/packages/([^/]+)/", url)
    return CAT.get(m.group(1), "tool") if m else "tool"


def parse_cards(cards: list[dict]) -> dict[str, Offer]:
    out: dict[str, Offer] = {}
    for c in cards:
        m = re.search(LINK, c["href"])
        if not m:
            continue
        price, regular = sale_and_regular(c["text"])
        if price is None:
            continue
        title = c["title"] or c["text"].split("\n")[0]
        pid = "u" + m.group(1)
        out[pid] = Offer(id=pid, store="Unity", name=title, url=c["href"].split("?")[0], price=price,
                         regular=regular, publisher=c.get("publisher", ""), category=category_from_url(c["href"]))
    return out


def merge_json(offers: dict[str, Offer], payloads: list) -> None:
    """내부 JSON에서 얻은 정가 정보로 빈칸을 채운다(이름·URL은 카드 쪽을 우선)."""
    for _, payload in payloads:
        for p in jsonproducts.extract(payload):
            if not str(p["id"]).isdigit():
                continue
            o = offers.get("u" + str(p["id"]))
            if o and o.regular is None and p["regular"]:
                o.regular = p["regular"]


def collect(new_page, cfg: dict) -> SourceResult:
    res = SourceResult(store="Unity")
    page = new_page()
    offers: dict[str, Offer] = {}
    try:
        for n in range(1, cfg.get("max_pages", 5) + 1):
            url = cfg["url"] + (f"&page={n}" if n > 1 else "")
            page.goto(url, wait_selector="a[href*='/packages/']")
            cards = page.eval(f"({CARDS_JS})({{linkPattern: {LINK!r}, publisherPattern: 'publishers/'}})")
            got = parse_cards(cards)
            new = {k: v for k, v in got.items() if k not in offers}
            print(f"[Unity] page {n}: 카드 {len(cards)}개, 새 상품 {len(new)}개")
            if not new:
                break
            offers.update(new)
        merge_json(offers, page.json_responses)
        res.offers = list(offers.values())
        if len(res.offers) < cfg.get("min_expected", 1):
            page.snapshot("unity")
    except Exception as e:
        res.ok, res.error = False, f"{type(e).__name__}: {e}"
        page.snapshot("unity")
    return res
