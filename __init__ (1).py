"""마켓별 수집기. 각 모듈은 collect(new_page, cfg) -> SourceResult 를 제공한다.

수집(브라우저)과 해석(parse_*)을 분리해서, 해석 부분은 네트워크 없이 테스트할 수 있다.
"""

# 페이지의 상품 카드에서 링크·제목·카드 전체 글자를 뽑아내는 공용 스크립트.
# 클래스 이름 대신 '상품 링크 모양'과 '가격이 들어 있는 가장 가까운 상자'를 기준으로 찾는다.
CARDS_JS = r"""
(cfg) => {
  const re = new RegExp(cfg.linkPattern);
  const out = [], seen = new Set();
  for (const a of document.querySelectorAll('a[href]')) {
    const href = a.href;
    if (!re.test(href) || seen.has(href)) continue;
    let box = a, hops = 0;
    while (box && hops < 7 && !/\$|free/i.test(box.innerText || '')) { box = box.parentElement; hops++; }
    if (!box) continue;
    // 카드가 너무 커지면(목록 전체) 버린다
    if ((box.innerText || '').length > 600) continue;
    seen.add(href);
    const img = a.querySelector('img') || box.querySelector('img');
    const pubA = cfg.publisherPattern ? [...box.querySelectorAll('a[href]')].find(x => new RegExp(cfg.publisherPattern).test(x.href)) : null;
    const title = (a.innerText || '').trim() || (img && img.alt) || a.getAttribute('aria-label') || '';
    out.push({ href, title, text: box.innerText || '', publisher: pubA ? pubA.innerText.trim() : '' });
  }
  return out;
}
"""
