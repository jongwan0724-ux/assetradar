"""Fab 세일·기간 한정 무료 수집기."""
from __future__ import annotations

import re

from ..models import Offer, SourceResult
from ..util import sale_and_regular, guess_category
from .. import jsonproducts
from . import CARDS_JS

LINK = r"fab\.com/listings/([0-9a-f-]{36})"


def parse_cards(cards: list[dict], free_page: bool = False) -> dict[str, Offer]:
    out: dict[str, Offer] = {}
    for c in cards:
        m = re.search(LINK, c["href"])
        if not m:
            continue
        price, regular = sale_and_regular(c["text"])
        if free_page:
            # 무료 페이지 카드는 'Free*  $19.99' 형태: 남은 $값이 정가
            vals = [v for v in (price, regular) if v]
            regular, price = (max(vals) if vals else None), 0.0
        if price is None:
            continue
        lines = [x.strip() for x in c["text"].split("\n") if x.strip()]
        title = c["title"] or (lines[0] if lines else "")
        publisher = c.get("publisher") or (lines[1] if len(lines) > 1 and "$" not in lines[1] else "")
        uid = m.group(1)
        out["f-" + uid] = Offer(id="f-" + uid, store="Fab", name=title, url=f"https://www.fab.com/listings/{uid}",
                                price=price, regular=regular, publisher=publisher, category=guess_category(title))
    return out


def merge_json(offers: dict[str, Offer], payloads: list) -> None:
    for _, payload in payloads:
        for p in jsonproducts.extract(payload):
            o = offers.get("f-" + str(p["id"]))
            if not o:
                continue
            if o.regular is None and p["regular"]:
                o.regular = p["regular"]
            if o.price is None and p["price"] is not None:
                o.price = p["price"]


def collect(new_page, cfg: dict) -> SourceResult:
    res = SourceResult(store="Fab")
    page = new_page()
    offers: dict[str, Offer] = {}
    try:
        for key, free in (("free_url", True), ("sale_url", False)):
            if not cfg.get(key):
                continue
            page.goto(cfg[key], wait_selector="a[href*='/listings/']", scrolls=cfg.get("scrolls", 6))
            cards = page.eval(f"({CARDS_JS})({{linkPattern: {LINK!r}, publisherPattern: 'sellers/'}})")
            got = parse_cards(cards, free_page=free)
            print(f"[Fab] {key}: 카드 {len(cards)}개, 상품 {len(got)}개")
            for k, v in got.items():
                offers.setdefault(k, v)
        merge_json(offers, page.json_responses)
        # 할인율 큰 순으로 상한 개수만 유지
        ranked = sorted(offers.values(), key=lambda o: (not o.free, -(o.discount or 0)))
        res.offers = ranked[: cfg.get("max_items", 300)]
        if len(res.offers) < cfg.get("min_expected", 1):
            page.snapshot("fab")
    except Exception as e:
        res.ok, res.error = False, f"{type(e).__name__}: {e}"
        page.snapshot("fab")
    return res
