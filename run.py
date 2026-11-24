"""수집 실행: python -m collector.run [--only unity,fab,itch] [--dry-run]"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import alerts, fx
from .browser import dump_json, session
from .sources import fab, itch, unity
from .store import merge

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
CFG = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
SOURCES = {"unity": (unity, "Unity"), "fab": (fab, "Fab"), "itch": (itch, "itch.io")}


def load(name: str, default):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="unity,fab,itch")
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 출력")
    args = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    prev = load("assets.json", {"assets": []})
    meta = load("meta.json", {})
    feed = load("alerts.json", {"events": []})

    results = []
    with session() as new_page:
        for key in args.only.split(","):
            mod, store = SOURCES[key.strip()]
            print(f"== {store} 수집 시작")
            r = mod.collect(new_page, CFG[key.strip()])
            print(f"== {store}: ok={r.ok} 상품 {len(r.offers)}개 {r.error}")
            results.append(r)

    min_exp = {SOURCES[k][1]: CFG[k].get("min_expected", 1) for k in SOURCES}
    assets, events, status = merge(prev["assets"], results, today, min_exp)

    src_meta = meta.get("sources", {})
    for store, st in status.items():
        last_ok = now.isoformat() if st["ok"] else src_meta.get(store, {}).get("last_ok")
        src_meta[store] = {**st, "last_run": now.isoformat(), "last_ok": last_ok}
        if not st["ok"]:
            print(f"::warning::{store} 수집 실패, 이전 데이터를 유지했어요: {st['error']}")

    meta = {"updated": now.isoformat(), "fx": fx.fetch(meta.get("fx")), "sources": src_meta}
    feed_events = alerts.update_feed(feed["events"], events)
    print(f"이벤트 {len(events)}건, 전체 상품 {len(assets)}개, 세일 중 {sum(a.get('on_sale', False) for a in assets)}개")

    if args.dry_run:
        for e in events[:20]:
            print("  " + alerts.line(e))
        return 0
    dump_json(DATA / "assets.json", {"updated": now.isoformat(), "assets": assets})
    dump_json(DATA / "meta.json", meta)
    dump_json(DATA / "alerts.json", {"events": feed_events})
    (ROOT / "docs" / "feed.xml").write_text(alerts.rss(feed_events), encoding="utf-8")
    alerts.discord(events)
    return 0 if any(s["ok"] for s in status.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
