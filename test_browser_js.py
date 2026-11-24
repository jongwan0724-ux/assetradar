"""카드 추출 스크립트를 실제 브라우저(로컬 HTML)에서 검사한다. Playwright 브라우저가 없으면 건너뛴다."""
import pytest

from collector.sources import CARDS_JS, unity, itch

UNITY_HTML = """<html><body><main><div class="grid">
<div class="card"><a href="https://assetstore.unity.com/packages/tools/animation/final-ik-14290"><img alt="Final IK"></a>
<div><a href="https://assetstore.unity.com/packages/tools/animation/final-ik-14290">Final IK</a></div>
<a href="https://assetstore.unity.com/publishers/3">RootMotion</a><div>4.9(877)</div><div><span>$45.00</span><s>$90.00</s><b>-50%</b></div></div>
<div class="card"><a href="https://assetstore.unity.com/packages/3d/environments/forest-150668">Forest Environment</a>
<a href="https://assetstore.unity.com/publishers/9">NatureManufacture</a><div>$30.00 $60.00 -50%</div></div>
</div></main></body></html>"""

ITCH_HTML = """<html><body><div class="game_grid_widget">
<div class="game_cell" data-game_id="2155711"><a class="thumb_link" href="https://multiplierx.itch.io/verdant-ruins"></a>
<div class="game_cell_data"><div class="game_title"><a class="title" href="https://multiplierx.itch.io/verdant-ruins">Verdant Ruins</a>
<a class="price_tag"><div class="price_value">$0.60</div><div class="sale_tag">-40%</div></a></div>
<div class="game_author"><a href="https://multiplierx.itch.io">multiplierx</a></div><div class="game_genre">Pixel art tileset</div></div></div>
</div></body></html>"""


@pytest.fixture(scope="module")
def page():
    pw = pytest.importorskip("playwright.sync_api")
    try:
        p = pw.sync_playwright().start()
        b = p.chromium.launch()
    except Exception as e:
        pytest.skip(f"브라우저 없음: {e}")
    pg = b.new_page()
    yield pg
    b.close()
    p.stop()


def test_cards_js_unity(page):
    page.set_content(UNITY_HTML)
    cards = page.evaluate(f"({CARDS_JS})({{linkPattern: {unity.LINK!r}, publisherPattern: 'publishers/'}})")
    got = unity.parse_cards(cards)
    assert got["u14290"].price == 45.0 and got["u14290"].regular == 90.0
    assert got["u14290"].publisher == "RootMotion"
    assert got["u150668"].category == "3d" and got["u150668"].name == "Forest Environment"


def test_cells_js_itch(page):
    page.set_content(ITCH_HTML)
    got = itch.parse_cells(page.evaluate(itch.CELLS_JS))
    o = got["i-2155711"]
    assert (o.name, o.price, o.regular, o.publisher, o.category) == ("Verdant Ruins", 0.6, 1.0, "multiplierx", "pixel")
