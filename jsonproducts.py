"""스토어 페이지가 내부적으로 받아오는 JSON에서 상품처럼 생긴 객체를 찾아낸다.

스토어마다 필드 이름이 다르고 예고 없이 바뀌기 때문에, 특정 필드 이름에 의존하지 않고
'ID + 이름 + 가격 필드'를 가진 객체를 일반적으로 찾는다.
"""
from __future__ import annotations

import re
from typing import Optional

from .util import walk, to_float, first_key

_ID_KEYS = ("uid", "packageId", "package_id", "productId", "id", "listingId")
_NAME_KEYS = ("title", "name", "displayName")
_REG = re.compile(r"original|regular|list|base|full|before|was", re.I)
_SALE = re.compile(r"discount(ed)?_?price|sale|final|current|now|effective", re.I)


def _price_fields(d: dict, depth: int = 0) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in d.items():
        if isinstance(v, dict) and depth < 2:
            for k2, v2 in _price_fields(v, depth + 1).items():
                out[f"{k}.{k2}"] = v2
        elif "price" in k.lower() or k.lower() in ("amount", "value"):
            f = to_float(v)
            if f is not None and 0 <= f < 100_000:
                out[k] = f
    return out


def _cents(fields: dict[str, float], hint_regular: Optional[float]) -> dict[str, float]:
    """정수 센트 단위로 보이는 값(예: 4500)을 달러로 바꾼다."""
    vals = list(fields.values())
    if vals and all(float(v).is_integer() for v in vals) and max(vals) >= 1000:
        return {k: v / 100 for k, v in fields.items()}
    return fields


def extract(obj) -> list[dict]:
    """반환: [{id, name, price, regular, free, raw_keys}] (중복 ID 제거)."""
    seen: dict[str, dict] = {}
    for d in walk(obj):
        pid = first_key(d, *_ID_KEYS)
        name = first_key(d, *_NAME_KEYS)
        if pid is None or not isinstance(name, str) or len(name) < 2:
            continue
        fields = _price_fields(d)
        is_free = bool(d.get("isFree") or d.get("is_free"))
        if not fields and not is_free:
            continue
        fields = _cents(fields, None)
        reg = [v for k, v in fields.items() if _REG.search(k)]
        sale = [v for k, v in fields.items() if _SALE.search(k)]
        vals = list(fields.values())
        regular = max(reg) if reg else (max(vals) if len(set(vals)) > 1 else None)
        price = min(sale) if sale else (min(vals) if vals else (0.0 if is_free else None))
        if regular is not None and price is not None and price > regular:
            price, regular = regular, price
        key = str(pid)
        cand = {"id": key, "name": name, "price": price, "regular": regular, "free": is_free or (price == 0 and bool(regular)), "raw_keys": sorted(fields)}
        prev = seen.get(key)
        if prev is None or (prev["regular"] is None and regular is not None):
            seen[key] = cand
    return list(seen.values())
