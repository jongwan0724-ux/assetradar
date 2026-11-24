"""해석기 단위 테스트(네트워크 불필요).

카드 글자 예시는 2026년 11월에 각 스토어 페이지에서 보인 표시 형식을 본떠 만들었다.
스토어 화면이 바뀌면 여기 예시도 실제 debug/ 스냅샷으로 교체해야 한다.
"""
from collector.util import money_values, sale_and_regular, guess_category, discount_pct
from collector.sources import unity, fab, itch
from collector import jsonproducts, fx


def test_money_and_discount():
    assert money_values("$20.00$40.00-50%") == [20.0, 40.0]
    assert money_values("US$1,299.99") == [1299.99]
    assert discount_pct("$20.00 -50%") == 50
    assert sale_and_regular("$45\n$90\n-50%") == (45.0, 90.0)
    assert sale_and_regular("$90 $45") == (45.0, 90.0)
    assert sale_and_regular("$0.60 -40%") == (0.6, 1.0)
    assert sale_and_regular("Free") == (0.0, None)
    assert sale_and_regular("no price") == (None, None)


def test_unity_cards():
    cards = [
        {"href": "https://assetstore.unity.com/packages/vfx/shaders/stylized-grass-shader-for-unity-6-357954",
         "title": "Stylized Grass Shader (for Unity 6)", "publisher": "Staggart Creations",
         "text": "VFX\nStylized Grass Shader (for Unity 6)\n4.7(58)\nStaggart Creations\n$20.00\n$40.00\n-50%"},
        {"href": "https://assetstore.unity.com/packages/tools/animation/final-ik-14290?aid=x",
         "title": "", "publisher": "", "text": "Final IK\nRootMotion\n$45.00$90.00-50%"},
        {"href": "https://assetstore.unity.com/publishers/123", "title": "x", "text": "$1"},
    ]
    got = unity.parse_cards(cards)
    assert set(got) == {"u357954", "u14290"}
    g = got["u357954"]
    assert (g.price, g.regular, g.category, g.publisher, g.discount) == (20.0, 40.0, "vfx", "Staggart Creations", 50)
    assert got["u14290"].name == "Final IK" and got["u14290"].url.endswith("final-ik-14290")
    assert got["u14290"].category == "tool"


def test_fab_cards_free_and_sale():
    free = fab.parse_cards([{"href": "https://www.fab.com/listings/81550176-a90e-4e07-8817-c8d1a1d3884b", "title": "",
                             "text": "Absorption FX\nSHOGUN GAMES\n4.6 (14)\n-100%\nFree*\n$19.99"}], free_page=True)
    o = free["f-81550176-a90e-4e07-8817-c8d1a1d3884b"]
    assert (o.price, o.regular, o.free, o.name, o.publisher) == (0.0, 19.99, True, "Absorption FX", "SHOGUN GAMES")
    assert o.category == "vfx"
    sale = fab.parse_cards([{"href": "https://www.fab.com/listings/0065f6c6-c61e-44ba-a361-25e41c0c490a",
                             "title": "Hyper Routine-driven NPC Framework v4", "publisher": "Games By Hyper",
                             "text": "Hyper Routine-driven NPC Framework v4\nGames By Hyper\n-50%\n$49.99\n$99.99"}])
    o = next(iter(sale.values()))
    assert (o.price, o.regular, o.free) == (49.99, 99.99, False)


def test_itch_cells():
    cells = [{"gid": "2155711", "href": "https://multiplierx.itch.io/verdant-ruins-game-asset-pack", "title": "Verdant Ruins",
              "author": "multiplierx", "price": "$0.60", "sale": "-40%", "genre": "", "text": "16x16 pixel tileset"},
             {"gid": "", "href": "", "title": "broken"}]
    got = itch.parse_cells(cells)
    o = got["i-2155711"]
    assert (o.price, o.regular, o.category, o.publisher) == (0.6, 1.0, "pixel", "multiplierx")


def test_jsonproducts_generic():
    payload = {"data": {"results": [
        {"uid": "abc", "title": "Pack A", "startingPrice": {"price": 99.99, "discountedPrice": 49.99}},
        {"packageId": 14290, "name": "Final IK", "originalPrice": "90.00", "finalPrice": "45.00"},
        {"id": 7, "name": "Cents item", "price": 4500, "originalPrice": 9000},
        {"id": 8, "name": "No price"},
        {"id": 9, "title": "Free thing", "isFree": True},
    ]}}
    got = {p["id"]: p for p in jsonproducts.extract(payload)}
    assert (got["abc"]["price"], got["abc"]["regular"]) == (49.99, 99.99)
    assert (got["14290"]["price"], got["14290"]["regular"]) == (45.0, 90.0)
    assert (got["7"]["price"], got["7"]["regular"]) == (45.0, 90.0)
    assert "8" not in got
    assert got["9"]["free"] and got["9"]["price"] == 0.0


def test_category_guess_and_fx():
    assert guess_category("Universal Sound FX") == "audio"
    assert guess_category("Low Poly Animals") == "3d"
    assert guess_category("Casual GUI Pack") == "2d"
    assert fx.parse({"amount": 1.0, "base": "USD", "date": "2026-11-23", "rates": {"KRW": 1348.85}})["rate"] == 1348.85
