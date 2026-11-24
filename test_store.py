from collector.models import Offer, SourceResult
from collector.store import merge
from collector import alerts

MIN = {"Unity": 1, "Fab": 1, "itch.io": 1}


def u(i, p, r=90.0, free=False):
    return Offer(id=f"u{i}", store="Unity", name=f"A{i}", url=f"https://x/{i}", price=p, regular=r)


def test_new_items_and_history():
    assets, ev, st = merge([], [SourceResult("Unity", [u(1, 45)])], "2026-11-24", MIN)
    a = assets[0]
    assert a["hist"] == [["2026-11-24", 45]] and a["atl"] == 45 and a["on_sale"] and st["Unity"]["ok"]
    assert ev == []  # 처음 본 상품은 비교 대상이 없어 이벤트 없음


def test_new_low_and_sale_end_and_restart():
    prev, _, _ = merge([], [SourceResult("Unity", [u(1, 45), u(2, 30, 60)])], "2026-11-01", MIN)
    # 1번은 더 싸지고, 2번은 목록에서 사라짐(세일 종료)
    assets, ev, _ = merge(prev, [SourceResult("Unity", [u(1, 27)])], "2026-11-24", MIN)
    by = {a["id"]: a for a in assets}
    assert [e["type"] for e in ev] == ["new_low"] and ev[0]["prev_low"] == 45
    assert by["u1"]["atl"] == 27 and by["u1"]["hist"][-1] == ["2026-11-24", 27]
    assert by["u2"]["on_sale"] is False and by["u2"]["price"] == 60 and by["u2"]["hist"][-1] == ["2026-11-24", 60]
    # 2번 세일 재시작
    assets, ev, _ = merge(assets, [SourceResult("Unity", [u(1, 27), u(2, 30, 60)])], "2026-12-01", MIN)
    assert [e["type"] for e in ev] == ["sale_started"]


def test_guard_keeps_previous_data_on_failure():
    prev, _, _ = merge([], [SourceResult("Unity", [u(i, 10) for i in range(50)])], "2026-11-01", MIN)
    assets, ev, st = merge(prev, [SourceResult("Unity", [u(1, 10)])], "2026-11-02", MIN)
    assert not st["Unity"]["ok"] and "sudden drop" in st["Unity"]["error"]
    assert sum(a["on_sale"] for a in assets) == 50  # 덮어쓰지 않음
    assets, ev, st = merge(prev, [SourceResult("Unity", ok=False, error="Timeout")], "2026-11-02", MIN)
    assert st["Unity"]["error"] == "Timeout" and sum(a["on_sale"] for a in assets) == 50


def test_other_store_untouched_and_free_event():
    prev, _, _ = merge([], [SourceResult("Unity", [u(1, 45)])], "2026-11-01", MIN)
    f = Offer(id="f-x", store="Fab", name="Free FX", url="https://f/x", price=0.0, regular=19.99)
    assets, ev, _ = merge(prev, [SourceResult("Fab", [f])], "2026-11-02", MIN)
    assert {a["id"]: a["on_sale"] for a in assets} == {"u1": True, "f-x": True}
    # 새 상품이라도 무료 전환은 알림
    assert ev == [] or ev[0]["type"] == "new_free"


def test_alert_outputs():
    e = {"type": "new_low", "id": "u1", "store": "Unity", "name": "Final IK & <Co>", "price": 27.0, "regular": 90.0, "date": "2026-11-24", "url": "https://x?a=1&b=2"}
    assert alerts.line(e) == "[역대 최저가] Final IK & <Co> · Unity · $27.00 (정가 $90.00)"
    xml = alerts.rss([e])
    assert "&amp;lt;Co&amp;gt;" not in xml and "&lt;Co&gt;" in xml and "a=1&amp;b=2" in xml
    assert alerts.update_feed([{"x": 1}] * 100, [e])[0] is e
