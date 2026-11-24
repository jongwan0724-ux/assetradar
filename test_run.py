"""브라우저 없이 수집 전체 흐름(합치기 → 파일 쓰기)을 검사한다."""
import json
from contextlib import contextmanager

from collector import run, fx
from collector.models import Offer, SourceResult


def test_run_end_to_end(tmp_path, monkeypatch):
    data = tmp_path / "docs" / "data"
    data.mkdir(parents=True)
    (data / "assets.json").write_text(json.dumps({"assets": [
        {"id": "u1", "store": "Unity", "name": "Old", "url": "u", "price": 45, "regular": 90, "on_sale": True,
         "hist": [["2026-11-01", 45]], "atl": 45, "atl_seeded": True, "last_seen": "2026-11-01"}]}))
    monkeypatch.setattr(run, "DATA", data)
    monkeypatch.setattr(run, "ROOT", tmp_path)

    @contextmanager
    def fake_session():
        yield lambda: None
    monkeypatch.setattr(run, "session", fake_session)
    monkeypatch.setattr(fx, "fetch", lambda prev: {"rate": 1350.0, "date": "2026-11-24", "source": "test"})
    monkeypatch.setattr(run.unity, "collect", lambda np, cfg: SourceResult("Unity", [
        Offer(id="u1", store="Unity", name="Old", url="u", price=27, regular=90)] + [
        Offer(id=f"u{i}", store="Unity", name=f"N{i}", url="u", price=5, regular=10) for i in range(2, 30)]))
    monkeypatch.setattr(run.fab, "collect", lambda np, cfg: SourceResult("Fab", ok=False, error="Timeout"))
    monkeypatch.setattr(run.itch, "collect", lambda np, cfg: SourceResult("itch.io", [
        Offer(id=f"i-{i}", store="itch.io", name=f"P{i}", url="u", price=1, regular=2) for i in range(12)]))

    assert run.main([]) == 0
    assets = json.loads((data / "assets.json").read_text())["assets"]
    meta = json.loads((data / "meta.json").read_text())
    feed = json.loads((data / "alerts.json").read_text())["events"]
    assert len(assets) == 41
    assert meta["sources"]["Fab"]["ok"] is False and meta["sources"]["Unity"]["ok"] is True
    assert meta["fx"]["rate"] == 1350.0
    assert feed[0]["type"] == "new_low" and feed[0]["id"] == "u1"
    assert (tmp_path / "docs" / "feed.xml").read_text().startswith("<?xml")
