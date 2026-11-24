"""수집 결과를 이전 데이터와 합쳐 가격 기록·최저가·이벤트를 만든다."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from .models import SourceResult

KEEP_DAYS = 180


def _guard_failed(res: SourceResult, prev_count: int, min_expected: int) -> str:
    """수집이 비정상적으로 적으면 실패로 본다(이전 데이터를 덮어쓰지 않기 위해)."""
    n = len(res.offers)
    if not res.ok:
        return res.error or "error"
    if n < min_expected:
        return f"too few items ({n} < {min_expected})"
    if prev_count >= 20 and n < prev_count * 0.3:
        return f"sudden drop ({prev_count} -> {n})"
    return ""


def merge(prev_assets: list[dict], results: Iterable[SourceResult], today: str, min_expected: dict[str, int]):
    """반환: (assets, events, source_status)."""
    by_id = {a["id"]: dict(a) for a in prev_assets}
    events: list[dict] = []
    status: dict[str, dict] = {}

    for res in results:
        prev_count = sum(1 for a in by_id.values() if a["store"] == res.store and a.get("on_sale"))
        why = _guard_failed(res, prev_count, min_expected.get(res.store, 1))
        if why:
            status[res.store] = {"ok": False, "count": len(res.offers), "error": why}
            continue  # 이전 데이터 그대로 유지
        status[res.store] = {"ok": True, "count": len(res.offers), "error": ""}
        seen = set()
        for o in res.offers:
            seen.add(o.id)
            a = by_id.get(o.id)
            is_new = a is None
            if is_new:
                a = {"id": o.id, "store": o.store, "first_seen": today, "hist": [], "atl": None, "atl_date": None, "atl_seeded": False}
            was_on_sale, was_free, prev_atl = a.get("on_sale", False), a.get("free", False), a.get("atl")
            a.update(name=o.name or a.get("name", ""), url=o.url, publisher=o.publisher or a.get("publisher", ""),
                     category=o.category if is_new or not a.get("category") else a["category"],
                     price=o.price, regular=o.regular if o.regular is not None else a.get("regular"),
                     free=o.free, ends=o.ends, on_sale=True, last_seen=today)
            if o.price is not None:
                if not a["hist"] or a["hist"][-1][1] != o.price:
                    a["hist"].append([today, o.price])
                if prev_atl is None or o.price < prev_atl:
                    a["atl"], a["atl_date"] = o.price, today
            ev = {"id": o.id, "store": o.store, "name": a["name"], "price": o.price, "regular": a.get("regular"), "date": today, "url": o.url}
            if o.free and not was_free:
                events.append({**ev, "type": "new_free"})
            elif not is_new and prev_atl is not None and o.price is not None and o.price < prev_atl:
                events.append({**ev, "type": "new_low", "prev_low": prev_atl})
            elif not is_new and not was_on_sale:
                events.append({**ev, "type": "sale_started"})
            by_id[o.id] = a
        # 이번에 안 보인 이 스토어 상품 = 세일 종료로 간주
        for a in by_id.values():
            if a["store"] == res.store and a.get("on_sale") and a["id"] not in seen:
                a["on_sale"], a["free"], a["ends"] = False, False, None
                if a.get("regular"):
                    a["price"] = a["regular"]
                    if not a["hist"] or a["hist"][-1][1] != a["regular"]:
                        a["hist"].append([today, a["regular"]])

    cutoff = (date.fromisoformat(today) - timedelta(days=KEEP_DAYS)).isoformat()
    assets = [a for a in by_id.values() if a.get("on_sale") or a.get("atl_seeded") or a.get("last_seen", today) >= cutoff]
    assets.sort(key=lambda a: (not a.get("on_sale"), a["store"], a.get("name", "")))
    return assets, events, status
