"""이벤트(역대 최저가, 새 무료, 세일 시작)를 알림 파일·RSS·디스코드로 내보낸다."""
from __future__ import annotations

import json
import os
import urllib.request
from email.utils import format_datetime
from datetime import datetime, timezone
from xml.sax.saxutils import escape

LABEL = {"new_low": "역대 최저가", "new_free": "기간 한정 무료", "sale_started": "세일 시작"}
SITE = os.environ.get("ASSETRADAR_SITE", "https://YOUR_ID.github.io/assetradar/")


def line(e: dict) -> str:
    p = "무료" if e.get("price") == 0 else (f"${e['price']:.2f}" if e.get("price") is not None else "가격 확인")
    r = f" (정가 ${e['regular']:.2f})" if e.get("regular") else ""
    return f"[{LABEL[e['type']]}] {e['name']} · {e['store']} · {p}{r}"


def update_feed(prev: list[dict], new: list[dict], keep: int = 100) -> list[dict]:
    return (new + prev)[:keep]


def rss(events: list[dict]) -> str:
    now = format_datetime(datetime.now(timezone.utc))
    items = "".join(
        f"<item><title>{escape(line(e))}</title><link>{escape(e['url'])}</link>"
        f"<guid isPermaLink=\"false\">{escape(e['type'] + ':' + e['id'] + ':' + e['date'])}</guid>"
        f"<pubDate>{format_datetime(datetime.fromisoformat(e['date']).replace(tzinfo=timezone.utc))}</pubDate></item>"
        for e in events[:50]
    )
    return ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>AssetRadar 알림</title><link>{escape(SITE)}</link>"
            f"<description>게임 에셋 역대 최저가·무료·세일 시작 알림</description><lastBuildDate>{now}</lastBuildDate>{items}</channel></rss>\n")


def discord(new: list[dict]) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url or not new:
        return
    text = "\n".join(f"• {line(e)}\n  {e['url']}" for e in new[:10])
    if len(new) > 10:
        text += f"\n…외 {len(new) - 10}건 · {SITE}"
    body = json.dumps({"username": "AssetRadar", "content": text[:1900]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "AssetRadarBot"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print(f"[discord] 전송 실패: {e}")
