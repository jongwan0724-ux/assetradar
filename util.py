"""파싱·수집 공통 도우미."""
from __future__ import annotations

import re
from typing import Any, Iterator, Optional

_MONEY = re.compile(r"(?:US)?\$\s?(\d{1,5}(?:[.,]\d{3})*(?:\.\d{1,2})?)")
_PCT = re.compile(r"-\s?(\d{1,3})\s?%")


def money_values(text: str) -> list[float]:
    """'$45.00$90.00-50%' -> [45.0, 90.0]. 천 단위 쉼표 허용."""
    out = []
    for m in _MONEY.finditer(text or ""):
        out.append(float(m.group(1).replace(",", "")))
    return out


def discount_pct(text: str) -> Optional[int]:
    m = _PCT.search(text or "")
    return int(m.group(1)) if m else None


def sale_and_regular(text: str) -> tuple[Optional[float], Optional[float]]:
    """카드 텍스트에서 (현재가, 정가)를 추정. 'Free'만 있으면 (0, None)."""
    vals = money_values(text)
    if len(vals) >= 2:
        return min(vals[:2]), max(vals[:2])
    if len(vals) == 1:
        pct = discount_pct(text)
        if pct and 0 < pct < 100:
            regular = round(vals[0] / (1 - pct / 100), 2)
            return vals[0], regular
        return vals[0], None
    if re.search(r"\bfree\b", text or "", re.I):
        return 0.0, None
    return None, None


def to_float(v: Any) -> Optional[float]:
    """'45.00', 4500(센트 아님), {'value':..} 등 숫자처럼 생긴 값을 float로."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        vals = money_values(v if "$" in v else "$" + v.strip())
        return vals[0] if vals else None
    if isinstance(v, dict):
        for k in ("value", "amount", "price"):
            if k in v:
                return to_float(v[k])
    return None


def walk(obj: Any) -> Iterator[dict]:
    """JSON 트리 안의 모든 dict를 깊이 우선으로 돌려준다."""
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            yield cur
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)


def first_key(d: dict, *names: str) -> Any:
    for n in names:
        if n in d and d[n] not in (None, ""):
            return d[n]
    return None


def guess_category(*texts: str) -> str:
    t = " ".join(x or "" for x in texts).lower()
    rules = [
        ("pixel", r"pixel|16x16|32x32|8-bit|tileset"),
        ("audio", r"\baudio\b|sound|sfx|music|voice"),
        ("vfx", r"\bv?fx\b|particle|effect|shader|post.?process"),
        ("tmpl", r"template|starter kit|complete project|engine\b|framework"),
        ("3d", r"\b3d\b|low.?poly|environment|model|character|prop|animation|scan"),
        ("2d", r"\b2d\b|\bui\b|\bgui\b|icon|sprite|background|font"),
        ("tool", r"tool|editor|plugin|system|inspector|integration|ai\b"),
    ]
    for cat, pat in rules:
        if re.search(pat, t):
            return cat
    return "tool"
